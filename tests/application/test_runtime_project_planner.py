import json
from types import SimpleNamespace

import pytest

from application.run_orchestration import RunOrchestrationError
from application.runtime_project_planner import (
    ProjectPlanningError,
    ProjectPlanningRequest,
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
        "scope": "",
        "kind": "EXECUTION",
        "required_capabilities": ["implementation.software"],
        "requested_skills": ["implementation"],
        "tools": [],
        "inputs": [],
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


def test_parse_rejects_json_code_fence_from_runtime() -> None:
    text = "```json\n" + payload([work_unit("a")]) + "\n```"

    with pytest.raises(ProjectPlanningError, match="strict JSON document"):
        RuntimeProjectPlanner.parse(text, max_work_units=2)


def test_parse_rejects_plan_above_work_unit_budget() -> None:
    with pytest.raises(ProjectPlanningError, match="too long"):
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
                    {"source_id": "a", "target_id": "b", "required": True, "condition": None},
                    {"source_id": "b", "target_id": "a", "required": True, "condition": None},
                ],
            ),
            max_work_units=2,
        )


class _CapturingRunner:
    def __init__(self) -> None:
        self.request = None

    def execute(self, request):
        self.request = request
        return SimpleNamespace(output=payload([work_unit("planner-probe")]))


def test_planner_declares_amep_request_and_result_contracts() -> None:
    from application.runtime_project_planner import ProjectPlanningRequest

    runner = _CapturingRunner()
    planner = RuntimeProjectPlanner(
        runner=runner,
        skill_profiles=(),
    )

    plan = planner.plan(
        ProjectPlanningRequest(
            objective="Inspect the project safely.",
            max_work_units=2,
        )
    )

    assert plan.work_units[0].id == "planner-probe"
    assert runner.request is not None
    assert runner.request.request_message_type == "planner.request"
    assert runner.request.request_schema_name == "planner-request"
    assert runner.request.result_message_type == "planner.plan"
    assert runner.request.result_schema_name == "planner-output"
    assert runner.request.result_content_type == "application/json"


def test_parse_rejects_unknown_planner_fields() -> None:
    item = work_unit("a")
    item["unexpected"] = "not in contract"

    with pytest.raises(ProjectPlanningError, match="Additional properties"):
        RuntimeProjectPlanner.parse(payload([item]), max_work_units=2)


class _SequenceRunner:
    def __init__(self, items) -> None:
        self.items = list(items)
        self.calls = 0

    def execute(self, request):
        item = self.items[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(output=item)


def test_planner_retries_once_after_contract_transport_failure() -> None:
    runner = _SequenceRunner(
        [
            RunOrchestrationError(
                "Runtime result retrieval failed: AMEP application/json payload is invalid."
            ),
            payload([work_unit("recovered")]),
        ]
    )
    planner = RuntimeProjectPlanner(runner=runner, skill_profiles=())

    plan = planner.plan(
        ProjectPlanningRequest(objective="Recover a malformed Planner document.")
    )

    assert runner.calls == 2
    assert plan.work_units[0].id == "recovered"


def test_planner_does_not_retry_unrelated_runtime_failure() -> None:
    runner = _SequenceRunner(
        [RunOrchestrationError("Runtime result retrieval failed: credentials unavailable.")]
    )
    planner = RuntimeProjectPlanner(runner=runner, skill_profiles=())

    with pytest.raises(RunOrchestrationError, match="credentials unavailable"):
        planner.plan(ProjectPlanningRequest(objective="Do not mask runtime failures."))

    assert runner.calls == 1
