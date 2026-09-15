import json

import pytest

from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.run_orchestration import (
    RunOrchestration,
    RunOrchestrationError,
    RunOrchestrationRequest,
)
from domain.evaluation import EvaluationVerdict
from domain.work_unit import WorkUnitState
from infrastructure.claim_registry import InMemoryClaimRegistry


class RecordingObservability:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event_type: str, **fields) -> None:
        self.events.append((event_type, fields))


class FakeRuntime:
    def __init__(self, output: str = "done", usage: dict | None = None) -> None:
        self.output = output
        self.usage = usage

    def submit(self, task):
        return ExecutionReference(
            id=f"execution:{task.task_id}",
            runtime="fake",
            external_id=f"external:{task.task_id}",
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution):
        return AgentRuntimeStatus.COMPLETED

    def retrieve_result(self, execution):
        return AgentRuntimeResult(
            execution=ExecutionReference(
                id=execution.id,
                runtime=execution.runtime,
                external_id=execution.external_id,
                status=AgentRuntimeStatus.COMPLETED,
            ),
            raw_result={"status": "ok", "output": self.output, **({"usage": self.usage} if self.usage else {})},
        )

    def cancel(self, execution):
        return execution

def test_dispatch_returns_reference_without_retrieving_result() -> None:
    runtime = FakeRuntime()
    calls = {"submit": 0, "retrieve": 0}
    original_submit, original_retrieve = runtime.submit, runtime.retrieve_result
    runtime.submit = lambda task: (calls.__setitem__("submit", calls["submit"] + 1), original_submit(task))[1]
    runtime.retrieve_result = lambda execution: (calls.__setitem__("retrieve", calls["retrieve"] + 1), original_retrieve(execution))[1]
    result = RunOrchestration(runtime=runtime, claim_registry=InMemoryClaimRegistry()).dispatch(RunOrchestrationRequest(objective="Dispatch only."))
    assert result.execution.external_id
    assert calls == {"submit": 1, "retrieve": 0}


def test_run_orchestration_completes_governed_work_unit() -> None:
    claims = InMemoryClaimRegistry()
    observability = RecordingObservability()
    result = RunOrchestration(
        runtime=FakeRuntime(),
        claim_registry=claims,
        observability=observability,
    ).execute(
        RunOrchestrationRequest(
            objective="Return a bounded result.",
        )
    )

    assert result.runtime_status is AgentRuntimeStatus.COMPLETED
    assert result.work_unit_state is WorkUnitState.COMPLETED
    assert result.verdict is EvaluationVerdict.ACCEPTED
    assert result.output == "done"
    assert result.evidence == ("runtime-completed",)
    assert claims.get(result.work_unit_id) is None
    assert observability.events[-1] == (
        "orchestration_completed",
        {"orchestration_id": result.task_id.removeprefix("task:"), "status": "COMPLETED", "verdict": "ACCEPTED"},
    )


def test_run_orchestration_evaluates_explicit_output_criterion() -> None:
    result = RunOrchestration(
        runtime=FakeRuntime(output="EXPECTED_RESULT"),
        claim_registry=InMemoryClaimRegistry(),
    ).execute(
        RunOrchestrationRequest(
            objective="Return the expected marker.",
            acceptance_criteria=("EXPECTED_RESULT",),
        )
    )

    assert result.verdict is EvaluationVerdict.ACCEPTED
    assert result.work_unit_state is WorkUnitState.COMPLETED


def test_run_orchestration_publishes_usage_on_terminal_event() -> None:
    observability = RecordingObservability()
    RunOrchestration(
        runtime=FakeRuntime(usage={"prompt_tokens": 7, "completion_tokens": 3}),
        claim_registry=InMemoryClaimRegistry(),
        observability=observability,
    ).execute(RunOrchestrationRequest(objective="Report usage."))
    evaluation = next(fields for event, fields in observability.events if event == "evaluation_finalized")
    assert evaluation["usage"] == {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}


def test_run_orchestration_blocks_unauthorized_side_effect() -> None:
    observability = RecordingObservability()
    runner = RunOrchestration(
        runtime=FakeRuntime(),
        claim_registry=InMemoryClaimRegistry(),
        observability=observability,
    )

    with pytest.raises(RunOrchestrationError, match="policy:DENY"):
        runner.execute(
            RunOrchestrationRequest(
                objective="Attempt a write.",
                requested_side_effects=("filesystem-write",),
            )
        )

    assert observability.events[-1][0] == "orchestration_completed"
    assert observability.events[-1][1]["status"] == "BLOCKED"
    assert observability.events[-1][1]["failure_category"] == "dispatch"


class FailingResultRuntime(FakeRuntime):
    def retrieve_result(self, execution):
        raise RuntimeError("transport interrupted")


def test_run_orchestration_emits_terminal_failure_on_runtime_result_error() -> None:
    observability = RecordingObservability()
    runner = RunOrchestration(
        runtime=FailingResultRuntime(),
        claim_registry=InMemoryClaimRegistry(),
        observability=observability,
    )

    with pytest.raises(RunOrchestrationError, match="Runtime result retrieval failed"):
        runner.execute(RunOrchestrationRequest(objective="Fail after dispatch."))

    terminal = [
        fields
        for event_type, fields in observability.events
        if event_type == "orchestration_completed"
    ]
    assert len(terminal) == 1
    assert terminal[0]["status"] == "FAILED"
    assert terminal[0]["failure_category"] == "runtime"
    assert terminal[0]["failure_code"] == "runtime_result_retrieval_failed"


def _planner_output_text() -> str:
    return json.dumps(
        {
            "summary": "one safe unit",
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
    )


def test_run_orchestration_accepts_governed_planner_schema() -> None:
    result = RunOrchestration(
        runtime=FakeRuntime(output=_planner_output_text()),
        claim_registry=InMemoryClaimRegistry(),
    ).execute(
        RunOrchestrationRequest(
            objective="Produce a Planner result.",
            result_schema_name="planner-output",
            result_content_type="application/json",
        )
    )

    assert json.loads(result.output)["work_units"][0]["id"] == "inspect"


def test_run_orchestration_rejects_invalid_governed_planner_schema() -> None:
    observability = RecordingObservability()
    claims = InMemoryClaimRegistry()
    runner = RunOrchestration(
        runtime=FakeRuntime(output='{"summary":"missing work graph"}'),
        claim_registry=claims,
        observability=observability,
    )

    with pytest.raises(RunOrchestrationError, match="RESULT_SCHEMA_VALIDATION_FAILED"):
        runner.execute(
            RunOrchestrationRequest(
                objective="Produce a Planner result.",
                result_schema_name="planner-output",
                result_content_type="application/json",
            )
        )

    terminal = [
        fields
        for event_type, fields in observability.events
        if event_type == "orchestration_completed"
    ]
    assert terminal[-1]["status"] == "FAILED"
    assert terminal[-1]["failure_category"] == "contract"
    assert terminal[-1]["failure_code"] == "result_schema_validation_failed"
