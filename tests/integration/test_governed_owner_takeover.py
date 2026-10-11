from __future__ import annotations

import threading
import time
from dataclasses import replace

from application.agent_runtime import AgentRuntimeResult, AgentRuntimeStatus, ExecutionReference
from application.continuous_project_orchestration import RunContinuousProjectOrchestration
from application.governed_takeover import GovernedTakeoverStore
from application.run_project_orchestration import (
    ProjectOrchestrationRequest, ProjectRunStatus, RecoveryLoopMode,
)
from domain.project_execution_plan import PlannedWorkUnit, ProjectExecutionPlan
from domain.work_unit import WorkUnitKind
from infrastructure.claim_registry import InMemoryClaimRegistry
from infrastructure.project_orchestration_checkpoint import FileProjectOrchestrationCheckpointStore


class Plan:
    def plan(self, request):
        return ProjectExecutionPlan(
            summary="Governed ownership transfer",
            work_units=(
                PlannedWorkUnit(
                    id="wu-1", objective="Finish the pending review",
                    role="review", kind=WorkUnitKind.EXECUTION,
                    acceptance_criteria=("runtime-completed",),
                    expected_output=("review finished",),
                ),
            ),
        )


class Runtime:
    def __init__(self):
        self.started = threading.Event()
        self.cancelled = threading.Event()
        self.completed = threading.Event()
        self.tasks = []
        self.states = {}
        self.lock = threading.Lock()

    def submit(self, task):
        with self.lock:
            self.tasks.append(task)
            index = len(self.tasks)
        external_id = f"external-{index}"
        self.states[external_id] = AgentRuntimeStatus.RUNNING
        if index == 1:
            self.started.set()
        return ExecutionReference(
            id=f"execution-{index}", runtime="fake", external_id=external_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def recover_execution(self, external_id):
        raise AssertionError("no recovery expected in one live controller")

    def get_status(self, execution):
        return self.states[execution.external_id]

    def cancel(self, execution):
        self.states[execution.external_id] = AgentRuntimeStatus.CANCELLED
        self.cancelled.set()
        return replace(execution, status=AgentRuntimeStatus.CANCELLED)

    def retrieve_result(self, execution):
        if execution.external_id == "external-1":
            if not self.cancelled.wait(timeout=6):
                raise AssertionError("controller failed to cancel old executor")
            raise RuntimeError("old executor terminated")
        self.states[execution.external_id] = AgentRuntimeStatus.COMPLETED
        self.completed.set()
        return AgentRuntimeResult(
            execution=replace(execution, status=AgentRuntimeStatus.COMPLETED),
            raw_result={
                "output": (
                    "Work Unit reviewed.\nADAPTIVE_WORK_STATUS: COMPLETE\n"
                    "ADAPTIVE_BLOCKER_TYPE: NONE\nADAPTIVE_UNMET_CRITERIA: NONE"
                )
            },
        )


def test_user_takeover_aborts_old_attempt_and_owner_completes_same_wu(tmp_path):
    runtime = Runtime()
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    takeover = GovernedTakeoverStore(project_root=tmp_path)
    runner = RunContinuousProjectOrchestration(
        runtime=runtime, claim_registry=InMemoryClaimRegistry(),
        planner=Plan(), skill_profiles=(), checkpoint_store=store,
    )
    request = ProjectOrchestrationRequest(
        objective="Finish review of original project",
        orchestration_id="orch-1",
        agent="delegated-worker",
        planner_agent="coordinator",
        worker_observation_interval_seconds=1,
        max_concurrency=1, max_waves=3,
        recovery_loop_mode=RecoveryLoopMode.DISABLED,
        acceptance_mode="STRICT" if False else __import__(
            "application.run_project_orchestration", fromlist=["AcceptanceMode"]
        ).AcceptanceMode.STRICT,
    )
    result = []
    error = []

    def execute():
        try:
            result.append(runner.execute(request))
        except Exception as exc:
            error.append(exc)

    thread = threading.Thread(target=execute, daemon=True)
    thread.start()
    assert runtime.started.wait(timeout=6)
    row = takeover.request(
        orchestration_id="orch-1", work_unit_id="wu-1",
        mode="direct", actor="user", owner_agent="coordinator",
        reason="User observed stalled review; direct fallback is preferable.",
    )
    assert row["state"] == "REQUESTED"
    thread.join(timeout=10)
    assert not thread.is_alive(), "governed takeover must not hang the controller"
    assert not error, str(error)
    assert runtime.cancelled.is_set()
    assert runtime.completed.is_set()
    assert len(runtime.tasks) == 2
    assert runtime.tasks[0].configuration.agent == "delegated-worker"
    assert runtime.tasks[1].configuration.agent == "coordinator"
    assert runtime.tasks[1].work_unit_id == runtime.tasks[0].work_unit_id
    assert result[0].status is ProjectRunStatus.COMPLETED
    assert takeover.current("orch-1", "wu-1")["state"] == "COMPLETED"
    records = store.load("orch-1")["records"]
    assert any("governed-takeover" in row["reason"] for row in records)
