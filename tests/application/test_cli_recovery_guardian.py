from __future__ import annotations

import argparse
import json
import subprocess

from adaptive_orchestrator import cli
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


class MemoryObservability:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event_type: str, **fields) -> None:
        self.events.append((event_type, fields))


def _args(project_root, **overrides):
    values = {
        "auto_supervisor": True,
        "project_root": str(project_root),
        "gateway_url": "ws://127.0.0.1:18789",
        "wait_timeout_ms": 120000,
        "session_id": "session-a",
        "skill_registry": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_orchestrate_parser_enables_auto_supervisor_by_default():
    args = cli.build_parser().parse_args(["orchestrate", "--objective", "x"])
    assert args.auto_supervisor is True
    assert args.max_work_units == 64
    assert args.concurrency_mode == "AUTO"


def test_guardian_is_detached_targets_same_orchestration_and_keeps_secrets_out_of_argv(
    tmp_path,
    monkeypatch,
):
    captured = {}
    sink = MemoryObservability()

    class Process:
        pass

    def fake_popen(command, **kwargs):
        captured["command"] = list(command)
        captured["kwargs"] = kwargs
        return Process()

    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "secret-token")
    monkeypatch.delenv("ADAPTIVE_SUPERVISOR_GUARDIAN", raising=False)
    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    cli._start_orchestration_guardian(
        _args(tmp_path),
        orchestration_id="orch-guardian",
        observability=sink,
    )

    command = captured["command"]
    assert command[:4] == [
        cli.sys.executable,
        "-m",
        "adaptive_orchestrator",
        "supervise-projects",
    ]
    assert "--watch" in command
    assert "--orchestration-id" in command
    assert command[command.index("--orchestration-id") + 1] == "orch-guardian"
    assert "--exit-when-terminal" in command
    assert "secret-token" not in command
    assert captured["kwargs"]["start_new_session"] is True
    assert captured["kwargs"]["stdin"] is subprocess.DEVNULL
    assert captured["kwargs"]["stdout"] is subprocess.DEVNULL
    assert captured["kwargs"]["stderr"] is subprocess.DEVNULL
    assert (
        captured["kwargs"]["env"]["ADAPTIVE_SUPERVISOR_GUARDIAN"] == "1"
    )
    assert sink.events == [
        (
            "orchestration_supervisor_started",
            {
                "orchestration_id": "orch-guardian",
                "status": "WATCHING",
                "mode": "detached-per-orchestration",
            },
        )
    ]


def test_guardian_does_not_recursively_spawn_inside_guardian_process(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("ADAPTIVE_SUPERVISOR_GUARDIAN", "1")
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("spawned")),
    )

    cli._start_orchestration_guardian(
        _args(tmp_path),
        orchestration_id="orch-guardian",
        observability=MemoryObservability(),
    )


def test_targeted_watcher_exits_when_checkpoint_is_terminal(tmp_path):
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save(
        "orch-terminal",
        {
            "orchestration_id": "orch-terminal",
            "desired_state": "RUNNING",
            "active_executions": [],
            "terminal": True,
        },
    )
    args = argparse.Namespace(
        interval_seconds=0.01,
        stale_after_seconds=0.01,
        startup_grace_seconds=1.0,
        exit_when_terminal=True,
        orchestration_id="orch-terminal",
        project_root=str(tmp_path),
        watch=True,
        session_id=None,
        skill_registry=None,
        gateway_url="ws://127.0.0.1:18789",
        wait_timeout_ms=100,
    )

    assert cli._supervise_projects(args) == 0



def test_targeted_watcher_survives_failed_resume_and_keeps_watching(
    tmp_path,
    monkeypatch,
    capsys,
):
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save(
        "orch-watch-retry",
        {
            "orchestration_id": "orch-watch-retry",
            "desired_state": "RUNNING",
            "active_executions": [],
            "terminal": False,
        },
    )
    args = argparse.Namespace(
        interval_seconds=0.01,
        stale_after_seconds=0.01,
        startup_grace_seconds=1.0,
        exit_when_terminal=True,
        orchestration_id="orch-watch-retry",
        project_root=str(tmp_path),
        watch=True,
        session_id=None,
        skill_registry=None,
        gateway_url="ws://127.0.0.1:18789",
        wait_timeout_ms=100,
    )

    monkeypatch.setattr(cli, "_resume_project", lambda _args: 2)

    def finish_after_first_watch_interval(_seconds):
        state = store.load("orch-watch-retry")
        assert state is not None
        state["terminal"] = True
        store.save("orch-watch-retry", state)

    monkeypatch.setattr(cli.time, "sleep", finish_after_first_watch_interval)

    assert cli._supervise_projects(args) == 0

    rows = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.strip()
    ]
    assert rows
    assert rows[0]["resumed_orchestration_ids"] == []
    assert rows[0]["resume_failures"]
    assert rows[0]["resume_failures"][0]["orchestration_id"] == "orch-watch-retry"
    assert rows[0]["resume_failures"][0]["error_type"] == "ProjectOrchestrationError"
