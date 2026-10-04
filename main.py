"""Fly-in entry point: parse a map, route the drones, show the result."""
import argparse
import sys

from src.algorithms.graph import Graph
from src.algorithms.scheduler import Scheduler
from src.models.network import Network
from src.parser.parser import MapParser
from src.simulation.simulation import Simulation
from src.simulation.state import SimulationState
from src.visualization.visualization import GraphicalVisualizer, TerminalVisualizer


class FlyInApp:
    """Orchestrates parsing, planning, simulation and display."""

    def __init__(self, args: argparse.Namespace) -> None:
        """Store the command-line options."""
        self.args = args

    def _load_network(self) -> Network:
        """Parse the map file into a Network (raises ValueError)."""
        return MapParser().parse(self.args.map_file)

    def _simulate(self, network: Network) -> Simulation:
        """Plan every drone, run the simulation and return it."""
        scheduler = Scheduler(network)
        drones = scheduler.create_drones()
        state = SimulationState(drones, network.start, network.end)
        simulation = Simulation(scheduler, state)
        simulation.run(max_turns=self.args.max_turns)
        return simulation

    def _display(self, network: Network, simulation: Simulation) -> None:
        """Print the visual replay and/or the official output."""
        if self.args.gui:
            print("\n".join(TerminalVisualizer(
                network, simulation).plain_lines()))
            GraphicalVisualizer(network, simulation).run()
            return
        viz = TerminalVisualizer(network, simulation)
        if self.args.plain:
            print("\n".join(viz.plain_lines()))
            return
        if not self.args.no_visual:
            viz.show_legend()
            viz.play(delay=self.args.delay, step=self.args.step)
            viz.show_summary()
            print("\n=== OUTPUT ===")
        print("\n".join(viz.plain_lines()))

    def run(self) -> int:
        """Run the whole pipeline; return a process exit code."""
        try:
            network = self._load_network()
            if not Graph(network).has_path(network.start, network.end):
                print(
                    "Error: map is unsolvable (no path from start to end).",
                    file=sys.stderr,
                )
                return 1
            simulation = self._simulate(network)
            self._display(network, simulation)
        except (ValueError, RuntimeError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        return 0


def build_arg_parser() -> argparse.ArgumentParser:
    """Define the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Fly-in: drone routing simulation",
    )
    parser.add_argument("map_file", help="path to the map file")
    parser.add_argument(
        "--delay", type=float, default=0.6,
        help="seconds between turns in the replay (default: 0.6)",
    )
    parser.add_argument(
        "--step", action="store_true",
        help="press Enter to advance each turn",
    )
    parser.add_argument(
        "--no-visual", action="store_true",
        help="skip the colored replay, print only the output lines",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="open the animated graphical window (tkinter)",
    )
    parser.add_argument(
        "--plain", action="store_true",
        help="print only the official uncolored output",
    )
    parser.add_argument(
        "--max-turns", type=int, default=100000,
        help="safety limit on simulation turns (default: 100000)",
    )
    return parser


def main() -> int:
    """Parse arguments and launch the application."""
    args = build_arg_parser().parse_args()
    return FlyInApp(args).run()


if __name__ == "__main__":
    sys.exit(main())
