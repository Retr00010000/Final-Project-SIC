"""
greedy nearest spot allocation
"""
class ParkingFullException(Exception):
    pass

def find_nearest_spot(grid, vehicle, gate_coords=(0, 0)):
    gate_r, gate_c = gate_coords
    compatible_types = vehicle.get_compatible_spot_types()

    # get candidate spots
    candidates = []
    for target_type in compatible_types:
        for row in grid:
            for spot in row:
                if not spot.is_occupied and spot.spot_type == target_type:
                    candidates.append(spot)
        if candidates:
            break

    if not candidates:
        raise ParkingFullException(f"No vacant spots available for {vehicle.vehicle_type} cars.")

    # pick nearest spot
    i = 0
    min_dist = candidates[i].distance_from(gate_r, gate_c)

    for j in range(1, len(candidates)):
        dist = candidates[j].distance_from(gate_r, gate_c)
        if dist < min_dist:
            min_dist = dist
            i = j

    return candidates[i], min_dist
