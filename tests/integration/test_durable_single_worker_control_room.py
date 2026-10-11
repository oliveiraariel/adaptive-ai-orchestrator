"""Local cross-process proof for the durable single-worker path.

This test deliberately uses a simulated Gateway: it verifies the real Adaptive
CLI/checkpoint/observability path and a separately running Control Room without
spending provider budget or touching the installed Control Room service.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest

from adaptive_orchestrator import cli
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


class SimulatedGatewayClient:
    """One completed worker result with literal semantic evidence and footer."""

    def __init__(self, _config, **_kwargs) -> None:
        self._run_id = "gateway:durable-single-worker"

    def submit(self, _task_payload):
        return self._run_id

    def get_status(self, _external_id):
        return "COMPLETED"

    def retrieve_result(self, _external_id):
        return {
            "status": "ok",
            "output": (
                "DURABLE_CONTINUITY_OK\n"
                "ADAPTIVE_WORK_STATUS: COMPLETE\n"
                "ADAPTIVE_BLOCKER_TYPE: NONE\n"
                "ADAPTIVE_UNMET_CRITERIA: NONE"
            ),
        }

    def cancel(self, _external_id):
        return None


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _read_json(url: str) -> dict:
    with urlopen(url, timeout=0.5) as response:  # noqa: S310 - localhost test server
        return json.loads(response.read())


def _wait_for_json(url: str, predicate) -> dict:
    deadline = time.monotonic() + 8
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            payload = _read_json(url)
            if predicate(payload):
                return payload
        except Exception as exc:  # server startup and poll race only
            last_error = exc
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {url}: {last_error}")


def test_durable_single_worker_cli_checkpoint_and_control_room_projection(
    monkeypatch, tmp_path, capsys
) -> None:
    control_room = Path(__file__).resolve().parents[3] / "adaptive-control-room"
    if not (control_room / "src" / "server.js").is_file():
        pytest.skip("Control Room sibling checkout is unavailable for local integration")

    project = tmp_path / "governed-project"
    project.mkdir()
    source = tmp_path / "adaptive-observability.jsonl"
    projection = tmp_path / "control-room-events.jsonl"
    registry = tmp_path / "skills.json"
    registry.write_text(json.dumps({"schema_version": 1, "skills": []}), encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "summary": "one durable simulated worker",
                "work_units": [
                    {
                        "id": "implement",
                        "objective": "Deliver the continuity marker.",
                        "role": "implementation",
                        "scope": "local test",
                        "kind": "EXECUTION",
                        "required_capabilities": [],
                        "requested_skills": [],
                        "tools": [],
                        "inputs": [],
                        "expected_output": ["DURABLE_CONTINUITY_OK"],
                        "acceptance_criteria": ["DURABLE_CONTINUITY_OK"],
                        "requested_side_effects": [],
                        "write_paths": [],
                        "priority": 1,
                        "criticality": 1,
                        "parallel_safe": True,
                    }
                ],
                "dependencies": [],
            }
        ),
        encoding="utf-8",
    )

    port = _free_port()
    environment = {
        **os.environ,
        "ADAPTIVE_OBSERVABILITY_LOG": str(source),
        "CONTROL_ROOM_EVENTS": str(projection),
        "PORT": str(port),
    }
    server = subprocess.Popen(
        ["node", "src/server.js"],
        cwd=control_room,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        health_url = f"http://127.0.0.1:{port}/api/health"
        _wait_for_json(health_url, lambda payload: payload.get("ok") is True)
        monkeypatch.setenv("ADAPTIVE_OBSERVABILITY_LOG", str(source))
        monkeypatch.setattr(cli, "OpenClawGatewayClient", SimulatedGatewayClient)
        monkeypatch.setattr(cli, "_start_orchestration_guardian", lambda *args, **kwargs: None)

        assert cli.main(
            [
                "orchestrate",
                "--objective",
                "Deliver one continuity-sensitive simulated change.",
                "--orchestration-id",
                "durable-single-worker-e2e",
                "--plan-file",
                str(plan),
                "--skill-registry",
                str(registry),
                "--project-root",
                str(project),
                "--max-concurrency",
                "1",
                "--concurrency-mode",
                "FIXED",
            ]
        ) == 0
        result = json.loads(capsys.readouterr().out)
        assert result["orchestration_id"] == "durable-single-worker-e2e"
        assert result["status"] == "COMPLETED"
        assert result["max_parallelism_observed"] == 1

        checkpoint = FileProjectOrchestrationCheckpointStore(project_root=project).load(
            "durable-single-worker-e2e"
        )
        assert checkpoint is not None
        assert checkpoint["terminal"] is True
        assert checkpoint["work_unit_states"] == {"implement": "COMPLETED"}

        snapshot = _wait_for_json(
            f"http://127.0.0.1:{port}/api/snapshot",
            lambda payload: any(
                session.get("orchestration_id") == "durable-single-worker-e2e"
                and session.get("state") == "CLOSED"
                for session in payload.get("operational_sessions", [])
            ),
        )
        sessions = [
            item
            for item in snapshot["operational_sessions"]
            if item["orchestration_id"] == "durable-single-worker-e2e"
        ]
        assert len(sessions) == 1
        assert sessions[0]["work_unit_count"] == 1
        card = next(
            item
            for item in snapshot["events"]
            if item.get("orchestration_id") == "durable-single-worker-e2e"
            and item.get("work_unit_id") == "implement"
        )
        assert card["status"] == "COMPLETED"
        assert card["verdict"] == "ACCEPTED"
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


def test_checkpoint_administration_hold_projects_to_control_room(
    monkeypatch, tmp_path, capsys
) -> None:
    control_room = Path(__file__).resolve().parents[3] / "adaptive-control-room"
    if not (control_room / "src" / "server.js").is_file():
        pytest.skip("Control Room sibling checkout is unavailable for local integration")

    project = tmp_path / "governed-project"
    project.mkdir()
    FileProjectOrchestrationCheckpointStore(project_root=project).save(
        "checkpoint-history",
        {
            "orchestration_id": "checkpoint-history",
            "desired_state": "RUNNING",
            "terminal": False,
            "active_executions": [{"work_unit_id": "WU-1", "execution_id": "exec-1"}],
            "work_unit_states": {"WU-1": "RUNNING"},
            "records": [],
        },
    )
    source = tmp_path / "adaptive-observability.jsonl"
    projection = tmp_path / "control-room-events.jsonl"
    port = _free_port()
    environment = {
        **os.environ,
        "ADAPTIVE_OBSERVABILITY_LOG": str(source),
        "CONTROL_ROOM_EVENTS": str(projection),
        "PORT": str(port),
    }
    server = subprocess.Popen(
        ["node", "src/server.js"], cwd=control_room, env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_json(f"http://127.0.0.1:{port}/api/health", lambda payload: payload.get("ok") is True)
        monkeypatch.setenv("ADAPTIVE_OBSERVABILITY_LOG", str(source))
        assert cli.main(["supervise-projects", "--project-root", str(project)]) == 0
        capsys.readouterr()

        snapshot = _wait_for_json(
            f"http://127.0.0.1:{port}/api/snapshot",
            lambda payload: any(
                event.get("event_type") == "checkpoint_reconciliation_persisted"
                and event.get("orchestration_id") == "checkpoint-history"
                for event in payload.get("checkpoint_administrations", [])
            ),
        )
        reconciliation = next(
            event for event in snapshot["checkpoint_administrations"]
            if event.get("event_type") == "checkpoint_reconciliation_persisted"
        )
        assert reconciliation["classification"] == "HUMAN_DECISION_REQUIRED"
        assert reconciliation["action"] == "PAUSE"
        session = next(
            item for item in snapshot["operational_sessions"]
            if item["orchestration_id"] == "checkpoint-history"
        )
        assert session["status"] == "PAUSED"
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
