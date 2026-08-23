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
                "features": {"methods": ["agent", "agent.wait", "sessions.abort"], "events": ["agent"]},
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
        "agent": {"runId": "run-001", "acceptedAt": 123},
        "agent.wait": {"status": "ok", "startedAt": 100, "endedAt": 200, "output": "done"},
        "sessions.abort": {"aborted": True},
    }
    url, holder, server, thread = start_gateway(responses)
    try:
        client = OpenClawGatewayClient(GatewayConfig(url=url, token="secret"))
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

        request_methods = [request["method"] for request in holder["requests"]]
        assert request_methods == ["agent", "agent.wait", "agent.wait", "sessions.abort"]
        assert holder["requests"][0]["params"]["sessionKey"] == "orchestrator:task-001"
        assert holder["connect"]["params"]["auth"] == {"token": "secret"}
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


def test_gateway_client_reports_wait_timeout_as_still_running() -> None:
    responses = {
        "agent": {"runId": "run-001", "acceptedAt": 123},
        "agent.wait": {"status": "timeout"},
    }
    url, _, server, thread = start_gateway(responses)
    try:
        client = OpenClawGatewayClient(GatewayConfig(url=url))
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
        assert client.get_status(external) == "TIMEOUT"
        try:
            client.retrieve_result(external)
        except OpenClawGatewayError as exc:
            assert "still running" in str(exc)
        else:
            raise AssertionError("Expected running execution to reject result retrieval.")
    finally:
        server.shutdown()
        thread.join(timeout=1)
