from domain.result_package import ResultPackage, ResultPackageStatus
from domain.evaluation import EvaluationVerdict
from application.evaluate_result import (
    EvaluateResult,
    EvaluateResultRequest,
)


def make_result(
    *,
    result: object | None = None,
    evidence: tuple[str, ...] = (),
    status: ResultPackageStatus = ResultPackageStatus.SUCCEEDED,
) -> ResultPackage:
    return ResultPackage(
        task_id="task-001",
        status=status,
        result=result if result is not None else {"status": "tests-pass"},
        evidence=evidence,
    )


def test_evaluate_result_accepts_when_all_criteria_are_satisfied() -> None:
    result = make_result(evidence=("tests-pass", "acceptance-pass"))

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result,
            criteria=("tests-pass", "acceptance-pass"),
            evaluator_id="evaluator-001",
        )
    ).evaluation

    assert evaluation.verdict is EvaluationVerdict.ACCEPTED
    assert evaluation.confidence == 1.0


def test_evaluate_result_returns_conditional_when_some_criteria_are_unsatisfied() -> None:
    result = make_result(evidence=("tests-pass",))

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result,
            criteria=("tests-pass", "acceptance-pass"),
            evaluator_id="evaluator-001",
        )
    ).evaluation

    assert evaluation.verdict is EvaluationVerdict.ACCEPTED_WITH_CONDITIONS
    assert evaluation.confidence == 0.5
    assert "UNSATISFIED: acceptance-pass" in evaluation.findings


def test_evaluate_result_returns_when_no_criterion_is_satisfied() -> None:
    result = make_result(evidence=("unrelated",))

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result,
            criteria=("acceptance-pass",),
            evaluator_id="evaluator-001",
        )
    ).evaluation

    assert evaluation.verdict is EvaluationVerdict.RETURNED
    assert evaluation.confidence == 0.0


def test_failed_execution_is_returned() -> None:
    result = make_result(
        result=None,
        evidence=("runtime-error",),
        status=ResultPackageStatus.FAILED,
    )

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result,
            criteria=("tests-pass",),
            evaluator_id="evaluator-001",
        )
    ).evaluation

    assert evaluation.verdict is EvaluationVerdict.RETURNED


def test_evaluate_result_requires_evaluator() -> None:
    result = make_result()

    try:
        EvaluateResult().execute(
            EvaluateResultRequest(
                result_package=result,
                criteria=("tests-pass",),
                evaluator_id="",
            )
        )
    except ValueError as exc:
        assert "Evaluator id" in str(exc)
    else:
        raise AssertionError("Expected evaluator validation error.")


def test_evaluate_result_requires_criteria() -> None:
    result = make_result()

    try:
        EvaluateResult().execute(
            EvaluateResultRequest(
                result_package=result,
                criteria=(),
                evaluator_id="evaluator-001",
            )
        )
    except ValueError as exc:
        assert "criterion" in str(exc)
    else:
        raise AssertionError("Expected criteria validation error.")

def test_partial_result_is_never_accepted_as_terminal() -> None:
    result = make_result(
        evidence=("runtime-completed",),
        status=ResultPackageStatus.PARTIAL,
    )

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result,
            criteria=("runtime-completed",),
            evaluator_id="evaluator-001",
        )
    ).evaluation

    assert evaluation.verdict is EvaluationVerdict.RETURNED
