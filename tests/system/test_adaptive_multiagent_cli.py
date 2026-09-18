import json

from adaptive_orchestrator import cli
from domain.project_execution_plan import PlannedDependency, PlannedWorkUnit, ProjectExecutionPlan
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


class MultiFakeGatewayClient:
    last_config = None
    counter = 0

    def __init__(self, config, **kwargs):
        type(self).last_config = config

    def submit(self, task_payload):
        type(self).counter += 1
        return f"gateway:multi-{type(self).counter}"

    def get_status(self, external_id):
        return "COMPLETED"

    def retrieve_result(self, external_id):
        return {"status": "ok", "output": f"done:{external_id}"}

    def cancel(self, external_id):
        return None


def test_cli_plan_only_calls_planner_and_never_dispatches(monkeypatch, tmp_path, capsys) -> None:
    registry = tmp_path / "skills.json"
    registry.write_text(json.dumps({"schema_version": 1, "skills": []}), encoding="utf-8")
    plan = ProjectExecutionPlan(
        summary="read-only plan",
        work_units=(PlannedWorkUnit(id="inspect", objective="Inspect documents"),),
        dependencies=(),
    )

    class FakePlanner:
        called = False

        def __init__(self, **kwargs):
            pass

        def plan(self, request):
            type(self).called = True
            assert request.max_work_units == 3
            return plan

    class ForbiddenExecutor:
        def __init__(self, *args, **kwargs):
            raise AssertionError("plan-only must not initialize the executor")

    monkeypatch.setattr(cli, "RuntimeProjectPlanner", FakePlanner)
    monkeypatch.setattr(cli, "RunContinuousProjectOrchestration", ForbiddenExecutor)
    monkeypatch.setattr(cli, "_runtime", lambda args: object())

    exit_code = cli.main([
        "orchestrate", "--plan-only", "--objective", "Inspect documents.",
        "--skill-registry", str(registry), "--max-work-units", "3",
        "--project-root", str(tmp_path),
    ])
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    payload = json.loads(captured.out)
    assert FakePlanner.called is True
    assert payload["mode"] == "plan-only"
    assert payload["work_unit_count"] == 1
    assert payload["work_units"][0]["id"] == "inspect"
    assert payload["dependencies"] == []


def test_cli_parser_keeps_max_waves_validation_range() -> None:
    args = cli.build_parser().parse_args([
        "orchestrate", "--plan-only", "--objective", "Inspect",
    ])
    assert args.plan_only is True


def test_cli_orchestrate_executes_static_parallel_plan(monkeypatch, tmp_path, capsys) -> None:
    MultiFakeGatewayClient.counter = 0
    monkeypatch.setattr(cli, "OpenClawGatewayClient", MultiFakeGatewayClient)

    registry = tmp_path / "skills.json"
    registry.write_text(
        json.dumps({"schema_version": 1, "skills": []}),
        encoding="utf-8",
    )
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "summary": "two independent workers",
                "work_units": [
                    {
                        "id": "a",
                        "objective": "Execute a",
                        "role": "worker",
                        "scope": "",
                        "kind": "EXECUTION",
                        "required_capabilities": [],
                        "requested_skills": [],
                        "tools": [],
                        "inputs": [],
                        "expected_output": ["result"],
                        "acceptance_criteria": ["runtime-completed"],
                        "requested_side_effects": [],
                        "write_paths": [],
                        "priority": 1,
                        "criticality": 0,
                        "parallel_safe": True,
                    },
                    {
                        "id": "b",
                        "objective": "Execute b",
                        "role": "worker",
                        "scope": "",
                        "kind": "EXECUTION",
                        "required_capabilities": [],
                        "requested_skills": [],
                        "tools": [],
                        "inputs": [],
                        "expected_output": ["result"],
                        "acceptance_criteria": ["runtime-completed"],
                        "requested_side_effects": [],
                        "write_paths": [],
                        "priority": 1,
                        "criticality": 0,
                        "parallel_safe": True,
                    },
                ],
                "dependencies": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "orchestrate",
            "--objective",
            "Execute two independent test workers.",
            "--plan-file",
            str(plan),
            "--skill-registry",
            str(registry),
            "--max-concurrency",
            "2",
            "--project-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "COMPLETED"
    assert payload["work_unit_count"] == 2
    assert payload["max_parallelism_observed"] == 2
    assert payload["stop_reasons"] == []
    assert payload["requires_human_decision"] is False
    assert payload["waves"][0]["selected_work_unit_ids"] == ["a", "b"]

class PlannerFailureGatewayClient:
    def __init__(self, config, **kwargs):
        self.config = config

    def submit(self, task_payload):
        return "gateway:planner-failure"

    def get_status(self, external_id):
        return "RUNNING"

    def retrieve_result(self, external_id):
        raise RuntimeError("planner transport interrupted")

    def cancel(self, external_id):
        return None


class CapturingSink:
    def __init__(self, *args, **kwargs):
        self.events = []

    def emit(self, event_type, **fields):
        self.events.append((event_type, fields))


def test_cli_emits_terminal_failure_when_planner_runtime_aborts(monkeypatch, tmp_path, capsys) -> None:
    sink = CapturingSink()
    monkeypatch.setattr(cli, "OpenClawGatewayClient", PlannerFailureGatewayClient)
    monkeypatch.setattr(cli, "JsonlObservabilitySink", lambda *args, **kwargs: sink)

    registry = tmp_path / "skills.json"
    registry.write_text(
        json.dumps({"schema_version": 1, "skills": []}),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "orchestrate",
            "--objective",
            "Plan then execute a project.",
            "--skill-registry",
            str(registry),
            "--project-root",
            str(tmp_path),
        ]
    )

    capsys.readouterr()
    assert exit_code == 1
    event_types = [event_type for event_type, _ in sink.events]
    assert "orchestration_started" in event_types
    terminal = [
        fields
        for event_type, fields in sink.events
        if event_type == "orchestration_completed"
    ]
    assert len(terminal) == 1
    assert terminal[0]["status"] == "FAILED"
    assert terminal[0]["failure_category"] == "runtime"
    assert terminal[0]["failure_code"] == "orchestration_runtime_failed"



def test_cli_orchestrate_honors_caller_allocated_orchestration_id(
    monkeypatch, tmp_path, capsys
) -> None:
    MultiFakeGatewayClient.counter = 0
    monkeypatch.setattr(cli, "OpenClawGatewayClient", MultiFakeGatewayClient)

    registry = tmp_path / "skills.json"
    registry.write_text(
        json.dumps({"schema_version": 1, "skills": []}),
        encoding="utf-8",
    )
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "summary": "one worker",
                "work_units": [
                    {
                        "id": "a",
                        "objective": "Execute a",
                        "role": "worker",
                        "scope": "",
                        "kind": "EXECUTION",
                        "required_capabilities": [],
                        "requested_skills": [],
                        "tools": [],
                        "inputs": [],
                        "expected_output": ["result"],
                        "acceptance_criteria": ["runtime-completed"],
                        "requested_side_effects": [],
                        "write_paths": [],
                        "priority": 1,
                        "criticality": 0,
                        "parallel_safe": True,
                    }
                ],
                "dependencies": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "orchestrate",
            "--objective",
            "Execute one worker.",
            "--orchestration-id",
            "bridge-owned-orch-001",
            "--plan-file",
            str(plan),
            "--skill-registry",
            str(registry),
            "--project-root",
            str(tmp_path),
            "--no-auto-supervisor",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["orchestration_id"] == "bridge-owned-orch-001"

    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    checkpoint = store.load("bridge-owned-orch-001")
    assert checkpoint is not None
    assert checkpoint["terminal"] is True


def test_cli_project_status_reads_authoritative_checkpoint_without_runtime(
    tmp_path, capsys
) -> None:
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save(
        "orch-status-001",
        {
            "orchestration_id": "orch-status-001",
            "phase": "EXECUTION",
            "desired_state": "RUNNING",
            "work_unit_states": {
                "discover": "COMPLETED",
                "fix": "COMPLETED",
                "gates": "COMPLETED",
                "package": "COMPLETED",
            },
            "active_executions": [],
            "pending_replan": False,
            "replan_count": 0,
            "terminal": True,
        },
    )

    exit_code = cli.main(
        [
            "project-status",
            "--orchestration-id",
            "orch-status-001",
            "--project-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "active_execution_count": 0,
        "blocked_work_unit_ids": [],
        "completed_work_unit_ids": ["discover", "fix", "gates", "package"],
        "desired_state": "RUNNING",
        "mode": "project-status",
        "ok": True,
        "orchestration_id": "orch-status-001",
        "pending_replan": False,
        "phase": "EXECUTION",
        "recovery_required_work_unit_ids": [],
        "replan_count": 0,
        "status": "COMPLETED",
        "terminal": True,
        "unfinished_work_unit_ids": [],
        "work_unit_count": 4,
    }


def test_cli_project_status_reports_nonterminal_project_as_running(
    tmp_path, capsys
) -> None:
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save(
        "orch-running-001",
        {
            "orchestration_id": "orch-running-001",
            "phase": "EXECUTION",
            "desired_state": "RUNNING",
            "work_unit_states": {
                "discover": "COMPLETED",
                "fix": "RUNNING",
                "gates": "PLANNED",
            },
            "active_executions": [{"work_unit_id": "fix"}],
            "pending_replan": False,
            "replan_count": 0,
            "terminal": False,
        },
    )

    exit_code = cli.main(
        [
            "project-status",
            "--orchestration-id",
            "orch-running-001",
            "--project-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["terminal"] is False
    assert payload["status"] == "RUNNING"
    assert payload["active_execution_count"] == 1
    assert payload["unfinished_work_unit_ids"] == ["fix", "gates"]
