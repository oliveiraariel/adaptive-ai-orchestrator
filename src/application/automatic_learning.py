from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from application.incident_management import (
    IncidentLifecycleManager,
    KnowledgeDisseminationPlanner,
    KnowledgePromotionPolicy,
)
from application.problem_solving_learning import ProblemSolvingLearningStore
from domain.incident import Incident, LearningScope
from domain.learning_candidate import LearningCandidate
from infrastructure.incident_registry import FileIncidentRegistry


@dataclass(frozen=True)
class LearningIncorporationReport:
    incident_id: str
    trigger: str
    scope: LearningScope
    targets: tuple[str, ...]
    candidate: LearningCandidate
    runtime_candidate_recorded: bool
    problem: str
    solution: str
    validation_refs: tuple[str, ...]


class AutomaticLearningCycle:
    """Turn a successful incident retest into a governed learning obligation.

    Every successful retest can produce learning, but not every lesson belongs
    globally. The cycle classifies scope, records a sanitized runtime candidate,
    plans dissemination targets, and leaves repository/Skill mutations as
    explicit governed obligations whose completion is tracked by the incident.
    """

    def __init__(
        self,
        *,
        registry: FileIncidentRegistry | None = None,
        learning_store: ProblemSolvingLearningStore | None = None,
        promotion_policy: KnowledgePromotionPolicy | None = None,
        dissemination_planner: KnowledgeDisseminationPlanner | None = None,
    ) -> None:
        self.registry = registry or FileIncidentRegistry()
        self.learning_store = learning_store or ProblemSolvingLearningStore.from_env()
        self.promotion_policy = promotion_policy or KnowledgePromotionPolicy()
        self.dissemination_planner = dissemination_planner or KnowledgeDisseminationPlanner()

    def successful_retest(
        self,
        incident_id: str,
        *,
        validation_refs: Iterable[str],
        trigger: str = "successful-retest",
    ) -> LearningIncorporationReport:
        lifecycle = IncidentLifecycleManager(self.registry)
        incident = self._require(incident_id)
        refs = tuple(str(item).strip()[:300] for item in validation_refs if str(item).strip())
        if not refs:
            raise ValueError("successful retest requires validation evidence")
        if not incident.root_cause or not incident.fix_summary:
            raise ValueError(
                "root cause and fix summary must be recorded before automatic learning"
            )

        validated = lifecycle.validate_fix(incident_id, validation_refs=refs)
        scope = self.promotion_policy.classify(validated)
        targets = self.dissemination_planner.targets(validated, scope)
        dispositioned = lifecycle.set_learning_scope(
            incident_id,
            scope=scope,
            dissemination_targets=targets,
        )
        candidate = lifecycle.extract_learning_candidate(incident_id)

        recorded = self.learning_store.record(
            strategy_id=f"incident-{dispositioned.fingerprint[:12]}",
            trigger=self._safe_learning_text(
                f"{dispositioned.category} in {dispositioned.component}: {dispositioned.symptom}"
            ),
            action=self._safe_learning_text(dispositioned.fix_summary),
            result=self._safe_learning_text(
                "Successful retest validated the remediation; learning dissemination is now governed by incident targets."
            ),
            orchestration_id=dispositioned.orchestration_id or dispositioned.id,
            work_unit_id=dispositioned.work_unit_id or "incident-learning",
            source="successful-incident-retest",
        )
        self.registry.append_event(
            incident_id,
            "automatic_learning_triggered",
            {
                "trigger": trigger,
                "scope": scope.value,
                "target_count": len(targets),
                "runtime_candidate_recorded": recorded,
            },
        )
        return LearningIncorporationReport(
            incident_id=incident_id,
            trigger=trigger,
            scope=scope,
            targets=targets,
            candidate=candidate,
            runtime_candidate_recorded=recorded,
            problem=dispositioned.root_cause,
            solution=dispositioned.fix_summary,
            validation_refs=refs,
        )

    def _require(self, incident_id: str) -> Incident:
        incident = self.registry.get(incident_id)
        if incident is None:
            raise ValueError(f"Unknown incident: {incident_id}")
        return incident

    @staticmethod
    def _safe_learning_text(value: str) -> str:
        return " ".join(value.replace("\r", " ").replace("\n", " ").split())[:500]
