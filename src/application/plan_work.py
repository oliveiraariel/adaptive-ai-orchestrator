from dataclasses import dataclass
from typing import Sequence

from domain.dependency import Dependency
from domain.plan import Plan, PlanVersion
from domain.project import Project
from domain.work_unit import WorkUnit, WorkUnitState


@dataclass(frozen=True)
class PlanWorkRequest:
    project: Project
    work_units: Sequence[WorkUnit]
    dependencies: Sequence[Dependency]
    version: int = 1


@dataclass(frozen=True)
class PlanWorkResult:
    plan: Plan
    ready_work_unit_ids: tuple[str, ...]
    blocked_work_unit_ids: tuple[str, ...]


class PlanWork:
    """Builds a minimal execution plan from current project state."""

    def execute(self, request: PlanWorkRequest) -> PlanWorkResult:
        self._validate(request)

        work_units_by_id = {work_unit.id.value: work_unit for work_unit in request.work_units}

        required_dependencies = {
            work_unit_id: []
            for work_unit_id in work_units_by_id
        }

        for dependency in request.dependencies:
            if dependency.target_id in required_dependencies and dependency.required:
                required_dependencies[dependency.target_id].append(dependency)

        ready_ids: list[str] = []
        blocked_ids: list[str] = []

        for work_unit in request.work_units:
            if self._is_ready(work_unit, required_dependencies[work_unit.id.value]):
                ready_ids.append(work_unit.id.value)
            else:
                blocked_ids.append(work_unit.id.value)

        ordered_ids = tuple(
            work_unit.id.value
            for work_unit in sorted(
                request.work_units,
                key=lambda item: (-item.priority, item.id.value),
            )
        )

        ready_group = tuple(
            sorted(ready_ids, key=lambda item: (-work_units_by_id[item].priority, item))
        )

        plan = Plan(
            version=PlanVersion(request.version),
            baseline=request.project.baseline,
            work_unit_ids=ordered_ids,
            dependency_ids=tuple(
                f"{dependency.source_id}->{dependency.target_id}"
                for dependency in request.dependencies
            ),
            priorities=ordered_ids,
            parallel_groups=(ready_group,) if ready_group else (),
            gates=(),
        )
        plan.activate()

        return PlanWorkResult(
            plan=plan,
            ready_work_unit_ids=tuple(ready_group),
            blocked_work_unit_ids=tuple(
                sorted(blocked_ids, key=lambda item: (-work_units_by_id[item].priority, item))
            ),
        )

    @staticmethod
    def _is_ready(
        work_unit: WorkUnit,
        dependencies: Sequence[Dependency],
    ) -> bool:
        if work_unit.state not in {
            WorkUnitState.PLANNED,
            WorkUnitState.READY,
            WorkUnitState.REOPENED,
        }:
            return False

        return all(dependency.is_satisfied for dependency in dependencies)

    @staticmethod
    def _validate(request: PlanWorkRequest) -> None:
        if request.version < 1:
            raise ValueError("Plan version must be at least 1.")

        work_unit_ids = [work_unit.id.value for work_unit in request.work_units]
        if len(work_unit_ids) != len(set(work_unit_ids)):
            raise ValueError("Work Unit identifiers must be unique.")

        known_ids = set(work_unit_ids)

        for dependency in request.dependencies:
            if dependency.source_id not in known_ids:
                raise ValueError(
                    f"Dependency source '{dependency.source_id}' is not in the Work Unit set."
                )
            if dependency.target_id not in known_ids:
                raise ValueError(
                    f"Dependency target '{dependency.target_id}' is not in the Work Unit set."
                )
