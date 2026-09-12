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
    orchestration_id: str
    task_id: str
    work_unit_id: str
    decision: ModelRoutingDecision
    started_monotonic: float


class OpenClawAdapter(AgentRuntime):
    """Translates the internal AgentRuntime seam to an OpenClaw client.

    Model and thinking routing are enforced at the runtime boundary. This keeps
    planner and worker calls under one deterministic policy even when upstream
    planning code leaves model/provider/thinking unspecified.
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
        thinking_constraint = (
            f"adaptive-thinking-level:{decision.thinking}"
            if decision.thinking is not None
            else "adaptive-thinking-level:provider-native"
        )
        auth_constraint = (
            "adaptive-auth-product:openai-oauth"
            if (
                decision.provider == "openai"
                and decision.model == "openai/gpt-5.6-luna"
            )
            else "adaptive-auth-product:provider-default"
        )
        routed_configuration = replace(
            configuration,
            model=decision.model,
            provider=decision.provider,
            auth_profile=decision.auth_profile,
            thinking=decision.thinking,
            policy_constraints=(
                *configuration.policy_constraints,
                f"adaptive-model-tier:{decision.tier}",
                f"adaptive-model-routing-reason:{decision.reason}",
                thinking_constraint,
                f"adaptive-thinking-routing-reason:{decision.thinking_reason}",
                auth_constraint,
            ),
        )

        # Write the routing decision before dispatch. If the audit trail is not
        # writable, execution is intentionally not started unlogged.
        self._audit.append(
            {
                "event": "routing-selected",
                "task_id": task.task_id,
                "orchestration_id": task.orchestration_id,
                "work_unit_id": task.work_unit_id,
                "model": decision.model,
                "provider": decision.provider,
                "tier": decision.tier,
                "reason": decision.reason,
                "attempt": decision.attempt,
                "thinking": decision.thinking,
                "thinking_reason": decision.thinking_reason,
                "auth_profile_configured": decision.auth_profile is not None,
                "auth_product": (
                    "openai-oauth"
                    if (
                        decision.provider == "openai"
                        and decision.model == "openai/gpt-5.6-luna"
                    )
                    else "provider-default"
                ),
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
            orchestration_id=task.orchestration_id,
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
            thinking=decision.thinking,
            auth_profile_configured=decision.auth_profile is not None,
            auth_product=(
                "openai-oauth"
                if (
                    decision.provider == "openai"
                    and decision.model == "openai/gpt-5.6-luna"
                )
                else "provider-default"
            ),
            attempt=decision.attempt, skills=list(configuration.skills),
        )
        self._audit.append(
            {
                "event": "model-dispatch",
                "task_id": task.task_id,
                "orchestration_id": task.orchestration_id,
                "work_unit_id": task.work_unit_id,
                "execution_id": execution.id,
                "external_id": external_id,
                "model": decision.model,
                "provider": decision.provider,
                "tier": decision.tier,
                "reason": decision.reason,
                "attempt": decision.attempt,
                "thinking": decision.thinking,
                "thinking_reason": decision.thinking_reason,
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
                        "orchestration_id": state.orchestration_id,
                        "work_unit_id": state.work_unit_id,
                        "execution_id": execution.id,
                        "external_id": execution.external_id,
                        "model": state.decision.model,
                        "provider": state.decision.provider,
                        "tier": state.decision.tier,
                        "attempt": state.decision.attempt,
                        "thinking": state.decision.thinking,
                        "thinking_reason": state.decision.thinking_reason,
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
        usage = self._extract_usage(raw_result)
        cost = self._extract_cost(raw_result)

        effective_model = state.decision.model if state is not None else None
        effective_provider = state.decision.provider if state is not None else None
        effective_thinking = state.decision.thinking if state is not None else None
        failover: dict[str, object] | None = None
        if isinstance(raw_result, dict):
            candidate = raw_result.get("model_failover")
            if isinstance(candidate, dict) and candidate.get("triggered") is True:
                failover = candidate
                to_model = candidate.get("to_model")
                to_provider = candidate.get("to_provider")
                if isinstance(to_model, str) and to_model:
                    effective_model = to_model
                if isinstance(to_provider, str) and to_provider:
                    effective_provider = to_provider
                if (
                    isinstance(effective_model, str)
                    and effective_model.casefold().startswith("moonshot/kimi-k2.7-code")
                ):
                    effective_thinking = None
                elif isinstance(effective_model, str):
                    effective_thinking = "medium"

        if state is not None:
            if failover is not None:
                incident = failover.get("incident")
                remediation = failover.get("remediation")
                self._observability.emit(
                    "model_failover",
                    orchestration_id=state.orchestration_id,
                    work_unit_id=state.work_unit_id,
                    execution_id=execution.id,
                    external_id=execution.external_id,
                    from_model=failover.get("from_model"),
                    to_model=effective_model,
                    provider=effective_provider,
                    reason=failover.get("reason"),
                    runtime_attempt=failover.get("runtime_attempt"),
                    incident=incident if isinstance(incident, dict) else None,
                    remediation=remediation if isinstance(remediation, dict) else None,
                    circuit_state=failover.get("circuit_state"),
                )
                self._audit.append(
                    {
                        "event": "model-failover",
                        "task_id": state.task_id,
                        "orchestration_id": state.orchestration_id,
                        "work_unit_id": state.work_unit_id,
                        "execution_id": execution.id,
                        "external_id": execution.external_id,
                        "from_model": failover.get("from_model"),
                        "to_model": effective_model,
                        "to_provider": effective_provider,
                        "failure_reason": failover.get("reason"),
                        "runtime_attempt": failover.get("runtime_attempt"),
                        **(
                            {"incident": failover.get("incident")}
                            if isinstance(failover.get("incident"), dict)
                            else {}
                        ),
                        **(
                            {"remediation": failover.get("remediation")}
                            if isinstance(failover.get("remediation"), dict)
                            else {}
                        ),
                        **(
                            {"circuit_state": failover.get("circuit_state")}
                            if isinstance(failover.get("circuit_state"), str)
                            else {}
                        ),
                    }
                )

            self._observability.emit(
                "work_unit_status_changed",
                orchestration_id=state.orchestration_id,
                work_unit_id=state.work_unit_id,
                execution_id=execution.id,
                external_id=execution.external_id,
                model=effective_model,
                provider=effective_provider,
                thinking=effective_thinking,
                attempt=state.decision.attempt,
                status=status.value,
                usage=usage,
                cost=cost,
            )
            self._audit.append(
                {
                    "event": "runtime-result",
                    "task_id": state.task_id,
                    "orchestration_id": state.orchestration_id,
                    "work_unit_id": state.work_unit_id,
                    "execution_id": execution.id,
                    "external_id": execution.external_id,
                    "model": effective_model,
                    "provider": effective_provider,
                    "tier": (
                        "fallback" if failover is not None else state.decision.tier
                    ),
                    "reason": (
                        f"operational-fallback-after-{failover.get('reason')}"
                        if failover is not None
                        else state.decision.reason
                    ),
                    "attempt": state.decision.attempt,
                    "thinking": effective_thinking,
                    "thinking_reason": (
                        "provider-native-code-specialist-reasoning"
                        if effective_thinking is None
                        else (
                            "operational-fallback-medium-reasoning"
                            if failover is not None
                            else state.decision.thinking_reason
                        )
                    ),
                    "escalated_from": (
                        failover.get("from_model")
                        if failover is not None
                        else state.decision.escalated_from
                    ),
                    "runtime_status": status.value,
                    **({"usage": usage} if usage else {}),
                    **({"cost": cost} if cost else {}),
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

    @staticmethod
    def _extract_usage(raw_result: object) -> dict[str, int] | None:
        if not isinstance(raw_result, dict):
            return None
        candidate = raw_result.get("usage") or raw_result.get("token_usage")
        if not isinstance(candidate, dict):
            return None
        aliases = {
            "input_tokens": ("input_tokens", "prompt_tokens", "input"),
            "output_tokens": ("output_tokens", "completion_tokens", "output"),
            "cache_read_tokens": ("cache_read_tokens", "cached_input_tokens"),
            "cache_write_tokens": ("cache_write_tokens", "cached_output_tokens"),
            "total_tokens": ("total_tokens", "total"),
        }
        result: dict[str, int] = {}
        for target, names in aliases.items():
            for name in names:
                value = candidate.get(name)
                if isinstance(value, int) and value >= 0:
                    result[target] = value
                    break
        if "total_tokens" not in result and {"input_tokens", "output_tokens"} <= result.keys():
            result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
        return result or None

    @staticmethod
    def _extract_cost(raw_result: object) -> dict[str, object] | None:
        if not isinstance(raw_result, dict) or not isinstance(raw_result.get("cost"), dict):
            return None
        value = raw_result["cost"]
        result: dict[str, object] = {}
        if value.get("status") in {"actual", "estimated", "unknown"}:
            result["status"] = value["status"]
        if isinstance(value.get("usd"), (int, float)) and value["usd"] >= 0:
            result["usd"] = value["usd"]
        if isinstance(value.get("pricing_source"), str):
            result["pricing_source"] = value["pricing_source"][:300]
        return result or None

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
                    "orchestration_id": state.orchestration_id,
                    "work_unit_id": state.work_unit_id,
                    "execution_id": execution.id,
                    "external_id": execution.external_id,
                    "model": state.decision.model,
                    "provider": state.decision.provider,
                    "tier": state.decision.tier,
                    "attempt": state.decision.attempt,
                    "thinking": state.decision.thinking,
                    "thinking_reason": state.decision.thinking_reason,
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
                "auth_profile": effective_configuration.auth_profile,
                "thinking": effective_configuration.thinking,
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
