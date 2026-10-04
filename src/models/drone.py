"""Drone model."""
from dataclasses import dataclass

from .zone import Zone


@dataclass
class Drone:
    """A drone following its planned path."""

    id: int
    curr_location: Zone
    path: list[Zone]
    remaining_turns: int = 0
    active_connection: frozenset[str] | None = None
