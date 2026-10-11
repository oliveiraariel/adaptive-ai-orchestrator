from __future__ import annotations

"""Durable, bounded model quota cooldowns shared by Gateway and worker routing.

This is an operational state store, not a permanent model preference or a
replacement for Work Unit recovery. It contains no credentials or prompts.
"""

import fcntl
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Callable


DEFAULT_COOLDOWN_SECONDS = 5 * 60 * 60 + 5 * 60
_RENEWABLE_QUOTA_SUBTYPES = frozenset({
    "tpm", "rpm", "concurrency", "provider_rate_limit_unknown",
    "model_usage_window", "rolling_usage_window",
})


class ModelQuotaCooldownStore:
    def __init__(
        self,
        path: str | Path,
        *,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
        wall_clock: Callable[[], float] = time.time,
        enabled: bool = True,
    ) -> None:
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")
        self.path = Path(path).expanduser()
        self.cooldown_seconds = cooldown_seconds
        self.wall_clock = wall_clock
        self.enabled = enabled

    @classmethod
    def from_env(cls) -> "ModelQuotaCooldownStore":
        enabled = os.environ.get("ADAPTIVE_QUOTA_CONTINUITY_ENABLED", "1").strip().casefold()
        if enabled not in {"1", "0", "true", "false", "yes", "no"}:
            raise ValueError("ADAPTIVE_QUOTA_CONTINUITY_ENABLED must be boolean")
        raw_seconds = os.environ.get("ADAPTIVE_GPT_QUOTA_COOLDOWN_SECONDS", "18300")
        seconds = int(raw_seconds)
        path = os.environ.get("ADAPTIVE_QUOTA_CONTINUITY_PATH") or (
            Path.home() / ".local/state/adaptive-ai-orchestrator/model-quota-cooldowns.json"
        )
        return cls(path, cooldown_seconds=seconds, enabled=enabled in {"1", "true", "yes"})

    @staticmethod
    def _route_key(provider: str, model: str, auth_profile: str | None) -> str:
        canonical = "\0".join((
            provider.strip().casefold(), model.strip().casefold(),
            (auth_profile or "").strip().casefold(),
        ))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _read_unlocked(self) -> dict[str, object]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"schema_version": 1, "routes": {}}
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ValueError("Invalid model quota continuity state")
        routes = raw.get("routes")
        if not isinstance(routes, dict):
            raise ValueError("Invalid model quota continuity routes")
        return raw

    def is_cooling(self, provider: str, model: str, auth_profile: str | None = None) -> bool:
        if not self.enabled:
            return False
        state = self._read_unlocked()
        routes = state["routes"]
        assert isinstance(routes, dict)
        row = routes.get(self._route_key(provider, model, auth_profile))
        return bool(
            isinstance(row, dict)
            and isinstance(row.get("until"), (int, float))
            and not isinstance(row.get("until"), bool)
            and row["until"] > self.wall_clock()
        )

    def record_quota(
        self, provider: str, model: str, auth_profile: str | None,
        *, category: str, subtype: str,
    ) -> bool:
        """Record only renewable quota limits, never billing/auth/config errors.

        Project daily/monthly budgets and weekly usage windows do not promise a
        5h05 reset; they must remain subject to normal incident remediation.
        """
        if (
            not self.enabled
            or provider.casefold() != "openai"
            or category != "quota"
            or subtype not in _RENEWABLE_QUOTA_SUBTYPES
        ):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self.path.with_name(self.path.name + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lock:
            os.chmod(lock_path, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            temporary: str | None = None
            try:
                state = self._read_unlocked()
                routes = state["routes"]
                assert isinstance(routes, dict)
                now = self.wall_clock()
                # Drop expired rows; keep other active provider/model profiles.
                routes = {
                    key: value for key, value in routes.items()
                    if isinstance(value, dict)
                    and isinstance(value.get("until"), (int, float))
                    and value["until"] > now
                }
                key = self._route_key(provider, model, auth_profile)
                old = routes.get(key, {})
                old_until = float(old.get("until", 0)) if isinstance(old, dict) else 0.0
                routes[key] = {
                    "until": max(old_until, now + self.cooldown_seconds),
                    "reason": "renewable-quota",
                }
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=self.path.parent,
                    prefix=".model-quota-", delete=False,
                ) as handle:
                    temporary = handle.name
                    os.chmod(handle.name, 0o600)
                    json.dump({"schema_version": 1, "routes": routes}, handle, sort_keys=True)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
                temporary = None
                return True
            finally:
                if temporary is not None:
                    try:
                        os.unlink(temporary)
                    except FileNotFoundError:
                        pass
                fcntl.flock(lock, fcntl.LOCK_UN)
