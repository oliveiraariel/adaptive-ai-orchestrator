from application.remediation_policy import RemediationPolicy
from domain.provider_incident import ProviderIncident


def make_incident(*, category: str, subtype: str, retryable: bool) -> ProviderIncident:
    return ProviderIncident(
        provider="moonshot",
        model="moonshot/kimi-k3",
        category=category,  # type: ignore[arg-type]
        subtype=subtype,
        scope="project",
        retryable=retryable,
        confidence=0.95,
        evidence=("test",),
        recommended_action="test",
        status_code=429,
    )


def test_budget_exhaustion_suppresses_same_model_retry() -> None:
    decision = RemediationPolicy().decide(
        make_incident(
            category="quota",
            subtype="project_daily_budget",
            retryable=False,
        )
    )

    assert decision.allow_same_model_retry is False
    assert decision.fallback_allowed is True
    assert decision.requires_human_action is True


def test_generic_429_allows_only_bounded_retry_then_fallback() -> None:
    decision = RemediationPolicy().decide(
        make_incident(
            category="quota",
            subtype="provider_rate_limit_unknown",
            retryable=True,
        )
    )

    assert decision.allow_same_model_retry is True
    assert decision.fallback_allowed is True
    assert decision.cooldown_seconds == 60


def test_auth_failure_requires_credential_verification() -> None:
    decision = RemediationPolicy().decide(
        make_incident(
            category="auth",
            subtype="credential_rejected",
            retryable=False,
        )
    )

    assert decision.allow_same_model_retry is False
    assert decision.requires_human_action is True
    assert "credential" in decision.action
