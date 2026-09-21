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


class SequencedReplanPlanner(StaticPlanner):
    def __init__(
        self,
        plan: ProjectExecutionPlan,
        revised_plans: list[ProjectExecutionPlan],
    ) -> None:
        super().__init__(plan)
        self._revised_plans = list(revised_plans)
        self.state_summaries: list[str] = []

    def replan(
        self,
        request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        state_summary: str,
    ) -> ProjectExecutionPlan:
        self.replan_calls += 1
        self.state_summaries.append(state_summary)
        index = min(self.replan_calls - 1, len(self._revised_plans) - 1)
        return self._revised_plans[index]


class ConcurrentRuntime:
    def __init__(
        self,
        outputs: dict[str, str] | None = None,
        fail_once: set[str] | None = None,
        failures_before_success: dict[str, int] | None = None,
        delays: dict[str, float] | None = None,
        result_refs: dict[str, str] | None = None,
    ) -> None:
        self.outputs = outputs or {}
        self.result_refs = result_refs or {}
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
        raw_result = {"output": self.outputs.get(work_unit_id, f"done:{work_unit_id}")}
        result_ref = self.result_refs.get(work_unit_id)
        if result_ref:
            raw_result["result_transport"] = {
                "source": "adaptive-result-store",
                "authoritative": True,
                "complete": True,
                "result_ref": result_ref,
                "result_bytes": len(raw_result["output"].encode("utf-8")),
            }
        return AgentRuntimeResult(
            execution=completed,
            raw_result=raw_result,
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return replace(execution, status=AgentRuntimeStatus.CANCELLED)


class SequencedOutputRuntime(ConcurrentRuntime):
    def __init__(self, sequences: dict[str, list[str]]) -> None:
        super().__init__()
        self.sequences = {key: list(value) for key, value in sequences.items()}
        self.calls: dict[str, int] = {}

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        task = self._tasks_by_execution[execution.id]
        work_unit_id = task.work_unit_id
        index = self.calls.get(work_unit_id, 0)
        self.calls[work_unit_id] = index + 1
        sequence = self.sequences[work_unit_id]
        output = sequence[min(index, len(sequence) - 1)]
        completed = replace(execution, status=AgentRuntimeStatus.COMPLETED)
        return AgentRuntimeResult(
            execution=completed,
            raw_result={"output": output},
        )


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
    max_strategies: int = 2,
    max_replans: int = 2,
    max_waves: int = 24,
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
            max_strategies_per_work_unit=max_strategies,
            max_replans=max_replans,
            max_waves=max_waves,
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


def test_authoritative_dependency_results_are_fanned_in_by_reference_not_inline() -> None:
    plan = ProjectExecutionPlan(
        summary="large worker artifact then dependent integration",
        work_units=(
            wu("producer", role="backend", priority=20),
            wu("consumer", role="integration", priority=10),
        ),
        dependencies=(PlannedDependency("producer", "consumer"),),
    )
    large_payload = "RESULT_BEGIN\n" + ("payload-line-" * 1500) + "\nRESULT_END"
    manifest = "/tmp/project/.adaptive/runs/orch/producer/exec/manifest.json"
    runtime = ConcurrentRuntime(
        outputs={
            "producer": large_payload,
            "consumer": "CONSUMED_BY_REFERENCE",
        },
        result_refs={"producer": manifest},
    )

    result, _ = run(plan, runtime, max_concurrency=2)

    assert result.status is ProjectRunStatus.COMPLETED
    producer_record = next(
        record for record in result.records if record.work_unit_id == "producer"
    )
    assert producer_record.result_authoritative is True
    assert producer_record.result_ref == manifest

    consumer_task = next(
        task for task in runtime.tasks if task.work_unit_id == "consumer"
    )
    context = "\n".join(consumer_task.context)
    assert manifest in context
    assert "payload is intentionally not copied" in context
    assert "RESULT_BEGIN" not in context
    assert "RESULT_END" not in context
    assert large_payload not in context
    assert consumer_task.artifacts == (manifest,)


def test_non_authoritative_dependency_keeps_bounded_legacy_inline_fallback() -> None:
    plan = ProjectExecutionPlan(
        summary="legacy runtime compatibility",
        work_units=(wu("legacy"), wu("consumer")),
        dependencies=(PlannedDependency("legacy", "consumer"),),
    )
    large_payload = "LEGACY_BEGIN-" + ("x" * 9000) + "-LEGACY_END"
    runtime = ConcurrentRuntime(
        outputs={"legacy": large_payload, "consumer": "DONE"},
    )
    actual_planner = StaticPlanner(plan)
    result = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=actual_planner,
        skill_profiles=(),
    ).execute(
        ProjectOrchestrationRequest(
            objective="legacy fallback",
            max_concurrency=2,
            dependency_context_chars=512,
            plan=plan,
        )
    )

    assert result.status is ProjectRunStatus.COMPLETED
    consumer_task = next(
        task for task in runtime.tasks if task.work_unit_id == "consumer"
    )
    context = "\n".join(consumer_task.context)
    assert "Legacy inline dependency result from legacy" in context
    assert "[dependency output truncated]" in context
    assert "LEGACY_END" not in context
    assert consumer_task.artifacts == ()


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

def test_worker_partial_footer_exhausts_strategies_before_recovery_required() -> None:
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

    result, planner = run(
        plan,
        runtime,
        max_attempts=1,
        max_strategies=2,
        max_replans=1,
    )

    assert result.status is ProjectRunStatus.RECOVERY_REQUIRED
    assert result.completed_work_unit_ids == ()
    assert result.blocked_work_unit_ids == ()
    assert result.recovery_required_work_unit_ids == ("partial-worker",)
    assert len(runtime.tasks) == 2
    assert result.records[0].reason.startswith(
        "strategy-exhausted:1:replacement:2:worker-partial"
    )
    assert result.records[-1].verdict == "RETURNED"
    assert result.records[-1].status == "RECOVERY_REQUIRED"
    assert result.records[-1].reason.startswith(
        "recovery-required:strategies-exhausted:2:worker-partial"
    )
    assert planner.replan_calls == 1


def test_strategy_a_fails_twice_then_strategy_b_succeeds_and_unlocks_dependency() -> None:
    partial = (
        "Still incomplete.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: unresolved item"
    )
    complete = (
        "Recovered with a different approach.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    downstream = (
        "downstream complete\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    plan = ProjectExecutionPlan(
        summary="strategy replacement",
        work_units=(wu("worker"), wu("downstream")),
        dependencies=(PlannedDependency("worker", "downstream"),),
    )
    runtime = SequencedOutputRuntime(
        {
            "worker": [partial, partial, complete],
            "downstream": [downstream],
        }
    )

    result, _ = run(
        plan,
        runtime,
        max_attempts=2,
        max_strategies=2,
        max_replans=0,
    )

    assert result.status is ProjectRunStatus.COMPLETED
    worker_records = [
        record for record in result.records if record.work_unit_id == "worker"
    ]
    assert [record.strategy for record in worker_records] == [1, 1, 2]
    assert worker_records[1].reason.startswith(
        "strategy-exhausted:1:replacement:2:"
    )
    strategy_two_task = [
        task for task in runtime.tasks if task.work_unit_id == "worker"
    ][2]
    assert ":strategy:2:" in strategy_two_task.task_id
    assert "materially different" in "\n".join(strategy_two_task.context)
    assert result.completed_work_unit_ids == ("downstream", "worker")


def test_exhausted_strategies_trigger_recovery_planner_remediation_then_resume() -> None:
    partial = (
        "Security findings remain.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: SEC-01; SEC-02"
    )
    complete_review = (
        "Security review accepted after remediation.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    remediation_done = (
        "SEC-01 and SEC-02 remediated.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    fanin_done = (
        "fan-in accepted\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    initial = ProjectExecutionPlan(
        summary="security review then fan-in",
        work_units=(wu("security-review"), wu("fan-in")),
        dependencies=(PlannedDependency("security-review", "fan-in"),),
    )
    revised = ProjectExecutionPlan(
        summary="remediate security then re-review",
        work_units=(
            wu("security-review"),
            wu("fan-in"),
            wu("security-remediation"),
        ),
        dependencies=(
            PlannedDependency("security-review", "fan-in"),
            PlannedDependency("security-remediation", "security-review"),
        ),
    )
    planner = StaticPlanner(initial, revised_plan=revised)
    runtime = SequencedOutputRuntime(
        {
            "security-review": [
                partial,
                partial,
                partial,
                partial,
                complete_review,
            ],
            "security-remediation": [remediation_done],
            "fan-in": [fanin_done],
        }
    )

    result, actual_planner = run(
        initial,
        runtime,
        planner=planner,
        max_attempts=2,
        max_strategies=2,
        max_replans=2,
    )

    assert result.status is ProjectRunStatus.COMPLETED
    assert actual_planner.replan_calls == 1
    assert "security-remediation" in result.completed_work_unit_ids
    review_tasks = [
        task for task in runtime.tasks if task.work_unit_id == "security-review"
    ]
    assert len(review_tasks) == 5
    remediation_index = next(
        index
        for index, task in enumerate(runtime.tasks)
        if task.work_unit_id == "security-remediation"
    )
    final_review_index = max(
        index
        for index, task in enumerate(runtime.tasks)
        if task.work_unit_id == "security-review"
    )
    assert remediation_index < final_review_index
    assert result.completed_work_unit_ids == (
        "fan-in",
        "security-remediation",
        "security-review",
    )


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


def test_unsubstantiated_worker_blocker_exhausts_distinct_strategies() -> None:
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

    result, _ = run(
        plan,
        runtime,
        max_attempts=2,
        max_strategies=2,
        max_replans=0,
    )

    assert result.status is ProjectRunStatus.RECOVERY_REQUIRED
    assert len(runtime.tasks) == 4
    assert [record.strategy for record in result.records] == [1, 1, 2, 2]
    assert result.records[0].status == "REVISION_REQUIRED"
    assert result.records[0].reason == "worker-blocker-unsubstantiated"
    assert result.records[1].reason.startswith(
        "strategy-exhausted:1:replacement:2:"
    )
    assert result.records[-1].status == "RECOVERY_REQUIRED"
    assert result.records[-1].reason.startswith(
        "recovery-required:strategies-exhausted:2:"
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

class MemoryProjectCheckpointStore:
    def __init__(self, state: dict | None = None) -> None:
        self.state = state
        self.saves: list[dict] = []

    def load(self, orchestration_id: str):
        if self.state is None:
            return None
        if self.state.get("orchestration_id") != orchestration_id:
            return None
        return self.state

    def save(self, orchestration_id: str, payload: dict) -> None:
        assert payload["orchestration_id"] == orchestration_id
        self.state = payload
        self.saves.append(payload)


class RecoverableProjectRuntime:
    def __init__(self, *, wrong_recovery_identity: bool = False) -> None:
        self.submitted: list[str] = []
        self.recovered: list[str] = []
        self.retrieve_calls: list[str] = []
        self.tasks: dict[str, TaskPackage] = {}
        self.wrong_recovery_identity = wrong_recovery_identity

    def submit(self, task: TaskPackage) -> ExecutionReference:
        self.submitted.append(task.work_unit_id)
        execution = ExecutionReference(
            id=f"execution:{task.work_unit_id}",
            runtime="fake",
            external_id=f"external:{task.work_unit_id}",
            status=AgentRuntimeStatus.SUBMITTED,
        )
        self.tasks[execution.id] = task
        return execution

    def recover_execution(self, external_id: str) -> ExecutionReference:
        self.recovered.append(external_id)
        work_unit_id = external_id.split(":", 1)[-1]
        execution_id = (
            "execution:wrong"
            if self.wrong_recovery_identity
            else f"execution:{work_unit_id}"
        )
        return ExecutionReference(
            id=execution_id,
            runtime="fake",
            external_id=external_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return AgentRuntimeStatus.COMPLETED

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        self.retrieve_calls.append(execution.id)
        work_unit_id = execution.external_id.split(":", 1)[-1]
        output = (
            f"done:{work_unit_id}\n"
            "ADAPTIVE_WORK_STATUS: COMPLETE\n"
            "ADAPTIVE_BLOCKER_TYPE: NONE\n"
            "ADAPTIVE_UNMET_CRITERIA: NONE"
        )
        completed = replace(execution, status=AgentRuntimeStatus.COMPLETED)
        return AgentRuntimeResult(
            execution=completed,
            raw_result={
                "output": output,
                "result_transport": {
                    "source": "adaptive-result-store",
                    "authoritative": True,
                    "complete": True,
                    "result_ref": f"/results/{work_unit_id}/manifest.json",
                    "result_bytes": len(output.encode("utf-8")),
                },
            },
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return replace(execution, status=AgentRuntimeStatus.CANCELLED)


def _lost_controller_checkpoint(
    executor: RunContinuousProjectOrchestration,
    request: ProjectOrchestrationRequest,
    plan: ProjectExecutionPlan,
) -> dict:
    return {
        "orchestration_id": "orch-recovery",
        "request": executor._request_to_payload(request),
        "plan": executor._plan_to_payload(plan),
        "work_unit_states": {
            "producer": "RUNNING",
            "consumer": "PLANNED",
        },
        "dependency_states": [
            {
                "source_id": "producer",
                "target_id": "consumer",
                "required": True,
                "status": "BLOCKED",
            }
        ],
        "attempts": {"producer": 1, "consumer": 0},
        "outputs": {},
        "output_refs": {},
        "revision_feedback": {},
        "records": [],
        "dispatch_records": [
            {
                "wave": 1,
                "ready_work_unit_ids": ["producer"],
                "selected_work_unit_ids": ["producer"],
                "conflict_deferred_ids": [],
            }
        ],
        "max_parallelism_observed": 1,
        "replan_count": 0,
        "dispatch_generation": 1,
        "pending_replan": False,
        "active_executions": [
            {
                "work_unit_id": "producer",
                "generation": 1,
                "execution_id": "execution:producer",
                "external_id": "external:producer",
                "runtime": "fake",
            }
        ],
        "terminal": False,
    }


def test_execute_persists_admission_checkpoint_before_planner_runs() -> None:
    store = MemoryProjectCheckpointStore()
    plan = ProjectExecutionPlan(
        summary="unused after planner failure",
        work_units=(wu("only"),),
    )

    class InspectingPlanner(StaticPlanner):
        def plan(self, request: ProjectPlanningRequest) -> ProjectExecutionPlan:
            assert store.state is not None
            assert store.state["orchestration_id"] == "orch-admitted"
            assert store.state["phase"] == "ADMITTED"
            assert store.state["terminal"] is False
            assert "plan" not in store.state
            raise RuntimeError("planner interrupted after admission")

    executor = RunContinuousProjectOrchestration(
        runtime=ConcurrentRuntime(),
        claim_registry=InMemoryClaimRegistry(),
        planner=InspectingPlanner(plan),
        skill_profiles=(),
        checkpoint_store=store,
    )

    import pytest

    with pytest.raises(RuntimeError, match="planner interrupted after admission"):
        executor.execute(
            ProjectOrchestrationRequest(
                objective="persist admission first",
                orchestration_id="orch-admitted",
            )
        )

    assert store.state is not None
    assert store.state["phase"] == "ADMITTED"
    assert store.state["terminal"] is False
    assert len(store.saves) == 1


def test_resume_from_admission_checkpoint_replans_same_orchestration() -> None:
    store = MemoryProjectCheckpointStore()
    plan = ProjectExecutionPlan(
        summary="resume admitted project",
        work_units=(wu("only"),),
    )

    class FailingPlanner(StaticPlanner):
        def plan(self, request: ProjectPlanningRequest) -> ProjectExecutionPlan:
            raise RuntimeError("planner interrupted")

    first = RunContinuousProjectOrchestration(
        runtime=ConcurrentRuntime(),
        claim_registry=InMemoryClaimRegistry(),
        planner=FailingPlanner(plan),
        skill_profiles=(),
        checkpoint_store=store,
    )

    import pytest

    with pytest.raises(RuntimeError, match="planner interrupted"):
        first.execute(
            ProjectOrchestrationRequest(
                objective="resume me",
                orchestration_id="orch-admitted",
            )
        )

    runtime = ConcurrentRuntime(
        outputs={
            "only": (
                "done\n"
                "ADAPTIVE_WORK_STATUS: COMPLETE\n"
                "ADAPTIVE_BLOCKER_TYPE: NONE\n"
                "ADAPTIVE_UNMET_CRITERIA: NONE"
            )
        }
    )
    resumed = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=StaticPlanner(plan),
        skill_profiles=(),
        checkpoint_store=store,
    ).resume("orch-admitted")

    assert resumed.status is ProjectRunStatus.COMPLETED
    assert resumed.orchestration_id == "orch-admitted"
    assert [task.work_unit_id for task in runtime.tasks] == ["only"]
    assert store.state is not None
    assert store.state["phase"] == "EXECUTION"
    assert store.state["terminal"] is True
    assert len(store.saves) >= 3


def test_resume_reconciles_active_worker_then_continues_frontier_without_redispatch() -> None:
    plan = ProjectExecutionPlan(
        summary="recover producer then continue consumer",
        work_units=(wu("producer"), wu("consumer")),
        dependencies=(PlannedDependency("producer", "consumer"),),
    )
    request = ProjectOrchestrationRequest(
        objective="recover project",
        orchestration_id="orch-recovery",
        plan=plan,
        max_concurrency=2,
    )
    runtime = RecoverableProjectRuntime()
    store = MemoryProjectCheckpointStore()
    executor = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=StaticPlanner(plan),
        skill_profiles=(),
        checkpoint_store=store,
    )
    store.state = _lost_controller_checkpoint(executor, request, plan)

    result = executor.resume("orch-recovery")

    assert result.status is ProjectRunStatus.COMPLETED
    assert runtime.recovered == ["external:producer"]
    assert "producer" not in runtime.submitted
    assert runtime.submitted == ["consumer"]
    assert runtime.retrieve_calls.count("execution:producer") == 1
    producer = next(
        item for item in result.records if item.work_unit_id == "producer"
    )
    assert producer.verdict == "ACCEPTED"
    assert producer.result_authoritative is True
    assert result.completed_work_unit_ids == ("consumer", "producer")
    assert store.state["terminal"] is True
    assert store.state["active_executions"] == []

    submissions_before_second_resume = list(runtime.submitted)
    retrievals_before_second_resume = list(runtime.retrieve_calls)
    second = executor.resume("orch-recovery")

    assert second.status is ProjectRunStatus.COMPLETED
    assert runtime.submitted == submissions_before_second_resume
    assert runtime.retrieve_calls == retrievals_before_second_resume


def test_resume_fails_closed_when_recovered_execution_identity_mismatches() -> None:
    plan = ProjectExecutionPlan(
        summary="identity validation",
        work_units=(wu("producer"), wu("consumer")),
        dependencies=(PlannedDependency("producer", "consumer"),),
    )
    request = ProjectOrchestrationRequest(
        objective="recover project",
        orchestration_id="orch-recovery",
        plan=plan,
    )
    runtime = RecoverableProjectRuntime(wrong_recovery_identity=True)
    store = MemoryProjectCheckpointStore()
    executor = RunContinuousProjectOrchestration(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
        planner=StaticPlanner(plan),
        skill_profiles=(),
        checkpoint_store=store,
    )
    store.state = _lost_controller_checkpoint(executor, request, plan)

    import pytest

    with pytest.raises(
        Exception,
        match="execution identity mismatch",
    ):
        executor.resume("orch-recovery")

    assert runtime.submitted == []

def test_planning_scope_blocker_replans_before_retrying_original_work_unit() -> None:
    planning_block = (
        "The delegated frontend bootstrap write_paths do not exist in this repository.\n"
        "ADAPTIVE_REPLAN_REQUIRED: inspect the repository and repair the delegated scope\n"
        "ADAPTIVE_WORK_STATUS: BLOCKED\n"
        "ADAPTIVE_BLOCKER_TYPE: PLANNING\n"
        "ADAPTIVE_UNMET_CRITERIA: correct bootstrap write paths"
    )
    scope_fixed = (
        "Located the real plugin bootstrap paths and produced the corrected scope.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    bootstrap_done = (
        "Frontend bootstrap is now wired through the real plugin paths.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    fanin_done = (
        "verification complete\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    initial = ProjectExecutionPlan(
        summary="bootstrap then verification",
        work_units=(wu("bootstrap"), wu("verification")),
        dependencies=(PlannedDependency("bootstrap", "verification"),),
    )
    revised = ProjectExecutionPlan(
        summary="repair scope then bootstrap",
        work_units=(
            wu("bootstrap"),
            wu("verification"),
            wu("scope-repair"),
        ),
        dependencies=(
            PlannedDependency("bootstrap", "verification"),
            PlannedDependency("scope-repair", "bootstrap"),
        ),
    )
    planner = StaticPlanner(initial, revised_plan=revised)
    runtime = SequencedOutputRuntime(
        {
            "bootstrap": [planning_block, bootstrap_done],
            "scope-repair": [scope_fixed],
            "verification": [fanin_done],
        }
    )

    result, actual_planner = run(
        initial,
        runtime,
        planner=planner,
        max_attempts=2,
        max_strategies=2,
        max_replans=2,
    )

    assert result.status is ProjectRunStatus.COMPLETED
    assert actual_planner.replan_calls == 1
    bootstrap_records = [
        record for record in result.records if record.work_unit_id == "bootstrap"
    ]
    assert bootstrap_records[0].status == "RECOVERY_REQUIRED"
    assert bootstrap_records[0].reason == "recovery-required:planning"
    bootstrap_tasks = [
        task for task in runtime.tasks if task.work_unit_id == "bootstrap"
    ]
    assert len(bootstrap_tasks) == 2
    scope_index = next(
        index
        for index, task in enumerate(runtime.tasks)
        if task.work_unit_id == "scope-repair"
    )
    final_bootstrap_index = max(
        index
        for index, task in enumerate(runtime.tasks)
        if task.work_unit_id == "bootstrap"
    )
    assert scope_index < final_bootstrap_index
    assert result.completed_work_unit_ids == (
        "bootstrap",
        "scope-repair",
        "verification",
    )


def test_reversed_recovery_graph_is_rejected_then_replanned_with_correct_direction() -> None:
    partial = (
        "Frontend review still has unresolved findings.\n"
        "ADAPTIVE_WORK_STATUS: PARTIAL\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: auth gate; editor action"
    )
    complete_review = (
        "Frontend review accepted after remediation.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    remediation_done = (
        "Frontend findings remediated.\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )
    fanin_done = (
        "fan-in accepted\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE"
    )

    initial = ProjectExecutionPlan(
        summary="review then fan-in",
        work_units=(wu("review"), wu("fan-in")),
        dependencies=(PlannedDependency("review", "fan-in"),),
    )
    invalid_recovery = ProjectExecutionPlan(
        summary="incorrect recovery direction",
        work_units=(wu("review"), wu("fan-in"), wu("remediation")),
        dependencies=(
            PlannedDependency("review", "fan-in"),
            PlannedDependency("review", "remediation"),
        ),
    )
    valid_recovery = ProjectExecutionPlan(
        summary="correct recovery direction",
        work_units=(wu("review"), wu("fan-in"), wu("remediation")),
        dependencies=(
            PlannedDependency("review", "fan-in"),
            PlannedDependency("remediation", "review"),
        ),
    )
    planner = SequencedReplanPlanner(
        initial,
        [invalid_recovery, valid_recovery],
    )
    runtime = SequencedOutputRuntime(
        {
            "review": [partial, partial, partial, partial, complete_review],
            "remediation": [remediation_done],
            "fan-in": [fanin_done],
        }
    )

    result, actual_planner = run(
        initial,
        runtime,
        planner=planner,
        max_attempts=2,
        max_strategies=2,
        max_replans=2,
    )

    assert result.status is ProjectRunStatus.COMPLETED
    assert actual_planner.replan_calls == 2
    assert "Recovery dependency direction is invalid" in (
        actual_planner.state_summaries[1]
    )
    remediation_index = next(
        index
        for index, task in enumerate(runtime.tasks)
        if task.work_unit_id == "remediation"
    )
    final_review_index = max(
        index
        for index, task in enumerate(runtime.tasks)
        if task.work_unit_id == "review"
    )
    assert remediation_index < final_review_index
    assert result.completed_work_unit_ids == ("fan-in", "remediation", "review")


def test_genuine_environment_blocker_remains_terminal() -> None:
    plan = ProjectExecutionPlan(
        summary="external environment boundary",
        work_units=(wu("external-e2e"),),
    )
    runtime = ConcurrentRuntime(
        outputs={
            "external-e2e": (
                "A real external WordPress environment is required.\n"
                "ADAPTIVE_WORK_STATUS: BLOCKED\n"
                "ADAPTIVE_BLOCKER_TYPE: ENVIRONMENT\n"
                "ADAPTIVE_UNMET_CRITERIA: external WordPress runtime"
            )
        }
    )

    result, _ = run(plan, runtime)

    assert result.status is ProjectRunStatus.BLOCKED
    assert result.blocked_work_unit_ids == ("external-e2e",)
    assert result.recovery_required_work_unit_ids == ()



def test_dispatch_budget_scales_with_serial_graph_instead_of_stopping_early() -> None:
    plan = ProjectExecutionPlan(
        summary="serial graph larger than explicit base wave budget",
        work_units=tuple(wu(f"serial-{index}") for index in range(1, 7)),
    )
    runtime = ConcurrentRuntime(
        outputs={
            f"serial-{index}": f"done-{index}"
            for index in range(1, 7)
        }
    )

    result, _ = run(
        plan,
        runtime,
        max_concurrency=1,
        max_waves=1,
    )

    assert result.status is ProjectRunStatus.COMPLETED
    assert len(result.completed_work_unit_ids) == 6
    assert len(result.waves) == 6


def test_missing_skill_blocks_only_affected_work_unit_and_independent_work_continues() -> None:
    from domain.work_unit import WorkUnitKind

    missing_skill = PlannedWorkUnit(
        id="missing-skill",
        objective="Needs a capability that is not registered",
        role="specialist",
        kind=WorkUnitKind.EXECUTION,
        required_capabilities=("capability.not-registered",),
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
        parallel_safe=True,
        priority=20,
    )
    healthy = wu("healthy", priority=10)
    plan = ProjectExecutionPlan(
        summary="skill-resolution bulkhead",
        work_units=(missing_skill, healthy),
    )
    runtime = ConcurrentRuntime(outputs={"healthy": "HEALTHY_DONE"})

    result, _ = run(
        plan,
        runtime,
        max_concurrency=1,
    )

    assert result.status is ProjectRunStatus.PARTIAL
    assert result.completed_work_unit_ids == ("healthy",)
    assert result.blocked_work_unit_ids == ("missing-skill",)
    assert [task.work_unit_id for task in runtime.tasks] == ["healthy"]
    blocked = [
        record
        for record in result.records
        if record.work_unit_id == "missing-skill"
    ]
    assert blocked
    assert blocked[-1].reason.startswith("skill-resolution:")
