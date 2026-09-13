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
    runner = RunOrchestration(
        runtime=FakeRuntime(),
        claim_registry=InMemoryClaimRegistry(),
    )

    with pytest.raises(RunOrchestrationError, match="policy:DENY"):
        runner.execute(
            RunOrchestrationRequest(
                objective="Attempt a write.",
                requested_side_effects=("filesystem-write",),
            )
        )
