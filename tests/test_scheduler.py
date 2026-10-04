import pytest

from src.models.zone import Zone, ZoneType
from src.models.connection import Connection
from src.models.drone import Drone
from src.algorithms.scheduler import Scheduler
from src.simulation.state import SimulationState


@pytest.fixture
def zones():
    start = Zone(
        "start",
        0,
        0,
        ZoneType.NORMAL,
        "green",
        max_drones=10,
    )

    a = Zone(
        "A",
        1,
        0,
        ZoneType.NORMAL,
        "blue",
        max_drones=2,
    )

    b = Zone(
        "B",
        2,
        0,
        ZoneType.NORMAL,
        "red",
        max_drones=2,
    )

    goal = Zone(
        "goal",
        3,
        0,
        ZoneType.NORMAL,
        "yellow",
        max_drones=10,
    )

    return start, a, b, goal


@pytest.fixture
def connections(zones):
    start, a, b, goal = zones

    return [
        Connection(start, a, max_link_capacity=10),
        Connection(a, b, max_link_capacity=10),
        Connection(b, goal, max_link_capacity=10),
    ]


# ============================================================
# ZONE CAPACITY
# ============================================================

def test_zone_capacity_allows_two_drones(zones, connections):
    start, a, b, goal = zones

    paths = [
        [start, a, b, goal],
    ]

    scheduler = Scheduler(
        paths=paths,
        nb_drones=2,
        connections=connections,
    )

    drones = scheduler.create_drones()
    state = SimulationState(drones)

    moves = scheduler.simulate_turn(state)

    assert len(moves) == 2
    assert drones[0].curr_location == a
    assert drones[1].curr_location == a


def test_zone_capacity_blocks_third_drone(zones, connections):
    start, a, b, goal = zones

    paths = [
        [start, a, b, goal],
    ]

    scheduler = Scheduler(
        paths=paths,
        nb_drones=3,
        connections=connections,
    )

    drones = scheduler.create_drones()
    state = SimulationState(drones)

    moves = scheduler.simulate_turn(state)

    assert len(moves) == 2
    assert drones[0].curr_location == a
    assert drones[1].curr_location == a
    assert drones[2].curr_location == start


def test_drone_can_enter_when_another_leaves():
    start = Zone(
        "start",
        0,
        0,
        ZoneType.NORMAL,
        "green",
        max_drones=10,
    )

    a = Zone(
        "A",
        1,
        0,
        ZoneType.NORMAL,
        "blue",
        max_drones=1,
    )

    b = Zone(
        "B",
        2,
        0,
        ZoneType.NORMAL,
        "red",
        max_drones=2,
    )

    goal = Zone(
        "goal",
        3,
        0,
        ZoneType.NORMAL,
        "yellow",
        max_drones=10,
    )

    connections = [
        Connection(start, a, max_link_capacity=10),
        Connection(a, b, max_link_capacity=10),
        Connection(b, goal, max_link_capacity=10),
    ]

    d1 = Drone(
        id=1,
        curr_location=a,
        path=[a, b, goal],
    )

    d2 = Drone(
        id=2,
        curr_location=start,
        path=[start, a, b, goal],
    )

    state = SimulationState([d1, d2])

    scheduler = Scheduler(
        paths=[[start, a, b, goal]],
        nb_drones=2,
        connections=connections,
    )

    moves = scheduler.simulate_turn(state)

    assert len(moves) == 2
    assert d1.curr_location == b
    assert d2.curr_location == a


# ============================================================
# BASIC MOVEMENT
# ============================================================

def test_drone_at_goal_does_not_move(zones, connections):
    start, a, b, goal = zones

    drone = Drone(
        id=1,
        curr_location=goal,
        path=[start, a, b, goal],
    )

    state = SimulationState([drone])

    scheduler = Scheduler(
        paths=[[start, a, b, goal]],
        nb_drones=1,
        connections=connections,
    )

    moves = scheduler.simulate_turn(state)

    assert moves == []
    assert drone.curr_location == goal


def test_drone_moves_one_zone_per_turn(zones, connections):
    start, a, b, goal = zones

    drone = Drone(
        id=1,
        curr_location=start,
        path=[start, a, b, goal],
    )

    state = SimulationState([drone])

    scheduler = Scheduler(
        paths=[[start, a, b, goal]],
        nb_drones=1,
        connections=connections,
    )

    # Turn 1
    moves = scheduler.simulate_turn(state)

    assert drone.curr_location == a
    assert len(moves) == 1

    # Turn 2
    moves = scheduler.simulate_turn(state)

    assert drone.curr_location == b
    assert len(moves) == 1

    # Turn 3
    moves = scheduler.simulate_turn(state)

    assert drone.curr_location == goal
    assert len(moves) == 1

    # Turn 4
    moves = scheduler.simulate_turn(state)

    assert drone.curr_location == goal
    assert moves == []


# ============================================================
# CONNECTION CAPACITY
# ============================================================

def test_connection_capacity_allows_two_drones(zones):
    start, a, b, goal = zones

    connections = [
        Connection(start, a, max_link_capacity=10),
        Connection(a, b, max_link_capacity=2),
        Connection(b, goal, max_link_capacity=10),
    ]

    paths = [
        [start, a, b, goal],
    ]

    scheduler = Scheduler(
        paths=paths,
        nb_drones=2,
        connections=connections,
    )

    drones = scheduler.create_drones()

    # Put both drones at A
    drones[0].curr_location = a
    drones[1].curr_location = a

    state = SimulationState(drones)

    moves = scheduler.simulate_turn(state)

    assert len(moves) == 2
    assert drones[0].curr_location == b
    assert drones[1].curr_location == b


def test_connection_capacity_blocks_third_drone(zones):
    start, a, b, goal = zones

    connections = [
        Connection(start, a, max_link_capacity=10),
        Connection(a, b, max_link_capacity=2),
        Connection(b, goal, max_link_capacity=10),
    ]

    paths = [
        [start, a, b, goal],
    ]

    scheduler = Scheduler(
        paths=paths,
        nb_drones=3,
        connections=connections,
    )

    drones = scheduler.create_drones()

    # Put all three drones at A
    for drone in drones:
        drone.curr_location = a

    state = SimulationState(drones)

    moves = scheduler.simulate_turn(state)

    assert len(moves) == 2

    assert drones[0].curr_location == b
    assert drones[1].curr_location == b
    assert drones[2].curr_location == a


# ============================================================
# RESTRICTED ZONE
# ============================================================

def test_restricted_zone_takes_two_turns():
    start = Zone(
        "start",
        0,
        0,
        ZoneType.NORMAL,
        "green",
        max_drones=10,
    )

    restricted = Zone(
        "R",
        1,
        0,
        ZoneType.RESTRICTED,
        "red",
        max_drones=1,
    )

    goal = Zone(
        "goal",
        2,
        0,
        ZoneType.NORMAL,
        "yellow",
        max_drones=10,
    )

    connections = [
        Connection(start, restricted, max_link_capacity=1),
        Connection(restricted, goal, max_link_capacity=1),
    ]

    drone = Drone(
        id=1,
        curr_location=start,
        path=[start, restricted, goal],
    )

    state = SimulationState([drone])

    scheduler = Scheduler(
        paths=[[start, restricted, goal]],
        nb_drones=1,
        connections=connections,
    )

    # Turn 1: start restricted movement
    moves = scheduler.simulate_turn(state)

    assert len(moves) == 1
    assert drone.curr_location == start
    assert drone.remaining_turns == 1

    # Turn 2: finish restricted movement
    moves = scheduler.simulate_turn(state)

    assert len(moves) == 1
    assert drone.curr_location == restricted
    assert drone.remaining_turns == 0


def test_restricted_connection_remains_occupied():
    start = Zone(
        "start",
        0,
        0,
        ZoneType.NORMAL,
        "green",
        max_drones=10,
    )

    restricted = Zone(
        "R",
        1,
        0,
        ZoneType.RESTRICTED,
        "red",
        max_drones=10,
    )

    goal = Zone(
        "goal",
        2,
        0,
        ZoneType.NORMAL,
        "yellow",
        max_drones=10,
    )

    connections = [
        Connection(start, restricted, max_link_capacity=1),
        Connection(restricted, goal, max_link_capacity=10),
    ]

    d1 = Drone(
        id=1,
        curr_location=start,
        path=[start, restricted, goal],
    )

    d2 = Drone(
        id=2,
        curr_location=start,
        path=[start, restricted, goal],
    )

    state = SimulationState([d1, d2])

    scheduler = Scheduler(
        paths=[[start, restricted, goal]],
        nb_drones=2,
        connections=connections,
    )

    # Turn 1:
    # D1 starts crossing start -> R.
    moves = scheduler.simulate_turn(state)

    assert len(moves) == 1
    assert d1.remaining_turns == 1
    assert d2.curr_location == start

    # Turn 2:
    # D1 finishes crossing.
    # D2 cannot use the connection yet.
    moves = scheduler.simulate_turn(state)

    assert d1.curr_location == restricted
    assert d2.curr_location == start


# ============================================================
# WAITING
# ============================================================

def test_drone_waits_when_connection_is_full():
    start = Zone(
        "start",
        0,
        0,
        ZoneType.NORMAL,
        "green",
        max_drones=10,
    )

    a = Zone(
        "A",
        1,
        0,
        ZoneType.NORMAL,
        "blue",
        max_drones=10,
    )

    goal = Zone(
        "goal",
        2,
        0,
        ZoneType.NORMAL,
        "yellow",
        max_drones=10,
    )

    connections = [
        Connection(start, a, max_link_capacity=1),
        Connection(a, goal, max_link_capacity=10),
    ]

    d1 = Drone(
        id=1,
        curr_location=start,
        path=[start, a, goal],
    )

    d2 = Drone(
        id=2,
        curr_location=start,
        path=[start, a, goal],
    )

    state = SimulationState([d1, d2])

    scheduler = Scheduler(
        paths=[[start, a, goal]],
        nb_drones=2,
        connections=connections,
    )

    # Turn 1
    moves = scheduler.simulate_turn(state)

    assert len(moves) == 1
    assert d1.curr_location == a
    assert d2.curr_location == start

    # Turn 2
    # D1 and D2 use different connections,
    # so both are allowed to move.
    moves = scheduler.simulate_turn(state)

    assert len(moves) == 2
    assert d1.curr_location == goal
    assert d2.curr_location == a
