"""Terminal and graphical visualization of a Fly-in simulation."""
import colorsys
import math
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

try:
    import tkinter as tk
except ImportError:  # tkinter is optional: only --gui needs it
    tk = None  # type: ignore[assignment]

# ======================================================================
# Replay frames (shared by both views)
# ======================================================================


@dataclass
class Frame:
    """State of the simulation right after one turn."""

    turn: int
    movements: list[Movement]
    positions: dict[int, Zone]
    in_transit: dict[int, Movement]


def build_frames(simulation: Simulation) -> list[Frame]:
    """Replay the history; a move not ending at its goal is in flight."""
    frames: list[Frame] = []
    for index, moves in enumerate(simulation.history):
        after = simulation.position_history[index]
        transit = {
            m.drone_id: m
            for m in moves
            if after[m.drone_id] != m.destination
        }
        ordered = sorted(moves, key=lambda m: m.drone_id)
        frames.append(Frame(index + 1, ordered, after, transit))
    return frames


# ======================================================================
# Terminal view
# ======================================================================


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
        self.frames = build_frames(simulation)

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
        cells: dict[tuple[int, int], Zone] = {}
        for z in zones:
            col, row = xs.index(z.x), ys.index(z.y)
            while (col, row) in cells:
                col += 1
            cells[(col, row)] = z
        n_cols = max(col for col, _ in cells) + 1
        rows = []
        for row in range(len(ys)):
            parts = []
            for col in range(n_cols):
                cell = cells.get((col, row))
                if cell is None:
                    parts.append(" " * width)
                    continue
                count = counts[cell.name]
                text = self._label(cell, count).center(width)
                code = self.painter.code_for(cell.color)
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


# ======================================================================
# Graphical view (tkinter)
# ======================================================================


Point = tuple[float, float]

ZONE_RADIUS = 24
DRONE_RADIUS = 8
TICK_MS = 33
MAX_RING = 8

BG = "#14181f"
FG = "#e6e9ef"
LINK = "#5b6575"
LINK_BUSY = "#f5a623"

HEX_COLORS: dict[str, str] = {
    "red": "#e74c3c", "green": "#2ecc71", "blue": "#3498db",
    "yellow": "#f1c40f", "orange": "#e67e22", "purple": "#9b59b6",
    "violet": "#8e44ad", "magenta": "#e84393", "cyan": "#1abc9c",
    "gray": "#95a5a6", "grey": "#95a5a6", "black": "#2c3e50",
    "white": "#ecf0f1", "brown": "#a0522d", "pink": "#ff7eb9",
    "gold": "#f5c542", "maroon": "#a93226", "none": "#8a94a6",
}


def color_to_hex(name: str) -> str:
    """Map any single-word color name to a hex color."""
    key = name.strip().lower()
    if key in HEX_COLORS:
        return HEX_COLORS[key]
    hue = (zlib.crc32(key.encode()) % 360) / 360
    r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.85)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def text_color(background: str) -> str:
    """Return black or white, whichever is readable on the background."""
    r, g, b = (int(background[i:i + 2], 16) for i in (1, 3, 5))
    return "#111111" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#ffffff"


def drone_color(drone_id: int) -> str:
    """Return a stable, well-separated color for a drone."""
    hue = (drone_id * 0.618033988) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.55, 0.95)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


class Layout:
    """Maps zone coordinates to canvas pixels."""

    def __init__(self, zones: list[Zone]) -> None:
        """Remember the zones to place."""
        self.zones = zones
        self._pos: dict[str, Point] = {}

    def fit(self, width: float, height: float, margin: float = 90) -> None:
        """Scale and center all zones inside the given canvas size."""
        xs = [z.x for z in self.zones]
        ys = [z.y for z in self.zones]
        span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
        scale = min(
            (width - 2 * margin) / max(span_x, 1),
            (height - 2 * margin) / max(span_y, 1),
            170.0,
        )
        scale = max(scale, 1.0)
        off_x = (width - span_x * scale) / 2
        off_y = (height - span_y * scale) / 2
        taken: set[tuple[int, int]] = set()
        self._pos = {}
        for zone in self.zones:
            px = off_x + (zone.x - min(xs)) * scale
            py = off_y + (max(ys) - zone.y) * scale
            while (round(px), round(py)) in taken:
                px += 2 * ZONE_RADIUS + 8
            taken.add((round(px), round(py)))
            self._pos[zone.name] = (px, py)

    def pos(self, zone: Zone) -> Point:
        """Pixel position of a zone."""
        return self._pos[zone.name]


class GraphicalVisualizer:
    """Animated tkinter view: zones, links, capacities and drones."""

    def __init__(self, network: Network, simulation: Simulation) -> None:
        """Build the window (raises RuntimeError without a display)."""
        self.network = network
        self.frames: list[Frame] = build_frames(simulation)
        self.drone_ids = sorted(d.id for d in simulation.state.drones)
        self.layout = Layout(network.zones)
        self.index = -1
        self.progress = 1.0
        self.playing = False
        if tk is None:
            raise RuntimeError(
                "tkinter is not installed (try: apt install python3-tk)"
            )
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            raise RuntimeError(f"Cannot open a window: {error}") from None
        self.root.title("Fly-in")
        self.root.configure(bg=BG)
        self._build_ui()

    # ---------- UI construction ----------

    def _build_ui(self) -> None:
        """Create the canvas, side panel and controls."""
        self.canvas = tk.Canvas(
            self.root, width=960, height=620, bg=BG, highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        side = tk.Frame(self.root, bg=BG, padx=12, pady=12)
        side.grid(row=0, column=1, sticky="ns")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.turn_var = tk.StringVar()
        self.delivered_var = tk.StringVar()
        self.moves_var = tk.StringVar()
        for var, size, bold in (
            (self.turn_var, 16, True),
            (self.delivered_var, 11, False),
        ):
            font = ("Helvetica", size, "bold" if bold else "normal")
            tk.Label(
                side, textvariable=var, bg=BG, fg=FG, font=font, anchor="w",
            ).pack(fill="x", pady=2)
        tk.Label(
            side, text="Moves this turn", bg=BG, fg=LINK_BUSY,
            font=("Helvetica", 10, "bold"), anchor="w",
        ).pack(fill="x", pady=(10, 0))
        tk.Label(
            side, textvariable=self.moves_var, bg=BG, fg=FG, justify="left",
            wraplength=230, anchor="nw", font=("Courier", 10),
        ).pack(fill="x")
        legend = (
            "Legend\n"
            "gold ring    priority zone\n"
            "dashed white restricted (2 turns)\n"
            "X            blocked\n"
            "orange link  used this turn (used/cap)\n"
            "red dot      zone is full\n"
            "n/cap        drones / capacity"
        )
        tk.Label(
            side, text=legend, bg=BG, fg="#9aa4b5", justify="left",
            anchor="w", font=("Courier", 9),
        ).pack(fill="x", side="bottom", pady=(10, 0))

        bar = tk.Frame(self.root, bg=BG, pady=8)
        bar.grid(row=1, column=0, columnspan=2)
        self.play_button = tk.Button(bar, text="Play", width=7,
                                     command=self.toggle_play)
        for text, command in (
            ("Reset", self.reset), ("Prev", self.prev_turn),
        ):
            tk.Button(bar, text=text, width=7, command=command).pack(
                side="left", padx=3)
        self.play_button.pack(side="left", padx=3)
        tk.Button(bar, text="Next", width=7, command=self.next_turn).pack(
            side="left", padx=3)
        tk.Label(bar, text="ms/turn", bg=BG, fg=FG).pack(
            side="left", padx=(16, 2))
        self.speed = tk.Scale(
            bar, from_=150, to=2000, orient="horizontal", length=180,
            bg=BG, fg=FG, highlightthickness=0,
        )
        self.speed.set(800)
        self.speed.pack(side="left")

        self.canvas.bind("<Configure>", lambda _e: self._redraw())
        self.root.bind("<space>", lambda _e: self.toggle_play())
        self.root.bind("<Right>", lambda _e: self.next_turn())
        self.root.bind("<Left>", lambda _e: self.prev_turn())
        self.root.bind("<Home>", lambda _e: self.reset())
        self.root.bind("<End>", lambda _e: self.go_to_end())
        self.root.bind("<Escape>", lambda _e: self.root.destroy())
        self.root.bind("q", lambda _e: self.root.destroy())

    # ---------- controls ----------

    def toggle_play(self) -> None:
        """Start or pause automatic playback."""
        if not self.playing and self.index >= len(self.frames) - 1:
            self.reset()
        self.playing = not self.playing
        self.play_button.config(text="Pause" if self.playing else "Play")

    def next_turn(self) -> None:
        """Advance one turn with animation."""
        if self.index < len(self.frames) - 1:
            self.index += 1
            self.progress = 0.0
            self._redraw()

    def prev_turn(self) -> None:
        """Go back one turn without animation."""
        if self.index >= 0:
            self.index -= 1
            self.progress = 1.0
            self._redraw()

    def reset(self) -> None:
        """Return to the initial state."""
        self.index, self.progress = -1, 1.0
        self._redraw()

    def go_to_end(self) -> None:
        """Jump to the last turn."""
        self.index, self.progress = len(self.frames) - 1, 1.0
        self.playing = False
        self.play_button.config(text="Play")
        self._redraw()

    def _tick(self) -> None:
        """Advance the animation clock."""
        if self.progress < 1.0:
            step = TICK_MS / self.speed.get()
            self.progress = min(1.0, self.progress + step)
            self._redraw()
        elif self.playing:
            if self.index < len(self.frames) - 1:
                self.next_turn()
            else:
                self.playing = False
                self.play_button.config(text="Play")
        self.root.after(TICK_MS, self._tick)

    def run(self) -> None:
        """Show the window and block until it is closed."""
        self.root.update_idletasks()
        self._redraw()
        self.root.after(TICK_MS, self._tick)
        self.root.mainloop()

    # ---------- geometry helpers (no tkinter needed) ----------

    def _anchor(self, index: int, drone_id: int) -> tuple[Zone, Zone | None]:
        """Where a drone is after frame ``index``: a zone or a link."""
        if index < 0:
            return self.network.start, None
        frame = self.frames[index]
        move = frame.in_transit.get(drone_id)
        if move is not None:
            return move.current, move.destination
        return frame.positions[drone_id], None

    def _anchor_point(self, anchor: tuple[Zone, Zone | None]) -> Point:
        """Pixel position of an anchor (links use their midpoint)."""
        ax, ay = self.layout.pos(anchor[0])
        if anchor[1] is None:
            return ax, ay
        bx, by = self.layout.pos(anchor[1])
        return (ax + bx) / 2, (ay + by) / 2

    def link_usage(self, index: int) -> dict[frozenset[str], int]:
        """Crossings started during turn ``index`` per link."""
        usage: dict[frozenset[str], int] = {}
        if index < 0:
            return usage
        previous = self.frames[index - 1].in_transit if index > 0 else {}
        for move in self.frames[index].movements:
            if move.drone_id in previous:
                continue
            key = frozenset((move.current.name, move.destination.name))
            usage[key] = usage.get(key, 0) + 1
        return usage

    def zone_counts(self, index: int) -> dict[str, int]:
        """Drones resting in each zone after frame ``index``."""
        counts: dict[str, int] = {}
        for drone_id in self.drone_ids:
            zone, link = self._anchor(index, drone_id)
            if link is None:
                counts[zone.name] = counts.get(zone.name, 0) + 1
        return counts

    # ---------- drawing ----------

    def _redraw(self) -> None:
        """Redraw the whole scene for the current index and progress."""
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 200)
        height = max(canvas.winfo_height(), 200)
        self.layout.fit(width, height)
        counts = self.zone_counts(self.index)
        usage = self.link_usage(self.index)
        self._draw_links(usage)
        for zone in self.network.zones:
            self._draw_zone(zone, counts.get(zone.name, 0))
        self._draw_drones()
        self._update_panel(counts)

    def _draw_links(self, usage: dict[frozenset[str], int]) -> None:
        """Draw connections; busy ones are highlighted with usage/cap."""
        for conn in self.network.connections:
            ax, ay = self.layout.pos(conn.zone_a)
            bx, by = self.layout.pos(conn.zone_b)
            used = usage.get(
                frozenset((conn.zone_a.name, conn.zone_b.name)), 0
            )
            color = LINK_BUSY if used else LINK
            self.canvas.create_line(
                ax, ay, bx, by, fill=color,
                width=min(2 + conn.max_link_capacity, 7),
            )
            label = (
                f"{used}/{conn.max_link_capacity}" if used
                else (f"x{conn.max_link_capacity}"
                      if conn.max_link_capacity > 1 else "")
            )
            if label:
                self.canvas.create_text(
                    (ax + bx) / 2, (ay + by) / 2 - 11, text=label,
                    fill=color, font=("Helvetica", 9, "bold"),
                )

    def _draw_zone(self, zone: Zone, count: int) -> None:
        """Draw one zone with its type styling and occupancy."""
        x, y = self.layout.pos(zone)
        r = ZONE_RADIUS
        fill = color_to_hex(zone.color)
        dash: tuple[int, ...] = ()
        outline, width = "#d9dee7", 2
        if zone.zone_type == ZoneType.PRIORITY:
            outline, width = "#f5c542", 5
        elif zone.zone_type == ZoneType.RESTRICTED:
            outline, width, dash = "#ffffff", 4, (6, 4)
        elif zone.zone_type == ZoneType.BLOCKED:
            fill = "#3a3f4b"
        is_start = zone == self.network.start
        is_end = zone == self.network.end
        if is_start or is_end:
            self.canvas.create_oval(
                x - r - 6, y - r - 6, x + r + 6, y + r + 6,
                outline="#ffffff", width=2,
            )
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r, fill=fill, outline=outline,
            width=width, dash=dash,
        )
        if zone.zone_type == ZoneType.BLOCKED:
            d = r * 0.6
            for sign in (1, -1):
                self.canvas.create_line(
                    x - d, y - sign * d, x + d, y + sign * d,
                    fill="#ff5c5c", width=3,
                )
        else:
            if is_end:
                inner = str(self._delivered())
            elif is_start:
                inner = str(count)
            else:
                inner = f"{count}/{zone.max_drones}"
            self.canvas.create_text(
                x, y, text=inner, fill=text_color(fill),
                font=("Helvetica", 10, "bold"),
            )
            if not (is_start or is_end) and count >= zone.max_drones:
                self.canvas.create_oval(
                    x + r - 6, y - r - 2, x + r + 4, y - r + 8,
                    fill="#ff3b30", outline="",
                )
        tag = " (START)" if is_start else " (END)" if is_end else ""
        self.canvas.create_text(
            x, y + r + 16, text=zone.name + tag, fill=FG,
            font=("Helvetica", 9),
        )

    def _delivered(self) -> int:
        """Number of drones at the end zone at the current index."""
        if self.index < 0:
            return 0
        end = self.network.end
        return sum(
            1 for z in self.frames[self.index].positions.values() if z == end
        )

    def _draw_drone(self, drone_id: int, x: float, y: float) -> None:
        """Draw one drone dot with its id."""
        color = drone_color(drone_id)
        r = DRONE_RADIUS
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r, fill=color, outline="#111111",
        )
        self.canvas.create_text(
            x, y, text=str(drone_id), fill=text_color(color),
            font=("Helvetica", 7, "bold"),
        )

    def _draw_drones(self) -> None:
        """Draw moving drones individually and resting ones around zones."""
        t = self.progress
        eased = t * t * (3 - 2 * t)
        end = self.network.end
        resting: dict[str, list[int]] = {}
        for drone_id in self.drone_ids:
            before = self._anchor(self.index - 1, drone_id)
            after = self._anchor(self.index, drone_id)
            x0, y0 = self._anchor_point(before)
            x1, y1 = self._anchor_point(after)
            at_end = after[1] is None and after[0] == end
            if at_end and (t >= 1.0 or before[0] == end):
                continue
            if t >= 1.0 or (x0, y0) == (x1, y1):
                if after[1] is None:
                    resting.setdefault(after[0].name, []).append(drone_id)
                    continue
                self._draw_drone(drone_id, x1, y1)
                continue
            self._draw_drone(
                drone_id, x0 + (x1 - x0) * eased, y0 + (y1 - y0) * eased,
            )
        zones = {z.name: z for z in self.network.zones}
        for name, ids in resting.items():
            self._draw_resting(zones[name], ids)

    def _draw_resting(self, zone: Zone, ids: list[int]) -> None:
        """Place resting drones on a ring, or show a count badge."""
        x, y = self.layout.pos(zone)
        if len(ids) > MAX_RING:
            self.canvas.create_rectangle(
                x + ZONE_RADIUS - 2, y + ZONE_RADIUS - 14,
                x + ZONE_RADIUS + 38, y + ZONE_RADIUS + 2,
                fill="#2b3342", outline=FG,
            )
            self.canvas.create_text(
                x + ZONE_RADIUS + 18, y + ZONE_RADIUS - 6,
                text=f"{len(ids)} drones", fill=FG, font=("Helvetica", 8),
            )
            return
        ring = ZONE_RADIUS + DRONE_RADIUS + 5
        for slot, drone_id in enumerate(ids):
            angle = -math.pi / 2 + 2 * math.pi * slot / max(len(ids), 1)
            self._draw_drone(
                drone_id,
                x + ring * math.cos(angle),
                y + ring * math.sin(angle),
            )

    def _update_panel(self, counts: dict[str, int]) -> None:
        """Refresh the text panel."""
        total = len(self.drone_ids)
        shown = max(self.index, -1) + 1
        self.turn_var.set(f"Turn {shown} / {len(self.frames)}")
        self.delivered_var.set(f"Delivered {self._delivered()} / {total}")
        if self.index < 0:
            self.moves_var.set("(start)")
            return
        frame = self.frames[self.index]
        tokens = []
        for move in frame.movements:
            if move.drone_id in frame.in_transit:
                dest = f"{move.current.name}-{move.destination.name}"
            else:
                dest = move.destination.name
            tokens.append(f"D{move.drone_id}-{dest}")
        self.moves_var.set("\n".join(tokens) if tokens else "(all waiting)")
