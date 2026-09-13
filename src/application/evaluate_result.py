from dataclasses import dataclass
from typing import Sequence

from domain.evaluation import Evaluation, EvaluationVerdict
from domain.result_package import ResultPackage


@dataclass(frozen=True)
class EvaluateResultRequest:
    result_package: ResultPackage
    criteria: Sequence[str]
    evaluator_id: str


@dataclass(frozen=True)
class EvaluateResultResult:
    evaluation: Evaluation


class EvaluateResult:
    """Evaluates a ResultPackage against explicit acceptance criteria."""

    def execute(
        self,
        request: EvaluateResultRequest,
    ) -> EvaluateResultResult:
        if not request.evaluator_id.strip():
            raise ValueError("Evaluator id must not be empty.")

        if not request.criteria:
            raise ValueError("At least one evaluation criterion is required.")

        findings: list[str] = []
        satisfied: list[str] = []
        unsatisfied: list[str] = []

        available_evidence = set(request.result_package.evidence)
        result_text = str(request.result_package.result)

        for criterion in request.criteria:
            normalized = criterion.strip()

            if not normalized:
                continue

            if self._criterion_is_satisfied(
                criterion=normalized,
                result_text=result_text,
                evidence=available_evidence,
            ):
                satisfied.append(normalized)
                findings.append(f"SATISFIED: {normalized}")
            else:
                unsatisfied.append(normalized)
                findings.append(f"UNSATISFIED: {normalized}")

        verdict = self._verdict(
            satisfied_count=len(satisfied),
            unsatisfied_count=len(unsatisfied),
            result_status=request.result_package.status.value,
        )

        confidence = (
            len(satisfied) / (len(satisfied) + len(unsatisfied))
            if satisfied or unsatisfied
            else 0.0
        )

        evaluation = Evaluation(
            id=f"evaluation:{request.result_package.task_id}",
            target=request.result_package.task_id,
            evaluator=request.evaluator_id,
            criteria=tuple(
                criterion.strip()
                for criterion in request.criteria
                if criterion.strip()
            ),
            evidence=request.result_package.evidence,
            findings=tuple(findings),
            verdict=verdict,
            confidence=confidence,
            impact=(
                "result-accepted",
            )
            if verdict in {
                EvaluationVerdict.ACCEPTED,
                EvaluationVerdict.ACCEPTED_WITH_CONDITIONS,
            }
            else (
                "result-returned",
            ),
        )

        return EvaluateResultResult(evaluation=evaluation)

    @staticmethod
    def _criterion_is_satisfied(
        *,
        criterion: str,
        result_text: str,
        evidence: set[str],
    ) -> bool:
        # Minimal observable rule for this first slice:
        # a criterion is satisfied when it appears either in explicit
        # evidence or in the normalized result representation.
        return criterion in evidence or criterion in result_text

    @staticmethod
    def _verdict(
        *,
        satisfied_count: int,
        unsatisfied_count: int,
        result_status: str,
    ) -> EvaluationVerdict:
        if result_status in {"FAILED", "PARTIAL"}:
            return EvaluationVerdict.RETURNED

        if unsatisfied_count == 0 and satisfied_count > 0:
            return EvaluationVerdict.ACCEPTED

        if satisfied_count > 0 and unsatisfied_count > 0:
            return EvaluationVerdict.ACCEPTED_WITH_CONDITIONS

        return EvaluationVerdict.RETURNED
