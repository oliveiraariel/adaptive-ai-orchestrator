from application.plan_work import PlanWork, PlanWorkRequest
from domain.dependency import Dependency
from domain.plan import PlanStatus
from domain.project import Project, ProjectId
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState


def make_project() -> Project:
    return Project(
        id=ProjectId("project-001"),
        identity="Adaptive AI Orchestrator",
        baseline="baseline-001",
    )


def make_work_unit(work_unit_id: str, priority: int = 0) -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId(work_unit_id),
        objective=f"Objective {work_unit_id}",
        priority=priority,
    )


def test_plan_work_produces_active_plan() -> None:
    project = make_project()
    work_units = [
        make_work_unit("wu-001"),
        make_work_unit("wu-002"),
    ]

    result = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=work_units,
            dependencies=[],
        )
    )

    assert result.plan.status is PlanStatus.ACTIVE
    assert result.plan.baseline == "baseline-001"
    assert result.plan.work_unit_ids == ("wu-001", "wu-002")
    assert result.ready_work_unit_ids == ("wu-001", "wu-002")


def test_required_unsatisfied_dependency_blocks_target() -> None:
    project = make_project()
    source = make_work_unit("wu-001", priority=1)
    target = make_work_unit("wu-002", priority=10)

    dependency = Dependency(
        source_id=source.id.value,
        target_id=target.id.value,
        required=True,
    )

    result = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=[source, target],
            dependencies=[dependency],
        )
    )

    assert result.ready_work_unit_ids == ("wu-001",)
    assert result.blocked_work_unit_ids == ("wu-002",)


def test_satisfied_dependency_allows_target() -> None:
    project = make_project()
    source = make_work_unit("wu-001")
    target = make_work_unit("wu-002")

    dependency = Dependency(
        source_id=source.id.value,
        target_id=target.id.value,
    )
    dependency.satisfy()

    result = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=[source, target],
            dependencies=[dependency],
        )
    )

    assert result.ready_work_unit_ids == ("wu-001", "wu-002")
    assert result.blocked_work_unit_ids == ()


def test_priority_is_used_to_order_plan() -> None:
    project = make_project()
    low = make_work_unit("wu-low", priority=1)
    high = make_work_unit("wu-high", priority=10)

    result = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=[low, high],
            dependencies=[],
        )
    )

    assert result.plan.work_unit_ids == ("wu-high", "wu-low")
    assert result.ready_work_unit_ids == ("wu-high", "wu-low")


def test_running_work_unit_is_not_ready() -> None:
    project = make_project()
    work_unit = make_work_unit("wu-001")
    work_unit.mark_ready()
    work_unit.start()

    result = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=[work_unit],
            dependencies=[],
        )
    )

    assert result.ready_work_unit_ids == ()
    assert result.blocked_work_unit_ids == ("wu-001",)


def test_unknown_dependency_work_unit_is_rejected() -> None:
    project = make_project()

    try:
        PlanWork().execute(
            PlanWorkRequest(
                project=project,
                work_units=[make_work_unit("wu-001")],
                dependencies=[
                    Dependency(
                        source_id="wu-missing",
                        target_id="wu-001",
                    )
                ],
            )
        )
    except ValueError as exc:
        assert "wu-missing" in str(exc)
    else:
        raise AssertionError("Expected unknown dependency to be rejected.")
