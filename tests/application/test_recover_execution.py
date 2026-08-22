from dataclasses import dataclass

from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.recover_execution import (
    RecoverExecution,
    RecoveryAction,
    RecoveryRequest,
)
from domain.work_unit import WorkUnit, WorkUnitId


@dataclass
class FakeRuntime:
    status: AgentRuntimeStatus = AgentRuntimeStatus.FAILED

    def submit(self, task):
        raise NotImplementedError

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return self.status

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        raise NotImplementedError

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        raise NotImplementedError


def make_request(reason: str) -> RecoveryRequest:
    return RecoveryRequest(
        work_unit=WorkUnit(
            id=WorkUnitId("wu-001"),
            objective="Recover a failed execution.",
        ),
        execution=ExecutionReference(
            id="execution-001",
            runtime="fake-runtime",
            external_id="external-001",
            status=AgentRuntimeStatus.FAILED,
        ),
        failure_reason=reason,
    )


def test_transient_failure_can_retry() -> None:
    result = RecoverExecution(FakeRuntime()).execute(
        make_request("temporary timeout from runtime")
    )

    assert result.action is RecoveryAction.RETRY


def test_model_or_quality_failure_can_reselect_resource() -> None:
    result = RecoverExecution(FakeRuntime()).execute(
        make_request("model quality was insufficient")
    )

    assert result.action is RecoveryAction.RESELECT_RESOURCE


def test_dependency_failure_can_trigger_replanning() -> None:
    result = RecoverExecution(FakeRuntime()).execute(
        make_request("new dependency invalidated the current plan")
    )

    assert result.action is RecoveryAction.REPLAN


def test_unknown_failure_is_escalated() -> None:
    result = RecoverExecution(FakeRuntime()).execute(
        make_request("unclassified execution problem")
    )

    assert result.action is RecoveryAction.ESCALATE


def test_recovery_stops_when_execution_is_not_failed() -> None:
    runtime = FakeRuntime(status=AgentRuntimeStatus.COMPLETED)

    result = RecoverExecution(runtime).execute(
        make_request("temporary timeout")
    )

    assert result.action is RecoveryAction.STOP


def test_failure_reason_is_required() -> None:
    request = make_request("")

    try:
        RecoverExecution(FakeRuntime()).execute(request)
    except ValueError as exc:
        assert "Failure reason" in str(exc)
    else:
        raise AssertionError("Expected failure reason validation.")
