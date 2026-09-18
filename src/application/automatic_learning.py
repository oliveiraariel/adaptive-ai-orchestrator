from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from application.incident_management import (
    IncidentLifecycleManager,
    KnowledgeDisseminationPlanner,
    KnowledgePromotionPolicy,
)
from application.problem_solving_learning import (
    ProblemSolvingLearningStore,
    ValidatedKnowledgeStore,
)
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
    validated_knowledge_recorded: bool
    dissemination_completed: tuple[str, ...]
    consistency_passed: bool
    closed: bool
    incorporation_refs: tuple[str, ...]
    problem: str
    solution: str
    validation_refs: tuple[str, ...]


class AutomaticLearningCycle:
    """Turn a successful incident retest into incorporated governed learning.

    Every successful retest can produce learning, but not every lesson belongs
    globally. The cycle classifies scope, records sanitized runtime evidence,
    promotes validated knowledge with explicit consumer targets, verifies that
    the promoted lesson contains the required targets/evidence, marks those
    runtime dissemination targets complete, and closes the incident only after
    consistency evidence exists. Source-controlled curation may still follow,
    but it is not required for workers to consume the validated lesson.
    """

    def __init__(
        self,
        *,
        registry: FileIncidentRegistry | None = None,
        learning_store: ProblemSolvingLearningStore | None = None,
        promotion_policy: KnowledgePromotionPolicy | None = None,
        dissemination_planner: KnowledgeDisseminationPlanner | None = None,
        validated_store: ValidatedKnowledgeStore | None = None,
    ) -> None:
        self.registry = registry or FileIncidentRegistry()
        self.learning_store = learning_store or ProblemSolvingLearningStore.from_env()
        self.promotion_policy = promotion_policy or KnowledgePromotionPolicy()
        self.dissemination_planner = dissemination_planner or KnowledgeDisseminationPlanner()
        self.validated_store = validated_store or ValidatedKnowledgeStore.from_env()

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
        lesson_id = f"incident-{dispositioned.fingerprint[:12]}"
        validated_recorded = self.validated_store.record(
            lesson_id=lesson_id,
            title=self._safe_learning_text(
                f"{dispositioned.component}: validated incident learning"
            ),
            trigger=self._safe_learning_text(
                f"{dispositioned.category} in {dispositioned.component}: {dispositioned.symptom}"
            ),
            guidance=self._safe_learning_text(dispositioned.fix_summary),
            result=self._safe_learning_text(
                "The remediation passed the successful retest evidence attached to this incident."
            ),
            scope=scope.value,
            targets=targets,
            evidence=refs,
            project_id=dispositioned.project_id,
        )
        dissemination_completed: tuple[str, ...] = ()
        consistency_passed = False
        closed = False
        incorporation_refs: tuple[str, ...] = ()

        if validated_recorded:
            current = self._require(incident_id)
            for target in current.dissemination_targets:
                lifecycle.mark_disseminated(incident_id, target)
            current = self._require(incident_id)
            dissemination_completed = current.dissemination_completed

            if self.validated_store.has_lesson(
                lesson_id,
                targets=current.dissemination_targets,
                evidence=refs,
            ):
                incorporation_refs = (
                    f"validated-runtime-knowledge:{lesson_id}",
                    *(
                        f"learning-target:{target}"
                        for target in current.dissemination_targets
                    ),
                )
                lifecycle.mark_consistency(
                    incident_id,
                    passed=True,
                    evidence_refs=incorporation_refs,
                )
                consistency_passed = True
                lifecycle.close(incident_id)
                closed = True
            else:
                lifecycle.mark_consistency(
                    incident_id,
                    passed=False,
                    evidence_refs=(),
                )

        self.registry.append_event(
            incident_id,
            "automatic_learning_triggered",
            {
                "trigger": trigger,
                "scope": scope.value,
                "target_count": len(targets),
                "runtime_candidate_recorded": recorded,
                "validated_knowledge_recorded": validated_recorded,
                "dissemination_completed": len(dissemination_completed),
                "consistency_passed": consistency_passed,
                "closed": closed,
            },
        )
        if closed:
            self.registry.append_event(
                incident_id,
                "automatic_learning_completed",
                {
                    "scope": scope.value,
                    "target_count": len(targets),
                    "incorporation_ref_count": len(incorporation_refs),
                },
            )
        return LearningIncorporationReport(
            incident_id=incident_id,
            trigger=trigger,
            scope=scope,
            targets=targets,
            candidate=candidate,
            runtime_candidate_recorded=recorded,
            validated_knowledge_recorded=validated_recorded,
            dissemination_completed=dissemination_completed,
            consistency_passed=consistency_passed,
            closed=closed,
            incorporation_refs=incorporation_refs,
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
