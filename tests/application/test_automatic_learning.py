from application.automatic_learning import AutomaticLearningCycle
from application.incident_management import IncidentLifecycleManager
from application.problem_solving_learning import (
    ProblemSolvingLearningStore,
    ValidatedKnowledgeStore,
)
from domain.incident import IncidentSeverity, LearningScope
from domain.learning_analysis import SuccessfulRetestLearningAnalysis
from infrastructure.incident_registry import FileIncidentRegistry


def test_successful_retest_triggers_scoped_learning_and_dissemination(tmp_path):
    registry = FileIncidentRegistry(root=tmp_path / "incidents")
    incident = registry.create_or_recur(
        category="runtime-failure",
        component="project-orchestration",
        symptom="Worker state was believed active after liveness evidence was gone.",
        severity=IncidentSeverity.HIGH,
        source="human-intervention",
        project_id="adaptive-ai-orchestrator",
        orchestration_id="orch-1",
        work_unit_id="U6",
        blocking=True,
        topics=("debugging", "recovery", "orchestration"),
    )
    assert incident is not None
    lifecycle = IncidentLifecycleManager(registry)
    lifecycle.confirm_root_cause(
        incident.id,
        root_cause="Conversational state was treated as stronger than correlated persistent liveness.",
        confidence=0.95,
    )
    lifecycle.record_fix(
        incident.id,
        fix_summary="Reconcile Result Store, active execution identity, lease and heartbeat before redispatch.",
    )

    learning_store = ProblemSolvingLearningStore(tmp_path / "learning.jsonl")
    validated_store = ValidatedKnowledgeStore(tmp_path / "validated.jsonl")
    report = AutomaticLearningCycle(
        registry=registry,
        learning_store=learning_store,
        validated_store=validated_store,
    ).successful_retest(
        incident.id,
        validation_refs=("tests/test_liveness.py::test_persisted_state_wins",),
    )

    assert report.scope is LearningScope.ARCHITECTURAL
    assert report.runtime_candidate_recorded is True
    assert report.validated_knowledge_recorded is True
    assert report.consistency_passed is True
    assert report.closed is True
    assert set(report.dissemination_completed) == set(report.targets)
    assert report.incorporation_refs
    assert "adaptive:problem-solving" in report.targets
    assert "skills:engineering-lifecycle" in report.targets
    updated = registry.get(incident.id)
    assert updated is not None
    assert updated.validation_refs
    assert updated.learning_scope is LearningScope.ARCHITECTURAL
    assert updated.status.value == "CLOSED"
    assert updated.consistency_check_passed is True
    assert set(updated.dissemination_completed) == set(updated.dissemination_targets)
    assert learning_store.path.read_text(encoding="utf-8").strip()
    assert validated_store.path.read_text(encoding="utf-8").strip()


def test_local_only_successful_retest_closes_without_leaking_reusable_knowledge(tmp_path):
    registry = FileIncidentRegistry(root=tmp_path / "incidents-local")
    incident = registry.create_or_recur(
        category="successful-retest",
        component="project-only-form",
        symptom="A one-off project form label failed a retest.",
        severity=IncidentSeverity.LOW,
        source="orchestrator-retest",
        project_id="project-a",
        orchestration_id="orch-local",
        work_unit_id="U-local",
        blocking=False,
        topics=("testing",),
    )
    assert incident is not None
    lifecycle = IncidentLifecycleManager(registry)
    lifecycle.confirm_root_cause(
        incident.id,
        root_cause="A project-local label had the wrong literal text.",
        confidence=0.95,
    )
    lifecycle.record_fix(
        incident.id,
        fix_summary="Correct the one project-local literal label.",
    )

    provisional = ProblemSolvingLearningStore(tmp_path / "local-provisional.jsonl")
    validated = ValidatedKnowledgeStore(tmp_path / "local-validated.jsonl")
    analysis = SuccessfulRetestLearningAnalysis(
        problem_summary="One project-local literal label was wrong.",
        root_cause="The project-local literal text was incorrect.",
        solution_summary="Correct the literal label.",
        learning_statement="This correction is too local to reuse outside the incident history.",
        scope=LearningScope.LOCAL_ONLY,
        target_hints=("skills:debugging", "adaptive:problem-solving"),
        confidence=0.96,
        should_promote=False,
        evidence_rationale="The evidence concerns only one literal label in one project.",
    )

    report = AutomaticLearningCycle(
        registry=registry,
        learning_store=provisional,
        validated_store=validated,
    ).successful_retest(
        incident.id,
        validation_refs=("test:project-local-label",),
        analysis=analysis,
    )

    assert report.scope is LearningScope.LOCAL_ONLY
    assert report.targets == ()
    assert report.runtime_candidate_recorded is False
    assert report.validated_knowledge_recorded is False
    assert report.consistency_passed is True
    assert report.closed is True
    assert not provisional.path.exists()
    assert not validated.path.exists()
