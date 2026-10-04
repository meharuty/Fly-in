from src.models.zone import ZoneType, Zone
from src.algorithms.graph import Graph
import heapq


class Pathfinder:
    def __init__(self, graph: Graph):
        self.graph = graph

    def get_zone_cost(self, zone: Zone) -> int:
        if zone.zone_type == ZoneType.NORMAL:
            return 1

        if zone.zone_type == ZoneType.PRIORITY:
            return 1

        if zone.zone_type == ZoneType.RESTRICTED:
            return 2

        return 0

    def dijkstra(
        self,
        start: Zone,
        end: Zone,
    ) -> tuple[list[Zone], int | float]:
        distances = {start.name: 0}
        parent: dict[str, str | None] = {start.name: None}
        queue = [(0, start.name)]

        while queue:
            current_distance, current_zone_name = heapq.heappop(queue)
            if current_zone_name == end.name:
                break
            current = self.graph.get_zone(current_zone_name)
            for neighbor in self.graph.get_neighbors(current):
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue

                new_distance = current_distance + self.get_zone_cost(neighbor)

                if (
                    neighbor.name not in distances
                    or new_distance < distances[neighbor.name]
                ):
                    distances[neighbor.name] = new_distance
                    parent[neighbor.name] = current_zone_name
                    heapq.heappush(queue, (new_distance, neighbor.name))

        if end.name not in distances:
            return [], float('inf')

        path = []
        current_name: str | None = end.name
        while current_name is not None:
            path.append(self.graph.get_zone(current_name))
            current_name = parent[current_name]
        path.reverse()
        return path, distances[end.name]

    def find_paths(
        self,
        start: Zone,
        end: Zone,
        max_paths: int = 3,
    ) -> list[list[Zone]]:
        if max_paths <= 0:
            return []

        all_paths = []

        def dfs(
            current: Zone,
            path: list[Zone],
            visited: set[str],
        ) -> None:
            if current.name == end.name:
                all_paths.append(path.copy())
                return

            for neighbor in self.graph.get_neighbors(current):
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue

                if neighbor.name in visited:
                    continue

                visited.add(neighbor.name)
                path.append(neighbor)

                dfs(neighbor, path, visited)

                path.pop()
                visited.remove(neighbor.name)

        dfs(start, [start], {start.name})

        def path_cost(path: list[Zone]) -> int:
            return sum(
                self.get_zone_cost(zone)
                for zone in path[1:]
            )

        def priority_count(path: list[Zone]) -> int:
            return sum(
                1
                for zone in path
                if zone.zone_type == ZoneType.PRIORITY
            )

        all_paths.sort(
            key=lambda path: (
                path_cost(path),
                -priority_count(path),
            )
        )

        return all_paths[:max_paths]
