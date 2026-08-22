from dataclasses import dataclass
from enum import Enum


class DependencyType(str, Enum):
    COMPLETION = "COMPLETION"
    AVAILABILITY = "AVAILABILITY"


class DependencyStatus(str, Enum):
    BLOCKED = "BLOCKED"
    SATISFIED = "SATISFIED"


class DependencyError(ValueError):
    """Raised when a dependency invariant is violated."""


@dataclass
class Dependency:
    source_id: str
    target_id: str
    type: DependencyType = DependencyType.COMPLETION
    required: bool = True
    condition: str | None = None
    status: DependencyStatus = DependencyStatus.BLOCKED

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise DependencyError("Dependency source_id must not be empty.")
        if not self.target_id.strip():
            raise DependencyError("Dependency target_id must not be empty.")
        if self.source_id == self.target_id:
            raise DependencyError("A dependency cannot target itself.")

    def satisfy(self) -> None:
        self.status = DependencyStatus.SATISFIED

    def block(self) -> None:
        self.status = DependencyStatus.BLOCKED

    @property
    def is_satisfied(self) -> bool:
        return self.status is DependencyStatus.SATISFIED

    @property
    def is_blocking(self) -> bool:
        return self.required and not self.is_satisfied
