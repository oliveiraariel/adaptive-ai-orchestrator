from __future__ import annotations

from application.incident_management import ResolutionDirective, ResolutionPressureEngine
from domain.incident import IncidentStatus, LearningScope
from infrastructure.incident_registry import FileIncidentRegistry


class IncidentSupervisor:
    """Turn persistent open incidents into bounded orchestration obligations."""

    def __init__(
        self,
        registry: FileIncidentRegistry | None = None,
        pressure: ResolutionPressureEngine | None = None,
    ) -> None:
        self.registry = registry or FileIncidentRegistry()
        self.pressure = pressure or ResolutionPressureEngine()

    def directives(self, *, limit: int = 5) -> tuple[ResolutionDirective, ...]:
        directives: list[ResolutionDirective] = []
        for incident in self.registry.list_active():
            score = self.pressure.score(incident)
            if incident.status in {
                IncidentStatus.LEARNING_PENDING,
                IncidentStatus.KNOWLEDGE_PROMOTED,
                IncidentStatus.DISSEMINATING,
                IncidentStatus.CONSISTENCY_CHECK,
            }:
                action = "complete-learning-dissemination-consistency"
                reason = "Validated incident still carries an unresolved learning obligation."
                research = False
            elif incident.root_cause:
                action = "validate-or-remediate-known-root-cause"
                reason = "Root cause exists but the incident has not completed validation."
                research = False
            elif incident.local_evidence_exhausted and incident.external_research_allowed:
                action = "external-research"
                reason = "Local evidence is exhausted while root cause remains unknown."
                research = True
            elif score >= 70:
                action = "diagnose-now"
                reason = "Resolution pressure is high."
                research = incident.external_research_allowed
            elif score >= 40:
                action = "diagnose-next-safe-slot"
                reason = "Resolution pressure is material and should compete with ordinary work."
                research = False
            else:
                action = "monitor-and-reconcile"
                reason = "Incident remains an active obligation but does not justify aggressive scheduling yet."
                research = False
            directives.append(
                ResolutionDirective(
                    incident_id=incident.id,
                    pressure=score,
                    action=action,
                    reason=reason,
                    external_research_allowed=research,
                )
            )
        directives.sort(key=lambda item: (-item.pressure, item.incident_id))
        return tuple(directives[:limit])

    def render_planner_obligations(self, *, limit: int = 5) -> str:
        by_id = {incident.id: incident for incident in self.registry.list_active()}
        directives = self.directives(limit=limit)
        if not directives:
            return ""
        lines = [
            "ACTIVE ADAPTIVE INCIDENT OBLIGATIONS:",
            "Unresolved incidents are persistent orchestration obligations; they must not disappear merely because a previous session ended.",
        ]
        for directive in directives:
            incident = by_id.get(directive.incident_id)
            if incident is None:
                continue
            lines.append(
                f"- {incident.id} pressure={directive.pressure}/100 severity={incident.severity.value} "
                f"status={incident.status.value} component={incident.component} category={incident.category}; "
                f"action={directive.action}; symptom={incident.symptom}"
            )
            if directive.external_research_allowed:
                lines.append(
                    "  * External authoritative research is allowed when local evidence is insufficient; attach findings as evidence, do not treat search output as validated knowledge."
                )
            if incident.learning_scope is not LearningScope.UNDECIDED:
                lines.append(
                    f"  * learning_scope={incident.learning_scope.value}; dissemination targets still govern closure."
                )
        lines.append(
            "Prioritize incident work against ordinary work using pressure, blocking impact, recurrence and safety. "
            "Research/diagnosis may be proactive; remediation remains bounded by the normal execution policy and side-effect authority."
        )
        return "\n".join(lines)
