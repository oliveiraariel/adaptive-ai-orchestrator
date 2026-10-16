from __future__ import annotations

import hashlib
import json
import time

import pytest

from application.new_project_admission_guard import (
    PriorProjectNotQuiescentError,
    govern_prior_projects,
)
from infrastructure.orchestration_control_plane import FileOrchestrationControlPlane
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


def _state(*, active=None, terminal=False):
    return {
        "phase": "EXECUTION",
        "desired_state": "RUNNING",
        "terminal": terminal,
        "active_executions": [] if active is None else active,
        "work_unit_states": {"T01": "REVISION_REQUIRED"},
    }


def test_old_stale_idle_execution_is_governedly_paused_before_new_admission(tmp_path):
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save("old", _state())
    held = govern_prior_projects(project_root=tmp_path, incoming_orchestration_id="new")

    assert held == ("old",)
    after = store.load("old")
    assert after["desired_state"] == "PAUSED"
    assert after["work_unit_states"]["T01"] == "REVISION_REQUIRED"
    control = FileOrchestrationControlPlane(project_root=tmp_path).load("old")
    assert control["state"] == "QUIESCENT"
    assert control["mutation_authority_released"] is True
    assert govern_prior_projects(project_root=tmp_path, incoming_orchestration_id="new") == ()


def test_active_worker_is_not_cancelled_or_force_closed(tmp_path):
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    worker = {"work_unit_id": "T01", "execution_id": "execution-1"}
    store.save("old", _state(active=[worker]))

    with pytest.raises(PriorProjectNotQuiescentError, match="active-executions"):
        govern_prior_projects(project_root=tmp_path, incoming_orchestration_id="new")

    after = store.load("old")
    assert after["desired_state"] == "PAUSED"
    assert after["terminal"] is False
    assert after["active_executions"] == [worker]
    assert FileOrchestrationControlPlane(project_root=tmp_path).load("old") is None


def test_fresh_controller_must_acknowledge_pause_even_when_idle(tmp_path):
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save("old", _state())
    control = FileOrchestrationControlPlane(project_root=tmp_path)
    control.activate(orchestration_id="old", reason="test")
    root = tmp_path / ".adaptive" / "orchestration-liveness"
    root.mkdir(parents=True)
    digest = hashlib.sha256(b"old").hexdigest()
    (root / f"{digest}.json").write_text(json.dumps({
        "orchestration_id": "old",
        "controller_state": "ACTIVE",
        "last_heartbeat_at": time.time(),
    }), encoding="utf-8")

    with pytest.raises(PriorProjectNotQuiescentError, match="awaiting-controller-quiescence"):
        govern_prior_projects(project_root=tmp_path, incoming_orchestration_id="new")

    assert store.load("old")["desired_state"] == "PAUSED"
    assert control.load("old")["mutation_authority_released"] is False


def test_terminal_checkpoint_is_preserved_and_only_control_fence_is_repaired(tmp_path):
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    state = _state(terminal=True)
    store.save("old", state)

    govern_prior_projects(project_root=tmp_path, incoming_orchestration_id="new")

    assert store.load("old") == state
    control = FileOrchestrationControlPlane(project_root=tmp_path).load("old")
    assert control["state"] == "QUIESCENT"
    assert control["history"][-1]["event"] == "TERMINAL"


def test_invalid_execution_state_fails_closed(tmp_path):
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    state = _state()
    state.pop("active_executions")
    store.save("old", state)

    with pytest.raises(PriorProjectNotQuiescentError, match="invalid-active-executions"):
        govern_prior_projects(project_root=tmp_path, incoming_orchestration_id="new")
