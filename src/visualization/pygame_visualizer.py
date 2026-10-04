import math
import pygame

from src.models.network import Network
from src.models.zone import Zone
from src.models.zone import ZoneType
from src.simulation.simulation import Simulation


class Visualizer:
    """Interactive animated visualization of the simulation."""

    BACKGROUND = (25, 25, 30)
    TEXT = (240, 240, 240)
    CONNECTION = (100, 100, 110)
    DRONE = (255, 220, 50)
    RESTRICTED = (255, 150, 50)

    ZONE_COLORS = {
        ZoneType.NORMAL: (70, 130, 220),
        ZoneType.PRIORITY: (70, 200, 100),
        ZoneType.RESTRICTED: (220, 130, 60),
        ZoneType.BLOCKED: (100, 100, 100),
    }

    def __init__(
        self,
        network: Network,
        simulation: Simulation,
        width: int = 1280,
        height: int = 720,
    ) -> None:
        """Initialize the Pygame visualizer."""
        self.network = network
        self.simulation = simulation

        self.width = width
        self.height = height

        self.screen: pygame.Surface | None = None
        self.clock = pygame.time.Clock()

        self.font: pygame.font.Font | None = None
        self.small_font: pygame.font.Font | None = None

        self.current_turn = 0
        self.progress = 0.0

        self.playing = True
        self.speed = 1.0

        self.offset_x = 0.0
        self.offset_y = 0.0
        self.zoom = 1.0

        self.zone_radius = 28

        self._auto_fit()

    # ---------------------------------------------------------
    # Camera
    # ---------------------------------------------------------

    def _auto_fit(self) -> None:
        """Fit the whole map into the window."""
        if not self.network.zones:
            return

        min_x = min(zone.x for zone in self.network.zones)
        max_x = max(zone.x for zone in self.network.zones)
        min_y = min(zone.y for zone in self.network.zones)
        max_y = max(zone.y for zone in self.network.zones)

        map_width = max(max_x - min_x, 1)
        map_height = max(max_y - min_y, 1)

        available_width = self.width - 200
        available_height = self.height - 180

        scale_x = available_width / map_width
        scale_y = available_height / map_height

        self.base_scale = min(scale_x, scale_y, 100)

        self.offset_x = (
            self.width / 2
            - ((min_x + max_x) / 2) * self.base_scale
        )
        self.offset_y = (
            self.height / 2
            + ((min_y + max_y) / 2) * self.base_scale
        )

    def world_to_screen(
        self,
        x: float,
        y: float,
    ) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        scale = self.base_scale * self.zoom

        screen_x = int(
            self.offset_x + x * scale
        )

        screen_y = int(
            self.offset_y - y * scale
        )

        return screen_x, screen_y

    # ---------------------------------------------------------
    # Drawing helpers
    # ---------------------------------------------------------

    def _zone_position(
        self,
        zone: Zone,
    ) -> tuple[int, int]:
        """Return the screen position of a zone."""
        return self.world_to_screen(
            zone.x,
            zone.y,
        )

    def _draw_connections(self) -> None:
        """Draw all map connections."""
        assert self.screen is not None

        for connection in self.network.connections:
            start = self._zone_position(
                connection.zone_a
            )
            end = self._zone_position(
                connection.zone_b
            )

            pygame.draw.line(
                self.screen,
                self.CONNECTION,
                start,
                end,
                3,
            )

            middle_x = (start[0] + end[0]) // 2
            middle_y = (start[1] + end[1]) // 2

            text = self.small_font.render(
                f"cap:{connection.max_link_capacity}",
                True,
                self.TEXT,
            )

            self.screen.blit(
                text,
                (
                    middle_x + 5,
                    middle_y + 5,
                ),
            )

    def _draw_zones(self) -> None:
        """Draw all zones."""
        assert self.screen is not None

        for zone in self.network.zones:
            position = self._zone_position(zone)

            if zone == self.network.start:
                color = (60, 200, 80)
            elif zone == self.network.end:
                color = (220, 70, 70)
            else:
                color = self.ZONE_COLORS[
                    zone.zone_type
                ]

            pygame.draw.circle(
                self.screen,
                color,
                position,
                self.zone_radius,
            )

            pygame.draw.circle(
                self.screen,
                self.TEXT,
                position,
                self.zone_radius,
                2,
            )

            name = self.font.render(
                zone.name,
                True,
                self.TEXT,
            )

            rect = name.get_rect(
                center=position
            )

            self.screen.blit(name, rect)

    # ---------------------------------------------------------
    # Drone position
    # ---------------------------------------------------------

    def _get_drone_position(
        self,
        drone_id: int,
    ) -> tuple[float, float] | None:
        """Calculate interpolated drone position."""
        history = self.simulation.position_history

        if not history:
            return None

        if self.current_turn == 0:
            first = history[0].get(drone_id)

            if first is None:
                return None

            return (
                float(first.x),
                float(first.y),
            )

        index = min(
            self.current_turn - 1,
            len(history) - 1,
        )

        current = history[index].get(drone_id)

        if current is None:
            return None

        current_x = float(current.x)
        current_y = float(current.y)

        if (
            self.progress >= 1.0
            or index == 0
        ):
            return current_x, current_y

        previous = history[index - 1].get(
            drone_id
        )

        if previous is None:
            return current_x, current_y

        previous_x = float(previous.x)
        previous_y = float(previous.y)

        x = (
            previous_x
            + (current_x - previous_x)
            * self.progress
        )

        y = (
            previous_y
            + (current_y - previous_y)
            * self.progress
        )

        return x, y

    def _draw_drones(self) -> None:
        """Draw all drones."""
        assert self.screen is not None

        if not self.simulation.position_history:
            return

        drone_ids = (
            self.simulation.position_history[0].keys()
        )

        for drone_id in drone_ids:
            position = self._get_drone_position(
                drone_id
            )

            if position is None:
                continue

            screen_position = self.world_to_screen(
                position[0],
                position[1],
            )

            pygame.draw.circle(
                self.screen,
                self.DRONE,
                screen_position,
                13,
            )

            pygame.draw.circle(
                self.screen,
                (20, 20, 20),
                screen_position,
                13,
                2,
            )

            text = self.small_font.render(
                f"D{drone_id}",
                True,
                (20, 20, 20),
            )

            rect = text.get_rect(
                center=screen_position
            )

            self.screen.blit(
                text,
                rect,
            )

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def _draw_ui(self) -> None:
        """Draw simulation information."""
        assert self.screen is not None

        total_turns = len(
            self.simulation.history
        )

        turn_text = (
            f"Turn: {self.current_turn}"
            f" / {total_turns}"
        )

        status = (
            "PLAYING"
            if self.playing
            else "PAUSED"
        )

        text = self.font.render(
            f"{turn_text}    {status}",
            True,
            self.TEXT,
        )

        self.screen.blit(
            text,
            (20, 20),
        )

        controls = (
            "SPACE: Play/Pause   "
            "LEFT/RIGHT: Step   "
            "R: Reset   "
            "UP/DOWN: Speed"
        )

        control_text = self.small_font.render(
            controls,
            True,
            self.TEXT,
        )

        self.screen.blit(
            control_text,
            (20, self.height - 40),
        )

    # ---------------------------------------------------------
    # Animation
    # ---------------------------------------------------------

    def _advance_animation(
        self,
        dt: float,
    ) -> None:
        """Advance the animation."""
        if not self.playing:
            return

        total_turns = len(
            self.simulation.history
        )

        if self.current_turn >= total_turns:
            self.playing = False
            self.progress = 1.0
            return

        self.progress += (
            dt * self.speed
        )

        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_turn += 1

    def _reset(self) -> None:
        """Reset the animation."""
        self.current_turn = 0
        self.progress = 0.0
        self.playing = True

    # ---------------------------------------------------------
    # Main loop
    # ---------------------------------------------------------

    def run(self) -> None:
        """Run the Pygame animation."""
        pygame.init()

        self.screen = pygame.display.set_mode(
            (self.width, self.height)
        )

        pygame.display.set_caption(
            "Fly-in Drones"
        )

        self.font = pygame.font.Font(
            None,
            24,
        )

        self.small_font = pygame.font.Font(
            None,
            18,
        )

        running = True

        while running:
            dt = (
                self.clock.tick(60) / 1000.0
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.playing = (
                            not self.playing
                        )

                    elif event.key == pygame.K_r:
                        self._reset()

                    elif event.key == pygame.K_RIGHT:
                        self.playing = False

                        if self.current_turn < len(
                            self.simulation.history
                        ):
                            self.current_turn += 1

                        self.progress = 0.0

                    elif event.key == pygame.K_LEFT:
                        self.playing = False

                        if self.current_turn > 0:
                            self.current_turn -= 1

                        self.progress = 0.0

                    elif event.key == pygame.K_UP:
                        self.speed = min(
                            self.speed + 0.5,
                            5.0,
                        )

                    elif event.key == pygame.K_DOWN:
                        self.speed = max(
                            self.speed - 0.5,
                            0.5,
                        )

                elif event.type == pygame.MOUSEWHEEL:
                    self.zoom *= (
                        1.1
                        if event.y > 0
                        else 0.9
                    )

                    self.zoom = max(
                        0.2,
                        min(self.zoom, 5.0),
                    )

            self._advance_animation(dt)

            self.screen.fill(
                self.BACKGROUND
            )

            self._draw_connections()
            self._draw_zones()
            self._draw_drones()
            self._draw_ui()

            pygame.display.flip()

        pygame.quit()
