"""Turn-by-turn simulation driven by a Scheduler."""
from src.algorithms.scheduler import Scheduler
from src.models.zone import Zone
from src.simulation.movement import Movement
from src.simulation.state import SimulationState


class Simulation:
    """Runs the scheduler turn by turn and records the history."""

    def __init__(
        self,
        scheduler: Scheduler,
        state: SimulationState,
    ) -> None:
        """Store the scheduler and the initial state."""
        self.scheduler = scheduler
        self.state = state
        self.history: list[list[Movement]] = []
        self.position_history: list[dict[int, Zone]] = []

    def is_finished(self) -> bool:
        """Return True when every drone has reached its final zone."""
        return all(
            drone.curr_location == drone.path[-1]
            for drone in self.state.drones
        )

    def run(self, max_turns: int = 100000) -> list[list[Movement]]:
        """Simulate until all drones are delivered.

        Raises:
            RuntimeError: if max_turns is exceeded.
        """
        while not self.is_finished():
            if self.state.turn >= max_turns:
                raise RuntimeError(
                    "Simulation exceeded maximum number of turns"
                )

            moves = self.scheduler.simulate_turn(self.state)
            self.history.append(moves)

            self.position_history.append(
                {
                    drone.id: drone.curr_location
                    for drone in self.state.drones
                }
            )
            self.state.turn += 1

        return self.history
