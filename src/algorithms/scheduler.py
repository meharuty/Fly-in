"""Scheduler: plans every drone, then replays the plan turn by turn."""
from src.algorithms.planner import Leg, TimeExpandedPlanner
from src.models.drone import Drone
from src.models.network import Network
from src.simulation.movement import Movement
from src.simulation.state import SimulationState


class Scheduler:
    """Builds conflict-free plans and replays them as movements."""

    def __init__(self, network: Network) -> None:
        """Create the planner for the given network."""
        self.network = network
        self.planner = TimeExpandedPlanner(network)
        self._events: dict[int, list[tuple[int, Leg, str]]] = {}

    def create_drones(self) -> list[Drone]:
        """Plan a route for every drone and return the drones."""
        drones: list[Drone] = []
        start = self.network.start
        for index in range(self.network.nb_drones):
            drone_id = index + 1
            legs = self.planner.plan_next()
            if legs is None:
                raise RuntimeError(
                    f"No route found for drone D{drone_id}"
                )
            self.planner.commit(legs)
            self._register(drone_id, legs)
            path = [start] + [leg.destination for leg in legs]
            drones.append(
                Drone(id=drone_id, curr_location=start, path=path)
            )
        return drones

    def _register(self, drone_id: int, legs: list[Leg]) -> None:
        """Index a drone's legs by the turn in which they happen."""
        for leg in legs:
            if leg.duration == 1:
                self._add(leg.depart, drone_id, leg, "hop")
            else:
                self._add(leg.depart, drone_id, leg, "start")
                self._add(leg.depart + 1, drone_id, leg, "land")

    def _add(self, turn: int, drone_id: int, leg: Leg, kind: str) -> None:
        """Store one event for a turn."""
        self._events.setdefault(turn, []).append((drone_id, leg, kind))

    def simulate_turn(self, state: SimulationState) -> list[Movement]:
        """Apply the planned events of the next turn."""
        turn = state.turn + 1
        by_id = {drone.id: drone for drone in state.drones}
        moves: list[Movement] = []
        for drone_id, leg, kind in sorted(
            self._events.get(turn, []), key=lambda e: e[0]
        ):
            drone = by_id[drone_id]
            moves.append(
                Movement(
                    drone_id=drone_id,
                    current=leg.origin,
                    destination=leg.destination,
                )
            )
            if kind == "start":
                drone.remaining_turns = 1
                drone.active_connection = frozenset(
                    (leg.origin.name, leg.destination.name)
                )
            else:
                drone.curr_location = leg.destination
                drone.remaining_turns = 0
                drone.active_connection = None
        return moves
