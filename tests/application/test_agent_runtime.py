from dataclasses import replace

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage


def make_task() -> TaskPackage:
    return TaskPackage(
        task_id="task-001",
        work_unit_id="wu-001",
        objective="Execute a delegated Work Unit.",
        configuration=ResourceConfiguration(
            agent="agent-001",
            skills=("tdd",),
            model="model-001",
            provider="provider-001",
            runtime="openclaw",
        ),
        expected_output=("implementation",),
        acceptance_criteria=("tests-pass",),
    )


class FakeAgentRuntime:
    def __init__(self) -> None:
        self.execution = ExecutionReference(
            id="execution-001",
            runtime="fake-runtime",
            external_id="external-001",
            status=AgentRuntimeStatus.SUBMITTED,
        )
        self.submitted_tasks: list[str] = []

    def submit(self, task: TaskPackage) -> ExecutionReference:
        self.submitted_tasks.append(task.task_id)
        return self.execution

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return execution.status

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        completed = replace(execution, status=AgentRuntimeStatus.COMPLETED)
        return AgentRuntimeResult(
            execution=completed,
            raw_result={"result": "done"},
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return replace(execution, status=AgentRuntimeStatus.CANCELLED)


def test_fake_runtime_satisfies_agent_runtime_contract() -> None:
    runtime: AgentRuntime = FakeAgentRuntime()

    execution = runtime.submit(make_task())

    assert execution.id == "execution-001"
    assert execution.runtime == "fake-runtime"
    assert execution.status is AgentRuntimeStatus.SUBMITTED


def test_runtime_status_is_normalized() -> None:
    runtime: AgentRuntime = FakeAgentRuntime()
    execution = runtime.submit(make_task())

    assert runtime.get_status(execution) is AgentRuntimeStatus.SUBMITTED


def test_runtime_result_is_returned_without_exposing_runtime_sdk() -> None:
    runtime: AgentRuntime = FakeAgentRuntime()
    execution = runtime.submit(make_task())

    result = runtime.retrieve_result(execution)

    assert result.execution.status is AgentRuntimeStatus.COMPLETED
    assert result.raw_result == {"result": "done"}


def test_runtime_can_cancel_execution() -> None:
    runtime: AgentRuntime = FakeAgentRuntime()
    execution = runtime.submit(make_task())

    cancelled = runtime.cancel(execution)

    assert cancelled.status is AgentRuntimeStatus.CANCELLED
