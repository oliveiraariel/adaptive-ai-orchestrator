import pytest

from domain.evidence_record import (
    EvidenceError,
    EvidenceRecord,
    EvidenceType,
)


def make_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        id="evidence-001",
        source="test-runner",
        evidence_type=EvidenceType.TEST,
        content="All domain tests passed.",
        confidence=1.0,
        timestamp="2026-08-22T17:42:00-03:00",
        references=("test-report-001",),
        metadata=("scope=domain",),
    )


def test_evidence_requires_id() -> None:
    with pytest.raises(EvidenceError):
        EvidenceRecord(
            id="",
            source="test-runner",
            evidence_type=EvidenceType.TEST,
            content="passed",
        )


def test_evidence_requires_source() -> None:
    with pytest.raises(EvidenceError):
        EvidenceRecord(
            id="evidence-001",
            source="",
            evidence_type=EvidenceType.TEST,
            content="passed",
        )


def test_evidence_requires_content() -> None:
    with pytest.raises(EvidenceError):
        EvidenceRecord(
            id="evidence-001",
            source="test-runner",
            evidence_type=EvidenceType.TEST,
            content="",
        )


def test_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(EvidenceError):
        EvidenceRecord(
            id="evidence-001",
            source="test-runner",
            evidence_type=EvidenceType.TEST,
            content="passed",
            confidence=1.1,
        )


def test_evidence_preserves_provenance_and_metadata() -> None:
    evidence = make_evidence()

    assert evidence.id == "evidence-001"
    assert evidence.source == "test-runner"
    assert evidence.evidence_type is EvidenceType.TEST
    assert evidence.content == "All domain tests passed."
    assert evidence.confidence == 1.0
    assert evidence.references == ("test-report-001",)
    assert evidence.metadata == ("scope=domain",)
