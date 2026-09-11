import json
import threading
import time

from websockets.sync.server import ServerConnection, serve

from infrastructure.openclaw_gateway_client import (
    GatewayConfig,
    OpenClawGatewayClient,
    OpenClawGatewayError,
)


def start_gateway(responses: dict[str, dict], *, protocol: int = 4):
    ready = threading.Event()
    holder: dict[str, object] = {}

    def handler(websocket: ServerConnection) -> None:
        websocket.send(json.dumps({
            "type": "event",
            "event": "connect.challenge",
            "payload": {"nonce": "n-001", "ts": int(time.time() * 1000)},
        }))

        connect_frame = json.loads(websocket.recv())
        holder["connect"] = connect_frame
        assert connect_frame["method"] == "connect"
        assert connect_frame["params"]["minProtocol"] == 4
        assert connect_frame["params"]["maxProtocol"] == 4

        websocket.send(json.dumps({
            "type": "res",
            "id": connect_frame["id"],
            "ok": True,
            "payload": {
                "type": "hello-ok",
                "protocol": protocol,
                "server": {"version": "test", "connId": "conn-001"},
                "features": {"methods": ["sessions.patch", "agent", "agent.wait", "sessions.abort"], "events": ["agent"]},
                "snapshot": {},
                "auth": {"role": "operator", "scopes": ["operator.read", "operator.write"]},
                "policy": {"maxPayload": 26214400, "maxBufferedBytes": 52428800, "tickIntervalMs": 15000},
            },
        }))

        request = json.loads(websocket.recv())
        method = request["method"]
        holder.setdefault("requests", []).append(request)
        payload = responses[method]
        websocket.send(json.dumps({
            "type": "res",
            "id": request["id"],
            "ok": True,
            "payload": payload,
        }))

    server = serve(handler, "127.0.0.1", 0)
    port = server.socket.getsockname()[1]
    holder["server"] = server
    ready.set()

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    ready.wait(1)
    return f"ws://127.0.0.1:{port}", holder, server, thread

def test_gateway_protocol_submit_status_result_and_cancel() -> None:
    responses = {
        "sessions.patch": {"ok": True},
        "agent": {"runId": "run-001", "acceptedAt": 123},
        "agent.wait": {
            "status": "ok",
            "startedAt": 100,
            "endedAt": 200,
            "stopReason": "stop",
        },
        "chat.history": {
            "sessionKey": "agent:agent-001:orchestrator:task-001",
            "messages": [
                {
                    "role": "user",
                    "content": "do work",
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "done",
                        }
                    ],
                    "stopReason": "stop",
                },
            ],
        },
        "sessions.abort": {"aborted": True},
    }

    url, holder, server, thread = start_gateway(responses)

    try:
        client = OpenClawGatewayClient(
            GatewayConfig(
                url=url,
                token="secret",
                archive_completed_sessions=False,
                archive_cancelled_sessions=False,
            )
        )

        external = client.submit({
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
                "model": "model-001",
                "provider": "provider-001",
            },
        })

        assert external == "gateway:run-001"
        assert client.get_status(external) == "COMPLETED"
        assert client.retrieve_result(external)["output"] == "done"

        client.cancel(external)

        request_methods = [
            request["method"]
            for request in holder["requests"]
        ]

        assert request_methods == [
            "sessions.patch",
            "agent",
            "agent.wait",
            "agent.wait",
            "chat.history",
            "sessions.abort",
        ]

        assert (
            holder["requests"][1]["params"]["sessionKey"]
            == "agent:agent-001:orchestrator:task-001"
        )

        assert holder["connect"]["params"]["auth"] == {
            "token": "secret"
        }

    finally:
        server.shutdown()
        thread.join(timeout=1)

def test_gateway_client_rejects_protocol_mismatch() -> None:
    url, _, server, thread = start_gateway({"agent": {"runId": "run-001"}}, protocol=3)
    try:
        client = OpenClawGatewayClient(GatewayConfig(url=url))
        try:
            client.submit({
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
                "configuration": {"agent": "agent-001"},
            })
        except OpenClawGatewayError as exc:
            assert "expected 4" in str(exc)
        else:
            raise AssertionError("Expected protocol mismatch to fail.")
        finally:
            server.shutdown()
            thread.join(timeout=1)
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_gateway_client_reports_wait_timeout_as_still_running() -> None:
    responses = {
        "sessions.patch": {"ok": True},
        "agent": {"runId": "run-001", "acceptedAt": 123},
        "agent.wait": {"status": "timeout"},
    }
    url, _, server, thread = start_gateway(responses)
    try:
        client = OpenClawGatewayClient(
            GatewayConfig(url=url, agent_result_timeout_seconds=0)
        )
        external = client.submit({
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
            "configuration": {"agent": "agent-001"},
        })
        assert client.get_status(external) == "RUNNING"
        try:
            client.retrieve_result(external)
        except OpenClawGatewayError as exc:
            assert "still running" in str(exc)
        else:
            raise AssertionError("Expected running execution to reject result retrieval.")
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_assistant_metadata_matches_message_with_text() -> None:
    history = {
        "messages": [
            {"role": "assistant", "content": [{"type": "text", "text": "done"}], "usage": {"total_tokens": 10}},
            {"role": "assistant", "content": [{"type": "toolCall"}], "usage": {"total_tokens": 99}},
        ]
    }
    assert OpenClawGatewayClient._extract_assistant_text(history) == "done"
    assert OpenClawGatewayClient._extract_assistant_metadata(history) == {"usage": {"total_tokens": 10}}


def test_gateway_client_retrieves_assistant_text_from_chat_history() -> None:
    responses = {
        "agent": {"runId": "run-002", "acceptedAt": 123},
        "agent.wait": {
            "status": "ok",
            "startedAt": 100,
            "endedAt": 200,
            "stopReason": "stop",
        },
        "chat.history": {
            "sessionKey": "agent:agent-001:orchestrator:task-002",
            "messages": [
                {
                    "role": "user",
                    "content": "do work",
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": "internal reasoning",
                        },
                        {
                            "type": "text",
                            "text": "ORCHESTRATOR_GATEWAY_OK",
                        },
                    ],
                    "stopReason": "stop",
                },
            ],
        },
    }

    url, holder, server, thread = start_gateway(responses)

    try:
        client = OpenClawGatewayClient(
            GatewayConfig(
                url=url,
                token="secret",
                archive_completed_sessions=False,
            )
        )

        external = client.submit({
            "task_id": "task-002",
            "work_unit_id": "wu-002",
            "objective": "do work",
            "scope": "",
            "context": [],
            "inputs": [],
            "artifacts": [],
            "decisions": [],
            "dependencies": [],
            "constraints": [],
            "expected_output": ["ORCHESTRATOR_GATEWAY_OK"],
            "acceptance_criteria": ["status=ok"],
            "configuration": {
                "agent": "agent-001",
            },
        })

        assert client.retrieve_result(external)["output"] == (
            "ORCHESTRATOR_GATEWAY_OK"
        )

        request_methods = [
            request["method"] for request in holder["requests"]
        ]
        assert request_methods == [
            "agent",
            "agent.wait",
            "chat.history",
        ]
        assert holder["requests"][2]["params"]["sessionKey"] == (
            "agent:agent-001:orchestrator:task-002"
        )
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_gateway_client_agent_wait_uses_long_poll_timeout_budget() -> None:
    ready = threading.Event()

    def handler(websocket: ServerConnection) -> None:
        websocket.send(json.dumps({
            "type": "event",
            "event": "connect.challenge",
            "payload": {"nonce": "n-long-poll", "ts": int(time.time() * 1000)},
        }))
        connect_frame = json.loads(websocket.recv())
        websocket.send(json.dumps({
            "type": "res",
            "id": connect_frame["id"],
            "ok": True,
            "payload": {
                "type": "hello-ok",
                "protocol": 4,
                "server": {"version": "test", "connId": "conn-long-poll"},
                "features": {"methods": ["agent", "agent.wait", "chat.history"], "events": ["agent"]},
                "snapshot": {},
                "auth": {"role": "operator", "scopes": ["operator.read", "operator.write"]},
                "policy": {"maxPayload": 26214400, "maxBufferedBytes": 52428800, "tickIntervalMs": 15000},
            },
        }))

        request = json.loads(websocket.recv())
        method = request["method"]
        if method == "agent":
            payload = {"runId": "run-long-poll", "acceptedAt": 123}
        elif method == "agent.wait":
            time.sleep(0.3)
            payload = {
                "status": "ok",
                "startedAt": 100,
                "endedAt": 200,
                "stopReason": "stop",
            }
        elif method == "chat.history":
            payload = {
                "sessionKey": "agent:agent-001:orchestrator:task-long-poll",
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "LONG_POLL_OK"}],
                        "stopReason": "stop",
                    }
                ],
            }
        else:
            raise AssertionError(f"Unexpected method: {method}")

        websocket.send(json.dumps({
            "type": "res",
            "id": request["id"],
            "ok": True,
            "payload": payload,
        }))

    server = serve(handler, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    ready.set()

    try:
        client = OpenClawGatewayClient(
            GatewayConfig(
                url=f"ws://127.0.0.1:{server.socket.getsockname()[1]}",
                timeout_seconds=0.2,
                agent_wait_timeout_ms=500,
                archive_completed_sessions=False,
            )
        )
        external = client.submit({
            "task_id": "task-long-poll",
            "work_unit_id": "wu-long-poll",
            "objective": "do work",
            "scope": "",
            "context": [],
            "inputs": [],
            "artifacts": [],
            "decisions": [],
            "dependencies": [],
            "constraints": [],
            "expected_output": ["LONG_POLL_OK"],
            "acceptance_criteria": ["status=ok"],
            "configuration": {"agent": "agent-001"},
        })

        assert client.retrieve_result(external)["output"] == "LONG_POLL_OK"
    finally:
        server.shutdown()
        thread.join(timeout=1)



def test_gateway_automatically_fails_over_luna_to_kimi_on_billing(monkeypatch) -> None:
    client = OpenClawGatewayClient(
        GatewayConfig(
            archive_completed_sessions=False,
            archive_cancelled_sessions=False,
        )
    )
    patched_models: list[str] = []
    agent_calls: list[dict] = []

    def fake_rpc(method: str, params: dict) -> dict:
        if method == "sessions.patch":
            patched_models.append(params["model"])
            return {"ok": True}
        if method == "agent":
            agent_calls.append(params)
            return {
                "runId": f"run-{len(agent_calls)}",
                "acceptedAt": 123,
            }
        if method == "agent.wait":
            if params["runId"] == "run-1":
                return {
                    "status": "error",
                    "error": "You have no credits remaining. Add credits to continue.",
                }
            return {
                "status": "ok",
                "startedAt": 100,
                "endedAt": 200,
                "stopReason": "stop",
            }
        if method == "chat.history":
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "KIMI_RECOVERED"}],
                    }
                ]
            }
        raise AssertionError(f"Unexpected RPC method: {method}")

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    external = client.submit(
        {
            "task_id": "task-billing-failover",
            "work_unit_id": "wu-billing-failover",
            "objective": "Implementar repository PHP simples.",
            "scope": "",
            "context": [],
            "inputs": [],
            "artifacts": [],
            "decisions": [],
            "dependencies": [],
            "constraints": [],
            "expected_output": ["done"],
            "acceptance_criteria": ["runtime-completed"],
            "configuration": {
                "agent": "sgfp",
                "model": "openai/gpt-5.6-luna",
                "provider": "openai",
                "thinking": "medium",
                "policy_constraints": [],
            },
        }
    )

    result = client.retrieve_result(external)

    assert result["output"] == "KIMI_RECOVERED"
    assert result["model_failover"] == {
        "triggered": True,
        "reason": "billing",
        "from_model": "openai/gpt-5.6-luna",
        "to_model": "moonshot/kimi-k2.7-code",
        "to_provider": "moonshot",
        "runtime_attempt": 2,
    }
    assert patched_models == [
        "openai/gpt-5.6-luna",
        "moonshot/kimi-k2.7-code",
    ]
    assert agent_calls[1]["idempotencyKey"].endswith(
        ":runtime-fallback:2"
    )
    fallback_message = json.loads(agent_calls[1]["message"])
    assert "automatic operational failover" in fallback_message["context"][-1]
    assert fallback_message["configuration"]["thinking"] is None
    assert client.get_status(external) == "COMPLETED"


def test_gateway_automatically_fails_over_kimi_to_luna_on_rate_limit(monkeypatch) -> None:
    client = OpenClawGatewayClient(
        GatewayConfig(
            archive_completed_sessions=False,
            archive_cancelled_sessions=False,
        )
    )
    patched_models: list[str] = []
    agent_calls: list[dict] = []

    def fake_rpc(method: str, params: dict) -> dict:
        if method == "sessions.patch":
            patched_models.append(params["model"])
            return {"ok": True}
        if method == "agent":
            agent_calls.append(params)
            return {
                "runId": f"run-{len(agent_calls)}",
                "acceptedAt": 123,
            }
        if method == "agent.wait":
            if params["runId"] == "run-1":
                return {
                    "status": "error",
                    "error": "provider slow down retry later",
                }
            return {
                "status": "ok",
                "startedAt": 100,
                "endedAt": 200,
                "stopReason": "stop",
            }
        if method == "chat.history":
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "LUNA_RECOVERED"}],
                    }
                ]
            }
        raise AssertionError(f"Unexpected RPC method: {method}")

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    external = client.submit(
        {
            "task_id": "task-rate-failover",
            "work_unit_id": "wu-rate-failover",
            "objective": "Definir arquitetura.",
            "scope": "",
            "context": [],
            "inputs": [],
            "artifacts": [],
            "decisions": [],
            "dependencies": [],
            "constraints": [],
            "expected_output": ["done"],
            "acceptance_criteria": ["runtime-completed"],
            "configuration": {
                "agent": "sgfp",
                "model": "moonshot/kimi-k2.7-code",
                "provider": "moonshot",
                "thinking": None,
                "policy_constraints": [],
            },
        }
    )

    result = client.retrieve_result(external)

    assert result["output"] == "LUNA_RECOVERED"
    assert result["model_failover"]["reason"] == "rate_limit"
    assert result["model_failover"]["to_model"] == "openai/gpt-5.6-luna"
    assert patched_models == [
        "moonshot/kimi-k2.7-code",
        "openai/gpt-5.6-luna",
    ]
    fallback_message = json.loads(agent_calls[1]["message"])
    assert fallback_message["configuration"]["thinking"] == "medium"


def test_gateway_does_not_fail_over_for_unclassified_semantic_failure(monkeypatch) -> None:
    client = OpenClawGatewayClient(
        GatewayConfig(
            archive_completed_sessions=False,
            archive_cancelled_sessions=False,
        )
    )

    def fake_rpc(method: str, params: dict) -> dict:
        if method == "sessions.patch":
            return {"ok": True}
        if method == "agent":
            return {"runId": "run-1", "acceptedAt": 123}
        if method == "agent.wait":
            return {
                "status": "error",
                "error": "acceptance criteria not satisfied",
            }
        raise AssertionError(f"Unexpected RPC method: {method}")

    monkeypatch.setattr(client, "_rpc", fake_rpc)

    external = client.submit(
        {
            "task_id": "task-semantic-failure",
            "work_unit_id": "wu-semantic-failure",
            "objective": "Implementar repository PHP simples.",
            "scope": "",
            "context": [],
            "inputs": [],
            "artifacts": [],
            "decisions": [],
            "dependencies": [],
            "constraints": [],
            "expected_output": ["done"],
            "acceptance_criteria": ["runtime-completed"],
            "configuration": {
                "agent": "sgfp",
                "model": "openai/gpt-5.6-luna",
                "provider": "openai",
                "thinking": "medium",
                "policy_constraints": [],
            },
        }
    )

    try:
        client.retrieve_result(external)
    except OpenClawGatewayError as exc:
        assert "acceptance criteria not satisfied" in str(exc)
    else:
        raise AssertionError("Expected unclassified failure to remain terminal.")
