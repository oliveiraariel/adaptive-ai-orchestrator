from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from domain.dependency import Dependency
from domain.work_unit import WorkUnit, WorkUnitState


class ReadinessStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class WorkUnitReadiness:
    work_unit_id: str
    status: ReadinessStatus
    blocking_dependency_ids: tuple[str, ...] = ()


class WorkUnitReadinessEvaluator:
    """Determines whether a Work Unit is eligible to start."""

    ELIGIBLE_STATES = frozenset(
        {
            WorkUnitState.PLANNED,
            WorkUnitState.READY,
            WorkUnitState.REOPENED,
            WorkUnitState.REVISION_REQUIRED,
        }
    )

    def evaluate(
        self,
        work_unit: WorkUnit,
        dependencies: Sequence[Dependency],
    ) -> WorkUnitReadiness:
        blocking_dependencies = tuple(
            f"{dependency.source_id}->{dependency.target_id}"
            for dependency in dependencies
            if dependency.required and not dependency.is_satisfied
        )

        if work_unit.state not in self.ELIGIBLE_STATES:
            return WorkUnitReadiness(
                work_unit_id=work_unit.id.value,
                status=ReadinessStatus.BLOCKED,
                blocking_dependency_ids=blocking_dependencies,
            )

        if blocking_dependencies:
            return WorkUnitReadiness(
                work_unit_id=work_unit.id.value,
                status=ReadinessStatus.BLOCKED,
                blocking_dependency_ids=blocking_dependencies,
            )

        return WorkUnitReadiness(
            work_unit_id=work_unit.id.value,
            status=ReadinessStatus.READY,
        )

    def evaluate_all(
        self,
        work_units: Sequence[WorkUnit],
        dependencies: Sequence[Dependency],
    ) -> tuple[WorkUnitReadiness, ...]:
        dependencies_by_target: dict[str, list[Dependency]] = {
            work_unit.id.value: [] for work_unit in work_units
        }

        for dependency in dependencies:
            if dependency.target_id in dependencies_by_target:
                dependencies_by_target[dependency.target_id].append(dependency)

        return tuple(
            self.evaluate(
                work_unit,
                dependencies_by_target[work_unit.id.value],
            )
            for work_unit in work_units
        )
