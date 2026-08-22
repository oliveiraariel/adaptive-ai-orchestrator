from application.agent_runtime import AgentRuntimeStatus, ExecutionReference
from application.delegate_work import DelegateWork, DelegateWorkRequest
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState


class FakeAgentRuntime:
    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, task: TaskPackage) -> ExecutionReference:
        self.submitted.append(task.task_id)
        return ExecutionReference(
            id="execution-001",
            runtime="fake-runtime",
            external_id="external-001",
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return execution.status

    def retrieve_result(self, execution: ExecutionReference):
        from application.agent_runtime import AgentRuntimeResult

        return AgentRuntimeResult(
            execution=execution,
            raw_result={"output": "done"},
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return execution


def make_configuration() -> ResourceConfiguration:
    return ResourceConfiguration(
        agent="agent-001",
        skills=("tdd",),
        model="model-001",
        provider="provider-001",
        runtime="openclaw",
    )


def make_ready_work_unit() -> WorkUnit:
    work_unit = WorkUnit(
        id=WorkUnitId("wu-001"),
        objective="Execute delegated implementation work.",
    )
    work_unit.mark_ready()
    return work_unit


def make_task(
    configuration: ResourceConfiguration,
) -> TaskPackage:
    return TaskPackage(
        task_id="task-001",
        work_unit_id="wu-001",
        objective="Execute delegated implementation work.",
        configuration=configuration,
        expected_output=("implementation",),
        acceptance_criteria=("tests-pass",),
    )


def test_delegation_vertical_slice_produces_execution_reference() -> None:
    work_unit = make_ready_work_unit()
    configuration = make_configuration()
    runtime = FakeAgentRuntime()

    result = DelegateWork(runtime).execute(
        DelegateWorkRequest(
            work_unit=work_unit,
            configuration=configuration,
            task_package=make_task(configuration),
        )
    )

    assert result.execution.id == "execution-001"
    assert result.execution.external_id == "external-001"
    assert result.execution.status is AgentRuntimeStatus.SUBMITTED
    assert work_unit.state is WorkUnitState.RUNNING
    assert runtime.submitted == ["task-001"]


def test_delegation_vertical_slice_does_not_execute_unready_work() -> None:
    work_unit = WorkUnit(
        id=WorkUnitId("wu-001"),
        objective="Execute delegated implementation work.",
    )
    configuration = make_configuration()
    runtime = FakeAgentRuntime()

    try:
        DelegateWork(runtime).execute(
            DelegateWorkRequest(
                work_unit=work_unit,
                configuration=configuration,
                task_package=make_task(configuration),
            )
        )
    except Exception:
        pass
    else:
        raise AssertionError("Expected delegation to reject planned Work Unit.")

    assert work_unit.state is WorkUnitState.PLANNED
    assert runtime.submitted == []
