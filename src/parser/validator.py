from src.models.connection import Connection
from src.models.zone import Zone, ZoneType


class CommonValidator:
    """Validation helpers shared across parsing components."""

    @staticmethod
    def positive_integer(value: str, field_name: str) -> int:
        """Validate and convert a positive integer."""
        try:
            number = int(value)
        except ValueError:
            raise ValueError(
                f"{field_name} must be a positive integer, "
                f"got '{value}'"
            ) from None

        if number <= 0:
            raise ValueError(
                f"{field_name} must be a positive integer, "
                f"got '{value}'"
            )

        return number


class ZoneValidator:
    """Validation rules for zone definitions."""

    @staticmethod
    def name(name: str) -> str:
        """Validate a zone name."""
        if not name:
            raise ValueError(
                "Zone name cannot be empty"
            )

        if any(character.isspace() for character in name):
            raise ValueError(
                f"Zone name '{name}' cannot contain whitespace"
            )

        if "-" in name:
            raise ValueError(
                f"Zone name '{name}' cannot contain dashes"
            )

        return name

    @staticmethod
    def zone_type(value: str) -> ZoneType:
        """Validate and convert a zone type."""
        try:
            return ZoneType(value)
        except ValueError:
            valid_types = ", ".join(
                zone_type.value
                for zone_type in ZoneType
            )

            raise ValueError(
                f"Invalid zone type '{value}'. "
                f"Expected one of: {valid_types}"
            ) from None

    @staticmethod
    def unique_name(
        zones: dict[str, Zone],
        zone: Zone,
    ) -> None:
        """Ensure the zone name has not already been used."""
        if zone.name in zones:
            raise ValueError(
                f"Duplicate zone name '{zone.name}'"
            )


class ConnectionValidator:
    """Validation rules for connection definitions."""

    @staticmethod
    def zones_exist(
        zone_a_name: str,
        zone_b_name: str,
        zones: dict[str, Zone],
    ) -> None:
        """Ensure both zones referenced by a connection exist."""
        if zone_a_name not in zones:
            raise ValueError(
                f"Zone '{zone_a_name}' does not exist"
            )

        if zone_b_name not in zones:
            raise ValueError(
                f"Zone '{zone_b_name}' does not exist"
            )

    @staticmethod
    def not_self_loop(
        zone_a_name: str,
        zone_b_name: str,
    ) -> None:
        """Ensure a connection does not connect a zone to itself."""
        if zone_a_name == zone_b_name:
            raise ValueError(
                "A connection cannot connect a zone to itself"
            )

    @staticmethod
    def unique(
        connections: list[Connection],
        connection: Connection,
    ) -> None:
        """Ensure an undirected connection does not already exist."""
        new_pair = frozenset(
            (
                connection.zone_a.name,
                connection.zone_b.name,
            )
        )

        for existing_connection in connections:
            existing_pair = frozenset(
                (
                    existing_connection.zone_a.name,
                    existing_connection.zone_b.name,
                )
            )

            if new_pair == existing_pair:
                raise ValueError(
                    "Duplicate connection: "
                    f"{connection.zone_a.name}-"
                    f"{connection.zone_b.name}"
                )


class MapStructureValidator:
    """Validation rules for the complete map."""

    @staticmethod
    def required_fields(
        nb_drones: int | None,
        start: Zone | None,
        end: Zone | None,
    ) -> None:
        """Ensure all required map definitions are present."""
        if nb_drones is None:
            raise ValueError(
                "Missing nb_drones definition"
            )

        if start is None:
            raise ValueError(
                "Missing start_hub definition"
            )

        if end is None:
            raise ValueError(
                "Missing end_hub definition"
            )
