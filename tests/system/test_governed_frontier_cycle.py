from application.agent_runtime import (
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
from application.finalize_execution import FinalizeExecution, FinalizeExecutionRequest
from domain.dependency import Dependency
from domain.evaluation import Evaluation, EvaluationVerdict
from domain.evaluation_plan import AxisEvaluation, EvaluationAxis, EvaluationPlan
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState
from infrastructure.claim_registry import InMemoryClaimRegistry


class SystemRuntime:
    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, task: TaskPackage) -> ExecutionReference:
        self.submitted.append(task.task_id)
        return ExecutionReference(
            id=f"execution:{task.task_id}",
            runtime="system-runtime",
            external_id=task.task_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return AgentRuntimeStatus.COMPLETED

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        return AgentRuntimeResult(execution=execution, raw_result={"ok": True})

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return execution


def assignment(work_unit: WorkUnit) -> WorkAssignment:
    configuration = ResourceConfiguration(
        agent=f"agent:{work_unit.id.value}",
        model="model-system",
        runtime="system-runtime",
    )
    task = TaskPackage(
        task_id=f"task:{work_unit.id.value}",
        work_unit_id=work_unit.id.value,
        objective=work_unit.objective,
        configuration=configuration,
        expected_output=("implementation",),
        acceptance_criteria=("spec", "standards"),
    )
    return WorkAssignment(work_unit, configuration, task)


def accepted_axis(axis_name: str) -> AxisEvaluation:
    return AxisEvaluation(
        axis_name=axis_name,
        evaluation=Evaluation(
            id=f"evaluation:{axis_name}",
            target="task:wu-a",
            evaluator=f"reviewer:{axis_name}",
            criteria=(axis_name,),
            evidence=(f"evidence:{axis_name}",),
            findings=(f"{axis_name}:pass",),
            verdict=EvaluationVerdict.ACCEPTED,
            confidence=1.0,
        ),
    )


def test_accepted_frontier_member_unlocks_next_work_unit() -> None:
    runtime = SystemRuntime()
    claims = InMemoryClaimRegistry()
    coordinator = ExecutionCoordinator(runtime=runtime, claim_registry=claims)

    first = WorkUnit(
        id=WorkUnitId("wu-a"),
        objective="Build first vertical slice",
        priority=10,
    )
    second = WorkUnit(
        id=WorkUnitId("wu-b"),
        objective="Build dependent vertical slice",
        priority=20,
    )
    dependency = Dependency(source_id="wu-a", target_id="wu-b")

    first_round = coordinator.dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(assignment(first), assignment(second)),
            dependencies=(dependency,),
            claimant_id="orchestrator",
            concurrency_limit=2,
        )
    )
    by_id = {outcome.work_unit_id: outcome for outcome in first_round.outcomes}

    assert by_id["wu-a"].status is DispatchStatus.DISPATCHED
    assert by_id["wu-b"].status is DispatchStatus.BLOCKED
    assert by_id["wu-a"].claim is not None

    evaluation_plan = EvaluationPlan(
        (
            EvaluationAxis(
                name="spec",
                evaluator_id="reviewer:spec",
                criteria=("spec",),
            ),
            EvaluationAxis(
                name="standards",
                evaluator_id="reviewer:standards",
                criteria=("standards",),
            ),
        )
    )
    summary = evaluation_plan.aggregate(
        (accepted_axis("spec"), accepted_axis("standards"))
    )
    assert summary.verdict is EvaluationVerdict.ACCEPTED

    FinalizeExecution(claims).execute(
        FinalizeExecutionRequest(
            work_unit=first,
            claim=by_id["wu-a"].claim,
                verdict=summary.verdict,
                dependencies=(dependency,),
                orchestration_id="orch-system",
        )
    )

    assert first.state is WorkUnitState.COMPLETED
    assert dependency.is_satisfied

    second_round = coordinator.dispatch_frontier(
        DispatchFrontierRequest(
            assignments=(assignment(second),),
            dependencies=(dependency,),
            claimant_id="orchestrator",
            concurrency_limit=2,
        )
    )

    assert second_round.outcomes[0].status is DispatchStatus.DISPATCHED
    assert second.state is WorkUnitState.RUNNING
    assert runtime.submitted == ["task:wu-a", "task:wu-b"]
