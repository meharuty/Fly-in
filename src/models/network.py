from dataclasses import dataclass
from .zone import Zone
from .connection import Connection


@dataclass
class Network():
    nb_drones: int
    zones: list[Zone]
    connections: list[Connection]
    start: Zone
    end: Zone
