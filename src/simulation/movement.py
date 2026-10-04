from dataclasses import dataclass
from src.models.zone import Zone


@dataclass
class Movement():
    drone_id: int
    current: Zone
    destination: Zone
