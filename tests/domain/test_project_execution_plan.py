import pytest

from domain.project_execution_plan import (
    PlannedDependency,
    PlannedWorkUnit,
    ProjectExecutionPlan,
    ProjectExecutionPlanError,
)


def unit(unit_id: str) -> PlannedWorkUnit:
    return PlannedWorkUnit(id=unit_id, objective=f"Execute {unit_id}")


def test_project_execution_plan_rejects_duplicate_work_unit_ids() -> None:
    with pytest.raises(ProjectExecutionPlanError, match="unique"):
        ProjectExecutionPlan(
            summary="duplicate",
            work_units=(unit("a"), unit("a")),
        )


def test_project_execution_plan_rejects_unknown_dependency_endpoint() -> None:
    with pytest.raises(ProjectExecutionPlanError, match="Unknown dependency target"):
        ProjectExecutionPlan(
            summary="unknown edge",
            work_units=(unit("a"),),
            dependencies=(PlannedDependency("a", "missing"),),
        )


def test_project_execution_plan_rejects_required_cycle() -> None:
    with pytest.raises(ProjectExecutionPlanError, match="acyclic"):
        ProjectExecutionPlan(
            summary="cycle",
            work_units=(unit("a"), unit("b")),
            dependencies=(
                PlannedDependency("a", "b"),
                PlannedDependency("b", "a"),
            ),
        )


def test_optional_cycle_does_not_block_required_dag_validation() -> None:
    plan = ProjectExecutionPlan(
        summary="optional information flow",
        work_units=(unit("a"), unit("b")),
        dependencies=(
            PlannedDependency("a", "b", required=False),
            PlannedDependency("b", "a", required=False),
        ),
    )

    assert len(plan.dependencies) == 2
