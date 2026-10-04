from src.models.network import Network
from src.models.zone import Zone
from collections import deque
from src.models.zone import ZoneType


class Graph:
    def __init__(self, network: Network):
        self.zones: dict[str, Zone] = {
            zone.name: zone
            for zone in network.zones
        }
        self.adjacency: dict[str, list[Zone]] = {}

        for zone in network.zones:
            self.adjacency[zone.name] = []

        for connection in network.connections:
            zone_a = connection.zone_a
            zone_b = connection.zone_b
            self.adjacency[zone_a.name].append(zone_b)
            self.adjacency[zone_b.name].append(zone_a)

    def get_neighbors(self, zone: Zone) -> list[Zone]:
        return self.adjacency[zone.name]

    def get_zone(self, name: str) -> Zone:
        return self.zones[name]

    def has_path(self, start: Zone, end: Zone) -> bool:
        queue = deque([start.name])
        visited = {start.name}

        while queue:
            current_name = queue.popleft()
            if current_name == end.name:
                return True

            current_zone = self.get_zone(current_name)
            for neighbor in self.get_neighbors(current_zone):
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue
                if neighbor.name not in visited:
                    visited.add(neighbor.name)
                    queue.append(neighbor.name)
        return False

    def bfs(self, start: Zone, end: Zone) -> list[Zone]:
        queue = deque([start.name])
        visited = {start.name}
        parent: dict[str, str | None] = {start.name: None}

        while queue:
            current_name = queue.popleft()
            if current_name == end.name:
                path: list[Zone] = []
                node_name: str | None = current_name

                while node_name is not None:
                    path.append(self.get_zone(node_name))
                    node_name = parent[node_name]
                path.reverse()
                return path

            current_zone = self.get_zone(current_name)
            for neighbor in self.get_neighbors(current_zone):
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue
                if neighbor.name not in visited:
                    visited.add(neighbor.name)
                    parent[neighbor.name] = current_name
                    queue.append(neighbor.name)
        return []
