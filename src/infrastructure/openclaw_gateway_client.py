from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from application.incident_classifier import IncidentClassifier
from application.provider_health_policy import ProviderHealthPolicy
from application.remediation_policy import RemediationPolicy
from infrastructure.openclaw_adapter import OpenClawClient
from infrastructure.provider_telemetry_store import ProviderTelemetryStore

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
    # A Gateway long-poll timeout means "not finished yet", not failure. The
    # client keeps polling until this bounded total is reached.
    agent_result_timeout_seconds: float = 600.0
    # Lifecycle-safe archival is a core Adaptive default. Callers can override
    # it explicitly or set ADAPTIVE_SESSION_AUTO_ARCHIVE=0 for diagnostics.
    archive_completed_sessions: bool | None = None
    archive_cancelled_sessions: bool | None = None
    session_archive_attempts: int = 3
    session_archive_retry_delay_seconds: float = 0.25


@dataclass(frozen=True)
class GatewayRun:
    run_id: str
    session_key: str
    task_payload: dict[str, Any] = field(default_factory=dict)
    runtime_attempt: int = 1


@dataclass(frozen=True)
class SessionArchiveOutcome:
    """Sanitized result of one OpenClaw session archive attempt."""

    status: str
    trigger: str
    error_type: str | None = None

    @property
    def archived(self) -> bool:
        return self.status in {"archived", "already-archived", "missing"}

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "trigger": self.trigger,
            "archived": self.archived,
        }
        if self.error_type:
            payload["error_type"] = self.error_type
        return payload


class OpenClawGatewayClient(OpenClawClient):
    """OpenClaw Gateway client using the documented WebSocket + RPC surface.

    The client intentionally implements only the orchestration-facing methods
    required by the existing ``OpenClawClient`` seam: submit, status, result,
    cancellation, and lifecycle-safe archival. It negotiates Gateway protocol
    v4 and does not expose Gateway SDK types to the application layer.
    """

    RUNTIME_NAME = "openclaw-gateway"

    def __init__(
        self,
        config: GatewayConfig | None = None,
        *,
        incident_classifier: IncidentClassifier | None = None,
        remediation_policy: RemediationPolicy | None = None,
        provider_health_policy: ProviderHealthPolicy | None = None,
        provider_telemetry: ProviderTelemetryStore | None = None,
    ) -> None:
        if _IMPORT_ERROR is not None:
            raise OpenClawGatewayError(
                "The OpenClaw Gateway client requires the 'websockets' package. "
                "Install the gateway optional dependency."
            ) from _IMPORT_ERROR

        self._config = config or GatewayConfig()
        if self._config.session_archive_attempts < 1:
            raise ValueError("session_archive_attempts must be at least 1.")
        if self._config.session_archive_retry_delay_seconds < 0:
            raise ValueError("session_archive_retry_delay_seconds must not be negative.")

        env_auto_archive = self._env_flag(
            "ADAPTIVE_SESSION_AUTO_ARCHIVE",
            default=True,
        )
        self._archive_completed_sessions = (
            env_auto_archive
            if self._config.archive_completed_sessions is None
            else self._config.archive_completed_sessions
        )
        self._archive_cancelled_sessions = (
            env_auto_archive
            if self._config.archive_cancelled_sessions is None
            else self._config.archive_cancelled_sessions
        )
        self._runs: dict[str, GatewayRun] = {}
        self._archive_outcomes: dict[str, SessionArchiveOutcome] = {}
        self._incident_classifier = incident_classifier or IncidentClassifier()
        self._remediation_policy = remediation_policy or RemediationPolicy()
        self._provider_health = provider_health_policy or ProviderHealthPolicy()
        self._provider_telemetry = provider_telemetry or ProviderTelemetryStore()

    def submit(self, task_payload: dict) -> str:
        return self._submit_task(task_payload, runtime_attempt=1)

    def _submit_task(
        self,
        task_payload: dict[str, Any],
        *,
        runtime_attempt: int,
    ) -> str:
        task_id = str(task_payload["task_id"])
        configuration = task_payload["configuration"]
        agent_id = str(configuration["agent"])
        session_key = f"agent:{agent_id}:orchestrator:{task_id}"
        idempotency_key = f"orchestrator:{task_id}"
        if runtime_attempt > 1:
            idempotency_key = f"{idempotency_key}:runtime-fallback:{runtime_attempt}"

        params: dict[str, Any] = {
            "message": self._build_message(task_payload),
            "agentId": agent_id,
            "sessionKey": session_key,
            "deliver": False,
            "timeout": self._config.agent_timeout_seconds,
            "idempotencyKey": idempotency_key,
        }
        model = configuration.get("model")
        provider = configuration.get("provider")
        auth_profile = configuration.get("auth_profile")
        thinking = configuration.get("thinking")
        policy_constraints = tuple(
            str(item)
            for item in (configuration.get("policy_constraints") or ())
        )
        requires_openai_oauth = (
            "adaptive-auth-product:openai-oauth" in policy_constraints
        )
        if requires_openai_oauth and not (
            isinstance(auth_profile, str) and auth_profile.strip()
        ):
            raise OpenClawGatewayError(
                "Adaptive Luna routing requires an explicit OpenAI OAuth auth "
                "profile. Set ADAPTIVE_OPENAI_OAUTH_PROFILE before dispatch."
            )

        if isinstance(thinking, str) and thinking.strip():
            # The Gateway `agent` RPC accepts a turn-level `thinking` value.
            # This keeps adaptive reasoning explicit without elevating this
            # client to operator.admin solely to patch privileged session state.
            params["thinking"] = thinking.strip()

        if model:
            model_ref = str(model)

            if "/" not in model_ref and provider:
                model_ref = f"{provider}/{model_ref}"

            if isinstance(auth_profile, str) and auth_profile.strip():
                model_ref = f"{model_ref}@{auth_profile.strip()}"

            self._rpc(
                "sessions.patch",
                {
                    "key": session_key,
                    "agentId": agent_id,
                    "model": model_ref,
                },
            )

        payload = self._rpc("agent", params)
        run_id = payload.get("runId")
        if not isinstance(run_id, str) or not run_id:
            raise OpenClawGatewayError(
                f"OpenClaw Gateway returned an invalid agent run: {payload!r}"
            )

        external_id = f"gateway:{run_id}"
        self._runs[external_id] = GatewayRun(
            run_id=run_id,
            session_key=session_key,
            task_payload=dict(task_payload),
            runtime_attempt=runtime_attempt,
        )
        return external_id

    def get_status(self, external_id: str) -> str:
        run = self._get_run(external_id)
        result = self._rpc(
            "agent.wait",
            {"runId": run.run_id, "timeoutMs": 0},
        )
        status = self._normalize_wait_status(result.get("status"))

        if status == "TIMEOUT":
            return "RUNNING"

        return status

    def retrieve_result(self, external_id: str) -> object:
        run = self._get_run(external_id)

        try:
            result = self._retrieve_result_for_run(external_id, run)
        except OpenClawGatewayError as exc:
            configuration = run.task_payload.get("configuration")
            if not isinstance(configuration, dict):
                raise
            model = str(configuration.get("model") or "").strip()
            provider = str(
                configuration.get("provider")
                or self._provider_from_model(model)
            ).strip()
            incident = self._incident_classifier.classify(
                exc,
                provider=provider,
                model=model,
            )
            if incident is None:
                raise

            remediation = self._remediation_policy.decide(incident)
            health = self._provider_health.record_failure(
                incident,
                cooldown_seconds=remediation.cooldown_seconds,
            )
            self._record_incident(run, incident, remediation)
            if not remediation.fallback_allowed:
                raise

            reason = incident.failover_reason
            fallback_payload = self._build_failover_payload(run, reason)
            if fallback_payload is None:
                raise

            fallback_external_id = self._submit_task(
                fallback_payload,
                runtime_attempt=run.runtime_attempt + 1,
            )
            fallback_run = self._get_run(fallback_external_id)

            try:
                result = self._retrieve_result_for_run(
                    fallback_external_id,
                    fallback_run,
                )
            except OpenClawGatewayError:
                raise

            fallback_configuration = fallback_payload["configuration"]
            fallback_model = str(fallback_configuration.get("model") or "")
            fallback_provider = str(
                fallback_configuration.get("provider")
                or self._provider_from_model(fallback_model)
            )
            self._provider_health.record_success(
                fallback_provider,
                fallback_model,
            )

            # Keep callers holding the original ExecutionReference on the
            # successful runtime candidate. get_status/cancel continue to work
            # without changing the application-level execution id.
            self._runs[external_id] = fallback_run

            if isinstance(result, dict):
                result = dict(result)
                original_model = str(configuration.get("model") or "")
                result["model_failover"] = {
                    "triggered": True,
                    "reason": reason,
                    "from_model": original_model,
                    "to_model": fallback_configuration.get("model"),
                    "to_provider": fallback_configuration.get("provider"),
                    "runtime_attempt": fallback_run.runtime_attempt,
                    "incident": incident.as_payload(),
                    "remediation": remediation.as_payload(),
                    "circuit_state": health.state,
                }
            return result
        else:
            configuration = run.task_payload.get("configuration")
            if isinstance(configuration, dict):
                model = str(configuration.get("model") or "").strip()
                provider = str(
                    configuration.get("provider")
                    or self._provider_from_model(model)
                ).strip()
                if model:
                    self._provider_health.record_success(provider, model)
            return result

    def _retrieve_result_for_run(
        self,
        external_id: str,
        run: GatewayRun,
    ) -> object:
        result = self._wait_for_result(run.run_id)
        status = self._normalize_wait_status(result.get("status"))

        if status == "TIMEOUT":
            raise OpenClawGatewayError(
                f"OpenClaw agent run '{run.run_id}' is still running."
            )

        if status == "FAILED":
            error = result.get("error") or "OpenClaw agent run failed."
            raise OpenClawGatewayError(str(error))

        history = self._rpc(
            "chat.history",
            {"sessionKey": run.session_key},
        )

        # Capture everything Adaptive needs before changing the OpenClaw session
        # lifecycle. Archive is preservation, not deletion, but history capture
        # remains the explicit safety boundary for automatic cleanup.
        output = self._extract_assistant_text(history)
        metadata = self._extract_assistant_metadata(history)

        lifecycle: dict[str, object] | None = None
        if self._archive_completed_sessions:
            lifecycle = self.archive(
                external_id,
                trigger="result-captured",
            ).as_payload()

        return {
            **result,
            "output": output,
            **metadata,
            **({"session_lifecycle": lifecycle} if lifecycle is not None else {}),
        }

    def _build_failover_payload(
        self,
        run: GatewayRun,
        reason: str | None,
    ) -> dict[str, Any] | None:
        if reason is None or run.runtime_attempt >= 2:
            return None

        configuration = run.task_payload.get("configuration")
        if not isinstance(configuration, dict):
            return None

        current_model = str(configuration.get("model") or "").strip()
        economy_model = os.environ.get(
            "ADAPTIVE_ECONOMY_MODEL",
            "openai/gpt-5.6-luna",
        ).strip()
        strong_model = os.environ.get(
            "ADAPTIVE_STRONG_MODEL",
            "moonshot/kimi-k2.7-code",
        ).strip()
        specialist_model = os.environ.get(
            "ADAPTIVE_CODE_SPECIALIST_MODEL",
            "moonshot/kimi-k2.7-code",
        ).strip()
        disabled_models = {
            item.strip().casefold()
            for item in os.environ.get(
                "ADAPTIVE_DISABLED_MODELS",
                "moonshot/kimi-k3,openai/gpt-5.6-sol",
            ).split(",")
            if item.strip()
        }

        normalized = current_model.casefold()
        if normalized in {
            strong_model.casefold(),
            specialist_model.casefold(),
        }:
            fallback_model = economy_model
        elif normalized == economy_model.casefold():
            # Cost-safe policy: Luna does not automatically escalate to a paid
            # Moonshot route for medium/low-complexity work.
            return None
        else:
            return None

        if (
            not fallback_model
            or fallback_model.casefold() == normalized
            or fallback_model.casefold() in disabled_models
        ):
            return None

        fallback_configuration = dict(configuration)
        fallback_configuration["model"] = fallback_model
        fallback_configuration["provider"] = self._provider_from_model(
            fallback_model
        )
        if fallback_model.casefold() == economy_model.casefold():
            fallback_configuration["auth_profile"] = (
                os.environ.get("ADAPTIVE_OPENAI_OAUTH_PROFILE") or None
            )
        elif fallback_model.casefold() in {
            strong_model.casefold(),
            specialist_model.casefold(),
        }:
            fallback_configuration["auth_profile"] = (
                os.environ.get(
                    "ADAPTIVE_KIMI_AUTH_PROFILE",
                    "moonshot:api-key",
                )
                or None
            )
        if fallback_model.casefold() in {
            "moonshot/kimi-k2.7-code",
            "moonshot/kimi-k2.7-code-highspeed",
        }:
            fallback_configuration["thinking"] = None
        elif fallback_model.casefold() == strong_model.casefold():
            fallback_configuration["thinking"] = os.environ.get(
                "ADAPTIVE_STRONG_THINKING",
                "low",
            )
        else:
            fallback_configuration["thinking"] = os.environ.get(
                "ADAPTIVE_ROUTINE_THINKING",
                "low",
            )
        constraints = list(
            fallback_configuration.get("policy_constraints") or ()
        )
        constraints.extend(
            (
                f"adaptive-operational-failover:{reason}",
                f"adaptive-failover-from:{current_model}",
                f"adaptive-failover-to:{fallback_model}",
            )
        )
        if fallback_model.casefold() == economy_model.casefold():
            constraints.append("adaptive-auth-product:openai-oauth")
        fallback_configuration["policy_constraints"] = constraints

        context = list(run.task_payload.get("context") or ())
        context.append(
            "Adaptive automatic operational failover: the previous model "
            f"failed because of {reason}. Continue in the same worker session. "
            "Inspect the transcript and repository state first; preserve "
            "completed work and side effects, do not blindly repeat completed "
            "actions, and continue idempotently from the interrupted point."
        )

        return {
            **run.task_payload,
            "configuration": fallback_configuration,
            "context": context,
        }

    @staticmethod
    def _classify_failover_error(
        exc: OpenClawGatewayError,
    ) -> str | None:
        """Compatibility wrapper around the structured incident classifier."""
        incident = IncidentClassifier().classify(
            exc,
            provider="unknown",
            model="unknown",
        )
        return incident.failover_reason if incident is not None else None

    def _record_incident(
        self,
        run: GatewayRun,
        incident: object,
        remediation: object,
    ) -> None:
        """Persist sanitized incident evidence without making telemetry fatal."""
        try:
            self._provider_telemetry.append_incident(
                incident,  # type: ignore[arg-type]
                remediation,  # type: ignore[arg-type]
                task_id=str(run.task_payload.get("task_id") or "") or None,
                work_unit_id=str(run.task_payload.get("work_unit_id") or "") or None,
                runtime_attempt=run.runtime_attempt,
            )
        except Exception:
            # Provider telemetry is diagnostic. Execution/audit policy must not
            # become unavailable solely because the auxiliary incident log
            # cannot be written.
            pass

    @staticmethod
    def _provider_from_model(model: str) -> str:
        normalized = model.strip()
        if "/" in normalized:
            return normalized.split("/", 1)[0]
        return "openai"

    def _wait_for_result(self, run_id: str) -> dict[str, Any]:
        """Poll bounded Gateway waits; timeout is an intermediate state."""
        deadline = time.monotonic() + self._config.agent_result_timeout_seconds
        while True:
            remaining = max(0.001, deadline - time.monotonic())
            timeout_ms = min(self._config.agent_wait_timeout_ms, max(1, int(remaining * 1000)))
            result = self._rpc(
                "agent.wait",
                {"runId": run_id, "timeoutMs": timeout_ms},
            )
            if self._normalize_wait_status(result.get("status")) != "TIMEOUT":
                return result
            if self._config.agent_result_timeout_seconds <= 0 or time.monotonic() >= deadline:
                return result

    def cancel(self, external_id: str) -> None:
        run = self._get_run(external_id)
        self._rpc(
            "sessions.abort",
            {"runId": run.run_id, "key": run.session_key},
        )
        if self._archive_cancelled_sessions:
            self.archive(external_id, trigger="cancelled")

    def archive(
        self,
        external_id: str,
        *,
        trigger: str = "explicit",
    ) -> SessionArchiveOutcome:
        """Archive an Adaptive-owned session without making cleanup fatal.

        OpenClaw archive is an in-place lifecycle operation that retains the
        transcript. The observed ``sessionId`` is supplied as
        ``expectedSessionId`` so a stale task key cannot archive a replacement
        generation. Any lifecycle failure leaves the session available for
        inspection and is returned as sanitized metadata instead of failing an
        already-completed Work Unit.
        """
        try:
            status = self._archive_session(external_id)
        except Exception as exc:
            outcome = SessionArchiveOutcome(
                status="failed",
                trigger=trigger,
                error_type=type(exc).__name__,
            )
        else:
            outcome = SessionArchiveOutcome(status=status, trigger=trigger)

        self._archive_outcomes[external_id] = outcome
        return outcome

    def get_archive_outcome(
        self,
        external_id: str,
    ) -> SessionArchiveOutcome | None:
        """Return the last sanitized archive outcome for diagnostics."""
        return self._archive_outcomes.get(external_id)

    def _archive_session(self, external_id: str) -> str:
        run = self._get_run(external_id)
        description = self._rpc(
            "sessions.describe",
            {"key": run.session_key},
        )
        session = description.get("session")
        if session is None:
            # Nothing remains in the active session index, so the cleanup goal
            # is already satisfied without creating or mutating a replacement.
            return "missing"
        if not isinstance(session, dict):
            raise OpenClawGatewayError(
                "OpenClaw sessions.describe returned an invalid session row."
            )
        if session.get("archived") is True:
            return "already-archived"

        session_id = session.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            raise OpenClawGatewayError(
                "OpenClaw sessions.describe returned no durable sessionId."
            )

        # Never allow cleanup of this run to cancel unrelated work that happens
        # to share the key. When exact activity identities are unavailable, the
        # conservative choice is to leave the session visible for inspection.
        active_run_ids = session.get("activeRunIds")
        if isinstance(active_run_ids, list):
            foreign_active = [
                item
                for item in active_run_ids
                if isinstance(item, str) and item and item != run.run_id
            ]
            if foreign_active:
                return "skipped-active"
        elif session.get("hasActiveRun") is True:
            return "skipped-active"

        params = {
            "key": run.session_key,
            "expectedSessionId": session_id,
            "archived": True,
        }
        for attempt in range(self._config.session_archive_attempts):
            try:
                self._rpc("sessions.patch", params)
                return "archived"
            except OpenClawGatewayError as exc:
                is_last = attempt + 1 >= self._config.session_archive_attempts
                if is_last or not self._is_retryable_archive_error(exc):
                    raise
                delay = self._config.session_archive_retry_delay_seconds * (2**attempt)
                if delay > 0:
                    time.sleep(delay)

        raise OpenClawGatewayError("OpenClaw session archive exhausted retries.")

    @staticmethod
    def _is_retryable_archive_error(exc: OpenClawGatewayError) -> bool:
        return "UNAVAILABLE" in str(exc).upper()

    @staticmethod
    def _env_flag(name: str, *, default: bool) -> bool:
        value = os.environ.get(name)
        if value is None:
            return default
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert connect is not None
        request_id = str(uuid.uuid4())
        handshake_deadline = time.monotonic() + self._config.timeout_seconds

        try:
            with connect(
                self._config.url,
                open_timeout=self._config.timeout_seconds,
                close_timeout=self._config.timeout_seconds,
            ) as websocket:
                self._handshake(websocket, handshake_deadline)
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

                response_timeout_seconds = self._config.timeout_seconds
                if method == "agent.wait":
                    timeout_ms = params.get("timeoutMs")
                    if isinstance(timeout_ms, (int, float)) and timeout_ms > 0:
                        response_timeout_seconds += timeout_ms / 1000

                response_deadline = time.monotonic() + response_timeout_seconds
                for frame in self._receive_until_response(
                    websocket,
                    request_id,
                    response_deadline,
                ):
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
                "id": "gateway-client",
                "version": self._config.client_version,
                "platform": self._config.platform,
                "mode": "backend",
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
    def _extract_assistant_text(history: dict[str, Any]) -> str:
        messages = history.get("messages")

        if not isinstance(messages, list):
            raise OpenClawGatewayError(
                "OpenClaw chat.history returned no valid messages."
            )

        for message in reversed(messages):
            if not isinstance(message, dict):
                continue

            if message.get("role") != "assistant":
                continue

            content = message.get("content")

            if not isinstance(content, list):
                continue

            text_parts: list[str] = []

            for block in content:
                if not isinstance(block, dict):
                    continue

                if block.get("type") != "text":
                    continue

                text = block.get("text")
                if isinstance(text, str):
                    text_parts.append(text)

            if text_parts:
                return "".join(text_parts)

        raise OpenClawGatewayError(
            "OpenClaw chat.history contained no assistant text output."
        )

    @staticmethod
    def _extract_assistant_metadata(history: dict[str, Any]) -> dict[str, Any]:
        messages = history.get("messages")
        if not isinstance(messages, list):
            return {}
        for message in reversed(messages):
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            content = message.get("content")
            if not isinstance(content, list) or not any(
                isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
                for block in content
            ):
                continue
            metadata: dict[str, Any] = {}
            for key in ("usage", "token_usage", "cost"):
                value = message.get(key)
                if isinstance(value, dict):
                    metadata[key] = value
            nested = message.get("metadata")
            if isinstance(nested, dict):
                for key in ("usage", "token_usage", "cost"):
                    value = nested.get(key)
                    if isinstance(value, dict):
                        metadata[key] = value
            return metadata
        return {}

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
                "configuration": task_payload["configuration"],
                "expected_output": task_payload["expected_output"],
                "acceptance_criteria": task_payload["acceptance_criteria"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )