import hashlib
import json

from application.orchestration_supervisor import ProjectOrchestrationSupervisor
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


def _heartbeat_path(project, orchestration_id):
    digest = hashlib.sha256(orchestration_id.encode("utf-8")).hexdigest()
    return project / ".adaptive" / "orchestration-liveness" / f"{digest}.json"


def _write_heartbeat(project, orchestration_id, *, timestamp, state="ACTIVE"):
    path = _heartbeat_path(project, orchestration_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "orchestration_id": orchestration_id,
                "controller_state": state,
                "status": "RUNNING",
                "terminal": state == "TERMINAL",
                "last_heartbeat_at": timestamp,
            }
        ),
        encoding="utf-8",
    )


def test_supervisor_resumes_nonterminal_project_with_missing_controller(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    store.save(
        "orch-1",
        {
            "orchestration_id": "orch-1",
            "desired_state": "RUNNING",
            "active_executions": [],
            "terminal": False,
        },
    )
    supervisor = ProjectOrchestrationSupervisor(
        project_root=project,
        stale_after_seconds=45,
        wall_clock=lambda: 100.0,
    )
    directive = supervisor.directives()[0]
    assert directive.action == "RESUME"
    assert directive.reason == "controller-heartbeat-missing"

    called = []
    assert supervisor.run_once(lambda orchestration_id: called.append(orchestration_id)) == (
        "orch-1",
    )
    assert called == ["orch-1"]


def test_supervisor_observes_fresh_controller_and_does_not_duplicate_resume(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    store.save(
        "orch-1",
        {
            "orchestration_id": "orch-1",
            "desired_state": "RUNNING",
            "active_executions": [{"work_unit_id": "U1"}],
            "terminal": False,
        },
    )
    _write_heartbeat(project, "orch-1", timestamp=90.0)
    supervisor = ProjectOrchestrationSupervisor(
        project_root=project,
        stale_after_seconds=45,
        wall_clock=lambda: 100.0,
    )
    directive = supervisor.directives()[0]
    assert directive.action == "OBSERVE"
    assert directive.active_execution_count == 1
    assert supervisor.run_once(lambda _: (_ for _ in ()).throw(AssertionError())) == ()


def test_supervisor_honors_developer_pause(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    store.save(
        "orch-1",
        {
            "orchestration_id": "orch-1",
            "desired_state": "PAUSED",
            "active_executions": [],
            "terminal": False,
        },
    )
    supervisor = ProjectOrchestrationSupervisor(
        project_root=project,
        wall_clock=lambda: 100.0,
    )
    directive = supervisor.directives()[0]
    assert directive.action == "PAUSED"
    assert supervisor.run_once(lambda _: (_ for _ in ()).throw(AssertionError())) == ()



def test_supervisor_can_target_one_orchestration_without_touching_others(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    for orchestration_id in ("orch-a", "orch-b"):
        store.save(
            orchestration_id,
            {
                "orchestration_id": orchestration_id,
                "desired_state": "RUNNING",
                "active_executions": [],
                "terminal": False,
            },
        )

    supervisor = ProjectOrchestrationSupervisor(
        project_root=project,
        stale_after_seconds=45,
        wall_clock=lambda: 100.0,
    )

    directives = supervisor.directives(orchestration_id="orch-b")
    assert [item.orchestration_id for item in directives] == ["orch-b"]

    called = []
    resumed = supervisor.run_once(
        lambda orchestration_id: called.append(orchestration_id),
        orchestration_id="orch-b",
    )
    assert resumed == ("orch-b",)
    assert called == ["orch-b"]



def test_persistent_supervisor_survives_resume_failure_and_retains_cooldown_lease(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    store.save(
        "orch-retry",
        {
            "orchestration_id": "orch-retry",
            "desired_state": "RUNNING",
            "active_executions": [],
            "terminal": False,
        },
    )
    now = [100.0]
    supervisor = ProjectOrchestrationSupervisor(
        project_root=project,
        stale_after_seconds=45,
        lease_seconds=30,
        wall_clock=lambda: now[0],
    )
    calls = []

    def fail_resume(orchestration_id):
        calls.append(orchestration_id)
        raise RuntimeError("transient controller resume failure")

    assert supervisor.run_once(
        fail_resume,
        orchestration_id="orch-retry",
        continue_on_error=True,
    ) == ()
    assert calls == ["orch-retry"]
    assert len(supervisor.last_resume_failures) == 1
    failure = supervisor.last_resume_failures[0]
    assert failure.orchestration_id == "orch-retry"
    assert failure.error_type == "RuntimeError"
    assert failure.retry_after_seconds == 30

    # The failed pass keeps the durable lease until expiry, so watch mode does
    # not hot-loop the same controller failure every interval.
    assert supervisor.run_once(
        fail_resume,
        orchestration_id="orch-retry",
        continue_on_error=True,
    ) == ()
    assert calls == ["orch-retry"]

    now[0] = 131.0
    assert supervisor.run_once(
        fail_resume,
        orchestration_id="orch-retry",
        continue_on_error=True,
    ) == ()
    assert calls == ["orch-retry", "orch-retry"]


def test_one_shot_supervisor_keeps_fail_fast_behavior_and_releases_lease(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    store.save(
        "orch-fail-fast",
        {
            "orchestration_id": "orch-fail-fast",
            "desired_state": "RUNNING",
            "active_executions": [],
            "terminal": False,
        },
    )
    supervisor = ProjectOrchestrationSupervisor(
        project_root=project,
        wall_clock=lambda: 100.0,
    )

    import pytest

    with pytest.raises(RuntimeError, match="boom"):
        supervisor.run_once(
            lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
            orchestration_id="orch-fail-fast",
        )

    # Historical one-shot behavior releases its lease, so an explicit operator
    # retry can run immediately.
    called = []
    assert supervisor.run_once(
        lambda orchestration_id: called.append(orchestration_id),
        orchestration_id="orch-fail-fast",
    ) == ("orch-fail-fast",)
    assert called == ["orch-fail-fast"]
