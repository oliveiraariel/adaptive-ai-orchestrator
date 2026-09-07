import pytest

from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.delegate_work import DelegateWork, DelegateWorkError, DelegateWorkRequest
from domain.execution_policy import AutonomyClass, ExecutionPolicy
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitKind, WorkUnitState


class RecordingRuntime:
    def __init__(self) -> None:
        self.submitted: list[TaskPackage] = []

    def submit(self, task: TaskPackage) -> ExecutionReference:
        self.submitted.append(task)
        return ExecutionReference(
            id=f"exec:{task.task_id}",
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


def make_configuration() -> ResourceConfiguration:
    return ResourceConfiguration(
        agent="agent-001",
        model="model-001",
        runtime="test-runtime",
    )


def make_work_unit(*, kind: WorkUnitKind = WorkUnitKind.EXECUTION) -> WorkUnit:
    work_unit = WorkUnit(
        id=WorkUnitId("wu-policy"),
        objective="Perform governed work",
        kind=kind,
    )
    work_unit.mark_ready()
    return work_unit


def make_task(
    configuration: ResourceConfiguration,
    policy: ExecutionPolicy,
) -> TaskPackage:
    return TaskPackage(
        task_id="task-policy",
        work_unit_id="wu-policy",
        objective="Perform governed work",
        configuration=configuration,
        expected_output=("result",),
        acceptance_criteria=("result-present",),
        execution_policy=policy,
    )


def test_human_approval_is_checked_before_runtime_submission() -> None:
    runtime = RecordingRuntime()
    configuration = make_configuration()
    work_unit = make_work_unit()
    task = make_task(
        configuration,
        ExecutionPolicy(autonomy=AutonomyClass.HUMAN_APPROVAL_REQUIRED),
    )

    with pytest.raises(DelegateWorkError, match="human approval"):
        DelegateWork(runtime).execute(
            DelegateWorkRequest(
                work_unit=work_unit,
                configuration=configuration,
                task_package=task,
            )
        )

    assert runtime.submitted == []
    assert work_unit.state is WorkUnitState.READY

    result = DelegateWork(runtime).execute(
        DelegateWorkRequest(
            work_unit=work_unit,
            configuration=configuration,
            task_package=task,
            human_approved=True,
        )
    )

    assert result.execution.status is AgentRuntimeStatus.SUBMITTED
    assert len(runtime.submitted) == 1
    assert work_unit.state is WorkUnitState.RUNNING
    assert work_unit.execution_reference == result.execution.id


def test_human_execution_required_never_reaches_agent_runtime() -> None:
    runtime = RecordingRuntime()
    configuration = make_configuration()
    work_unit = make_work_unit()
    task = make_task(
        configuration,
        ExecutionPolicy(autonomy=AutonomyClass.HUMAN_EXECUTION_REQUIRED),
    )

    with pytest.raises(DelegateWorkError, match="human execution"):
        DelegateWork(runtime).execute(
            DelegateWorkRequest(
                work_unit=work_unit,
                configuration=configuration,
                task_package=task,
                human_approved=True,
            )
        )

    assert runtime.submitted == []
    assert work_unit.state is WorkUnitState.READY


def test_forbidden_policy_never_reaches_agent_runtime() -> None:
    runtime = RecordingRuntime()
    configuration = make_configuration()
    work_unit = make_work_unit()
    task = make_task(
        configuration,
        ExecutionPolicy(autonomy=AutonomyClass.FORBIDDEN),
    )

    with pytest.raises(DelegateWorkError, match="denied"):
        DelegateWork(runtime).execute(
            DelegateWorkRequest(
                work_unit=work_unit,
                configuration=configuration,
                task_package=task,
                human_approved=True,
            )
        )

    assert runtime.submitted == []


def test_human_action_kind_cannot_bypass_policy_by_direct_delegation() -> None:
    runtime = RecordingRuntime()
    configuration = make_configuration()
    work_unit = make_work_unit(kind=WorkUnitKind.HUMAN_ACTION)
    task = make_task(configuration, ExecutionPolicy())

    with pytest.raises(DelegateWorkError, match="HUMAN_ACTION"):
        DelegateWork(runtime).execute(
            DelegateWorkRequest(
                work_unit=work_unit,
                configuration=configuration,
                task_package=task,
                human_approved=True,
            )
        )

    assert runtime.submitted == []
    assert work_unit.execution_reference is None
    assert work_unit.state is WorkUnitState.READY
