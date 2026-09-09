from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from datetime import datetime, timezone
from uuid import uuid4


class ObservabilitySink(Protocol):
    def emit(self, event_type: str, **fields: Any) -> None: ...


class NullObservabilitySink:
    def emit(self, event_type: str, **fields: Any) -> None:
        return None


class JsonlObservabilitySink:
    """Append-only, allowlisted operational events; never stores raw payloads."""

    _fields = {
        "event_id", "timestamp", "orchestration_id", "work_unit_id",
        "execution_id", "external_id", "role", "skills",
        "model", "provider", "attempt", "wave", "status", "verdict",
        "runtime_status",
    }
    _event_types = {
        "orchestration_started", "work_unit_created", "work_unit_ready",
        "worker_dispatched", "model_selected", "worker_started",
        "work_unit_status_changed", "worker_escalated", "evaluation_finalized",
        "orchestration_completed",
    }

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = Lock()

    def emit(self, event_type: str, **fields: Any) -> None:
        if event_type not in self._event_types:
            raise ValueError(f"Unsupported observability event type: {event_type!r}")
        if event_type in {"model_selected", "worker_dispatched", "worker_started", "work_unit_status_changed", "evaluation_finalized"}:
            for key in ("orchestration_id", "work_unit_id"):
                if not isinstance(fields.get(key), str) or not fields[key].strip():
                    raise ValueError(f"{event_type} requires nonblank {key}")
        safe = {key: value for key, value in fields.items() if key in self._fields}
        safe["event_type"] = event_type
        safe.setdefault("event_id", f"adaptive:{uuid4().hex}")
        safe.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(safe, ensure_ascii=False, separators=(",", ":")) + "\n")
