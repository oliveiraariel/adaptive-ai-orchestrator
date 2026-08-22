from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class EvaluationError(ValueError):
    """Raised when an Evaluation invariant is violated."""


class EvaluationVerdict(str, Enum):
    ACCEPTED = "ACCEPTED"
    ACCEPTED_WITH_CONDITIONS = "ACCEPTED_WITH_CONDITIONS"
    RETURNED = "RETURNED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Evaluation:
    id: str
    target: str
    evaluator: str
    criteria: Tuple[str, ...] = field(default_factory=tuple)
    evidence: Tuple[str, ...] = field(default_factory=tuple)
    findings: Tuple[str, ...] = field(default_factory=tuple)
    verdict: EvaluationVerdict | None = None
    confidence: float | None = None
    impact: Tuple[str, ...] = field(default_factory=tuple)
    timestamp: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise EvaluationError("Evaluation id must not be empty.")

        if not self.target.strip():
            raise EvaluationError("Evaluation target must not be empty.")

        if not self.evaluator.strip():
            raise EvaluationError("Evaluation evaluator must not be empty.")

        if not (0.0 <= self.confidence <= 1.0) if self.confidence is not None else False:
            raise EvaluationError(
                "Evaluation confidence must be between 0.0 and 1.0."
            )

        if self.verdict is None:
            return

        if self.verdict in {
            EvaluationVerdict.ACCEPTED,
            EvaluationVerdict.ACCEPTED_WITH_CONDITIONS,
        } and not self.evidence:
            raise EvaluationError(
                "Accepted evaluations must contain evidence."
            )
