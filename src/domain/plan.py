from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class PlanError(ValueError):
    """Raised when a Plan invariant or transition is violated."""


@dataclass(frozen=True)
class PlanVersion:
    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise PlanError("PlanVersion must be at least 1.")


@dataclass
class Plan:
    version: PlanVersion
    baseline: str | None = None
    work_unit_ids: Tuple[str, ...] = field(default_factory=tuple)
    dependency_ids: Tuple[str, ...] = field(default_factory=tuple)
    priorities: Tuple[str, ...] = field(default_factory=tuple)
    parallel_groups: Tuple[Tuple[str, ...], ...] = field(default_factory=tuple)
    gates: Tuple[str, ...] = field(default_factory=tuple)
    status: PlanStatus = PlanStatus.DRAFT

    def __post_init__(self) -> None:
        if self.baseline is not None and not self.baseline.strip():
            raise PlanError("Plan baseline must not be blank when provided.")

    def activate(self) -> None:
        if self.status is not PlanStatus.DRAFT:
            raise PlanError(
                f"Plan can only be activated from {PlanStatus.DRAFT.value}."
            )
        self.status = PlanStatus.ACTIVE

    def supersede(self) -> None:
        if self.status is not PlanStatus.ACTIVE:
            raise PlanError(
                f"Plan can only be superseded from {PlanStatus.ACTIVE.value}."
            )
        self.status = PlanStatus.SUPERSEDED
