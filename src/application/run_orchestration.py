from dataclasses import dataclass, field
from typing import Tuple
from uuid import uuid4

from application.agent_runtime import AgentRuntime, AgentRuntimeStatus
from application.observability import ObservabilitySink, NullObservabilitySink
from application.claim_registry import ClaimRegistry
from application.evaluate_result import EvaluateResult, EvaluateResultRequest
from application.execution_coordinator import (
    DispatchFrontierRequest,
    DispatchStatus,
    ExecutionCoordinator,
    WorkAssignment,
)
from application.finalize_execution import FinalizeExecution, FinalizeExecutionRequest
from domain.evaluation import EvaluationVerdict
from domain.execution_policy import ExecutionPolicy
from domain.resource_configuration import ResourceConfiguration
from domain.result_package import ResultPackage, ResultPackageStatus
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState


class RunOrchestrationError(RuntimeError):
    """Raised when a high-level orchestration run cannot complete."""


@dataclass(frozen=True)
class RunOrchestrationRequest:
    objective: str
    agent: str = "main"
    skills: Tuple[str, ...] = field(default_factory=tuple)
    model: str | None = None
    provider: str | None = None
    tools: Tuple[str, ...] = field(default_factory=tuple)
    scope: str = ""
    context: Tuple[str, ...] = field(default_factory=tuple)
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    constraints: Tuple[str, ...] = field(default_factory=tuple)
    expected_output: Tuple[str, ...] = ("agent response",)
    acceptance_criteria: Tuple[str, ...] = ("runtime-completed",)
    execution_policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    requested_side_effects: Tuple[str, ...] = field(default_factory=tuple)
    human_approved: bool = False
    claimant_id: str = "adaptive-orchestrator-cli"

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("objective must not be empty.")
        if not self.agent.strip():
            raise ValueError("agent must not be empty.")
        if not self.expected_output:
            raise ValueError("expected_output must contain at least one item.")
        if not self.acceptance_criteria:
            raise ValueError("acceptance_criteria must contain at least one item.")
        if not self.claimant_id.strip():
            raise ValueError("claimant_id must not be empty.")


@dataclass(frozen=True)
class RunOrchestrationResult:
    task_id: str
    work_unit_id: str
    execution_id: str
    external_id: str
    runtime_status: AgentRuntimeStatus
    work_unit_state: WorkUnitState
    verdict: EvaluationVerdict
    output: str
    raw_result: object
    evidence: Tuple[str, ...]


class RunOrchestration:
    """Execute one governed Work Unit through the real Adaptive core seams.

    This is deliberately a small inbound application service. It does not
    duplicate runtime behavior or turn OpenClaw-specific details into domain
    concepts. The caller supplies a normalized agent/resource configuration;
    the service applies Work Unit readiness, claims, execution policy,
    delegation, result evaluation, and finalization.
    """

    def __init__(self, *, runtime: AgentRuntime, claim_registry: ClaimRegistry, observability: ObservabilitySink | None = None) -> None:
        self._runtime = runtime
        self._claim_registry = claim_registry
        self._observability = observability or NullObservabilitySink()

    def execute(self, request: RunOrchestrationRequest) -> RunOrchestrationResult:
        run_id = uuid4().hex
        work_unit_id = f"wu:{run_id}"
        task_id = f"task:{run_id}"

        work_unit = WorkUnit(
            id=WorkUnitId(work_unit_id),
            objective=request.objective,
            scope=request.scope,
            inputs=request.inputs,
            outputs=request.expected_output,
            criteria=request.acceptance_criteria,
        )
        configuration = ResourceConfiguration(
            agent=request.agent,
            skills=request.skills,
            model=request.model,
            provider=request.provider,
            tools=request.tools,
            runtime="openclaw",
        )
        task_package = TaskPackage(
            task_id=task_id,
            work_unit_id=work_unit_id,
            objective=request.objective,
            orchestration_id=run_id,
            scope=request.scope,
            context=request.context,
            inputs=request.inputs,
            constraints=request.constraints,
            configuration=configuration,
            expected_output=request.expected_output,
            acceptance_criteria=request.acceptance_criteria,
            execution_policy=request.execution_policy,
            requested_side_effects=request.requested_side_effects,
        )
        self._observability.emit("orchestration_started", orchestration_id=run_id)
        self._observability.emit(
            "work_unit_created", orchestration_id=run_id, work_unit_id=work_unit_id,
            role=request.agent, skills=list(request.skills), status="READY",
        )

        dispatched = ExecutionCoordinator(
            runtime=self._runtime,
            claim_registry=self._claim_registry,
        ).dispatch_frontier(
            DispatchFrontierRequest(
                assignments=(
                    WorkAssignment(
                        work_unit=work_unit,
                        configuration=configuration,
                        task_package=task_package,
                    ),
                ),
                dependencies=(),
                claimant_id=request.claimant_id,
                concurrency_limit=1,
                human_approved_work_unit_ids=(work_unit_id,)
                if request.human_approved
                else (),
            )
        )

        outcome = dispatched.outcomes[0]
        if outcome.status is not DispatchStatus.DISPATCHED:
            raise RunOrchestrationError(
                f"Work Unit was not dispatched: {outcome.status.value}: {outcome.reason}"
            )
        if outcome.execution is None or outcome.claim is None:
            raise RunOrchestrationError(
                "ExecutionCoordinator returned an incomplete dispatched outcome."
            )
        self._observability.emit(
            "worker_started", orchestration_id=run_id, work_unit_id=work_unit_id,
            execution_id=outcome.execution.id, external_id=outcome.execution.external_id,
            role=request.agent, skills=list(request.skills), attempt=1, status="RUNNING",
        )

        try:
            runtime_result = self._runtime.retrieve_result(outcome.execution)
        except Exception as exc:
            self._claim_registry.release(outcome.claim)
            raise RunOrchestrationError(
                f"Runtime result retrieval failed: {exc}"
            ) from exc

        runtime_status = runtime_result.execution.status
        result_status = (
            ResultPackageStatus.SUCCEEDED
            if runtime_status is AgentRuntimeStatus.COMPLETED
            else ResultPackageStatus.FAILED
        )
        raw_result = runtime_result.raw_result
        if result_status is ResultPackageStatus.SUCCEEDED and raw_result is None:
            raw_result = {"status": "completed"}

        evidence = []
        if runtime_status is AgentRuntimeStatus.COMPLETED:
            evidence.append("runtime-completed")

        result_package = ResultPackage(
            task_id=task_id,
            status=result_status,
            result=raw_result,
            evidence=tuple(evidence),
        )
        evaluation = EvaluateResult().execute(
            EvaluateResultRequest(
                result_package=result_package,
                criteria=request.acceptance_criteria,
                evaluator_id="adaptive-orchestrator",
            )
        ).evaluation

        finalized = FinalizeExecution(self._claim_registry).execute(
            FinalizeExecutionRequest(
                work_unit=work_unit,
                claim=outcome.claim,
                verdict=evaluation.verdict,
                dependencies=(),
                orchestration_id=run_id,
            )
        )
        self._observability.emit(
            "evaluation_finalized", orchestration_id=run_id, work_unit_id=work_unit_id,
            execution_id=outcome.execution.id, external_id=outcome.execution.external_id,
            role=request.agent, skills=list(request.skills), attempt=1,
            status=finalized.work_unit_state.value, verdict=evaluation.verdict.value,
            usage=self._extract_usage(raw_result),
        )
        self._observability.emit(
            "orchestration_completed", orchestration_id=run_id,
            status=finalized.work_unit_state.value, verdict=evaluation.verdict.value,
        )

        output = self._extract_output(raw_result)
        return RunOrchestrationResult(
            task_id=task_id,
            work_unit_id=work_unit_id,
            execution_id=outcome.execution.id,
            external_id=outcome.execution.external_id,
            runtime_status=runtime_status,
            work_unit_state=finalized.work_unit_state,
            verdict=evaluation.verdict,
            output=output,
            raw_result=raw_result,
            evidence=result_package.evidence,
        )

    @staticmethod
    def _extract_output(raw_result: object) -> str:
        if isinstance(raw_result, dict):
            output = raw_result.get("output")
            if isinstance(output, str):
                return output
        if raw_result is None:
            return ""
        return str(raw_result)

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
        }
        usage = {
            name: int(value)
            for name, keys in aliases.items()
            for key in keys
            if isinstance(value := candidate.get(key), int) and value >= 0
        }
        total = candidate.get("total_tokens")
        if isinstance(total, int) and total >= 0:
            usage["total_tokens"] = total
        elif {"input_tokens", "output_tokens"} <= usage.keys():
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
        return usage or None
