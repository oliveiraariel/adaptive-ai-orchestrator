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
