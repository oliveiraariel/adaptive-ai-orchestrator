from domain.incident import IncidentSeverity, IncidentStatus, LearningScope
from infrastructure.incident_registry import FileIncidentRegistry
from application.incident_management import (
    IncidentLifecycleManager,
    IncidentSentinel,
    KnowledgeDisseminationPlanner,
    KnowledgePromotionPolicy,
    parse_worker_defect_signal,
)


def test_worker_signal_becomes_persistent_incident(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    sentinel = IncidentSentinel(registry)
    output = (
        'ADAPTIVE_DEFECT_SIGNAL: {"category":"result-transport","component":"runtime-adapter",'
        '"symptom":"runtime completed but authoritative result is missing","severity":"HIGH",'
        '"topics":["transport","recovery","debugging"],"blocking":true}'
    )
    incident = sentinel.observe_worker_output(
        output,
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        execution_id="exec-1",
        runtime="future-runtime",
    )
    assert incident is not None
    assert incident.severity is IncidentSeverity.HIGH
    assert incident.runtime == "future-runtime"
    assert registry.get(incident.id) is not None
    assert (tmp_path / "incidents" / incident.id / "timeline.jsonl").is_file()


def test_repeated_signal_reuses_active_incident_and_increases_recurrence(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    sentinel = IncidentSentinel(registry)
    for orch in ("orch-1", "orch-2"):
        incident = sentinel.observe_runtime_failure(
            "result integrity mismatch",
            orchestration_id=orch,
            work_unit_id="wu",
            runtime="runtime-x",
        )
    assert incident is not None
    assert len(registry.list_active()) == 1
    assert incident.recurrence_count == 2


def test_incident_cannot_close_before_learning_and_consistency(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    sentinel = IncidentSentinel(registry)
    incident = sentinel.observe_runtime_failure(
        "transport mismatch",
        orchestration_id="orch",
        work_unit_id="wu",
        runtime="runtime-x",
        blocking=True,
    )
    assert incident is not None
    lifecycle = IncidentLifecycleManager(registry)
    lifecycle.confirm_root_cause(
        incident.id,
        root_cause="control-plane summary was treated as authoritative result",
        confidence=0.95,
    )
    lifecycle.record_fix(
        incident.id,
        fix_summary="use durable result store and reference-only fan-in",
    )
    lifecycle.validate_fix(incident.id, validation_refs=("test:small-medium-large",))
    try:
        lifecycle.close(incident.id)
    except ValueError as exc:
        assert "learning disposition" in str(exc)
    else:
        raise AssertionError("incident should not close before learning disposition")


def test_generalizable_incident_gets_dissemination_targets(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    incident = IncidentSentinel(registry).record(
        signal=parse_worker_defect_signal(
            'ADAPTIVE_DEFECT_SIGNAL: {"category":"result-transport","component":"adapter",'
            '"symptom":"result missing after runtime completion","severity":"HIGH",'
            '"topics":["result-transport","recovery","testing"],"blocking":false}'
        ),
        source="worker",
    )
    assert incident is not None
    policy = KnowledgePromotionPolicy()
    scope = policy.classify(incident)
    assert scope in {LearningScope.GENERALIZABLE, LearningScope.ARCHITECTURAL}
    targets = KnowledgeDisseminationPlanner().targets(incident, scope)
    assert "adaptive:problem-solving" in targets
    assert "skills:debugging" in targets
    assert "skills:testing" in targets
