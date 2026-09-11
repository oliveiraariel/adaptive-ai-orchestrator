from application.provider_health_policy import ProviderHealthPolicy
from domain.provider_incident import ProviderIncident


def incident(*, retryable: bool = True) -> ProviderIncident:
    return ProviderIncident(
        provider="moonshot",
        model="moonshot/kimi-k3",
        category="quota",
        subtype="provider_rate_limit_unknown",
        scope="provider",
        retryable=retryable,
        confidence=0.7,
        evidence=("429",),
        recommended_action="backoff",
        status_code=429,
    )


def test_retryable_failures_open_circuit_at_threshold() -> None:
    policy = ProviderHealthPolicy(failure_threshold=3)

    assert policy.record_failure(
        incident(), cooldown_seconds=60, now=0
    ).state == "closed"
    assert policy.record_failure(
        incident(), cooldown_seconds=60, now=1
    ).state == "closed"
    third = policy.record_failure(
        incident(), cooldown_seconds=60, now=2
    )

    assert third.state == "open"
    assert policy.can_attempt(
        "moonshot", "moonshot/kimi-k3", now=30
    ).allowed is False
    probe = policy.can_attempt(
        "moonshot", "moonshot/kimi-k3", now=63
    )
    assert probe.allowed is True
    assert probe.state == "half_open"


def test_non_retryable_incident_opens_immediately() -> None:
    policy = ProviderHealthPolicy(failure_threshold=3)
    decision = policy.record_failure(
        incident(retryable=False),
        cooldown_seconds=600,
        now=0,
    )

    assert decision.state == "open"
    assert decision.allowed is False


def test_success_closes_and_resets_circuit() -> None:
    policy = ProviderHealthPolicy(failure_threshold=1)
    policy.record_failure(incident(), cooldown_seconds=60, now=0)
    assert policy.state_for("moonshot", "moonshot/kimi-k3") == "open"

    policy.record_success("moonshot", "moonshot/kimi-k3")

    assert policy.state_for("moonshot", "moonshot/kimi-k3") == "closed"
