import pytest

from domain.evaluation import (
    Evaluation,
    EvaluationError,
    EvaluationVerdict,
)


def make_evaluation() -> Evaluation:
    return Evaluation(
        id="evaluation-001",
        target="task-001",
        evaluator="evaluator-001",
        criteria=("tests-pass", "acceptance-criteria"),
        evidence=("test-report-001",),
        findings=("all expected behavior verified",),
        verdict=EvaluationVerdict.ACCEPTED,
        confidence=0.95,
        impact=("task-complete",),
        timestamp="2026-08-22T17:00:00-03:00",
    )


def test_evaluation_requires_id() -> None:
    with pytest.raises(EvaluationError):
        Evaluation(
            id="",
            target="task-001",
            evaluator="evaluator-001",
        )


def test_evaluation_requires_target() -> None:
    with pytest.raises(EvaluationError):
        Evaluation(
            id="evaluation-001",
            target="",
            evaluator="evaluator-001",
        )


def test_evaluation_requires_evaluator() -> None:
    with pytest.raises(EvaluationError):
        Evaluation(
            id="evaluation-001",
            target="task-001",
            evaluator="",
        )


def test_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(EvaluationError):
        Evaluation(
            id="evaluation-001",
            target="task-001",
            evaluator="evaluator-001",
            confidence=1.1,
        )


def test_accepted_evaluation_requires_evidence() -> None:
    with pytest.raises(EvaluationError):
        Evaluation(
            id="evaluation-001",
            target="task-001",
            evaluator="evaluator-001",
            verdict=EvaluationVerdict.ACCEPTED,
        )


def test_evaluation_preserves_findings_and_verdict() -> None:
    evaluation = make_evaluation()

    assert evaluation.id == "evaluation-001"
    assert evaluation.target == "task-001"
    assert evaluation.evaluator == "evaluator-001"
    assert evaluation.criteria == ("tests-pass", "acceptance-criteria")
    assert evaluation.evidence == ("test-report-001",)
    assert evaluation.findings == ("all expected behavior verified",)
    assert evaluation.verdict is EvaluationVerdict.ACCEPTED
    assert evaluation.confidence == 0.95
    assert evaluation.impact == ("task-complete",)
    assert evaluation.timestamp == "2026-08-22T17:00:00-03:00"
