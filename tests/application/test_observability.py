import json

from application.observability import JsonlObservabilitySink, canonical_observability_path


def test_jsonl_observability_sink_allowlists_fields(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    JsonlObservabilitySink(path).emit(
        "worker_dispatched",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        model="GPT-5.6 Luna",
        thinking="high",
        objective="must not persist",
        prompt="must not persist",
        token="must not persist",
    )
    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["event_type"] == "worker_dispatched"
    assert event["work_unit_id"] == "wu-1"
    assert event["thinking"] == "high"
    assert "prompt" not in event
    assert "token" not in event
    assert "objective" not in event


def test_jsonl_observability_sanitizes_nested_telemetry(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    JsonlObservabilitySink(path).emit(
        "work_unit_status_changed", orchestration_id="orch-1", work_unit_id="wu-1",
        usage={"input_tokens": 2, "prompt": "secret"},
        cost={"status": "actual", "usd": 0.01, "credential": "secret"},
    )
    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["usage"] == {"input_tokens": 2}
    assert event["cost"] == {"status": "actual", "usd": 0.01}


def test_jsonl_observability_drops_invalid_telemetry_shapes(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    JsonlObservabilitySink(path).emit(
        "work_unit_status_changed", orchestration_id="orch-1", work_unit_id="wu-1",
        usage="secret usage payload", cost=["secret cost payload"],
    )
    event = json.loads(path.read_text(encoding="utf-8"))
    assert "usage" not in event
    assert "cost" not in event


def test_canonical_path_uses_xdg_state_home(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("ADAPTIVE_OBSERVABILITY_LOG", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert canonical_observability_path() == tmp_path / "adaptive-ai-orchestrator" / "observability.jsonl"


def test_observability_override_wins(monkeypatch, tmp_path) -> None:
    override = tmp_path / "override.jsonl"
    monkeypatch.setenv("ADAPTIVE_OBSERVABILITY_LOG", str(override))
    assert canonical_observability_path() == override


def test_observability_accepts_recovery_and_learning_events(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    sink = JsonlObservabilitySink(path)

    sink.emit(
        "worker_recovered",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        execution_id="exec-1",
        external_id="run-1",
        status="RECOVERED",
    )
    sink.emit(
        "work_unit_reconciled",
        orchestration_id="orch-1",
        work_unit_id="wu-original",
        reconciled_by_work_unit_id="wu-fix",
        status="COMPLETED",
        verdict="ACCEPTED",
    )
    sink.emit(
        "recovery_strategy_analyzed",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        incident_id="INC-1",
        recovery_epoch=2,
        recommended_path_id="path-c",
        disposition="REPLAN_WITH_PREREQUISITE",
        confidence=0.9,
    )
    sink.emit(
        "work_unit_practical_test_ready",
        orchestration_id="orch-1",
        work_unit_id="wu-ui",
        execution_id="exec-ui",
        wave=7,
        status="COMPLETED",
        verdict="ACCEPTED",
    )
    sink.emit(
        "work_unit_recovery_skipped",
        orchestration_id="orch-1",
        work_unit_id="wu-returned",
        status="BLOCKED",
        reason="recovery-loop-disabled",
    )
    sink.emit(
        "recovery_human_question_requested",
        orchestration_id="orch-1",
        work_unit_id="wu-recovery",
        recovery_epoch=3,
        question="Qual comportamento visual deve prevalecer?",
        suggested_skills=["grill", "grill-me"],
        status="WAIT_HUMAN",
    )
    sink.emit(
        "orchestration_idle_watchdog_triggered",
        orchestration_id="orch-1",
        idle_seconds=31.5,
        active_execution_count=0,
        ready_work_unit_count=2,
        pending_replan=False,
        recovery_loop_mode="DISABLED",
    )
    sink.emit(
        "automatic_learning_triggered",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        incident_id="INC-1",
        scope="ARCHITECTURAL",
        targets=["adaptive:problem-solving", "skills:debugging"],
        runtime_candidate_recorded=True,
    )
    sink.emit(
        "orchestration_paused",
        orchestration_id="orch-1",
        status="PAUSED",
        terminal=False,
    )
    sink.emit(
        "orchestration_supervisor_started",
        orchestration_id="orch-1",
        status="WATCHING",
        mode="detached-per-orchestration",
    )

    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event_type"] for event in events] == [
        "worker_recovered",
        "work_unit_reconciled",
        "recovery_strategy_analyzed",
        "work_unit_practical_test_ready",
        "work_unit_recovery_skipped",
        "recovery_human_question_requested",
        "orchestration_idle_watchdog_triggered",
        "automatic_learning_triggered",
        "orchestration_paused",
        "orchestration_supervisor_started",
    ]
    assert events[1]["reconciled_by_work_unit_id"] == "wu-fix"
    assert events[2]["incident_id"] == "INC-1"
    assert events[2]["recovery_epoch"] == 2
    assert events[3]["work_unit_id"] == "wu-ui"
    assert events[5]["question"].startswith("Qual comportamento")
    assert events[5]["suggested_skills"] == ["grill", "grill-me"]
    assert events[6]["idle_seconds"] == 31.5
    assert events[7]["targets"] == [
        "adaptive:problem-solving",
        "skills:debugging",
    ]

    assert events[-1]["mode"] == "detached-per-orchestration"
