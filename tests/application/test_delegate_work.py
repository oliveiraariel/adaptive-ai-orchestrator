from dataclasses import dataclass

import pytest

from application.agent_runtime import (
    AgentRuntimeStatus,
    AgentRuntimeResult,
    ExecutionReference,
)
from application.delegate_work import (
    DelegateWork,
    DelegateWorkError,
    DelegateWorkRequest,
)
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState


@dataclass
class FakeRuntime:
    submit_status: AgentRuntimeStatus = AgentRuntimeStatus.SUBMITTED

    def submit(self, task: TaskPackage) -> ExecutionReference:
        return ExecutionReference(
            id="execution-001",
            runtime="fake-runtime",
            external_id="external-001",
            status=self.submit_status,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return execution.status

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        return AgentRuntimeResult(execution=execution, raw_result={"ok": True})

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


def make_work_unit() -> WorkUnit:
    work_unit = WorkUnit(
        id=WorkUnitId("wu-001"),
        objective="Execute delegated work.",
    )
    work_unit.mark_ready()
    return work_unit


def make_task(configuration: ResourceConfiguration) -> TaskPackage:
    return TaskPackage(
        task_id="task-001",
        work_unit_id="wu-001",
        objective="Execute delegated work.",
        configuration=configuration,
        expected_output=("result",),
        acceptance_criteria=("accepted",),
    )


def make_request(
    work_unit: WorkUnit,
    configuration: ResourceConfiguration,
) -> DelegateWorkRequest:
    return DelegateWorkRequest(
        work_unit=work_unit,
        configuration=configuration,
        task_package=make_task(configuration),
    )


def test_delegate_work_submits_task_and_starts_work_unit() -> None:
    work_unit = make_work_unit()
    configuration = make_configuration()
    runtime = FakeRuntime()

    result = DelegateWork(runtime).execute(
        make_request(work_unit, configuration)
    )

    assert result.execution.id == "execution-001"
    assert work_unit.state is WorkUnitState.RUNNING


def test_delegate_work_rejects_non_ready_work_unit() -> None:
    work_unit = WorkUnit(
        id=WorkUnitId("wu-001"),
        objective="Execute delegated work.",
    )
    configuration = make_configuration()

    with pytest.raises(DelegateWorkError):
        DelegateWork(FakeRuntime()).execute(
            make_request(work_unit, configuration)
        )

    assert work_unit.state is WorkUnitState.PLANNED


def test_delegate_work_rejects_mismatched_work_unit_reference() -> None:
    work_unit = make_work_unit()
    configuration = make_configuration()
    task = TaskPackage(
        task_id="task-001",
        work_unit_id="different-wu",
        objective=work_unit.objective,
        configuration=configuration,
        expected_output=("result",),
        acceptance_criteria=("accepted",),
    )

    request = DelegateWorkRequest(
        work_unit=work_unit,
        configuration=configuration,
        task_package=task,
    )

    with pytest.raises(DelegateWorkError):
        DelegateWork(FakeRuntime()).execute(request)


def test_delegate_work_rejects_configuration_mismatch() -> None:
    work_unit = make_work_unit()
    selected_configuration = make_configuration()

    different_configuration = ResourceConfiguration(
        agent="other-agent",
        skills=("tdd",),
        model="model-001",
        provider="provider-001",
        runtime="openclaw",
    )

    request = DelegateWorkRequest(
        work_unit=work_unit,
        configuration=selected_configuration,
        task_package=make_task(different_configuration),
    )

    with pytest.raises(DelegateWorkError):
        DelegateWork(FakeRuntime()).execute(request)


def test_delegate_work_rejects_objective_mismatch() -> None:
    work_unit = make_work_unit()
    configuration = make_configuration()

    task = TaskPackage(
        task_id="task-001",
        work_unit_id=work_unit.id.value,
        objective="Different objective.",
        configuration=configuration,
        expected_output=("result",),
        acceptance_criteria=("accepted",),
    )

    request = DelegateWorkRequest(
        work_unit=work_unit,
        configuration=configuration,
        task_package=task,
    )

    with pytest.raises(DelegateWorkError):
        DelegateWork(FakeRuntime()).execute(request)


def test_delegate_work_rejects_runtime_failure_to_accept() -> None:
    work_unit = make_work_unit()
    configuration = make_configuration()

    runtime = FakeRuntime(
        submit_status=AgentRuntimeStatus.FAILED
    )

    with pytest.raises(DelegateWorkError):
        DelegateWork(runtime).execute(
            make_request(work_unit, configuration)
        )

    assert work_unit.state is WorkUnitState.READY
