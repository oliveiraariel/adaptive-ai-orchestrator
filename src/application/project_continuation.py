"""Governed successor creation for immutable terminal project checkpoints."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from application.project_orchestration_checkpoint import ProjectOrchestrationCheckpointStore
from domain.work_unit import WorkUnitState


class ProjectContinuationError(RuntimeError):
    """Raised when a terminal project cannot safely produce a successor."""


@dataclass(frozen=True)
class ProjectContinuationResult:
    predecessor_orchestration_id: str
    successor_orchestration_id: str
    reused_work_unit_ids: tuple[str, ...]
    pending_work_unit_ids: tuple[str, ...]
    already_exists: bool


class CreateProjectSuccessor:
    """Create an idempotent successor without mutating terminal evidence."""

    def __init__(self, *, checkpoint_store: ProjectOrchestrationCheckpointStore) -> None:
        self._checkpoints = checkpoint_store

    def execute(
        self, *, predecessor_orchestration_id: str, clarification: str, actor: str
    ) -> ProjectContinuationResult:
        clarification = " ".join(clarification.split())
        if not clarification or not actor.strip():
            raise ProjectContinuationError("clarification and actor must not be blank.")
        predecessor = self._checkpoints.load(predecessor_orchestration_id)
        if predecessor is None:
            raise ProjectContinuationError("Predecessor project checkpoint does not exist.")
        if predecessor.get("terminal") is not True:
            raise ProjectContinuationError("Only terminal project checkpoints may create successors.")
        if predecessor.get("active_executions"):
            raise ProjectContinuationError("Terminal predecessor still reports active executions.")
        states = predecessor.get("work_unit_states")
        plan = predecessor.get("plan")
        request = predecessor.get("request")
        if not isinstance(states, dict) or not isinstance(plan, dict) or not isinstance(request, dict):
            raise ProjectContinuationError("Predecessor checkpoint lacks a reusable plan/request.")
        successor_id = hashlib.sha256(
            f"successor-v1\x1f{predecessor_orchestration_id}\x1f{clarification}".encode()
        ).hexdigest()[:32]
        existing = self._checkpoints.load(successor_id)
        if existing is not None:
            lineage = existing.get("continuation")
            if not isinstance(lineage, dict) or lineage.get("predecessor_orchestration_id") != predecessor_orchestration_id:
                raise ProjectContinuationError("Successor identity collision.")
            return ProjectContinuationResult(
                predecessor_orchestration_id, successor_id,
                tuple(lineage.get("reused_work_unit_ids", ())),
                tuple(lineage.get("pending_work_unit_ids", ())), True,
            )
        units = [item for item in plan.get("work_units", ()) if isinstance(item, dict)]
        pending = tuple(str(item.get("id")) for item in units if states.get(item.get("id")) != WorkUnitState.COMPLETED.value)
        if not pending:
            raise ProjectContinuationError("Terminal predecessor has no unfinished Work Units.")
        pending_set = set(pending)
        successor_plan = {
            "summary": "Successor of %s: %s" % (predecessor_orchestration_id, plan.get("summary", "")),
            "work_units": [deepcopy(item) for item in units if item.get("id") in pending_set],
            "dependencies": [deepcopy(item) for item in plan.get("dependencies", ()) if item.get("source_id") in pending_set and item.get("target_id") in pending_set],
        }
        successor_request = deepcopy(request)
        context = list(successor_request.get("context", ()))
        context.append("Approved clarification from %s: %s" % (actor, clarification))
        context.append("Predecessor %s is terminal; reuse accepted evidence by reference and execute only listed pending Work Units." % predecessor_orchestration_id)
        successor_request["context"] = context
        successor_request["objective"] = str(request.get("objective", "")) + "\n\nApproved clarification: " + clarification
        reused = tuple(sorted(key for key, value in states.items() if value == WorkUnitState.COMPLETED.value))
        payload: dict[str, Any] = {
            "orchestration_id": successor_id,
            "phase": "EXECUTION",
            "desired_state": "RUNNING",
            "terminal": False,
            "request": successor_request,
            "plan": successor_plan,
            "work_unit_states": {item: WorkUnitState.PLANNED.value for item in pending},
            "dependency_states": [
                {"source_id": item["source_id"], "target_id": item["target_id"], "required": bool(item.get("required", True)), "status": "BLOCKED"}
                for item in successor_plan["dependencies"]
            ],
            "attempts": {item: 0 for item in pending},
            "strategy_generations": {item: 1 for item in pending},
            "outputs": {}, "output_refs": {}, "revision_feedback": {}, "records": [],
            "dispatch_records": [], "max_parallelism_observed": 0, "replan_count": 0,
            "dispatch_generation": 0, "pending_replan": False, "replan_feedback": "",
            "recovery_epoch_counts": {item: 0 for item in pending},
            "recovery_replans_in_epoch": {item: 0 for item in pending},
            "recovery_no_progress_counts": {item: 0 for item in pending},
            "recovery_guidance": {}, "active_executions": [],
            "continuation": {
                "schema_version": 1, "predecessor_orchestration_id": predecessor_orchestration_id,
                "clarification": clarification, "actor": actor,
                "reused_work_unit_ids": list(reused), "pending_work_unit_ids": list(pending),
                "accepted_result_refs": {key: value for key, value in predecessor.get("output_refs", {}).items() if key in reused},
            },
        }
        self._checkpoints.save(successor_id, payload)
        return ProjectContinuationResult(predecessor_orchestration_id, successor_id, reused, pending, False)
