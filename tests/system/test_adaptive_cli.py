import json

from adaptive_orchestrator import cli
from application.incident_management import IncidentSentinel
from infrastructure.incident_registry import FileIncidentRegistry
from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)


class FakeGatewayClient:
    last_config = None
    last_result_store = None

    def __init__(self, config, **kwargs):
        type(self).last_config = config
        type(self).last_result_store = kwargs.get("result_store")

    def submit(self, task_payload):
        return "gateway:fake-run"

    def get_status(self, external_id):
        return "COMPLETED"

    def retrieve_result(self, external_id):
        return {"status": "ok", "output": "CLI_OK"}

    def cancel(self, external_id):
        return None


def test_cli_run_invokes_adaptive_core_and_returns_json(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "do-not-print-this")
    monkeypatch.setattr(cli, "OpenClawGatewayClient", FakeGatewayClient)

    exit_code = cli.main(
        [
            "run",
            "--objective",
            "Return CLI_OK.",
            "--agent",
            "main",
            "--accept",
            "CLI_OK",
            "--project-root",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["verdict"] == "ACCEPTED"
    assert payload["work_unit_state"] == "COMPLETED"
    assert payload["output"] == "CLI_OK"
    assert "do-not-print-this" not in captured.out
    assert FakeGatewayClient.last_config.token == "do-not-print-this"
    assert FakeGatewayClient.last_result_store.root == tmp_path.resolve() / ".adaptive" / "runs"


def test_cli_doctor_never_prints_gateway_secret(monkeypatch, capsys) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "secret-value")

    exit_code = cli.main(["doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["gateway_token_available"] is True
    assert "secret-value" not in captured.out


def test_cli_returns_nonzero_when_acceptance_is_not_met(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "OpenClawGatewayClient", FakeGatewayClient)

    exit_code = cli.main(
        [
            "run",
            "--objective",
            "Return a result.",
            "--accept",
            "MISSING_MARKER",
            "--project-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["ok"] is False
    assert payload["verdict"] == "RETURNED"
    assert payload["work_unit_state"] == "REVISION_REQUIRED"



class FakeLifecycleRuntime:
    def __init__(self) -> None:
        self.submit_calls = 0
        self.retrieve_calls = 0
        self.status_calls = 0

    def submit(self, task):
        self.submit_calls += 1
        return ExecutionReference(
            id="fake-execution-001",
            runtime="fake",
            external_id="fake-external-001",
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def recover_execution(self, external_id):
        assert external_id == "fake-external-001"
        return ExecutionReference(
            id="fake-execution-001",
            runtime="fake",
            external_id=external_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution):
        self.status_calls += 1
        return AgentRuntimeStatus.COMPLETED

    def retrieve_result(self, execution):
        self.retrieve_calls += 1
        return AgentRuntimeResult(
            execution=ExecutionReference(
                id=execution.id,
                runtime=execution.runtime,
                external_id=execution.external_id,
                status=AgentRuntimeStatus.COMPLETED,
            ),
            raw_result={"output": "LIFECYCLE_OK"},
        )

    def cancel(self, execution):
        raise AssertionError("wait must not cancel automatically")


def test_cli_dispatch_persists_initial_liveness_without_waiting(
    monkeypatch, tmp_path, capsys
) -> None:
    runtime = FakeLifecycleRuntime()
    monkeypatch.setattr(cli, "_runtime", lambda args: runtime)

    exit_code = cli.main(
        [
            "dispatch",
            "--objective",
            "Dispatch one bounded task.",
            "--project-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["external_id"] == "fake-external-001"
    assert payload["liveness_persisted"] is True
    assert runtime.submit_calls == 1
    assert runtime.retrieve_calls == 0

    records = list((tmp_path / ".adaptive" / "liveness").glob("*.json"))
    assert len(records) == 1
    liveness = json.loads(records[0].read_text(encoding="utf-8"))
    assert liveness["state"] == "SUBMITTED"
    assert liveness["heartbeat_sequence"] == 0


def test_cli_wait_emits_runtime_heartbeat_and_final_result(
    monkeypatch, tmp_path, capsys
) -> None:
    runtime = FakeLifecycleRuntime()
    monkeypatch.setattr(cli, "_runtime", lambda args: runtime)

    exit_code = cli.main(
        [
            "wait",
            "--external-id",
            "fake-external-001",
            "--project-root",
            str(tmp_path),
            "--heartbeat-interval-seconds",
            "30",
            "--liveness-timeout-seconds",
            "90",
            "--hard-deadline-seconds",
            "600",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    heartbeat_lines = [
        json.loads(line)
        for line in captured.err.splitlines()
        if line.strip()
    ]

    assert exit_code == 0
    assert payload["runtime_status"] == "COMPLETED"
    assert payload["result"] == {"output": "LIFECYCLE_OK"}
    assert payload["liveness"]["state"] == "COMPLETED"
    assert runtime.submit_calls == 0
    assert runtime.status_calls == 1
    assert runtime.retrieve_calls == 1
    assert heartbeat_lines[-1]["event"] == "execution-heartbeat"
    assert heartbeat_lines[-1]["state"] == "COMPLETED"
    assert heartbeat_lines[-1]["source"] == "runtime-status"


def test_cli_wait_defaults_to_30_90_600_liveness_windows(tmp_path) -> None:
    args = cli.build_parser().parse_args(
        [
            "wait",
            "--external-id",
            "fake-external-001",
            "--project-root",
            str(tmp_path),
        ]
    )

    assert args.heartbeat_interval_seconds == 30.0
    assert args.liveness_timeout_seconds == 90.0
    assert args.hard_deadline_seconds == 600.0


def test_cli_incidents_surfaces_pressure_and_supervision_outbox(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    registry = FileIncidentRegistry()
    IncidentSentinel(registry).observe_runtime_failure(
        "runtime completed but authoritative result is missing",
        orchestration_id="orch-cli",
        work_unit_id="wu-cli",
        runtime="runtime-x",
        blocking=True,
    )

    project_root = tmp_path / "project"
    project_root.mkdir()
    exit_code = cli.main(
        ["incidents", "--supervise", "--project-root", str(project_root)]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["active_incident_count"] == 1
    assert payload["supervision_cycle"] is True
    assert payload["incidents"][0]["pressure"] >= 70
    assert payload["incidents"][0]["action"] == "diagnose-now"
    assert payload["incidents"][0]["research_query"]
    assert (tmp_path / "adaptive-ai-orchestrator" / "notifications.jsonl").is_file()


def test_cli_incidents_registers_project_intake_before_supervision(
    monkeypatch, tmp_path, capsys
) -> None:
    state_root = tmp_path / "state"
    project_root = tmp_path / "project"
    intake_root = project_root / "incidents" / "intake"
    intake_root.mkdir(parents=True)
    monkeypatch.setenv("XDG_STATE_HOME", str(state_root))

    (intake_root / "INC-CLI-INTAKE.md").write_text("# investigation intent\n", encoding="utf-8")
    (intake_root / "INC-CLI-INTAKE.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "declaration_id": "INC-CLI-INTAKE",
                "enabled": True,
                "category": "capability-gap",
                "component": "investigation",
                "symptom": "investigation capability is not finalized",
                "severity": "MEDIUM",
                "project_id": "adaptive-ai-orchestrator",
                "blocking": False,
                "topics": ["investigation", "learning"],
                "evidence_ref": "incidents/intake/INC-CLI-INTAKE.md",
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "incidents",
            "--project-root",
            str(project_root),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["active_incident_count"] == 1
    assert len(payload["project_intake_incident_ids"]) == 1
    assert payload["incidents"][0]["category"] == "capability-gap"
    registry = FileIncidentRegistry()
    active = registry.list_active()
    assert len(active) == 1
    assert active[0].status.value == "TRIAGED"
    assert active[0].recurrence_count == 1


def test_cli_report_intervention_creates_persistent_learning_gap_incident(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    exit_code = cli.main(
        [
            "report-intervention",
            "--component",
            "project-orchestrator",
            "--symptom",
            "human had to redirect diagnosis from model quality to transport",
            "--correction-type",
            "strategy-correction",
            "--orchestration-id",
            "orch-human",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["category"] == "human-intervention"
    assert payload["incident_id"].startswith("INC-")
    registry = FileIncidentRegistry()
    active = registry.list_active()
    assert len(active) == 1
    assert "strategy-correction" in active[0].symptom
    assert "learning-gap" in active[0].topics


def test_cli_incident_watch_runs_persistent_bounded_supervision_cycles(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr(cli.time, "sleep", lambda seconds: None)
    registry = FileIncidentRegistry()
    IncidentSentinel(registry).observe_runtime_failure(
        "persistent result transport defect",
        orchestration_id="orch-watch",
        work_unit_id="wu-watch",
        runtime="runtime-x",
        blocking=True,
    )

    exit_code = cli.main(
        [
            "incidents",
            "--watch",
            "--max-cycles",
            "2",
            "--interval-seconds",
            "0.01",
            "--project-root",
            str(tmp_path),
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]
    assert exit_code == 0
    assert len(lines) == 2
    assert lines[0]["cycle"] == 1
    assert lines[1]["cycle"] == 2
    assert all(item["watch"] is True for item in lines)
    assert all(item["active_incident_count"] == 1 for item in lines)
