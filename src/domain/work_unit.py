from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class WorkUnitState(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    BLOCKED = "BLOCKED"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REOPENED = "REOPENED"


class WorkUnitKind(str, Enum):
    EXECUTION = "EXECUTION"
    DECISION = "DECISION"
    RESEARCH = "RESEARCH"
    PROTOTYPE = "PROTOTYPE"
    HUMAN_ACTION = "HUMAN_ACTION"


class WorkUnitStateError(ValueError):
    """Raised when a Work Unit invariant or transition is violated."""


@dataclass(frozen=True)
class WorkUnitId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise WorkUnitStateError("WorkUnitId must not be empty.")


@dataclass
class WorkUnit:
    id: WorkUnitId
    objective: str
    scope: str = ""
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    outputs: Tuple[str, ...] = field(default_factory=tuple)
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    preconditions: Tuple[str, ...] = field(default_factory=tuple)
    required_capabilities: Tuple[str, ...] = field(default_factory=tuple)
    criteria: Tuple[str, ...] = field(default_factory=tuple)
    priority: int = 0
    criticality: int = 0
    state: WorkUnitState = WorkUnitState.PLANNED
    execution_reference: str | None = None
    kind: WorkUnitKind = WorkUnitKind.EXECUTION

    def __post_init__(self) -> None:
        if not self.objective or not self.objective.strip():
            raise WorkUnitStateError("WorkUnit objective must not be empty.")
        if self.priority < 0:
            raise WorkUnitStateError("WorkUnit priority must not be negative.")
        if self.criticality < 0:
            raise WorkUnitStateError("WorkUnit criticality must not be negative.")

    def mark_ready(self) -> None:
        self._transition(
            allowed={WorkUnitState.PLANNED, WorkUnitState.BLOCKED},
            target=WorkUnitState.READY,
        )

    def mark_blocked(self) -> None:
        if self.state in {WorkUnitState.COMPLETED, WorkUnitState.CANCELLED}:
            raise WorkUnitStateError(
                f"WorkUnit cannot be blocked from {self.state.value}."
            )
        self.state = WorkUnitState.BLOCKED

    def start(self) -> None:
        self._transition(
            allowed={WorkUnitState.READY, WorkUnitState.REVISION_REQUIRED, WorkUnitState.REOPENED},
            target=WorkUnitState.RUNNING,
        )

    def start_evaluation(self) -> None:
        self._transition(
            allowed={WorkUnitState.RUNNING},
            target=WorkUnitState.EVALUATING,
        )

    def complete(self) -> None:
        self._transition(
            allowed={WorkUnitState.EVALUATING},
            target=WorkUnitState.COMPLETED,
        )

    def require_revision(self) -> None:
        self._transition(
            allowed={WorkUnitState.EVALUATING},
            target=WorkUnitState.REVISION_REQUIRED,
        )

    def reopen(self) -> None:
        self._transition(
            allowed={WorkUnitState.COMPLETED},
            target=WorkUnitState.REOPENED,
        )

    def cancel(self) -> None:
        if self.state == WorkUnitState.COMPLETED:
            raise WorkUnitStateError("Completed WorkUnit cannot be cancelled.")
        self.state = WorkUnitState.CANCELLED

    def _transition(
        self,
        *,
        allowed: set[WorkUnitState],
        target: WorkUnitState,
    ) -> None:
        if self.state not in allowed:
            allowed_values = ", ".join(sorted(s.value for s in allowed))
            raise WorkUnitStateError(
                f"Invalid WorkUnit transition from {self.state.value} "
                f"to {target.value}. Allowed source states: {allowed_values}."
            )
        self.state = target
