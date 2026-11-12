"""
parking lot manager
"""
from models.parking_spot import ParkingSpot
from models.ticket import ParkingTicket
from algorithms.allocation import find_nearest_spot

class ParkingLot:
    def __init__(self, rows=4, cols=8):
        self.active_tickets = {}
        self.rows = rows
        self.cols = cols
        self.grid = self._initialize_grid()
        self.active_plates = set()

    def _initialize_grid(self):
        grid = []
        for r in range(self.rows):
            row_spots = []
            row_letter = chr(ord('A') + r)
            for c in range(self.cols):
                spot_id = f"{row_letter}{c + 1:02d}"

                # row 0 has handicap and ev, row 1 has VIP (B01-B03), others regular
                if r == 0:
                    s_type = "Handicap" if c < 3 else "EV Charging"
                elif r == 1 and c < 3:
                    s_type = "VIP"
                else:
                    s_type = "Regular"

                row_spots.append(ParkingSpot(spot_id, r, c, s_type))
            grid.append(row_spots)
        return grid

    def park_vehicle(self, vehicle):
        # check if already inside
        if vehicle.plate in self.active_plates:
            raise ValueError(f"Vehicle '{vehicle.plate}' is already parked inside!")

        spot, distance = find_nearest_spot(self.grid, vehicle)
        spot.occupy(vehicle.plate)
        self.active_plates.add(vehicle.plate)

        ticket = ParkingTicket(vehicle.plate, spot.spot_id, vehicle.vehicle_type)
        ticket.spot = spot.spot_id
        self.active_tickets[vehicle.plate] = ticket
        return ticket, spot, distance

    def get_occupancy_stats(self):
        total = self.rows * self.cols
        occupied = sum(1 for row in self.grid for spot in row if spot.is_occupied)
        return {
            "total_spots": total,
            "occupied_spots": occupied,
            "vacant_spots": total - occupied
        }
    
    def find_ticket(self, plate):
        if not plate:
            return None
        clean_target = str(plate).replace(" ", "").replace("-", "").upper()
        for p, ticket in self.active_tickets.items():
            if str(p).replace(" ", "").replace("-", "").upper() == clean_target:
                v_lower = str(getattr(ticket, "vehicle_type", "Regular")).lower()
                ticket.vehicle_type = "vip" if "vip" in v_lower else "car"
                ticket.spot = getattr(ticket, "spot_id", getattr(ticket, "spot", "A01"))
                return ticket
            if getattr(ticket, "ticket_id", "").replace("-", "").upper() == clean_target:
                v_lower = str(getattr(ticket, "vehicle_type", "Regular")).lower()
                ticket.vehicle_type = "vip" if "vip" in v_lower else "car"
                ticket.spot = getattr(ticket, "spot_id", getattr(ticket, "spot", "A01"))
                return ticket
        for row in self.grid:
            for spot in row:
                if spot.is_occupied and spot.current_plate:
                    if str(spot.current_plate).replace(" ", "").replace("-", "").upper() == clean_target:
                        ticket = ParkingTicket(spot.current_plate, spot.spot_id, "car")
                        ticket.spot = spot.spot_id
                        ticket.vehicle_type = "car"
                        return ticket
        return None

    def release_spot(self, plate):
        clean_target = str(plate).replace(" ", "").replace("-", "").upper()
        to_remove = [p for p in self.active_plates if str(p).replace(" ", "").replace("-", "").upper() == clean_target]
        for p in to_remove:
            self.active_plates.remove(p)
        to_del = [p for p in self.active_tickets if str(p).replace(" ", "").replace("-", "").upper() == clean_target]
        for p in to_del:
            del self.active_tickets[p]

        for row in self.grid:
            for spot in row:
                if spot.current_plate and str(spot.current_plate).replace(" ", "").replace("-", "").upper() == clean_target:
                    spot.vacate()
                    return True
        return False