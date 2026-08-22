from domain.dependency import Dependency
from domain.work_unit import WorkUnit, WorkUnitId
from domain.work_unit_readiness import (
    ReadinessStatus,
    WorkUnitReadinessEvaluator,
)


def make_work_unit(work_unit_id: str = "wu-001") -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId(work_unit_id),
        objective=f"Objective {work_unit_id}",
    )


def test_planned_work_unit_without_blocking_dependency_is_ready() -> None:
    evaluator = WorkUnitReadinessEvaluator()

    result = evaluator.evaluate(make_work_unit(), [])

    assert result.status is ReadinessStatus.READY
    assert result.blocking_dependency_ids == ()


def test_required_unsatisfied_dependency_blocks_work_unit() -> None:
    evaluator = WorkUnitReadinessEvaluator()
    dependency = Dependency(
        source_id="wu-source",
        target_id="wu-001",
        required=True,
    )

    result = evaluator.evaluate(make_work_unit(), [dependency])

    assert result.status is ReadinessStatus.BLOCKED
    assert result.blocking_dependency_ids == ("wu-source->wu-001",)


def test_satisfied_dependency_does_not_block_work_unit() -> None:
    evaluator = WorkUnitReadinessEvaluator()
    dependency = Dependency(
        source_id="wu-source",
        target_id="wu-001",
        required=True,
    )
    dependency.satisfy()

    result = evaluator.evaluate(make_work_unit(), [dependency])

    assert result.status is ReadinessStatus.READY
    assert result.blocking_dependency_ids == ()


def test_optional_unsatisfied_dependency_does_not_block() -> None:
    evaluator = WorkUnitReadinessEvaluator()
    dependency = Dependency(
        source_id="wu-source",
        target_id="wu-001",
        required=False,
    )

    result = evaluator.evaluate(make_work_unit(), [dependency])

    assert result.status is ReadinessStatus.READY
    assert result.blocking_dependency_ids == ()


def test_running_work_unit_is_blocked_even_without_dependencies() -> None:
    evaluator = WorkUnitReadinessEvaluator()
    work_unit = make_work_unit()
    work_unit.mark_ready()
    work_unit.start()

    result = evaluator.evaluate(work_unit, [])

    assert result.status is ReadinessStatus.BLOCKED


def test_evaluate_all_uses_dependency_target() -> None:
    evaluator = WorkUnitReadinessEvaluator()
    first = make_work_unit("wu-001")
    second = make_work_unit("wu-002")
    dependency = Dependency(
        source_id=first.id.value,
        target_id=second.id.value,
    )

    results = evaluator.evaluate_all([first, second], [dependency])

    assert results[0].status is ReadinessStatus.READY
    assert results[1].status is ReadinessStatus.BLOCKED


def test_reopened_work_unit_is_ready() -> None:
    evaluator = WorkUnitReadinessEvaluator()
    work_unit = make_work_unit()
    work_unit.mark_ready()
    work_unit.start()
    work_unit.start_evaluation()
    work_unit.complete()
    work_unit.reopen()

    result = evaluator.evaluate(work_unit, [])

    assert result.status is ReadinessStatus.READY
