"""Regression tests for opt-in execution profiles (no live Gateway needed)."""
from __future__ import annotations

from dataclasses import replace
import json

import pytest

from adaptive_orchestrator.cli import build_parser
from application.execution_profiles import (
    BUILTIN_PROFILES, ExecutionProfile, ExecutionProfileError,
    custom_profiles, delete_profile, get_profile, list_profiles, save_profile,
)
from application.run_project_orchestration import ProjectOrchestrationRequest
from application.continuous_project_orchestration import RunContinuousProjectOrchestration


def test_original_profile_has_no_routing_or_concurrency_overrides():
    profile = get_profile("original")
    assert profile.planner_model is None
    assert profile.worker_model is None
    assert profile.concurrency_mode is None
    assert profile.max_concurrency is None
    assert profile.worker_stall_overflow_slots is None
    assert profile.routing_policy("planner").pinned_model is None
    assert profile.routing_policy("worker").pinned_model is None


def test_economy_profile_pins_distinct_planner_and_worker_thinking(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth")
    profile = get_profile("economy-serial")
    planner = profile.routing_policy("planner")
    worker = profile.routing_policy("worker")
    assert planner.pinned_model == worker.pinned_model == "openai/gpt-5.6-luna"
    assert planner.pinned_thinking == "medium"
    assert worker.pinned_thinking == "low"
    assert profile.concurrency_mode == "FIXED"
    assert profile.max_concurrency == 1
    assert profile.worker_stall_overflow_slots == 0


def test_parallel_profile_is_bounded_and_direct_is_not_automatic():
    quality = get_profile("quality-parallel")
    direct = get_profile("governed-direct")
    assert quality.max_concurrency == 8
    assert direct.direct_takeover == "manual"
    assert direct.max_concurrency == 1


@pytest.mark.parametrize("changes", [
    {"name": "../out"},
    {"max_concurrency": 33},
    {"max_concurrency": True},
    {"worker_thinking": "medium"},
    {"planner_thinking": "ultra"},
    {"worker_model": "not-a-provider-model"},
    {"direct_takeover": "automatic"},
    {"concurrency_mode": "FIXED", "worker_stall_overflow_slots": 2},
])
def test_invalid_profile_values_fail_closed(changes):
    with pytest.raises(ExecutionProfileError):
        replace(ExecutionProfile(name="example"), **changes)


def test_custom_profile_crud_and_schema(tmp_path):
    path = tmp_path / "profiles.json"
    custom = ExecutionProfile(
        name="weekday", worker_model="openai/gpt-5.6-luna",
        worker_thinking="low", concurrency_mode="FIXED",
        max_concurrency=2, worker_stall_overflow_slots=0,
    )
    save_profile(custom, path)
    assert get_profile("weekday", path) == custom
    assert "weekday" in list_profiles(path)
    assert json.loads(path.read_text())["version"] == 1
    assert (path.stat().st_mode & 0o777) == 0o600
    delete_profile("weekday", path)
    assert custom_profiles(path) == {}
    with pytest.raises(ExecutionProfileError):
        get_profile("weekday", path)


def test_builtin_profiles_are_immutable(tmp_path):
    with pytest.raises(ExecutionProfileError):
        save_profile(BUILTIN_PROFILES["original"], tmp_path / "profiles.json")
    with pytest.raises(ExecutionProfileError):
        delete_profile("original", tmp_path / "profiles.json")


def test_registry_rejects_shadowing_and_unrecognized_fields(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({
        "version": 1, "profiles": {"original": BUILTIN_PROFILES["original"].to_dict()}
    }))
    with pytest.raises(ExecutionProfileError):
        custom_profiles(path)
    with pytest.raises(ExecutionProfileError):
        ExecutionProfile.from_dict({"name": "incomplete"})
    with pytest.raises(ExecutionProfileError):
        ExecutionProfile.from_dict({**BUILTIN_PROFILES["original"].to_dict(), "secret": "x"})


def test_checkpoint_round_trip_preserves_snapshot_not_mutable_registry():
    profile = get_profile("economy-serial")
    req = ProjectOrchestrationRequest(
        objective="test", execution_profile_snapshot=profile.to_dict(),
    )
    raw = RunContinuousProjectOrchestration._request_to_payload(req)
    checkpoint = {
        "orchestration_id": "orch-1", "request": raw, "phase": "ADMITTED",
    }
    recovered = RunContinuousProjectOrchestration._request_from_checkpoint(checkpoint)
    assert ExecutionProfile.from_dict(recovered.execution_profile_snapshot) == profile


def test_cli_profile_dispatch_flag_and_management_parser():
    parser = build_parser()
    args = parser.parse_args([
        "orchestrate", "--objective", "do work",
        "--execution-profile", "economy-serial",
    ])
    assert args.execution_profile == "economy-serial"
    assert parser.parse_args(["execution-profile", "list"]).profile_action == "list"
    assert parser.parse_args([
        "execution-profile", "save", "--file", "/tmp/profiles.json"
    ]).profile_action == "save"


def test_profile_applies_at_actual_model_selection_boundary(monkeypatch):
    """Pinned roles must beat even a planner-provided explicit worker model."""
    from domain.resource_configuration import ResourceConfiguration
    from domain.task_package import TaskPackage

    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-test")
    p = get_profile("economy-serial")
    task = TaskPackage(
        task_id="task-profile", work_unit_id="wu-profile",
        objective="Review critical transaction correctness.",
        configuration=ResourceConfiguration(
            agent="sgfp", runtime="openclaw",
            model="moonshot/kimi-k2.7-code",
        ),
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
    )
    planner = p.routing_policy("planner").select(task)
    worker = p.routing_policy("worker").select(task)
    assert planner.model == worker.model == "openai/gpt-5.6-luna"
    assert planner.thinking == "medium"
    assert worker.thinking == "low"
    assert planner.auth_profile == worker.auth_profile == "openai:oauth-test"
    assert planner.reason == worker.reason == "explicit-execution-profile"


def test_profiles_do_not_change_process_policy_or_other_runs(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-test")
    p = get_profile("economy-serial")
    worker = p.routing_policy("worker")
    original = get_profile("original").routing_policy("worker")
    assert worker.pinned_model == "openai/gpt-5.6-luna"
    assert original.pinned_model is None
    assert original.pinned_thinking is None


def test_bad_profile_snapshot_fails_closed():
    from application.execution_profiles import ExecutionProfile
    with pytest.raises(ExecutionProfileError):
        ExecutionProfile.from_dict({
            **get_profile("original").to_dict(), "direct_takeover": "automatic"
        })
