from application.agent_runtime import (
    AgentRuntimeError,
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.execution_coordinator import (
    DispatchFrontierRequest,
    DispatchStatus,
    ExecutionCoordinator,
    WorkAssignment,
)
from domain.dependency import Dependency
from domain.execution_policy import AutonomyClass, ExecutionPolicy
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitKind, WorkUnitState
from infrastructure.claim_registry import InMemoryClaimRegistry


class FrontierRuntime:
    def __init__(self, failing_task_ids: tuple[str, ...] = ()) -> None:
        self.failing = set(failing_task_ids)
        self.submitted: list[str] = []

    def submit(self, task: TaskPackage) -> ExecutionReference:
        if task.task_id in self.failing:
            raise AgentRuntimeError(f"runtime failure for {task.task_id}")
        self.submitted.append(task.task_id)
        return ExecutionReference(
            id=f"execution:{task.task_id}",
            runtime="test-runtime",
            external_id=task.task_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return execution.status

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        return AgentRuntimeResult(execution=execution)

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return execution


def make_assignment(
    work_unit_id: str,
    *,
    priority: int = 0,
    policy: ExecutionPolicy | None = None,
    kind: WorkUnitKind = WorkUnitKind.EXECUTION,
) -> WorkAssignment:
    work_unit = WorkUnit(
        id=WorkUnitId(work_unit_id),
        objective=f"Execute {work_unit_id}",
        priority=priority,
        kind=kind,
    )
    configuration = ResourceConfiguration(
        agent=f"agent:{work_unit_id}",
        model="model-001",
        runtime="test-runtime",
    )
    task_package = TaskPackage(
        task_id=f"task:{work_unit_id}",
        work_unit_id=work_unit_id,
        objective=work_unit.objective,
        configuration=configuration,
        expected_output=("result",),
        acceptance_criteria=("result-present",),
        execution_policy=policy or ExecutionPolicy(),
    )
    return WorkAssignment(work_unit, configuration, task_package)


def test_dispatches_only_ready_frontier_and_respects_dependency() -> None:
    runtime = FrontierRuntime()
    claims = InMemoryClaimRegistry()
    coordinator = ExecutionCoordinator(runtime=runtime, claim_registry=claims)
    first = make_assignment("wu-a", priority=10)
    blocked = make_assignment("wu-b", priority=20)
    dependency = Dependency(source_id="wu-a", target_id="wu-b")

    result = coordinator.dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(first, blocked),
            dependencies=(dependency,),
            claimant_id="scheduler-1",
            concurrency_limit=2,
        )
    )

    by_id = {outcome.work_unit_id: outcome for outcome in result.outcomes}
    assert by_id["wu-a"].status is DispatchStatus.DISPATCHED
    assert by_id["wu-b"].status is DispatchStatus.BLOCKED
    assert runtime.submitted == ["task:wu-a"]
    assert first.work_unit.state is WorkUnitState.RUNNING
    assert blocked.work_unit.state is WorkUnitState.PLANNED


def test_concurrency_budget_limits_parallel_dispatch() -> None:
    runtime = FrontierRuntime()
    coordinator = ExecutionCoordinator(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
    )
    high = make_assignment("wu-high", priority=20)
    low = make_assignment("wu-low", priority=10)

    result = coordinator.dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(low, high),
            dependencies=(),
            claimant_id="scheduler-1",
            concurrency_limit=1,
        )
    )

    assert [outcome.status for outcome in result.outcomes] == [
        DispatchStatus.DISPATCHED,
        DispatchStatus.DEFERRED,
    ]
    assert result.outcomes[0].work_unit_id == "wu-high"
    assert runtime.submitted == ["task:wu-high"]


def test_active_execution_count_reduces_available_slots() -> None:
    runtime = FrontierRuntime()
    coordinator = ExecutionCoordinator(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
    )
    assignment = make_assignment("wu-a")

    result = coordinator.dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(assignment,),
            dependencies=(),
            claimant_id="scheduler-1",
            concurrency_limit=1,
            active_execution_count=1,
        )
    )

    assert result.outcomes[0].status is DispatchStatus.DEFERRED
    assert runtime.submitted == []


def test_existing_claim_prevents_duplicate_dispatch() -> None:
    runtime = FrontierRuntime()
    claims = InMemoryClaimRegistry()
    assignment = make_assignment("wu-a")
    existing = claims.acquire(work_unit_id="wu-a", claimant_id="other-scheduler")
    assert existing is not None

    result = ExecutionCoordinator(runtime=runtime, claim_registry=claims).dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(assignment,),
            dependencies=(),
            claimant_id="scheduler-1",
            concurrency_limit=1,
        )
    )

    assert result.outcomes[0].status is DispatchStatus.BLOCKED
    assert result.outcomes[0].reason == "work-unit-already-claimed"
    assert runtime.submitted == []


def test_failed_dispatch_releases_claim_for_retry() -> None:
    runtime = FrontierRuntime(("task:wu-a",))
    claims = InMemoryClaimRegistry()
    assignment = make_assignment("wu-a")

    result = ExecutionCoordinator(runtime=runtime, claim_registry=claims).dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(assignment,),
            dependencies=(),
            claimant_id="scheduler-1",
            concurrency_limit=1,
        )
    )

    assert result.outcomes[0].status is DispatchStatus.FAILED
    assert claims.get("wu-a") is None
    assert assignment.work_unit.state is WorkUnitState.READY


def test_successful_dispatch_binds_claim_to_execution() -> None:
    runtime = FrontierRuntime()
    claims = InMemoryClaimRegistry()
    assignment = make_assignment("wu-a")

    result = ExecutionCoordinator(runtime=runtime, claim_registry=claims).dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(assignment,),
            dependencies=(),
            claimant_id="scheduler-1",
            concurrency_limit=1,
        )
    )

    outcome = result.outcomes[0]
    assert outcome.status is DispatchStatus.DISPATCHED
    assert outcome.claim is not None
    assert outcome.execution is not None
    assert outcome.claim.execution_id == outcome.execution.id
    assert claims.get("wu-a") == outcome.claim


def test_policy_and_human_action_block_before_claim_or_runtime() -> None:
    runtime = FrontierRuntime()
    claims = InMemoryClaimRegistry()
    approval = make_assignment(
        "wu-approval",
        policy=ExecutionPolicy(autonomy=AutonomyClass.HUMAN_APPROVAL_REQUIRED),
    )
    human = make_assignment("wu-human", kind=WorkUnitKind.HUMAN_ACTION)

    result = ExecutionCoordinator(runtime=runtime, claim_registry=claims).dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(approval, human),
            dependencies=(),
            claimant_id="scheduler-1",
            concurrency_limit=2,
        )
    )

    assert all(outcome.status is DispatchStatus.BLOCKED for outcome in result.outcomes)
    assert claims.get("wu-approval") is None
    assert claims.get("wu-human") is None
    assert runtime.submitted == []


def test_human_approved_work_unit_can_enter_frontier() -> None:
    runtime = FrontierRuntime()
    assignment = make_assignment(
        "wu-approval",
        policy=ExecutionPolicy(autonomy=AutonomyClass.HUMAN_APPROVAL_REQUIRED),
    )

    result = ExecutionCoordinator(
        runtime=runtime,
        claim_registry=InMemoryClaimRegistry(),
    ).dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(assignment,),
            dependencies=(),
            claimant_id="scheduler-1",
            concurrency_limit=1,
            human_approved_work_unit_ids=("wu-approval",),
        )
    )

    assert result.outcomes[0].status is DispatchStatus.DISPATCHED
