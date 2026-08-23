from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from infrastructure.openclaw_adapter import OpenClawClient

try:
    from websockets.sync.client import ClientConnection, connect
except ImportError as exc:  # pragma: no cover - exercised by packaging/runtime validation
    ClientConnection = Any  # type: ignore[assignment,misc]
    connect = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class OpenClawGatewayError(RuntimeError):
    """Raised when the OpenClaw Gateway protocol cannot fulfill a request."""


@dataclass(frozen=True)
class GatewayConfig:
    url: str = "ws://127.0.0.1:18789"
    token: str | None = None
    password: str | None = None
    protocol_version: int = 4
    client_version: str = "0.2.0"
    platform: str = "linux"
    timeout_seconds: float = 30.0
    agent_timeout_seconds: int = 600
    agent_wait_timeout_ms: int = 30_000


@dataclass(frozen=True)
class GatewayRun:
    run_id: str
    session_key: str


class OpenClawGatewayClient(OpenClawClient):
    """OpenClaw Gateway client using the documented WebSocket + RPC surface.

    The client intentionally implements only the orchestration-facing methods
    required by the existing ``OpenClawClient`` seam: submit, status, result,
    and cancel. It negotiates Gateway protocol v4 and does not expose Gateway
    SDK types to the application layer.
    """

    RUNTIME_NAME = "openclaw-gateway"

    def __init__(self, config: GatewayConfig | None = None) -> None:
        if _IMPORT_ERROR is not None:
            raise OpenClawGatewayError(
                "The OpenClaw Gateway client requires the 'websockets' package. "
                "Install the gateway optional dependency."
            ) from _IMPORT_ERROR

        self._config = config or GatewayConfig()
        self._runs: dict[str, GatewayRun] = {}

    def submit(self, task_payload: dict) -> str:
        task_id = str(task_payload["task_id"])
        configuration = task_payload["configuration"]
        session_key = f"orchestrator:{task_id}"

        params: dict[str, Any] = {
            "message": self._build_message(task_payload),
            "agentId": str(configuration["agent"]),
            "sessionKey": session_key,
            "deliver": False,
            "timeout": self._config.agent_timeout_seconds,
            "idempotencyKey": f"orchestrator:{task_id}",
        }
        model = configuration.get("model")
        provider = configuration.get("provider")
        if model:
            params["model"] = str(model)
        if provider:
            params["provider"] = str(provider)

        payload = self._rpc("agent", params)
        run_id = payload.get("runId")
        if not isinstance(run_id, str) or not run_id:
            raise OpenClawGatewayError(
                f"OpenClaw Gateway returned an invalid agent run: {payload!r}"
            )

        external_id = f"gateway:{run_id}"
        self._runs[external_id] = GatewayRun(run_id=run_id, session_key=session_key)
        return external_id

    def get_status(self, external_id: str) -> str:
        run = self._get_run(external_id)
        result = self._rpc(
            "agent.wait",
            {"runId": run.run_id, "timeoutMs": 0},
        )
        return self._normalize_wait_status(result.get("status"))

    def retrieve_result(self, external_id: str) -> object:
        run = self._get_run(external_id)
        result = self._rpc(
            "agent.wait",
            {
                "runId": run.run_id,
                "timeoutMs": self._config.agent_wait_timeout_ms,
            },
        )
        status = self._normalize_wait_status(result.get("status"))
        if status == "TIMEOUT":
            raise OpenClawGatewayError(
                f"OpenClaw agent run '{run.run_id}' is still running."
            )
        if status == "FAILED":
            error = result.get("error") or "OpenClaw agent run failed."
            raise OpenClawGatewayError(str(error))
        return result

    def cancel(self, external_id: str) -> None:
        run = self._get_run(external_id)
        self._rpc(
            "sessions.abort",
            {"runId": run.run_id, "key": run.session_key},
        )

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert connect is not None
        request_id = str(uuid.uuid4())
        deadline = time.monotonic() + self._config.timeout_seconds

        try:
            with connect(
                self._config.url,
                open_timeout=self._config.timeout_seconds,
                close_timeout=self._config.timeout_seconds,
            ) as websocket:
                self._handshake(websocket, deadline)
                websocket.send(
                    json.dumps(
                        {
                            "type": "req",
                            "id": request_id,
                            "method": method,
                            "params": params,
                        },
                        separators=(",", ":"),
                    )
                )
                for frame in self._receive_until_response(websocket, request_id, deadline):
                    if frame.get("ok") is True:
                        payload = frame.get("payload")
                        if not isinstance(payload, dict):
                            raise OpenClawGatewayError(
                                f"OpenClaw Gateway returned invalid payload for {method!r}."
                            )
                        return payload

                    error = frame.get("error")
                    raise OpenClawGatewayError(
                        self._format_rpc_error(method, error)
                    )
        except OpenClawGatewayError:
            raise
        except Exception as exc:  # websockets exceptions vary by version
            raise OpenClawGatewayError(
                f"OpenClaw Gateway request {method!r} failed: {exc}"
            ) from exc

        raise OpenClawGatewayError(
            f"OpenClaw Gateway request {method!r} timed out."
        )

    def _handshake(self, websocket: ClientConnection, deadline: float) -> None:
        challenge = self._receive_json(websocket, deadline)
        if challenge.get("type") != "event" or challenge.get("event") != "connect.challenge":
            raise OpenClawGatewayError(
                f"Expected connect.challenge, received {challenge!r}"
            )

        params: dict[str, Any] = {
            "minProtocol": self._config.protocol_version,
            "maxProtocol": self._config.protocol_version,
            "client": {
                "id": "adaptive-ai-orchestrator",
                "version": self._config.client_version,
                "platform": self._config.platform,
                "mode": "operator",
            },
            "role": "operator",
            "scopes": ["operator.read", "operator.write"],
            "caps": [],
            "commands": [],
            "permissions": {},
            "locale": "en-US",
            "userAgent": "adaptive-ai-orchestrator",
        }
        auth: dict[str, str] = {}
        if self._config.token:
            auth["token"] = self._config.token
        if self._config.password:
            auth["password"] = self._config.password
        if auth:
            params["auth"] = auth

        request_id = str(uuid.uuid4())
        websocket.send(
            json.dumps(
                {
                    "type": "req",
                    "id": request_id,
                    "method": "connect",
                    "params": params,
                },
                separators=(",", ":"),
            )
        )
        response = self._receive_json(websocket, deadline)
        if response.get("type") != "res" or response.get("id") != request_id:
            raise OpenClawGatewayError(
                f"Invalid connect response: {response!r}"
            )
        if response.get("ok") is not True:
            raise OpenClawGatewayError(
                self._format_rpc_error("connect", response.get("error"))
            )

        hello = response.get("payload")
        if not isinstance(hello, dict) or hello.get("type") != "hello-ok":
            raise OpenClawGatewayError(
                f"Invalid hello-ok payload: {hello!r}"
            )
        protocol = hello.get("protocol")
        if protocol != self._config.protocol_version:
            raise OpenClawGatewayError(
                f"Unsupported OpenClaw Gateway protocol {protocol!r}; "
                f"expected {self._config.protocol_version}."
            )

    @staticmethod
    def _receive_until_response(
        websocket: ClientConnection,
        request_id: str,
        deadline: float,
    ) -> Iterator[dict[str, Any]]:
        while time.monotonic() < deadline:
            frame = OpenClawGatewayClient._receive_json(websocket, deadline)
            if frame.get("type") == "event":
                continue
            if frame.get("type") != "res" or frame.get("id") != request_id:
                continue
            yield frame
            return

    @staticmethod
    def _receive_json(websocket: ClientConnection, deadline: float) -> dict[str, Any]:
        remaining = max(0.001, deadline - time.monotonic())
        try:
            raw = websocket.recv(timeout=remaining)
        except TimeoutError as exc:
            raise OpenClawGatewayError("OpenClaw Gateway receive timed out.") from exc

        if not isinstance(raw, str):
            raise OpenClawGatewayError("OpenClaw Gateway returned a non-text frame.")
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenClawGatewayError("OpenClaw Gateway returned invalid JSON.") from exc
        if not isinstance(decoded, dict):
            raise OpenClawGatewayError("OpenClaw Gateway returned a non-object frame.")
        return decoded

    @staticmethod
    def _normalize_wait_status(status: object) -> str:
        if status == "ok":
            return "COMPLETED"
        if status == "error":
            return "FAILED"
        if status == "timeout":
            return "TIMEOUT"
        raise OpenClawGatewayError(
            f"Unsupported OpenClaw agent.wait status: {status!r}"
        )

    @staticmethod
    def _format_rpc_error(method: str, error: object) -> str:
        return f"OpenClaw Gateway RPC {method!r} failed: {error!r}"

    def _get_run(self, external_id: str) -> GatewayRun:
        try:
            return self._runs[external_id]
        except KeyError as exc:
            raise OpenClawGatewayError(
                f"Unknown OpenClaw Gateway execution '{external_id}'."
            ) from exc

    @staticmethod
    def _build_message(task_payload: dict[str, Any]) -> str:
        return json.dumps(
            {
                "task_id": task_payload["task_id"],
                "work_unit_id": task_payload["work_unit_id"],
                "objective": task_payload["objective"],
                "scope": task_payload["scope"],
                "context": task_payload["context"],
                "inputs": task_payload["inputs"],
                "artifacts": task_payload["artifacts"],
                "decisions": task_payload["decisions"],
                "dependencies": task_payload["dependencies"],
                "constraints": task_payload["constraints"],
                "expected_output": task_payload["expected_output"],
                "acceptance_criteria": task_payload["acceptance_criteria"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
