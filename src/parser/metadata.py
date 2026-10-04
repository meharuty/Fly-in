class MetadataParser:
    """Parse optional [key=value ...] metadata blocks."""

    @staticmethod
    def parse(metadata_text: str) -> dict[str, str]:
        """Parse a metadata block into a dictionary."""

        text = metadata_text.strip()

        if not text.startswith("[") or not text.endswith("]"):
            raise ValueError(
                "Metadata must be enclosed in brackets"
            )

        content = text[1:-1].strip()

        if not content:
            return {}

        metadata: dict[str, str] = {}

        for item in content.split():
            if item.count("=") != 1:
                raise ValueError(
                    f"Invalid metadata format: '{item}'. "
                    "Expected key=value"
                )

            key, value = item.split("=", maxsplit=1)

            if not key:
                raise ValueError(
                    f"Invalid metadata format: '{item}'. "
                    "Metadata key cannot be empty"
                )

            if not value:
                raise ValueError(
                    f"Invalid metadata format: '{item}'. "
                    "Metadata value cannot be empty"
                )

            if key in metadata:
                raise ValueError(
                    f"Duplicate metadata key: '{key}'"
                )

            metadata[key] = value

        return metadata

    @staticmethod
    def ensure_known_keys(
        metadata: dict[str, str],
        allowed: set[str],
        context: str,
    ) -> None:
        """Raise if metadata contains unsupported keys."""
        unknown_keys = set(metadata) - allowed

        if not unknown_keys:
            return

        unknown_list = ", ".join(sorted(unknown_keys))
        allowed_list = ", ".join(sorted(allowed))

        raise ValueError(
            f"Unknown metadata key(s) for {context}: "
            f"{unknown_list}. Allowed: {allowed_list}"
        )
