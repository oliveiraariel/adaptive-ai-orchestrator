from __future__ import annotations

import time
from dataclasses import dataclass, replace

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.model_routing_policy import (
    ModelRoutingDecision,
    ModelRoutingPolicy,
)
from application.observability import NullObservabilitySink, ObservabilitySink
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from infrastructure.model_routing_audit import ModelRoutingAuditLog


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


@dataclass(frozen=True)
class _RoutingExecutionState:
    task_id: str
    work_unit_id: str
    decision: ModelRoutingDecision
    started_monotonic: float


class OpenClawAdapter(AgentRuntime):
    """Translates the internal AgentRuntime seam to an OpenClaw client.

    Model routing is enforced at the runtime boundary. This keeps planner and
    worker calls under one deterministic policy even when upstream planning
    code leaves model/provider unspecified.
    """

    RUNTIME_NAME = "openclaw"

    def __init__(
        self,
        client: OpenClawClient,
        *,
        model_routing_policy: ModelRoutingPolicy | None = None,
        audit_log: ModelRoutingAuditLog | None = None,
        observability: ObservabilitySink | None = None,
    ) -> None:
        self._client = client
        self._executions: dict[str, ExecutionReference] = {}
        self._routing_policy = model_routing_policy or ModelRoutingPolicy.from_env()
        self._audit = audit_log or ModelRoutingAuditLog()
        self._observability = observability or NullObservabilitySink()
        self._routing_executions: dict[str, _RoutingExecutionState] = {}

    def submit(self, task: TaskPackage) -> ExecutionReference:
        configuration = task.configuration
        assert configuration is not None

        decision = self._routing_policy.select(task)
        routed_configuration = replace(
            configuration,
            model=decision.model,
            provider=decision.provider,
            policy_constraints=(
                *configuration.policy_constraints,
                f"adaptive-model-tier:{decision.tier}",
                f"adaptive-model-routing-reason:{decision.reason}",
            ),
        )

        # Write the routing decision before dispatch. If the audit trail is not
        # writable, execution is intentionally not started unlogged.
        self._audit.append(
            {
                "event": "routing-selected",
                "task_id": task.task_id,
                "work_unit_id": task.work_unit_id,
                "model": decision.model,
                "provider": decision.provider,
                "tier": decision.tier,
                "reason": decision.reason,
                "attempt": decision.attempt,
                "escalated_from": decision.escalated_from,
            }
        )

        external_id = self._client.submit(
            self._to_payload(task, configuration=routed_configuration)
        )
        execution = ExecutionReference(
            id=f"openclaw:{external_id}",
            runtime=self.RUNTIME_NAME,
            external_id=external_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )
        self._executions[execution.id] = execution
        self._routing_executions[execution.id] = _RoutingExecutionState(
            task_id=task.task_id,
            work_unit_id=task.work_unit_id,
            decision=decision,
            started_monotonic=time.monotonic(),
        )
        self._observability.emit(
            "model_selected", orchestration_id=task.orchestration_id,
            work_unit_id=task.work_unit_id,
            execution_id=execution.id, external_id=external_id,
            model=decision.model, provider=decision.provider,
            attempt=decision.attempt, skills=list(configuration.skills),
        )
        self._audit.append(
            {
                "event": "model-dispatch",
                "task_id": task.task_id,
                "work_unit_id": task.work_unit_id,
                "execution_id": execution.id,
                "external_id": external_id,
                "model": decision.model,
                "provider": decision.provider,
                "tier": decision.tier,
                "reason": decision.reason,
                "attempt": decision.attempt,
                "escalated_from": decision.escalated_from,
            }
        )
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
        state = self._routing_executions.get(execution.id)

        try:
            raw_result = self._client.retrieve_result(execution.external_id)
            status = self.get_status(execution)
        except Exception as exc:
            if state is not None:
                self._audit.append(
                    {
                        "event": "runtime-result-error",
                        "task_id": state.task_id,
                        "work_unit_id": state.work_unit_id,
                        "execution_id": execution.id,
                        "external_id": execution.external_id,
                        "model": state.decision.model,
                        "provider": state.decision.provider,
                        "tier": state.decision.tier,
                        "attempt": state.decision.attempt,
                        "elapsed_seconds": round(
                            max(0.0, time.monotonic() - state.started_monotonic),
                            3,
                        ),
                        "error_type": type(exc).__name__,
                    }
                )
            raise

        updated = replace(execution, status=status)
        self._executions[execution.id] = updated

        if state is not None:
            self._audit.append(
                {
                    "event": "runtime-result",
                    "task_id": state.task_id,
                    "work_unit_id": state.work_unit_id,
                    "execution_id": execution.id,
                    "external_id": execution.external_id,
                    "model": state.decision.model,
                    "provider": state.decision.provider,
                    "tier": state.decision.tier,
                    "reason": state.decision.reason,
                    "attempt": state.decision.attempt,
                    "escalated_from": state.decision.escalated_from,
                    "runtime_status": status.value,
                    "elapsed_seconds": round(
                        max(0.0, time.monotonic() - state.started_monotonic),
                        3,
                    ),
                }
            )

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

        state = self._routing_executions.get(execution.id)
        if state is not None:
            self._audit.append(
                {
                    "event": "runtime-cancelled",
                    "task_id": state.task_id,
                    "work_unit_id": state.work_unit_id,
                    "execution_id": execution.id,
                    "external_id": execution.external_id,
                    "model": state.decision.model,
                    "provider": state.decision.provider,
                    "tier": state.decision.tier,
                    "attempt": state.decision.attempt,
                    "elapsed_seconds": round(
                        max(0.0, time.monotonic() - state.started_monotonic),
                        3,
                    ),
                }
            )
        return cancelled

    @staticmethod
    def _to_payload(
        task: TaskPackage,
        *,
        configuration: ResourceConfiguration | None = None,
    ) -> dict:
        effective_configuration = configuration or task.configuration
        assert effective_configuration is not None

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
                "agent": effective_configuration.agent,
                "skills": effective_configuration.skills,
                "model": effective_configuration.model,
                "provider": effective_configuration.provider,
                "tools": effective_configuration.tools,
                "runtime": effective_configuration.runtime,
                "policy_constraints": effective_configuration.policy_constraints,
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
