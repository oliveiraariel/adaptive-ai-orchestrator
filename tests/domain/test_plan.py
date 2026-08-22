import pytest

from domain.plan import Plan, PlanError, PlanStatus, PlanVersion


def test_plan_requires_positive_version() -> None:
    with pytest.raises(PlanError):
        Plan(version=PlanVersion(0))


def test_plan_starts_as_draft() -> None:
    plan = Plan(version=PlanVersion(1))

    assert plan.status is PlanStatus.DRAFT


def test_plan_can_be_activated() -> None:
    plan = Plan(version=PlanVersion(1))

    plan.activate()

    assert plan.status is PlanStatus.ACTIVE


def test_plan_can_be_superseded_after_activation() -> None:
    plan = Plan(version=PlanVersion(1))
    plan.activate()

    plan.supersede()

    assert plan.status is PlanStatus.SUPERSEDED


def test_plan_cannot_be_superseded_before_activation() -> None:
    plan = Plan(version=PlanVersion(1))

    with pytest.raises(PlanError):
        plan.supersede()


def test_blank_baseline_is_rejected() -> None:
    with pytest.raises(PlanError):
        Plan(version=PlanVersion(1), baseline="   ")


def test_plan_holds_planning_state() -> None:
    plan = Plan(
        version=PlanVersion(2),
        baseline="baseline-001",
        work_unit_ids=("wu-001", "wu-002"),
        dependency_ids=("dep-001",),
        priorities=("wu-001", "wu-002"),
        parallel_groups=(("wu-001",),),
        gates=("gate-001",),
    )

    assert plan.version.value == 2
    assert plan.baseline == "baseline-001"
    assert plan.work_unit_ids == ("wu-001", "wu-002")
    assert plan.dependency_ids == ("dep-001",)
    assert plan.priorities == ("wu-001", "wu-002")
    assert plan.parallel_groups == (("wu-001",),)
    assert plan.gates == ("gate-001",)
