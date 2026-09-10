import json

from application.observability import JsonlObservabilitySink


def test_jsonl_observability_sink_allowlists_fields(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    JsonlObservabilitySink(path).emit(
        "worker_dispatched",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        model="GPT-5.6 Luna",
        objective="must not persist",
        prompt="must not persist",
        token="must not persist",
    )
    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["event_type"] == "worker_dispatched"
    assert event["work_unit_id"] == "wu-1"
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
