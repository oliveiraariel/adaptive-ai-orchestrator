from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class ProjectStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"


class ProjectStateError(ValueError):
    """Raised when a Project invariant would be violated."""


@dataclass(frozen=True)
class ProjectId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ProjectStateError("ProjectId must not be empty.")


@dataclass
class Project:
    id: ProjectId
    identity: str
    objectives: Tuple[str, ...] = field(default_factory=tuple)
    requirements: Tuple[str, ...] = field(default_factory=tuple)
    constraints: Tuple[str, ...] = field(default_factory=tuple)
    decisions: Tuple[str, ...] = field(default_factory=tuple)
    baseline: str | None = None
    work_unit_ids: Tuple[str, ...] = field(default_factory=tuple)
    dependency_ids: Tuple[str, ...] = field(default_factory=tuple)
    risks: Tuple[str, ...] = field(default_factory=tuple)
    status: ProjectStatus = ProjectStatus.INITIALIZING

    def __post_init__(self) -> None:
        if not self.identity or not self.identity.strip():
            raise ProjectStateError("Project identity must not be empty.")

    def activate(self) -> None:
        if self.status not in {
            ProjectStatus.INITIALIZING,
            ProjectStatus.SUSPENDED,
        }:
            raise ProjectStateError(
                f"Project cannot be activated from {self.status.value}."
            )
        self.status = ProjectStatus.ACTIVE

    def complete(self) -> None:
        if self.status != ProjectStatus.ACTIVE:
            raise ProjectStateError(
                f"Project can only be completed from {ProjectStatus.ACTIVE.value}."
            )
        self.status = ProjectStatus.COMPLETED

    def block(self) -> None:
        if self.status == ProjectStatus.COMPLETED:
            raise ProjectStateError("Completed project cannot be blocked.")
        self.status = ProjectStatus.BLOCKED

    def suspend(self) -> None:
        if self.status != ProjectStatus.ACTIVE:
            raise ProjectStateError(
                f"Project can only be suspended from {ProjectStatus.ACTIVE.value}."
            )
        self.status = ProjectStatus.SUSPENDED
