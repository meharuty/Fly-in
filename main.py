"""Fly-in entry point: parse a map, route the drones, show the result."""

import argparse
import sys

from src.algorithms.graph import Graph
from src.algorithms.pathfinder import Pathfinder
from src.algorithms.scheduler import Scheduler
from src.models.network import Network
from src.models.zone import Zone
from src.parser.parser import MapParser
from src.simulation.simulation import Simulation
from src.simulation.state import SimulationState
from src.visualization.terminal import TerminalVisualizer
from src.visualization.pygame_visualizer import Visualizer


class FlyInApp:
    """Orchestrates parsing, pathfinding, simulation and display."""

    def __init__(self, args: argparse.Namespace) -> None:
        """Store the command-line options."""
        self.args = args

    def _load_network(self) -> Network:
        """Parse the map file into a Network."""
        return MapParser().parse(self.args.map_file)

    def _find_paths(
        self,
        network: Network,
    ) -> list[list[Zone]]:
        """Return candidate start-to-end paths."""
        graph = Graph(network)

        if not graph.has_path(
            network.start,
            network.end,
        ):
            return []

        finder = Pathfinder(graph)

        return finder.find_paths(
            network.start,
            network.end,
            max_paths=self.args.max_paths,
        )

    def _simulate(
        self,
        network: Network,
        paths: list[list[Zone]],
    ) -> Simulation:
        """Create drones, run the simulation and return it."""
        scheduler = Scheduler(
            paths,
            network.nb_drones,
            network.connections,
        )

        drones = scheduler.create_drones()

        state = SimulationState(
            drones,
            network.start,
            network.end,
        )

        simulation = Simulation(
            scheduler,
            state,
        )

        simulation.run(
            max_turns=self.args.max_turns,
        )

        return simulation

    def _display(
        self,
        network: Network,
        simulation: Simulation,
    ) -> None:
        """Show official output and graphical animation."""

        terminal_viz = TerminalVisualizer(
            network,
            simulation,
        )

        # Official VII.5 output
        print("\n=== OUTPUT ===")
        print(
            "\n".join(
                terminal_viz.plain_lines()
            )
        )

        # Pygame animated visualization
        if not self.args.no_visual:
            visualizer = Visualizer(
                network,
                simulation,
            )
            visualizer.run()

    def run(self) -> int:
        """Run the whole pipeline and return an exit code."""
        try:
            network = self._load_network()

            paths = self._find_paths(network)

            if not paths:
                print(
                    "Error: map is unsolvable "
                    "(no path from start to end).",
                    file=sys.stderr,
                )
                return 1

            print("Available paths:")
            for index, path in enumerate(
                paths,
                start=1,
            ):
                print(
                    f"Path {index}:",
                    " -> ".join(
                        zone.name
                        for zone in path
                    ),
                )

            simulation = self._simulate(
                network,
                paths,
            )

            self._display(
                network,
                simulation,
            )

        except FileNotFoundError:
            print(
                f"Error: file not found: "
                f"{self.args.map_file}",
                file=sys.stderr,
            )
            return 1

        except (ValueError, RuntimeError) as error:
            print(
                f"Error: {error}",
                file=sys.stderr,
            )
            return 1

        except KeyboardInterrupt:
            print(
                "\nInterrupted.",
                file=sys.stderr,
            )
            return 130

        return 0


def build_arg_parser() -> argparse.ArgumentParser:
    """Define the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Fly-in: drone routing simulation",
    )

    parser.add_argument(
        "map_file",
        help="path to the map file",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.6,
        help=(
            "seconds between turns in terminal replay "
            "(default: 0.6)"
        ),
    )

    parser.add_argument(
        "--step",
        action="store_true",
        help="press Enter to advance each terminal turn",
    )

    parser.add_argument(
        "--no-visual",
        action="store_true",
        help="skip the Pygame visualization",
    )

    parser.add_argument(
        "--plain",
        action="store_true",
        help="print only the official uncolored output",
    )

    parser.add_argument(
        "--max-paths",
        type=int,
        default=5,
        help=(
            "number of candidate paths to consider "
            "(default: 5)"
        ),
    )

    parser.add_argument(
        "--max-turns",
        type=int,
        default=1000,
        help=(
            "safety limit on simulation turns "
            "(default: 1000)"
        ),
    )

    return parser


def main() -> int:
    """Parse arguments and launch the application."""
    args = build_arg_parser().parse_args()
    return FlyInApp(args).run()


if __name__ == "__main__":
    sys.exit(main())
