import json

from adaptive_orchestrator import cli
from application.continuous_project_orchestration import RunContinuousProjectOrchestration
from application.run_project_orchestration import (
    ConcurrencyMode,
    ProjectOrchestrationRequest,
)
from domain.project_execution_plan import PlannedWorkUnit, ProjectExecutionPlan
from domain.work_unit import WorkUnitKind
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


def _plan() -> ProjectExecutionPlan:
    return ProjectExecutionPlan(
        summary="pause/resume test",
        work_units=(
            PlannedWorkUnit(
                id="U1",
                objective="Complete U1",
                role="worker",
                kind=WorkUnitKind.EXECUTION,
                expected_output=("result",),
                acceptance_criteria=("runtime-completed",),
            ),
        ),
    )


def _checkpoint(orchestration_id: str) -> dict:
    plan = _plan()
    request = ProjectOrchestrationRequest(
        objective="Pause and resume safely.",
        orchestration_id=orchestration_id,
        project_id="test-project",
        plan=plan,
    )
    return {
        "orchestration_id": orchestration_id,
        "phase": "EXECUTION",
        "desired_state": "RUNNING",
        "terminal": False,
        "request": RunContinuousProjectOrchestration._request_to_payload(request),
        "plan": RunContinuousProjectOrchestration._plan_to_payload(plan),
    }


def test_pause_project_cli_persists_resumable_desired_state(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    store.save("orch-pause", _checkpoint("orch-pause"))

    exit_code = cli.main(
        [
            "pause-project",
            "--orchestration-id",
            "orch-pause",
            "--project-root",
            str(project),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["desired_state"] == "PAUSED"
    assert payload["orchestration_id"] == "orch-pause"
    state = store.load("orch-pause")
    assert state is not None
    assert state["desired_state"] == "PAUSED"
    assert state["terminal"] is False


class ResumeProbe(RunContinuousProjectOrchestration):
    def __init__(self, checkpoint_store):
        self._checkpoint_store = checkpoint_store
        self.seen_checkpoint = None

    def _execute(self, request, *, observability, checkpoint):
        self.seen_checkpoint = checkpoint
        return request


def test_resume_changes_paused_checkpoint_back_to_running_before_execution(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    state = _checkpoint("orch-resume")
    state["desired_state"] = "PAUSED"
    store.save("orch-resume", state)

    probe = ResumeProbe(store)
    request = probe.resume("orch-resume")

    assert request.orchestration_id == "orch-resume"
    assert probe.seen_checkpoint is not None
    assert probe.seen_checkpoint["desired_state"] == "RUNNING"
    persisted = store.load("orch-resume")
    assert persisted is not None
    assert persisted["desired_state"] == "RUNNING"
    assert persisted["terminal"] is False



def test_legacy_checkpoint_concurrency_is_upgraded_to_auto_floor_four() -> None:
    state = _checkpoint("orch-legacy-concurrency")
    raw = state["request"]
    raw.pop("concurrency_mode", None)
    raw.pop("worker_observation_interval_seconds", None)
    raw.pop("worker_soft_stall_seconds", None)
    raw.pop("worker_stall_overflow_slots", None)
    raw["max_concurrency"] = 1

    request = RunContinuousProjectOrchestration._request_from_checkpoint(state)

    assert request.concurrency_mode is ConcurrencyMode.AUTO
    assert request.max_concurrency == 4
    assert request.worker_observation_interval_seconds == 5
    assert request.worker_soft_stall_seconds == 90
    assert request.worker_stall_overflow_slots == 1


def test_fixed_concurrency_checkpoint_preserves_explicit_serial_constraint() -> None:
    state = _checkpoint("orch-fixed-concurrency")
    state["request"]["concurrency_mode"] = ConcurrencyMode.FIXED.value
    state["request"]["max_concurrency"] = 1

    request = RunContinuousProjectOrchestration._request_from_checkpoint(state)

    assert request.concurrency_mode is ConcurrencyMode.FIXED
    assert request.max_concurrency == 1
