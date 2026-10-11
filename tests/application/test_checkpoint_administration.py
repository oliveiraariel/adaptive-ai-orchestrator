import json

import pytest

from application.checkpoint_administration import (
    CheckpointAdministrationAction,
    CheckpointAdministrator,
    CheckpointClassification,
)
from infrastructure.orchestration_control_plane import FileOrchestrationControlPlane
from infrastructure.project_orchestration_checkpoint import FileProjectOrchestrationCheckpointStore
from infrastructure.result_store import FileResultStore


def _store(project):
    return FileProjectOrchestrationCheckpointStore(project_root=project)


def _checkpoint(*, state="RUNNING", active=None, terminal=False, records=None):
    return {
        "orchestration_id": "orch-1",
        "desired_state": state,
        "terminal": terminal,
        "phase": "EXECUTION",
        "active_executions": active if active is not None else [],
        "work_unit_states": {"WU-1": "COMPLETED"},
        "records": records or [],
    }


def _heartbeat(project, timestamp=90.0):
    import hashlib

    digest = hashlib.sha256(b"orch-1").hexdigest()
    path = project / ".adaptive" / "orchestration-liveness" / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "orchestration_id": "orch-1",
        "controller_state": "ACTIVE",
        "last_heartbeat_at": timestamp,
    }), encoding="utf-8")


def _accepted_record(project):
    results = FileResultStore(project_root=project)
    target = results.prepare_target(
        orchestration_id="orch-1", work_unit_id="WU-1", execution_id="publication-1"
    )
    results.publish(
        target,
        content="ADAPTIVE_WORK_STATUS: COMPLETE\nADAPTIVE_BLOCKER_TYPE: NONE\nADAPTIVE_UNMET_CRITERIA: NONE\n",
    )
    return {
        "work_unit_id": "WU-1",
        "execution_id": "runtime-1",
        "runtime_status": "COMPLETED",
        "verdict": "ACCEPTED",
        "result_authoritative": True,
        "result_ref": str(target.manifest_path),
    }


def test_fresh_controller_is_observed_without_mutation(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _store(project).save("orch-1", _checkpoint())
    _heartbeat(project)

    result = CheckpointAdministrator(
        project_root=project, stale_after_seconds=45, wall_clock=lambda: 100.0
    ).reconcile()[0]

    assert result.classification is CheckpointClassification.ACTIVE
    assert result.action is CheckpointAdministrationAction.OBSERVE
    assert _store(project).load("orch-1")["desired_state"] == "RUNNING"


def test_global_stale_history_is_paused_with_backup_and_preserves_active_identity(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    active = [{"work_unit_id": "WU-1", "execution_id": "external-1"}]
    _store(project).save("orch-1", _checkpoint(active=active))
    original = _store(project).path_for("orch-1").read_bytes()

    administrator = CheckpointAdministrator(project_root=project, wall_clock=lambda: 100.0)
    result = administrator.reconcile()[0]
    persisted = _store(project).load("orch-1")

    assert result.classification is CheckpointClassification.HUMAN_DECISION_REQUIRED
    assert result.action is CheckpointAdministrationAction.PAUSE
    assert result.persisted is True
    assert persisted["desired_state"] == "PAUSED"
    assert persisted["active_executions"] == active
    assert persisted["checkpoint_administration"]["reports"][0]["prior_desired_state"] == "RUNNING"
    assert len(persisted["checkpoint_administration"]["reports"]) == 1
    backups = list((project / ".adaptive" / "checkpoint-administration-backups").rglob("*.json"))
    assert backups and backups[0].read_bytes() == original

    repeat = administrator.reconcile()[0]
    assert repeat.classification is CheckpointClassification.PAUSED
    assert len(_store(project).load("orch-1")["checkpoint_administration"]["reports"]) == 1


def test_clean_targeted_stale_checkpoint_is_only_marked_recoverable(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _store(project).save("orch-1", _checkpoint())

    result = CheckpointAdministrator(project_root=project, wall_clock=lambda: 100.0).reconcile(
        orchestration_id="orch-1", allow_resume=True
    )[0]

    assert result.classification is CheckpointClassification.RECOVERABLE
    assert result.action is CheckpointAdministrationAction.RESUME
    assert result.persisted is False
    assert _store(project).load("orch-1")["desired_state"] == "RUNNING"


def test_explicit_new_admission_policy_allows_guarded_global_recovery(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    checkpoint = _checkpoint()
    checkpoint["checkpoint_administration"] = {
        "schema_version": 1,
        "global_auto_resume": True,
        "reports": [],
    }
    _store(project).save("orch-1", checkpoint)

    result = CheckpointAdministrator(project_root=project, wall_clock=lambda: 100.0).reconcile()[0]

    assert result.classification is CheckpointClassification.RECOVERABLE
    assert result.action is CheckpointAdministrationAction.RESUME


def test_dirty_workspace_requires_hold(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    _store(project).save("orch-1", _checkpoint())

    class Completed:
        returncode = 0
        stdout = " M src/app.py\n"

    monkeypatch.setattr("application.checkpoint_administration.subprocess.run", lambda *args, **kwargs: Completed())
    result = CheckpointAdministrator(project_root=project, wall_clock=lambda: 100.0).reconcile(
        orchestration_id="orch-1", allow_resume=True
    )[0]

    assert result.classification is CheckpointClassification.HUMAN_DECISION_REQUIRED
    assert result.reason == "workspace-dirty"
    assert _store(project).load("orch-1")["desired_state"] == "PAUSED"


def test_proven_complete_checkpoint_is_terminalized_through_store(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    record = _accepted_record(project)
    _store(project).save("orch-1", _checkpoint(records=[record]))

    result = CheckpointAdministrator(project_root=project, wall_clock=lambda: 100.0).reconcile()[0]
    persisted = _store(project).load("orch-1")

    assert result.classification is CheckpointClassification.COMPLETED
    assert result.action is CheckpointAdministrationAction.TERMINALIZE
    assert persisted["terminal"] is True
    assert persisted["phase"] == "TERMINAL"
    assert persisted["checkpoint_administration"]["reports"][0]["backup_sha256"]


def test_partial_authoritative_result_cannot_terminalize(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    record = _accepted_record(project)
    manifest = record["result_ref"]
    result_path = str(manifest).replace("manifest.json", "result.txt")
    with open(result_path, "w", encoding="utf-8") as stream:
        stream.write("ADAPTIVE_WORK_STATUS: PARTIAL\nADAPTIVE_UNMET_CRITERIA: still pending\n")
    _store(project).save("orch-1", _checkpoint(records=[record]))

    result = CheckpointAdministrator(project_root=project, wall_clock=lambda: 100.0).reconcile()[0]
    persisted = _store(project).load("orch-1")

    assert result.classification is CheckpointClassification.HUMAN_DECISION_REQUIRED
    assert persisted["terminal"] is False
    assert persisted["desired_state"] == "PAUSED"


def test_concurrent_mutation_is_reported_busy_without_mutation(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    _store(project).save("orch-1", _checkpoint())
    control = FileOrchestrationControlPlane(project_root=project)
    administrator = CheckpointAdministrator(project_root=project, wall_clock=lambda: 100.0)

    with control.mutation_lock("orch-1"):
        result = administrator.reconcile()[0]

    assert result.classification is CheckpointClassification.BUSY
    assert result.action is CheckpointAdministrationAction.RETRY_LATER
    assert _store(project).load("orch-1")["desired_state"] == "RUNNING"
