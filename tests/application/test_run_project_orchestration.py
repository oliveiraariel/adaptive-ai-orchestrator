import threading
import time
from dataclasses import replace

from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.continuous_project_orchestration import (
    RunContinuousProjectOrchestration,
)
from application.run_project_orchestration import (
    ProjectOrchestrationRequest,
    ProjectRunStatus,
)
from application.runtime_project_planner import ProjectPlanningRequest
from domain.execution_policy import ExecutionPolicy
from domain.project_execution_plan import (
    PlannedDependency,
    PlannedWorkUnit,
    ProjectExecutionPlan,
)
from domain.task_package import TaskPackage
from infrastructure.claim_registry import InMemoryClaimRegistry


class StaticPlanner:
    def __init__(
        self,
        plan: ProjectExecutionPlan,
        revised_plan: ProjectExecutionPlan | None = None,
    ) -> None:
        self._plan = plan
        self._revised_plan = revised_plan
        self.replan_calls = 0

    def plan(self, request: ProjectPlanningRequest) -> ProjectExecutionPlan:
        return self._plan

    def replan(
        self,
        request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        state_summary: str,
    ) -> ProjectExecutionPlan:
        self.replan_calls += 1
        return self._revised_plan or current_plan


class ConcurrentRuntime:
    def __init__(
        self,
        outputs: dict[str, str] | None = None,
        fail_once: set[str] | None = None,
        failures_before_success: dict[str, int] | None = None,
        delays: dict[str, float] | None = None,
    ) -> None:
        self.outputs = outputs or {}
        self.fail_once = set(fail_once or ())
        self.failures_before_success = dict(failures_before_success or {})
        for work_unit_id in self.fail_once:
            self.failures_before_success.setdefault(work_unit_id, 1)
        self.delays = dict(delays or {})
        self.failed_counts: dict[str, int] = {}
        self.tasks: list[TaskPackage] = []
        self._tasks_by_execution: dict[str, TaskPackage] = {}
        self._lock = threading.Lock()
        self.active_retrievals = 0
        self.max_active_retrievals = 0
        self.started_at: dict[str, float] = {}
        self.finished_at: dict[str, float] = {}

    def submit(self, task: TaskPackage) -> ExecutionReference:
        execution_id = f"execution:{task.task_id}"
        with self._lock:
            self.tasks.append(task)
            self._tasks_by_execution[execution_id] = task
        return ExecutionReference(
            id=execution_id,
            runtime="fake",
            external_id=execution_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return AgentRuntimeStatus.COMPLETED

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        task = self._tasks_by_execution[execution.id]
        work_unit_id = task.work_unit_id
        with self._lock:
            self.started_at.setdefault(work_unit_id, time.monotonic())
            failures = self.failed_counts.get(work_unit_id, 0)
            failure_limit = self.failures_before_success.get(work_unit_id, 0)
            if failures < failure_limit:
                self.failed_counts[work_unit_id] = failures + 1
                raise RuntimeError(f"transient:{work_unit_id}:{failures + 1}")
            self.active_retrievals += 1
            self.max_active_retrievals = max(
                self.max_active_retrievals,
                self.active_retrievals,
            )
        time.sleep(self.delays.get(work_unit_id, 0.02))
        with self._lock:
            self.active_retrievals -= 1
            self.finished_at[work_unit_id] = time.monotonic()
        completed = replace(execution, status=AgentRuntimeStatus.COMPLETED)
        return AgentRuntimeResult(
            execution=completed,
            raw_result={"output": self.outputs.get(work_unit_id, f"done:{work_unit_id}")},
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return replace(execution, status=AgentRuntimeStatus.CANCELLED)


def wu(
    unit_id: str,
    *,
    role: str = "worker",
    side_effects: tuple[str, ...] = (),
    write_paths: tuple[str, ...] = (),
    parallel_safe: bool = True,
    kind: str = "EXECUTION",
    priority: int = 10,
) -> PlannedWorkUnit:
    from domain.work_unit import WorkUnitKind

    return PlannedWorkUnit(
        id=unit_id,
        objective=f"Execute {unit_id}",
        role=role,
        kind=WorkUnitKind(kind),
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
        requested_side_effects=side_effects,
        write_paths=write_paths,
        parallel_safe=parallel_safe,
        priority=priority,
    )


def run(
    plan: ProjectExecutionPlan,
    runtime: ConcurrentRuntime,
    *,
    max_concurrency: int = 4,
    policy: ExecutionPolicy | None = None,
    planner: StaticPlanner | None = None,
    max_attempts: int = 2,
    max_replans: int = 2,
):
    actual_planner = planner or StaticPlanner(plan)
    result = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=actual_planner,
        skill_profiles=(),
    ).execute(
        ProjectOrchestrationRequest(
            objective="Execute test project",
            max_concurrency=max_concurrency,
            execution_policy=policy or ExecutionPolicy(),
            max_attempts_per_work_unit=max_attempts,
            max_replans=max_replans,
            plan=plan,
        )
    )
    return result, actual_planner


def test_contract_unlocks_parallel_backend_frontend_then_fan_in() -> None:
    plan = ProjectExecutionPlan(
        summary="contract then lateral implementation then integration",
        work_units=(
            wu("contract", role="architecture", priority=30),
            wu("backend", role="backend", priority=20),
            wu("frontend", role="frontend", priority=20),
            wu("integration", role="integration", priority=10),
        ),
        dependencies=(
            PlannedDependency("contract", "backend"),
            PlannedDependency("contract", "frontend"),
            PlannedDependency("backend", "integration"),
            PlannedDependency("frontend", "integration"),
        ),
    )
    runtime = ConcurrentRuntime(
        outputs={
            "contract": "API_CONTRACT_READY",
            "backend": "BACKEND_READY",
            "frontend": "FRONTEND_READY",
            "integration": "INTEGRATED",
        }
    )

    result, _ = run(plan, runtime, max_concurrency=4)

    assert result.status is ProjectRunStatus.COMPLETED
    assert [generation.selected_work_unit_ids for generation in result.waves] == [
        ("contract",),
        ("backend", "frontend"),
        ("integration",),
    ]
    assert result.max_parallelism_observed == 2
    assert runtime.max_active_retrievals >= 2

    integration_task = next(
        task for task in runtime.tasks if task.work_unit_id == "integration"
    )
    context = "\n".join(integration_task.context)
    assert "BACKEND_READY" in context
    assert "FRONTEND_READY" in context


def test_freed_slot_is_replenished_before_unrelated_worker_finishes() -> None:
    plan = ProjectExecutionPlan(
        summary="continuous lateral frontier",
        work_units=(
            wu("fast-contract", priority=30),
            wu("long-backend", role="backend", priority=20),
            wu("frontend-after-contract", role="frontend", priority=10),
        ),
        dependencies=(
            PlannedDependency("fast-contract", "frontend-after-contract"),
        ),
    )
    runtime = ConcurrentRuntime(
        delays={
            "fast-contract": 0.01,
            "long-backend": 0.15,
            "frontend-after-contract": 0.01,
        }
    )

    result, _ = run(plan, runtime, max_concurrency=2)

    assert result.status is ProjectRunStatus.COMPLETED
    assert result.max_parallelism_observed == 2
    assert (
        runtime.started_at["frontend-after-contract"]
        < runtime.finished_at["long-backend"]
    )


def test_six_independent_units_scale_to_six_parallel_workers() -> None:
    plan = ProjectExecutionPlan(
        summary="six independent read-only workers",
        work_units=tuple(wu(f"worker-{index}") for index in range(6)),
    )
    runtime = ConcurrentRuntime()

    result, _ = run(plan, runtime, max_concurrency=6)

    assert result.status is ProjectRunStatus.COMPLETED
    assert result.max_parallelism_observed == 6
    assert runtime.max_active_retrievals >= 2
    assert len(result.waves) == 1


def test_overlapping_write_scopes_are_serialized() -> None:
    plan = ProjectExecutionPlan(
        summary="shared workspace write safety",
        work_units=(
            wu(
                "backend-a",
                side_effects=("filesystem.write",),
                write_paths=("src/backend",),
            ),
            wu(
                "backend-b",
                side_effects=("filesystem.write",),
                write_paths=("src/backend/controllers",),
            ),
        ),
    )
    runtime = ConcurrentRuntime()
    policy = ExecutionPolicy(allowed_side_effects=("filesystem.write",))

    result, _ = run(plan, runtime, max_concurrency=4, policy=policy)

    assert result.status is ProjectRunStatus.COMPLETED
    assert result.max_parallelism_observed == 1
    assert len(result.waves) == 2
    assert result.waves[0].conflict_deferred_ids


def test_disjoint_frontend_backend_write_scopes_can_run_in_parallel() -> None:
    plan = ProjectExecutionPlan(
        summary="disjoint shared workspace writes",
        work_units=(
            wu(
                "backend",
                role="backend",
                side_effects=("filesystem.write",),
                write_paths=("plugin/src",),
            ),
            wu(
                "frontend",
                role="frontend",
                side_effects=("filesystem.write",),
                write_paths=("theme/assets",),
            ),
        ),
    )
    runtime = ConcurrentRuntime()
    policy = ExecutionPolicy(allowed_side_effects=("filesystem.write",))

    result, _ = run(plan, runtime, max_concurrency=4, policy=policy)

    assert result.status is ProjectRunStatus.COMPLETED
    assert result.max_parallelism_observed == 2
    assert len(result.waves) == 1


def test_write_side_effect_is_blocked_before_runtime_without_authorization() -> None:
    plan = ProjectExecutionPlan(
        summary="policy gate",
        work_units=(
            wu(
                "writer",
                side_effects=("filesystem.write",),
                write_paths=("src",),
            ),
        ),
    )
    runtime = ConcurrentRuntime()

    result, _ = run(plan, runtime)

    assert result.status is ProjectRunStatus.BLOCKED
    assert result.blocked_work_unit_ids == ("writer",)
    assert runtime.tasks == []


def test_transient_result_failure_retries_then_completes() -> None:
    plan = ProjectExecutionPlan(
        summary="retry",
        work_units=(wu("flaky"),),
    )
    runtime = ConcurrentRuntime(fail_once={"flaky"})

    result, _ = run(plan, runtime, max_attempts=2)

    assert result.status is ProjectRunStatus.COMPLETED
    assert len([task for task in runtime.tasks if task.work_unit_id == "flaky"]) == 2
    assert any(record.status == "REVISION_REQUIRED" for record in result.records)


def test_retry_execution_ids_remain_unique_beyond_second_attempt() -> None:
    plan = ProjectExecutionPlan(
        summary="unique retry idempotency",
        work_units=(wu("twice-flaky"),),
    )
    runtime = ConcurrentRuntime(failures_before_success={"twice-flaky": 2})

    result, _ = run(plan, runtime, max_attempts=3)

    assert result.status is ProjectRunStatus.COMPLETED
    task_ids = [
        task.task_id for task in runtime.tasks if task.work_unit_id == "twice-flaky"
    ]
    assert len(task_ids) == 3
    assert len(set(task_ids)) == 3


def test_human_action_is_not_delegated_to_runtime() -> None:
    plan = ProjectExecutionPlan(
        summary="human boundary",
        work_units=(wu("approval", kind="HUMAN_ACTION"),),
    )
    runtime = ConcurrentRuntime()

    result, _ = run(plan, runtime)

    assert result.status is ProjectRunStatus.BLOCKED
    assert result.blocked_work_unit_ids == ("approval",)
    assert runtime.tasks == []


def test_replan_signal_adds_new_required_work_then_resumes_frontier() -> None:
    initial = ProjectExecutionPlan(
        summary="initial",
        work_units=(wu("discover"),),
    )
    revised = ProjectExecutionPlan(
        summary="expanded",
        work_units=(wu("discover"), wu("necessary-followup")),
        dependencies=(PlannedDependency("discover", "necessary-followup"),),
    )
    planner = StaticPlanner(initial, revised_plan=revised)
    runtime = ConcurrentRuntime(
        outputs={
            "discover": "ADAPTIVE_REPLAN_REQUIRED: necessary follow-up discovered",
            "necessary-followup": "FOLLOWUP_DONE",
        }
    )

    result, actual_planner = run(initial, runtime, planner=planner)

    assert result.status is ProjectRunStatus.COMPLETED
    assert result.replan_count == 1
    assert actual_planner.replan_calls == 1
    assert result.completed_work_unit_ids == ("discover", "necessary-followup")

def test_worker_partial_footer_cannot_complete_and_trips_attempt_circuit_breaker() -> None:
    plan = ProjectExecutionPlan(
        summary="partial completion must remain open",
        work_units=(wu("partial-worker"),),
    )
    runtime = ConcurrentRuntime(
        outputs={
            "partial-worker": (
                "Implemented only one requested item.\n"
                "ADAPTIVE_WORK_STATUS: PARTIAL\n"
                "ADAPTIVE_BLOCKER_TYPE: NONE\n"
                "ADAPTIVE_UNMET_CRITERIA: remaining acceptance item"
            ),
        }
    )

    result, _ = run(plan, runtime, max_attempts=1)

    assert result.status is ProjectRunStatus.BLOCKED
    assert result.completed_work_unit_ids == ()
    assert result.blocked_work_unit_ids == ("partial-worker",)
    assert result.records[-1].verdict == "RETURNED"
    assert result.records[-1].reason == "circuit-breaker:max-attempts:worker-partial"


def test_worker_genuine_human_blocker_stops_without_false_completion() -> None:
    plan = ProjectExecutionPlan(
        summary="human decision blocker",
        work_units=(wu("decision-boundary"),),
    )
    runtime = ConcurrentRuntime(
        outputs={
            "decision-boundary": (
                "Need an irreversible business decision.\n"
                "ADAPTIVE_WORK_STATUS: BLOCKED\n"
                "ADAPTIVE_BLOCKER_TYPE: HUMAN_DECISION\n"
                "ADAPTIVE_UNMET_CRITERIA: choose deletion semantics"
            ),
        }
    )

    result, _ = run(plan, runtime, max_attempts=2)

    assert result.status is ProjectRunStatus.BLOCKED
    assert result.completed_work_unit_ids == ()
    assert len(runtime.tasks) == 1
    assert result.records[-1].verdict == "BLOCKED"
    assert result.records[-1].reason == "worker-blocked:HUMAN_DECISION"


def test_unsubstantiated_worker_blocker_is_retried_then_circuit_broken() -> None:
    plan = ProjectExecutionPlan(
        summary="implementation difficulty is not blocker",
        work_units=(wu("implementation-worker"),),
    )
    runtime = ConcurrentRuntime(
        outputs={
            "implementation-worker": (
                "A repository dependency must be wired.\n"
                "ADAPTIVE_WORK_STATUS: BLOCKED\n"
                "ADAPTIVE_BLOCKER_TYPE: IMPLEMENTATION\n"
                "ADAPTIVE_UNMET_CRITERIA: add repository wiring"
            ),
        }
    )

    result, _ = run(plan, runtime, max_attempts=2)

    assert result.status is ProjectRunStatus.BLOCKED
    assert len(runtime.tasks) == 2
    assert result.records[0].status == "REVISION_REQUIRED"
    assert result.records[0].reason == "worker-blocker-unsubstantiated"
    assert result.records[-1].reason == (
        "circuit-breaker:max-attempts:worker-blocker-unsubstantiated"
    )


def test_worker_assignment_requires_structured_completion_footer() -> None:
    plan = ProjectExecutionPlan(
        summary="completion footer contract",
        work_units=(wu("footer-worker"),),
    )
    runtime = ConcurrentRuntime(
        outputs={
            "footer-worker": (
                "done\n"
                "ADAPTIVE_WORK_STATUS: COMPLETE\n"
                "ADAPTIVE_BLOCKER_TYPE: NONE\n"
                "ADAPTIVE_UNMET_CRITERIA: NONE"
            ),
        }
    )

    result, _ = run(plan, runtime, max_attempts=1)

    assert result.status is ProjectRunStatus.COMPLETED
    task = next(task for task in runtime.tasks if task.work_unit_id == "footer-worker")
    constraints = "\n".join(task.constraints)
    assert "ADAPTIVE_WORK_STATUS: COMPLETE|PARTIAL|BLOCKED" in constraints
    assert "Missing implementation, wiring, tests" in constraints
