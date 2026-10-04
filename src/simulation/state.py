from src.models.drone import Drone
from src.models.zone import Zone


class SimulationState:
    def __init__(
        self,
        drones: list[Drone],
        start: Zone | None = None,
        end: Zone | None = None,
    ):
        self.drones = drones
        self.start = start
        self.end = end
        self.turn = 0

    def drones_at(self, zone_name: str) -> list[Drone]:
        return [
            drone
            for drone in self.drones
            if drone.curr_location.name == zone_name
        ]
