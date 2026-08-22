from dataclasses import dataclass, field
from typing import Tuple

from domain.resource_configuration import ResourceConfiguration


class TaskPackageError(ValueError):
    """Raised when a TaskPackage invariant is violated."""


@dataclass(frozen=True)
class TaskPackage:
    task_id: str
    work_unit_id: str
    objective: str
    scope: str = ""
    context: Tuple[str, ...] = field(default_factory=tuple)
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    artifacts: Tuple[str, ...] = field(default_factory=tuple)
    decisions: Tuple[str, ...] = field(default_factory=tuple)
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    constraints: Tuple[str, ...] = field(default_factory=tuple)
    configuration: ResourceConfiguration | None = None
    expected_output: Tuple[str, ...] = field(default_factory=tuple)
    acceptance_criteria: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise TaskPackageError("TaskPackage task_id must not be empty.")

        if not self.work_unit_id.strip():
            raise TaskPackageError("TaskPackage work_unit_id must not be empty.")

        if not self.objective.strip():
            raise TaskPackageError("TaskPackage objective must not be empty.")

        if self.configuration is None:
            raise TaskPackageError(
                "TaskPackage configuration is required before delegation."
            )

        if not self.expected_output:
            raise TaskPackageError(
                "TaskPackage must declare at least one expected output."
            )

        if not self.acceptance_criteria:
            raise TaskPackageError(
                "TaskPackage must declare at least one acceptance criterion."
            )
