from __future__ import annotations

import json
import os
import base64
import hashlib
from pathlib import Path
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError as exc:  # pragma: no cover - packaging validation
    serialization = None  # type: ignore[assignment]
    Ed25519PrivateKey = None  # type: ignore[assignment,misc]
    _CRYPTO_IMPORT_ERROR = exc
else:
    _CRYPTO_IMPORT_ERROR = None

from application.incident_classifier import IncidentClassifier
from application.model_routing_policy import ModelRoutingDecision, ModelRoutingPolicy
from application.provider_health_policy import ProviderHealthPolicy
from application.remediation_policy import RemediationPolicy
from application.worker_protocol import (
    PROTOCOL_COMPLETION_STATE,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    build_worker_protocol,
)
from infrastructure.message_store import FileMessageStore, MessageStoreError
from infrastructure.openclaw_adapter import OpenClawClient
from infrastructure.provider_telemetry_store import ProviderTelemetryStore
from infrastructure.result_store import FileResultStore, ResultStoreError, ResultStoreTarget

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
    device_identity_path: str | None = None
    device_token_path: str | None = None
    run_identity_path: str | None = None


@dataclass(frozen=True)
class GatewayRun:
    run_id: str
    session_key: str
    task_payload: dict[str, Any] = field(default_factory=dict)
    runtime_attempt: int = 1
    result_target: ResultStoreTarget | None = None
    request_message_ref: dict[str, Any] | None = None
    recovered: bool = False


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
        result_store: FileResultStore | None = None,
        message_store: FileMessageStore | None = None,
    ) -> None:
        if _IMPORT_ERROR is not None or _CRYPTO_IMPORT_ERROR is not None:
            raise OpenClawGatewayError(
                "The OpenClaw Gateway client requires the gateway optional "
                "dependencies. Install with 'pip install -e .[gateway]'."
            ) from (_IMPORT_ERROR or _CRYPTO_IMPORT_ERROR)

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
        self._device_identity = self._load_or_create_device_identity()
        self._result_store = result_store or FileResultStore()
        if message_store is not None:
            self._message_store = message_store
        elif self._result_store.project_root is not None:
            self._message_store = FileMessageStore(
                project_root=self._result_store.project_root
            )
        else:
            self._message_store = FileMessageStore(
                root=self._result_store.root / "messages"
            )
        self._run_identity_path = self._resolve_run_identity_path()

    def recover_run(self, external_id: str) -> GatewayRun:
        """Load one persisted execution identity without redispatching work."""
        records: list[dict[str, Any]] = []
        try:
            lines = self._run_identity_path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError as exc:
            raise OpenClawGatewayError(
                f"No persisted execution identity for '{external_id}'."
            ) from exc
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError) as exc:
                raise OpenClawGatewayError(
                    "RUN_ID_RECOVERY_RECORD_INVALID: malformed JSON."
                ) from exc
            if isinstance(record, dict) and record.get("external_id") == external_id:
                records.append(record)
        if not records:
            raise OpenClawGatewayError(
                f"No persisted execution identity for '{external_id}'."
            )
        record = records[-1]
        if record.get("schema_version") != 1:
            raise OpenClawGatewayError("RUN_ID_RECOVERY_RECORD_INVALID: unsupported schema.")
        required = (
            "external_id", "run_id", "session_key", "task_id",
            "orchestration_id", "work_unit_id", "execution_id",
        )
        if any(not isinstance(record.get(key), str) or not record[key] for key in required):
            raise OpenClawGatewayError("RUN_ID_RECOVERY_RECORD_INVALID: incomplete record.")
        target_data = record["result_target"]
        if not isinstance(target_data, dict):
            raise OpenClawGatewayError("RUN_ID_RECOVERY_RECORD_INVALID: missing target.")
        try:
            root = self._result_store.root.resolve()
            target = ResultStoreTarget(
                root=root,
                orchestration_id=record["orchestration_id"],
                work_unit_id=record["work_unit_id"],
                execution_id=record["execution_id"],
                project_root=Path(target_data["project_root"]) if target_data.get("project_root") else None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenClawGatewayError("RUN_ID_RECOVERY_RECORD_INVALID: invalid target.") from exc
        if target.directory.resolve() != Path(str(target_data.get("directory"))).resolve():
            raise OpenClawGatewayError("RUN_ID_RECOVERY_RECORD_INVALID: inconsistent target.")
        try:
            target.directory.resolve().relative_to(root)
        except ValueError as exc:
            raise OpenClawGatewayError("RUN_ID_RECOVERY_RECORD_INVALID: target outside result root.") from exc
        persisted_project = target_data.get("project_root")
        current_project = getattr(self._result_store, "project_root", None)
        if persisted_project and current_project and Path(str(persisted_project)).resolve() != Path(str(current_project)).resolve():
            raise OpenClawGatewayError("RUN_ID_RECOVERY_RECORD_INVALID: project root mismatch.")
        run = GatewayRun(
            run_id=record["run_id"],
            session_key=record["session_key"],
            task_payload={
                "task_id": record["task_id"],
                "orchestration_id": record["orchestration_id"],
                "work_unit_id": record["work_unit_id"],
            },
            runtime_attempt=int(record.get("runtime_attempt", 1)),
            result_target=target,
            request_message_ref=(
                record.get("request_message_ref")
                if isinstance(record.get("request_message_ref"), dict)
                else None
            ),
            recovered=True,
        )
        self._runs[external_id] = run
        return run

    def submit(self, task_payload: dict) -> str:
        return self._submit_task(task_payload, runtime_attempt=1)

    def _submit_task(
        self,
        task_payload: dict[str, Any],
        *,
        runtime_attempt: int,
    ) -> str:
        task_id = str(task_payload["task_id"])
        orchestration_id = str(task_payload.get("orchestration_id") or task_id)
        work_unit_id = str(task_payload["work_unit_id"])
        execution_id = uuid.uuid4().hex
        result_target = self._result_store.prepare_target(
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
        )
        task_payload = self._with_result_store_contract(task_payload, result_target)
        configuration = task_payload["configuration"]
        agent_id = str(configuration["agent"])
        exchange = task_payload.get("message_exchange")
        if not isinstance(exchange, dict):
            exchange = {}
        request_message_type = str(
            exchange.get("request_message_type") or "work.assignment"
        )
        request_schema_name = str(
            exchange.get("request_schema_name") or "task-package"
        )
        request_schema_version = str(exchange.get("schema_version") or "1")
        request_message = self._message_store.publish_json(
            sender="adaptive",
            recipient=f"agent:{agent_id}",
            message_type=request_message_type,
            schema_name=request_schema_name,
            schema_version=request_schema_version,
            correlation_id=orchestration_id,
            payload=task_payload,
        )
        session_key = f"agent:{agent_id}:orchestrator:{task_id}"
        idempotency_key = f"orchestrator:{task_id}"
        if runtime_attempt > 1:
            idempotency_key = f"{idempotency_key}:runtime-fallback:{runtime_attempt}"

        params: dict[str, Any] = {
            "message": self._build_message(request_message.reference),
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
            result_target=result_target,
            request_message_ref=request_message.reference,
        )
        self._persist_run_identity(self._runs[external_id])
        return external_id

    def _resolve_run_identity_path(self) -> Path:
        configured = self._config.run_identity_path or os.environ.get("ADAPTIVE_RUN_IDENTITY_PATH")
        if configured:
            return Path(configured).expanduser()
        state_home = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
        return Path(state_home) / "adaptive-ai-orchestrator" / "runs.jsonl"

    def _persist_run_identity(self, run: GatewayRun) -> None:
        """Persist safe execution identity before the first wait observation."""
        record = {
            "schema_version": 1,
            "external_id": f"gateway:{run.run_id}",
            "run_id": run.run_id,
            "session_key": run.session_key,
            "task_id": str(run.task_payload.get("task_id") or ""),
            "orchestration_id": str(run.task_payload.get("orchestration_id") or ""),
            "work_unit_id": str(run.task_payload.get("work_unit_id") or ""),
            "execution_id": run.result_target.execution_id if run.result_target else None,
            "result_target": run.result_target.as_payload() if run.result_target else None,
            "request_message_ref": run.request_message_ref,
            "runtime_attempt": run.runtime_attempt,
            "recorded_at": time.time(),
        }
        path = self._run_identity_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        try:
            path.chmod(0o600)
        except OSError:
            pass

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
        root_external_id = external_id
        current_external_id = external_id
        failover_history: list[dict[str, object]] = []

        while True:
            run = self._get_run(current_external_id)
            try:
                result = self._retrieve_result_for_run(current_external_id, run)
            except OpenClawGatewayError as exc:
                configuration = run.task_payload.get("configuration")
                if not isinstance(configuration, dict):
                    raise
                model = str(configuration.get("model") or "").strip()
                provider = str(configuration.get("provider") or self._provider_from_model(model)).strip()
                incident = self._incident_classifier.classify(exc, provider=provider, model=model)
                if incident is None:
                    raise
                remediation = self._remediation_policy.decide(incident)
                health = self._provider_health.record_failure(
                    incident, cooldown_seconds=remediation.cooldown_seconds
                )
                self._record_incident(run, incident, remediation)
                if not remediation.fallback_allowed:
                    raise
                payload = self._build_failover_payload(run, incident.failover_reason)
                if payload is None:
                    raise
                next_id = self._submit_task(payload, runtime_attempt=run.runtime_attempt + 1)
                next_run = self._get_run(next_id)
                fc = payload["configuration"]
                failover_history.append({
                    "reason": incident.failover_reason,
                    "from_model": model, "from_provider": provider,
                    "to_model": fc.get("model"), "to_provider": fc.get("provider"),
                    "runtime_attempt": next_run.runtime_attempt,
                    "incident": incident.as_payload(),
                    "remediation": remediation.as_payload(),
                    "circuit_state": health.state,
                })
                self._runs[root_external_id] = next_run
                current_external_id = next_id
                continue

            configuration = run.task_payload.get("configuration")
            if isinstance(configuration, dict):
                model = str(configuration.get("model") or "").strip()
                provider = str(configuration.get("provider") or self._provider_from_model(model)).strip()
                if model:
                    self._provider_health.record_success(provider, model)
            self._runs[root_external_id] = run
            if failover_history and isinstance(result, dict):
                result = dict(result)
                summary = dict(failover_history[-1])
                summary["triggered"] = True
                summary["from_model"] = failover_history[0]["from_model"]
                summary["from_provider"] = failover_history[0]["from_provider"]
                summary["attempts"] = len(failover_history)
                summary["history"] = list(failover_history)
                result["model_failover"] = summary
            return result


    def _retrieve_result_for_run(
        self,
        external_id: str,
        run: GatewayRun,
    ) -> object:
        # The worker protocol makes the atomic publication of final result.txt
        # an authoritative completion signal. A controller may disappear after
        # that rename while OpenClaw still reports the run as RUNNING. Reconcile
        # the exact persisted target first so recovery never waits forever for a
        # stale Gateway lifecycle state.
        stored = (
            self._reconcile_persisted_worker_result(run)
            if run.recovered
            else None
        )
        if stored is not None:
            result = {
                "status": "ok",
                "reconciled": True,
                "reconciliation_phase": "resume",
                "stopReason": "adaptive-result-store",
            }
        else:
            try:
                result = self._wait_for_result(run.run_id)
            except OpenClawGatewayError:
                # A transport/RPC failure can arrive after the worker has already
                # atomically published its authoritative result. Reconcile the
                # exact assigned target before classifying the observation as a
                # runtime failure or allowing provider failover.
                stored = self._reconcile_persisted_worker_result(run)
                if stored is None:
                    raise
                result = {
                    "status": "ok",
                    "reconciled": True,
                    "reconciliation_phase": "gateway_error",
                    "stopReason": "adaptive-result-store",
                }
            else:
                status = self._normalize_wait_status(result.get("status"))

                if status in {"TIMEOUT", "FAILED"}:
                    # agent.wait is an observation boundary, not authoritative
                    # semantic completion. A final result published just before
                    # timeout/error must win after identity/integrity validation.
                    stored = self._reconcile_persisted_worker_result(run)
                    if stored is not None:
                        result = {
                            "status": "ok",
                            "reconciled": True,
                            "reconciliation_phase": (
                                "timeout" if status == "TIMEOUT" else "gateway_error"
                            ),
                            "stopReason": "adaptive-result-store",
                        }
                    elif status == "TIMEOUT":
                        raise OpenClawGatewayError(
                            f"OpenClaw agent run '{run.run_id}' is still running."
                        )
                    else:
                        error = result.get("error") or "OpenClaw agent run failed."
                        raise OpenClawGatewayError(str(error))

        output: str
        metadata: dict[str, Any] = {}
        result_transport: dict[str, object]
        protocol_error: str | None = None

        protocol = run.task_payload.get("worker_protocol")
        if not isinstance(protocol, dict) and run.result_target is not None:
            protocol = build_worker_protocol(
                orchestration_id=run.result_target.orchestration_id,
                work_unit_id=run.result_target.work_unit_id,
                execution_id=run.result_target.execution_id,
                result_store=run.result_target.as_payload(),
            )

        if stored is None and run.result_target is not None:
            try:
                # Every terminal path uses the same idempotent reconciliation
                # seam. Existing manifests are verified rather than overwritten;
                # a final result.txt without a manifest is finalized by Adaptive.
                stored = self._result_store.reconcile_worker_result(run.result_target)
            except ResultStoreError as exc:
                protocol_error = str(exc)

        if stored is not None:
            exchange = run.task_payload.get("message_exchange")
            if not isinstance(exchange, dict):
                exchange = {}
            configuration = run.task_payload.get("configuration")
            agent_id = (
                str(configuration.get("agent") or "worker")
                if isinstance(configuration, dict)
                else "worker"
            )
            reply_to = None
            if isinstance(run.request_message_ref, dict):
                candidate = run.request_message_ref.get("message_id")
                if isinstance(candidate, str) and candidate:
                    reply_to = candidate
            try:
                exchanged = self._message_store.publish_text(
                    sender=f"agent:{agent_id}",
                    recipient="adaptive",
                    message_type=str(
                        exchange.get("result_message_type") or "worker.result"
                    ),
                    schema_name=str(
                        exchange.get("result_schema_name") or "worker-result"
                    ),
                    schema_version=str(exchange.get("schema_version") or "1"),
                    content_type=str(
                        exchange.get("result_content_type") or "text/plain"
                    ),
                    correlation_id=(
                        run.result_target.orchestration_id
                        if run.result_target is not None
                        else str(run.task_payload.get("orchestration_id") or "runtime")
                    ),
                    reply_to=reply_to,
                    content=stored.content,
                )
            except MessageStoreError as exc:
                raise OpenClawGatewayError(
                    f"AMEP result publication failed: {exc}"
                ) from exc

            # Read through the AMEP reference before exposing the result upward.
            # This makes manifest/payload verification part of the runtime boundary.
            exchanged = self._message_store.read_reference(exchanged.reference)
            output = exchanged.content
            result_transport = {
                "source": "adaptive-result-store+amep",
                "authoritative": True,
                "result_ref": str(run.result_target.manifest_path),
                "result_sha256": stored.sha256,
                "result_bytes": stored.byte_length,
                "message_ref": exchanged.reference,
                "message_manifest": exchanged.reference["manifest"],
                "message_sha256": exchanged.sha256,
                "message_bytes": exchanged.byte_length,
                "complete": True,
                "completion_state": PROTOCOL_COMPLETION_STATE,
                **(
                    {"reconciliation_phase": result["reconciliation_phase"]}
                    if isinstance(result.get("reconciliation_phase"), str)
                    else {}
                ),
            }
        else:
            history = self._rpc(
                "chat.history",
                {"sessionKey": run.session_key},
            )

            # Human/progress fallback remains available only as diagnostics.
            # Adaptive application-layer semantics reject it for mandatory
            # protocol executions because it is not authoritative.
            output = self._extract_assistant_text(history)
            metadata = self._extract_assistant_metadata(history)
            result_transport = {
                "source": "chat-history-fallback",
                "authoritative": False,
                "complete": False,
                "completion_state": "RESULT_UNVERIFIED",
                **(
                    {"protocol_error": protocol_error}
                    if protocol_error is not None
                    else {}
                ),
            }

        protocol_result: dict[str, object] = {
            "name": PROTOCOL_NAME,
            "version": PROTOCOL_VERSION,
            "required": True,
            "completion_state": (
                PROTOCOL_COMPLETION_STATE
                if stored is not None
                else "RESULT_UNVERIFIED"
            ),
        }
        if isinstance(protocol, dict):
            digest = protocol.get("contract_sha256")
            if isinstance(digest, str):
                protocol_result["contract_sha256"] = digest

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
            "result_transport": result_transport,
            "worker_protocol": protocol_result,
            **({"session_lifecycle": lifecycle} if lifecycle is not None else {}),
        }

    def _reconcile_persisted_worker_result(
        self,
        run: GatewayRun,
    ):
        target = run.result_target
        if target is None:
            return None
        if not target.result_path.exists() and not target.manifest_path.exists():
            return None
        try:
            return self._result_store.reconcile_worker_result(target)
        except ResultStoreError as exc:
            raise OpenClawGatewayError(
                "PERSISTED_RESULT_RECONCILIATION_FAILED: "
                f"{exc}"
            ) from exc

    def _build_failover_payload(
        self,
        run: GatewayRun,
        reason: str | None,
    ) -> dict[str, Any] | None:
        if reason is None:
            return None
        configuration = run.task_payload.get("configuration")
        if not isinstance(configuration, dict):
            return None
        current_model = str(configuration.get("model") or "").strip()
        provider = str(configuration.get("provider") or self._provider_from_model(current_model)).strip()
        auth = configuration.get("auth_profile")
        auth = auth if isinstance(auth, str) else None
        thinking = configuration.get("thinking")
        thinking = thinking if isinstance(thinking, str) else None
        policy = ModelRoutingPolicy.from_env()
        current = ModelRoutingDecision(
            model=current_model, provider=provider, auth_profile=auth, tier="runtime-current",
            reason="runtime-current", attempt=run.runtime_attempt, thinking=thinking,
            thinking_reason="runtime-current",
        )
        fallback = policy.fallback_for(current, failure_reason=reason)
        if fallback is None:
            return None

        fc = dict(configuration)
        fc["model"] = fallback.model
        fc["provider"] = fallback.provider
        fc["auth_profile"] = fallback.auth_profile
        fc["thinking"] = fallback.thinking
        prefixes = (
            "adaptive-operational-failover:", "adaptive-failover-from:",
            "adaptive-failover-to:", "adaptive-model-tier:",
            "adaptive-thinking-level:", "adaptive-thinking-routing-reason:",
            "adaptive-auth-product:",
        )
        constraints=[str(x) for x in (fc.get("policy_constraints") or ()) if not str(x).startswith(prefixes)]
        constraints += [
            f"adaptive-operational-failover:{reason}",
            f"adaptive-failover-from:{current_model}",
            f"adaptive-failover-to:{fallback.model}",
            "adaptive-model-tier:fallback",
            (f"adaptive-thinking-level:{fallback.thinking}" if fallback.thinking is not None else "adaptive-thinking-level:provider-native"),
            ("adaptive-auth-product:openai-oauth" if fallback.provider == "openai" and fallback.model == policy.economy_model else "adaptive-auth-product:provider-default"),
        ]
        fc["policy_constraints"] = constraints
        context=list(run.task_payload.get("context") or ())
        context.append(
            "Adaptive automatic operational failover: the previous model failed because "
            f"of {reason}. Continue in the same worker session. Inspect transcript and "
            "repository state first; preserve completed work and continue idempotently."
        )
        return {**run.task_payload, "configuration": fc, "context": context}


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

    def _with_result_store_contract(
        self,
        task_payload: dict[str, Any],
        target: ResultStoreTarget,
    ) -> dict[str, Any]:
        payload = dict(task_payload)
        result_store_payload = target.as_payload()
        protocol = build_worker_protocol(
            orchestration_id=target.orchestration_id,
            work_unit_id=target.work_unit_id,
            execution_id=target.execution_id,
            result_store=result_store_payload,
        )
        constraints = list(payload.get("constraints") or ())
        constraints.append(self._result_store.worker_instructions(target))
        payload["worker_protocol"] = protocol
        payload["constraints"] = constraints
        payload["result_store"] = result_store_payload
        return payload

    @staticmethod
    def _provider_from_model(model: str) -> str:
        normalized = model.strip()
        if "/" in normalized:
            return normalized.split("/", 1)[0]
        return "openai"

    def _wait_for_result(self, run_id: str) -> dict[str, Any]:
        """Poll bounded Gateway waits and reconcile worker publication on timeout.

        A normal fast terminal Gateway response remains the preferred lifecycle
        signal. When Gateway keeps returning the intermediate TIMEOUT state,
        Adaptive checks whether the exact worker Result Store target has been
        atomically published. That prevents a healthy completed worker from
        being held behind a stale RUNNING lifecycle while preserving the normal
        Gateway path when it is functioning.

        The call shape intentionally remains one run_id argument because
        lifecycle tests and adapters replace this seam. The matching GatewayRun
        is recovered from the client's in-memory registry.
        """
        run = next(
            (
                candidate
                for candidate in self._runs.values()
                if candidate.run_id == run_id
            ),
            None,
        )
        deadline = time.monotonic() + self._config.agent_result_timeout_seconds
        while True:
            remaining = max(0.001, deadline - time.monotonic())
            timeout_ms = min(
                self._config.agent_wait_timeout_ms,
                max(1, int(remaining * 1000)),
            )
            if run is not None and run.result_target is not None:
                # Re-check the authoritative worker publication frequently
                # without imposing a phase deadline on useful worker progress.
                timeout_ms = min(timeout_ms, 5000)
            result = self._rpc(
                "agent.wait",
                {"runId": run_id, "timeoutMs": timeout_ms},
            )
            if self._normalize_wait_status(result.get("status")) != "TIMEOUT":
                return result
            if (
                run is not None
                and run.result_target is not None
                and run.result_target.result_path.exists()
            ):
                return {
                    "status": "ok",
                    "reconciled": True,
                    "stopReason": "adaptive-result-store",
                }
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

        nonce = str((challenge.get("payload") or {}).get("nonce") or "").strip()
        challenge_ts = (challenge.get("payload") or {}).get("ts")
        if not nonce or not isinstance(challenge_ts, int):
            raise OpenClawGatewayError("OpenClaw challenge missing nonce or timestamp.")
        scopes = ["operator.read", "operator.write"]
        signed_at = challenge_ts
        device_token = self._load_device_token()
        token = self._config.token or self._config.password or device_token
        platform = self._config.platform.strip().lower()
        payload = "|".join((
            "v3", self._device_identity["device_id"], "gateway-client", "backend",
            "operator", ",".join(scopes), str(signed_at), token or "", nonce, platform, "",
        ))
        signature = self._sign_device_payload(payload)
        params: dict[str, Any] = {
            "minProtocol": self._config.protocol_version,
            "maxProtocol": self._config.protocol_version,
            "client": {
                "id": "gateway-client",
                "version": self._config.client_version,
                "platform": platform,
                "mode": "backend",
            },
            "role": "operator",
            "scopes": scopes,
            "caps": [],
            "commands": [],
            "permissions": {},
            "locale": "en-US",
            "userAgent": "adaptive-ai-orchestrator",
            "device": {
                "id": self._device_identity["device_id"],
                "publicKey": self._device_identity["public_key_raw"],
                "signature": signature,
                "signedAt": signed_at,
                "nonce": nonce,
            },
        }
        auth: dict[str, str] = {}
        if self._config.token:
            auth["token"] = self._config.token
        elif self._config.password:
            auth["password"] = self._config.password
        elif device_token:
            auth["deviceToken"] = device_token
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
        auth_info = hello.get("auth")
        if isinstance(auth_info, dict) and isinstance(auth_info.get("deviceToken"), str):
            self._persist_device_token(auth_info["deviceToken"])

    def _load_or_create_device_identity(self) -> dict[str, str]:
        path = Path(self._config.device_identity_path or (
            Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
            / "adaptive-ai-orchestrator" / "device-identity.json"
        ))
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or not all(isinstance(data.get(k), str) and data[k] for k in ("private_key", "public_key", "device_id")):
                raise OpenClawGatewayError("Invalid device identity record.")
            key = serialization.load_pem_private_key(data["private_key"].encode(), password=None)
            raw_public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            expected_id = hashlib.sha256(raw_public).hexdigest()
            if data["device_id"] != expected_id:
                raise OpenClawGatewayError("Device identity public key does not match device_id.")
            derived_raw = base64.urlsafe_b64encode(raw_public).rstrip(b"=").decode()
            if data.get("public_key_raw") != derived_raw:
                data["public_key_raw"] = derived_raw
                temporary = path.with_suffix(path.suffix + ".tmp")
                temporary.write_text(json.dumps(data, separators=(",", ":")))
                temporary.chmod(0o600)
                temporary.replace(path)
            return data
        except OpenClawGatewayError:
            raise
        except (OSError, ValueError, TypeError) as exc:
            if path.exists():
                raise OpenClawGatewayError("Invalid device identity record.") from exc
        private = Ed25519PrivateKey.generate()
        private_pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        public_pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        raw_public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        data = {"private_key": private_pem, "public_key": public_pem, "public_key_raw": base64.urlsafe_b64encode(raw_public).rstrip(b"=").decode(), "device_id": hashlib.sha256(raw_public).hexdigest()}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, separators=(",", ":")))
        path.chmod(0o600)
        return data

    def _sign_device_payload(self, payload: str) -> str:
        key = serialization.load_pem_private_key(self._device_identity["private_key"].encode(), password=None)
        return base64.urlsafe_b64encode(key.sign(payload.encode())).rstrip(b"=").decode()

    def _load_device_token(self) -> str | None:
        path = Path(self._config.device_token_path or (Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "adaptive-ai-orchestrator" / "device-token.json"))
        try:
            value = json.loads(path.read_text()).get("token")
        except (OSError, ValueError):
            return None
        return value if isinstance(value, str) and value else None

    def _persist_device_token(self, token: str) -> None:
        path = Path(self._config.device_token_path or (Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "adaptive-ai-orchestrator" / "device-token.json"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"token": token}, separators=(",", ":")))
        path.chmod(0o600)

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
        # AMEP v1 uses chat/runtime as a control plane only. New executions carry
        # a compact reference; the full task package lives in the Message Store.
        if task_payload.get("type") == "adaptive.message.ref":
            return FileMessageStore.reference_message(task_payload)

        # Legacy/test compatibility for callers that still provide an inline
        # task payload directly. Runtime dispatch no longer uses this path.
        message = {
            "worker_protocol": task_payload["worker_protocol"],
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
            "result_store": task_payload.get("result_store"),
        }
        return json.dumps(
            message,
            ensure_ascii=False,
            separators=(",", ":"),
        )
