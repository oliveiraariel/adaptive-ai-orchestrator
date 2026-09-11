from application.incident_classifier import IncidentClassifier
from domain.provider_incident import IncidentEvidence


def test_generic_429_remains_unknown_quota_not_assumed_tpm() -> None:
    incident = IncidentClassifier().classify(
        "API rate limit reached. Please try again later. 429",
        provider="moonshot",
        model="moonshot/kimi-k3",
    )

    assert incident is not None
    assert incident.category == "quota"
    assert incident.subtype == "provider_rate_limit_unknown"
    assert incident.retryable is True
    assert incident.confidence < 0.8


def test_project_daily_budget_evidence_outranks_generic_429() -> None:
    incident = IncidentClassifier().classify(
        "API rate limit reached. Please try again later. 429",
        provider="moonshot",
        model="moonshot/kimi-k3",
        evidence=IncidentEvidence(
            status_code=429,
            project_daily_budget_exhausted=True,
        ),
    )

    assert incident is not None
    assert incident.category == "quota"
    assert incident.subtype == "project_daily_budget"
    assert incident.scope == "project"
    assert incident.retryable is False
    assert incident.failover_reason == "rate_limit"


def test_tpm_rpm_and_concurrency_are_distinct_quota_causes() -> None:
    classifier = IncidentClassifier()

    tpm = classifier.classify(
        "TPM rate limit exceeded",
        provider="moonshot",
        model="moonshot/kimi-k3",
    )
    rpm = classifier.classify(
        "requests per minute limit exceeded",
        provider="moonshot",
        model="moonshot/kimi-k3",
    )
    concurrency = classifier.classify(
        "organization concurrency limit reached",
        provider="moonshot",
        model="moonshot/kimi-k3",
    )

    assert tpm is not None and tpm.subtype == "tpm"
    assert rpm is not None and rpm.subtype == "rpm"
    assert concurrency is not None and concurrency.subtype == "concurrency"


def test_openai_insufficient_credits_is_billing_not_rate_limit() -> None:
    incident = IncidentClassifier().classify(
        "You have no credits remaining. Add credits to continue.",
        provider="openai",
        model="openai/gpt-5.6-luna",
    )

    assert incident is not None
    assert incident.category == "billing"
    assert incident.subtype == "insufficient_funds"
    assert incident.retryable is False


def test_unknown_model_is_configuration_incident() -> None:
    incident = IncidentClassifier().classify(
        "Unknown model: kimi/k3",
        provider="kimi",
        model="kimi/k3",
    )

    assert incident is not None
    assert incident.category == "configuration"
    assert incident.subtype == "model_resolution"
    assert incident.failover_reason == "unavailable"


def test_semantic_quality_failure_is_not_provider_incident() -> None:
    incident = IncidentClassifier().classify(
        "acceptance criteria not satisfied",
        provider="openai",
        model="openai/gpt-5.6-luna",
    )

    assert incident is None
