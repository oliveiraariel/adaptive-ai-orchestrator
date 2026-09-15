from __future__ import annotations

from copy import deepcopy
from typing import Any

from application.planner_output_contract import PLANNER_OUTPUT_SCHEMA_V1


_SCHEMA_REGISTRY: dict[tuple[str, str], dict[str, Any]] = {
    ("planner-output", "1"): PLANNER_OUTPUT_SCHEMA_V1,
}


def resolve_message_schema(
    schema_name: str,
    schema_version: str = "1",
) -> dict[str, Any] | None:
    """Return a copy of a registered machine-message schema, when governed."""

    schema = _SCHEMA_REGISTRY.get((schema_name, schema_version))
    return deepcopy(schema) if schema is not None else None
