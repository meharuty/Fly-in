from dataclasses import dataclass
from .zone import Zone


@dataclass
class Drone():
    id: int
    curr_location: Zone
    path: list[Zone]
    state: str = ""
    remaining_turns: int = 0
    active_connection: frozenset[str] | None = None
