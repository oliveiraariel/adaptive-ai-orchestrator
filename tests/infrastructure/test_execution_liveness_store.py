import json

import pytest

from application.execution_liveness import ExecutionLiveness, ExecutionLivenessState
from infrastructure.execution_liveness_store import (
    ExecutionLivenessStoreError,
    FileExecutionLivenessStore,
)


def snapshot() -> ExecutionLiveness:
    return ExecutionLiveness(
        external_id="gateway:orchestrator:task:abc",
        execution_id="execution-abc",
        runtime="openclaw",
        state=ExecutionLivenessState.RUNNING,
        heartbeat_sequence=4,
        started_at=100.0,
        last_heartbeat_at=130.0,
        last_progress_at=100.0,
        source="runtime-status",
    )


def test_liveness_store_is_project_local_and_round_trips(tmp_path) -> None:
    store = FileExecutionLivenessStore(project_root=tmp_path)
    store.write(snapshot())

    path = store.path_for(snapshot().external_id)

    assert path.parent == tmp_path.resolve() / ".adaptive" / "liveness"
    assert path.is_file()
    loaded = store.read(snapshot().external_id)
    assert loaded == snapshot()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["external_id"] == snapshot().external_id


def test_liveness_store_replaces_snapshot_atomically(tmp_path) -> None:
    store = FileExecutionLivenessStore(project_root=tmp_path)
    store.write(snapshot())
    updated = ExecutionLiveness(
        **{
            **snapshot().__dict__,
            "state": ExecutionLivenessState.COMPLETED,
            "heartbeat_sequence": 5,
            "last_heartbeat_at": 160.0,
            "last_progress_at": 160.0,
        }
    )
    store.write(updated)

    assert store.read(updated.external_id) == updated
    assert not list(store.root.glob("*.tmp"))


def test_liveness_store_fails_closed_on_identity_mismatch(tmp_path) -> None:
    store = FileExecutionLivenessStore(project_root=tmp_path)
    store.write(snapshot())
    path = store.path_for(snapshot().external_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["external_id"] = "different-external-id"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExecutionLivenessStoreError, match="identity"):
        store.read(snapshot().external_id)


def test_liveness_store_fails_closed_on_unknown_schema(tmp_path) -> None:
    store = FileExecutionLivenessStore(project_root=tmp_path)
    store.write(snapshot())
    path = store.path_for(snapshot().external_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExecutionLivenessStoreError, match="unsupported schema"):
        store.read(snapshot().external_id)
