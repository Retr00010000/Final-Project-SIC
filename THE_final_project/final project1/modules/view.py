import streamlit as st
from algorithms.stack import Stack

def init_valet():
    if "valet" not in st.session_state:
        st.session_state.valet = Stack(capacity=5)

def show_grid_page(parking_lot=None):
    if parking_lot is None:
        parking_lot = st.session_state.parking_lot

    init_valet()
    valet = st.session_state.valet

    st.header("Live Parking")
    st.subheader("Parking Floors")

    spot_styles = """
    <style>
    .spot-card {
        border-radius: 8px;
        padding: 10px 12px;
        min-height: 74px;
        margin-bottom: 8px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .spot-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        line-height: 1.2;
    }
    .spot-id {
        font-weight: 700;
        font-size: 15px;
    }
    .spot-tag {
        font-size: 12px;
        font-weight: 500;
        opacity: 0.85;
    }
    .spot-body {
        font-size: 13px;
        margin-top: 6px;
    }
    .spot-green {
        background-color: rgba(33, 195, 84, 0.12);
        border: 1px solid rgba(33, 195, 84, 0.3);
        color: #15803d;
    }
    .spot-red {
        background-color: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #b91c1c;
    }
    .spot-purple {
        background-color: rgba(147, 51, 234, 0.12);
        border: 1.5px solid rgba(147, 51, 234, 0.4);
        color: #7e22ce;
    }
    @media (prefers-color-scheme: dark) {
        .spot-green {
            background-color: rgba(33, 195, 84, 0.18);
            border-color: rgba(33, 195, 84, 0.4);
            color: #4ade80;
        }
        .spot-red {
            background-color: rgba(239, 68, 68, 0.18);
            border-color: rgba(239, 68, 68, 0.4);
            color: #f87171;
        }
        .spot-purple {
            background-color: rgba(147, 51, 234, 0.18);
            border-color: rgba(147, 51, 234, 0.5);
            color: #c084fc;
        }
    }
    </style>
    """
    st.markdown(spot_styles, unsafe_allow_html=True)

    tabs = st.tabs(["Floor 1 (Rows A-B)", "Floor 2 (Rows C-D)"])

    floor_mapping = {
        0: [parking_lot.grid[0], parking_lot.grid[1]],
        1: [parking_lot.grid[2], parking_lot.grid[3]],
    }

    for floor_idx, tab in enumerate(tabs):
        with tab:
            rows = floor_mapping[floor_idx]
            for row in rows:
                cols = st.columns(len(row))
                for i, spot in enumerate(row):
                    with cols[i]:
                        # Spot type indication: Private, Electric, VIP, or Public
                        if spot.spot_type == "Handicap":
                            type_name = "Private"
                        elif spot.spot_type == "EV Charging":
                            type_name = "Electric"
                        elif spot.spot_type == "VIP":
                            type_name = "VIP"
                        else:
                            type_name = "Public"

                        if spot.is_occupied:
                            card_class = "spot-red"
                            body_html = f'<div class="spot-body" style="font-weight: 600;">{spot.current_plate}</div>'
                        elif spot.spot_type == "VIP":
                            card_class = "spot-purple"
                            body_html = '<div class="spot-body">Available</div>'
                        else:
                            card_class = "spot-green"
                            body_html = '<div class="spot-body">Available</div>'

                        card_html = (
                            f'<div class="spot-card {card_class}">'
                            f'<div class="spot-header">'
                            f'<span class="spot-id">{spot.spot_id}</span>'
                            f'<span class="spot-tag">({type_name})</span>'
                            f'</div>'
                            f'{body_html}'
                            f'</div>'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)

                        if spot.is_occupied:
                            if st.button("Leave", key=f"v_leave_{spot.spot_id}", use_container_width=True):
                                if "last_ticket" in st.session_state and st.session_state["last_ticket"] is not None:
                                    last_p = str(getattr(st.session_state["last_ticket"], "plate", "")).replace(" ", "").replace("-", "").upper()
                                    curr_p = str(spot.current_plate).replace(" ", "").replace("-", "").upper()
                                    if last_p == curr_p:
                                        st.session_state["last_ticket"] = None
                                        st.session_state["last_spot"] = None
                                        st.session_state["last_distance"] = None
                                parking_lot.release_spot(spot.current_plate)
                                st.rerun()

    st.write("---")

    st.subheader("Valet Parking (Stack)")
    left_col, right_col = st.columns(2)

    with left_col:
        st.write("Park Car in Valet:")
        car_input = st.text_input("Enter Car Plate", key="new_valet")
        if st.button("Park in Valet"):
            if car_input:
                try:
                    valet.push(car_input.strip().upper())
                    st.success("Car parked in valet lane...")
                    st.rerun()
                except Exception as error:
                    st.error(str(error))

        st.write("")
        if st.button("Exit Front Car"):
            try:
                removed_car = valet.pop()
                st.info(f"Car {removed_car} left.")
                st.rerun()
            except Exception as error:
                st.error(str(error))

    with right_col:
        st.write("Current Cars in Valet:")
        valet_cars = valet.get_all()
        if valet_cars:
            for c in reversed(valet_cars):
                st.text(f"Car: {c}")
        else:
            st.caption("Valet lane is empty.")

    st.write("")
    st.write("Retrieve Target Car:")
    target_car = st.text_input("Car to Retrieve", key="target_valet")
    if st.button("Retrieve"):
        if target_car:
            found, steps = valet.retrieve_car(target_car.strip().upper())
            if found:
                st.success("Car retrieved successfully...")
            else:
                st.error("Car not found...")

            for s in steps:
                st.write(f"- {s}")
            st.rerun()

if __name__ == "__main__":
    show_grid_page()