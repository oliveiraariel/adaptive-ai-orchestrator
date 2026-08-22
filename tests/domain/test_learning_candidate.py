import pytest

from domain.learning_candidate import (
    LearningCandidate,
    LearningCandidateError,
    LearningValidationStatus,
)


def make_candidate(
    *,
    evidence: tuple[str, ...] = ("evidence-001",),
) -> LearningCandidate:
    return LearningCandidate(
        observation="Testing skill produced better acceptance outcomes.",
        context=("wu-001", "agent-001"),
        evidence=evidence,
        scope="current project",
        confidence=0.8,
        potential_impact=("resource-selection",),
        proposed_use="candidate-selection heuristic",
    )


def test_learning_candidate_requires_observation() -> None:
    with pytest.raises(LearningCandidateError):
        LearningCandidate(observation="")


def test_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(LearningCandidateError):
        LearningCandidate(
            observation="observation",
            confidence=1.1,
        )


def test_candidate_starts_unvalidated() -> None:
    candidate = make_candidate()

    assert candidate.validation_status is LearningValidationStatus.UNVALIDATED


def test_candidate_can_enter_validation() -> None:
    candidate = make_candidate()

    validated = candidate.start_validation()

    assert candidate.validation_status is LearningValidationStatus.UNVALIDATED
    assert validated.validation_status is LearningValidationStatus.UNDER_VALIDATION
    assert validated.history == ("validation-started",)


def test_candidate_requires_evidence_to_be_validated() -> None:
    candidate = make_candidate(evidence=()).start_validation()

    with pytest.raises(LearningCandidateError):
        candidate.validate()


def test_candidate_can_be_validated_with_evidence() -> None:
    candidate = make_candidate().start_validation()

    validated = candidate.validate()

    assert validated.validation_status is LearningValidationStatus.VALIDATED
    assert validated.history == (
        "validation-started",
        "validated",
    )


def test_unvalidated_candidate_can_be_rejected() -> None:
    candidate = make_candidate()

    rejected = candidate.reject()

    assert rejected.validation_status is LearningValidationStatus.REJECTED
    assert rejected.history == ("rejected",)


def test_validated_candidate_cannot_be_rejected() -> None:
    candidate = make_candidate().start_validation().validate()

    with pytest.raises(LearningCandidateError):
        candidate.reject()


def test_learning_candidate_preserves_context_and_provenance() -> None:
    candidate = make_candidate()

    assert candidate.context == ("wu-001", "agent-001")
    assert candidate.evidence == ("evidence-001",)
    assert candidate.scope == "current project"
    assert candidate.potential_impact == ("resource-selection",)
    assert candidate.proposed_use == "candidate-selection heuristic"
