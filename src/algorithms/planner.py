"""Time-expanded planner producing conflict-free routes for each drone."""
import heapq
from dataclasses import dataclass

from src.algorithms.graph import Graph
from src.models.connection import Connection
from src.models.network import Network
from src.models.zone import Zone, ZoneType


@dataclass(frozen=True)
class Leg:
    """One hop of a drone's route.

    Attributes:
        depart: 1-based turn in which the drone leaves ``origin``.
        origin: Zone the drone leaves.
        destination: Zone the drone reaches.
        duration: Turns needed (1, or 2 for a restricted destination).
    """

    depart: int
    origin: Zone
    destination: Zone
    duration: int


class ReservationTable:
    """Records zone occupancy per time and link usage per turn."""

    def __init__(self) -> None:
        """Create an empty table."""
        self._zone_use: dict[tuple[str, int], int] = {}
        self._link_use: dict[tuple[frozenset[str], int], int] = {}
        self.last_time = 0

    def zone_load(self, name: str, time: int) -> int:
        """Drones in a zone after ``time`` turns."""
        return self._zone_use.get((name, time), 0)

    def link_load(self, key: frozenset[str], turn: int) -> int:
        """Drones starting to cross a link during ``turn``."""
        return self._link_use.get((key, turn), 0)

    def add_zone(self, name: str, first: int, stop: int) -> None:
        """Reserve a zone for times first..stop-1."""
        for time in range(first, stop):
            slot = (name, time)
            self._zone_use[slot] = self._zone_use.get(slot, 0) + 1
        self.last_time = max(self.last_time, stop)

    def add_link(self, key: frozenset[str], turn: int) -> None:
        """Reserve one unit of a link for ``turn``."""
        slot = (key, turn)
        self._link_use[slot] = self._link_use.get(slot, 0) + 1
        self.last_time = max(self.last_time, turn)


class TimeExpandedPlanner:
    """Plans drones one by one with A* over (zone, time) states.

    Each drone gets the earliest possible arrival given the capacity
    reservations of the drones planned before it. Waiting is a normal
    action, so waits and conflicts are resolved at planning time.
    """

    def __init__(self, network: Network) -> None:
        """Precompute lookups and the static distance-to-end heuristic."""
        self.network = network
        self.graph = Graph(network)
        self.table = ReservationTable()
        self.links: dict[frozenset[str], Connection] = {
            frozenset((c.zone_a.name, c.zone_b.name)): c
            for c in network.connections
        }
        self.heuristic = self._distance_to_end()

    @staticmethod
    def _cost(zone: Zone) -> int:
        """Turns needed to enter a zone."""
        return 2 if zone.zone_type == ZoneType.RESTRICTED else 1

    def _unlimited(self, zone: Zone) -> bool:
        """Start and end zones have no capacity limit."""
        return zone == self.network.start or zone == self.network.end

    def _distance_to_end(self) -> dict[str, int]:
        """Capacity-free shortest time from each zone to the end."""
        end = self.network.end
        dist: dict[str, int] = {end.name: 0}
        queue: list[tuple[int, str]] = [(0, end.name)]
        while queue:
            d, name = heapq.heappop(queue)
            if d > dist.get(name, d):
                continue
            node = self.graph.get_zone(name)
            if node.zone_type == ZoneType.BLOCKED:
                continue
            step = self._cost(node)
            for nb in self.graph.get_neighbors(node):
                if nb.zone_type == ZoneType.BLOCKED:
                    continue
                if d + step < dist.get(nb.name, 1 << 30):
                    dist[nb.name] = d + step
                    heapq.heappush(queue, (d + step, nb.name))
        return dist

    def plan_next(self) -> list[Leg] | None:
        """Find the earliest-arrival route for one more drone."""
        start, end = self.network.start, self.network.end
        if start.name not in self.heuristic:
            return None
        horizon = self.table.last_time + 2 * len(self.network.zones) + 5
        State = tuple[str, int]
        parent: dict[State, tuple[State, Leg | None]] = {}
        prio: dict[State, int] = {(start.name, 0): 0}
        closed: set[State] = set()
        seq = 0
        h0 = self.heuristic[start.name]
        heap: list[tuple[int, int, int, int, str]] = [
            (h0, 0, seq, 0, start.name)
        ]
        while heap:
            _, _, _, time, name = heapq.heappop(heap)
            state = (name, time)
            if state in closed:
                continue
            closed.add(state)
            if name == end.name:
                return self._rebuild(state, parent)
            zone = self.graph.get_zone(name)
            score = prio[state]
            candidates: list[tuple[Zone, int, Leg | None]] = []
            if time + 1 <= horizon and (
                self._unlimited(zone)
                or self.table.zone_load(name, time + 1) < zone.max_drones
            ):
                candidates.append((zone, time + 1, None))
            for nb in self.graph.get_neighbors(zone):
                if nb.zone_type == ZoneType.BLOCKED:
                    continue
                if nb.name not in self.heuristic:
                    continue
                key = frozenset((name, nb.name))
                link = self.links[key]
                turn = time + 1
                if self.table.link_load(key, turn) >= link.max_link_capacity:
                    continue
                arrive = time + self._cost(nb)
                if arrive > horizon:
                    continue
                if (
                    not self._unlimited(nb)
                    and self.table.zone_load(nb.name, arrive) >= nb.max_drones
                ):
                    continue
                hop = Leg(turn, zone, nb, arrive - time)
                candidates.append((nb, arrive, hop))
            for nb, arrive, leg in candidates:
                nxt = (nb.name, arrive)
                if nxt in closed:
                    continue
                bonus = 1 if nb.zone_type == ZoneType.PRIORITY else 0
                new_score = score + (bonus if leg is not None else 0)
                if nxt not in prio or new_score > prio[nxt]:
                    prio[nxt] = new_score
                    parent[nxt] = (state, leg)
                seq += 1
                f = arrive + self.heuristic[nb.name]
                heapq.heappush(
                    heap, (f, -prio[nxt], seq, arrive, nb.name)
                )
        return None

    @staticmethod
    def _rebuild(
        state: tuple[str, int],
        parent: dict[tuple[str, int], tuple[tuple[str, int], Leg | None]],
    ) -> list[Leg]:
        """Walk parents back to the start and collect the legs."""
        legs: list[Leg] = []
        while state in parent:
            state, leg = parent[state]
            if leg is not None:
                legs.append(leg)
        legs.reverse()
        return legs

    def commit(self, legs: list[Leg]) -> None:
        """Reserve links and zones used by a planned route."""
        for index, leg in enumerate(legs):
            key = frozenset((leg.origin.name, leg.destination.name))
            self.table.add_link(key, leg.depart)
            arrive = leg.depart - 1 + leg.duration
            if self._unlimited(leg.destination):
                self.table.last_time = max(self.table.last_time, arrive)
                continue
            leave = legs[index + 1].depart
            self.table.add_zone(leg.destination.name, arrive, leave)
