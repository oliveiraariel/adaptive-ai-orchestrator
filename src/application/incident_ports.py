from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Protocol


@dataclass(frozen=True)
class IncidentNotification:
    key: str
    incident_id: str
    severity: str
    status: str
    action: str
    message: str


@dataclass(frozen=True)
class ExternalResearchRequest:
    incident_id: str
    query: str
    preferred_sources: tuple[str, ...] = (
        "vendor-documentation",
        "official-issue-tracker",
        "upstream-source-repository",
    )


class NotificationPort(Protocol):
    def publish(self, notification: IncidentNotification) -> bool: ...


class ExternalResearchPort(Protocol):
    def research(self, request: ExternalResearchRequest) -> tuple[str, ...]: ...


class NullNotificationPort:
    def publish(self, notification: IncidentNotification) -> bool:
        return False


def canonical_notification_outbox() -> Path:
    override = os.environ.get("ADAPTIVE_NOTIFICATION_OUTBOX", "").strip()
    if override:
        return Path(override).expanduser()
    state_home = os.environ.get("XDG_STATE_HOME", "").strip()
    root = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return root / "adaptive-ai-orchestrator" / "notifications.jsonl"


class JsonlNotificationOutbox:
    """Persistent, deduplicated notification port for UI/runtime adapters.

    The Adaptive core writes small safe event records. A CLI, OpenClaw adapter,
    Slack/email connector, or future runtime may consume this outbox without
    putting external communication authority inside the incident domain.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or canonical_notification_outbox()
        self._lock = Lock()

    def publish(self, notification: IncidentNotification) -> bool:
        if not notification.key.strip() or not notification.incident_id.strip():
            return False
        if self._already_published(notification.key):
            return False
        payload = {
            "key": notification.key[:240],
            "incident_id": notification.incident_id[:120],
            "severity": notification.severity[:24],
            "status": notification.status[:48],
            "action": notification.action[:120],
            "message": notification.message.replace("\n", " ").strip()[:500],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        return True

    def _already_published(self, key: str) -> bool:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        for raw in reversed(lines[-500:]):
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("key") == key:
                return True
        return False
