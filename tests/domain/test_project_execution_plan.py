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


def test_filesystem_write_requires_explicit_repository_write_scope() -> None:
    with pytest.raises(ProjectExecutionPlanError, match="declares no"):
        PlannedWorkUnit(
            id="writer",
            objective="Write code",
            requested_side_effects=("filesystem.write",),
        )


def test_write_scope_rejects_absolute_and_parent_escape_paths() -> None:
    for unsafe_path in ("/etc/passwd", "../outside", "src/../../outside", "C:/temp"):
        with pytest.raises(ProjectExecutionPlanError):
            PlannedWorkUnit(
                id=f"writer-{unsafe_path}",
                objective="Write code safely",
                requested_side_effects=("filesystem.write",),
                write_paths=(unsafe_path,),
            )


def test_write_scope_rejects_globs_but_accepts_literal_relative_prefix() -> None:
    with pytest.raises(ProjectExecutionPlanError, match="literal path prefix"):
        PlannedWorkUnit(
            id="glob-writer",
            objective="Write code",
            requested_side_effects=("filesystem.write",),
            write_paths=("src/**/*.py",),
        )

    unit = PlannedWorkUnit(
        id="safe-writer",
        objective="Write code",
        requested_side_effects=("filesystem.write",),
        write_paths=("src/backend/controllers",),
    )
    assert unit.write_paths == ("src/backend/controllers",)
