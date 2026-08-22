from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class LearningCandidateError(ValueError):
    """Raised when a LearningCandidate invariant is violated."""


class LearningValidationStatus(str, Enum):
    UNVALIDATED = "UNVALIDATED"
    UNDER_VALIDATION = "UNDER_VALIDATION"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class LearningCandidate:
    observation: str
    context: Tuple[str, ...] = field(default_factory=tuple)
    evidence: Tuple[str, ...] = field(default_factory=tuple)
    scope: str = ""
    confidence: float | None = None
    potential_impact: Tuple[str, ...] = field(default_factory=tuple)
    proposed_use: str = ""
    validation_status: LearningValidationStatus = LearningValidationStatus.UNVALIDATED
    history: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.observation.strip():
            raise LearningCandidateError(
                "LearningCandidate observation must not be empty."
            )

        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise LearningCandidateError(
                "LearningCandidate confidence must be between 0.0 and 1.0."
            )

    def start_validation(self) -> "LearningCandidate":
        if self.validation_status is not LearningValidationStatus.UNVALIDATED:
            raise LearningCandidateError(
                "Only an unvalidated candidate can enter validation."
            )

        return self._with_status(
            LearningValidationStatus.UNDER_VALIDATION,
            "validation-started",
        )

    def validate(self) -> "LearningCandidate":
        if self.validation_status is not LearningValidationStatus.UNDER_VALIDATION:
            raise LearningCandidateError(
                "Only a candidate under validation can become validated."
            )

        if not self.evidence:
            raise LearningCandidateError(
                "A candidate must have evidence before validation."
            )

        return self._with_status(
            LearningValidationStatus.VALIDATED,
            "validated",
        )

    def reject(self) -> "LearningCandidate":
        if self.validation_status is LearningValidationStatus.VALIDATED:
            raise LearningCandidateError(
                "A validated candidate cannot be rejected through this transition."
            )

        return self._with_status(
            LearningValidationStatus.REJECTED,
            "rejected",
        )

    def _with_status(
        self,
        status: LearningValidationStatus,
        history_entry: str,
    ) -> "LearningCandidate":
        return LearningCandidate(
            observation=self.observation,
            context=self.context,
            evidence=self.evidence,
            scope=self.scope,
            confidence=self.confidence,
            potential_impact=self.potential_impact,
            proposed_use=self.proposed_use,
            validation_status=status,
            history=(*self.history, history_entry),
        )
