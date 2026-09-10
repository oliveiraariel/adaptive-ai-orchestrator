from infrastructure.openclaw_gateway_client import (
    GatewayConfig,
    OpenClawGatewayClient,
)


def test_session_auto_archive_is_enabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ADAPTIVE_SESSION_AUTO_ARCHIVE", raising=False)

    client = OpenClawGatewayClient(GatewayConfig())

    assert client._archive_completed_sessions is True  # noqa: SLF001
    assert client._archive_cancelled_sessions is True  # noqa: SLF001


def test_session_auto_archive_can_be_disabled_with_environment_override(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ADAPTIVE_SESSION_AUTO_ARCHIVE", "0")

    client = OpenClawGatewayClient(GatewayConfig())

    assert client._archive_completed_sessions is False  # noqa: SLF001
    assert client._archive_cancelled_sessions is False  # noqa: SLF001


def test_explicit_gateway_config_overrides_environment(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVE_SESSION_AUTO_ARCHIVE", "0")

    client = OpenClawGatewayClient(
        GatewayConfig(
            archive_completed_sessions=True,
            archive_cancelled_sessions=True,
        )
    )

    assert client._archive_completed_sessions is True  # noqa: SLF001
    assert client._archive_cancelled_sessions is True  # noqa: SLF001
