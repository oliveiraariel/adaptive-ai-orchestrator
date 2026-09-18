from __future__ import annotations

from dataclasses import dataclass

from domain.incident import LearningScope


@dataclass(frozen=True)
class SuccessfulRetestLearningAnalysis:
    """Structured learning decision produced after a previously failing retest succeeds."""

    problem_summary: str
    root_cause: str
    solution_summary: str
    learning_statement: str
    scope: LearningScope
    target_hints: tuple[str, ...]
    confidence: float
    should_promote: bool
    evidence_rationale: str

    def __post_init__(self) -> None:
        if not self.problem_summary.strip():
            raise ValueError("problem_summary must not be blank")
        if not self.solution_summary.strip():
            raise ValueError("solution_summary must not be blank")
        if not self.learning_statement.strip():
            raise ValueError("learning_statement must not be blank")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
