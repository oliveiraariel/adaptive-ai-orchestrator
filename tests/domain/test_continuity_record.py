import pytest

from domain.continuity_record import (
    ContinuityError,
    ContinuityRecord,
    ContinuityStatus,
)


def make_record() -> ContinuityRecord:
    return ContinuityRecord(
        project_id="project-001",
        current_plan_version=2,
        current_work_unit_ids=("wu-001", "wu-002"),
        pending_work_unit_ids=("wu-002",),
        decisions=("decision-001",),
        evidence=("evidence-001",),
        open_issues=("issue-001",),
        risks=("risk-001",),
        context=("baseline-001",),
    )


def test_continuity_record_requires_project_id() -> None:
    with pytest.raises(ContinuityError):
        ContinuityRecord(project_id="")


def test_current_plan_version_must_be_positive() -> None:
    with pytest.raises(ContinuityError):
        ContinuityRecord(
            project_id="project-001",
            current_plan_version=0,
        )


def test_continuity_record_preserves_context() -> None:
    record = make_record()

    assert record.project_id == "project-001"
    assert record.status is ContinuityStatus.ACTIVE
    assert record.current_plan_version == 2
    assert record.current_work_unit_ids == ("wu-001", "wu-002")
    assert record.pending_work_unit_ids == ("wu-002",)
    assert record.decisions == ("decision-001",)
    assert record.evidence == ("evidence-001",)
    assert record.open_issues == ("issue-001",)
    assert record.risks == ("risk-001",)
    assert record.context == ("baseline-001",)


def test_plan_version_can_be_updated_immutably() -> None:
    record = make_record()

    updated = record.update_plan_version(3)

    assert record.current_plan_version == 2
    assert updated.current_plan_version == 3
    assert updated.project_id == record.project_id


def test_pause_and_resume_preserve_state() -> None:
    record = make_record()

    paused = record.pause()
    resumed = paused.resume()

    assert paused.status is ContinuityStatus.PAUSED
    assert resumed.status is ContinuityStatus.ACTIVE
    assert resumed.current_plan_version == record.current_plan_version
    assert resumed.context == record.context


def test_completion_preserves_historical_context() -> None:
    record = make_record()

    completed = record.complete()

    assert completed.status is ContinuityStatus.COMPLETED
    assert completed.decisions == record.decisions
    assert completed.evidence == record.evidence
    assert completed.open_issues == record.open_issues
    assert completed.risks == record.risks
