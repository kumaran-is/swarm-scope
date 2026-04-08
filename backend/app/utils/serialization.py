"""Snapshot serialization/deserialization utilities."""

import json
from typing import Any


def serialize_snapshot(data: dict[str, Any]) -> str:
    """Serialize a snapshot dict to JSON string."""
    return json.dumps(data, default=str)


def deserialize_snapshot(raw: str) -> dict[str, Any]:
    """Deserialize a JSON string back to a snapshot dict."""
    result: dict[str, Any] = json.loads(raw)
    return result
