from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class EvidenceError(ValueError):
    """Raised when an EvidenceRecord invariant is violated."""


class EvidenceType(str, Enum):
    OBSERVATION = "OBSERVATION"
    TEST = "TEST"
    RESULT = "RESULT"
    DECISION = "DECISION"
    EXECUTION = "EXECUTION"
    TELEMETRY = "TELEMETRY"


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    source: str
    evidence_type: EvidenceType
    content: str
    confidence: float | None = None
    timestamp: str | None = None
    references: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise EvidenceError("EvidenceRecord id must not be empty.")

        if not self.source.strip():
            raise EvidenceError("EvidenceRecord source must not be empty.")

        if not self.content.strip():
            raise EvidenceError("EvidenceRecord content must not be empty.")

        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise EvidenceError(
                "EvidenceRecord confidence must be between 0.0 and 1.0."
            )
