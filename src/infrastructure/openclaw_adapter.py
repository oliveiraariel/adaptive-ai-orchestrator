from dataclasses import replace

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from domain.task_package import TaskPackage


class OpenClawClient:
    """External runtime client contract expected by the OpenClaw adapter."""

    def submit(self, task_payload: dict) -> str:
        raise NotImplementedError

    def get_status(self, external_id: str) -> str:
        raise NotImplementedError

    def retrieve_result(self, external_id: str) -> object:
        raise NotImplementedError

    def cancel(self, external_id: str) -> None:
        raise NotImplementedError


class OpenClawAdapter(AgentRuntime):
    """Translates the internal AgentRuntime seam to an OpenClaw client."""

    RUNTIME_NAME = "openclaw"

    def __init__(self, client: OpenClawClient) -> None:
        self._client = client
        self._executions: dict[str, ExecutionReference] = {}

    def submit(self, task: TaskPackage) -> ExecutionReference:
        external_id = self._client.submit(self._to_payload(task))
        execution = ExecutionReference(
            id=f"openclaw:{external_id}",
            runtime=self.RUNTIME_NAME,
            external_id=external_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )
        self._executions[execution.id] = execution
        return execution

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        self._ensure_openclaw_execution(execution)

        status = self._normalize_status(
            self._client.get_status(execution.external_id)
        )
        updated = replace(execution, status=status)
        self._executions[execution.id] = updated
        return status

    def retrieve_result(
        self,
        execution: ExecutionReference,
    ) -> AgentRuntimeResult:
        self._ensure_openclaw_execution(execution)

        raw_result = self._client.retrieve_result(execution.external_id)
        status = self.get_status(execution)

        updated = replace(execution, status=status)

        return AgentRuntimeResult(
            execution=updated,
            raw_result=raw_result,
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        self._ensure_openclaw_execution(execution)

        self._client.cancel(execution.external_id)

        cancelled = replace(
            execution,
            status=AgentRuntimeStatus.CANCELLED,
        )
        self._executions[execution.id] = cancelled
        return cancelled

    @staticmethod
    def _to_payload(task: TaskPackage) -> dict:
        configuration = task.configuration

        return {
            "task_id": task.task_id,
            "work_unit_id": task.work_unit_id,
            "objective": task.objective,
            "scope": task.scope,
            "context": task.context,
            "inputs": task.inputs,
            "artifacts": task.artifacts,
            "decisions": task.decisions,
            "dependencies": task.dependencies,
            "constraints": task.constraints,
            "configuration": {
                "agent": configuration.agent,
                "skills": configuration.skills,
                "model": configuration.model,
                "provider": configuration.provider,
                "tools": configuration.tools,
                "runtime": configuration.runtime,
                "policy_constraints": configuration.policy_constraints,
            },
            "expected_output": task.expected_output,
            "acceptance_criteria": task.acceptance_criteria,
        }

    @classmethod
    def _normalize_status(cls, status: str) -> AgentRuntimeStatus:
        normalized = status.strip().upper()

        mapping = {
            "SUBMITTED": AgentRuntimeStatus.SUBMITTED,
            "QUEUED": AgentRuntimeStatus.SUBMITTED,
            "PENDING": AgentRuntimeStatus.SUBMITTED,
            "RUNNING": AgentRuntimeStatus.RUNNING,
            "COMPLETED": AgentRuntimeStatus.COMPLETED,
            "SUCCEEDED": AgentRuntimeStatus.COMPLETED,
            "FAILED": AgentRuntimeStatus.FAILED,
            "ERROR": AgentRuntimeStatus.FAILED,
            "CANCELLED": AgentRuntimeStatus.CANCELLED,
            "CANCELED": AgentRuntimeStatus.CANCELLED,
        }

        if normalized not in mapping:
            raise ValueError(f"Unsupported OpenClaw status: {status!r}")

        return mapping[normalized]

    @staticmethod
    def _ensure_openclaw_execution(
        execution: ExecutionReference,
    ) -> None:
        if execution.runtime != OpenClawAdapter.RUNTIME_NAME:
            raise ValueError(
                "ExecutionReference does not belong to OpenClaw."
            )
