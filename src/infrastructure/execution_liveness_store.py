from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from application.execution_liveness import (
    ExecutionLiveness,
    ExecutionLivenessState,
    ExecutionLivenessStore,
)


class ExecutionLivenessStoreError(RuntimeError):
    """Raised when a durable liveness record is invalid or cannot be persisted."""


class FileExecutionLivenessStore(ExecutionLivenessStore):
    SCHEMA_VERSION = 1

    def __init__(self, *, project_root: Path) -> None:
        project_root = project_root.expanduser().resolve()
        if not project_root.is_dir():
            raise ValueError(
                f"Adaptive project root does not exist or is not a directory: {project_root}"
            )
        self.project_root = project_root
        self.root = project_root / ".adaptive" / "liveness"

    def read(self, external_id: str) -> ExecutionLiveness | None:
        path = self.path_for(external_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise ExecutionLivenessStoreError(
                "Execution liveness record is unreadable."
            ) from exc
        if not isinstance(payload, dict):
            raise ExecutionLivenessStoreError(
                "Execution liveness record must be a JSON object."
            )
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ExecutionLivenessStoreError(
                "Execution liveness record has an unsupported schema."
            )
        if payload.get("external_id") != external_id:
            raise ExecutionLivenessStoreError(
                "Execution liveness identity does not match the requested execution."
            )
        try:
            state = ExecutionLivenessState(str(payload["state"]))
            snapshot = ExecutionLiveness(
                external_id=str(payload["external_id"]),
                execution_id=str(payload["execution_id"]),
                runtime=str(payload["runtime"]),
                state=state,
                heartbeat_sequence=int(payload["heartbeat_sequence"]),
                started_at=float(payload["started_at"]),
                last_heartbeat_at=float(payload["last_heartbeat_at"]),
                last_progress_at=float(payload["last_progress_at"]),
                source=str(payload["source"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExecutionLivenessStoreError(
                "Execution liveness record is incomplete."
            ) from exc
        if snapshot.heartbeat_sequence < 0:
            raise ExecutionLivenessStoreError(
                "Execution liveness sequence must not be negative."
            )
        return snapshot

    def write(self, snapshot: ExecutionLiveness) -> None:
        path = self.path_for(snapshot.external_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "external_id": snapshot.external_id,
            "execution_id": snapshot.execution_id,
            "runtime": snapshot.runtime,
            "state": snapshot.state.value,
            "heartbeat_sequence": snapshot.heartbeat_sequence,
            "started_at": snapshot.started_at,
            "last_heartbeat_at": snapshot.last_heartbeat_at,
            "last_progress_at": snapshot.last_progress_at,
            "source": snapshot.source,
        }
        temp = path.with_name(f".{path.name}.tmp")
        try:
            temp.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            try:
                temp.chmod(0o600)
            except OSError:
                pass
            os.replace(temp, path)
            try:
                path.chmod(0o600)
            except OSError:
                pass
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ExecutionLivenessStoreError(
                "Unable to persist execution liveness."
            ) from exc

    def path_for(self, external_id: str) -> Path:
        if not external_id.strip():
            raise ValueError("external_id must not be empty.")
        digest = hashlib.sha256(external_id.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"
