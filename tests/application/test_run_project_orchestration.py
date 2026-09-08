import threading
import time
from dataclasses import replace

from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.run_project_orchestration import (
    ProjectOrchestrationRequest,
    ProjectRunStatus,
    RunProjectOrchestration,
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
    ) -> None:
        self.outputs = outputs or {}
        self.fail_once = set(fail_once or ())
        self.failed_once: set[str] = set()
        self.tasks: list[TaskPackage] = []
        self._tasks_by_execution: dict[str, TaskPackage] = {}
        self._lock = threading.Lock()
        self.active_retrievals = 0
        self.max_active_retrievals = 0

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
            if work_unit_id in self.fail_once and work_unit_id not in self.failed_once:
                self.failed_once.add(work_unit_id)
                raise RuntimeError(f"transient:{work_unit_id}")
            self.active_retrievals += 1
            self.max_active_retrievals = max(
                self.max_active_retrievals,
                self.active_retrievals,
            )
        time.sleep(0.02)
        with self._lock:
            self.active_retrievals -= 1
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
):
    actual_planner = planner or StaticPlanner(plan)
    result = RunProjectOrchestration(
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
    assert [wave.selected_work_unit_ids for wave in result.waves] == [
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
