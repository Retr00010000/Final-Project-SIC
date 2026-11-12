"""
parking ticket model
"""
import random
import string
from datetime import datetime

class ParkingTicket:
    """
    Represents the digital ticket issued at arrival.
    """
    def __init__(self, plate, spot_id, vehicle_type="Regular", ticket_id=None, entry_time=None):
        self.ticket_id = ticket_id or self.generate_ticket_id()
        self.plate = plate.upper()
        self.spot_id = spot_id
        self.vehicle_type = vehicle_type
        self.entry_time = entry_time or datetime.now()

    def generate_ticket_id(self=None):
        date_str = datetime.now().strftime("%Y%m%d")
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"TCK-{date_str}-{suffix}"

    def __repr__(self):
        return f"<ParkingTicket {self.ticket_id} Plate={self.plate} Spot={self.spot_id}>"
