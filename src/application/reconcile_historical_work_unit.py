"""Official, evidence-gated reconciliation of a historical returned Work Unit."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from application.completion_integrity import parse_worker_completion
from application.project_orchestration_checkpoint import ProjectOrchestrationCheckpointStore
from domain.dependency import DependencyStatus
from domain.work_unit import WorkUnitState
from infrastructure.orchestration_control_plane import FileOrchestrationControlPlane
from infrastructure.result_store import FileResultStore, ResultStoreError


class ReconciliationDecision(str, Enum):
    ACCEPTED = "ACCEPTED"
    PRACTICAL_TEST_READY = "PRACTICAL_TEST_READY"


class HistoricalWorkUnitReconciliationError(RuntimeError):
    """Raised when historical evidence does not support a governed promotion."""


@dataclass(frozen=True)
class HistoricalWorkUnitReconciliationResult:
    orchestration_id: str
    work_unit_id: str
    decision: ReconciliationDecision
    decision_id: str
    already_reconciled: bool
    source_execution_id: str
    source_result_ref: str


class ReconcileHistoricalWorkUnit:
    """Append a decision; never rewrite the prior RETURNED execution record."""

    def __init__(
        self,
        *,
        project_root: Path,
        checkpoint_store: ProjectOrchestrationCheckpointStore,
        control_plane: FileOrchestrationControlPlane,
    ) -> None:
        self._project_root = project_root.expanduser().resolve()
        self._checkpoints = checkpoint_store
        self._control = control_plane
        self._results = FileResultStore(project_root=self._project_root)

    def execute(
        self,
        *,
        orchestration_id: str,
        work_unit_id: str,
        decision: ReconciliationDecision,
        reason: str,
        actor: str,
        policy: str,
    ) -> HistoricalWorkUnitReconciliationResult:
        if not work_unit_id.strip():
            raise HistoricalWorkUnitReconciliationError("work_unit_id must not be blank.")
        if not reason.strip() or not actor.strip() or not policy.strip():
            raise HistoricalWorkUnitReconciliationError(
                "reason, actor, and policy must be explicit for reconciliation."
            )
        with self._control.mutation_lock(orchestration_id):
            checkpoint = self._checkpoints.load(orchestration_id)
            if checkpoint is None:
                raise HistoricalWorkUnitReconciliationError("Project checkpoint does not exist.")
            self._validate_quiescent(orchestration_id, checkpoint)
            result = self._apply(
                orchestration_id=orchestration_id,
                checkpoint=checkpoint,
                work_unit_id=work_unit_id,
                decision=decision,
                reason=reason,
                actor=actor,
                policy=policy,
            )
            if not result.already_reconciled:
                self._checkpoints.save(orchestration_id, checkpoint)
            return result

    def _validate_quiescent(self, orchestration_id: str, checkpoint: dict[str, Any]) -> None:
        if checkpoint.get("desired_state") != "PAUSED":
            raise HistoricalWorkUnitReconciliationError(
                "Reconciliation is an administrative PAUSED operation."
            )
        active = checkpoint.get("active_executions")
        if not isinstance(active, list) or active:
            raise HistoricalWorkUnitReconciliationError(
                "Reconciliation requires no active executions."
            )
        if not self._control.is_quiescent(orchestration_id):
            raise HistoricalWorkUnitReconciliationError(
                "Reconciliation requires a governed QUIESCENT controller fence."
            )

    def _apply(
        self,
        *,
        orchestration_id: str,
        checkpoint: dict[str, Any],
        work_unit_id: str,
        decision: ReconciliationDecision,
        reason: str,
        actor: str,
        policy: str,
    ) -> HistoricalWorkUnitReconciliationResult:
        states = checkpoint.get("work_unit_states")
        if not isinstance(states, dict) or work_unit_id not in states:
            raise HistoricalWorkUnitReconciliationError("Work Unit is not in the persisted Work Graph.")
        current = str(states[work_unit_id])
        decisions = checkpoint.setdefault("reconciliation_decisions", [])
        if not isinstance(decisions, list):
            raise HistoricalWorkUnitReconciliationError("Reconciliation audit trail is malformed.")
        existing = [
            item for item in decisions
            if isinstance(item, dict) and item.get("work_unit_id") == work_unit_id
        ]
        if current == WorkUnitState.COMPLETED.value:
            if not existing:
                raise HistoricalWorkUnitReconciliationError(
                    "Completed Work Unit has no governed reconciliation audit trail."
                )
            latest = existing[-1]
            if latest.get("decision") != decision.value:
                raise HistoricalWorkUnitReconciliationError(
                    "A different reconciliation decision already exists for this Work Unit."
                )
            return HistoricalWorkUnitReconciliationResult(
                orchestration_id, work_unit_id, decision, str(latest["decision_id"]),
                True, str(latest["source_execution_id"]), str(latest["source_result_ref"]),
            )
        if current not in {
            WorkUnitState.REVISION_REQUIRED.value,
            WorkUnitState.RECOVERY_REQUIRED.value,
            WorkUnitState.BLOCKED.value,
        }:
            raise HistoricalWorkUnitReconciliationError(
                f"Only RETURNED/RECOVERY_REQUIRED Work Units may be reconciled, got {current}."
            )

        candidate = self._candidate(checkpoint, work_unit_id)
        if (
            current == WorkUnitState.BLOCKED.value
            and candidate.get("verdict") != "RETURNED"
        ):
            raise HistoricalWorkUnitReconciliationError(
                "A blocked Work Unit may be reconciled only from a historical "
                "RETURNED result that independently satisfies the evidence gate."
            )
        execution_id = str(candidate.get("execution_id") or "")
        result_ref = str(candidate.get("result_ref") or "")
        self._verify_result(
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
            result_ref=result_ref,
        )
        completion = parse_worker_completion(str(candidate.get("output") or ""))
        if not completion.is_terminal_success:
            raise HistoricalWorkUnitReconciliationError(
                "Worker completion is not a usable COMPLETE result without blockers or unmet criteria."
            )
        decision_id = hashlib.sha256(
            "\x1f".join((orchestration_id, work_unit_id, decision.value, execution_id, result_ref)).encode("utf-8")
        ).hexdigest()
        audit = {
            "schema_version": 1,
            "decision_id": decision_id,
            "work_unit_id": work_unit_id,
            "decision": decision.value,
            "source_execution_id": execution_id,
            "source_result_ref": result_ref,
            "historical_verdict": str(candidate.get("verdict") or "RETURNED"),
            "historical_status": str(candidate.get("status") or current),
            "actor": actor,
            "policy": policy,
            "reason": reason,
            "recorded_at": time.time(),
        }
        decisions.append(audit)
        # COMPLETED is the graph's dependency-satisfaction state. The audit
        # decision preserves whether this was normal ACCEPTED or practical-test
        # release without erasing the historical RETURNED record.
        states[work_unit_id] = WorkUnitState.COMPLETED.value
        for dependency in checkpoint.get("dependency_states", []):
            if isinstance(dependency, dict) and dependency.get("source_id") == work_unit_id:
                dependency["status"] = DependencyStatus.SATISFIED.value
        outputs = checkpoint.setdefault("outputs", {})
        refs = checkpoint.setdefault("output_refs", {})
        if isinstance(outputs, dict):
            outputs[work_unit_id] = str(candidate.get("output") or "")
        if isinstance(refs, dict):
            refs[work_unit_id] = result_ref
        for name in ("revision_feedback", "recovery_guidance"):
            mapping = checkpoint.get(name)
            if isinstance(mapping, dict):
                mapping.pop(work_unit_id, None)
        recovery = checkpoint.get("recovery_replans_in_epoch")
        if isinstance(recovery, dict):
            recovery[work_unit_id] = 0
        no_progress = checkpoint.get("recovery_no_progress_counts")
        if isinstance(no_progress, dict):
            no_progress[work_unit_id] = 0
        remaining_recovery = any(value == WorkUnitState.RECOVERY_REQUIRED.value for value in states.values())
        if not remaining_recovery:
            checkpoint["pending_replan"] = False
        return HistoricalWorkUnitReconciliationResult(
            orchestration_id, work_unit_id, decision, decision_id, False, execution_id, result_ref
        )

    @staticmethod
    def _candidate(checkpoint: dict[str, Any], work_unit_id: str) -> dict[str, Any]:
        records = checkpoint.get("records")
        if not isinstance(records, list):
            raise HistoricalWorkUnitReconciliationError("Work Unit execution history is unavailable.")
        for candidate in reversed(records):
            if not isinstance(candidate, dict) or candidate.get("work_unit_id") != work_unit_id:
                continue
            if (
                candidate.get("runtime_status") == "COMPLETED"
                and candidate.get("result_authoritative") is True
                and isinstance(candidate.get("execution_id"), str)
                and isinstance(candidate.get("result_ref"), str)
                and candidate.get("result_ref")
            ):
                return candidate
        raise HistoricalWorkUnitReconciliationError(
            "No completed authoritative worker result supports reconciliation."
        )

    def _verify_result(
        self,
        *,
        orchestration_id: str,
        work_unit_id: str,
        execution_id: str,
        result_ref: str,
    ) -> None:
        try:
            self._results.read_manifest_ref(
                orchestration_id=orchestration_id,
                work_unit_id=work_unit_id,
                execution_id=execution_id,
                manifest_ref=result_ref,
            )
        except ResultStoreError as exc:
            raise HistoricalWorkUnitReconciliationError(
                f"Result Store evidence is not intact: {exc}"
            ) from exc
