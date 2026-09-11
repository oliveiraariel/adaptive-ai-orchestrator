import json
from pathlib import Path

from application.agent_runtime import AgentRuntimeStatus
from application.model_routing_policy import ModelRoutingPolicy
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from infrastructure.model_routing_audit import ModelRoutingAuditLog
from infrastructure.openclaw_adapter import OpenClawAdapter


class FakeClient:
    def __init__(self) -> None:
        self.submissions: list[dict] = []

    def submit(self, task_payload: dict) -> str:
        self.submissions.append(task_payload)
        return "run-001"

    def get_status(self, external_id: str) -> str:
        assert external_id == "run-001"
        return "completed"

    def retrieve_result(self, external_id: str) -> object:
        assert external_id == "run-001"
        return {"output": "done"}

    def cancel(self, external_id: str) -> None:
        pass


def make_task(
    objective: str,
    *,
    task_id: str = "project:o:wave:1:wu:attempt-number:1",
    context: tuple[str, ...] = (),
    model: str | None = None,
    provider: str | None = None,
    thinking: str | None = None,
) -> TaskPackage:
    return TaskPackage(
        task_id=task_id,
        work_unit_id="wu-001",
        objective=objective,
        context=context,
        configuration=ResourceConfiguration(
            agent="sgfp",
            model=model,
            provider=provider,
            thinking=thinking,
            runtime="openclaw",
        ),
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
    )


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_adapter_enforces_luna_medium_for_routine_code_and_audits_result(tmp_path) -> None:
    client = FakeClient()
    log_path = tmp_path / "routing.jsonl"
    adapter = OpenClawAdapter(
        client,
        model_routing_policy=ModelRoutingPolicy(),
        audit_log=ModelRoutingAuditLog(log_path),
    )

    execution = adapter.submit(
        make_task("Implementar endpoint PHP para listar categorias.")
    )
    result = adapter.retrieve_result(execution)

    submitted = client.submissions[0]["configuration"]
    assert submitted["model"] == "openai/gpt-5.6-luna"
    assert submitted["provider"] == "openai"
    assert submitted["thinking"] == "medium"
    assert "adaptive-model-tier:economy" in submitted["policy_constraints"]
    assert "adaptive-thinking-level:medium" in submitted["policy_constraints"]
    assert result.execution.status is AgentRuntimeStatus.COMPLETED

    events = read_events(log_path)
    assert [event["event"] for event in events] == [
        "routing-selected",
        "model-dispatch",
        "runtime-result",
    ]
    assert events[-1]["model"] == "openai/gpt-5.6-luna"
    assert events[-1]["thinking"] == "medium"
    assert events[-1]["runtime_status"] == "COMPLETED"
    assert events[-1]["elapsed_seconds"] >= 0


def test_adapter_keeps_routine_non_code_work_at_medium(tmp_path) -> None:
    client = FakeClient()
    adapter = OpenClawAdapter(
        client,
        model_routing_policy=ModelRoutingPolicy(),
        audit_log=ModelRoutingAuditLog(tmp_path / "routing.jsonl"),
    )

    adapter.submit(make_task("Organizar os nomes dos arquivos de saída."))

    submitted = client.submissions[0]["configuration"]
    assert submitted["model"] == "openai/gpt-5.6-luna"
    assert submitted["thinking"] == "medium"


def test_adapter_escalates_second_code_attempt_to_kimi_without_thinking_override(tmp_path) -> None:
    client = FakeClient()
    log_path = tmp_path / "routing.jsonl"
    adapter = OpenClawAdapter(
        client,
        model_routing_policy=ModelRoutingPolicy(),
        audit_log=ModelRoutingAuditLog(log_path),
    )

    adapter.submit(
        make_task(
            "Implementar testes unitários para o service PHP.",
            task_id="project:o:wave:2:wu:attempt-number:2",
            context=("Revision feedback from previous attempt: tests failed",),
        )
    )

    submitted = client.submissions[0]["configuration"]
    assert submitted["model"] == "moonshot/kimi-k2.7-code"
    assert submitted["provider"] == "moonshot"
    assert submitted["thinking"] is None
    assert "adaptive-model-tier:code-specialist" in submitted["policy_constraints"]
    assert "adaptive-thinking-level:provider-native" in submitted["policy_constraints"]

    events = read_events(log_path)
    assert events[0]["model"] == "moonshot/kimi-k2.7-code"
    assert events[0]["thinking"] is None


def test_adapter_does_not_dispatch_disabled_sol_override(tmp_path) -> None:
    client = FakeClient()
    adapter = OpenClawAdapter(
        client,
        model_routing_policy=ModelRoutingPolicy(),
        audit_log=ModelRoutingAuditLog(tmp_path / "routing.jsonl"),
    )

    adapter.submit(
        make_task(
            "Implementar código PHP simples.",
            model="openai/gpt-5.6-sol",
            provider="openai",
            thinking="high",
        )
    )

    submitted = client.submissions[0]["configuration"]
    assert submitted["model"] == "openai/gpt-5.6-luna"
    assert submitted["provider"] == "openai"
    assert submitted["thinking"] == "medium"
    assert "adaptive-model-tier:economy" in submitted["policy_constraints"]
    assert "adaptive-thinking-level:medium" in submitted["policy_constraints"]
