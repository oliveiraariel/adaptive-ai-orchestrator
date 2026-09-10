import pytest

from infrastructure.openclaw_gateway_client import (
    GatewayConfig,
    GatewayRun,
    OpenClawGatewayClient,
    OpenClawGatewayError,
)


def make_client(*, attempts: int = 3) -> tuple[OpenClawGatewayClient, str]:
    client = OpenClawGatewayClient(
        GatewayConfig(
            archive_completed_sessions=True,
            archive_cancelled_sessions=True,
            session_archive_attempts=attempts,
            session_archive_retry_delay_seconds=0,
        )
    )
    external_id = "gateway:run-001"
    client._runs[external_id] = GatewayRun(  # noqa: SLF001 - protocol seam test
        run_id="run-001",
        session_key="agent:main:orchestrator:task-001",
    )
    return client, external_id


def test_archive_uses_observed_session_identity_guard() -> None:
    client, external_id = make_client()
    calls: list[tuple[str, dict]] = []

    def rpc(method: str, params: dict) -> dict:
        calls.append((method, params))
        if method == "sessions.describe":
            return {
                "session": {
                    "sessionId": "session-001",
                    "archived": False,
                    "hasActiveRun": False,
                    "activeRunIds": [],
                }
            }
        if method == "sessions.patch":
            return {"ok": True}
        raise AssertionError(f"Unexpected method: {method}")

    client._rpc = rpc  # type: ignore[method-assign]

    outcome = client.archive(external_id, trigger="result-captured")

    assert outcome.status == "archived"
    assert outcome.archived is True
    assert calls == [
        ("sessions.describe", {"key": "agent:main:orchestrator:task-001"}),
        (
            "sessions.patch",
            {
                "key": "agent:main:orchestrator:task-001",
                "expectedSessionId": "session-001",
                "archived": True,
            },
        ),
    ]


def test_archive_retries_unavailable_without_changing_expected_session_id() -> None:
    client, external_id = make_client(attempts=3)
    patch_params: list[dict] = []

    def rpc(method: str, params: dict) -> dict:
        if method == "sessions.describe":
            return {
                "session": {
                    "sessionId": "session-stable",
                    "archived": False,
                    "activeRunIds": [],
                }
            }
        if method == "sessions.patch":
            patch_params.append(dict(params))
            if len(patch_params) == 1:
                raise OpenClawGatewayError(
                    "sessions.patch failed: {'code': 'UNAVAILABLE'}"
                )
            return {"ok": True}
        raise AssertionError(f"Unexpected method: {method}")

    client._rpc = rpc  # type: ignore[method-assign]

    outcome = client.archive(external_id)

    assert outcome.status == "archived"
    assert len(patch_params) == 2
    assert {
        item["expectedSessionId"] for item in patch_params
    } == {"session-stable"}


def test_archive_never_cancels_foreign_active_work() -> None:
    client, external_id = make_client()
    methods: list[str] = []

    def rpc(method: str, params: dict) -> dict:
        methods.append(method)
        if method == "sessions.describe":
            return {
                "session": {
                    "sessionId": "session-001",
                    "archived": False,
                    "hasActiveRun": True,
                    "activeRunIds": ["run-from-another-owner"],
                }
            }
        raise AssertionError("Archive patch must not run while foreign work is active")

    client._rpc = rpc  # type: ignore[method-assign]

    outcome = client.archive(external_id)

    assert outcome.status == "skipped-active"
    assert outcome.archived is False
    assert methods == ["sessions.describe"]


def test_completed_result_is_captured_before_session_is_archived() -> None:
    client, external_id = make_client()
    methods: list[str] = []
    client._wait_for_result = lambda run_id: {  # type: ignore[method-assign]
        "status": "ok",
        "runId": run_id,
    }

    def rpc(method: str, params: dict) -> dict:
        methods.append(method)
        if method == "chat.history":
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "captured"}],
                    }
                ]
            }
        if method == "sessions.describe":
            return {
                "session": {
                    "sessionId": "session-001",
                    "archived": False,
                    "activeRunIds": [],
                }
            }
        if method == "sessions.patch":
            return {"ok": True}
        raise AssertionError(f"Unexpected method: {method}")

    client._rpc = rpc  # type: ignore[method-assign]

    result = client.retrieve_result(external_id)

    assert isinstance(result, dict)
    assert result["output"] == "captured"
    assert result["session_lifecycle"] == {
        "status": "archived",
        "trigger": "result-captured",
        "archived": True,
    }
    assert methods == ["chat.history", "sessions.describe", "sessions.patch"]


def test_result_capture_failure_keeps_session_unarchived_for_diagnosis() -> None:
    client, external_id = make_client()
    methods: list[str] = []
    client._wait_for_result = lambda run_id: {  # type: ignore[method-assign]
        "status": "ok",
        "runId": run_id,
    }

    def rpc(method: str, params: dict) -> dict:
        methods.append(method)
        if method == "chat.history":
            return {"messages": []}
        raise AssertionError("Archive must not run before result capture succeeds")

    client._rpc = rpc  # type: ignore[method-assign]

    with pytest.raises(OpenClawGatewayError, match="no assistant text"):
        client.retrieve_result(external_id)

    assert methods == ["chat.history"]
    assert client.get_archive_outcome(external_id) is None


def test_archive_failure_is_nonfatal_after_result_capture() -> None:
    client, external_id = make_client(attempts=1)
    client._wait_for_result = lambda run_id: {  # type: ignore[method-assign]
        "status": "ok",
        "runId": run_id,
    }

    def rpc(method: str, params: dict) -> dict:
        if method == "chat.history":
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "done"}],
                    }
                ]
            }
        if method == "sessions.describe":
            return {
                "session": {
                    "sessionId": "session-001",
                    "archived": False,
                    "activeRunIds": [],
                }
            }
        if method == "sessions.patch":
            raise OpenClawGatewayError("archive unavailable")
        raise AssertionError(f"Unexpected method: {method}")

    client._rpc = rpc  # type: ignore[method-assign]

    result = client.retrieve_result(external_id)

    assert isinstance(result, dict)
    assert result["output"] == "done"
    assert result["session_lifecycle"] == {
        "status": "failed",
        "trigger": "result-captured",
        "archived": False,
        "error_type": "OpenClawGatewayError",
    }


def test_cancel_archives_only_after_abort_boundary() -> None:
    client, external_id = make_client()
    methods: list[str] = []

    def rpc(method: str, params: dict) -> dict:
        methods.append(method)
        if method == "sessions.abort":
            return {"aborted": True}
        if method == "sessions.describe":
            return {
                "session": {
                    "sessionId": "session-001",
                    "archived": False,
                    "activeRunIds": [],
                }
            }
        if method == "sessions.patch":
            return {"ok": True}
        raise AssertionError(f"Unexpected method: {method}")

    client._rpc = rpc  # type: ignore[method-assign]

    client.cancel(external_id)

    assert methods == ["sessions.abort", "sessions.describe", "sessions.patch"]
    outcome = client.get_archive_outcome(external_id)
    assert outcome is not None
    assert outcome.status == "archived"
    assert outcome.trigger == "cancelled"
