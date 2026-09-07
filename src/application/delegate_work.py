from dataclasses import dataclass

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeStatus,
    ExecutionReference,
)
from domain.execution_policy import PolicyDecision
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitKind, WorkUnitState


class DelegateWorkError(RuntimeError):
    """Raised when a Work Unit cannot be delegated."""


@dataclass(frozen=True)
class DelegateWorkRequest:
    work_unit: WorkUnit
    configuration: ResourceConfiguration
    task_package: TaskPackage
    human_approved: bool = False


@dataclass(frozen=True)
class DelegateWorkResult:
    execution: ExecutionReference


class DelegateWork:
    """Coordinates delegation without exposing runtime-specific details."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    def execute(self, request: DelegateWorkRequest) -> DelegateWorkResult:
        self._validate(request)

        self._ensure_ready_for_execution(request.work_unit)
        self._ensure_task_matches(request)
        self._ensure_agent_delegable_kind(request.work_unit)
        self._ensure_policy_allows_delegation(request)

        execution = self._runtime.submit(request.task_package)

        if execution.status not in {
            AgentRuntimeStatus.SUBMITTED,
            AgentRuntimeStatus.RUNNING,
        }:
            raise DelegateWorkError(
                "Runtime did not accept the delegated execution."
            )

        request.work_unit.execution_reference = execution.id
        request.work_unit.start()

        return DelegateWorkResult(execution=execution)

    @staticmethod
    def _validate(request: DelegateWorkRequest) -> None:
        if request.task_package.work_unit_id != request.work_unit.id.value:
            raise DelegateWorkError(
                "TaskPackage does not reference the supplied Work Unit."
            )

        task_configuration = request.task_package.configuration

        if task_configuration != request.configuration:
            raise DelegateWorkError(
                "TaskPackage configuration does not match the selected configuration."
            )

    @staticmethod
    def _ensure_ready_for_execution(work_unit: WorkUnit) -> None:
        if work_unit.state not in {
            WorkUnitState.READY,
            WorkUnitState.REVISION_REQUIRED,
            WorkUnitState.REOPENED,
        }:
            raise DelegateWorkError(
                f"Work Unit cannot be delegated from state "
                f"{work_unit.state.value}."
            )

    @staticmethod
    def _ensure_task_matches(request: DelegateWorkRequest) -> None:
        if request.task_package.objective != request.work_unit.objective:
            raise DelegateWorkError(
                "TaskPackage objective does not match the Work Unit objective."
            )

    @staticmethod
    def _ensure_agent_delegable_kind(work_unit: WorkUnit) -> None:
        if work_unit.kind is WorkUnitKind.HUMAN_ACTION:
            raise DelegateWorkError(
                "HUMAN_ACTION Work Units cannot be delegated to an agent runtime."
            )

    @staticmethod
    def _ensure_policy_allows_delegation(request: DelegateWorkRequest) -> None:
        decision = request.task_package.execution_policy.decide(
            human_approved=request.human_approved,
            requested_side_effects=request.task_package.requested_side_effects,
            requested_tools=request.configuration.tools,
        )

        if decision is PolicyDecision.ALLOW:
            return

        if decision is PolicyDecision.REQUIRE_HUMAN_APPROVAL:
            raise DelegateWorkError(
                "Delegation requires explicit human approval before execution."
            )

        if decision is PolicyDecision.REQUIRE_HUMAN_EXECUTION:
            raise DelegateWorkError(
                "This Work Unit requires human execution and cannot be delegated "
                "to an agent."
            )

        raise DelegateWorkError("Execution policy denied agent delegation.")
