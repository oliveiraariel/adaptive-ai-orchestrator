from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from datetime import datetime, timezone


class ObservabilitySink(Protocol):
    def emit(self, event_type: str, **fields: Any) -> None: ...


class NullObservabilitySink:
    def emit(self, event_type: str, **fields: Any) -> None:
        return None


class JsonlObservabilitySink:
    """Append-only, allowlisted operational events; never stores raw payloads."""

    _fields = {
        "event_id", "timestamp", "orchestration_id", "work_unit_id",
        "execution_id", "external_id", "role", "objective", "skills",
        "model", "provider", "attempt", "wave", "status", "verdict",
        "summary", "reason", "runtime_status",
    }

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = Lock()

    def emit(self, event_type: str, **fields: Any) -> None:
        safe = {key: value for key, value in fields.items() if key in self._fields}
        safe["event_type"] = event_type
        safe.setdefault("event_id", f"adaptive:{datetime.now(timezone.utc).isoformat()}:{id(safe)}")
        safe.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(safe, ensure_ascii=False, separators=(",", ":")) + "\n")
