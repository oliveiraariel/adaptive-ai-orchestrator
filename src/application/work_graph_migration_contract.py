from __future__ import annotations

from copy import deepcopy
from typing import Any


_NON_EMPTY_STRING: dict[str, Any] = {"type": "string", "minLength": 1}
_STRING_ARRAY: dict[str, Any] = {
    "type": "array",
    "items": _NON_EMPTY_STRING,
}

WORK_GRAPH_MIGRATION_SCHEMA_V1: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://adaptive.local/schemas/work-graph-migration-v1.schema.json",
    "title": "Adaptive Work Graph Migration v1",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "migration_id",
        "reason",
        "work_units",
        "dependencies",
        "resume_recovery_targets",
        "consume_pending_replan",
    ],
    "properties": {
        "schema_version": {"const": "work-graph-migration/1"},
        "migration_id": _NON_EMPTY_STRING,
        "reason": _NON_EMPTY_STRING,
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
                    "initial_state",
                    "evidence_lineage",
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
                    "expected_output": {**_STRING_ARRAY, "minItems": 1},
                    "acceptance_criteria": {**_STRING_ARRAY, "minItems": 1},
                    "requested_side_effects": _STRING_ARRAY,
                    "write_paths": _STRING_ARRAY,
                    "priority": {"type": "integer", "minimum": 0},
                    "criticality": {"type": "integer", "minimum": 0},
                    "parallel_safe": {"type": "boolean"},
                    "reconciles_work_unit_id": {
                        "type": ["string", "null"],
                        "minLength": 1,
                    },
                    "initial_state": {
                        "type": "string",
                        "enum": ["PLANNED", "COMPLETED"],
                    },
                    "evidence_lineage": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "source_work_unit_id",
                                "result_ref",
                                "note",
                            ],
                            "properties": {
                                "source_work_unit_id": _NON_EMPTY_STRING,
                                "result_ref": {
                                    "type": ["string", "null"],
                                    "minLength": 1,
                                },
                                "note": {"type": "string"},
                            },
                        },
                    },
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
        "resume_recovery_targets": _STRING_ARRAY,
        "consume_pending_replan": {"type": "boolean"},
    },
}


def work_graph_migration_schema(max_new_work_units: int) -> dict[str, Any]:
    if isinstance(max_new_work_units, bool) or not isinstance(max_new_work_units, int):
        raise ValueError("max_new_work_units must be an integer.")
    if max_new_work_units < 1:
        raise ValueError("max_new_work_units must be at least 1.")

    schema = deepcopy(WORK_GRAPH_MIGRATION_SCHEMA_V1)
    schema["properties"]["work_units"]["maxItems"] = max_new_work_units
    return schema
