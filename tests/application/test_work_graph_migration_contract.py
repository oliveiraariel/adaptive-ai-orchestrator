from __future__ import annotations

import json
from pathlib import Path

import pytest

from application.structured_output_contract import (
    StructuredOutputContractError,
    validate_structured_json,
)
from application.work_graph_migration_contract import (
    WORK_GRAPH_MIGRATION_SCHEMA_V1,
    work_graph_migration_schema,
)


def _valid_migration() -> dict:
    return {
        "schema_version": "work-graph-migration/1",
        "migration_id": "m1",
        "reason": "restore granularity",
        "work_units": [
            {
                "id": "WU-A-01",
                "objective": "Do A",
                "role": "worker",
                "scope": "",
                "kind": "EXECUTION",
                "required_capabilities": [],
                "requested_skills": [],
                "tools": [],
                "inputs": [],
                "expected_output": ["agent response"],
                "acceptance_criteria": ["runtime-completed"],
                "requested_side_effects": [],
                "write_paths": [],
                "priority": 0,
                "criticality": 0,
                "parallel_safe": True,
                "initial_state": "PLANNED",
                "evidence_lineage": [],
            }
        ],
        "dependencies": [],
        "resume_recovery_targets": [],
        "consume_pending_replan": False,
    }


def test_runtime_migration_contract_matches_versioned_specification() -> None:
    root = Path(__file__).resolve().parents[2]
    documented = json.loads(
        (
            root
            / "specifications/protocols/work-graph-migration-v1.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert documented == WORK_GRAPH_MIGRATION_SCHEMA_V1


def test_run_specific_migration_schema_enforces_new_work_unit_budget() -> None:
    migration = _valid_migration()
    migration["work_units"].append(
        {**migration["work_units"][0], "id": "WU-A-02"}
    )

    with pytest.raises(StructuredOutputContractError, match="too long"):
        validate_structured_json(
            json.dumps(migration),
            work_graph_migration_schema(1),
        )
