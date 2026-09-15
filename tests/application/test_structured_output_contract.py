import json
from pathlib import Path

import pytest

from application.planner_output_contract import (
    PLANNER_OUTPUT_SCHEMA_V1,
    planner_output_schema,
)
from application.structured_output_contract import (
    StructuredOutputContractError,
    validate_structured_json,
)


def _valid_plan() -> dict:
    return {
        "summary": "bounded plan",
        "work_units": [
            {
                "id": "inspect",
                "objective": "Inspect safely",
                "role": "reviewer",
                "scope": "",
                "kind": "RESEARCH",
                "required_capabilities": [],
                "requested_skills": [],
                "tools": [],
                "inputs": [],
                "expected_output": ["evidence"],
                "acceptance_criteria": ["runtime-completed"],
                "requested_side_effects": [],
                "write_paths": [],
                "priority": 1,
                "criticality": 0,
                "parallel_safe": True,
            }
        ],
        "dependencies": [],
    }


def test_validate_structured_json_returns_canonical_document() -> None:
    raw = json.dumps(_valid_plan(), indent=2)

    payload, canonical = validate_structured_json(raw, planner_output_schema(4))

    assert payload["work_units"][0]["id"] == "inspect"
    assert canonical == json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def test_validate_structured_json_rejects_prose_wrapping() -> None:
    raw = "Here is the plan:\n" + json.dumps(_valid_plan())

    with pytest.raises(StructuredOutputContractError, match="strict JSON document"):
        validate_structured_json(raw, planner_output_schema(4))


def test_validate_structured_json_rejects_schema_violation() -> None:
    raw = _valid_plan()
    raw["work_units"][0]["parallel_safe"] = "yes"

    with pytest.raises(StructuredOutputContractError, match="violates schema"):
        validate_structured_json(json.dumps(raw), planner_output_schema(4))


def test_runtime_planner_contract_matches_versioned_specification() -> None:
    root = Path(__file__).resolve().parents[2]
    documented = json.loads(
        (root / "specifications/protocols/planner-output-v1.schema.json").read_text()
    )

    assert documented == PLANNER_OUTPUT_SCHEMA_V1


def test_run_specific_schema_enforces_work_unit_budget() -> None:
    schema = planner_output_schema(1)
    plan = _valid_plan()
    plan["work_units"].append({**plan["work_units"][0], "id": "second"})

    with pytest.raises(StructuredOutputContractError, match="too long"):
        validate_structured_json(json.dumps(plan), schema)
