from datetime import datetime, timedelta

import streamlit as st

from billing import (BillingError, CardPayment, CashPayment, Invoice,
                     PaymentError, TransactionHistory, WalletPayment,
                     format_duration, normalize_plate, remove_session,
                     save_session)

def find_ticket(garage, text):
    # the cashier can type the plate number or scan the ticket id
    ticket = garage.find_ticket(normalize_plate(text))
    if ticket is None and hasattr(garage, "find_ticket_by_id"):
        ticket = garage.find_ticket_by_id(text.strip().upper())
    return ticket

def release(garage, plate):
    if "last_ticket" in st.session_state and st.session_state["last_ticket"] is not None:
        last_p = str(getattr(st.session_state["last_ticket"], "plate", "")).replace(" ", "").replace("-", "").upper()
        target_p = str(plate).replace(" ", "").replace("-", "").upper()
        if last_p == target_p:
            st.session_state["last_ticket"] = None
            st.session_state["last_spot"] = None
            st.session_state["last_distance"] = None
    garage.release_spot(plate)

def ticket_info(t):
    return t.plate, t.vehicle_type, t.spot, t.entry_time, getattr(t, "ticket_id", None)

def render_exit_screen(garage):
    st.header("Exit & Payment")

    # session_state so the data stays after each click
    if "pending_invoice" not in st.session_state:
        st.session_state.pending_invoice = None
    if "paid_invoice" not in st.session_state:
        st.session_state.paid_invoice = None
    if "history" not in st.session_state:
        st.session_state.history = TransactionHistory()

    tab1, tab2 = st.tabs(["Checkout", "Transactions"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        plate_text = col1.text_input("Plate number or ticket ID", placeholder="e.g. ABC 1234 or T-001")
        col2.write("")
        col2.write("")
        if col2.button("Find car", use_container_width=True):
            search_car(garage, plate_text)

        if st.session_state.pending_invoice is not None:
            show_invoice(garage, st.session_state.pending_invoice)
        elif st.session_state.paid_invoice is not None:
            show_receipt(st.session_state.paid_invoice)

    with tab2:
        show_history(garage)

def search_car(garage, plate_text):
    st.session_state.paid_invoice = None
    st.session_state.pending_invoice = None

    if plate_text.strip() == "":
        st.error("Please enter the plate number or the ticket ID")
        return

    ticket = find_ticket(garage, plate_text)
    if ticket is None:
        st.error("No parked car found for " + plate_text.strip().upper())
        return

    try:
        p, vtype, spot, entry, ticket_id = ticket_info(ticket)
        st.session_state.pending_invoice = Invoice(p, vtype, spot, entry, datetime.now(), ticket_id)
    except BillingError as e:
        st.error(str(e))

def show_invoice(garage, invoice):
    fee = invoice.fee
    st.subheader("Car " + invoice.plate + " - Spot " + str(invoice.spot) + " - Ticket " + str(invoice.ticket_id))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entry", invoice.entry_time.strftime("%H:%M"))
    c2.metric("Exit (now)", invoice.exit_time.strftime("%H:%M"))
    c3.metric("Duration", format_duration(fee["duration_min"]))
    c4.metric("Total", "%.2f EGP" % fee["total"])

    if fee["peak_hours"] > 0:
        st.info(str(fee["peak_hours"]) + " hour(s) were in rush time and billed at x1.5")

    if fee["total"] == 0:
        st.success("Free stay (under the grace period), nothing to pay")

    with st.expander("Invoice details", expanded=True):
        st.code(invoice.as_text(), language=None)

    st.markdown("#### Payment method")
    method = st.radio("How do you want to pay?", ["Cash", "Card", "Mobile Wallet"],
                      horizontal=True)

    if method == "Cash":
        given = st.number_input("Amount received (EGP)", min_value=0.0,
                                value=float(invoice.total), step=5.0)
        payer = CashPayment(given)
    elif method == "Card":
        number = st.text_input("Card number", placeholder="1234 5678 9012 3456")
        c1, c2 = st.columns(2)
        expiry = c1.text_input("Expiry (MM/YY)", placeholder="08/28")
        cvv = c2.text_input("CVV", type="password", max_chars=3)
        payer = CardPayment(number, expiry, cvv)
    else:
        phone = st.text_input("Wallet mobile number", placeholder="01012345678")
        payer = WalletPayment(phone)

    if st.button("Pay & open gate", type="primary"):
        try:
            result = payer.pay(invoice.total)
        except PaymentError as e:
            st.error(str(e))
            return

        invoice.payment_method = result["method"]
        release(garage, invoice.plate)
        save_session(invoice)
        st.session_state.history.push(invoice)
        st.session_state.paid_invoice = invoice
        st.session_state.pending_invoice = None
        st.session_state.change = result.get("change")
        st.rerun()


def show_receipt(invoice):
    st.success("Payment received (" + invoice.payment_method + "). Gate is open, have a safe trip!")
    change = st.session_state.get("change")
    if change:
        st.info("Change to return: %.2f EGP" % change)
    st.code(invoice.as_text(), language=None)
    st.download_button("Download invoice", invoice.as_text(),
                       file_name=invoice.invoice_no + ".txt")


def show_history(garage):
    history = st.session_state.history
    if len(history) == 0:
        st.info("No payments yet in this session")
        return

    rows = []
    total = 0
    for inv in history.recent():
        rows.append({
            "Invoice": inv.invoice_no,
            "Ticket": inv.ticket_id,
            "Plate": inv.plate,
            "Total (EGP)": inv.total,
            "Method": inv.payment_method,
            "Exit": inv.exit_time.strftime("%H:%M"),
        })
        total += inv.total

    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.metric("Session revenue", "%.2f EGP" % total)

    st.caption("Undo takes the last payment out of the stack (refund)")
    if st.button("Undo last payment"):
        inv = history.undo_last()
        remove_session(inv)
        # put the car back if member 2 made restore_spot
        if hasattr(garage, "restore_spot"):
            garage.restore_spot(inv.plate, inv.vehicle_type, inv.spot, inv.entry_time)
        st.warning(inv.invoice_no + " refunded (%.2f EGP)" % inv.total)
        st.rerun()

# ---- fake garage, only for testing this screen alone ----
class FakeTicket:
    def __init__(self, plate, vtype, spot, entry, ticket_id):
        self.ticket_id = ticket_id
        self.plate = plate
        self.vehicle_type = vtype
        self.spot = spot
        self.entry_time = entry

class FakeGarage:
    def __init__(self):
        now = datetime.now()
        self.tickets = {
            "ABC123": FakeTicket("ABC123", "car", "A-3", now - timedelta(hours=2, minutes=20), "T-001"),
            "XYZ789": FakeTicket("XYZ789", "motorcycle", "B-1", now - timedelta(minutes=6), "T-002"),
            "TRK555": FakeTicket("TRK555", "truck", "C-2", now - timedelta(days=1, hours=3), "T-003"),
        }

    def find_ticket(self, plate):
        return self.tickets.get(plate)

    def find_ticket_by_id(self, ticket_id):
        for t in self.tickets.values():
            if t.ticket_id == ticket_id:
                return t
        return None

    def release_spot(self, plate):
        if plate in self.tickets:
            del self.tickets[plate]

if __name__ == "__main__":
    st.set_page_config(page_title="ParkFlow - Exit")
    if "garage" not in st.session_state:
        st.session_state.garage = FakeGarage()
    st.caption("Test plates: ABC123, XYZ789, TRK555  |  test tickets: T-001, T-002, T-003")
    render_exit_screen(st.session_state.garage)