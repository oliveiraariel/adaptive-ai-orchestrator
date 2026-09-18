from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class IncidentStatus(str, Enum):
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_CANDIDATE = "ROOT_CAUSE_CANDIDATE"
    ROOT_CAUSE_CONFIRMED = "ROOT_CAUSE_CONFIRMED"
    FIX_IN_PROGRESS = "FIX_IN_PROGRESS"
    FIX_IMPLEMENTED = "FIX_IMPLEMENTED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    LEARNING_PENDING = "LEARNING_PENDING"
    KNOWLEDGE_PROMOTED = "KNOWLEDGE_PROMOTED"
    DISSEMINATING = "DISSEMINATING"
    CONSISTENCY_CHECK = "CONSISTENCY_CHECK"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"
    MITIGATED = "MITIGATED"
    WAIVED = "WAIVED"
    REOPENED = "REOPENED"


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LearningScope(str, Enum):
    UNDECIDED = "UNDECIDED"
    LOCAL_ONLY = "LOCAL_ONLY"
    PROJECT_SPECIFIC = "PROJECT_SPECIFIC"
    RUNTIME_SPECIFIC = "RUNTIME_SPECIFIC"
    PROVIDER_SPECIFIC = "PROVIDER_SPECIFIC"
    GENERALIZABLE = "GENERALIZABLE"
    ARCHITECTURAL = "ARCHITECTURAL"
    SECURITY_CRITICAL = "SECURITY_CRITICAL"


_TERMINAL = {IncidentStatus.CLOSED, IncidentStatus.WAIVED}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Incident:
    id: str
    fingerprint: str
    title: str
    category: str
    component: str
    symptom: str
    severity: IncidentSeverity
    source: str
    status: IncidentStatus = IncidentStatus.DETECTED
    detected_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    project_id: str = ""
    orchestration_id: str = ""
    work_unit_id: str = ""
    execution_id: str = ""
    runtime: str = ""
    blocking: bool = False
    recurrence_count: int = 1
    root_cause_confidence: float = 0.0
    local_evidence_exhausted: bool = False
    external_research_allowed: bool = True
    research_attempt_count: int = 0
    last_research_at: str = ""
    root_cause: str = ""
    fix_summary: str = ""
    validation_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    learning_scope: LearningScope = LearningScope.UNDECIDED
    dissemination_targets: tuple[str, ...] = ()
    dissemination_completed: tuple[str, ...] = ()
    consistency_check_passed: bool = False
    consistency_refs: tuple[str, ...] = ()
    last_progress_at: str = field(default_factory=utc_now)

    @property
    def is_active(self) -> bool:
        return self.status not in _TERMINAL

    def touch(self, **changes: Any) -> "Incident":
        progress_at = changes.pop("last_progress_at", utc_now())
        return replace(
            self,
            **changes,
            updated_at=utc_now(),
            last_progress_at=progress_at,
        )

    def with_status(self, status: IncidentStatus) -> "Incident":
        return replace(self, status=status, updated_at=utc_now(), last_progress_at=utc_now())

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "category": self.category,
            "component": self.component,
            "symptom": self.symptom,
            "severity": self.severity.value,
            "source": self.source,
            "status": self.status.value,
            "detected_at": self.detected_at,
            "updated_at": self.updated_at,
            "project_id": self.project_id,
            "orchestration_id": self.orchestration_id,
            "work_unit_id": self.work_unit_id,
            "execution_id": self.execution_id,
            "runtime": self.runtime,
            "blocking": self.blocking,
            "recurrence_count": self.recurrence_count,
            "root_cause_confidence": self.root_cause_confidence,
            "local_evidence_exhausted": self.local_evidence_exhausted,
            "external_research_allowed": self.external_research_allowed,
            "research_attempt_count": self.research_attempt_count,
            "last_research_at": self.last_research_at,
            "root_cause": self.root_cause,
            "fix_summary": self.fix_summary,
            "validation_refs": list(self.validation_refs),
            "evidence_refs": list(self.evidence_refs),
            "topics": list(self.topics),
            "learning_scope": self.learning_scope.value,
            "dissemination_targets": list(self.dissemination_targets),
            "dissemination_completed": list(self.dissemination_completed),
            "consistency_check_passed": self.consistency_check_passed,
            "consistency_refs": list(self.consistency_refs),
            "last_progress_at": self.last_progress_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Incident":
        return cls(
            id=str(payload["id"]),
            fingerprint=str(payload["fingerprint"]),
            title=str(payload.get("title", "")),
            category=str(payload.get("category", "")),
            component=str(payload.get("component", "")),
            symptom=str(payload.get("symptom", "")),
            severity=IncidentSeverity(str(payload.get("severity", "MEDIUM"))),
            source=str(payload.get("source", "")),
            status=IncidentStatus(str(payload.get("status", "DETECTED"))),
            detected_at=str(payload.get("detected_at", utc_now())),
            updated_at=str(payload.get("updated_at", utc_now())),
            project_id=str(payload.get("project_id", "")),
            orchestration_id=str(payload.get("orchestration_id", "")),
            work_unit_id=str(payload.get("work_unit_id", "")),
            execution_id=str(payload.get("execution_id", "")),
            runtime=str(payload.get("runtime", "")),
            blocking=bool(payload.get("blocking", False)),
            recurrence_count=max(1, int(payload.get("recurrence_count", 1))),
            root_cause_confidence=float(payload.get("root_cause_confidence", 0.0)),
            local_evidence_exhausted=bool(payload.get("local_evidence_exhausted", False)),
            external_research_allowed=bool(payload.get("external_research_allowed", True)),
            research_attempt_count=max(0, int(payload.get("research_attempt_count", 0))),
            last_research_at=str(payload.get("last_research_at", "")),
            root_cause=str(payload.get("root_cause", "")),
            fix_summary=str(payload.get("fix_summary", "")),
            validation_refs=tuple(str(x) for x in payload.get("validation_refs", []) if str(x)),
            evidence_refs=tuple(str(x) for x in payload.get("evidence_refs", []) if str(x)),
            topics=tuple(str(x) for x in payload.get("topics", []) if str(x)),
            learning_scope=LearningScope(str(payload.get("learning_scope", "UNDECIDED"))),
            dissemination_targets=tuple(str(x) for x in payload.get("dissemination_targets", []) if str(x)),
            dissemination_completed=tuple(str(x) for x in payload.get("dissemination_completed", []) if str(x)),
            consistency_check_passed=bool(payload.get("consistency_check_passed", False)),
            consistency_refs=tuple(str(x) for x in payload.get("consistency_refs", []) if str(x)),
            last_progress_at=str(payload.get("last_progress_at", utc_now())),
        )
