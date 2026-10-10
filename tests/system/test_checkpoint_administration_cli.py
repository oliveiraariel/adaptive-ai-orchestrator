from adaptive_orchestrator import cli
from infrastructure.project_orchestration_checkpoint import FileProjectOrchestrationCheckpointStore


def test_global_supervision_holds_stale_checkpoint_without_invoking_resume(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    FileProjectOrchestrationCheckpointStore(project_root=project).save(
        "orch-1",
        {
            "orchestration_id": "orch-1",
            "desired_state": "RUNNING",
            "terminal": False,
            "active_executions": [{"work_unit_id": "WU-1", "execution_id": "exec-1"}],
            "work_unit_states": {"WU-1": "RUNNING"},
            "records": [],
        },
    )
    monkeypatch.setenv("ADAPTIVE_OBSERVABILITY_LOG", str(tmp_path / "events.jsonl"))
    monkeypatch.setattr(cli, "_resume_project", lambda _: (_ for _ in ()).throw(AssertionError("must not resume globally")))

    assert cli.main(["supervise-projects", "--project-root", str(project)]) == 0

    state = FileProjectOrchestrationCheckpointStore(project_root=project).load("orch-1")
    assert state["desired_state"] == "PAUSED"
    assert state["active_executions"][0]["execution_id"] == "exec-1"
