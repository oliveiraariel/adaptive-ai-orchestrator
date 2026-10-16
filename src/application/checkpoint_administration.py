"""Evidence-gated administration of durable project checkpoints.

This module deliberately does not schedule work.  It classifies durable state,
regularizes proven terminal/unsafe historical records through the official
checkpoint store, and leaves recovery dispatch to the existing supervisor.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from application.completion_integrity import parse_worker_completion
from infrastructure.orchestration_control_plane import (
    FileOrchestrationControlPlane,
    OrchestrationControlPlaneError,
)
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
    ProjectOrchestrationCheckpointError,
)
from infrastructure.result_store import FileResultStore, ResultStoreError
from domain.release_delivery import (
    release_delivery_required_for_checkpoint,
    validate_release_delivery,
)


class CheckpointClassification(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    RECOVERABLE = "RECOVERABLE"
    HUMAN_DECISION_REQUIRED = "HUMAN_DECISION_REQUIRED"
    BUSY = "BUSY"
    TERMINAL = "TERMINAL"


class CheckpointAdministrationAction(str, Enum):
    OBSERVE = "OBSERVE"
    TERMINALIZE = "TERMINALIZE"
    RESUME = "RESUME"
    PAUSE = "PAUSE"
    RETRY_LATER = "RETRY_LATER"


@dataclass(frozen=True)
class CheckpointAdministrationResult:
    orchestration_id: str
    classification: CheckpointClassification
    action: CheckpointAdministrationAction
    reason: str
    checkpoint_digest: str
    report_id: str | None = None
    persisted: bool = False


class CheckpointAdministrationError(RuntimeError):
    """Raised when administration cannot safely preserve durable evidence."""


class CheckpointAdministrator:
    """Classify and safely regularize durable orchestration lifecycle state."""

    def __init__(
        self,
        *,
        project_root: Path,
        stale_after_seconds: float = 45.0,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        self.project_root = project_root.expanduser().resolve()
        self.stale_after_seconds = stale_after_seconds
        self.wall_clock = wall_clock
        self.checkpoints = FileProjectOrchestrationCheckpointStore(
            project_root=self.project_root
        )
        self.control = FileOrchestrationControlPlane(project_root=self.project_root)
        # Inspection must not mutate a project's Git exclude file merely to
        # construct a Result Store reader.
        self.results = FileResultStore(
            project_root=self.project_root,
            manage_git_exclude=False,
        )
        self._heartbeat_root = self.project_root / ".adaptive" / "orchestration-liveness"
        self._backup_root = self.project_root / ".adaptive" / "checkpoint-administration-backups"

    def reconcile(
        self,
        *,
        orchestration_id: str | None = None,
        allow_resume: bool = False,
    ) -> tuple[CheckpointAdministrationResult, ...]:
        """Inspect a scope and persist only terminalization or a safe hold.

        ``allow_resume`` is intentionally reserved for a targeted guardian.
        Global supervision is detect-and-hold, never a historical redispatch
        sweep.
        """
        outcomes: list[CheckpointAdministrationResult] = []
        for candidate_id, checkpoint in self.checkpoints.list_all():
            if orchestration_id is not None and candidate_id != orchestration_id:
                continue
            outcome = self._classify(
                orchestration_id=candidate_id,
                checkpoint=checkpoint,
                allow_resume=allow_resume and orchestration_id == candidate_id,
            )
            if outcome.action in {
                CheckpointAdministrationAction.TERMINALIZE,
                CheckpointAdministrationAction.PAUSE,
            }:
                outcome = self._persist(candidate_id, outcome, allow_resume=allow_resume)
            outcomes.append(outcome)
        return tuple(outcomes)

    def _persist(
        self,
        orchestration_id: str,
        expected: CheckpointAdministrationResult,
        *,
        allow_resume: bool,
    ) -> CheckpointAdministrationResult:
        try:
            with self.control.mutation_lock(orchestration_id):
                checkpoint = self.checkpoints.load(orchestration_id)
                if checkpoint is None:
                    raise CheckpointAdministrationError("Checkpoint disappeared during administration.")
                current = self._classify(
                    orchestration_id=orchestration_id,
                    checkpoint=checkpoint,
                    allow_resume=allow_resume,
                )
                if current.action not in {
                    CheckpointAdministrationAction.TERMINALIZE,
                    CheckpointAdministrationAction.PAUSE,
                }:
                    return current
                backup_sha256 = self._backup(orchestration_id)
                report_id = self._append_report(
                    checkpoint=checkpoint,
                    outcome=current,
                    backup_sha256=backup_sha256,
                )
                if current.action is CheckpointAdministrationAction.TERMINALIZE:
                    checkpoint["terminal"] = True
                    checkpoint["phase"] = "TERMINAL"
                else:
                    # A hold changes controller intent only. It preserves active
                    # identities and Work Unit obligations for later recovery.
                    checkpoint["desired_state"] = "PAUSED"
                self.checkpoints.save(orchestration_id, checkpoint)
                return CheckpointAdministrationResult(
                    orchestration_id=orchestration_id,
                    classification=current.classification,
                    action=current.action,
                    reason=current.reason,
                    checkpoint_digest=current.checkpoint_digest,
                    report_id=report_id,
                    persisted=True,
                )
        except OrchestrationControlPlaneError:
            return CheckpointAdministrationResult(
                orchestration_id=orchestration_id,
                classification=CheckpointClassification.BUSY,
                action=CheckpointAdministrationAction.RETRY_LATER,
                reason="governed-mutation-in-progress",
                checkpoint_digest=expected.checkpoint_digest,
            )

    def _classify(
        self,
        *,
        orchestration_id: str,
        checkpoint: dict[str, Any],
        allow_resume: bool,
    ) -> CheckpointAdministrationResult:
        digest = self._checkpoint_digest(checkpoint)
        if checkpoint.get("terminal") is True:
            return self._outcome(orchestration_id, CheckpointClassification.TERMINAL, CheckpointAdministrationAction.OBSERVE, "checkpoint-terminal", digest)
        if str(checkpoint.get("desired_state") or "RUNNING") == "PAUSED":
            return self._outcome(orchestration_id, CheckpointClassification.PAUSED, CheckpointAdministrationAction.OBSERVE, "desired-state-paused", digest)
        if self._controller_is_fresh(orchestration_id):
            return self._outcome(orchestration_id, CheckpointClassification.ACTIVE, CheckpointAdministrationAction.OBSERVE, "controller-heartbeat-fresh", digest)
        if self._has_proven_completion(orchestration_id, checkpoint):
            return self._outcome(orchestration_id, CheckpointClassification.COMPLETED, CheckpointAdministrationAction.TERMINALIZE, "authoritative-semantic-completion", digest)
        if self._workspace_is_dirty():
            return self._outcome(orchestration_id, CheckpointClassification.HUMAN_DECISION_REQUIRED, CheckpointAdministrationAction.PAUSE, "workspace-dirty", digest)
        if not allow_resume and not self._global_auto_resume_allowed(checkpoint):
            return self._outcome(orchestration_id, CheckpointClassification.HUMAN_DECISION_REQUIRED, CheckpointAdministrationAction.PAUSE, "global-supervision-requires-targeted-guardian", digest)
        return self._outcome(orchestration_id, CheckpointClassification.RECOVERABLE, CheckpointAdministrationAction.RESUME, "controller-heartbeat-missing-or-stale", digest)

    @staticmethod
    def _outcome(
        orchestration_id: str,
        classification: CheckpointClassification,
        action: CheckpointAdministrationAction,
        reason: str,
        digest: str,
    ) -> CheckpointAdministrationResult:
        return CheckpointAdministrationResult(orchestration_id, classification, action, reason, digest)

    def _has_proven_completion(self, orchestration_id: str, checkpoint: dict[str, Any]) -> bool:
        active = checkpoint.get("active_executions")
        states = checkpoint.get("work_unit_states")
        if not isinstance(active, list) or active or not isinstance(states, dict) or not states:
            return False
        if any(state != "COMPLETED" for state in states.values()):
            return False
        records = checkpoint.get("records")
        if not isinstance(records, list):
            return False
        for work_unit_id in states:
            matching = [
                record for record in records
                if isinstance(record, dict)
                and record.get("work_unit_id") == work_unit_id
                and record.get("verdict") == "ACCEPTED"
                and record.get("runtime_status") == "COMPLETED"
                and record.get("result_authoritative") is True
                and isinstance(record.get("execution_id"), str)
                and isinstance(record.get("result_ref"), str)
            ]
            if not matching:
                return False
            record = matching[-1]
            try:
                stored = self.results.read_manifest_ref(
                    orchestration_id=orchestration_id,
                    work_unit_id=work_unit_id,
                    execution_id=record["execution_id"],
                    manifest_ref=record["result_ref"],
                )
            except (ResultStoreError, OSError, TypeError, ValueError):
                return False
            if not parse_worker_completion(stored.content).is_terminal_success:
                return False
            if release_delivery_required_for_checkpoint(checkpoint, work_unit_id):
                delivery = validate_release_delivery(raw_result=None, output=stored.content)
                if not delivery.valid:
                    return False
        return True

    def _controller_is_fresh(self, orchestration_id: str) -> bool:
        digest = hashlib.sha256(orchestration_id.encode("utf-8")).hexdigest()
        path = self._heartbeat_root / f"{digest}.json"
        try:
            heartbeat = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, json.JSONDecodeError):
            return False
        timestamp = heartbeat.get("last_heartbeat_at") if isinstance(heartbeat, dict) else None
        return bool(
            isinstance(heartbeat, dict)
            and heartbeat.get("orchestration_id") == orchestration_id
            and heartbeat.get("controller_state") == "ACTIVE"
            and isinstance(timestamp, (int, float))
            and not isinstance(timestamp, bool)
            and self.wall_clock() - float(timestamp) <= self.stale_after_seconds
        )

    def _workspace_is_dirty(self) -> bool:
        if not (self.project_root / ".git").exists():
            return False
        try:
            completed = subprocess.run(
                ["git", "-C", str(self.project_root), "status", "--porcelain"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return True
        return completed.returncode != 0 or bool(completed.stdout.strip())

    @staticmethod
    def _global_auto_resume_allowed(checkpoint: dict[str, Any]) -> bool:
        administration = checkpoint.get("checkpoint_administration")
        return bool(
            isinstance(administration, dict)
            and administration.get("global_auto_resume") is True
        )

    def _backup(self, orchestration_id: str) -> str:
        source = self.checkpoints.path_for(orchestration_id)
        try:
            raw = source.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            destination = self._backup_root / hashlib.sha256(orchestration_id.encode("utf-8")).hexdigest() / f"{digest}.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                temporary = destination.with_suffix(".tmp")
                shutil.copyfile(source, temporary)
                temporary.chmod(0o600)
                temporary.replace(destination)
            return digest
        except OSError as exc:
            raise CheckpointAdministrationError("Unable to create a verifiable checkpoint backup.") from exc

    def _append_report(
        self,
        *,
        checkpoint: dict[str, Any],
        outcome: CheckpointAdministrationResult,
        backup_sha256: str,
    ) -> str:
        report_id = hashlib.sha256(
            "\x1f".join((outcome.orchestration_id, outcome.classification.value, outcome.action.value, outcome.checkpoint_digest)).encode("utf-8")
        ).hexdigest()
        administration = checkpoint.setdefault("checkpoint_administration", {"schema_version": 1, "reports": []})
        if not isinstance(administration, dict):
            raise CheckpointAdministrationError("Checkpoint administration history is malformed.")
        reports = administration.setdefault("reports", [])
        if not isinstance(reports, list):
            raise CheckpointAdministrationError("Checkpoint administration reports are malformed.")
        if not any(isinstance(item, dict) and item.get("report_id") == report_id for item in reports):
            reports.append(
                {
                    "schema_version": 1,
                    "report_id": report_id,
                    "prior_desired_state": str(checkpoint.get("desired_state") or "RUNNING"),
                    "classification": outcome.classification.value,
                    "action": outcome.action.value,
                    "reason": outcome.reason,
                    "checkpoint_digest": outcome.checkpoint_digest,
                    "backup_sha256": backup_sha256,
                    "recorded_at": self.wall_clock(),
                    "evidence": ["checkpoint", "controller-heartbeat", "result-store", "workspace"],
                }
            )
        return report_id

    @staticmethod
    def _checkpoint_digest(checkpoint: dict[str, Any]) -> str:
        material = {key: value for key, value in checkpoint.items() if key != "checkpoint_administration"}
        encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
