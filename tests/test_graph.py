import pytest
from src.algorithms.graph import Graph
from src.models.network import Network
from src.models.connection import Connection
from src.models.zone import Zone, ZoneType
from src.algorithms.pathfinder import Pathfinder


@pytest.fixture
def zones():
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    roof1 = Zone("roof1", 3, 4, ZoneType.NORMAL, "blue")
    roof2 = Zone("roof2", 6, 2, ZoneType.NORMAL, "blue")
    goal = Zone("goal", 10, 10, ZoneType.NORMAL, "yellow")

    return hub, roof1, roof2, goal


@pytest.fixture
def network(zones):
    hub, roof1, roof2, goal = zones

    connections = [
        Connection(hub, roof1),
        Connection(roof1, roof2),
        Connection(roof2, goal),
    ]

    return Network(
        nb_drones=3,
        zones=list(zones),
        connections=connections,
        start=hub,
        end=goal,
    )


@pytest.fixture
def graph(network):
    return Graph(network)


def test_get_neighbors(graph, zones):
    hub, roof1, _, _ = zones

    neighbors = graph.get_neighbors(hub)

    assert roof1 in neighbors
    assert len(neighbors) == 1


def test_connection_is_bidirectional(graph, zones):
    hub, roof1, _, _ = zones

    assert roof1 in graph.get_neighbors(hub)
    assert hub in graph.get_neighbors(roof1)


def test_get_zone(graph, zones):
    hub, _, _, _ = zones

    assert graph.get_zone("hub") is hub


def test_reachable_path(graph, zones):
    hub, _, _, goal = zones

    assert graph.has_path(hub, goal) is True


def test_unreachable_path(graph, zones):
    hub, _, _, _ = zones

    isolated = Zone(
        "isolated",
        20,
        20,
        ZoneType.NORMAL,
        "white",
    )

    # The isolated zone is not connected to the graph.
    graph.zones[isolated.name] = isolated
    graph.adjacency[isolated.name] = []

    assert graph.has_path(hub, isolated) is False


def test_blocked_zone_is_not_reachable(graph, zones):
    hub, roof1, _, goal = zones

    roof1.zone_type = ZoneType.BLOCKED

    assert graph.has_path(hub, goal) is False


def test_cycle_does_not_cause_infinite_loop():
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    roof1 = Zone("roof1", 1, 1, ZoneType.NORMAL, "blue")
    roof2 = Zone("roof2", 2, 2, ZoneType.NORMAL, "blue")

    connections = [
        Connection(hub, roof1),
        Connection(roof1, roof2),
        Connection(roof2, hub),
    ]

    network = Network(
        nb_drones=1,
        zones=[hub, roof1, roof2],
        connections=connections,
        start=hub,
        end=roof2,
    )

    graph = Graph(network)

    assert graph.has_path(hub, roof2) is True


def test_dijkstra(graph, zones):
    hub, _, _, goal = zones

    pathfinder = Pathfinder(graph)

    path, cost = pathfinder.dijkstra(hub, goal)

    assert path[0] == hub
    assert path[-1] == goal
    assert cost == 3
