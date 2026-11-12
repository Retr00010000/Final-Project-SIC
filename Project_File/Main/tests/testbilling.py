# quick tests for billing.py
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules.billing import *

start = datetime(2026, 1, 1, 10, 0)


def fee(vtype, **kw):
    return calculate_fee(vtype, start, start + timedelta(**kw))


# free period
assert fee("car", minutes=10)["total"] == 0

# 61 min = 2 hours = 20 + 14% vat
assert fee("car", minutes=61)["subtotal"] == 20
assert fee("car", minutes=61)["total"] == 22.8

# exactly 1 hour
assert fee("car", minutes=60)["subtotal"] == 10

# daily cap (12 hours should cost 8 hours)
assert fee("car", hours=12)["subtotal"] == 80

# one day and 3 hours
assert fee("car", days=1, hours=3)["subtotal"] == 110

# other vehicles
assert fee("motorcycle", hours=2)["subtotal"] == 10
assert fee("truck", hours=2)["subtotal"] == 40

# wrong type
try:
    calculate_fee("bike", start, start)
    raise SystemExit("should have failed")
except BillingError:
    pass

# exit before entry
try:
    calculate_fee("car", start, start - timedelta(hours=1))
    raise SystemExit("should have failed")
except BillingError:
    pass

# cash
assert CashPayment(50).pay(22.8)["change"] == 27.2

# bad payments, all of them should raise PaymentError
bad_ones = [
    CashPayment(10),
    CardPayment("1234", "08/28", "123"),
    CardPayment("1234567890123456", "13/28", "123"),
    CardPayment("1234567890123456", "01/20", "123"),
    CardPayment("1234567890123456", "08/99", "12"),
    WalletPayment("0912345678"),
]
for p in bad_ones:
    try:
        p.pay(22.8)
        raise SystemExit("should have failed")
    except PaymentError:
        pass

# good payments
assert CardPayment("1234 5678 9012 3456", "08/99", "123").pay(1)["card"].endswith("3456")
assert WalletPayment("01012345678").pay(1)

# stack order (last in, first out)
h = TransactionHistory()
a = Invoice("A", "car", "s", start, start)
b = Invoice("B", "car", "s", start, start)
h.push(a)
h.push(b)
assert h.undo_last() is b
assert h.undo_last() is a
try:
    h.undo_last()
    raise SystemExit("should have failed")
except IndexError:
    pass

assert normalize_plate(" abc-123 ") == "ABC123"
# rush hours: car enters 08:00 for 2 hours, both hours are peak (2 x 15)
rush = datetime(2026, 1, 1, 8, 0)
r = calculate_fee("car", rush, rush + timedelta(hours=2))
assert r["subtotal"] == 30 and r["peak_hours"] == 2

# starts 09:30 for 1h30 -> hours start 09:30 (peak) and 10:30 (normal) = 15 + 10
r = calculate_fee("car", datetime(2026, 1, 1, 9, 30), datetime(2026, 1, 1, 11, 0))
assert r["subtotal"] == 25 and r["peak_hours"] == 1

# peak hours still respect the daily cap (08:00 for 12 hours would be over 80)
assert calculate_fee("car", rush, rush + timedelta(hours=12))["subtotal"] == 80

# ticket id is saved on the invoice and in the csv row
inv = Invoice("ABC123", "car", "A-3", start, start + timedelta(hours=1), "T-009")
assert inv.ticket_id == "T-009" and inv.to_row()["ticket_id"] == "T-009"
assert Invoice("A", "car", "s", start, start).ticket_id == "-"
print("All tests passed")