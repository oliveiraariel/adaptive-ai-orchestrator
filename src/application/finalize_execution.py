from dataclasses import dataclass
from typing import Sequence, Tuple

from application.claim_registry import ClaimRegistry
from domain.dependency import Dependency
from domain.evaluation import EvaluationVerdict
from domain.execution_claim import ExecutionClaim
from domain.work_unit import WorkUnit, WorkUnitState


@dataclass(frozen=True)
class FinalizeExecutionRequest:
    work_unit: WorkUnit
    claim: ExecutionClaim
    verdict: EvaluationVerdict
    dependencies: Sequence[Dependency]


@dataclass(frozen=True)
class FinalizeExecutionResult:
    work_unit_state: WorkUnitState
    satisfied_dependency_ids: Tuple[str, ...]


class FinalizeExecution:
    """Applies an evaluated result to orchestration state.

    Dependencies advance only after an accepted outcome. The execution claim is
    released after the evaluation has been incorporated so a revision can be
    claimed by a later execution.
    """

    def __init__(self, claim_registry: ClaimRegistry) -> None:
        self._claim_registry = claim_registry

    def execute(self, request: FinalizeExecutionRequest) -> FinalizeExecutionResult:
        work_unit = request.work_unit
        if work_unit.state is WorkUnitState.RUNNING:
            work_unit.start_evaluation()
        elif work_unit.state is not WorkUnitState.EVALUATING:
            raise ValueError(
                "Execution can only be finalized from RUNNING or EVALUATING state."
            )

        satisfied: list[str] = []

        if request.verdict in {
            EvaluationVerdict.ACCEPTED,
            EvaluationVerdict.ACCEPTED_WITH_CONDITIONS,
        }:
            work_unit.complete()
            for dependency in request.dependencies:
                if dependency.source_id != work_unit.id.value:
                    continue
                if not dependency.required:
                    continue
                dependency.satisfy()
                satisfied.append(
                    f"{dependency.source_id}->{dependency.target_id}"
                )
        elif request.verdict in {
            EvaluationVerdict.RETURNED,
            EvaluationVerdict.REJECTED,
        }:
            work_unit.require_revision()
        elif request.verdict is EvaluationVerdict.BLOCKED:
            work_unit.mark_blocked()
        else:
            raise ValueError("Evaluation verdict is not finalizable.")

        self._claim_registry.release(request.claim)

        return FinalizeExecutionResult(
            work_unit_state=work_unit.state,
            satisfied_dependency_ids=tuple(satisfied),
        )
