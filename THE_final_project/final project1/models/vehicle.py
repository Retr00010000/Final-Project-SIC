"""
vehicle classes and regex plate validation
"""
import re
class InvalidPlateException(Exception):
    pass

class Vehicle:
    plate_regex = re.compile(r"^[A-Za-z0-9\u0600-\u06FF\s\-]{3,10}$")

    def __init__(self, plate, vehicle_type="Regular"):
        self.plate = self.validate_plate(plate)
        self.vehicle_type = vehicle_type

    @classmethod
    def validate_plate(cls, plate):
        if not plate or not isinstance(plate, str):
            raise InvalidPlateException("License plate cannot be empty.")
        
        cleaned = plate.strip().upper()
        if not cls.plate_regex.match(cleaned):
            raise InvalidPlateException(
                f"Invalid plate '{cleaned}'. Must be 3-10 characters (e.g. 'ABC 1234')."
            )
        return cleaned

    def get_compatible_spot_types(self):
        """Polymorphic method overridden by subclasses."""
        return ["Regular"]

    def __repr__(self):
        return f"<{self.vehicle_type} Plate={self.plate}>"

class RegularCar(Vehicle):
    """Standard car."""
    def __init__(self, plate):
        super().__init__(plate, "Regular")

    def get_compatible_spot_types(self):
        return ["Regular"]

class ElectricVehicle(Vehicle):
    """Electric car (prefers EV charging spots)."""
    def __init__(self, plate):
        super().__init__(plate, "EV")

    def get_compatible_spot_types(self):
        return ["EV Charging", "Regular"]

class HandicapVehicle(Vehicle):
    """Handicap accessible car (prefers accessible spots near gate)."""
    def __init__(self, plate):
        super().__init__(plate, "Handicap")

    def get_compatible_spot_types(self):
        return ["Handicap", "Regular"]

class VIPVehicle(Vehicle):
    def __init__(self, plate):
        super().__init__(plate, "VIP")

    def get_compatible_spot_types(self):
        return ["VIP", "Regular"]

def create_vehicle(plate, vehicle_type="Regular"):
    v_type = vehicle_type.strip().lower()
    if "ev" in v_type or "electric" in v_type:
        return ElectricVehicle(plate)
    elif "handicap" in v_type or "disab" in v_type:
        return HandicapVehicle(plate)
    elif "vip" in v_type:
        return VIPVehicle(plate)
    else:
        return RegularCar(plate)
