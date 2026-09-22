"""Durable, governed controller quiescence for administrative operations.

The liveness heartbeat is an observation channel, not a write lease.  A paused
project with no active executions must be administratively quiescent even if an
older supervisor continues publishing diagnostic heartbeats.  This store is the
authoritative, append-only-ish control-plane fence used by supported commands.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class OrchestrationControlPlaneError(RuntimeError):
    """Raised when a governed control-plane transition is unsafe."""


class FileOrchestrationControlPlane:
    SCHEMA_VERSION = 1

    def __init__(self, *, project_root: Path) -> None:
        self.project_root = project_root.expanduser().resolve()
        if not self.project_root.is_dir():
            raise ValueError("Adaptive project root does not exist or is not a directory.")
        self.root = self.project_root / ".adaptive" / "orchestration-control"

    @staticmethod
    def _digest(orchestration_id: str) -> str:
        value = orchestration_id.strip()
        if not value:
            raise ValueError("orchestration_id must not be empty.")
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def path_for(self, orchestration_id: str) -> Path:
        return self.root / f"{self._digest(orchestration_id)}.json"

    def load(self, orchestration_id: str) -> dict[str, Any] | None:
        path = self.path_for(orchestration_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise OrchestrationControlPlaneError("Control-plane record is unreadable.") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != self.SCHEMA_VERSION
            or payload.get("orchestration_id") != orchestration_id
        ):
            raise OrchestrationControlPlaneError("Control-plane record is invalid.")
        return payload

    def mark_quiescent(
        self,
        *,
        orchestration_id: str,
        checkpoint: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        if checkpoint.get("desired_state") != "PAUSED":
            raise OrchestrationControlPlaneError(
                "Controller quiescence requires desired_state=PAUSED."
            )
        active = checkpoint.get("active_executions")
        if not isinstance(active, list) or active:
            raise OrchestrationControlPlaneError(
                "Controller quiescence requires no active executions."
            )
        existing = self.load(orchestration_id)
        if existing is not None and existing.get("state") == "QUIESCENT":
            return existing
        now = time.time()
        history = list(existing.get("history", [])) if isinstance(existing, dict) else []
        history.append(
            {
                "event": "QUIESCENT",
                "at": now,
                "reason": reason,
                "desired_state": "PAUSED",
                "active_execution_count": 0,
            }
        )
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "orchestration_id": orchestration_id,
            "state": "QUIESCENT",
            "mutation_authority_released": True,
            "desired_state": "PAUSED",
            "active_execution_count": 0,
            "recorded_at": now,
            "reason": reason,
            "history": history,
        }
        self._save(orchestration_id, payload)
        return payload

    def activate(self, *, orchestration_id: str, reason: str) -> dict[str, Any]:
        """Record a governed resume without deleting prior quiescence evidence."""
        existing = self.load(orchestration_id)
        now = time.time()
        history = list(existing.get("history", [])) if isinstance(existing, dict) else []
        history.append({"event": "ACTIVE", "at": now, "reason": reason})
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "orchestration_id": orchestration_id,
            "state": "ACTIVE",
            "mutation_authority_released": False,
            "recorded_at": now,
            "reason": reason,
            "history": history,
        }
        self._save(orchestration_id, payload)
        return payload

    def is_quiescent(self, orchestration_id: str) -> bool:
        payload = self.load(orchestration_id)
        return bool(
            isinstance(payload, dict)
            and payload.get("state") == "QUIESCENT"
            and payload.get("mutation_authority_released") is True
        )

    @contextmanager
    def mutation_lock(self, orchestration_id: str) -> Iterator[None]:
        path = self.root / f"{self._digest(orchestration_id)}.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise OrchestrationControlPlaneError(
                "A governed control-plane operation is already in progress."
            ) from exc
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(str(os.getpid()))
            yield
        finally:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _save(self, orchestration_id: str, payload: dict[str, Any]) -> None:
        path = self.path_for(orchestration_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise OrchestrationControlPlaneError("Unable to persist control-plane state.") from exc
