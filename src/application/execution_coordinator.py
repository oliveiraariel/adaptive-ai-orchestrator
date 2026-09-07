from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, Tuple

from application.agent_runtime import AgentRuntime, AgentRuntimeError, ExecutionReference
from application.claim_registry import ClaimRegistry
from application.delegate_work import DelegateWork, DelegateWorkError, DelegateWorkRequest
from domain.dependency import Dependency
from domain.execution_claim import ExecutionClaim
from domain.execution_policy import PolicyDecision
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitKind, WorkUnitState
from domain.work_unit_readiness import ReadinessStatus, WorkUnitReadinessEvaluator


class DispatchStatus(str, Enum):
    DISPATCHED = "DISPATCHED"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class WorkAssignment:
    work_unit: WorkUnit
    configuration: ResourceConfiguration
    task_package: TaskPackage


@dataclass(frozen=True)
class DispatchFrontierRequest:
    assignments: Sequence[WorkAssignment]
    dependencies: Sequence[Dependency]
    claimant_id: str
    concurrency_limit: int
    active_execution_count: int = 0
    human_approved_work_unit_ids: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DispatchOutcome:
    work_unit_id: str
    status: DispatchStatus
    reason: str
    execution: ExecutionReference | None = None
    claim: ExecutionClaim | None = None


@dataclass(frozen=True)
class DispatchFrontierResult:
    outcomes: Tuple[DispatchOutcome, ...]

    @property
    def dispatched(self) -> Tuple[DispatchOutcome, ...]:
        return tuple(
            outcome
            for outcome in self.outcomes
            if outcome.status is DispatchStatus.DISPATCHED
        )


class ExecutionCoordinator:
    """Dispatches the safe ready frontier without depending on one harness.

    The coordinator intentionally stops at dispatch. Result monitoring,
    evaluation and dependency advancement remain separate orchestration
    responsibilities so the runtime port stays small and testable.
    """

    def __init__(
        self,
        *,
        runtime: AgentRuntime,
        claim_registry: ClaimRegistry,
        readiness_evaluator: WorkUnitReadinessEvaluator | None = None,
    ) -> None:
        self._runtime = runtime
        self._claim_registry = claim_registry
        self._readiness = readiness_evaluator or WorkUnitReadinessEvaluator()

    def dispatch_frontier(
        self,
        request: DispatchFrontierRequest,
    ) -> DispatchFrontierResult:
        claimant = request.claimant_id.strip()
        if not claimant:
            raise ValueError("claimant_id must not be empty.")
        if request.concurrency_limit < 1:
            raise ValueError("concurrency_limit must be at least 1.")
        if request.active_execution_count < 0:
            raise ValueError("active_execution_count must not be negative.")

        work_unit_ids = [assignment.work_unit.id.value for assignment in request.assignments]
        if len(work_unit_ids) != len(set(work_unit_ids)):
            raise ValueError("Frontier assignments must reference unique Work Units.")

        readiness = {
            item.work_unit_id: item
            for item in self._readiness.evaluate_all(
                [assignment.work_unit for assignment in request.assignments],
                request.dependencies,
            )
        }

        available_slots = max(
            0,
            request.concurrency_limit - request.active_execution_count,
        )
        approvals = set(request.human_approved_work_unit_ids)
        outcomes: list[DispatchOutcome] = []

        ordered = sorted(
            request.assignments,
            key=lambda assignment: (
                -assignment.work_unit.priority,
                assignment.work_unit.id.value,
            ),
        )

        for assignment in ordered:
            work_unit = assignment.work_unit
            work_unit_id = work_unit.id.value
            readiness_result = readiness[work_unit_id]

            if readiness_result.status is not ReadinessStatus.READY:
                outcomes.append(
                    DispatchOutcome(
                        work_unit_id=work_unit_id,
                        status=DispatchStatus.BLOCKED,
                        reason="work-unit-not-ready",
                    )
                )
                continue

            if work_unit.kind is WorkUnitKind.HUMAN_ACTION:
                outcomes.append(
                    DispatchOutcome(
                        work_unit_id=work_unit_id,
                        status=DispatchStatus.BLOCKED,
                        reason="human-action-work-unit",
                    )
                )
                continue

            policy_decision = assignment.task_package.execution_policy.decide(
                human_approved=work_unit_id in approvals,
                requested_side_effects=assignment.task_package.requested_side_effects,
                requested_tools=assignment.configuration.tools,
            )
            if policy_decision is not PolicyDecision.ALLOW:
                outcomes.append(
                    DispatchOutcome(
                        work_unit_id=work_unit_id,
                        status=DispatchStatus.BLOCKED,
                        reason=f"policy:{policy_decision.value}",
                    )
                )
                continue

            if available_slots == 0:
                outcomes.append(
                    DispatchOutcome(
                        work_unit_id=work_unit_id,
                        status=DispatchStatus.DEFERRED,
                        reason="concurrency-budget-exhausted",
                    )
                )
                continue

            claim = self._claim_registry.acquire(
                work_unit_id=work_unit_id,
                claimant_id=claimant,
            )
            if claim is None:
                outcomes.append(
                    DispatchOutcome(
                        work_unit_id=work_unit_id,
                        status=DispatchStatus.BLOCKED,
                        reason="work-unit-already-claimed",
                    )
                )
                continue

            if work_unit.state is WorkUnitState.PLANNED:
                work_unit.mark_ready()

            try:
                delegated = DelegateWork(self._runtime).execute(
                    DelegateWorkRequest(
                        work_unit=work_unit,
                        configuration=assignment.configuration,
                        task_package=assignment.task_package,
                        human_approved=work_unit_id in approvals,
                    )
                )
            except (DelegateWorkError, AgentRuntimeError, RuntimeError) as exc:
                self._claim_registry.release(claim)
                outcomes.append(
                    DispatchOutcome(
                        work_unit_id=work_unit_id,
                        status=DispatchStatus.FAILED,
                        reason=str(exc),
                    )
                )
                continue

            bound_claim = self._claim_registry.bind_execution(
                claim,
                execution_id=delegated.execution.id,
            )
            available_slots -= 1
            outcomes.append(
                DispatchOutcome(
                    work_unit_id=work_unit_id,
                    status=DispatchStatus.DISPATCHED,
                    reason="runtime-accepted",
                    execution=delegated.execution,
                    claim=bound_claim,
                )
            )

        return DispatchFrontierResult(outcomes=tuple(outcomes))
