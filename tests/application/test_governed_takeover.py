import json
from argparse import Namespace

from application.governed_takeover import GovernedTakeoverError, GovernedTakeoverStore
from adaptive_orchestrator.cli import _takeover_work_unit
from infrastructure.project_orchestration_checkpoint import FileProjectOrchestrationCheckpointStore


def _request(store, **kwargs):
    return store.request(
        orchestration_id="orch-1", work_unit_id="wu-1", mode="direct",
        actor="operator", reason="No progress observed in Control Room",
        owner_agent="coordinator", **kwargs,
    )


def test_takeover_is_durable_idempotent_and_auditable(tmp_path):
    first = GovernedTakeoverStore(project_root=tmp_path)
    row = _request(first)
    again = _request(GovernedTakeoverStore(project_root=tmp_path))
    assert row == again
    assert row["state"] == "REQUESTED"
    second = GovernedTakeoverStore(project_root=tmp_path)
    applied = second.transition("orch-1", row["id"], state="APPLIED", detail="verified abort")
    assert applied["state"] == "APPLIED"
    assert applied["history"][0]["detail"] == "verified abort"
    assert _request(first)["id"] == row["id"]
    finished = second.transition(
        "orch-1", row["id"], state="COMPLETED", detail="accepted by evaluator"
    )
    assert finished["state"] == "COMPLETED"
    assert len(finished["history"]) == 2
    assert _request(first)["id"] == "2"


def test_takeover_requires_owner_and_rejects_conflicting_live_request(tmp_path):
    import pytest

    store = GovernedTakeoverStore(project_root=tmp_path)
    with pytest.raises(GovernedTakeoverError, match="explicit owner"):
        store.request(
            orchestration_id="orch-1", work_unit_id="wu-1", mode="direct",
            actor="owner", reason="Work is stopped",
        )
    _request(store)
    replacement = store.request(
        orchestration_id="orch-1", work_unit_id="wu-1", mode="replacement",
        actor="owner", reason="Changed strategy",
    )
    assert replacement["id"] == "2"
    assert store.current("orch-1", "wu-1")["mode"] == "replacement"
    history = store.load("orch-1")["requests"]
    assert history[0]["state"] == "SUPERSEDED"
    assert history[0]["history"][-1]["state"] == "SUPERSEDED"


def test_cli_requires_authorization_and_preserves_checkpoint(tmp_path, capsys):
    checkpoint_store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    state = {
        "orchestration_id": "orch-1", "terminal": False,
        "desired_state": "RUNNING",
        "work_unit_states": {"wu-1": "RUNNING", "wu-done": "COMPLETED"},
        "active_executions": [{"work_unit_id": "wu-1", "external_id": "run-1"}],
    }
    checkpoint_store.save("orch-1", state)
    args = Namespace(
        project_root=str(tmp_path), orchestration_id="orch-1",
        work_unit_id="wu-1", mode="direct", actor="owner",
        reason="I authorize coordinator to finish", owner_agent="coordinator",
        authorize=False,
    )
    assert _takeover_work_unit(args) != 0
    assert GovernedTakeoverStore(project_root=tmp_path).load("orch-1") is None
    args.authorize = True
    assert _takeover_work_unit(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["takeover"]["state"] == "REQUESTED"
    assert checkpoint_store.load("orch-1") == state
    args.work_unit_id = "wu-done"
    assert _takeover_work_unit(args) != 0
    args.work_unit_id = "wu-1"
    assert _takeover_work_unit(args) == 0
    assert len(GovernedTakeoverStore(project_root=tmp_path).load("orch-1")["requests"]) == 1


def test_cli_refuses_terminal_or_paused_project(tmp_path):
    checkpoint_store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    args = Namespace(
        project_root=str(tmp_path), orchestration_id="orch-1",
        work_unit_id="wu-1", mode="direct", actor="owner",
        reason="Owner priority override", owner_agent="coordinator",
        authorize=True,
    )
    for state in (
        {"terminal": True, "desired_state": "RUNNING"},
        {"terminal": False, "desired_state": "PAUSED"},
    ):
        checkpoint_store.save("orch-1", {
            "orchestration_id": "orch-1", "work_unit_states": {"wu-1": "RUNNING"},
            "active_executions": [], **state,
        })
        assert _takeover_work_unit(args) != 0
    assert GovernedTakeoverStore(project_root=tmp_path).load("orch-1") is None
