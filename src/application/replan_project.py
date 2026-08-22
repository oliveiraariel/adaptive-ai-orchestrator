from dataclasses import dataclass
from typing import Sequence

from application.plan_work import PlanWork, PlanWorkRequest
from domain.dependency import Dependency
from domain.plan import Plan
from domain.plan_revision import PlanRevision
from domain.project import Project
from domain.work_unit import WorkUnit, WorkUnitState


@dataclass(frozen=True)
class ReplanProjectRequest:
    project: Project
    current_plan: Plan
    work_units: Sequence[WorkUnit]
    dependencies: Sequence[Dependency]
    trigger: str
    affected_work_unit_ids: tuple[str, ...] = ()
    added_work_units: tuple[WorkUnit, ...] = ()
    removed_work_unit_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReplanProjectResult:
    revision: PlanRevision


class ReplanProject:
    """Produces a new plan while preserving unaffected valid work."""

    def __init__(self, planner: PlanWork) -> None:
        self._planner = planner

    def execute(
        self,
        request: ReplanProjectRequest,
    ) -> ReplanProjectResult:
        if not request.trigger.strip():
            raise ValueError("Replanning trigger must not be empty.")

        removed_ids = set(request.removed_work_unit_ids)
        affected_ids = set(request.affected_work_unit_ids)

        current_ids = {
            work_unit.id.value
            for work_unit in request.work_units
        }

        unknown_removed = removed_ids - current_ids
        if unknown_removed:
            raise ValueError(
                "Cannot remove unknown Work Units: "
                + ", ".join(sorted(unknown_removed))
            )

        added_ids = {
            work_unit.id.value
            for work_unit in request.added_work_units
        }

        unknown_affected = (
            affected_ids - current_ids - added_ids
        )
        if unknown_affected:
            raise ValueError(
                "Affected Work Units are unknown: "
                + ", ".join(sorted(unknown_affected))
            )

        effective_work_units = [
            work_unit
            for work_unit in request.work_units
            if work_unit.id.value not in removed_ids
        ]

        effective_ids = {
            work_unit.id.value
            for work_unit in effective_work_units
        }

        for added in request.added_work_units:
            if added.id.value in effective_ids:
                raise ValueError(
                    f"Work Unit '{added.id.value}' already exists."
                )

            effective_work_units.append(added)
            effective_ids.add(added.id.value)

        effective_dependencies = [
            dependency
            for dependency in request.dependencies
            if (
                dependency.source_id in effective_ids
                and dependency.target_id in effective_ids
            )
        ]

        for work_unit in effective_work_units:
            if (
                work_unit.id.value in affected_ids
                and work_unit.state is WorkUnitState.COMPLETED
            ):
                work_unit.reopen()

        new_version = request.current_plan.version.value + 1

        planning_result = self._planner.execute(
            PlanWorkRequest(
                project=request.project,
                work_units=effective_work_units,
                dependencies=effective_dependencies,
                version=new_version,
            )
        )

        changes = self._describe_changes(
            request.current_plan,
            planning_result.plan,
            affected_ids,
            removed_ids,
            request.added_work_units,
        )

        revision = PlanRevision(
            previous_version=request.current_plan.version.value,
            new_plan=planning_result.plan,
            trigger=request.trigger,
            affected_work_unit_ids=tuple(sorted(affected_ids)),
            changes=tuple(changes),
        )

        return ReplanProjectResult(revision=revision)

    @staticmethod
    def _describe_changes(
        current_plan: Plan,
        new_plan: Plan,
        affected_ids: set[str],
        removed_ids: set[str],
        added_work_units: Sequence[WorkUnit],
    ) -> list[str]:
        changes: list[str] = []

        if current_plan.baseline != new_plan.baseline:
            changes.append("baseline-changed")

        if affected_ids:
            changes.append(
                "affected-work-units:"
                + ",".join(sorted(affected_ids))
            )

        if removed_ids:
            changes.append(
                "removed-work-units:"
                + ",".join(sorted(removed_ids))
            )

        if added_work_units:
            changes.append(
                "added-work-units:"
                + ",".join(
                    sorted(
                        work_unit.id.value
                        for work_unit in added_work_units
                    )
                )
            )

        if current_plan.work_unit_ids != new_plan.work_unit_ids:
            changes.append("work-unit-set-or-priority-changed")

        if current_plan.dependency_ids != new_plan.dependency_ids:
            changes.append("dependencies-changed")

        if (
            current_plan.parallel_groups
            and new_plan.parallel_groups
            and current_plan.parallel_groups
            != new_plan.parallel_groups
        ):
            changes.append("parallel-groups-changed")

        if not changes:
            changes.append("plan-revalidated")

        return changes
