"""
arrival and ticket screen
"""
import random
import streamlit as st
from models.vehicle import create_vehicle, InvalidPlateException
from algorithms.allocation import find_nearest_spot, ParkingFullException
from models.parking_lot import ParkingLot
from models.ticket import ParkingTicket

def render_arrival_screen(parking_lot):
    if parking_lot is None:
        parking_lot = ParkingLot()
        st.session_state["parking_lot"] = parking_lot

    st.header("Arrival & Digital Ticket")

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.subheader("Vehicle Check-In")

        # auto fill button
        if st.button(" Auto-Fill Sample Vehicle", use_container_width=True):
            sample = random.choice([
                ("ABC 1234", "Regular"),
                ("EV-8092", "EV"),
                ("DIS-3310", "Handicap"),
                ("VIP-7777", "VIP"),
                ("EGY 5541", "Regular"),
                ("TESLA-9", "EV"),
                ("VIP-9999", "VIP"),
            ])
            st.session_state["plate_val"] = sample[0]
            st.session_state["type_val"] = sample[1]

        # plate and vehicle type inputs
        plate_input = st.text_input(
            "License Plate Number",
            value=st.session_state.get("plate_val", "ABC 1234"),
            placeholder="e.g. ABC 1234, CA-5829",
            help="Validated with Regular Expressions (3-10 characters)."
        )

        car_type_options = ["Regular", "EV", "Handicap", "VIP"]
        current_type = st.session_state.get("type_val", "Regular")
        selected_index = car_type_options.index(current_type) if current_type in car_type_options else 0

        car_type = st.selectbox(
            "Car Type",
            options=car_type_options,
            index=selected_index,
            format_func=lambda x: {
                "Regular": " Regular Car",
                "EV": " Electric Vehicle",
                "Handicap": " Handicap Accessible",
                "VIP": " VIP Guest"
            }.get(x, x)
        )

        # separate action buttons
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            find_btn = st.button(" Find Nearest Spot", use_container_width=True)
        with btn_col2:
            issue_btn = st.button(" Issue Ticket", use_container_width=True, type="primary")

        # action 1: find nearest spot only
        if find_btn:
            if not plate_input or not plate_input.strip():
                st.warning(" Please enter a license plate number first.")
            else:
                try:
                    vehicle = create_vehicle(plate_input, car_type)
                    if vehicle.plate in parking_lot.active_plates:
                        st.warning(f" Vehicle '{vehicle.plate}' is already parked inside!")
                    else:
                        spot, distance = find_nearest_spot(parking_lot.grid, vehicle)
                        st.session_state["staged_vehicle"] = vehicle
                        st.session_state["staged_spot"] = spot
                        st.session_state["staged_distance"] = distance
                        st.success(f" Nearest spot found: **{spot.spot_id}** ({spot.spot_type}) | Distance: **{distance}** units.")
                except InvalidPlateException as ex:
                    st.error(f" {str(ex)}")
                except ParkingFullException as ex:
                    st.error(f" {str(ex)}")
                except ValueError as ex:
                    st.warning(f" {str(ex)}")
                except Exception as ex:
                    st.error(f" {str(ex)}")

        # action 2: issue ticket
        if issue_btn:
            if not plate_input or not plate_input.strip():
                st.warning(" Please enter a license plate number first.")
            else:
                try:
                    staged_spot = st.session_state.get("staged_spot")
                    staged_vehicle = st.session_state.get("staged_vehicle")

                    # if already staged for this plate
                    if staged_spot is not None and staged_vehicle is not None and staged_vehicle.plate == plate_input.strip().upper():
                        vehicle = staged_vehicle
                        spot = staged_spot
                        distance = st.session_state.get("staged_distance", 0)

                        if vehicle.plate in parking_lot.active_plates:
                            st.warning(f" Vehicle '{vehicle.plate}' is already parked inside!")
                        elif spot.is_occupied:
                            st.warning(f" Spot {spot.spot_id} was already taken! Click 'Find Nearest Spot' again.")
                        else:
                            spot.occupy(vehicle.plate)
                            parking_lot.active_plates.add(vehicle.plate)
                            ticket = ParkingTicket(vehicle.plate, spot.spot_id, vehicle.vehicle_type)
                            ticket.spot = spot.spot_id
                            parking_lot.active_tickets[vehicle.plate] = ticket

                            st.session_state["last_ticket"] = ticket
                            st.session_state["last_spot"] = spot
                            st.session_state["last_distance"] = distance
                            st.session_state["staged_spot"] = None
                            st.session_state["staged_vehicle"] = None
                            st.session_state["staged_distance"] = None

                            st.success(f" Ticket issued for Spot **{spot.spot_id}**!")
                            st.rerun()
                    else:
                        # find nearest and issue ticket directly
                        vehicle = create_vehicle(plate_input, car_type)
                        ticket, spot, distance = parking_lot.park_vehicle(vehicle)

                        st.session_state["last_ticket"] = ticket
                        st.session_state["last_spot"] = spot
                        st.session_state["last_distance"] = distance
                        st.session_state["staged_spot"] = None
                        st.session_state["staged_vehicle"] = None
                        st.session_state["staged_distance"] = None

                        st.success(f" Ticket issued for Spot **{spot.spot_id}**!")
                        st.rerun()

                except InvalidPlateException as ex:
                    st.error(f" {str(ex)}")
                except ParkingFullException as ex:
                    st.error(f" {str(ex)}")
                except ValueError as ex:
                    st.warning(f" {str(ex)}")
                except Exception as ex:
                    st.error(f" {str(ex)}")

        # status message when a spot is found and waiting to be ticketed
        if st.session_state.get("staged_spot") is not None:
            s_spot = st.session_state["staged_spot"]
            s_dist = st.session_state["staged_distance"]
            s_veh = st.session_state["staged_vehicle"]
            st.info(f" Staged Spot: **{s_spot.spot_id}** ({s_spot.spot_type}) for **{s_veh.plate}** ({s_dist} units away). Click **'Issue Ticket'** to confirm entry.")

    with right_col:
        st.subheader("Issued Digital Ticket")

        # check if last issued ticket's vehicle is still actively parked in the garage
        last_ticket = st.session_state.get("last_ticket")
        if last_ticket is not None:
            clean_plate = str(getattr(last_ticket, "plate", "")).replace(" ", "").replace("-", "").upper()
            is_active = any(str(p).replace(" ", "").replace("-", "").upper() == clean_plate for p in parking_lot.active_plates)
            if not is_active:
                st.session_state["last_ticket"] = None
                st.session_state["last_spot"] = None
                st.session_state["last_distance"] = None
                last_ticket = None

        # show ticket if available and car is still in garage
        if last_ticket is not None:
            ticket = last_ticket
            spot = st.session_state["last_spot"]
            distance = st.session_state["last_distance"]

            # digital ticket card without leading whitespace
            ticket_card = (
                f'<div style="background: #1e293b; border: 2px solid #38bdf8; border-radius: 14px; padding: 20px; color: white;">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">'
                f'<div><strong style="color: #38bdf8; font-size: 18px;">🅿️ PARKFLOW TICKET</strong></div>'
                f'<div style="text-align: right;"><span style="font-family: monospace; color: #cbd5e1;">{ticket.ticket_id}</span></div>'
                f'</div>'
                f'<div style="display: flex; justify-content: space-between; margin-bottom: 14px;">'
                f'<div><span style="font-size: 11px; color: #94a3b8;">LICENSE PLATE</span><div style="font-size: 20px; font-weight: bold; color: #facc15;">{ticket.plate}</div></div>'
                f'<div style="text-align: right;"><span style="font-size: 11px; color: #94a3b8;">ASSIGNED SPOT</span><div style="font-size: 22px; font-weight: bold; color: #4ade80;">{spot.spot_id}</div></div>'
                f'</div>'
                f'<div style="background: rgba(255,255,255,0.06); padding: 10px; border-radius: 8px; font-size: 13px;">'
                f'<div>Car Type: <strong>{ticket.vehicle_type}</strong></div>'
                f'<div>Spot Type: <strong>{spot.spot_type}</strong></div>'
                f'<div>Distance from Gate: <strong>{distance} units</strong></div>'
                f'<div>Entry Time: <strong>{ticket.entry_time.strftime("%Y-%m-%d %H:%M:%S")}</strong></div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(ticket_card, unsafe_allow_html=True)
            if st.button("Dismiss Ticket", key="dismiss_ticket_btn", use_container_width=True):
                st.session_state["last_ticket"] = None
                st.session_state["last_spot"] = None
                st.session_state["last_distance"] = None
                st.rerun()

        else:
            st.info("Enter a license plate, click **'Find Nearest Spot'**, then click **'Issue Ticket'**.")

    # 2d garage map
    st.divider()
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
    .spot-yellow {
        background-color: rgba(234, 179, 8, 0.15);
        border: 1.5px solid #eab308;
        color: #a16207;
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
        .spot-yellow {
            background-color: rgba(234, 179, 8, 0.2);
            border-color: #facc15;
            color: #facc15;
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

    # Staged nearest spot id
    staged_spot_id = None
    if "staged_spot" in st.session_state and st.session_state["staged_spot"] is not None:
        staged_spot_id = getattr(st.session_state["staged_spot"], "spot_id", None)

    for floor_idx in range(len(tabs)):
        tab = tabs[floor_idx]
        with tab:
            rows = floor_mapping[floor_idx]
            for row in rows:
                cols = st.columns(len(row))
                for i in range(len(row)):
                    spot = row[i]
                    with cols[i]:
                        # Spot type indication: Private, Electric, VIP, or Public (no emoji)
                        if spot.spot_type == "Handicap":
                            type_name = "Private"
                        elif spot.spot_type == "EV Charging":
                            type_name = "Electric"
                        elif spot.spot_type == "VIP":
                            type_name = "VIP"
                        else:
                            type_name = "Public"

                        is_staged = (spot.spot_id == staged_spot_id and not spot.is_occupied)

                        if spot.is_occupied:
                            card_class = "spot-red"
                            body_html = f'<div class="spot-body" style="font-weight: 600;">{spot.current_plate}</div>'
                        elif is_staged:
                            card_class = "spot-yellow"
                            body_html = '<div class="spot-body" style="font-weight: 600;">Nearest Found</div>'
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
