import pytest

from src.algorithms.graph import Graph
from src.algorithms.pathfinder import Pathfinder
from src.models.connection import Connection
from src.models.network import Network
from src.models.zone import Zone, ZoneType


def make_network(zones, connections, start, end):
    return Network(
        nb_drones=1,
        zones=zones,
        connections=connections,
        start=start,
        end=end,
    )


# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------


@pytest.fixture
def simple_graph():
    """Graph with only one path:

    hub -> roof1 -> end
    """
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    roof1 = Zone("roof1", 3, 4, ZoneType.NORMAL, "blue")
    end = Zone("end", 6, 8, ZoneType.NORMAL, "red")

    connections = [
        Connection(hub, roof1),
        Connection(roof1, end),
    ]

    network = make_network(
        [hub, roof1, end],
        connections,
        hub,
        end,
    )

    return Graph(network), hub, roof1, end


@pytest.fixture
def two_path_graph():
    """Graph with two different paths:

             roof1
            /     \
        hub         end
            \     /
             roof2
    """
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    roof1 = Zone("roof1", 3, 4, ZoneType.NORMAL, "blue")
    roof2 = Zone("roof2", 3, -4, ZoneType.NORMAL, "yellow")
    end = Zone("end", 6, 0, ZoneType.NORMAL, "red")

    connections = [
        Connection(hub, roof1),
        Connection(roof1, end),
        Connection(hub, roof2),
        Connection(roof2, end),
    ]

    network = make_network(
        [hub, roof1, roof2, end],
        connections,
        hub,
        end,
    )

    return Graph(network), hub, roof1, roof2, end


@pytest.fixture
def three_path_graph():
    """Graph with three different paths:

                roof1
               /     \
              /       \
        hub -- roof2 -- end
              \       /
               \     /
                roof3
    """
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    roof1 = Zone("roof1", 2, 4, ZoneType.NORMAL, "blue")
    roof2 = Zone("roof2", 3, 0, ZoneType.NORMAL, "yellow")
    roof3 = Zone("roof3", 2, -4, ZoneType.NORMAL, "purple")
    end = Zone("end", 6, 0, ZoneType.NORMAL, "red")

    connections = [
        Connection(hub, roof1),
        Connection(roof1, end),
        Connection(hub, roof2),
        Connection(roof2, end),
        Connection(hub, roof3),
        Connection(roof3, end),
    ]

    network = make_network(
        [hub, roof1, roof2, roof3, end],
        connections,
        hub,
        end,
    )

    return Graph(network), hub, roof1, roof2, roof3, end


@pytest.fixture
def disconnected_graph():
    """Graph where end is unreachable from hub.

    hub -> roof1

    end (isolated)
    """
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    roof1 = Zone("roof1", 3, 4, ZoneType.NORMAL, "blue")
    end = Zone("end", 10, 10, ZoneType.NORMAL, "red")

    connections = [
        Connection(hub, roof1),
    ]

    network = make_network(
        [hub, roof1, end],
        connections,
        hub,
        end,
    )

    return Graph(network), hub, roof1, end


# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------


def test_find_paths_one_path(simple_graph):
    graph, hub, roof1, end = simple_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(hub, end)

    assert len(paths) == 1
    assert paths[0] == [hub, roof1, end]


def test_find_paths_two_paths(two_path_graph):
    graph, hub, roof1, roof2, end = two_path_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(hub, end)

    assert len(paths) == 2

    expected_paths = [
        [hub, roof1, end],
        [hub, roof2, end],
    ]

    assert paths[0] in expected_paths
    assert paths[1] in expected_paths
    assert paths[0] != paths[1]


def test_find_paths_three_paths(three_path_graph):
    graph, hub, roof1, roof2, roof3, end = three_path_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(
        hub,
        end,
        max_paths=3,
    )

    assert len(paths) == 3

    path_tuples = [tuple(path) for path in paths]
    assert len(path_tuples) == len(set(path_tuples))


def test_find_paths_no_path(disconnected_graph):
    graph, hub, roof1, end = disconnected_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(hub, end)

    assert paths == []


def test_find_paths_max_paths(three_path_graph):
    graph, hub, roof1, roof2, roof3, end = three_path_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(
        hub,
        end,
        max_paths=2,
    )

    assert len(paths) == 2


def test_find_paths_max_paths_one(three_path_graph):
    graph, hub, roof1, roof2, roof3, end = three_path_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(
        hub,
        end,
        max_paths=1,
    )

    assert len(paths) == 1


def test_paths_start_and_end_correctly(two_path_graph):
    graph, hub, roof1, roof2, end = two_path_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(hub, end)

    for path in paths:
        assert path[0] == hub
        assert path[-1] == end


def test_find_paths_no_duplicates(three_path_graph):
    graph, hub, roof1, roof2, roof3, end = three_path_graph
    pathfinder = Pathfinder(graph)

    paths = pathfinder.find_paths(
        hub,
        end,
        max_paths=3,
    )

    path_names = [
        tuple(zone.name for zone in path)
        for path in paths
    ]

    assert len(path_names) == len(set(path_names))


@pytest.fixture
def restricted_graph():
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    restricted = Zone("restricted", 3, 0, ZoneType.RESTRICTED, "red")
    end = Zone("end", 6, 0, ZoneType.NORMAL, "blue")

    connections = [
        Connection(hub, restricted),
        Connection(restricted, end),
    ]

    network = Network(
        nb_drones=1,
        zones=[hub, restricted, end],
        connections=connections,
        start=hub,
        end=end,
    )

    return Graph(network), hub, restricted, end


def test_dijkstra_restricted_zone_cost(restricted_graph):
    graph, hub, restricted, end = restricted_graph

    pathfinder = Pathfinder(graph)

    path, cost = pathfinder.dijkstra(hub, end)

    assert [zone.name for zone in path] == [
        "hub",
        "restricted",
        "end",
    ]

    assert cost == 3


def test_dijkstra_priority_zone_cost():
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    priority = Zone("priority", 3, 0, ZoneType.PRIORITY, "yellow")
    end = Zone("end", 6, 0, ZoneType.NORMAL, "red")

    connections = [
        Connection(hub, priority),
        Connection(priority, end),
    ]

    network = Network(
        nb_drones=1,
        zones=[hub, priority, end],
        connections=connections,
        start=hub,
        end=end,
    )

    graph = Graph(network)
    pathfinder = Pathfinder(graph)

    path, cost = pathfinder.dijkstra(hub, end)

    assert [zone.name for zone in path] == [
        "hub",
        "priority",
        "end",
    ]
    assert cost == 2


def test_dijkstra_prefers_lower_cost_path():
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    restricted = Zone(
        "restricted",
        2,
        0,
        ZoneType.RESTRICTED,
        "red",
    )
    normal1 = Zone(
        "normal1",
        2,
        2,
        ZoneType.NORMAL,
        "green",
    )
    normal2 = Zone(
        "normal2",
        4,
        2,
        ZoneType.NORMAL,
        "green",
    )
    end = Zone("end", 6, 0, ZoneType.NORMAL, "blue")

    connections = [
        Connection(hub, restricted),
        Connection(restricted, end),
        Connection(hub, normal1),
        Connection(normal1, normal2),
        Connection(normal2, end),
    ]

    network = Network(
        nb_drones=1,
        zones=[hub, restricted, normal1, normal2, end],
        connections=connections,
        start=hub,
        end=end,
    )

    graph = Graph(network)
    pathfinder = Pathfinder(graph)

    path, cost = pathfinder.dijkstra(hub, end)

    assert [zone.name for zone in path] == [
        "hub",
        "normal1",
        "normal2",
        "end",
    ]
    assert cost == 3


def test_dijkstra_avoids_blocked_zone():
    hub = Zone("hub", 0, 0, ZoneType.NORMAL, "green")
    blocked = Zone("blocked", 2, 0, ZoneType.BLOCKED, "black")
    normal = Zone("normal", 2, 2, ZoneType.NORMAL, "green")
    end = Zone("end", 6, 0, ZoneType.NORMAL, "blue")

    connections = [
        Connection(hub, blocked),
        Connection(blocked, end),
        Connection(hub, normal),
        Connection(normal, end),
    ]

    network = Network(
        nb_drones=1,
        zones=[hub, blocked, normal, end],
        connections=connections,
        start=hub,
        end=end,
    )

    graph = Graph(network)
    pathfinder = Pathfinder(graph)

    path, cost = pathfinder.dijkstra(hub, end)

    assert [zone.name for zone in path] == [
        "hub",
        "normal",
        "end",
    ]
    assert cost == 2
