"""Human-authorized Work Unit takeover intents.

The CLI writes only an intent. The live controller alone reconciles/cancels an
execution and changes Work Unit ownership, avoiding a second controller racing
against the old one. An intent is not evidence of cancellation or completion.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator


class GovernedTakeoverError(ValueError):
    pass


class GovernedTakeoverStore:
    VERSION = 1
    MODES = frozenset({"direct", "replacement"})

    def __init__(self, *, project_root: Path, wall_clock: Callable[[], float] = time.time):
        self.root = project_root.expanduser().resolve() / ".adaptive" / "governed-takeovers"
        self.wall_clock = wall_clock

    def _path(self, orchestration_id: str) -> Path:
        if not orchestration_id.strip():
            raise GovernedTakeoverError("Orchestration ID is required.")
        digest = hashlib.sha256(orchestration_id.encode("utf-8")).hexdigest()
        return self.root / (digest + ".json")

    @contextmanager
    def _lock(self, orchestration_id: str) -> Iterator[None]:
        target = self._path(orchestration_id)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = target.with_suffix(".lock")
        with path.open("a+", encoding="utf-8") as stream:
            os.chmod(path, 0o600)
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def load(self, orchestration_id: str) -> dict | None:
        try:
            row = json.loads(self._path(orchestration_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            raise GovernedTakeoverError("Takeover state is unreadable.") from exc
        if (
            not isinstance(row, dict) or row.get("version") != self.VERSION
            or row.get("orchestration_id") != orchestration_id
            or not isinstance(row.get("sequence"), int)
            or not isinstance(row.get("requests"), list)
        ):
            raise GovernedTakeoverError("Takeover state is invalid.")
        return row

    def _save(self, orchestration_id: str, row: dict) -> None:
        target = self._path(orchestration_id)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=target.parent,
                prefix=".takeover-", delete=False,
            ) as stream:
                temporary = stream.name
                os.chmod(temporary, 0o600)
                json.dump(row, stream, sort_keys=True, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)

    def request(
        self, *, orchestration_id: str, work_unit_id: str, mode: str,
        actor: str, reason: str, owner_agent: str | None = None,
    ) -> dict:
        if mode not in self.MODES:
            raise GovernedTakeoverError("Invalid takeover mode.")
        if not all(x.strip() for x in (work_unit_id, actor, reason)):
            raise GovernedTakeoverError("Work Unit, actor and reason are required.")
        if mode == "direct" and not (owner_agent or "").strip():
            raise GovernedTakeoverError("Direct takeover requires an explicit owner agent.")
        with self._lock(orchestration_id):
            row = self.load(orchestration_id) or {
                "version": self.VERSION,
                "orchestration_id": orchestration_id,
                "sequence": 0,
                "requests": [],
            }
            for existing in row["requests"]:
                if (
                    existing.get("work_unit_id") == work_unit_id
                    and existing.get("state") in {"REQUESTED", "QUIESCING", "APPLIED"}
                ):
                    if (existing["mode"], existing.get("owner_agent")) == (mode, owner_agent):
                        return existing
                    existing["state"] = "SUPERSEDED"
                    existing["history"].append({
                        "state": "SUPERSEDED",
                        "detail": "Superseded by newly authorized owner strategy",
                        "at": self.wall_clock(),
                    })
            row["sequence"] += 1
            request = {
                "id": str(row["sequence"]),
                "work_unit_id": work_unit_id,
                "mode": mode,
                "actor": actor,
                "reason": reason[:1000],
                "owner_agent": owner_agent,
                "state": "REQUESTED",
                "requested_at": self.wall_clock(),
                "history": [],
            }
            row["requests"].append(request)
            self._save(orchestration_id, row)
            return request

    def request_many(
        self, *, orchestration_id: str, work_unit_ids: tuple[str, ...],
        mode: str, actor: str, reason: str, owner_agent: str | None = None,
    ) -> list[dict]:
        """Atomically stage governed intents; execution remains controller-owned."""
        if not work_unit_ids or len(set(work_unit_ids)) != len(work_unit_ids):
            raise GovernedTakeoverError("Batch needs distinct pending Work Units.")
        if mode not in self.MODES or not actor.strip() or not reason.strip():
            raise GovernedTakeoverError("Invalid takeover request.")
        if mode == "direct" and not (owner_agent or "").strip():
            raise GovernedTakeoverError("A coordinator agent is required.")
        if any(not isinstance(key, str) or not key.strip() for key in work_unit_ids):
            raise GovernedTakeoverError("Invalid Work Unit identifier.")
        with self._lock(orchestration_id):
            row = self.load(orchestration_id) or {
                "version": self.VERSION, "orchestration_id": orchestration_id,
                "sequence": 0, "requests": [],
            }
            staged: list[dict] = []
            for work_unit_id in work_unit_ids:
                existing_current = next((
                    item for item in reversed(row["requests"])
                    if item.get("work_unit_id") == work_unit_id
                    and item.get("state") in {"REQUESTED", "QUIESCING", "APPLIED"}
                ), None)
                if existing_current is not None and (
                    existing_current["mode"], existing_current.get("owner_agent")
                ) == (mode, owner_agent):
                    staged.append(existing_current)
                    continue
                if existing_current is not None:
                    existing_current["state"] = "SUPERSEDED"
                    existing_current["history"].append({
                        "state": "SUPERSEDED",
                        "detail": "Replaced by operator-authorized batch",
                        "at": self.wall_clock(),
                    })
                row["sequence"] += 1
                entry = {
                    "id": str(row["sequence"]), "work_unit_id": work_unit_id,
                    "mode": mode, "actor": actor, "reason": reason[:1000],
                    "owner_agent": owner_agent, "state": "REQUESTED",
                    "requested_at": self.wall_clock(), "history": [],
                }
                row["requests"].append(entry)
                staged.append(entry)
            self._save(orchestration_id, row)
            return staged

    def current(self, orchestration_id: str, work_unit_id: str) -> dict | None:
        row = self.load(orchestration_id)
        if row is None:
            return None
        for item in reversed(row["requests"]):
            if item.get("work_unit_id") == work_unit_id:
                return item
        return None

    def transition(
        self, orchestration_id: str, request_id: str, *, state: str, detail: str,
    ) -> dict:
        if state not in {"QUIESCING", "APPLIED", "COMPLETED", "FAILED", "SUPERSEDED"}:
            raise GovernedTakeoverError("Invalid takeover transition.")
        with self._lock(orchestration_id):
            row = self.load(orchestration_id)
            if row is None:
                raise GovernedTakeoverError("Takeover state missing.")
            for item in row["requests"]:
                if item.get("id") != request_id:
                    continue
                if item["state"] in {"COMPLETED", "FAILED", "SUPERSEDED"}:
                    return item
                if item["state"] == state:
                    return item
                item["state"] = state
                item["history"].append({
                    "state": state, "detail": detail[:300], "at": self.wall_clock(),
                })
                self._save(orchestration_id, row)
                return item
            raise GovernedTakeoverError("Unknown takeover request.")
