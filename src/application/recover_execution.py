from dataclasses import dataclass
from enum import Enum

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeStatus,
    ExecutionReference,
)
from domain.work_unit import WorkUnit, WorkUnitState


class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    RESELECT_RESOURCE = "RESELECT_RESOURCE"
    REPLAN = "REPLAN"
    ESCALATE = "ESCALATE"
    STOP = "STOP"


@dataclass(frozen=True)
class RecoveryRequest:
    work_unit: WorkUnit
    execution: ExecutionReference
    failure_reason: str


@dataclass(frozen=True)
class RecoveryResult:
    action: RecoveryAction
    execution: ExecutionReference
    reason: str


class RecoverExecution:
    """Classifies execution failures into a bounded recovery action."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    def execute(self, request: RecoveryRequest) -> RecoveryResult:
        if not request.failure_reason.strip():
            raise ValueError("Failure reason must not be empty.")

        status = self._runtime.get_status(request.execution)

        if status is not AgentRuntimeStatus.FAILED:
            return RecoveryResult(
                action=RecoveryAction.STOP,
                execution=request.execution,
                reason=(
                    "Recovery was not started because the execution is not "
                    "currently failed."
                ),
            )

        reason = request.failure_reason.lower()

        if any(
            marker in reason
            for marker in (
                "timeout",
                "temporary",
                "transient",
                "rate limit",
            )
        ):
            return RecoveryResult(
                action=RecoveryAction.RETRY,
                execution=request.execution,
                reason="Failure classified as potentially transient.",
            )

        if any(
            marker in reason
            for marker in (
                "model",
                "quality",
                "capability",
                "skill",
            )
        ):
            return RecoveryResult(
                action=RecoveryAction.RESELECT_RESOURCE,
                execution=request.execution,
                reason="Failure suggests resource/configuration insufficiency.",
            )

        if any(
            marker in reason
            for marker in (
                "dependency",
                "requirement",
                "scope",
                "changed",
            )
        ):
            return RecoveryResult(
                action=RecoveryAction.REPLAN,
                execution=request.execution,
                reason="Failure suggests the current plan may no longer be valid.",
            )

        return RecoveryResult(
            action=RecoveryAction.ESCALATE,
            execution=request.execution,
            reason="Failure cause is not safely classifiable automatically.",
        )
