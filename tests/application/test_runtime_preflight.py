from application.runtime_preflight import RuntimePreflight
from domain.provider_incident import CredentialProfile, RuntimeSnapshot


def test_kimi_platform_key_rejects_kimi_code_style_route() -> None:
    snapshot = RuntimeSnapshot(
        provider="kimi",
        model="kimi/k3",
        credential_profile=CredentialProfile(
            provider="kimi",
            product="kimi-platform",
            auth_type="api-key",
            billing_mode="pay-as-you-go",
            endpoint_family="moonshot-platform",
            allowed_model_prefixes=("moonshot/",),
        ),
    )

    findings = RuntimePreflight().evaluate(snapshot)

    codes = {finding.code for finding in findings}
    assert "credential-route-mismatch" in codes
    assert "kimi-platform-vs-kimi-code-route" in codes
    assert RuntimePreflight().blocking_findings(snapshot)


def test_kimi_platform_key_accepts_moonshot_k3_route() -> None:
    snapshot = RuntimeSnapshot(
        provider="moonshot",
        model="moonshot/kimi-k3",
        credential_profile=CredentialProfile(
            provider="moonshot",
            product="kimi-platform",
            auth_type="api-key",
            billing_mode="pay-as-you-go",
            endpoint_family="moonshot-platform",
            allowed_model_prefixes=("moonshot/",),
        ),
    )

    assert RuntimePreflight().blocking_findings(snapshot) == ()


def test_authored_provider_catalog_shadowing_is_detected() -> None:
    snapshot = RuntimeSnapshot(
        provider="moonshot",
        model="moonshot/kimi-k3",
        plugin_models=(
            "moonshot/kimi-k3",
            "moonshot/kimi-k2.7-code",
        ),
        effective_catalog_models=("moonshot/kimi-k2.7-code",),
        authored_provider_models=("moonshot/kimi-k2.7-code",),
    )

    findings = RuntimePreflight().evaluate(snapshot)

    assert any(
        finding.code == "provider-catalog-shadowing"
        and finding.severity == "error"
        for finding in findings
    )


def test_context_window_mismatch_after_live_switch_is_detected() -> None:
    snapshot = RuntimeSnapshot(
        provider="moonshot",
        model="moonshot/kimi-k3",
        native_context_tokens=1_048_576,
        effective_context_tokens=200_000,
    )

    findings = RuntimePreflight().evaluate(snapshot)

    assert any(
        finding.code == "context-window-mismatch"
        and finding.severity == "warning"
        for finding in findings
    )


def test_core_plugin_version_mismatch_is_diagnostic_not_destructive() -> None:
    snapshot = RuntimeSnapshot(
        provider="moonshot",
        model="moonshot/kimi-k3",
        core_version="2026.9.4",
        plugin_version="2026.9.2",
    )

    findings = RuntimePreflight().evaluate(snapshot)

    match = next(
        finding
        for finding in findings
        if finding.code == "openclaw-plugin-version-mismatch"
    )
    assert match.severity == "warning"
    assert match.blocks_execution is False
