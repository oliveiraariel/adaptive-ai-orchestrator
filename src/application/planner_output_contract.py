from __future__ import annotations

from copy import deepcopy
from typing import Any


_NON_EMPTY_STRING: dict[str, Any] = {"type": "string", "minLength": 1}
_STRING_ARRAY: dict[str, Any] = {
    "type": "array",
    "items": _NON_EMPTY_STRING,
}

PLANNER_OUTPUT_SCHEMA_V1: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://adaptive.local/schemas/planner-output-v1.schema.json",
    "title": "Adaptive Planner Output v1",
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "work_units", "dependencies"],
    "properties": {
        "summary": _NON_EMPTY_STRING,
        "work_units": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "objective",
                    "role",
                    "scope",
                    "kind",
                    "required_capabilities",
                    "requested_skills",
                    "tools",
                    "inputs",
                    "expected_output",
                    "acceptance_criteria",
                    "requested_side_effects",
                    "write_paths",
                    "priority",
                    "criticality",
                    "parallel_safe",
                ],
                "properties": {
                    "id": _NON_EMPTY_STRING,
                    "objective": _NON_EMPTY_STRING,
                    "role": _NON_EMPTY_STRING,
                    "scope": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "EXECUTION",
                            "DECISION",
                            "RESEARCH",
                            "PROTOTYPE",
                            "HUMAN_ACTION",
                        ],
                    },
                    "required_capabilities": _STRING_ARRAY,
                    "requested_skills": _STRING_ARRAY,
                    "tools": _STRING_ARRAY,
                    "inputs": _STRING_ARRAY,
                    "expected_output": {
                        **_STRING_ARRAY,
                        "minItems": 1,
                    },
                    "acceptance_criteria": {
                        **_STRING_ARRAY,
                        "minItems": 1,
                    },
                    "requested_side_effects": _STRING_ARRAY,
                    "write_paths": _STRING_ARRAY,
                    "priority": {"type": "integer", "minimum": 0},
                    "criticality": {"type": "integer", "minimum": 0},
                    "parallel_safe": {"type": "boolean"},
                },
            },
        },
        "dependencies": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_id",
                    "target_id",
                    "required",
                    "condition",
                ],
                "properties": {
                    "source_id": _NON_EMPTY_STRING,
                    "target_id": _NON_EMPTY_STRING,
                    "required": {"type": "boolean"},
                    "condition": {"type": ["string", "null"]},
                },
            },
        },
    },
}


def planner_output_schema(max_work_units: int) -> dict[str, Any]:
    """Return the canonical Planner v1 schema with the run-specific work limit."""

    if isinstance(max_work_units, bool) or not isinstance(max_work_units, int):
        raise ValueError("max_work_units must be an integer.")
    if max_work_units < 1:
        raise ValueError("max_work_units must be at least 1.")

    schema = deepcopy(PLANNER_OUTPUT_SCHEMA_V1)
    schema["properties"]["work_units"]["maxItems"] = max_work_units
    return schema
