import pytest

from domain.work_unit import (
    WorkUnit,
    WorkUnitId,
    WorkUnitState,
    WorkUnitStateError,
)


def make_work_unit() -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId("wu-001"),
        objective="Implement Work Unit domain",
    )


def test_work_unit_requires_objective() -> None:
    with pytest.raises(WorkUnitStateError):
        WorkUnit(id=WorkUnitId("wu-001"), objective="")


def test_work_unit_starts_planned() -> None:
    work_unit = make_work_unit()

    assert work_unit.state is WorkUnitState.PLANNED


def test_work_unit_can_be_marked_ready() -> None:
    work_unit = make_work_unit()

    work_unit.mark_ready()

    assert work_unit.state is WorkUnitState.READY


def test_work_unit_can_start_and_enter_evaluation() -> None:
    work_unit = make_work_unit()
    work_unit.mark_ready()

    work_unit.start()
    work_unit.start_evaluation()

    assert work_unit.state is WorkUnitState.EVALUATING


def test_work_unit_can_complete_from_evaluation() -> None:
    work_unit = make_work_unit()
    work_unit.mark_ready()
    work_unit.start()
    work_unit.start_evaluation()

    work_unit.complete()

    assert work_unit.state is WorkUnitState.COMPLETED


def test_work_unit_can_require_revision() -> None:
    work_unit = make_work_unit()
    work_unit.mark_ready()
    work_unit.start()
    work_unit.start_evaluation()

    work_unit.require_revision()

    assert work_unit.state is WorkUnitState.REVISION_REQUIRED


def test_work_unit_can_reopen_after_completion() -> None:
    work_unit = make_work_unit()
    work_unit.mark_ready()
    work_unit.start()
    work_unit.start_evaluation()
    work_unit.complete()

    work_unit.reopen()

    assert work_unit.state is WorkUnitState.REOPENED


def test_work_unit_can_restart_after_revision() -> None:
    work_unit = make_work_unit()
    work_unit.mark_ready()
    work_unit.start()
    work_unit.start_evaluation()
    work_unit.require_revision()

    work_unit.start()

    assert work_unit.state is WorkUnitState.RUNNING


def test_completed_work_unit_cannot_be_blocked_or_cancelled() -> None:
    work_unit = make_work_unit()
    work_unit.mark_ready()
    work_unit.start()
    work_unit.start_evaluation()
    work_unit.complete()

    with pytest.raises(WorkUnitStateError):
        work_unit.mark_blocked()

    with pytest.raises(WorkUnitStateError):
        work_unit.cancel()


def test_negative_priority_is_rejected() -> None:
    with pytest.raises(WorkUnitStateError):
        WorkUnit(
            id=WorkUnitId("wu-001"),
            objective="test",
            priority=-1,
        )


def test_negative_criticality_is_rejected() -> None:
    with pytest.raises(WorkUnitStateError):
        WorkUnit(
            id=WorkUnitId("wu-001"),
            objective="test",
            criticality=-1,
        )
