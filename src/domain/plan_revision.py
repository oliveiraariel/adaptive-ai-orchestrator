from dataclasses import dataclass, field
from typing import Tuple

from domain.plan import Plan


class PlanRevisionError(ValueError):
    """Raised when a PlanRevision invariant is violated."""


@dataclass(frozen=True)
class PlanRevision:
    previous_version: int
    new_plan: Plan
    trigger: str
    affected_work_unit_ids: Tuple[str, ...] = field(default_factory=tuple)
    changes: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.previous_version < 1:
            raise PlanRevisionError("Previous plan version must be at least 1.")

        if not self.trigger.strip():
            raise PlanRevisionError("Plan revision trigger must not be empty.")

        if self.new_plan.version.value <= self.previous_version:
            raise PlanRevisionError(
                "New plan version must be greater than the previous version."
            )
