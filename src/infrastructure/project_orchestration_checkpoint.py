from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


class ProjectOrchestrationCheckpointError(RuntimeError):
    """Raised when a project-orchestration checkpoint is invalid or unreadable."""


class FileProjectOrchestrationCheckpointStore:
    """Project-local, atomic checkpoint storage for runtime recovery.

    This is operational state, not the richer continuity/reporting artifact
    tracked separately by issue #46.
    """

    SCHEMA_VERSION = 1

    def __init__(self, *, project_root: Path) -> None:
        root = project_root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(
                f"Adaptive project root does not exist or is not a directory: {root}"
            )
        self.project_root = root
        self.root = root / ".adaptive" / "orchestrations"

    def path_for(self, orchestration_id: str) -> Path:
        value = orchestration_id.strip()
        if not value:
            raise ValueError("orchestration_id must not be empty.")
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def load(self, orchestration_id: str) -> dict[str, Any] | None:
        path = self.path_for(orchestration_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise ProjectOrchestrationCheckpointError(
                "Project orchestration checkpoint is unreadable."
            ) from exc

        if not isinstance(payload, dict):
            raise ProjectOrchestrationCheckpointError(
                "Project orchestration checkpoint must be a JSON object."
            )
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ProjectOrchestrationCheckpointError(
                "Project orchestration checkpoint has an unsupported schema."
            )
        if payload.get("orchestration_id") != orchestration_id:
            raise ProjectOrchestrationCheckpointError(
                "Project orchestration checkpoint identity mismatch."
            )
        state = payload.get("state")
        if not isinstance(state, dict):
            raise ProjectOrchestrationCheckpointError(
                "Project orchestration checkpoint is missing state."
            )
        return state

    def list_all(self) -> tuple[tuple[str, dict[str, Any]], ...]:
        """Return readable checkpoint states with their authoritative ids."""
        if not self.root.is_dir():
            return ()
        items: list[tuple[str, dict[str, Any]]] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
            if not isinstance(payload, dict):
                continue
            orchestration_id = payload.get("orchestration_id")
            state = payload.get("state")
            if (
                payload.get("schema_version") != self.SCHEMA_VERSION
                or not isinstance(orchestration_id, str)
                or not orchestration_id.strip()
                or not isinstance(state, dict)
            ):
                continue
            if self.path_for(orchestration_id) != path:
                continue
            items.append((orchestration_id, state))
        return tuple(items)

    def save(self, orchestration_id: str, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise TypeError("Project orchestration checkpoint payload must be an object.")
        path = self.path_for(orchestration_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "schema_version": self.SCHEMA_VERSION,
            "orchestration_id": orchestration_id,
            "state": payload,
        }
        temporary = path.with_name(f".{path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(
                    envelope,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            try:
                temporary.chmod(0o600)
            except OSError:
                pass
            os.replace(temporary, path)
            try:
                path.chmod(0o600)
            except OSError:
                pass
        except (OSError, TypeError, ValueError) as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise ProjectOrchestrationCheckpointError(
                "Unable to persist project orchestration checkpoint."
            ) from exc
