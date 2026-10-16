"""Governed interlock for starting a new project in a checkout with prior work.

A new job must not inherit the write authority of an unfinished controller.
The interlock requests a cooperative pause and allows admission only when
the earlier controller has actually released authority (or the controller
heartbeat is stale AND the durable checkpoint has no active executions).
It never fabricates a successful terminal result.
"""

from __future__ import annotations

from pathlib import Path

from application.checkpoint_administration import CheckpointAdministrator
from infrastructure.orchestration_control_plane import (
    FileOrchestrationControlPlane,
    OrchestrationControlPlaneError,
)
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


class PriorProjectNotQuiescentError(RuntimeError):
    """A prior execution still owns or may own the checkout."""


def govern_prior_projects(*, project_root: Path, incoming_orchestration_id: str) -> tuple[str, ...]:
    """Cooperatively pause prior nonterminal projects before a fresh admission.

    Mutations are limited to the old checkpoint's desired_state and its
    control-plane record. Every active worker is left untouched. An active
    controller must acknowledge PAUSED by becoming QUIESCENT before a new
    admission proceeds; a stale controller with zero persisted executions can
    be quiesced under the governed lock. No terminal verdict is forged.
    """
    root = project_root.expanduser().resolve()
    checkpoints = FileProjectOrchestrationCheckpointStore(project_root=root)
    control = FileOrchestrationControlPlane(project_root=root)
    administrator = CheckpointAdministrator(project_root=root)
    held: list[str] = []
    blocked: list[str] = []

    for prior_id, _ in checkpoints.list_all():
        if prior_id == incoming_orchestration_id:
            continue
        with control.mutation_lock(prior_id):
            checkpoint = checkpoints.load(prior_id)
            if checkpoint is None:
                continue
            active = checkpoint.get("active_executions")
            if not isinstance(active, list):
                if checkpoint.get("phase") == "ADMITTED" and checkpoint.get("terminal") is not True:
                    # No dispatch inventory exists yet. The planner may still
                    # be running: request pause, but never assume quiescence.
                    if checkpoint.get("desired_state") != "PAUSED":
                        checkpoint["desired_state"] = "PAUSED"
                        checkpoints.save(prior_id, checkpoint)
                        held.append(prior_id)
                    blocked.append(f"{prior_id}:admitted-planner-not-yet-quiescent")
                else:
                    blocked.append(f"{prior_id}:invalid-active-executions")
                continue
            if checkpoint.get("terminal") is True:
                if active:
                    blocked.append(f"{prior_id}:terminal-with-active-executions")
                    continue
                # Historical terminal checkpoints remain immutable. Repair only
                # a missing terminal control-plane fence where safe.
                if not active and not control.is_quiescent(prior_id):
                    control.mark_terminal(
                        orchestration_id=prior_id,
                        checkpoint=checkpoint,
                        reason="new-admission:terminal-control-plane-reconciliation",
                    )
                continue
            if active:
                if checkpoint.get("desired_state") != "PAUSED":
                    checkpoint["desired_state"] = "PAUSED"
                    checkpoints.save(prior_id, checkpoint)
                    held.append(prior_id)
                blocked.append(f"{prior_id}:active-executions")
                continue
            if control.is_quiescent(prior_id) and checkpoint.get("desired_state") == "PAUSED":
                continue
            if checkpoint.get("desired_state") != "PAUSED":
                checkpoint["desired_state"] = "PAUSED"
                checkpoints.save(prior_id, checkpoint)
                held.append(prior_id)
            if administrator._controller_is_fresh(prior_id):
                # Never release a fresh controller's mutation authority based
                # solely on its worker count: it may dispatch the next wave.
                blocked.append(f"{prior_id}:awaiting-controller-quiescence")
                continue
            control.mark_quiescent(
                orchestration_id=prior_id,
                checkpoint=checkpoint,
                reason="new-admission:stale-controller-without-active-executions",
            )

    if blocked:
        raise PriorProjectNotQuiescentError(
            "New admission deferred: prior project must quiesce safely. "
            + "; ".join(blocked)
            + ". Pause intents were persisted; retry after the controller "
            "has settled. Do not force-close an active worker."
        )
    return tuple(held)
