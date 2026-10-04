import pytest

from src.models.connection import Connection
from src.models.zone import Zone, ZoneType
from src.parser.validator import (
    CommonValidator,
    ConnectionValidator,
    MapStructureValidator,
    ZoneValidator,
)


class TestCommonValidator:

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("1", 1),
            ("10", 10),
            ("999", 999),
        ],
    )
    def test_positive_integer_valid(
        self,
        value: str,
        expected: int,
    ) -> None:
        result = CommonValidator.positive_integer(
            value,
            "test",
        )

        assert result == expected

    @pytest.mark.parametrize(
        "value",
        [
            "0",
            "-1",
            "-100",
            "abc",
            "",
        ],
    )
    def test_positive_integer_invalid(
        self,
        value: str,
    ) -> None:
        with pytest.raises(ValueError):
            CommonValidator.positive_integer(
                value,
                "test",
            )


class TestZoneValidator:

    def test_valid_zone_name(self) -> None:
        assert ZoneValidator.name("hub1") == "hub1"

    def test_empty_zone_name(self) -> None:
        with pytest.raises(
            ValueError,
            match="Zone name cannot be empty",
        ):
            ZoneValidator.name("")

    def test_zone_name_with_whitespace(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain whitespace",
        ):
            ZoneValidator.name("hub 1")

    def test_zone_name_with_dash(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot contain dashes",
        ):
            ZoneValidator.name("hub-1")

    def test_valid_zone_type(self) -> None:
        result = ZoneValidator.zone_type("normal")

        assert result == ZoneType.NORMAL

    def test_invalid_zone_type(self) -> None:
        with pytest.raises(
            ValueError,
            match="Invalid zone type",
        ):
            ZoneValidator.zone_type("invalid")

    def test_unique_zone_name(self) -> None:
        zone = Zone(
            name="A",
            x=0,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="red",
            max_drones=1,
        )

        zones = {
            "A": zone,
        }

        duplicate = Zone(
            name="A",
            x=1,
            y=1,
            zone_type=ZoneType.NORMAL,
            color="blue",
            max_drones=1,
        )

        with pytest.raises(
            ValueError,
            match="Duplicate zone name",
        ):
            ZoneValidator.unique_name(
                zones,
                duplicate,
            )

    def test_unique_zone_coordinates(self) -> None:
        zone = Zone(
            name="A",
            x=0,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="red",
            max_drones=1,
        )

        zones = {
            "A": zone,
        }

        duplicate_coordinates = Zone(
            name="B",
            x=0,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="blue",
            max_drones=1,
        )

        with pytest.raises(
            ValueError,
            match="Duplicate zone coordinates",
        ):
            ZoneValidator.unique_coordinates(
                zones,
                duplicate_coordinates,
            )


class TestConnectionValidator:

    def test_connection_zones_exist(self) -> None:
        zone_a = Zone(
            name="A",
            x=0,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        zone_b = Zone(
            name="B",
            x=1,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        zones = {
            "A": zone_a,
            "B": zone_b,
        }

        ConnectionValidator.zones_exist(
            "A",
            "B",
            zones,
        )

    def test_connection_first_zone_missing(self) -> None:
        zones = {}

        with pytest.raises(
            ValueError,
            match="Zone 'A' does not exist",
        ):
            ConnectionValidator.zones_exist(
                "A",
                "B",
                zones,
            )

    def test_connection_self_loop(self) -> None:
        with pytest.raises(
            ValueError,
            match="cannot connect a zone to itself",
        ):
            ConnectionValidator.not_self_loop(
                "A",
                "A",
            )

    def test_duplicate_connection(self) -> None:
        zone_a = Zone(
            name="A",
            x=0,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        zone_b = Zone(
            name="B",
            x=1,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        existing = Connection(
            zone_a=zone_a,
            zone_b=zone_b,
            max_link_capacity=1,
        )

        reversed_connection = Connection(
            zone_a=zone_b,
            zone_b=zone_a,
            max_link_capacity=1,
        )

        with pytest.raises(
            ValueError,
            match="Duplicate connection",
        ):
            ConnectionValidator.unique(
                [existing],
                reversed_connection,
            )


class TestMapStructureValidator:

    def test_valid_structure(self) -> None:
        start = Zone(
            name="start",
            x=0,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        end = Zone(
            name="end",
            x=1,
            y=1,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        MapStructureValidator.required_fields(
            10,
            start,
            end,
        )

    def test_missing_nb_drones(self) -> None:
        with pytest.raises(
            ValueError,
            match="Missing nb_drones",
        ):
            MapStructureValidator.required_fields(
                None,
                None,
                None,
            )

    def test_missing_start_hub(self) -> None:
        end = Zone(
            name="end",
            x=1,
            y=1,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        with pytest.raises(
            ValueError,
            match="Missing start_hub",
        ):
            MapStructureValidator.required_fields(
                10,
                None,
                end,
            )

    def test_missing_end_hub(self) -> None:
        start = Zone(
            name="start",
            x=0,
            y=0,
            zone_type=ZoneType.NORMAL,
            color="none",
            max_drones=1,
        )

        with pytest.raises(
            ValueError,
            match="Missing end_hub",
        ):
            MapStructureValidator.required_fields(
                10,
                start,
                None,
            )
