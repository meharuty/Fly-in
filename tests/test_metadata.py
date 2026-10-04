import pytest

from src.parser.metadata import MetadataParser


class TestMetadataParser:

    def test_parse_valid_metadata(self) -> None:
        metadata = MetadataParser.parse(
            "[zone=normal color=red max_drones=3]"
        )

        assert metadata == {
            "zone": "normal",
            "color": "red",
            "max_drones": "3",
        }

    def test_parse_empty_metadata(self) -> None:
        metadata = MetadataParser.parse("[]")

        assert metadata == {}

    def test_parse_metadata_without_brackets(self) -> None:
        with pytest.raises(
            ValueError,
            match="Metadata must be enclosed in brackets",
        ):
            MetadataParser.parse("zone=normal")

    def test_parse_metadata_missing_value(self) -> None:
        with pytest.raises(
            ValueError,
            match="Metadata value cannot be empty",
        ):
            MetadataParser.parse("[zone=]")

    def test_parse_metadata_missing_key(self) -> None:
        with pytest.raises(
            ValueError,
            match="Metadata key cannot be empty",
        ):
            MetadataParser.parse("[=normal]")

    def test_parse_metadata_multiple_equals(self) -> None:
        with pytest.raises(
            ValueError,
            match="Invalid metadata format",
        ):
            MetadataParser.parse("[zone=normal=wrong]")

    def test_parse_metadata_without_equals(self) -> None:
        with pytest.raises(
            ValueError,
            match="Invalid metadata format",
        ):
            MetadataParser.parse("[zone]")

    def test_parse_duplicate_metadata_key(self) -> None:
        with pytest.raises(
            ValueError,
            match="Duplicate metadata key",
        ):
            MetadataParser.parse(
                "[color=red color=blue]"
            )

    def test_known_metadata_keys(self) -> None:
        metadata = {
            "zone": "normal",
            "color": "red",
        }

        MetadataParser.ensure_known_keys(
            metadata,
            {"zone", "color"},
            "a hub",
        )

    def test_unknown_metadata_key(self) -> None:
        metadata = {
            "zoen": "normal",
        }

        with pytest.raises(
            ValueError,
            match="Unknown metadata key",
        ):
            MetadataParser.ensure_known_keys(
                metadata,
                {"zone", "color"},
                "a hub",
            )
