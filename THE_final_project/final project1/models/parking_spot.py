"""
parking spot model
"""
class SpotOccupiedException(Exception):
    pass

class ParkingSpot:
    def __init__(self, spot_id, row, col, spot_type="Regular"):
        self.spot_id = spot_id
        self.row = row
        self.col = col
        self.spot_type = spot_type
        self.is_occupied = False
        self.current_plate = None

    def distance_from(self, gate_row=0, gate_col=0):
        # manhattan distance to gate
        return abs(self.row - gate_row) + abs(self.col - gate_col)

    def occupy(self, plate):
        if self.is_occupied:
            raise SpotOccupiedException(f"Spot {self.spot_id} is already occupied.")
        self.is_occupied = True
        self.current_plate = plate

    def vacate(self):
        self.is_occupied = False
        self.current_plate = None

    def __repr__(self):
        status = "OCCUPIED" if self.is_occupied else "VACANT"
        return f"<ParkingSpot {self.spot_id} ({self.spot_type}) [{status}]>"
