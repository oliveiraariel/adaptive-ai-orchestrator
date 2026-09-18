from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from application.automatic_learning import (
    AutomaticLearningCycle,
    LearningIncorporationReport,
)
from application.incident_management import (
    IncidentLifecycleManager,
    IncidentSentinel,
    IncidentSignal,
)
from application.investigation_strategy import (
    RecoveryStrategist,
    RecoveryStrategyRequest,
)
from domain.incident import Incident, IncidentSeverity, IncidentStatus
from domain.investigation import RecoveryStrategyAnalysis
from infrastructure.incident_registry import FileIncidentRegistry


@dataclass(frozen=True)
class RecoveryCycleResult:
    incident_id: str
    recovery_epoch: int
    analysis: RecoveryStrategyAnalysis


class PersistentRecoveryCoordinator:
    """Coordinate incident-backed strategic recovery without stealing authority.

    The orchestrator owns dispatch and graph mutation. This coordinator owns only
    the bounded investigation/reanalysis step and the incident/learning lifecycle
    around it.
    """

    def __init__(
        self,
        *,
        strategist: RecoveryStrategist,
        registry: FileIncidentRegistry | None = None,
        learning_cycle: AutomaticLearningCycle | None = None,
    ) -> None:
        self.registry = registry or FileIncidentRegistry()
        self.strategist = strategist
        self.learning_cycle = learning_cycle or AutomaticLearningCycle(
            registry=self.registry
        )
        self.sentinel = IncidentSentinel(self.registry)

    def analyze(
        self,
        *,
        project_objective: str,
        orchestration_id: str,
        work_unit_id: str,
        work_unit_objective: str,
        state_summary: str,
        project_id: str = "",
        attempt_history: Iterable[str],
        constraints: Iterable[str] = (),
        agent: str = "main",
        failure_class: str = "strategy-exhausted",
    ) -> RecoveryCycleResult:
        incident = self.registry.find_active_by_work_unit(
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
        )
        if incident is None:
            incident = self.sentinel.record(
                IncidentSignal(
                    category="work-unit-recovery",
                    component=work_unit_id,
                    symptom=(
                        f"{failure_class}: Work Unit requires strategic reanalysis "
                        "after returned/exhausted execution paths."
                    ),
                    severity=IncidentSeverity.HIGH,
                    topics=("recovery", "orchestration", "debugging"),
                    blocking=True,
                ),
                source="orchestrator",
                orchestration_id=orchestration_id,
                work_unit_id=work_unit_id,
                runtime="adaptive",
                project_id=project_id,
            )
        if incident is None:
            raise RuntimeError("Unable to create persistent recovery incident")

        epoch = incident.resolution_epoch + 1
        request = RecoveryStrategyRequest(
            project_objective=project_objective,
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            work_unit_objective=work_unit_objective,
            state_summary=state_summary,
            attempt_history=tuple(attempt_history),
            constraints=tuple(constraints),
            agent=agent,
            recovery_epoch=epoch,
        )
        analysis = self.strategist.analyze(request)
        recommended = analysis.recommended_path
        attempted_paths = incident.attempted_path_ids
        if recommended is not None and recommended.id not in attempted_paths:
            attempted_paths = (*attempted_paths, recommended.id)

        updated = replace(
            incident,
            status=IncidentStatus.INVESTIGATING,
            resolution_epoch=epoch,
            attempted_path_ids=attempted_paths,
            root_cause=incident.root_cause or analysis.problem_summary[:500],
            root_cause_confidence=max(
                incident.root_cause_confidence,
                min(analysis.confidence, 0.89),
            ),
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(
            updated.id,
            "recovery_strategy_analyzed",
            {
                "recovery_epoch": epoch,
                "failure_class": analysis.failure_class,
                "problem_summary": analysis.problem_summary[:500],
                "recommended_path_id": analysis.recommended_path_id[:120],
                "recommended_path_title": (
                    recommended.title[:240] if recommended is not None else ""
                ),
                "recommended_path_rationale": (
                    recommended.rationale[:500] if recommended is not None else ""
                ),
                "disposition": analysis.disposition.value,
                "human_decision_required": analysis.human_decision_required,
                "external_research_required": analysis.external_research_required,
                "confidence": analysis.confidence,
            },
        )
        return RecoveryCycleResult(
            incident_id=updated.id,
            recovery_epoch=epoch,
            analysis=analysis,
        )

    def successful_retest(
        self,
        *,
        orchestration_id: str,
        work_unit_id: str,
        validation_refs: Iterable[str],
    ) -> LearningIncorporationReport | None:
        incident = self.registry.find_active_by_work_unit(
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
        )
        if incident is None:
            return None

        events = self.registry.read_events(incident.id)
        last_analysis: dict[str, object] | None = None
        for event in reversed(events):
            if event.get("event_type") == "recovery_strategy_analyzed":
                last_analysis = event
                break

        lifecycle = IncidentLifecycleManager(self.registry)
        current = self.registry.get(incident.id)
        assert current is not None
        if not current.root_cause:
            lifecycle.confirm_root_cause(
                incident.id,
                root_cause=(
                    str((last_analysis or {}).get("problem_summary") or current.symptom)
                ),
                confidence=float((last_analysis or {}).get("confidence") or 0.7),
            )
        else:
            current = self.registry.get(incident.id)
            assert current is not None
            if current.status not in {
                IncidentStatus.ROOT_CAUSE_CONFIRMED,
                IncidentStatus.FIX_IN_PROGRESS,
                IncidentStatus.FIX_IMPLEMENTED,
                IncidentStatus.VALIDATING,
                IncidentStatus.VALIDATED,
                IncidentStatus.LEARNING_PENDING,
                IncidentStatus.KNOWLEDGE_PROMOTED,
                IncidentStatus.DISSEMINATING,
                IncidentStatus.CONSISTENCY_CHECK,
            }:
                lifecycle.transition(
                    incident.id,
                    IncidentStatus.ROOT_CAUSE_CONFIRMED,
                    note="successful retest confirmed recovery analysis was causally useful",
                )

        current = self.registry.get(incident.id)
        assert current is not None
        if not current.fix_summary:
            title = str((last_analysis or {}).get("recommended_path_title") or "")
            rationale = str((last_analysis or {}).get("recommended_path_rationale") or "")
            fix_summary = " - ".join(item for item in (title, rationale) if item)
            lifecycle.record_fix(
                incident.id,
                fix_summary=fix_summary or "Recovery path produced an accepted retest.",
            )

        return self.learning_cycle.successful_retest(
            incident.id,
            validation_refs=validation_refs,
            trigger="successful-retest-after-investigation",
        )

    def pause(self, incident_id: str, *, reason: str) -> Incident:
        incident = self._require(incident_id)
        updated = replace(
            incident,
            status=IncidentStatus.PAUSED_BY_DEVELOPER,
            pause_reason=" ".join(reason.split())[:500],
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(
            incident_id,
            "recovery_paused_by_developer",
            {"reason": updated.pause_reason},
        )
        return updated

    def resume(self, incident_id: str) -> Incident:
        incident = self._require(incident_id)
        if incident.status is not IncidentStatus.PAUSED_BY_DEVELOPER:
            return incident
        updated = replace(
            incident,
            status=IncidentStatus.INVESTIGATING,
            pause_reason="",
        ).touch()
        self.registry.save(updated)
        self.registry.append_event(incident_id, "recovery_resumed")
        return updated

    def stop_report(self, incident_id: str) -> dict[str, object]:
        incident = self._require(incident_id)
        events = self.registry.read_events(incident_id)
        last_strategy = next(
            (
                event
                for event in reversed(events)
                if event.get("event_type") == "recovery_strategy_analyzed"
            ),
            {},
        )
        return {
            "incident_id": incident.id,
            "status": incident.status.value,
            "problem": incident.root_cause or incident.symptom,
            "resolution_epoch": incident.resolution_epoch,
            "attempted_path_ids": list(incident.attempted_path_ids),
            "last_recommended_path_id": last_strategy.get("recommended_path_id", ""),
            "last_recommended_path_title": last_strategy.get("recommended_path_title", ""),
            "pause_reason": incident.pause_reason,
            "validation_refs": list(incident.validation_refs),
            "learning_scope": incident.learning_scope.value,
            "dissemination_targets": list(incident.dissemination_targets),
            "dissemination_completed": list(incident.dissemination_completed),
        }

    def _require(self, incident_id: str) -> Incident:
        incident = self.registry.get(incident_id)
        if incident is None:
            raise ValueError(f"Unknown incident: {incident_id}")
        return incident
