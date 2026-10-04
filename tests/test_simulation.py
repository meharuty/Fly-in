from src.models.zone import Zone, ZoneType
from src.models.connection import Connection
from src.models.drone import Drone
from src.simulation.state import SimulationState
from src.algorithms.scheduler import Scheduler
from src.simulation.simulation import Simulation


def test_simulation_one_drone():
    start = Zone(
        "start", 0, 0, ZoneType.NORMAL, "green"
    )

    a = Zone(
        "A", 1, 0, ZoneType.NORMAL, "blue"
    )

    goal = Zone(
        "goal", 2, 0, ZoneType.NORMAL, "yellow"
    )

    connections = [
        Connection(start, a),
        Connection(a, goal),
    ]

    drone = Drone(
        id=1,
        curr_location=start,
        path=[start, a, goal],
    )

    state = SimulationState([drone])

    scheduler = Scheduler(
        paths=[[start, a, goal]],
        nb_drones=1,
        connections=connections,
    )

    simulation = Simulation(scheduler, state)

    history = simulation.run()

    assert drone.curr_location == goal
    assert len(history) == 2
    assert state.turn == 2
