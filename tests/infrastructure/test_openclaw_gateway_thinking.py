from typing import Any

from infrastructure.openclaw_gateway_client import GatewayConfig, OpenClawGatewayClient


class RecordingGatewayClient(OpenClawGatewayClient):
    def __init__(self) -> None:
        super().__init__(GatewayConfig())
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.requests.append((method, params))
        if method == "agent":
            return {"runId": "run-001", "acceptedAt": 123}
        return {"ok": True}


def make_payload(*, model: str, provider: str, thinking: str | None) -> dict:
    return {
        "task_id": "task-001",
        "work_unit_id": "wu-001",
        "objective": "do work",
        "scope": "",
        "context": [],
        "inputs": [],
        "artifacts": [],
        "decisions": [],
        "dependencies": [],
        "constraints": [],
        "expected_output": ["done"],
        "acceptance_criteria": ["status=ok"],
        "configuration": {
            "agent": "agent-001",
            "model": model,
            "provider": provider,
            "thinking": thinking,
        },
    }


def test_gateway_sends_openai_thinking_on_agent_rpc_without_admin_session_patch() -> None:
    client = RecordingGatewayClient()

    external = client.submit(
        make_payload(
            model="openai/gpt-5.6-luna",
            provider="openai",
            thinking="high",
        )
    )

    assert external == "gateway:run-001"
    assert [method for method, _ in client.requests] == ["sessions.patch", "agent"]

    session_patch = client.requests[0][1]
    assert session_patch["model"] == "openai/gpt-5.6-luna"
    assert "thinking" not in session_patch
    assert "thinkingLevel" not in session_patch

    agent_params = client.requests[1][1]
    assert agent_params["thinking"] == "high"


def test_gateway_omits_thinking_for_kimi_provider_native_reasoning() -> None:
    client = RecordingGatewayClient()

    client.submit(
        make_payload(
            model="moonshot/kimi-k2.7-code",
            provider="moonshot",
            thinking=None,
        )
    )

    agent_params = client.requests[1][1]
    assert "thinking" not in agent_params
