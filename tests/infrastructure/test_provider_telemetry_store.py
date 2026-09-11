import json

from application.remediation_policy import RemediationPolicy
from domain.provider_incident import ProviderIncident
from infrastructure.provider_telemetry_store import ProviderTelemetryStore


def test_provider_telemetry_is_structured_and_does_not_store_raw_secret(tmp_path) -> None:
    store = ProviderTelemetryStore(tmp_path / "provider-incidents.jsonl")
    incident = ProviderIncident(
        provider="moonshot",
        model="moonshot/kimi-k3",
        category="quota",
        subtype="project_daily_budget",
        scope="project",
        retryable=False,
        confidence=0.99,
        evidence=("project-daily-budget-exhausted", "http-429"),
        recommended_action="wait-or-raise-project-daily-budget",
        status_code=429,
    )
    remediation = RemediationPolicy().decide(incident)

    store.append_incident(
        incident,
        remediation,
        task_id="task-1",
        work_unit_id="wu-1",
        runtime_attempt=1,
    )

    payload = json.loads(
        (tmp_path / "provider-incidents.jsonl").read_text(encoding="utf-8")
    )
    assert payload["event"] == "provider-incident"
    assert payload["incident"]["subtype"] == "project_daily_budget"
    assert payload["remediation"]["allow_same_model_retry"] is False
    assert "api_key" not in payload
    assert "Authorization" not in payload
