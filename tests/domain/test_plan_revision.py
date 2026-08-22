import pytest

from domain.plan import Plan, PlanVersion
from domain.plan_revision import PlanRevision, PlanRevisionError


def test_plan_revision_requires_newer_version() -> None:
    plan = Plan(version=PlanVersion(1))

    with pytest.raises(PlanRevisionError):
        PlanRevision(
            previous_version=1,
            new_plan=plan,
            trigger="new-result",
        )


def test_plan_revision_preserves_trigger_and_changes() -> None:
    plan = Plan(version=PlanVersion(2))

    revision = PlanRevision(
        previous_version=1,
        new_plan=plan,
        trigger="evaluation-returned",
        affected_work_unit_ids=("wu-001",),
        changes=("affected-work-units:wu-001",),
    )

    assert revision.previous_version == 1
    assert revision.new_plan.version.value == 2
    assert revision.trigger == "evaluation-returned"
    assert revision.affected_work_unit_ids == ("wu-001",)
    assert revision.changes == ("affected-work-units:wu-001",)
