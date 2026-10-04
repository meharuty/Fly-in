"""Colored terminal visualization for the Fly-in simulation."""
import os
import sys
import time
import zlib
from collections import Counter
from dataclasses import dataclass

from src.models.network import Network
from src.models.zone import Zone, ZoneType
from src.simulation.movement import Movement
from src.simulation.simulation import Simulation

RESET = "\033[0m"

NAMED_COLORS: dict[str, str] = {
    "black": "90",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "purple": "35",
    "cyan": "36",
    "white": "37",
    "gray": "90",
    "grey": "90",
    "orange": "38;5;208",
    "brown": "38;5;130",
    "pink": "38;5;213",
    "gold": "38;5;220",
    "maroon": "38;5;88",
    "violet": "38;5;99",
}

TYPE_MARKERS: dict[ZoneType, str] = {
    ZoneType.NORMAL: " ",
    ZoneType.PRIORITY: "*",
    ZoneType.RESTRICTED: "!",
    ZoneType.BLOCKED: "#",
}


class Painter:
    """Wraps text in ANSI escape codes (or leaves it plain)."""

    def __init__(self, enabled: bool | None = None) -> None:
        """Enable colors if stdout is a TTY, unless NO_COLOR is set."""
        if enabled is None:
            enabled = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        self.enabled = enabled

    def code_for(self, color: str) -> str:
        """Map any single-word color name to an ANSI code."""
        key = color.strip().lower()
        if key in ("", "none"):
            return ""
        if key in NAMED_COLORS:
            return NAMED_COLORS[key]
        return f"38;5;{16 + zlib.crc32(key.encode()) % 216}"

    def paint(self, text: str, code: str) -> str:
        """Return text wrapped in the given ANSI code."""
        if not self.enabled or not code:
            return text
        return f"\033[{code}m{text}{RESET}"

    def zone(self, text: str, zone: Zone) -> str:
        """Paint text using a zone's own color."""
        return self.paint(text, self.code_for(zone.color))


@dataclass
class Frame:
    """State of the simulation right after one turn."""

    turn: int
    movements: list[Movement]
    positions: dict[int, Zone]
    in_transit: dict[int, Movement]


class TerminalVisualizer:
    """Renders the map, each turn and a final summary in the terminal."""

    def __init__(
        self,
        network: Network,
        simulation: Simulation,
        painter: Painter | None = None,
    ) -> None:
        """Build replay frames from the simulation history."""
        self.network = network
        self.simulation = simulation
        self.painter = painter or Painter()
        self.frames = self._build_frames()

    # ---------- frame construction ----------

    def _build_frames(self) -> list[Frame]:
        """Replay history; a move not ending 
        at its destination is in flight."""
        frames: list[Frame] = []
        history = self.simulation.history
        for index, moves in enumerate(history):
            after = self.simulation.position_history[index]
            transit = {
                m.drone_id: m
                for m in moves
                if after[m.drone_id] != m.destination
            }
            ordered = sorted(moves, key=lambda m: m.drone_id)
            frames.append(Frame(index + 1, ordered, after, transit))
        return frames

    # ---------- small helpers ----------

    def _capacity(self, zone: Zone) -> str:
        if zone == self.network.start or zone == self.network.end:
            return "inf"
        return str(zone.max_drones)

    def _tag(self, zone: Zone) -> str:
        if zone == self.network.start:
            return "START"
        if zone == self.network.end:
            return "END"
        return zone.zone_type.value

    def _format_move(self, move: Movement, frame: Frame) -> str:
        """Format a move as D<ID>-<zone> or D<ID>-<connection>."""
        if move.drone_id in frame.in_transit:
            name = f"{move.current.name}-{move.destination.name}"
            text = f"D{move.drone_id}-{name}"
            return self.painter.paint(text, "33")
        text = f"D{move.drone_id}-{move.destination.name}"
        return self.painter.zone(text, move.destination)

    def plain_lines(self) -> list[str]:
        """Return the uncolored official output, one line per turn."""
        lines = []
        for frame in self.frames:
            tokens = []
            for move in frame.movements:
                if move.drone_id in frame.in_transit:
                    dest = f"{move.current.name}-{move.destination.name}"
                else:
                    dest = move.destination.name
                tokens.append(f"D{move.drone_id}-{dest}")
            lines.append(" ".join(tokens))
        return lines

    # ---------- legend ----------

    def show_legend(self) -> None:
        """Print every zone and connection with its properties."""
        p = self.painter
        print(p.paint("=== MAP ===", "1"))
        print(
            "Markers: > start  $ end  * priority  ! restricted(2 turns)"
            "  # blocked"
        )
        for zone in self.network.zones:
            name = p.zone(f"{zone.name:<14}", zone)
            print(
                f"  {name} ({zone.x:>3},{zone.y:>3})  "
                f"{self._tag(zone):<10} cap={self._capacity(zone)}"
            )
        print(p.paint("Connections:", "1"))
        for conn in self.network.connections:
            a = p.zone(conn.zone_a.name, conn.zone_a)
            b = p.zone(conn.zone_b.name, conn.zone_b)
            print(f"  {a} <-> {b}  cap={conn.max_link_capacity}")
        print()

    # ---------- grid ----------

    def _label(self, zone: Zone, count: int) -> str:
        marker = TYPE_MARKERS[zone.zone_type]
        if zone == self.network.start:
            marker = ">"
        elif zone == self.network.end:
            marker = "$"
        suffix = f"[{count}]" if count else ""
        return f"{marker}{zone.name}{suffix}"

    def render_grid(self, frame: Frame | None = None) -> str:
        """Draw zones on a compressed coordinate grid with drone counts."""
        zones = self.network.zones
        xs = sorted({z.x for z in zones})
        ys = sorted({z.y for z in zones}, reverse=True)
        counts: Counter[str] = Counter()
        if frame is not None:
            for drone_id, zone in frame.positions.items():
                if drone_id not in frame.in_transit:
                    counts[zone.name] += 1
        else:
            counts[self.network.start.name] = self.simulation_drones()
        width = max(len(z.name) for z in zones) + 7
        cells: dict[tuple[int, int], Zone] = {
            (xs.index(z.x), ys.index(z.y)): z for z in zones
        }
        rows = []
        for row in range(len(ys)):
            parts = []
            for col in range(len(xs)):
                zone = cells.get((col, row))
                if zone is None:
                    parts.append(" " * width)
                    continue
                count = counts[zone.name]
                text = self._label(zone, count).center(width)
                code = self.painter.code_for(zone.color)
                if count:
                    code = f"1;{code}" if code else "1"
                parts.append(self.painter.paint(text, code))
            rows.append(" ".join(parts).rstrip())
        return "\n\n".join(rows)

    def simulation_drones(self) -> int:
        """Number of drones in the simulation."""
        return len(self.simulation.state.drones)

    # ---------- turn rendering ----------

    def render_turn(self, frame: Frame) -> None:
        """Print moves, grid, zone occupancy, connections and progress."""
        p = self.painter
        total = self.simulation_drones()
        end = self.network.end
        delivered = sum(
            1 for z in frame.positions.values() if z == end
        )
        print(p.paint(f"--- Turn {frame.turn} ---", "1"))
        print("  " + " ".join(
            self._format_move(m, frame) for m in frame.movements
        ))
        print()
        print(self.render_grid(frame))
        print()

        by_zone: dict[str, list[int]] = {}
        for drone_id, zone in frame.positions.items():
            if drone_id in frame.in_transit or zone == end:
                continue
            by_zone.setdefault(zone.name, []).append(drone_id)
        for zone in self.network.zones:
            ids = sorted(by_zone.get(zone.name, []))
            if not ids:
                continue
            cap = self._capacity(zone)
            label = p.zone(f"{zone.name:<14}", zone)
            drones = " ".join(f"D{i}" for i in ids)
            print(f"  {label} {len(ids)}/{cap:<3} {drones}")

        for drone_id, move in sorted(frame.in_transit.items()):
            name = f"{move.current.name}-{move.destination.name}"
            print(
                "  "
                + p.paint(f"{name:<14}", "33")
                + f" in flight: D{drone_id}"
            )

        bar_len = 30
        filled = bar_len * delivered // total if total else bar_len
        bar = "#" * filled + "." * (bar_len - filled)
        progress = p.paint(f"[{bar}] {delivered}/{total}", "32")
        print(f"  Delivered {progress}\n")

    # ---------- public entry points ----------

    def play(self, delay: float = 0.6, step: bool = False) -> None:
        """Replay every turn; wait for Enter if step, else sleep delay."""
        print(self.painter.paint("=== START ===", "1"))
        print(self.render_grid(None), "\n")
        for frame in self.frames:
            self.render_turn(frame)
            if step:
                input("  [Enter] next turn ")
            elif delay > 0:
                time.sleep(delay)

    def show_summary(self) -> None:
        """Print the turn count and per-drone arrival turns."""
        p = self.painter
        end = self.network.end
        arrival: dict[int, int] = {}
        for frame in self.frames:
            for drone_id, zone in frame.positions.items():
                if zone == end and drone_id not in arrival:
                    arrival[drone_id] = frame.turn
        print(p.paint("=== SUMMARY ===", "1"))
        print(f"  Drones : {self.simulation_drones()}")
        print(f"  Turns  : {len(self.frames)}")
        if arrival:
            avg = sum(arrival.values()) / len(arrival)
            print(f"  Average arrival turn: {avg:.1f}")
            for drone_id, turn in sorted(arrival.items()):
                print(f"    D{drone_id:<3} arrived at turn {turn}")
