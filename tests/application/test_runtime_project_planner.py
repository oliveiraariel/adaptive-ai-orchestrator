import json

import pytest

from application.runtime_project_planner import (
    ProjectPlanningError,
    RuntimeProjectPlanner,
)


def payload(work_units: list[dict], dependencies: list[dict] | None = None) -> str:
    return json.dumps(
        {
            "summary": "test plan",
            "work_units": work_units,
            "dependencies": dependencies or [],
        }
    )


def work_unit(unit_id: str) -> dict:
    return {
        "id": unit_id,
        "objective": f"Execute {unit_id}",
        "role": "worker",
        "kind": "EXECUTION",
        "required_capabilities": ["implementation.software"],
        "requested_skills": ["implementation"],
        "expected_output": ["result"],
        "acceptance_criteria": ["runtime-completed"],
        "requested_side_effects": [],
        "write_paths": [],
        "priority": 1,
        "criticality": 0,
        "parallel_safe": True,
    }


def test_parse_accepts_strict_json_and_preserves_parallel_metadata() -> None:
    plan = RuntimeProjectPlanner.parse(
        payload([work_unit("backend"), work_unit("frontend")]),
        max_work_units=4,
    )

    assert [item.id for item in plan.work_units] == ["backend", "frontend"]
    assert all(item.parallel_safe for item in plan.work_units)


def test_parse_accepts_json_code_fence_from_runtime() -> None:
    text = "```json\n" + payload([work_unit("a")]) + "\n```"

    plan = RuntimeProjectPlanner.parse(text, max_work_units=2)

    assert plan.work_units[0].id == "a"


def test_parse_rejects_plan_above_work_unit_budget() -> None:
    with pytest.raises(ProjectPlanningError, match="limit"):
        RuntimeProjectPlanner.parse(
            payload([work_unit("a"), work_unit("b")]),
            max_work_units=1,
        )


def test_parse_rejects_malformed_write_paths() -> None:
    malformed = work_unit("a")
    malformed["write_paths"] = [""]

    with pytest.raises(ProjectPlanningError, match="write_paths"):
        RuntimeProjectPlanner.parse(payload([malformed]), max_work_units=2)


def test_parse_rejects_required_dependency_cycle() -> None:
    with pytest.raises(ProjectPlanningError, match="acyclic"):
        RuntimeProjectPlanner.parse(
            payload(
                [work_unit("a"), work_unit("b")],
                [
                    {"source_id": "a", "target_id": "b", "required": True},
                    {"source_id": "b", "target_id": "a", "required": True},
                ],
            ),
            max_work_units=2,
        )
