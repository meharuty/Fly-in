from dataclasses import dataclass

from .zone import Zone


@dataclass
class Connection:
    zone_a: Zone
    zone_b: Zone
    max_link_capacity: int = 1

    @property
    def name(self) -> str:
        return f"{self.zone_a.name}-{self.zone_b.name}"
