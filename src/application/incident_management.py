from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable

from domain.incident import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    LearningScope,
)
from domain.learning_candidate import LearningCandidate
from domain.provider_incident import ProviderIncident
from infrastructure.incident_registry import FileIncidentRegistry


DEFECT_MARKER = "ADAPTIVE_DEFECT_SIGNAL:"


@dataclass(frozen=True)
class IncidentSignal:
    category: str
    component: str
    symptom: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    topics: tuple[str, ...] = ()
    blocking: bool = False


@dataclass(frozen=True)
class ResolutionDirective:
    incident_id: str
    pressure: int
    action: str
    reason: str
    external_research_allowed: bool = False


class IncidentSentinel:
    """Convert bounded defect signals from any intelligent/runtime layer into incidents.

    Workers may report observations, but Adaptive owns persistence, lifecycle,
    promotion and closure. The sentinel never stores the full worker output.
    """

    def __init__(self, registry: FileIncidentRegistry | None = None) -> None:
        self.registry = registry or FileIncidentRegistry()

    def observe_worker_output(
        self,
        output: str,
        *,
        orchestration_id: str,
        work_unit_id: str,
        execution_id: str = "",
        runtime: str = "",
        project_id: str = "",
    ) -> Incident | None:
        signal = parse_worker_defect_signal(output)
        if signal is None:
            return None
        return self.record(
            signal,
            source="worker",
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
            runtime=runtime,
            project_id=project_id,
        )

    def observe_runtime_failure(
        self,
        error: BaseException | str,
        *,
        orchestration_id: str,
        work_unit_id: str,
        execution_id: str = "",
        runtime: str = "",
        project_id: str = "",
        blocking: bool = False,
    ) -> Incident | None:
        message = str(error).strip()
        if not message:
            return None
        return self.record(
            IncidentSignal(
                category="runtime-failure",
                component=runtime or "agent-runtime",
                symptom=message[:500],
                severity=IncidentSeverity.HIGH if blocking else IncidentSeverity.MEDIUM,
                topics=("runtime", "recovery", "debugging"),
                blocking=blocking,
            ),
            source="runtime",
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
            runtime=runtime,
            project_id=project_id,
        )

    def observe_dispatch_failure(
        self,
        reason: str,
        *,
        orchestration_id: str,
        work_unit_id: str,
        runtime: str = "",
        project_id: str = "",
        blocking: bool = False,
    ) -> Incident | None:
        normalized = reason.strip()
        if not normalized or normalized in {
            "work-unit-not-ready",
            "human-action-work-unit",
            "concurrency-budget-exhausted",
        } or normalized.startswith("policy:"):
            return None
        return self.record(
            IncidentSignal(
                category="dispatch-failure",
                component=runtime or "execution-coordinator",
                symptom=normalized[:500],
                severity=IncidentSeverity.HIGH if blocking else IncidentSeverity.MEDIUM,
                topics=("runtime", "orchestration", "recovery"),
                blocking=blocking,
            ),
            source="orchestrator",
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            runtime=runtime,
            project_id=project_id,
        )

    def observe_provider_incident(
        self,
        provider_incident: ProviderIncident,
        *,
        orchestration_id: str = "",
        work_unit_id: str = "",
        execution_id: str = "",
        project_id: str = "",
    ) -> Incident | None:
        severity = IncidentSeverity.HIGH if not provider_incident.retryable else IncidentSeverity.MEDIUM
        return self.record(
            IncidentSignal(
                category=f"provider-{provider_incident.category}",
                component=f"{provider_incident.provider}/{provider_incident.model}",
                symptom=provider_incident.subtype,
                severity=severity,
                topics=("provider", provider_incident.category, "recovery"),
                blocking=not provider_incident.retryable,
            ),
            source="provider-classifier",
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
            runtime=provider_incident.provider,
            project_id=project_id,
        )

    def record(
        self,
        signal: IncidentSignal,
        *,
        source: str,
        orchestration_id: str = "",
        work_unit_id: str = "",
        execution_id: str = "",
        runtime: str = "",
        project_id: str = "",
    ) -> Incident | None:
        return self.registry.create_or_recur(
            category=signal.category,
            component=signal.component,
            symptom=signal.symptom,
            severity=signal.severity,
            source=source,
            project_id=project_id,
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
            runtime=runtime,
            blocking=signal.blocking,
            topics=signal.topics,
        )


class ResolutionPressureEngine:
    _severity = {
        IncidentSeverity.LOW: 10,
        IncidentSeverity.MEDIUM: 25,
        IncidentSeverity.HIGH: 45,
        IncidentSeverity.CRITICAL: 70,
    }

    def score(self, incident: Incident, *, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        try:
            detected = datetime.fromisoformat(incident.detected_at)
            age_hours = max(0.0, (now - detected).total_seconds() / 3600)
        except ValueError:
            age_hours = 0.0
        pressure = self._severity[incident.severity]
        pressure += 25 if incident.blocking else 0
        pressure += min(20, max(0, incident.recurrence_count - 1) * 4)
        pressure += min(15, int(age_hours // 6))
        pressure += 10 if incident.root_cause_confidence < 0.5 else 0
        if incident.status in {IncidentStatus.VALIDATED, IncidentStatus.LEARNING_PENDING}:
            pressure += 8
        if incident.status in {IncidentStatus.BLOCKED, IncidentStatus.MITIGATED}:
            pressure = max(10, pressure - 15)
        return max(0, min(100, pressure))


class IncidentLifecycleManager:
    """Govern the defect -> validation -> learning -> dissemination lifecycle."""

    def __init__(self, registry: FileIncidentRegistry) -> None:
        self.registry = registry

    def transition(self, incident_id: str, status: IncidentStatus, *, note: str = "") -> Incident:
        incident = self._require(incident_id)
        updated = incident.with_status(status)
        self.registry.save(updated)
        self.registry.append_event(incident_id, "status_changed", {
            "from": incident.status.value,
            "to": status.value,
            "note": note,
        })
        return updated

    def confirm_root_cause(self, incident_id: str, *, root_cause: str, confidence: float) -> Incident:
        incident = self._require(incident_id)
        if not root_cause.strip():
            raise ValueError("root_cause must not be blank")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        updated = replace(
            incident,
            root_cause=root_cause.strip()[:500],
            root_cause_confidence=confidence,
            status=IncidentStatus.ROOT_CAUSE_CONFIRMED,
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(incident_id, "root_cause_confirmed", {"confidence": confidence})
        return updated

    def record_fix(self, incident_id: str, *, fix_summary: str) -> Incident:
        incident = self._require(incident_id)
        if not fix_summary.strip():
            raise ValueError("fix_summary must not be blank")
        updated = replace(
            incident,
            fix_summary=fix_summary.strip()[:500],
            status=IncidentStatus.FIX_IMPLEMENTED,
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(incident_id, "fix_implemented")
        return updated

    def validate_fix(self, incident_id: str, *, validation_refs: Iterable[str]) -> Incident:
        incident = self._require(incident_id)
        refs = tuple(str(item).strip()[:300] for item in validation_refs if str(item).strip())
        if not refs:
            raise ValueError("validation evidence is required")
        if not incident.root_cause or not incident.fix_summary:
            raise ValueError("root cause and fix must be recorded before validation")
        updated = replace(
            incident,
            validation_refs=tuple(dict.fromkeys((*incident.validation_refs, *refs))),
            status=IncidentStatus.LEARNING_PENDING,
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(incident_id, "fix_validated", {"evidence_count": len(refs)})
        return updated

    def set_learning_scope(
        self,
        incident_id: str,
        *,
        scope: LearningScope,
        dissemination_targets: Iterable[str] = (),
    ) -> Incident:
        incident = self._require(incident_id)
        targets = tuple(dict.fromkeys(str(x).strip()[:120] for x in dissemination_targets if str(x).strip()))
        status = (
            IncidentStatus.KNOWLEDGE_PROMOTED
            if scope not in {LearningScope.UNDECIDED, LearningScope.LOCAL_ONLY}
            else IncidentStatus.CONSISTENCY_CHECK
        )
        updated = replace(
            incident,
            learning_scope=scope,
            dissemination_targets=targets,
            status=status,
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(incident_id, "learning_disposition", {
            "scope": scope.value,
            "target_count": len(targets),
        })
        return updated

    def mark_disseminated(self, incident_id: str, target: str) -> Incident:
        incident = self._require(incident_id)
        clean = target.strip()[:120]
        if clean not in incident.dissemination_targets:
            raise ValueError("target is not part of the dissemination plan")
        completed = tuple(dict.fromkeys((*incident.dissemination_completed, clean)))
        status = (
            IncidentStatus.CONSISTENCY_CHECK
            if set(completed) >= set(incident.dissemination_targets)
            else IncidentStatus.DISSEMINATING
        )
        updated = replace(incident, dissemination_completed=completed, status=status).touch()
        self.registry.save(updated)
        self.registry.append_event(incident_id, "knowledge_disseminated", {"target": clean})
        return updated

    def mark_consistency(
        self,
        incident_id: str,
        *,
        passed: bool,
        evidence_refs: Iterable[str] = (),
    ) -> Incident:
        incident = self._require(incident_id)
        refs = tuple(
            str(item).strip()[:300]
            for item in evidence_refs
            if str(item).strip()
        )
        if passed and not refs:
            raise ValueError("a passing consistency check requires evidence references")
        updated = replace(
            incident,
            consistency_check_passed=passed,
            consistency_refs=tuple(dict.fromkeys((*incident.consistency_refs, *refs))),
            status=IncidentStatus.CONSISTENCY_CHECK,
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(
            incident_id,
            "consistency_check",
            {"passed": passed, "evidence_count": len(refs)},
        )
        return updated

    def close(self, incident_id: str) -> Incident:
        incident = self._require(incident_id)
        if not incident.validation_refs:
            raise ValueError("validated evidence is required before closing an incident")
        if incident.learning_scope is LearningScope.UNDECIDED:
            raise ValueError("learning disposition must be decided before closing an incident")
        if set(incident.dissemination_completed) < set(incident.dissemination_targets):
            raise ValueError("dissemination must finish before closing an incident")
        if not incident.consistency_check_passed:
            raise ValueError("consistency check must pass before closing an incident")
        updated = incident.with_status(IncidentStatus.CLOSED)
        self.registry.save(updated)
        self.registry.append_event(incident_id, "incident_closed")
        return updated

    def extract_learning_candidate(self, incident_id: str) -> LearningCandidate:
        incident = self._require(incident_id)
        if not incident.root_cause or not incident.fix_summary or not incident.validation_refs:
            raise ValueError("incident is not validated enough for learning extraction")
        return LearningCandidate(
            observation=f"{incident.component}: {incident.root_cause}",
            context=(incident.category, *incident.topics),
            evidence=incident.validation_refs,
            scope=incident.learning_scope.value,
            confidence=max(incident.root_cause_confidence, 0.5),
            potential_impact=incident.topics,
            proposed_use=incident.fix_summary,
        )

    def _require(self, incident_id: str) -> Incident:
        incident = self.registry.get(incident_id)
        if incident is None:
            raise ValueError(f"Unknown incident: {incident_id}")
        return incident


class KnowledgePromotionPolicy:
    def classify(self, incident: Incident) -> LearningScope:
        topics = {item.casefold() for item in incident.topics}
        category = incident.category.casefold()
        if "security" in topics or "security" in category:
            return LearningScope.SECURITY_CRITICAL
        if any(item in topics for item in {"architecture", "protocol", "result-transport", "orchestration"}):
            return LearningScope.ARCHITECTURAL
        if incident.runtime and incident.runtime not in {"", "adaptive"}:
            if any(item in topics for item in {"provider", "runtime-specific"}):
                return LearningScope.RUNTIME_SPECIFIC
        if incident.recurrence_count >= 2 or len(topics & {"debugging", "testing", "recovery", "transport"}) >= 2:
            return LearningScope.GENERALIZABLE
        if incident.project_id:
            return LearningScope.PROJECT_SPECIFIC
        return LearningScope.LOCAL_ONLY


class KnowledgeDisseminationPlanner:
    _topic_targets = {
        "transport": ("adaptive:problem-solving", "adaptive:architecture", "skills:debugging", "skills:testing", "skills:software-architecture"),
        "result-transport": ("adaptive:problem-solving", "adaptive:architecture", "skills:debugging", "skills:testing", "skills:software-architecture"),
        "recovery": ("adaptive:problem-solving", "skills:debugging", "skills:project-handoff", "skills:engineering-lifecycle"),
        "runtime": ("adaptive:problem-solving", "skills:debugging", "skills:technical-research"),
        "provider": ("adaptive:provider-lessons", "skills:technical-research", "skills:debugging"),
        "security": ("adaptive:problem-solving", "skills:security-review", "skills:debugging"),
        "testing": ("adaptive:problem-solving", "skills:testing"),
        "debugging": ("adaptive:problem-solving", "skills:debugging"),
        "orchestration": ("adaptive:architecture", "skills:engineering-lifecycle", "skills:software-architecture"),
        "protocol": ("adaptive:architecture", "skills:engineering-lifecycle", "skills:software-architecture"),
    }

    def targets(self, incident: Incident, scope: LearningScope) -> tuple[str, ...]:
        if scope is LearningScope.LOCAL_ONLY:
            return ()
        targets = {"adaptive:incident-history"}
        if scope in {LearningScope.GENERALIZABLE, LearningScope.ARCHITECTURAL, LearningScope.SECURITY_CRITICAL}:
            targets.add("adaptive:problem-solving")
        for topic in incident.topics:
            targets.update(self._topic_targets.get(topic.casefold(), ()))
        if scope is LearningScope.PROJECT_SPECIFIC:
            targets.add("project:knowledge")
        return tuple(sorted(targets))


def parse_worker_defect_signal(output: str) -> IncidentSignal | None:
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith(DEFECT_MARKER):
            continue
        candidate = line[len(DEFECT_MARKER):].strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        required = {"category", "component", "symptom", "severity"}
        allowed = required | {"topics", "blocking"}
        if not required <= set(payload) or not set(payload) <= allowed:
            return None
        if any(not isinstance(payload[key], str) or not payload[key].strip() for key in required):
            return None
        try:
            severity = IncidentSeverity(payload["severity"].strip().upper())
        except ValueError:
            return None
        topics_raw = payload.get("topics", [])
        if not isinstance(topics_raw, list) or any(not isinstance(item, str) for item in topics_raw):
            return None
        blocking = payload.get("blocking", False)
        if not isinstance(blocking, bool):
            return None
        if any(len(payload[key]) > 500 or "\n" in payload[key] or "\r" in payload[key] for key in required):
            return None
        return IncidentSignal(
            category=payload["category"].strip()[:80],
            component=payload["component"].strip()[:120],
            symptom=payload["symptom"].strip()[:500],
            severity=severity,
            topics=tuple(item.strip()[:80] for item in topics_raw if item.strip())[:16],
            blocking=blocking,
        )
    return None
