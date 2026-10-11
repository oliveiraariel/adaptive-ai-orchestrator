from __future__ import annotations

from application.model_quota_continuity import (
    DEFAULT_COOLDOWN_SECONDS,
    ModelQuotaCooldownStore,
)
from application.model_routing_policy import ModelRoutingPolicy, ModelRoutingDecision
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage


def _task() -> TaskPackage:
    return TaskPackage(
        task_id="orch:1:wu:attempt-number:1",
        work_unit_id="wu-1",
        objective="Atualizar a agenda financeira.",
        configuration=ResourceConfiguration(
            agent="sgfp", runtime="openclaw",
        ),
        expected_output=("validated changes",),
        acceptance_criteria=("tests pass",),
    )


def _policy(store: ModelQuotaCooldownStore) -> ModelRoutingPolicy:
    return ModelRoutingPolicy(
        economy_model="openai/gpt-5.6-terra",
        economy_auth_profile="openai:oauth-primary",
        routine_thinking="medium",
        code_thinking="medium",
        quota_cooldowns=store,
    )


def test_gpt_to_kimi_to_gpt_after_five_hours_five_minutes(tmp_path) -> None:
    clock = [1000.0]
    path = tmp_path / "quota.json"
    store = ModelQuotaCooldownStore(path, wall_clock=lambda: clock[0])
    primary = _policy(store).select(_task())
    assert primary.model == "openai/gpt-5.6-terra"
    assert primary.thinking == "medium"

    assert store.record_quota(
        "openai", primary.model, primary.auth_profile,
        category="quota", subtype="provider_rate_limit_unknown",
    )

    # A fresh process/session sees the persisted cooldown, not just memory.
    restored = ModelQuotaCooldownStore(path, wall_clock=lambda: clock[0])
    active = _policy(restored).select(_task())
    assert active.model == "moonshot/kimi-k2.7-code"
    assert active.thinking is None
    assert active.tier == "quota-continuation"
    assert active.escalated_from == primary.model

    clock[0] += DEFAULT_COOLDOWN_SECONDS - 1
    assert _policy(restored).select(_task()).model == active.model
    clock[0] += 1
    returned = _policy(restored).select(_task())
    assert returned.model == primary.model
    assert returned.thinking == "medium"


def test_runtime_quota_fallback_prefers_kimi_and_does_not_retry_gpt(tmp_path) -> None:
    store = ModelQuotaCooldownStore(tmp_path / "quota.json")
    policy = _policy(store)
    primary = policy.select(_task())
    store.record_quota(
        "openai", primary.model, primary.auth_profile,
        category="quota", subtype="tpm",
    )
    followup = policy.fallback_for(primary, failure_reason="rate_limit")
    assert followup is not None
    assert followup.model == "moonshot/kimi-k2.7-code"
    assert followup.provider == "moonshot"
    assert followup.escalated_from == primary.model


def test_billing_and_nonrenewable_budget_never_enable_five_hour_reset(tmp_path) -> None:
    store = ModelQuotaCooldownStore(tmp_path / "quota.json")
    assert not store.record_quota(
        "openai", "openai/gpt-5.6-terra", "openai:oauth-primary",
        category="billing", subtype="insufficient_funds",
    )
    assert not store.record_quota(
        "openai", "openai/gpt-5.6-terra", "openai:oauth-primary",
        category="quota", subtype="weekly_usage_window",
    )
    assert not store.is_cooling(
        "openai", "openai/gpt-5.6-terra", "openai:oauth-primary"
    )


def test_cooldown_does_not_affect_a_different_profile(tmp_path) -> None:
    store = ModelQuotaCooldownStore(tmp_path / "quota.json")
    store.record_quota(
        "openai", "openai/gpt-5.6-terra", "openai:oauth-primary",
        category="quota", subtype="rpm",
    )
    assert not store.is_cooling(
        "openai", "openai/gpt-5.6-terra", "openai:oauth-secondary"
    )


def test_disabled_kimi_and_disabled_continuity_do_not_force_paid_route(tmp_path) -> None:
    store = ModelQuotaCooldownStore(tmp_path / "quota.json")
    store.record_quota(
        "openai", "openai/gpt-5.6-terra", "openai:oauth-primary",
        category="quota", subtype="rpm",
    )
    disabled_kimi = ModelRoutingPolicy(
        economy_model="openai/gpt-5.6-terra",
        economy_auth_profile="openai:oauth-primary",
        routine_thinking="medium",
        kimi_enabled=False, quota_cooldowns=store,
    )
    assert disabled_kimi.select(_task()).model == "openai/gpt-5.6-terra"
    disabled_state = ModelQuotaCooldownStore(
        tmp_path / "quota.json", enabled=False
    )
    assert _policy(disabled_state).select(_task()).model == "openai/gpt-5.6-terra"


def test_configuration_rejects_nonpositive_cooldown(tmp_path) -> None:
    import pytest
    with pytest.raises(ValueError, match="positive"):
        ModelQuotaCooldownStore(tmp_path / "quota.json", cooldown_seconds=0)
