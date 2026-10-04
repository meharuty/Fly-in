import pytest

from src.parser.parser import MapParser


class TestMapParser:

    # ------------------------------------------------------------------
    # Valid maps
    # ------------------------------------------------------------------

    def test_parse_simple_valid_map(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 3

            start_hub: start 0 0
            hub: middle 1 0
            end_hub: end 2 0

            connection: start-middle
            connection: middle-end
            """,
            encoding="utf-8",
        )

        network = MapParser().parse(str(map_file))

        assert network.nb_drones == 3
        assert len(network.zones) == 3
        assert len(network.connections) == 2

        assert network.start.name == "start"
        assert network.end.name == "end"

    def test_parse_zone_metadata(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 5

            start_hub: start 0 0
            hub: middle 1 2 [zone=normal color=red max_drones=3]
            end_hub: end 3 4

            connection: start-middle
            connection: middle-end
            """,
            encoding="utf-8",
        )

        network = MapParser().parse(str(map_file))

        middle = next(
            zone
            for zone in network.zones
            if zone.name == "middle"
        )

        assert middle.x == 1
        assert middle.y == 2
        assert middle.color == "red"
        assert middle.max_drones == 3

    def test_parse_connection_metadata(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            end_hub: end 1 0

            connection: start-end [max_link_capacity=5]
            """,
            encoding="utf-8",
        )

        network = MapParser().parse(str(map_file))

        assert len(network.connections) == 1
        assert network.connections[0].max_link_capacity == 5

    def test_connections_can_appear_before_zones(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            connection: start-end

            start_hub: start 0 0
            end_hub: end 1 0
            """,
            encoding="utf-8",
        )

        network = MapParser().parse(str(map_file))

        assert len(network.connections) == 1
        assert network.connections[0].zone_a.name == "start"
        assert network.connections[0].zone_b.name == "end"

    def test_comments_and_empty_lines_are_ignored(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            # Number of drones
            nb_drones: 2

            # Start position
            start_hub: start 0 0

            # End position
            end_hub: end 1 0

            # Connection
            connection: start-end
            """,
            encoding="utf-8",
        )

        network = MapParser().parse(str(map_file))

        assert network.nb_drones == 2
        assert len(network.zones) == 2
        assert len(network.connections) == 1

    def test_parser_can_be_reused(
        self,
        tmp_path,
    ) -> None:
        first_map = tmp_path / "first.txt"
        second_map = tmp_path / "second.txt"

        first_map.write_text(
            """
            nb_drones: 1
            start_hub: start1 0 0
            end_hub: end1 1 0
            connection: start1-end1
            """,
            encoding="utf-8",
        )

        second_map.write_text(
            """
            nb_drones: 2
            start_hub: start2 0 0
            end_hub: end2 2 0
            connection: start2-end2
            """,
            encoding="utf-8",
        )

        parser = MapParser()

        first_network = parser.parse(str(first_map))
        second_network = parser.parse(str(second_map))

        assert first_network.nb_drones == 1
        assert second_network.nb_drones == 2

        assert first_network.start.name == "start1"
        assert second_network.start.name == "start2"

    # ------------------------------------------------------------------
    # Missing required fields
    # ------------------------------------------------------------------

    def test_missing_nb_drones(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            start_hub: start 0 0
            end_hub: end 1 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Missing nb_drones definition",
        ):
            MapParser().parse(str(map_file))

    def test_missing_start_hub(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2
            end_hub: end 1 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Missing start_hub definition",
        ):
            MapParser().parse(str(map_file))

    def test_missing_end_hub(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2
            start_hub: start 0 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Missing end_hub definition",
        ):
            MapParser().parse(str(map_file))

    # ------------------------------------------------------------------
    # Duplicate definitions
    # ------------------------------------------------------------------

    def test_duplicate_nb_drones(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2
            nb_drones: 3

            start_hub: start 0 0
            end_hub: end 1 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Duplicate nb_drones definition",
        ):
            MapParser().parse(str(map_file))

    def test_duplicate_start_hub(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start1 0 0
            start_hub: start2 1 0
            end_hub: end 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Duplicate start_hub definition",
        ):
            MapParser().parse(str(map_file))

    def test_duplicate_end_hub(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            end_hub: end1 1 0
            end_hub: end2 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Duplicate end_hub definition",
        ):
            MapParser().parse(str(map_file))

    def test_duplicate_zone_name(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            hub: start 1 0
            end_hub: end 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Duplicate zone name",
        ):
            MapParser().parse(str(map_file))

    def test_duplicate_zone_coordinates(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            hub: middle 0 0
            end_hub: end 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Duplicate zone coordinates",
        ):
            MapParser().parse(str(map_file))

    # ------------------------------------------------------------------
    # Invalid zone definitions
    # ------------------------------------------------------------------

    def test_invalid_zone_coordinates(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start hello 0
            end_hub: end 1 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Zone coordinates must be integers",
        ):
            MapParser().parse(str(map_file))

    def test_invalid_zone_definition(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0
            end_hub: end 1 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Invalid zone definition",
        ):
            MapParser().parse(str(map_file))

    def test_invalid_zone_type(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            hub: middle 1 0 [zone=invalid]
            end_hub: end 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Invalid zone type",
        ):
            MapParser().parse(str(map_file))

    def test_unknown_zone_metadata(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            hub: middle 1 0 [unknown=value]
            end_hub: end 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Unknown metadata key",
        ):
            MapParser().parse(str(map_file))

    # ------------------------------------------------------------------
    # Invalid connections
    # ------------------------------------------------------------------

    def test_connection_zone_does_not_exist(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            end_hub: end 1 0

            connection: start-missing
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Zone 'missing' does not exist",
        ):
            MapParser().parse(str(map_file))

    def test_connection_self_loop(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            end_hub: end 1 0

            connection: start-start
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="cannot connect a zone to itself",
        ):
            MapParser().parse(str(map_file))

    def test_duplicate_connection(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            end_hub: end 1 0

            connection: start-end
            connection: end-start
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Duplicate connection",
        ):
            MapParser().parse(str(map_file))

    def test_invalid_connection_format(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            end_hub: end 1 0

            connection: start-end-other
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Invalid connection definition",
        ):
            MapParser().parse(str(map_file))

    def test_unknown_connection_metadata(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            end_hub: end 1 0

            connection: start-end [capacity=5]
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="Unknown metadata key",
        ):
            MapParser().parse(str(map_file))

    # ------------------------------------------------------------------
    # Metadata errors
    # ------------------------------------------------------------------

    def test_metadata_not_at_end(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            hub: middle [color=red] 1 0
            end_hub: end 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            MapParser().parse(str(map_file))

    def test_missing_metadata_closing_bracket(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            """
            nb_drones: 2

            start_hub: start 0 0
            hub: middle 1 0 [color=red
            end_hub: end 2 0
            """,
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match="missing closing",
        ):
            MapParser().parse(str(map_file))

    # ------------------------------------------------------------------
    # Line numbers
    # ------------------------------------------------------------------

    def test_error_contains_line_number(
        self,
        tmp_path,
    ) -> None:
        map_file = tmp_path / "map.txt"

        map_file.write_text(
            "nb_drones: 2\n"
            "start_hub: start 0 0\n"
            "hub: middle invalid 0\n"
            "end_hub: end 2 0\n",
            encoding="utf-8",
        )

        with pytest.raises(
            ValueError,
            match=r"Line 3:",
        ):
            MapParser().parse(str(map_file))
