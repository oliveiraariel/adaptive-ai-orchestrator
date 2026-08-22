from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class ResultPackageError(ValueError):
    """Raised when a ResultPackage invariant is violated."""


class ResultPackageStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True)
class ResultPackage:
    task_id: str
    status: ResultPackageStatus
    result: object | None = None
    artifacts: Tuple[str, ...] = field(default_factory=tuple)
    decisions: Tuple[str, ...] = field(default_factory=tuple)
    assumptions: Tuple[str, ...] = field(default_factory=tuple)
    evidence: Tuple[str, ...] = field(default_factory=tuple)
    discovered_dependencies: Tuple[str, ...] = field(default_factory=tuple)
    discovered_issues: Tuple[str, ...] = field(default_factory=tuple)
    uncertainty: Tuple[str, ...] = field(default_factory=tuple)
    recommendations: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ResultPackageError("ResultPackage task_id must not be empty.")

        if self.status is ResultPackageStatus.SUCCEEDED and self.result is None:
            raise ResultPackageError(
                "A succeeded ResultPackage must contain a result."
            )

        if self.status is ResultPackageStatus.PARTIAL and (
            self.result is None and not self.artifacts
        ):
            raise ResultPackageError(
                "A partial ResultPackage must contain result or artifacts."
            )
