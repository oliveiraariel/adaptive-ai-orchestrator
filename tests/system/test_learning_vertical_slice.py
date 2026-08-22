from domain.evidence_record import EvidenceRecord, EvidenceType
from domain.learning_candidate import (
    LearningCandidate,
    LearningValidationStatus,
)


def make_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        id="evidence-001",
        source="evaluation-001",
        evidence_type=EvidenceType.RESULT,
        content="TDD Skill produced accepted results on repeated Work Units.",
        confidence=0.9,
        references=("task-001", "task-002"),
    )


def make_candidate(evidence: EvidenceRecord) -> LearningCandidate:
    return LearningCandidate(
        observation="TDD Skill repeatedly improved accepted execution outcomes.",
        context=("project-001",),
        evidence=(evidence.id,),
        scope="project-001",
        confidence=0.85,
        potential_impact=("resource-selection",),
        proposed_use="consider TDD Skill during future resource selection",
    )


def test_learning_vertical_slice_creates_candidate_from_evidence() -> None:
    evidence = make_evidence()

    candidate = make_candidate(evidence)

    assert candidate.validation_status is LearningValidationStatus.UNVALIDATED
    assert candidate.evidence == ("evidence-001",)
    assert candidate.observation.startswith(
        "TDD Skill repeatedly improved"
    )


def test_learning_vertical_slice_requires_validation_before_promotion() -> None:
    evidence = make_evidence()
    candidate = make_candidate(evidence)

    under_validation = candidate.start_validation()
    validated = under_validation.validate()

    assert candidate.validation_status is LearningValidationStatus.UNVALIDATED
    assert under_validation.validation_status is (
        LearningValidationStatus.UNDER_VALIDATION
    )
    assert validated.validation_status is LearningValidationStatus.VALIDATED


def test_learning_vertical_slice_can_reject_candidate() -> None:
    evidence = make_evidence()
    candidate = make_candidate(evidence)

    rejected = candidate.reject()

    assert rejected.validation_status is LearningValidationStatus.REJECTED
    assert rejected.evidence == ("evidence-001",)
