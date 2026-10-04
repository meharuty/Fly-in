from dataclasses import dataclass
from enum import Enum


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass(eq=True, unsafe_hash=True)
class Zone():
    name: str
    x: int
    y: int
    zone_type: ZoneType
    color: str
    max_drones: int = 1
