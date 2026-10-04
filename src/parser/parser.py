from src.models.connection import Connection
from src.models.network import Network
from src.models.zone import Zone
from src.parser.metadata import MetadataParser
from src.parser.validator import (
    CommonValidator,
    ConnectionValidator,
    MapStructureValidator,
    ZoneValidator
)


ZONE_METADATA_KEYS = {
    "zone",
    "color",
    "max_drones"
}

CONNECTION_METADATA_KEYS = {
    "max_link_capacity"
}

_HUB_PREFIXES = (
    "start_hub:",
    "end_hub:",
    "hub:"
)


class MapParser:
    """Parse a map file into a Network object.

    Connections are stored during the first parsing pass and resolved
    after all zones have been parsed. This allows connections to reference
    zones defined later in the file.
    """

    def __init__(self) -> None:
        self._reset()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, file_path: str) -> Network:
        """Parse a map file and return a Network object."""
        self._reset()

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:
                for line_number, raw_line in enumerate(
                    file,
                    start=1,
                ):
                    line = raw_line.strip()

                    if not line or line.startswith("#"):
                        continue

                    try:
                        self._parse_line(
                            line_number,
                            line,
                        )
                    except ValueError as error:
                        raise ValueError(
                            f"Line {line_number}: {error}"
                        ) from None

        except OSError as error:
            raise ValueError(
                f"Could not read map file "
                f"'{file_path}': {error}"
            ) from None

        MapStructureValidator.required_fields(
            self._nb_drones,
            self._start,
            self._end,
        )

        self._resolve_connections()

        assert self._nb_drones is not None
        assert self._start is not None
        assert self._end is not None

        return Network(
            nb_drones=self._nb_drones,
            zones=list(self._zones.values()),
            connections=self._connections,
            start=self._start,
            end=self._end,
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """Reset parser state so an instance can be reused."""
        self._nb_drones: int | None = None
        self._zones: dict[str, Zone] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None
        self._connections: list[Connection] = []
        self._pending_connections: list[
            tuple[int, str]
        ] = []

    # ------------------------------------------------------------------
    # Line dispatch
    # ------------------------------------------------------------------

    def _parse_line(
        self,
        line_number: int,
        line: str,
    ) -> None:
        """Dispatch a line to its corresponding parser."""

        if line.startswith("nb_drones:"):
            self._parse_nb_drones_line(line)
            return

        if line.startswith(_HUB_PREFIXES):
            kind, _, _ = line.partition(":")

            self._parse_hub_line(
                line,
                kind=kind.strip(),
            )
            return

        if line.startswith("connection:"):
            self._pending_connections.append(
                (line_number, line)
            )
            return

        raise ValueError(
            f"Unknown line type: '{line}'"
        )

    # ------------------------------------------------------------------
    # nb_drones
    # ------------------------------------------------------------------

    def _parse_nb_drones_line(
        self,
        line: str,
    ) -> None:
        """Parse an nb_drones definition."""

        if self._nb_drones is not None:
            raise ValueError(
                "Duplicate nb_drones definition"
            )

        key, separator, value = line.partition(":")

        if not separator:
            raise ValueError(
                "Invalid nb_drones definition"
            )

        key = key.strip()
        value = value.strip()

        if key != "nb_drones":
            raise ValueError(
                f"Invalid field '{key}'. "
                "Expected 'nb_drones'"
            )

        self._nb_drones = (
            CommonValidator.positive_integer(
                value,
                "nb_drones",
            )
        )

    # ------------------------------------------------------------------
    # Zones
    # ------------------------------------------------------------------

    def _parse_hub_line(
        self,
        line: str,
        *,
        kind: str,
    ) -> None:
        """Parse a start_hub, end_hub, or normal hub."""

        if kind == "start_hub" and self._start is not None:
            raise ValueError(
                "Duplicate start_hub definition"
            )

        if kind == "end_hub" and self._end is not None:
            raise ValueError(
                "Duplicate end_hub definition"
            )

        is_start_or_end = kind in {
            "start_hub",
            "end_hub",
        }

        zone = self._build_zone(
            line,
            is_start_or_end=is_start_or_end,
        )

        ZoneValidator.unique_name(
            self._zones,
            zone,
        )

        self._zones[zone.name] = zone

        if kind == "start_hub":
            self._start = zone

        elif kind == "end_hub":
            self._end = zone

    def _build_zone(
        self,
        line: str,
        *,
        is_start_or_end: bool,
    ) -> Zone:
        """Build a Zone from a hub definition."""

        _, separator, content = line.partition(":")

        if not separator:
            raise ValueError(
                "Invalid zone definition"
            )

        content = content.strip()

        metadata, content = (
            self._extract_metadata(content)
        )

        MetadataParser.ensure_known_keys(
            metadata,
            ZONE_METADATA_KEYS,
            "a hub",
        )

        parts = content.split()

        if len(parts) != 3:
            raise ValueError(
                "Invalid zone definition. "
                "Expected: <name> <x> <y>"
            )

        name, x_value, y_value = parts

        name = ZoneValidator.name(name)

        try:
            x = int(x_value)
            y = int(y_value)
        except ValueError:
            raise ValueError(
                "Zone coordinates must be integers"
            ) from None

        zone_type = ZoneValidator.zone_type(
            metadata.get("zone", "normal")
        )

        color = metadata.get(
            "color",
            "none",
        )

        if is_start_or_end:
            # max_drones is irrelevant for start/end hubs.
            max_drones = 1
        else:
            max_drones_value = metadata.get(
                "max_drones",
                "1",
            )

            max_drones = (
                CommonValidator.positive_integer(
                    max_drones_value,
                    "max_drones",
                )
            )

        return Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
        )

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def _resolve_connections(self) -> None:
        """Resolve pending connections after all zones exist."""

        for line_number, line in (
            self._pending_connections
        ):
            try:
                connection = (
                    self._parse_connection_line(line)
                )

                ConnectionValidator.unique(
                    self._connections,
                    connection,
                )

                self._connections.append(
                    connection
                )

            except ValueError as error:
                raise ValueError(
                    f"Line {line_number}: {error}"
                ) from None

    def _parse_connection_line(
        self,
        line: str,
    ) -> Connection:
        """Parse a connection definition."""

        key, separator, content = line.partition(":")

        if not separator:
            raise ValueError(
                "Invalid connection definition"
            )

        key = key.strip()
        content = content.strip()

        if key != "connection":
            raise ValueError(
                f"Invalid connection type '{key}'"
            )

        metadata, content = (
            self._extract_metadata(content)
        )

        MetadataParser.ensure_known_keys(
            metadata,
            CONNECTION_METADATA_KEYS,
            "a connection",
        )

        if content.count("-") != 1:
            raise ValueError(
                "Invalid connection definition. "
                "Expected: <zone_a>-<zone_b>"
            )

        zone_a_name, zone_b_name = (
            part.strip()
            for part in content.split("-")
        )

        if not zone_a_name or not zone_b_name:
            raise ValueError(
                "Connection must contain two zone names"
            )

        ConnectionValidator.not_self_loop(
            zone_a_name,
            zone_b_name,
        )

        ConnectionValidator.zones_exist(
            zone_a_name,
            zone_b_name,
            self._zones,
        )

        max_capacity_value = metadata.get(
            "max_link_capacity",
            "1",
        )

        max_link_capacity = (
            CommonValidator.positive_integer(
                max_capacity_value,
                "max_link_capacity",
            )
        )

        return Connection(
            zone_a=self._zones[zone_a_name],
            zone_b=self._zones[zone_b_name],
            max_link_capacity=max_link_capacity,
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metadata(
        content: str,
    ) -> tuple[dict[str, str], str]:
        """Extract an optional trailing metadata block.

        Valid:
            A 1 2
            A 1 2 [color=red]

        Invalid:
            A [color=red] 1 2
            A 1 2 ]
            A 1 2 [
            A 1 2 [color=red] extra
        """

        has_opening = "[" in content
        has_closing = "]" in content

        if not has_opening and not has_closing:
            return {}, content

        if not has_opening:
            raise ValueError(
                "Invalid metadata: missing opening '['"
            )

        if not has_closing:
            raise ValueError(
                "Invalid metadata: missing closing ']'"
            )

        if content.count("[") != 1:
            raise ValueError(
                "Only one metadata block is allowed"
            )

        if content.count("]") != 1:
            raise ValueError(
                "Only one metadata block is allowed"
            )

        metadata_start = content.find("[")

        definition = content[
            :metadata_start
        ].strip()

        metadata_text = content[
            metadata_start:
        ].strip()

        if not metadata_text.endswith("]"):
            raise ValueError(
                "Metadata must appear at the end "
                "of the definition"
            )

        metadata = MetadataParser.parse(
            metadata_text
        )

        return metadata, definition
