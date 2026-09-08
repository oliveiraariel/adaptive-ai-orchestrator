import json
import threading
import time

from websockets.sync.server import ServerConnection, serve

from application.agent_runtime import AgentRuntimeStatus
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from infrastructure.openclaw_adapter import OpenClawAdapter
from infrastructure.openclaw_gateway_client import GatewayConfig, OpenClawGatewayClient


def start_gateway() -> tuple[str, object, threading.Thread]:
    def handler(websocket: ServerConnection) -> None:
        websocket.send(json.dumps({
            "type": "event",
            "event": "connect.challenge",
            "payload": {"nonce": "n", "ts": int(time.time() * 1000)},
        }))
        connect_frame = json.loads(websocket.recv())
        websocket.send(json.dumps({
            "type": "res",
            "id": connect_frame["id"],
            "ok": True,
            "payload": {
                "type": "hello-ok",
                "protocol": 4,
                "server": {"version": "test", "connId": "c"},
                "features": {"methods": ["agent", "agent.wait", "chat.history", "sessions.abort"], "events": ["agent"]},
                "snapshot": {},
                "auth": {"role": "operator", "scopes": ["operator.read", "operator.write"]},
                "policy": {"maxPayload": 26214400, "maxBufferedBytes": 52428800, "tickIntervalMs": 15000},
            },
        }))

        request = json.loads(websocket.recv())
        payloads = {
            "agent": {"runId": "run-vertical-001", "acceptedAt": 1},
            "agent.wait": {
                "status": "ok",
                "startedAt": 1,
                "endedAt": 2,
                "summary": "integration-ok",
            },
            "chat.history": {
                "sessionKey": "agent:agent-001:orchestrator:task-gateway-001",
                "messages": [
                    {
                        "role": "user",
                        "content": "integration test",
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": "integration-ok",
                            }
                        ],
                        "stopReason": "stop",
                    },
                ],
            },
            "sessions.abort": {"aborted": True},
        }
        websocket.send(json.dumps({
            "type": "res",
            "id": request["id"],
            "ok": True,
            "payload": payloads[request["method"]],
        }))

    server = serve(handler, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"ws://127.0.0.1:{server.socket.getsockname()[1]}", server, thread


def make_task() -> TaskPackage:
    return TaskPackage(
        task_id="task-gateway-001",
        work_unit_id="wu-gateway-001",
        objective="Exercise the real Gateway protocol boundary.",
        configuration=ResourceConfiguration(
            agent="agent-001",
            skills=("tdd",),
            model="provider/model-001",
            provider="provider",
            runtime="openclaw",
        ),
        expected_output=("integration-ok",),
        acceptance_criteria=("status=ok",),
    )


def test_openclaw_gateway_vertical_slice() -> None:
    url, server, thread = start_gateway()
    try:
        client = OpenClawGatewayClient(GatewayConfig(url=url))
        runtime = OpenClawAdapter(client)

        execution = runtime.submit(make_task())
        assert execution.external_id == "gateway:run-vertical-001"
        assert runtime.get_status(execution) is AgentRuntimeStatus.COMPLETED

        result = runtime.retrieve_result(execution)
        assert result.execution.status is AgentRuntimeStatus.COMPLETED
        assert result.raw_result["summary"] == "integration-ok"

        cancelled = runtime.cancel(execution)
        assert cancelled.status is AgentRuntimeStatus.CANCELLED
    finally:
        server.shutdown()
        thread.join(timeout=1)
