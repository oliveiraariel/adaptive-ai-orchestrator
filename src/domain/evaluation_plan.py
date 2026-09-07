from dataclasses import dataclass, field
from typing import Tuple

from domain.evaluation import Evaluation, EvaluationVerdict


class EvaluationPlanError(ValueError):
    """Raised when evaluation-plan invariants are violated."""


@dataclass(frozen=True)
class EvaluationAxis:
    name: str
    evaluator_id: str
    criteria: Tuple[str, ...]
    required: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise EvaluationPlanError("Evaluation axis name must not be empty.")
        if not self.evaluator_id.strip():
            raise EvaluationPlanError("Evaluation axis evaluator_id must not be empty.")
        if not self.criteria or any(not criterion.strip() for criterion in self.criteria):
            raise EvaluationPlanError(
                "Evaluation axis must contain non-blank criteria."
            )


@dataclass(frozen=True)
class AxisEvaluation:
    axis_name: str
    evaluation: Evaluation

    def __post_init__(self) -> None:
        if not self.axis_name.strip():
            raise EvaluationPlanError("axis_name must not be empty.")


@dataclass(frozen=True)
class EvaluationSummary:
    verdict: EvaluationVerdict
    axis_evaluations: Tuple[AxisEvaluation, ...] = field(default_factory=tuple)
    missing_required_axes: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvaluationPlan:
    """Keeps review axes independent until an explicit aggregate verdict."""

    axes: Tuple[EvaluationAxis, ...]

    def __post_init__(self) -> None:
        if not self.axes:
            raise EvaluationPlanError("Evaluation plan must contain at least one axis.")
        names = [axis.name for axis in self.axes]
        if len(names) != len(set(names)):
            raise EvaluationPlanError("Evaluation axis names must be unique.")

    def aggregate(
        self,
        evaluations: Tuple[AxisEvaluation, ...],
    ) -> EvaluationSummary:
        planned = {axis.name: axis for axis in self.axes}
        supplied: dict[str, AxisEvaluation] = {}

        for axis_evaluation in evaluations:
            if axis_evaluation.axis_name not in planned:
                raise EvaluationPlanError(
                    f"Evaluation supplied for unplanned axis "
                    f"'{axis_evaluation.axis_name}'."
                )
            if axis_evaluation.axis_name in supplied:
                raise EvaluationPlanError(
                    f"Duplicate evaluation for axis '{axis_evaluation.axis_name}'."
                )
            supplied[axis_evaluation.axis_name] = axis_evaluation

        missing_required = tuple(
            axis.name
            for axis in self.axes
            if axis.required and axis.name not in supplied
        )

        required_verdicts = tuple(
            supplied[axis.name].evaluation.verdict
            for axis in self.axes
            if axis.required and axis.name in supplied
        )

        if EvaluationVerdict.REJECTED in required_verdicts:
            verdict = EvaluationVerdict.REJECTED
        elif EvaluationVerdict.RETURNED in required_verdicts:
            verdict = EvaluationVerdict.RETURNED
        elif missing_required or EvaluationVerdict.BLOCKED in required_verdicts:
            verdict = EvaluationVerdict.BLOCKED
        elif EvaluationVerdict.ACCEPTED_WITH_CONDITIONS in required_verdicts:
            verdict = EvaluationVerdict.ACCEPTED_WITH_CONDITIONS
        elif required_verdicts and all(
            item is EvaluationVerdict.ACCEPTED for item in required_verdicts
        ):
            verdict = EvaluationVerdict.ACCEPTED
        else:
            verdict = EvaluationVerdict.BLOCKED

        ordered_evaluations = tuple(
            supplied[axis.name]
            for axis in self.axes
            if axis.name in supplied
        )

        return EvaluationSummary(
            verdict=verdict,
            axis_evaluations=ordered_evaluations,
            missing_required_axes=missing_required,
        )
