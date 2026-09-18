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

    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event_type"] for event in events] == [
        "worker_recovered",
        "recovery_strategy_analyzed",
        "automatic_learning_triggered",
        "orchestration_paused",
    ]
    assert events[1]["incident_id"] == "INC-1"
    assert events[1]["recovery_epoch"] == 2
    assert events[2]["targets"] == [
        "adaptive:problem-solving",
        "skills:debugging",
    ]
