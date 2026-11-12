import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "modules"))
)

import streamlit as st
from models.parking_lot import ParkingLot
from modules.arrival import render_arrival_screen
from modules.exitscreen import render_exit_screen
from modules.member4_admin import render_member4_admin
from modules.view import show_grid_page

st.set_page_config(page_title="ParkFlow - Smart Parking System", layout="wide")

if "parking_lot" not in st.session_state:
    st.session_state.parking_lot = ParkingLot()

parking_lot = st.session_state.parking_lot

st.title("ParkFlow: Smart Parking Management System")
st.caption("Samsung Innovation Campus (SIC 8) - Applied Graduation Project (Chapters 1-8)")
st.write("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "1. Arrival & Entry",
    "2. Live 2D Grid & Valet",
    "3. Exit & Checkout",
    "4. Admin Intelligence",
])

with tab1:
    render_arrival_screen(parking_lot)

with tab2:
    show_grid_page()

with tab3:
    render_exit_screen(parking_lot)

with tab4:
    render_member4_admin(total_spots=parking_lot.rows * parking_lot.cols)

with st.sidebar:
    st.header("Garage Overview")
    stats = parking_lot.get_occupancy_stats()
    st.metric("Total Spots", stats["total_spots"])
    st.metric("Active Occupied", stats["occupied_spots"])
    st.metric("Free Vacant", stats["vacant_spots"])
    st.write("---")
    if st.button("Reset Garage", use_container_width=True):
        st.session_state.parking_lot = ParkingLot()
        st.session_state["pending_invoice"] = None
        st.session_state["paid_invoice"] = None
        st.session_state["last_ticket"] = None
        st.session_state["last_spot"] = None
        st.session_state["last_distance"] = None
        st.session_state["staged_spot"] = None
        st.session_state["staged_vehicle"] = None
        st.session_state["staged_distance"] = None
        st.session_state["plate_val"] = "ABC 1234"
        if "valet" in st.session_state:
            from algorithms.stack import Stack
            st.session_state.valet = Stack(capacity=5)
        st.rerun()
