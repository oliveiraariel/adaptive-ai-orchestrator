from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from domain.task_package import TaskPackage


class AgentRuntimeStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentRuntimeError(RuntimeError):
    """Raised when the Agent Runtime seam cannot fulfill its contract."""


@dataclass(frozen=True)
class ExecutionReference:
    id: str
    runtime: str
    external_id: str
    status: AgentRuntimeStatus


@dataclass(frozen=True)
class AgentRuntimeResult:
    execution: ExecutionReference
    raw_result: object | None = None


class AgentRuntime(Protocol):
    """Application seam for delegated execution.

    The contract intentionally describes orchestration concerns rather than
    copying any specific runtime SDK.
    """

    def submit(self, task: TaskPackage) -> ExecutionReference:
        """Submit a task package for execution."""
        ...

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        """Return the current normalized execution status."""
        ...

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        """Retrieve the normalized execution result."""
        ...

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        """Request cancellation of an execution."""
        ...
