from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ModelRoutingAuditError(RuntimeError):
    """Raised when the model-routing audit trail cannot be written."""


class ModelRoutingAuditLog:
    """Append-only JSONL audit log for model routing and execution outcomes."""

    _lock = threading.Lock()

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.environ.get("ADAPTIVE_MODEL_ROUTING_LOG")
        self.path = (
            Path(configured).expanduser()
            if configured
            else Path.home()
            / ".local"
            / "state"
            / "adaptive-ai-orchestrator"
            / "model-routing-history.jsonl"
        )

    def append(self, event: dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            *event,
        }
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
                    # The append succeeded. Some filesystems may not support chmod.
                    pass
        except OSError as exc:
            raise ModelRoutingAuditError(
                f"Could not write model-routing audit log at '{self.path}'."
            ) from exc
