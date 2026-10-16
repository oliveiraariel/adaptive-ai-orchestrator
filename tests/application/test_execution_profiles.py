"""Regression tests for opt-in execution profiles (no live Gateway needed)."""
from __future__ import annotations

from dataclasses import replace
import json

import pytest

from application import execution_profiles as execution_profiles_module
from adaptive_orchestrator.cli import build_parser
from application.execution_profiles import (
    BUILTIN_PROFILES, ExecutionProfile, ExecutionProfileError,
    custom_profiles, delete_profile, get_profile, list_profiles, save_profile,
    load_selection_policy, set_default_execution_profile, select_new_project_profile,
    ExecutionProfileSelectionPolicy,
    AgentRoleSelectionPolicy, load_agent_role_policy, set_default_agent_roles,
    resolve_project_agents,
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


def test_user_defined_four_profiles_and_rules():
    terra = get_profile("gpt-terra-medium-low")
    luna = get_profile("gpt-luna-medium-low")
    direct = get_profile("gpt-fallback-direto")
    kimi = get_profile("kimi-k3-k27")
    assert (terra.planner_model, terra.planner_thinking) == (
        "openai/gpt-5.6-terra", "medium"
    )
    assert (terra.worker_model, terra.worker_thinking) == (
        "openai/gpt-5.6-terra", "low"
    )
    assert terra.worker_fallback_models == ("moonshot/kimi-k2.7-code",)
    assert terra.planner_fallback_models == ("moonshot/kimi-k2.7-code",)
    assert terra.quality_direct_fallback is True
    assert (luna.planner_model, luna.planner_thinking) == (
        "openai/gpt-5.6-luna", "medium"
    )
    assert (luna.worker_model, luna.worker_thinking) == (
        "openai/gpt-5.6-luna", "low"
    )
    assert luna.worker_fallback_models == luna.planner_fallback_models == ()
    assert luna.max_concurrency == 1 and luna.concurrency_mode == "FIXED"
    assert direct.direct_owner_mode is True
    assert direct.worker_model == direct.planner_model
    assert direct.worker_thinking == direct.planner_thinking
    assert kimi.planner_model == "moonshot/kimi-k3"
    assert kimi.worker_model == "moonshot/kimi-k2.7-code"
    assert kimi.worker_fallback_models == ("openai/gpt-5.6-terra",)


def test_quota_only_fallback_is_bounded_and_not_a_quality_fallback(monkeypatch):
    from application.model_routing_policy import ModelRoutingDecision
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-test")
    terra = get_profile("gpt-terra-medium-low").routing_policy("worker")
    primary = ModelRoutingDecision(
        model="openai/gpt-5.6-terra", provider="openai",
        auth_profile="openai:oauth-test", tier="execution-profile",
        reason="test", attempt=1, thinking="low", thinking_reason="test",
    )
    assert terra.fallback_for(primary, failure_reason="timeout") is None
    decision = terra.fallback_for(primary, failure_reason="quota")
    assert decision is not None
    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.thinking is None
    excluded = frozenset({(decision.model, decision.auth_profile)})
    assert terra.fallback_for(primary, failure_reason="quota", excluded_routes=excluded) is None
    luna = get_profile("gpt-luna-medium-low").routing_policy("worker")
    assert luna.fallback_for(primary, failure_reason="quota") is None
    kimi = get_profile("kimi-k3-k27").routing_policy("worker")
    alternate = kimi.fallback_for(
        ModelRoutingDecision(
            model="moonshot/kimi-k2.7-code", provider="moonshot",
            auth_profile="moonshot:api-key", tier="execution-profile",
            reason="test", attempt=1, thinking=None, thinking_reason="test",
        ), failure_reason="rate_limit",
    )
    assert alternate is not None
    assert alternate.model == "openai/gpt-5.6-terra"
    assert alternate.thinking == "low"
    assert alternate.auth_profile == "openai:oauth-test"


def test_k3_opt_in_is_scoped_and_default_exclusion_persists(monkeypatch):
    from application.model_routing_policy import ModelRoutingPolicy
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-test")
    model = "moonshot/kimi-k3"
    assert ModelRoutingPolicy.from_env().is_disabled(model)
    chosen = get_profile("kimi-k3-k27").routing_policy("planner")
    assert not chosen.is_disabled(model)
    assert chosen.pinned_model == model
    assert ModelRoutingPolicy.from_env().is_disabled(model)


def test_missing_openai_oauth_profile_fails_closed(monkeypatch):
    monkeypatch.delenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", raising=False)
    with pytest.raises(ExecutionProfileError):
        get_profile("gpt-luna-medium-low").routing_policy("worker")
    with pytest.raises(ExecutionProfileError):
        get_profile("kimi-k3-k27").routing_policy("worker")


def test_runtime_gateway_respects_profile_allowlist(monkeypatch):
    from types import SimpleNamespace
    from infrastructure.openclaw_gateway_client import OpenClawGatewayClient
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-test")
    client = object.__new__(OpenClawGatewayClient)
    terra_run = SimpleNamespace(runtime_attempt=1, task_payload={
        "configuration": {
            "model": "openai/gpt-5.6-terra",
            "provider": "openai",
            "auth_profile": "openai:oauth-test",
            "thinking": "low",
            "policy_constraints": [
                "adaptive-profile-quota-fallback-models:moonshot/kimi-k2.7-code",
            ],
        }, "context": [],
    })
    next_payload = client._build_failover_payload(terra_run, "quota")
    assert next_payload is not None
    assert next_payload["configuration"]["model"] == "moonshot/kimi-k2.7-code"
    assert client._build_failover_payload(terra_run, "timeout") is None
    luna_run = SimpleNamespace(runtime_attempt=1, task_payload={
        "configuration": {
            **terra_run.task_payload["configuration"],
            "model": "openai/gpt-5.6-luna",
            "policy_constraints": ["adaptive-profile-quota-fallback-models:none"],
        }, "context": [],
    })
    assert client._build_failover_payload(luna_run, "quota") is None
    secondary = SimpleNamespace(runtime_attempt=2, task_payload={
        **next_payload,
        "configuration": next_payload["configuration"],
    })
    assert client._build_failover_payload(secondary, "quota") is None


def test_fallback_direto_batch_intent_does_not_touch_completed_work(tmp_path, capsys):
    from adaptive_orchestrator.cli import main
    from application.governed_takeover import GovernedTakeoverStore
    from infrastructure.project_orchestration_checkpoint import FileProjectOrchestrationCheckpointStore

    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save("one", {
        "terminal": False, "desired_state": "RUNNING",
        "request": {"agent": "sgfp", "planner_agent": "adaptive"},
        "work_unit_states": {
            "done": "COMPLETED", "now": "RUNNING",
            "later": "READY", "manual": "BLOCKED",
        },
        "plan": {"work_units": [
            {"id": "done", "kind": "EXECUTION"},
            {"id": "now", "kind": "EXECUTION"},
            {"id": "later", "kind": "EXECUTION"},
            {"id": "manual", "kind": "HUMAN_ACTION"},
        ]},
    })
    args = [
        "fallback-direto", "--orchestration-id", "one",
        "--project-root", str(tmp_path), "--owner-agent", "adaptive",
        "--actor", "user", "--reason", "Switch pending tasks to direct owner",
        "--authorize", "--all-pending",
    ]
    assert main(args) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "REQUESTED"
    assert set(out["target_work_unit_ids"]) == {"now", "later"}
    takeover = GovernedTakeoverStore(project_root=tmp_path)
    assert takeover.current("one", "done") is None
    assert takeover.current("one", "later")["mode"] == "direct"
    assert main(args) == 0  # idempotent
    capsys.readouterr()


def test_switch_profile_requires_quiescence_and_persists_audit(monkeypatch, tmp_path, capsys):
    from adaptive_orchestrator.cli import main
    from infrastructure.orchestration_control_plane import FileOrchestrationControlPlane
    from infrastructure.project_orchestration_checkpoint import FileProjectOrchestrationCheckpointStore
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-test")
    state = {
        "terminal": False, "desired_state": "PAUSED", "active_executions": [],
        "request": {
            "agent": "sgfp", "planner_agent": "adaptive",
            "execution_profile_snapshot": get_profile("original").to_dict(),
            "concurrency_mode": "AUTO", "max_concurrency": 4,
            "worker_stall_overflow_slots": 1,
        },
    }
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save("one", state)
    args = [
        "switch-execution-profile", "--orchestration-id", "one",
        "--project-root", str(tmp_path), "--execution-profile", "gpt-luna-medium-low",
        "--actor", "user", "--reason", "Conserve tokens", "--authorize",
    ]
    assert main(args) != 0
    capsys.readouterr()
    control = FileOrchestrationControlPlane(project_root=tmp_path)
    control.mark_quiescent(orchestration_id="one", checkpoint=state, reason="test")
    assert main(args) == 0
    result = store.load("one")
    assert result["request"]["max_concurrency"] == 1
    assert result["request"]["concurrency_mode"] == "FIXED"
    assert result["request"]["execution_profile_snapshot"]["name"] == "gpt-luna-medium-low"
    assert len(result["execution_profile_history"]) == 1


def test_coordinator_owner_direct_session_uses_planner_thinking(monkeypatch, tmp_path):
    from domain.resource_configuration import ResourceConfiguration
    from domain.task_package import TaskPackage
    from infrastructure.openclaw_adapter import OpenClawAdapter
    from infrastructure.model_routing_audit import ModelRoutingAuditLog

    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-test")
    profile = get_profile("gpt-terra-medium-low")

    class Client:
        def __init__(self):
            self.submitted = []

        def submit(self, payload):
            self.submitted.append(payload)
            return "fake-run"

    client = Client()
    runtime = OpenClawAdapter(
        client, model_routing_policy=profile.routing_policy("worker"),
        owner_agent="adaptive",
        owner_model_routing_policy=profile.routing_policy("planner"),
        audit_log=ModelRoutingAuditLog(tmp_path / "routing.jsonl"),
    )
    for agent in ("sgfp", "adaptive"):
        runtime.submit(TaskPackage(
            task_id=f"task:{agent}", work_unit_id=f"wu:{agent}",
            objective="Correct an authorized coding task",
            configuration=ResourceConfiguration(agent=agent, runtime="openclaw"),
            expected_output=("report",), acceptance_criteria=("tests pass",),
        ))
    worker = client.submitted[0]["configuration"]
    direct = client.submitted[1]["configuration"]
    assert worker["model"] == direct["model"] == "openai/gpt-5.6-terra"
    assert worker["thinking"] == "low"
    assert direct["thinking"] == "medium"
    assert "adaptive-profile-quota-fallback-models:moonshot/kimi-k2.7-code" in (
        direct["policy_constraints"]
    )


def test_capacity_error_returns_wu_without_unbounded_retry():
    from types import SimpleNamespace
    from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState
    from application.continuous_project_orchestration import RunContinuousProjectOrchestration

    released = []
    controller = object.__new__(RunContinuousProjectOrchestration)
    controller._claims = SimpleNamespace(release=lambda claim: released.append(claim))
    work = WorkUnit(
        id=WorkUnitId("wu1"), objective="example", state=WorkUnitState.RUNNING,
    )
    records = []
    feedback = {}
    outcome = SimpleNamespace(claim="claim", work_unit_id="wu1", execution=None)
    pending = controller._handle_runtime_result_error(
        outcome=outcome,
        error=RuntimeError("PROFILE_MODEL_CAPACITY_EXHAUSTED"),
        generation=1, specs={"wu1": SimpleNamespace(role="executor")},
        work_units={"wu1": work}, skill_sets={"wu1": ()},
        attempts={"wu1": 1}, strategy_generations={"wu1": 1},
        records=records, revision_feedback=feedback,
        max_attempts=2, max_strategies=2,
    )
    assert pending is False
    assert work.state is WorkUnitState.BLOCKED
    assert records[0].status == "BLOCKED"
    assert "PROFILE_MODEL_CAPACITY_EXHAUSTED" in records[0].reason
    assert released == ["claim"]


def test_default_policy_is_backward_compatible_until_operator_sets_it(tmp_path):
    file = tmp_path / "selection.json"
    assert load_selection_policy(file) == ExecutionProfileSelectionPolicy()
    assert select_new_project_profile(None, policy_path=file).name == "original"
    # Explicit run-scoped profiles keep working on installations that have not
    # opted in to an operator-locked default.
    assert select_new_project_profile("gpt-terra-medium-low", policy_path=file).name == "gpt-terra-medium-low"


def test_authorized_default_luna_applies_to_new_projects_only(tmp_path):
    file = tmp_path / "selection.json"
    with pytest.raises(ExecutionProfileError, match="authorization"):
        set_default_execution_profile(
            "gpt-luna-medium-low", authorized=False, actor="operator",
            reason="Prefer serial GPT Luna", path=file,
        )
    assert not file.exists()
    chosen = set_default_execution_profile(
        "gpt-luna-medium-low", authorized=True, actor="operator",
        reason="Prefer serial GPT Luna", path=file,
    )
    assert chosen.default_profile == "gpt-luna-medium-low"
    assert chosen.require_authorized_override
    assert (file.stat().st_mode & 0o777) == 0o600
    assert load_selection_policy(file) == chosen
    profile = select_new_project_profile(None, policy_path=file)
    assert profile.name == "gpt-luna-medium-low"
    assert profile.planner_thinking == "medium"
    assert profile.worker_thinking == "low"
    assert profile.concurrency_mode == "FIXED"
    assert profile.max_concurrency == 1
    assert profile.worker_stall_overflow_slots == 0
    assert profile.planner_fallback_models == ()
    assert profile.worker_fallback_models == ()
    assert get_profile("original").name == "original"


def _write_openclaw_agents(path, *agent_ids):
    path.write_text(json.dumps({"agents": {"entries": {
        agent_id: {"name": agent_id} for agent_id in agent_ids
    }}}))


def _mock_openclaw_agent_list(monkeypatch, *agent_ids):
    def run(*args, **kwargs):
        assert kwargs["env"]["OPENCLAW_CONFIG_PATH"]
        return type("Completed", (), {
            "returncode": 0,
            "stdout": json.dumps({"agents": [{"id": agent_id} for agent_id in agent_ids]}),
        })()
    monkeypatch.setattr(execution_profiles_module.subprocess, "run", run)


def test_quality_profile_resolves_persistent_distinct_roles_before_admission(tmp_path, monkeypatch):
    config = tmp_path / "openclaw.json"
    policy = tmp_path / "agent-roles.json"
    _write_openclaw_agents(config, "adaptive", "main")
    _mock_openclaw_agent_list(monkeypatch, "adaptive", "main")
    monkeypatch.setenv("ADAPTIVE_OPENCLAW_CONFIG_FILE", str(config))
    set_default_agent_roles(
        "adaptive", "main", authorized=True, actor="operator",
        reason="Use adaptive coordinator and main executor", path=policy,
    )
    assert load_agent_role_policy(policy) == AgentRoleSelectionPolicy(
        "adaptive", "main", "operator", "Use adaptive coordinator and main executor"
    )
    assert resolve_project_agents(
        get_profile("gpt-luna-medium-low"), requested_worker=None,
        requested_planner=None, policy_path=policy, config_path=config,
    ) == ("main", "adaptive")


def test_quality_profile_preserves_explicit_valid_roles_and_rejects_conflicts(tmp_path, monkeypatch):
    config = tmp_path / "openclaw.json"
    policy = tmp_path / "agent-roles.json"
    _write_openclaw_agents(config, "adaptive", "main", "other")
    _mock_openclaw_agent_list(monkeypatch, "adaptive", "main", "other")
    policy.write_text(json.dumps({"version": 1, "planner_agent": "adaptive",
        "worker_agent": "main", "actor": "operator", "reason": "test"}))
    profile = get_profile("gpt-luna-medium-low")
    assert resolve_project_agents(profile, requested_worker="other",
        requested_planner="adaptive", policy_path=policy, config_path=config) == ("other", "adaptive")
    with pytest.raises(ExecutionProfileError, match="distinct"):
        resolve_project_agents(profile, requested_worker="adaptive",
            requested_planner="adaptive", policy_path=policy, config_path=config)
    with pytest.raises(ExecutionProfileError, match="do not exist"):
        resolve_project_agents(profile, requested_worker="missing",
            requested_planner=None, policy_path=policy, config_path=config)


def test_quality_profile_without_role_policy_fails_closed(tmp_path):
    config = tmp_path / "openclaw.json"
    _write_openclaw_agents(config, "adaptive", "main")
    with pytest.raises(ExecutionProfileError, match="not configured"):
        resolve_project_agents(get_profile("gpt-luna-medium-low"),
            requested_worker=None, requested_planner=None,
            policy_path=tmp_path / "missing.json", config_path=config)


def test_non_quality_profile_keeps_legacy_agent_compatibility(tmp_path):
    config = tmp_path / "openclaw.json"
    _write_openclaw_agents(config, "main")
    assert resolve_project_agents(get_profile("original"),
        requested_worker=None, requested_planner=None, config_path=config) == ("main", None)


def test_openclaw_json5_and_openclaw_config_path_are_delegated_to_authoritative_cli(tmp_path, monkeypatch):
    config = tmp_path / "openclaw.json5"
    config.write_text("// JSON5 fixture\n{ agents: { entries: { adaptive: {}, main: {} } } }")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return type("Completed", (), {
            "returncode": 0,
            "stdout": json.dumps({"agents": [{"id": "adaptive"}, {"id": "main"}]}),
        })()

    monkeypatch.setattr(execution_profiles_module.subprocess, "run", run)
    assert execution_profiles_module.eligible_openclaw_agents(config) == {"adaptive", "main"}
    assert calls[0][1]["env"]["OPENCLAW_CONFIG_PATH"] == str(config)


def test_openclaw_agent_query_timeout_is_configurable_and_finite(tmp_path, monkeypatch):
    config = tmp_path / "openclaw.json5"
    calls = []

    def run(command, **kwargs):
        calls.append(kwargs["timeout"])
        return type("Completed", (), {
            "returncode": 0, "stdout": json.dumps({"agents": [{"id": "main"}]}),
        })()

    monkeypatch.setenv("ADAPTIVE_OPENCLAW_AGENTS_TIMEOUT", "22")
    monkeypatch.setattr(execution_profiles_module.subprocess, "run", run)
    assert execution_profiles_module.eligible_openclaw_agents(config) == {"main"}
    assert calls == [22.0]

    monkeypatch.setenv("ADAPTIVE_OPENCLAW_AGENTS_TIMEOUT", "999")
    execution_profiles_module.eligible_openclaw_agents(config)
    assert calls[-1] == 60.0


def test_openclaw_agent_query_rejects_invalid_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTIVE_OPENCLAW_AGENTS_TIMEOUT", "inf")
    with pytest.raises(ExecutionProfileError, match="finite positive"):
        execution_profiles_module.eligible_openclaw_agents(tmp_path / "openclaw.json5")


def test_openclaw_agent_query_reports_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("ADAPTIVE_OPENCLAW_AGENTS_TIMEOUT", "18")

    def timeout(*args, **kwargs):
        raise execution_profiles_module.subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(execution_profiles_module.subprocess, "run", timeout)
    with pytest.raises(ExecutionProfileError, match="timed out after 18 seconds"):
        execution_profiles_module.eligible_openclaw_agents(tmp_path / "openclaw.json5")


def test_explicit_roles_do_not_require_persistent_defaults(tmp_path, monkeypatch):
    config = tmp_path / "openclaw.json5"
    _write_openclaw_agents(config, "adaptive", "main")
    _mock_openclaw_agent_list(monkeypatch, "adaptive", "main")
    result = resolve_project_agents(
        get_profile("gpt-luna-medium-low"), requested_worker="main",
        requested_planner="adaptive", policy_path=tmp_path / "missing.json",
        config_path=config,
    )
    assert result == ("main", "adaptive")


def test_nondefault_profile_requires_explicit_operator_attestation(tmp_path):
    file = tmp_path / "selection.json"
    set_default_execution_profile(
        "gpt-luna-medium-low", authorized=True, actor="operator",
        reason="Prefer serial GPT Luna", path=file,
    )
    for kwargs in [
        {},
        {"override_authorized": True},
        {"override_authorized": True, "override_actor": "operator"},
        {"override_authorized": True, "override_reason": "Human requested other profile"},
    ]:
        with pytest.raises(ExecutionProfileError, match="human authorization"):
            select_new_project_profile(
                "gpt-terra-medium-low", policy_path=file, **kwargs
            )
    alternate = select_new_project_profile(
        "gpt-terra-medium-low", policy_path=file,
        override_authorized=True, override_actor="operator",
        override_reason="Human explicitly requested alternate profile",
    )
    assert alternate.name == "gpt-terra-medium-low"
    assert load_selection_policy(file).default_profile == "gpt-luna-medium-low"
    assert select_new_project_profile(None, policy_path=file).name == "gpt-luna-medium-low"


def test_corrupt_default_policy_fails_closed_without_dispatched_project(tmp_path):
    file = tmp_path / "selection.json"
    for raw in [
        "{not json",
        '{"version":2,"default_profile":"original","require_authorized_override":true,"actor":"user","reason":"yes"}',
        '{"version":1,"default_profile":"original","require_authorized_override":false,"actor":"user","reason":"yes"}',
        '{"version":1,"default_profile":"unknown-profile","require_authorized_override":true,"actor":"user","reason":"yes"}',
    ]:
        file.write_text(raw)
        with pytest.raises(ExecutionProfileError):
            select_new_project_profile(None, policy_path=file)


def test_cli_default_policy_management_and_override_flags():
    parser = build_parser()
    no_profile = parser.parse_args(["orchestrate", "--objective", "Implement feature"])
    assert no_profile.execution_profile is None
    assert not no_profile.authorize_profile_override
    alternate = parser.parse_args([
        "orchestrate", "--objective", "Implement feature",
        "--execution-profile", "gpt-terra-medium-low",
        "--authorize-profile-override", "--profile-override-actor", "user",
        "--profile-override-reason", "human requested parallel profile",
    ])
    assert alternate.execution_profile == "gpt-terra-medium-low"
    assert alternate.authorize_profile_override
    assert parser.parse_args(["execution-profile", "default"]).profile_action == "default"
    configured = parser.parse_args([
        "execution-profile", "set-default", "gpt-luna-medium-low",
        "--actor", "user", "--reason", "Prefer Luna", "--authorize",
    ])
    assert configured.profile_action == "set-default"
    assert configured.authorize
