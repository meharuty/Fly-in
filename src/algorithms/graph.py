"""Graph of zones built from a Network."""
from collections import deque

from src.models.network import Network
from src.models.zone import Zone, ZoneType


class Graph:
    """Adjacency structure over the zones of a Network."""

    def __init__(self, network: Network) -> None:
        """Build the adjacency lists from the network connections."""
        self.zones: dict[str, Zone] = {
            zone.name: zone for zone in network.zones
        }
        self.adjacency: dict[str, list[Zone]] = {
            zone.name: [] for zone in network.zones
        }

        for connection in network.connections:
            zone_a = connection.zone_a
            zone_b = connection.zone_b
            self.adjacency[zone_a.name].append(zone_b)
            self.adjacency[zone_b.name].append(zone_a)

    def get_neighbors(self, zone: Zone) -> list[Zone]:
        """Return the zones directly connected to ``zone``."""
        return self.adjacency[zone.name]

    def get_zone(self, name: str) -> Zone:
        """Return a zone by name."""
        return self.zones[name]

    def has_path(self, start: Zone, end: Zone) -> bool:
        """Return True if end is reachable without blocked zones."""
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
