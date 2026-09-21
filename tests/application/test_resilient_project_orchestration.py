from __future__ import annotations

import time

import pytest

from adaptive_orchestrator.resilient_project_orchestration import (
    RunResilientProjectOrchestration,
    SupervisedAgentRuntime,
)
from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.execution_liveness import ExecutionLivenessTimeout
from application.run_project_orchestration import (
    ProjectOrchestrationResult,
    ProjectRunStatus,
)
from infrastructure.claim_registry import InMemoryClaimRegistry


class MemoryObservability:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event_type: str, **fields) -> None:
        self.events.append((event_type, fields))


class SlowRuntime:
    def __init__(self, *, result_delay: float, status: AgentRuntimeStatus = AgentRuntimeStatus.RUNNING) -> None:
        self.result_delay = result_delay
        self.status = status
        self.status_calls = 0
        self.cancel_calls = 0

    def submit(self, task):  # pragma: no cover - not needed by these focused tests
        raise AssertionError("not used")

    def recover_execution(self, external_id):  # pragma: no cover - not used
        raise AssertionError("not used")

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        self.status_calls += 1
        return self.status

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        time.sleep(self.result_delay)
        completed = ExecutionReference(
            id=execution.id,
            runtime=execution.runtime,
            external_id=execution.external_id,
            status=AgentRuntimeStatus.COMPLETED,
        )
        return AgentRuntimeResult(execution=completed, raw_result={"output": "done"})

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        self.cancel_calls += 1
        return ExecutionReference(
            id=execution.id,
            runtime=execution.runtime,
            external_id=execution.external_id,
            status=AgentRuntimeStatus.CANCELLED,
        )


def execution() -> ExecutionReference:
    return ExecutionReference(
        id="execution-1",
        runtime="fake",
        external_id="external-1",
        status=AgentRuntimeStatus.SUBMITTED,
    )


def test_project_runtime_emits_heartbeat_while_result_is_pending(tmp_path) -> None:
    sink = MemoryObservability()
    runtime = SlowRuntime(result_delay=0.045)
    supervised = SupervisedAgentRuntime(
        runtime,
        project_root=tmp_path,
        observability=sink,
        heartbeat_interval_seconds=0.01,
        liveness_timeout_seconds=0.03,
        hard_deadline_seconds=0.20,
    )
    supervised.prebind_external_context(
        external_id="external-1",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
    )

    result = supervised.retrieve_result(execution())

    assert result.execution.status is AgentRuntimeStatus.COMPLETED
    heartbeats = [fields for event, fields in sink.events if event == "worker_heartbeat"]
    assert any(item["status"] == "RUNNING" for item in heartbeats)
    assert heartbeats[-1]["status"] == "COMPLETED"
    assert runtime.status_calls >= 1
    assert runtime.cancel_calls == 0


def test_project_runtime_hard_deadline_cancels_stale_run_and_returns_control(tmp_path) -> None:
    sink = MemoryObservability()
    runtime = SlowRuntime(result_delay=0.30)
    supervised = SupervisedAgentRuntime(
        runtime,
        project_root=tmp_path,
        observability=sink,
        heartbeat_interval_seconds=0.01,
        liveness_timeout_seconds=0.02,
        hard_deadline_seconds=0.04,
    )
    supervised.prebind_external_context(
        external_id="external-1",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
    )

    started = time.monotonic()
    with pytest.raises(ExecutionLivenessTimeout, match="bounded recovery"):
        supervised.retrieve_result(execution())
    elapsed = time.monotonic() - started

    assert elapsed < 0.20
    assert runtime.cancel_calls == 1
    timeout_events = [fields for event, fields in sink.events if event == "worker_liveness_timeout"]
    assert timeout_events
    assert timeout_events[-1]["action"] == "CANCEL_REQUESTED"


class MemoryCheckpointStore:
    def __init__(self, project_root, state: dict) -> None:
        self.project_root = project_root
        self.state = state
        self.saved: list[dict] = []

    def load(self, orchestration_id: str) -> dict:
        return self.state

    def save(self, orchestration_id: str, payload: dict) -> None:
        self.state = payload
        self.saved.append(payload)


class NoopRuntime:
    def submit(self, task):  # pragma: no cover
        raise AssertionError("not used")

    def recover_execution(self, external_id):  # pragma: no cover
        raise AssertionError("not used")

    def get_status(self, execution):  # pragma: no cover
        raise AssertionError("not used")

    def retrieve_result(self, execution):  # pragma: no cover
        raise AssertionError("not used")

    def cancel(self, execution):  # pragma: no cover
        raise AssertionError("not used")


class NoopPlanner:
    pass


def test_unfinished_work_is_terminally_blocked_after_bounded_recovery(tmp_path) -> None:
    checkpoint = {
        "work_unit_states": {
            "wu-done": "COMPLETED",
            "wu-review": "RECOVERY_REQUIRED",
            "wu-pack": "PLANNED",
        },
        "attempts": {"wu-done": 1, "wu-review": 2, "wu-pack": 0},
        "strategy_generations": {"wu-done": 1, "wu-review": 2, "wu-pack": 1},
        "records": [],
        "dispatch_generation": 6,
        "pending_replan": False,
        "active_executions": [],
        "terminal": True,
        "plan": {
            "work_units": [
                {"id": "wu-done", "role": "implementation", "requested_skills": ["implementation"]},
                {"id": "wu-review", "role": "review", "requested_skills": ["code-review"]},
                {"id": "wu-pack", "role": "packaging", "requested_skills": ["testing"]},
            ]
        },
    }
    store = MemoryCheckpointStore(tmp_path, checkpoint)
    sink = MemoryObservability()
    runner = RunResilientProjectOrchestration(
        runtime=NoopRuntime(),
        claim_registry=InMemoryClaimRegistry(),
        planner=NoopPlanner(),
        skill_profiles=(),
        checkpoint_store=store,
    )
    result = ProjectOrchestrationResult(
        orchestration_id="orch-1",
        status=ProjectRunStatus.RECOVERY_REQUIRED,
        plan_summary="test",
        work_unit_count=3,
        completed_work_unit_ids=("wu-done",),
        blocked_work_unit_ids=(),
        unfinished_work_unit_ids=("wu-pack", "wu-review"),
        records=(),
        waves=(),
        max_parallelism_observed=1,
        replan_count=2,
        recovery_required_work_unit_ids=("wu-review",),
    )

    finalized = runner._terminalize_unfinished(result, sink)

    assert finalized.status is ProjectRunStatus.PARTIAL
    assert finalized.unfinished_work_unit_ids == ()
    assert finalized.recovery_required_work_unit_ids == ()
    assert finalized.blocked_work_unit_ids == ("wu-pack", "wu-review")
    assert store.state["terminal"] is True
    assert store.state["pending_replan"] is False
    assert store.state["active_executions"] == []
    assert store.state["work_unit_states"]["wu-review"] == "BLOCKED"
    assert store.state["work_unit_states"]["wu-pack"] == "BLOCKED"
    assert any(
        row["reason"].startswith("auto-recovery-exhausted")
        for row in store.state["records"]
        if row["work_unit_id"] == "wu-review"
    )
    assert any(event == "orchestration_terminalized" for event, _ in sink.events)
    assert sink.events[-1][0] == "orchestration_completed"



def test_persistent_recovery_yield_is_not_terminalized(tmp_path) -> None:
    checkpoint = {
        "work_unit_states": {
            "wu-review": "RECOVERY_REQUIRED",
        },
        "attempts": {"wu-review": 2},
        "strategy_generations": {"wu-review": 2},
        "records": [],
        "dispatch_generation": 6,
        "pending_replan": True,
        "active_executions": [],
        "terminal": False,
        "request": {"persistent_recovery": True},
        "plan": {
            "work_units": [
                {
                    "id": "wu-review",
                    "role": "review",
                    "requested_skills": ["code-review"],
                },
            ]
        },
    }
    store = MemoryCheckpointStore(tmp_path, checkpoint)
    sink = MemoryObservability()
    runner = RunResilientProjectOrchestration(
        runtime=NoopRuntime(),
        claim_registry=InMemoryClaimRegistry(),
        planner=NoopPlanner(),
        skill_profiles=(),
        checkpoint_store=store,
    )
    result = ProjectOrchestrationResult(
        orchestration_id="orch-recovery-yield",
        status=ProjectRunStatus.RECOVERY_REQUIRED,
        plan_summary="yield for next supervised recovery epoch",
        work_unit_count=1,
        completed_work_unit_ids=(),
        blocked_work_unit_ids=(),
        unfinished_work_unit_ids=("wu-review",),
        records=(),
        waves=(),
        max_parallelism_observed=0,
        replan_count=3,
        recovery_required_work_unit_ids=("wu-review",),
    )

    preserved = runner._terminalize_unfinished(result, sink)

    assert preserved is result
    assert store.state["terminal"] is False
    assert store.state["pending_replan"] is True
    assert store.state["work_unit_states"]["wu-review"] == "RECOVERY_REQUIRED"
    assert store.saved == []
    assert not any(event == "orchestration_terminalized" for event, _ in sink.events)
