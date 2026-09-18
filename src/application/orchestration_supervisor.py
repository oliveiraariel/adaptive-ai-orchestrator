from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


@dataclass(frozen=True)
class OrchestrationRecoveryDirective:
    orchestration_id: str
    action: str
    reason: str
    desired_state: str
    active_execution_count: int
    last_controller_heartbeat_at: float | None


class ProjectOrchestrationSupervisor:
    """Deterministically revive RUNNING checkpointed projects whose controller died.

    This supervisor does not plan or reason. It decides only whether a persisted
    orchestration is eligible for resume. The resumed orchestrator still owns
    active-execution reconciliation, claims, Recovery Strategist invocation,
    policy, planning, dispatch and learning.
    """

    def __init__(
        self,
        *,
        project_root: Path,
        stale_after_seconds: float = 45.0,
        lease_seconds: float = 120.0,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.project_root = project_root.expanduser().resolve()
        self.checkpoints = FileProjectOrchestrationCheckpointStore(
            project_root=self.project_root
        )
        self.stale_after_seconds = stale_after_seconds
        self.lease_seconds = lease_seconds
        self.wall_clock = wall_clock
        self._controller_root = (
            self.project_root / ".adaptive" / "orchestration-liveness"
        )
        self._lease_root = self.project_root / ".adaptive" / "supervisor-leases"

    def directives(
        self,
        *,
        orchestration_id: str | None = None,
    ) -> tuple[OrchestrationRecoveryDirective, ...]:
        now = self.wall_clock()
        directives: list[OrchestrationRecoveryDirective] = []
        for candidate_id, state in self.checkpoints.list_all():
            if orchestration_id is not None and candidate_id != orchestration_id:
                continue
            current_orchestration_id = candidate_id
            if state.get("terminal") is True:
                continue
            desired_state = str(state.get("desired_state") or "RUNNING")
            active = state.get("active_executions")
            active_count = len(active) if isinstance(active, list) else 0
            heartbeat = self._controller_heartbeat(current_orchestration_id)
            last = self._heartbeat_timestamp(heartbeat)
            controller_active = bool(
                isinstance(heartbeat, dict)
                and heartbeat.get("controller_state") == "ACTIVE"
                and last is not None
                and now - last <= self.stale_after_seconds
            )
            if desired_state == "PAUSED":
                directives.append(
                    OrchestrationRecoveryDirective(
                        orchestration_id=current_orchestration_id,
                        action="PAUSED",
                        reason="developer-requested-pause",
                        desired_state=desired_state,
                        active_execution_count=active_count,
                        last_controller_heartbeat_at=last,
                    )
                )
                continue
            if controller_active:
                directives.append(
                    OrchestrationRecoveryDirective(
                        orchestration_id=current_orchestration_id,
                        action="OBSERVE",
                        reason="controller-heartbeat-fresh",
                        desired_state=desired_state,
                        active_execution_count=active_count,
                        last_controller_heartbeat_at=last,
                    )
                )
                continue
            directives.append(
                OrchestrationRecoveryDirective(
                    orchestration_id=current_orchestration_id,
                    action="RESUME",
                    reason=(
                        "controller-heartbeat-missing"
                        if last is None
                        else "controller-heartbeat-stale"
                    ),
                    desired_state=desired_state,
                    active_execution_count=active_count,
                    last_controller_heartbeat_at=last,
                )
            )
        return tuple(directives)

    def run_once(
        self,
        resume: Callable[[str], object],
        *,
        orchestration_id: str | None = None,
    ) -> tuple[str, ...]:
        resumed: list[str] = []
        for directive in self.directives(orchestration_id=orchestration_id):
            if directive.action != "RESUME":
                continue
            if not self._acquire_lease(directive.orchestration_id):
                continue
            try:
                resume(directive.orchestration_id)
                resumed.append(directive.orchestration_id)
            finally:
                self._release_lease(directive.orchestration_id)
        return tuple(resumed)

    def _controller_heartbeat(self, orchestration_id: str) -> dict | None:
        digest = hashlib.sha256(orchestration_id.encode("utf-8")).hexdigest()
        path = self._controller_root / f"{digest}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("orchestration_id") != orchestration_id:
            return None
        return payload

    @staticmethod
    def _heartbeat_timestamp(payload: dict | None) -> float | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get("last_heartbeat_at")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    def _lease_path(self, orchestration_id: str) -> Path:
        digest = hashlib.sha256(orchestration_id.encode("utf-8")).hexdigest()
        return self._lease_root / f"{digest}.lease"

    def _acquire_lease(self, orchestration_id: str) -> bool:
        path = self._lease_path(orchestration_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = self.wall_clock()

        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            existing = None
        except (OSError, json.JSONDecodeError, TypeError):
            existing = None

        if isinstance(existing, dict):
            expires_at = existing.get("expires_at")
            if isinstance(expires_at, (int, float)) and not isinstance(expires_at, bool):
                if float(expires_at) > now:
                    return False
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                return False

        payload = {
            "orchestration_id": orchestration_id,
            "pid": os.getpid(),
            "acquired_at": now,
            "expires_at": now + self.lease_seconds,
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError:
            return False
        except OSError:
            return False
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(payload, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
        except OSError:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        return True

    def _release_lease(self, orchestration_id: str) -> None:
        path = self._lease_path(orchestration_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return
        if isinstance(payload, dict) and payload.get("pid") == os.getpid():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
