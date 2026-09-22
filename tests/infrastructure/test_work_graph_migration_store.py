from __future__ import annotations

import hashlib
import json
import time

import pytest

from application.work_graph_migration import WorkGraphMigrationError
from infrastructure.work_graph_migration_store import FileWorkGraphMigrationStore
from infrastructure.orchestration_control_plane import FileOrchestrationControlPlane


def test_receipt_is_immutable_and_idempotent(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)
    receipt = {"migration_id": "m1", "ok": True}

    first = store.write_receipt(
        orchestration_id="orch",
        migration_id="m1",
        spec_digest="a" * 64,
        receipt=receipt,
    )
    second = store.write_receipt(
        orchestration_id="orch",
        migration_id="m1",
        spec_digest="a" * 64,
        receipt=receipt,
    )

    assert first == second
    assert json.loads((tmp_path / first).read_text(encoding="utf-8")) == receipt

    with pytest.raises(WorkGraphMigrationError, match="different content"):
        store.write_receipt(
            orchestration_id="orch",
            migration_id="m1",
            spec_digest="a" * 64,
            receipt={"migration_id": "m1", "ok": False},
        )


def test_apply_lock_prevents_concurrent_migration(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)

    with store.apply_lock("orch"):
        with pytest.raises(WorkGraphMigrationError, match="already in progress"):
            with store.apply_lock("orch"):
                pass

    with store.apply_lock("orch"):
        pass



def test_controller_quiescence_rejects_fresh_active_heartbeat(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)
    digest = hashlib.sha256(b"orch").hexdigest()
    path = (
        tmp_path
        / ".adaptive"
        / "orchestration-liveness"
        / f"{digest}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "orchestration_id": "orch",
                "controller_state": "ACTIVE",
                "last_heartbeat_at": time.time(),
            }
        ),
        encoding="utf-8",
    )

    quiescent, reason = store.controller_quiescence("orch")

    assert quiescent is False
    assert "heartbeat-fresh" in reason

    path.write_text(
        json.dumps(
            {
                "orchestration_id": "orch",
                "controller_state": "TERMINAL",
                "last_heartbeat_at": time.time(),
            }
        ),
        encoding="utf-8",
    )

    quiescent, reason = store.controller_quiescence("orch")

    assert quiescent is True
    assert reason == "controller-state:TERMINAL"



def test_controller_quiescence_fails_closed_without_liveness(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)

    quiescent, reason = store.controller_quiescence("orch")

    assert quiescent is False
    assert reason == "controller-liveness-missing"



def test_controller_quiescence_rejects_stale_active_heartbeat(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)
    digest = hashlib.sha256(b"orch").hexdigest()
    path = (
        tmp_path
        / ".adaptive"
        / "orchestration-liveness"
        / f"{digest}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "orchestration_id": "orch",
                "controller_state": "ACTIVE",
                "last_heartbeat_at": time.time() - 600,
            }
        ),
        encoding="utf-8",
    )

    quiescent, reason = store.controller_quiescence(
        "orch",
        stale_after_seconds=45,
    )

    assert quiescent is False
    assert "heartbeat-stale" in reason


def test_governed_quiescence_fence_allows_admin_operation_despite_active_heartbeat(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)
    checkpoint = {"desired_state": "PAUSED", "active_executions": []}
    FileOrchestrationControlPlane(project_root=tmp_path).mark_quiescent(
        orchestration_id="orch", checkpoint=checkpoint, reason="test-pause"
    )
    digest = hashlib.sha256(b"orch").hexdigest()
    liveness = tmp_path / ".adaptive" / "orchestration-liveness" / f"{digest}.json"
    liveness.parent.mkdir(parents=True, exist_ok=True)
    liveness.write_text(json.dumps({
        "orchestration_id": "orch", "controller_state": "ACTIVE", "last_heartbeat_at": time.time(),
    }), encoding="utf-8")

    quiescent, reason = store.controller_quiescence("orch")

    assert quiescent is True
    assert reason == "controller-state:QUIESCENT-control-plane"
