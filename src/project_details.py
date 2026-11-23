"""Formatting helpers for displaying project details."""


def split_items(value: str) -> list[str]:
    """Split pipe-separated dataset fields into clean list items."""
    if not value:
        return []

    return [item.strip() for item in str(value).split("|") if item.strip()]
