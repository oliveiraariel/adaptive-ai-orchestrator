from application.finalize_execution import FinalizeExecution, FinalizeExecutionRequest
from domain.dependency import Dependency, DependencyStatus
from domain.evaluation import EvaluationVerdict
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState
from infrastructure.claim_registry import InMemoryClaimRegistry


def make_running_work() -> tuple[WorkUnit, InMemoryClaimRegistry, object]:
    work_unit = WorkUnit(
        id=WorkUnitId("wu-a"),
        objective="Execute A",
    )
    work_unit.mark_ready()
    work_unit.start()
    registry = InMemoryClaimRegistry()
    claim = registry.acquire(work_unit_id="wu-a", claimant_id="scheduler")
    assert claim is not None
    claim = registry.bind_execution(claim, execution_id="execution:a")
    return work_unit, registry, claim


def test_accepted_execution_completes_work_advances_dependencies_and_releases_claim() -> None:
    work_unit, registry, claim = make_running_work()
    dependency = Dependency(source_id="wu-a", target_id="wu-b")

    result = FinalizeExecution(registry).execute(
        FinalizeExecutionRequest(
            work_unit=work_unit,
            claim=claim,
            verdict=EvaluationVerdict.ACCEPTED,
            dependencies=(dependency,),
        )
    )

    assert result.work_unit_state is WorkUnitState.COMPLETED
    assert result.satisfied_dependency_ids == ("wu-a->wu-b",)
    assert dependency.status is DependencyStatus.SATISFIED
    assert registry.get("wu-a") is None


def test_returned_execution_requires_revision_and_does_not_advance_dependency() -> None:
    work_unit, registry, claim = make_running_work()
    dependency = Dependency(source_id="wu-a", target_id="wu-b")

    result = FinalizeExecution(registry).execute(
        FinalizeExecutionRequest(
            work_unit=work_unit,
            claim=claim,
            verdict=EvaluationVerdict.RETURNED,
            dependencies=(dependency,),
        )
    )

    assert result.work_unit_state is WorkUnitState.REVISION_REQUIRED
    assert result.satisfied_dependency_ids == ()
    assert dependency.status is DependencyStatus.BLOCKED
    assert registry.get("wu-a") is None


def test_blocked_evaluation_blocks_work_and_releases_claim() -> None:
    work_unit, registry, claim = make_running_work()

    result = FinalizeExecution(registry).execute(
        FinalizeExecutionRequest(
            work_unit=work_unit,
            claim=claim,
            verdict=EvaluationVerdict.BLOCKED,
            dependencies=(),
        )
    )

    assert result.work_unit_state is WorkUnitState.BLOCKED
    assert registry.get("wu-a") is None
