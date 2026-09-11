from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domain.provider_incident import ProviderIncident
from application.remediation_policy import RemediationDecision


class ProviderTelemetryError(RuntimeError):
    """Raised when provider incident telemetry cannot be written."""


class ProviderTelemetryStore:
    """Append-only JSONL store for sanitized provider/runtime incidents."""

    _lock = threading.Lock()

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.environ.get("ADAPTIVE_PROVIDER_INCIDENT_LOG")
        self.path = (
            Path(configured).expanduser()
            if configured
            else Path.home()
            / ".local"
            / "state"
            / "adaptive-ai-orchestrator"
            / "provider-incidents.jsonl"
        )

    def append_incident(
        self,
        incident: ProviderIncident,
        remediation: RemediationDecision,
        *,
        task_id: str | None = None,
        work_unit_id: str | None = None,
        runtime_attempt: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "provider-incident",
            "incident": incident.as_payload(),
            "remediation": remediation.as_payload(),
        }
        if task_id:
            payload["task_id"] = task_id
        if work_unit_id:
            payload["work_unit_id"] = work_unit_id
        if runtime_attempt is not None:
            payload["runtime_attempt"] = runtime_attempt
        self._append(payload)

    def append_event(self, event: dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        self._append(payload)

    def _append(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(encoded)
                    handle.write("\n")
                try:
                    self.path.chmod(0o600)
                except OSError:
                    pass
        except OSError as exc:
            raise ProviderTelemetryError(
                f"Could not write provider incident telemetry at '{self.path}'."
            ) from exc
