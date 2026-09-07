import pytest

from domain.evaluation import Evaluation, EvaluationVerdict
from domain.evaluation_plan import (
    AxisEvaluation,
    EvaluationAxis,
    EvaluationPlan,
    EvaluationPlanError,
)


def make_axis(name: str, *, required: bool = True) -> EvaluationAxis:
    return EvaluationAxis(
        name=name,
        evaluator_id=f"reviewer:{name}",
        criteria=(f"criterion:{name}",),
        required=required,
    )


def make_evaluation(axis: str, verdict: EvaluationVerdict) -> AxisEvaluation:
    evidence = (f"evidence:{axis}",) if verdict in {
        EvaluationVerdict.ACCEPTED,
        EvaluationVerdict.ACCEPTED_WITH_CONDITIONS,
    } else ()
    return AxisEvaluation(
        axis_name=axis,
        evaluation=Evaluation(
            id=f"evaluation:{axis}",
            target="result-001",
            evaluator=f"reviewer:{axis}",
            criteria=(f"criterion:{axis}",),
            evidence=evidence,
            findings=(f"finding:{axis}",),
            verdict=verdict,
            confidence=1.0,
        ),
    )


def test_all_required_axes_must_be_present_before_acceptance() -> None:
    plan = EvaluationPlan((make_axis("spec"), make_axis("standards")))

    summary = plan.aggregate((make_evaluation("spec", EvaluationVerdict.ACCEPTED),))

    assert summary.verdict is EvaluationVerdict.BLOCKED
    assert summary.missing_required_axes == ("standards",)


def test_required_axis_rejection_cannot_be_masked_by_other_acceptance() -> None:
    plan = EvaluationPlan((make_axis("spec"), make_axis("security")))

    summary = plan.aggregate(
        (
            make_evaluation("spec", EvaluationVerdict.ACCEPTED),
            make_evaluation("security", EvaluationVerdict.REJECTED),
        )
    )

    assert summary.verdict is EvaluationVerdict.REJECTED


def test_required_returned_axis_requires_revision() -> None:
    plan = EvaluationPlan((make_axis("spec"), make_axis("standards")))

    summary = plan.aggregate(
        (
            make_evaluation("spec", EvaluationVerdict.ACCEPTED),
            make_evaluation("standards", EvaluationVerdict.RETURNED),
        )
    )

    assert summary.verdict is EvaluationVerdict.RETURNED


def test_conditional_required_axis_remains_visible_in_aggregate() -> None:
    plan = EvaluationPlan((make_axis("spec"), make_axis("standards")))

    summary = plan.aggregate(
        (
            make_evaluation("spec", EvaluationVerdict.ACCEPTED),
            make_evaluation(
                "standards",
                EvaluationVerdict.ACCEPTED_WITH_CONDITIONS,
            ),
        )
    )

    assert summary.verdict is EvaluationVerdict.ACCEPTED_WITH_CONDITIONS
    assert [item.axis_name for item in summary.axis_evaluations] == [
        "spec",
        "standards",
    ]


def test_optional_axis_failure_does_not_override_required_acceptance() -> None:
    plan = EvaluationPlan(
        (
            make_axis("spec"),
            make_axis("advisory-style", required=False),
        )
    )

    summary = plan.aggregate(
        (
            make_evaluation("spec", EvaluationVerdict.ACCEPTED),
            make_evaluation("advisory-style", EvaluationVerdict.REJECTED),
        )
    )

    assert summary.verdict is EvaluationVerdict.ACCEPTED
    assert len(summary.axis_evaluations) == 2


def test_unplanned_or_duplicate_axis_is_rejected() -> None:
    plan = EvaluationPlan((make_axis("spec"),))

    with pytest.raises(EvaluationPlanError, match="unplanned"):
        plan.aggregate((make_evaluation("security", EvaluationVerdict.REJECTED),))

    with pytest.raises(EvaluationPlanError, match="Duplicate"):
        plan.aggregate(
            (
                make_evaluation("spec", EvaluationVerdict.ACCEPTED),
                make_evaluation("spec", EvaluationVerdict.ACCEPTED),
            )
        )
