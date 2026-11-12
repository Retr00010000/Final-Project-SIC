# billing.py - exit and payment logic (part 3)
# no streamlit in this file, only the calculations and the classes

import csv
import math
import os
import re
from datetime import datetime, timedelta

# prices per hour in EGP
RATES = {"car": 10, "motorcycle": 5, "truck": 20, "vip": 35}
FREE_MINUTES = 10     
DAY_CAP_HOURS = 8     
VAT = 0.14

# rush hours cost more: an hour that starts in these hours is billed x1.5
PEAK_HOURS = (7, 8, 9, 16, 17, 18)
PEAK_MULTIPLIER = 1.5

COLUMNS = ["invoice_no", "ticket_id", "plate", "vehicle_type", "spot", "entry_time",
           "exit_time", "duration_min", "subtotal", "vat", "total",
           "payment_method"]

class BillingError(Exception):
    pass

class PaymentError(Exception):
    pass

# my own stack, we need it for the undo
class Stack:
    def __init__(self):
        self.items = []

    def push(self, x):
        self.items.append(x)

    def pop(self):
        if len(self.items) == 0:
            raise IndexError("stack is empty")
        return self.items.pop()

    def is_empty(self):
        return len(self.items) == 0

    def size(self):
        return len(self.items)

    def newest_first(self):
        result = []
        i = len(self.items) - 1
        while i >= 0:
            result.append(self.items[i])
            i -= 1
        return result

def calculate_fee(vehicle_type, entry_time, exit_time):
    vtype = str(vehicle_type).strip().lower()
    if vtype not in RATES:
        raise BillingError("Unknown vehicle type: " + str(vehicle_type))
    if exit_time < entry_time:
        raise BillingError("Exit time is before entry time")

    rate = RATES[vtype]
    minutes = int((exit_time - entry_time).total_seconds() // 60)

    subtotal = 0
    hours = 0
    peak_hours = 0

    if minutes > FREE_MINUTES:
        # every hour that started is paid
        hours = math.ceil(minutes / 60)
        cap = DAY_CAP_HOURS * rate
        block_fee = 0

        for k in range(hours):
            hour_start = entry_time + timedelta(hours=k)
            price = rate
            if hour_start.hour in PEAK_HOURS:
                price = rate * PEAK_MULTIPLIER
                peak_hours += 1
            block_fee += price

            # close the block after 24 hours (or at the last hour) and apply the daily cap
            if (k + 1) % 24 == 0 or k == hours - 1:
                subtotal += min(block_fee, cap)
                block_fee = 0

    vat = round(subtotal * VAT, 2)
    return {
        "duration_min": minutes,
        "billable_hours": hours,
        "peak_hours": peak_hours,
        "rate": rate,
        "subtotal": round(subtotal, 2),
        "vat": vat,
        "total": round(subtotal + vat, 2),
    }

def format_duration(minutes):
    h = int(minutes) // 60
    m = int(minutes) % 60
    return str(h) + "h " + str(m).zfill(2) + "m"

class Invoice:
    counter = 1000

    def __init__(self, plate, vehicle_type, spot, entry_time, exit_time, ticket_id=None):
        Invoice.counter += 1
        self.invoice_no = "INV-" + str(Invoice.counter)
        self.ticket_id = ticket_id or "-"
        self.plate = plate
        self.vehicle_type = vehicle_type
        self.spot = spot
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.fee = calculate_fee(vehicle_type, entry_time, exit_time)
        self.payment_method = None
        self.refunded = False

    @property
    def total(self):
        return self.fee["total"]

    def as_text(self):
        f = self.fee
        line = "=" * 38
        lines = [
            line,
            "          PARKFLOW - INVOICE",
            line,
            "Invoice no : " + self.invoice_no,
            "Ticket     : " + str(self.ticket_id),
            "Plate      : " + self.plate,
            "Vehicle    : " + self.vehicle_type.title(),
            "Spot       : " + str(self.spot),
            "Entry      : " + self.entry_time.strftime("%Y-%m-%d %H:%M"),
            "Exit       : " + self.exit_time.strftime("%Y-%m-%d %H:%M"),
            "Duration   : " + format_duration(f["duration_min"]),
            "-" * 38,
            "Rate       : %.2f EGP / hour" % f["rate"],
            "Billable   : %d hour(s)" % f["billable_hours"],
            "Peak hours : %d (x%.1f rate)" % (f["peak_hours"], PEAK_MULTIPLIER),
            "Subtotal   : %.2f EGP" % f["subtotal"],
            "VAT 14%%    : %.2f EGP" % f["vat"],
            "TOTAL      : %.2f EGP" % f["total"],
            "-" * 38,
            "Paid by    : " + str(self.payment_method or "-"),
            line,
        ]
        return "\n".join(lines)

    def to_row(self):
        f = self.fee
        return {
            "invoice_no": self.invoice_no,
            "ticket_id": self.ticket_id,
            "plate": self.plate,
            "vehicle_type": self.vehicle_type,
            "spot": self.spot,
            "entry_time": self.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time": self.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_min": f["duration_min"],
            "subtotal": f["subtotal"],
            "vat": f["vat"],
            "total": f["total"],
            "payment_method": self.payment_method,
        }

# payment methods - same pay() function, each one checks different things
class PaymentMethod:
    name = "Base"

    def pay(self, amount):
        raise NotImplementedError

class CashPayment(PaymentMethod):
    name = "Cash"

    def __init__(self, given):
        self.given = given

    def pay(self, amount):
        if self.given is None or self.given < amount:
            raise PaymentError("Not enough cash. Total is %.2f EGP" % amount)
        return {"method": self.name, "change": round(self.given - amount, 2)}

class CardPayment(PaymentMethod):
    name = "Card"

    def __init__(self, number, expiry, cvv):
        self.number = re.sub(r"[\s-]", "", number or "")
        self.expiry = (expiry or "").strip()
        self.cvv = (cvv or "").strip()

    def pay(self, amount):
        if not re.match(r"^\d{16}$", self.number):
            raise PaymentError("Card number must be 16 digits")

        m = re.match(r"^(0[1-9]|1[0-2])/(\d{2})$", self.expiry)
        if not m:
            raise PaymentError("Expiry should be like 08/28")
        month = int(m.group(1))
        year = 2000 + int(m.group(2))
        now = datetime.now()
        if year < now.year or (year == now.year and month < now.month):
            raise PaymentError("Card is expired")

        if not re.match(r"^\d{3}$", self.cvv):
            raise PaymentError("CVV must be 3 digits")

        return {"method": self.name, "card": "**** " + self.number[-4:]}

class WalletPayment(PaymentMethod):
    name = "Mobile Wallet"

    def __init__(self, phone):
        self.phone = (phone or "").strip()

    def pay(self, amount):
        # egyptian numbers: 010, 011, 012, 015 + 8 digits
        if not re.match(r"^01[0125]\d{8}$", self.phone):
            raise PaymentError("Wallet number should be like 01012345678")
        return {"method": self.name, "wallet": self.phone[:3] + "*****" + self.phone[-3:]}


# every paid invoice goes on the stack, so undo takes the last one
class TransactionHistory:
    def __init__(self):
        self.stack = Stack()

    def push(self, invoice):
        self.stack.push(invoice)

    def undo_last(self):
        if self.stack.is_empty():
            raise IndexError("Nothing to undo")
        invoice = self.stack.pop()
        invoice.refunded = True
        return invoice

    def recent(self):
        return self.stack.newest_first()

    def __len__(self):
        return self.stack.size()

def save_session(invoice, path="data/sessions.csv"):
    # the admin dashboard reads this file
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    is_new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(invoice.to_row())

def remove_session(invoice, path="data/sessions.csv"):
    # used when a payment is undone
    if not os.path.exists(path):
        return
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["invoice_no"] != invoice.invoice_no]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

def normalize_plate(text):
    # "abc 123" -> "ABC123"
    return re.sub(r"[\s-]", "", text or "").upper()