from src.simulation.state import SimulationState
from src.algorithms.scheduler import Scheduler
from src.simulation.movement import Movement
from src.models.zone import Zone


class Simulation:
    def __init__(
        self,
        scheduler: Scheduler,
        state: SimulationState,
    ):
        self.scheduler = scheduler
        self.state = state
        self.history: list[list[Movement]] = []
        self.position_history: list[dict[int, Zone]] = []

    def is_finished(self) -> bool:
        return all(
            drone.curr_location == drone.path[-1]
            for drone in self.state.drones
        )

    def run(self, max_turns: int = 1000):
        while not self.is_finished():
            if self.state.turn >= max_turns:
                raise RuntimeError(
                    "Simulation exceeded maximum number of turns"
                )

            moves = self.scheduler.simulate_turn(
                self.state
            )

            self.history.append(moves)

            # Save drone positions after this turn.
            positions = {
                drone.id: drone.curr_location
                for drone in self.state.drones
            }

            self.position_history.append(positions)

            self.state.turn += 1

            if not moves:
                raise RuntimeError(
                    "Simulation is stuck: no drone can move"
                )

        return self.history
