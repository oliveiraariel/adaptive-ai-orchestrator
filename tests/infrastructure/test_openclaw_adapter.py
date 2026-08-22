from application.agent_runtime import AgentRuntimeStatus
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from infrastructure.openclaw_adapter import OpenClawAdapter


class FakeOpenClawClient:
    def __init__(self) -> None:
        self.submissions: list[dict] = []
        self.status = "queued"
        self.result = {"output": "done"}
        self.cancelled: list[str] = []

    def submit(self, task_payload: dict) -> str:
        self.submissions.append(task_payload)
        return "oc-001"

    def get_status(self, external_id: str) -> str:
        assert external_id == "oc-001"
        return self.status

    def retrieve_result(self, external_id: str) -> object:
        assert external_id == "oc-001"
        return self.result

    def cancel(self, external_id: str) -> None:
        self.cancelled.append(external_id)


def make_task() -> TaskPackage:
    return TaskPackage(
        task_id="task-001",
        work_unit_id="wu-001",
        objective="Execute through OpenClaw.",
        configuration=ResourceConfiguration(
            agent="agent-001",
            skills=("tdd",),
            model="model-001",
            provider="provider-001",
            runtime="openclaw",
        ),
        expected_output=("result",),
        acceptance_criteria=("success",),
    )


def test_submit_translates_task_and_returns_execution_reference() -> None:
    client = FakeOpenClawClient()
    adapter = OpenClawAdapter(client)

    execution = adapter.submit(make_task())

    assert execution.id == "openclaw:oc-001"
    assert execution.runtime == "openclaw"
    assert execution.external_id == "oc-001"
    assert execution.status is AgentRuntimeStatus.SUBMITTED

    assert client.submissions[0]["task_id"] == "task-001"
    assert client.submissions[0]["configuration"]["agent"] == "agent-001"


def test_status_is_normalized_from_openclaw_values() -> None:
    client = FakeOpenClawClient()
    adapter = OpenClawAdapter(client)

    execution = adapter.submit(make_task())

    client.status = "running"
    assert adapter.get_status(execution) is AgentRuntimeStatus.RUNNING

    client.status = "succeeded"
    assert adapter.get_status(execution) is AgentRuntimeStatus.COMPLETED


def test_result_is_returned_through_internal_result_contract() -> None:
    client = FakeOpenClawClient()
    adapter = OpenClawAdapter(client)

    execution = adapter.submit(make_task())
    client.status = "completed"

    result = adapter.retrieve_result(execution)

    assert result.execution.status is AgentRuntimeStatus.COMPLETED
    assert result.raw_result == {"output": "done"}


def test_cancel_translates_to_internal_cancelled_state() -> None:
    client = FakeOpenClawClient()
    adapter = OpenClawAdapter(client)

    execution = adapter.submit(make_task())

    cancelled = adapter.cancel(execution)

    assert cancelled.status is AgentRuntimeStatus.CANCELLED
    assert client.cancelled == ["oc-001"]


def test_adapter_rejects_execution_from_other_runtime() -> None:
    client = FakeOpenClawClient()
    adapter = OpenClawAdapter(client)

    from application.agent_runtime import ExecutionReference

    execution = ExecutionReference(
        id="other:001",
        runtime="other-runtime",
        external_id="001",
        status=AgentRuntimeStatus.RUNNING,
    )

    try:
        adapter.get_status(execution)
    except ValueError as exc:
        assert "does not belong to OpenClaw" in str(exc)
    else:
        raise AssertionError("Expected runtime ownership validation.")
