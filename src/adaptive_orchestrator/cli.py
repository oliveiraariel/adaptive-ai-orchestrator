from __future__ import annotations

import argparse
import json
import os
import sys
import time
from uuid import uuid4
from application.observability import JsonlObservabilitySink, canonical_observability_path
from pathlib import Path
from typing import Sequence

from application.continuous_project_orchestration import (
    RunContinuousProjectOrchestration,
)
from application.execution_liveness import (
    ExecutionLiveness,
    ExecutionLivenessMonitor,
    ExecutionLivenessState,
    ExecutionLivenessTimeout,
)
from application.run_orchestration import (
    RunOrchestration,
    RunOrchestrationError,
    RunOrchestrationRequest,
)
from application.investigation_strategy import RuntimeRecoveryStrategist
from application.persistent_recovery import PersistentRecoveryCoordinator
from application.orchestration_supervisor import ProjectOrchestrationSupervisor
from application.run_project_orchestration import (
    ProjectOrchestrationError,
    ProjectOrchestrationRequest,
    ProjectRunStatus,
)
from application.runtime_project_planner import (
    ProjectPlanningError,
    ProjectPlanningRequest,
    RuntimeProjectPlanner,
)
from application.skill_resolution import SkillResolutionError
from domain.evaluation import EvaluationVerdict
from domain.execution_policy import AutonomyClass, ExecutionPolicy
from infrastructure.claim_registry import InMemoryClaimRegistry
from infrastructure.execution_liveness_store import (
    ExecutionLivenessStoreError,
    FileExecutionLivenessStore,
)
from infrastructure.openclaw_adapter import OpenClawAdapter
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
    ProjectOrchestrationCheckpointError,
)
from infrastructure.openclaw_gateway_client import (
    GatewayConfig,
    OpenClawGatewayClient,
    OpenClawGatewayError,
)
from infrastructure.result_store import FileResultStore, ResultStoreError
from infrastructure.skill_registry_loader import (
    SkillRegistryError,
    load_skill_profiles,
)

from adaptive_orchestrator import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adaptive-orchestrator",
        description="Run the Adaptive AI Orchestrator through a runtime adapter.",
    )
    parser.add_argument("--version", action="version", version=__version__)

    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser(
        "run",
        help="Execute one governed Work Unit through the Adaptive core.",
    )
    _add_single_work_unit_arguments(run)
    dispatch = commands.add_parser("dispatch", help="Dispatch one Work Unit without waiting for its result.")
    _add_single_work_unit_arguments(dispatch)
    wait = commands.add_parser("wait", help="Recover and observe a previously dispatched execution.")
    wait.add_argument("--external-id", required=True)
    wait.add_argument(
        "--heartbeat-interval-seconds",
        type=float,
        default=float(os.environ.get("ADAPTIVE_HEARTBEAT_INTERVAL_SECONDS", "30")),
        help="Seconds between runtime-confirmed liveness observations.",
    )
    wait.add_argument(
        "--liveness-timeout-seconds",
        type=float,
        default=float(os.environ.get("ADAPTIVE_LIVENESS_TIMEOUT_SECONDS", "90")),
        help="Silence window before an execution is marked SUSPECT; it is not cancelled.",
    )
    wait.add_argument(
        "--hard-deadline-seconds",
        type=float,
        default=float(os.environ.get("ADAPTIVE_EXECUTION_HARD_DEADLINE_SECONDS", "600")),
        help="Maximum observer lifetime. Reaching it never redispatches or cancels the run.",
    )
    _add_gateway_arguments(wait)

    orchestrate = commands.add_parser(
        "orchestrate",
        help=(
            "Plan and continuously execute a synchronized multi-Work-Unit project "
            "graph with bounded parallel workers."
        ),
    )
    _add_project_arguments(orchestrate)

    resume_project = commands.add_parser(
        "resume-project",
        help=(
            "Resume a durably checkpointed multi-Work-Unit project without "
            "redispatching already active workers."
        ),
    )
    resume_project.add_argument("--orchestration-id", required=True)
    resume_project.add_argument(
        "--session-id",
        default=os.environ.get("ADAPTIVE_SESSION_ID"),
    )
    resume_project.add_argument("--skill-registry")
    _add_gateway_arguments(resume_project)

    pause_project = commands.add_parser(
        "pause-project",
        help=(
            "Request a graceful pause for a durably checkpointed project. "
            "No new workers are dispatched; active work is allowed to settle."
        ),
    )
    pause_project.add_argument("--orchestration-id", required=True)
    pause_project.add_argument(
        "--project-root",
        default=os.environ.get("ADAPTIVE_PROJECT_ROOT") or os.getcwd(),
    )

    supervise_projects = commands.add_parser(
        "supervise-projects",
        help=(
            "Reconcile non-terminal checkpointed projects and resume only those "
            "whose controller heartbeat is missing/stale. Use --watch for an "
            "active persistence loop."
        ),
    )
    supervise_projects.add_argument("--watch", action="store_true")
    supervise_projects.add_argument("--interval-seconds", type=float, default=15.0)
    supervise_projects.add_argument("--stale-after-seconds", type=float, default=45.0)
    supervise_projects.add_argument(
        "--session-id",
        default=os.environ.get("ADAPTIVE_SESSION_ID"),
    )
    supervise_projects.add_argument("--skill-registry")
    _add_gateway_arguments(supervise_projects)

    doctor = commands.add_parser(
        "doctor",
        help="Report inbound bridge prerequisites without revealing secrets.",
    )
    doctor.add_argument(
        "--gateway-url",
        default=os.environ.get("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789"),
    )

    return parser


def _add_single_work_unit_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--objective", required=True)
    parser.add_argument("--session-id", default=os.environ.get("ADAPTIVE_SESSION_ID"))
    parser.add_argument("--agent", default="main")
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--model")
    parser.add_argument("--provider")
    parser.add_argument("--tool", action="append", default=[])
    parser.add_argument("--scope", default="")
    parser.add_argument("--project-id", default=os.environ.get("ADAPTIVE_PROJECT_ID"))
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--expected-output", action="append", default=[])
    parser.add_argument("--accept", action="append", default=[])
    parser.add_argument("--side-effect", action="append", default=[])
    _add_policy_arguments(parser)
    _add_gateway_arguments(parser)


def _add_project_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--objective", required=True)
    parser.add_argument("--session-id", default=os.environ.get("ADAPTIVE_SESSION_ID"))
    parser.add_argument("--agent", default="main")
    parser.add_argument("--planner-agent")
    parser.add_argument("--scope", default="")
    parser.add_argument("--context", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--skill-registry")
    parser.add_argument("--plan-file")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--max-work-units", type=int, default=24)
    parser.add_argument("--max-waves", type=int, default=24)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument(
        "--max-strategies",
        type=int,
        default=2,
        help=(
            "Maximum distinct worker strategies per Work Unit before "
            "project-level recovery is required."
        ),
    )
    parser.add_argument("--max-replans", type=int, default=2)
    parser.add_argument(
        "--persistent-recovery",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Keep strategy-exhausted technical work in strategist-guided recovery "
            "epochs until success, a governed human/external stop, or developer pause."
        ),
    )
    parser.add_argument(
        "--max-recovery-epochs",
        type=int,
        default=0,
        help="Optional recovery epoch cap; 0 means no fixed cap.",
    )
    parser.add_argument("--recovery-strategist-agent")
    parser.add_argument(
        "--learning-after-successful-retest",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Automatically trigger incident learning/dissemination after a recovery "
            "retest reaches ACCEPTED."
        ),
    )
    parser.add_argument("--dependency-context-chars", type=int, default=6000)
    _add_policy_arguments(parser)
    _add_gateway_arguments(parser)


def _add_policy_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--allow-side-effect", action="append", default=[])
    parser.add_argument("--deny-tool", action="append", default=[])
    parser.add_argument(
        "--autonomy",
        choices=[item.value for item in AutonomyClass],
        default=AutonomyClass.AUTONOMOUS.value,
    )
    parser.add_argument("--human-approved", action="store_true")


def _add_gateway_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--gateway-url",
        default=os.environ.get("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789"),
    )
    parser.add_argument(
        "--wait-timeout-ms",
        type=int,
        default=int(os.environ.get("ADAPTIVE_GATEWAY_WAIT_TIMEOUT_MS", "120000")),
    )
    parser.add_argument(
        "--project-root",
        default=os.environ.get("ADAPTIVE_PROJECT_ROOT") or os.getcwd(),
        help=(
            "Project root that owns .adaptive/runs. Defaults to ADAPTIVE_PROJECT_ROOT "
            "or the current working directory."
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _doctor(args.gateway_url)
    if args.command == "run":
        return _run(args)
    if args.command == "dispatch":
        return _dispatch(args)
    if args.command == "wait":
        return _wait(args)
    if args.command == "orchestrate":
        return _orchestrate(args)
    if args.command == "resume-project":
        return _resume_project(args)
    if args.command == "pause-project":
        return _pause_project(args)
    if args.command == "supervise-projects":
        return _supervise_projects(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _doctor(gateway_url: str) -> int:
    registry = _find_skill_registry(required=False)
    payload = {
        "ok": True,
        "adaptive_version": __version__,
        "gateway_url": gateway_url,
        "gateway_token_available": bool(os.environ.get("OPENCLAW_GATEWAY_TOKEN")),
        "gateway_password_available": bool(
            os.environ.get("OPENCLAW_GATEWAY_PASSWORD")
        ),
        "skill_registry_available": registry is not None,
        "skill_registry_path": str(registry) if registry is not None else None,
        "auth_note": (
            "Credentials are read from OPENCLAW_GATEWAY_TOKEN or "
            "OPENCLAW_GATEWAY_PASSWORD and are never printed."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run(args: argparse.Namespace) -> int:
    policy = _execution_policy(args)
    observability = JsonlObservabilitySink(canonical_observability_path(), args.session_id)

    try:
        runtime = _runtime(args)
        result = RunOrchestration(
            runtime=runtime,
            claim_registry=InMemoryClaimRegistry(),
            observability=observability,
        ).execute(
            RunOrchestrationRequest(
                objective=args.objective,
                agent=args.agent,
                skills=tuple(args.skill),
                model=args.model,
                provider=args.provider,
                tools=tuple(args.tool),
                scope=args.scope,
                project_id=(
                    args.project_id
                    or Path(args.project_root).expanduser().resolve().name
                ),
                context=tuple(args.context),
                inputs=tuple(args.input),
                constraints=tuple(args.constraint),
                expected_output=tuple(args.expected_output) or ("agent response",),
                acceptance_criteria=tuple(args.accept) or ("runtime-completed",),
                execution_policy=policy,
                requested_side_effects=tuple(args.side_effect),
                human_approved=args.human_approved,
            )
        )
    except (
        RunOrchestrationError,
        OpenClawGatewayError,
        ValueError,
        ResultStoreError,
    ) as exc:
        return _print_error(exc)

    accepted = result.verdict is EvaluationVerdict.ACCEPTED
    observability.emit(
        "work_unit_status_changed",
        orchestration_id=result.task_id.removeprefix("task:"),
        work_unit_id=result.work_unit_id,
        execution_id=result.execution_id,
        external_id=result.external_id,
        skills=list(args.skill),
        model=args.model,
        provider=args.provider,
        attempt=1,
        status=result.work_unit_state.value,
        runtime_status=result.runtime_status.value,
        verdict=result.verdict.value,
        usage=RunOrchestration._extract_usage(result.raw_result),
    )
    print(
        json.dumps(
            {
                "ok": accepted,
                "task_id": result.task_id,
                "work_unit_id": result.work_unit_id,
                "execution_id": result.execution_id,
                "external_id": result.external_id,
                "runtime_status": result.runtime_status.value,
                "work_unit_state": result.work_unit_state.value,
                "verdict": result.verdict.value,
                "output": result.output,
                "evidence": list(result.evidence),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if accepted else 3

def _request_from_args(args: argparse.Namespace) -> RunOrchestrationRequest:
    return RunOrchestrationRequest(objective=args.objective, agent=args.agent, skills=tuple(args.skill), model=args.model, provider=args.provider, tools=tuple(args.tool), scope=args.scope, context=tuple(args.context), inputs=tuple(args.input), constraints=tuple(args.constraint), expected_output=tuple(args.expected_output) or ("agent response",), acceptance_criteria=tuple(args.accept) or ("runtime-completed",), execution_policy=_execution_policy(args), requested_side_effects=tuple(args.side_effect), human_approved=args.human_approved)

def _dispatch(args: argparse.Namespace) -> int:
    try:
        result = RunOrchestration(
            runtime=_runtime(args),
            claim_registry=InMemoryClaimRegistry(),
        ).dispatch(_request_from_args(args))
        execution = result.execution
    except (
        RunOrchestrationError,
        OpenClawGatewayError,
        ValueError,
        ResultStoreError,
    ) as exc:
        return _print_error(exc)

    # Liveness persistence happens after the runtime has already accepted the
    # work. Never turn a liveness-file failure into an apparent dispatch
    # failure, because a caller could otherwise redispatch the same task.
    liveness_persisted = True
    liveness_warning = None
    now = time.time()
    try:
        FileExecutionLivenessStore(
            project_root=Path(args.project_root).expanduser().resolve()
        ).write(
            ExecutionLiveness(
                external_id=execution.external_id,
                execution_id=execution.id,
                runtime=execution.runtime,
                state=ExecutionLivenessState.SUBMITTED,
                heartbeat_sequence=0,
                started_at=now,
                last_heartbeat_at=now,
                last_progress_at=now,
                source="dispatch",
            )
        )
    except (ExecutionLivenessStoreError, OSError, ValueError) as exc:
        liveness_persisted = False
        liveness_warning = type(exc).__name__

    print(
        json.dumps(
            {
                "ok": True,
                "task_id": result.task_id,
                "work_unit_id": result.work_unit_id,
                "execution_id": execution.id,
                "external_id": execution.external_id,
                "runtime": execution.runtime,
                "runtime_status": execution.status.value,
                "liveness_persisted": liveness_persisted,
                "liveness_warning": liveness_warning,
            },
            sort_keys=True,
        )
    )
    return 0


def _wait(args: argparse.Namespace) -> int:
    try:
        runtime = _runtime(args)
        execution = runtime.recover_execution(args.external_id)
        liveness_store = FileExecutionLivenessStore(
            project_root=Path(args.project_root).expanduser().resolve()
        )
        monitor = ExecutionLivenessMonitor(
            runtime=runtime,
            store=liveness_store,
            heartbeat_interval_seconds=args.heartbeat_interval_seconds,
            liveness_timeout_seconds=args.liveness_timeout_seconds,
            hard_deadline_seconds=args.hard_deadline_seconds,
        )

        def emit_heartbeat(snapshot: ExecutionLiveness) -> None:
            print(
                json.dumps(
                    {
                        "event": "execution-heartbeat",
                        "external_id": snapshot.external_id,
                        "execution_id": snapshot.execution_id,
                        "state": snapshot.state.value,
                        "sequence": snapshot.heartbeat_sequence,
                        "last_heartbeat_at": snapshot.last_heartbeat_at,
                        "last_progress_at": snapshot.last_progress_at,
                        "source": snapshot.source,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )

        def emit_observer_pulse(
            observed_execution,
            silence_seconds: float,
        ) -> None:
            print(
                json.dumps(
                    {
                        "event": "execution-observer-pulse",
                        "external_id": observed_execution.external_id,
                        "execution_id": observed_execution.id,
                        "state": "OBSERVATION_UNAVAILABLE",
                        "silence_seconds": round(max(0.0, silence_seconds), 3),
                        "action": "CONTINUE_SAME_RUN",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )

        result = monitor.wait(
            execution,
            on_heartbeat=emit_heartbeat,
            on_observer_pulse=emit_observer_pulse,
        )
        final_liveness = liveness_store.read(execution.external_id)
        print(
            json.dumps(
                {
                    "ok": True,
                    "external_id": execution.external_id,
                    "execution_id": execution.id,
                    "runtime": execution.runtime,
                    "runtime_status": result.execution.status.value,
                    "liveness": (
                        {
                            "state": final_liveness.state.value,
                            "sequence": final_liveness.heartbeat_sequence,
                            "last_heartbeat_at": final_liveness.last_heartbeat_at,
                            "last_progress_at": final_liveness.last_progress_at,
                            "source": final_liveness.source,
                        }
                        if final_liveness is not None
                        else None
                    ),
                    "result": result.raw_result,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (
        ExecutionLivenessStoreError,
        ExecutionLivenessTimeout,
        OpenClawGatewayError,
        ValueError,
        ResultStoreError,
    ) as exc:
        return _print_error(exc)


def _orchestrate(args: argparse.Namespace) -> int:
    orchestration_id = uuid4().hex
    observability = JsonlObservabilitySink(canonical_observability_path(), args.session_id)
    try:
        registry_path = (
            Path(args.skill_registry).expanduser().resolve()
            if args.skill_registry
            else _find_skill_registry(required=True)
        )
        assert registry_path is not None
        profiles = load_skill_profiles(registry_path)

        runtime = _runtime(args)
        claims = InMemoryClaimRegistry()
        planner_runner = RunOrchestration(runtime=runtime, claim_registry=claims)
        planner = RuntimeProjectPlanner(
            runner=planner_runner,
            skill_profiles=profiles,
        )
        persistent_recovery = PersistentRecoveryCoordinator(
            strategist=RuntimeRecoveryStrategist(runner=planner_runner)
        )

        if args.plan_only:
            planning_request = ProjectPlanningRequest(
                objective=args.objective,
                scope=args.scope,
                context=tuple(args.context),
                constraints=tuple(args.constraint),
                agent=args.planner_agent or args.agent,
                max_work_units=args.max_work_units,
                max_concurrency=args.max_concurrency,
            )
            plan = planner.plan(planning_request)
            observability.emit(
                "orchestration_completed", orchestration_id=orchestration_id,
                status="PLANNED", mode="plan-only",
                work_unit_count=len(plan.work_units),
            )
            print(json.dumps({
                "ok": True,
                "mode": "plan-only",
                "orchestration_id": orchestration_id,
                "plan_summary": plan.summary,
                "work_unit_count": len(plan.work_units),
                "work_units": [
                    {"id": unit.id, "objective": unit.objective, "role": unit.role,
                     "scope": unit.scope, "kind": unit.kind.value}
                    for unit in plan.work_units
                ],
                "dependencies": [
                    {"source_id": item.source_id, "target_id": item.target_id,
                     "required": item.required, "condition": item.condition}
                    for item in plan.dependencies
                ],
            }, sort_keys=True))
            return 0

        plan = None
        if args.plan_file:
            plan_path = Path(args.plan_file).expanduser().resolve()
            plan = RuntimeProjectPlanner.parse(
                plan_path.read_text(encoding="utf-8"),
                max_work_units=args.max_work_units,
            )

        checkpoint_store = FileProjectOrchestrationCheckpointStore(
            project_root=Path(args.project_root).expanduser().resolve()
        )
        result = RunContinuousProjectOrchestration(
            runtime=runtime,
            claim_registry=claims,
            planner=planner,
            skill_profiles=profiles,
            checkpoint_store=checkpoint_store,
            persistent_recovery=persistent_recovery,
        ).execute(
            ProjectOrchestrationRequest(
                objective=args.objective,
                orchestration_id=orchestration_id,
                agent=args.agent,
                planner_agent=args.planner_agent,
                scope=args.scope,
                context=tuple(args.context),
                constraints=tuple(args.constraint),
                max_concurrency=args.max_concurrency,
                max_work_units=args.max_work_units,
                max_waves=args.max_waves,
                max_attempts_per_work_unit=args.max_attempts,
                max_strategies_per_work_unit=args.max_strategies,
                max_replans=args.max_replans,
                persistent_recovery=args.persistent_recovery,
                max_recovery_epochs=args.max_recovery_epochs,
                recovery_strategist_agent=args.recovery_strategist_agent,
                learning_after_successful_retest=args.learning_after_successful_retest,
                dependency_context_chars=args.dependency_context_chars,
                execution_policy=_execution_policy(args),
                human_approved=args.human_approved,
                plan=plan,
            ),
            observability=observability,
        )
    except (
        OSError,
        ProjectOrchestrationError,
        ProjectPlanningError,
        RunOrchestrationError,
        SkillRegistryError,
        SkillResolutionError,
        OpenClawGatewayError,
        ResultStoreError,
        ProjectOrchestrationCheckpointError,
        ValueError,
    ) as exc:
        observability.emit(
            "orchestration_completed",
            orchestration_id=orchestration_id,
            status="FAILED",
            failure_category=_safe_failure_category(exc),
            failure_code=_safe_failure_code(exc),
        )
        return _print_error(exc)

    completed = result.status is ProjectRunStatus.COMPLETED
    stop_reasons = sorted(
        {
            record.reason
            for record in result.records
            if record.status == "BLOCKED" and record.reason
        }
    )
    requires_human_decision = any(
        reason.startswith("circuit-breaker:")
        or reason.startswith("worker-blocked:HUMAN_DECISION")
        or reason.startswith("worker-blocked:AUTHORITY")
        for reason in stop_reasons
    )
    print(
        json.dumps(
            {
                "ok": completed,
                "orchestration_id": result.orchestration_id,
                "status": result.status.value,
                "plan_summary": result.plan_summary,
                "work_unit_count": result.work_unit_count,
                "completed_work_unit_ids": list(result.completed_work_unit_ids),
                "blocked_work_unit_ids": list(result.blocked_work_unit_ids),
                "recovery_required_work_unit_ids": list(
                    result.recovery_required_work_unit_ids
                ),
                "unfinished_work_unit_ids": list(result.unfinished_work_unit_ids),
                "max_parallelism_observed": result.max_parallelism_observed,
                "replan_count": result.replan_count,
                "stop_reasons": stop_reasons,
                "requires_human_decision": requires_human_decision,
                "dispatch_generations": [
                    {
                        "generation": wave.wave,
                        "ready_work_unit_ids": list(wave.ready_work_unit_ids),
                        "selected_work_unit_ids": list(wave.selected_work_unit_ids),
                        "conflict_deferred_ids": list(wave.conflict_deferred_ids),
                    }
                    for wave in result.waves
                ],
                # Compatibility alias for callers that consumed v0.4 pre-merge
                # project-mode output while dispatch generations were named waves.
                "waves": [
                    {
                        "wave": wave.wave,
                        "ready_work_unit_ids": list(wave.ready_work_unit_ids),
                        "selected_work_unit_ids": list(wave.selected_work_unit_ids),
                        "conflict_deferred_ids": list(wave.conflict_deferred_ids),
                    }
                    for wave in result.waves
                ],
                "records": [
                    {
                        "work_unit_id": record.work_unit_id,
                        "role": record.role,
                        "wave": record.wave,
                        "attempt": record.attempt,
                        "status": record.status,
                        "skills": list(record.skills),
                        "execution_id": record.execution_id,
                        "external_id": record.external_id,
                        "runtime_status": record.runtime_status,
                        "verdict": record.verdict,
                        "output": record.output,
                        "result_ref": record.result_ref,
                        "result_authoritative": record.result_authoritative,
                        "reason": record.reason,
                        "strategy": record.strategy,
                    }
                    for record in result.records
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if completed else 3


def _resume_project(args: argparse.Namespace) -> int:
    observability = JsonlObservabilitySink(
        canonical_observability_path(),
        args.session_id,
    )
    try:
        registry_path = (
            Path(args.skill_registry).expanduser().resolve()
            if args.skill_registry
            else _find_skill_registry(required=True)
        )
        assert registry_path is not None
        profiles = load_skill_profiles(registry_path)
        runtime = _runtime(args)
        claims = InMemoryClaimRegistry()
        recovery_runner = RunOrchestration(
            runtime=runtime,
            claim_registry=claims,
        )
        planner = RuntimeProjectPlanner(
            runner=recovery_runner,
            skill_profiles=profiles,
        )
        persistent_recovery = PersistentRecoveryCoordinator(
            strategist=RuntimeRecoveryStrategist(runner=recovery_runner)
        )
        checkpoint_store = FileProjectOrchestrationCheckpointStore(
            project_root=Path(args.project_root).expanduser().resolve()
        )
        result = RunContinuousProjectOrchestration(
            runtime=runtime,
            claim_registry=claims,
            planner=planner,
            skill_profiles=profiles,
            checkpoint_store=checkpoint_store,
            persistent_recovery=persistent_recovery,
        ).resume(
            args.orchestration_id,
            observability=observability,
        )
    except (
        OSError,
        ProjectOrchestrationError,
        ProjectPlanningError,
        RunOrchestrationError,
        SkillRegistryError,
        SkillResolutionError,
        OpenClawGatewayError,
        ResultStoreError,
        ProjectOrchestrationCheckpointError,
        ValueError,
    ) as exc:
        observability.emit(
            "orchestration_completed",
            orchestration_id=args.orchestration_id,
            status="FAILED",
            failure_category=_safe_failure_category(exc),
            failure_code=_safe_failure_code(exc),
        )
        return _print_error(exc)

    completed = result.status is ProjectRunStatus.COMPLETED
    print(
        json.dumps(
            {
                "ok": completed,
                "mode": "resume-project",
                "orchestration_id": result.orchestration_id,
                "status": result.status.value,
                "plan_summary": result.plan_summary,
                "work_unit_count": result.work_unit_count,
                "completed_work_unit_ids": list(result.completed_work_unit_ids),
                "blocked_work_unit_ids": list(result.blocked_work_unit_ids),
                "recovery_required_work_unit_ids": list(
                    result.recovery_required_work_unit_ids
                ),
                "unfinished_work_unit_ids": list(result.unfinished_work_unit_ids),
                "max_parallelism_observed": result.max_parallelism_observed,
                "replan_count": result.replan_count,
                "dispatch_generations": [
                    {
                        "generation": wave.wave,
                        "ready_work_unit_ids": list(wave.ready_work_unit_ids),
                        "selected_work_unit_ids": list(wave.selected_work_unit_ids),
                        "conflict_deferred_ids": list(wave.conflict_deferred_ids),
                    }
                    for wave in result.waves
                ],
                "records": [
                    {
                        "work_unit_id": record.work_unit_id,
                        "role": record.role,
                        "wave": record.wave,
                        "attempt": record.attempt,
                        "status": record.status,
                        "skills": list(record.skills),
                        "execution_id": record.execution_id,
                        "external_id": record.external_id,
                        "runtime_status": record.runtime_status,
                        "verdict": record.verdict,
                        "output": record.output,
                        "result_ref": record.result_ref,
                        "result_authoritative": record.result_authoritative,
                        "reason": record.reason,
                        "strategy": record.strategy,
                    }
                    for record in result.records
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if completed else 3


def _supervise_projects(args: argparse.Namespace) -> int:
    if args.interval_seconds <= 0:
        return _print_error(ValueError("interval-seconds must be positive"))
    if args.stale_after_seconds <= 0:
        return _print_error(ValueError("stale-after-seconds must be positive"))

    project_root = Path(args.project_root).expanduser().resolve()
    try:
        supervisor = ProjectOrchestrationSupervisor(
            project_root=project_root,
            stale_after_seconds=args.stale_after_seconds,
        )
    except (OSError, ValueError, ProjectOrchestrationCheckpointError) as exc:
        return _print_error(exc)

    def resume_one(orchestration_id: str) -> None:
        child = argparse.Namespace(**vars(args))
        child.command = "resume-project"
        child.orchestration_id = orchestration_id
        code = _resume_project(child)
        if code not in {0, 3}:
            raise ProjectOrchestrationError(
                f"Automatic resume failed for {orchestration_id} with exit code {code}."
            )

    while True:
        try:
            directives = supervisor.directives()
            resumed = supervisor.run_once(resume_one)
        except (
            OSError,
            ProjectOrchestrationError,
            ProjectOrchestrationCheckpointError,
            ValueError,
        ) as exc:
            return _print_error(exc)

        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "supervise-projects",
                    "watch": bool(args.watch),
                    "resumed_orchestration_ids": list(resumed),
                    "directives": [
                        {
                            "orchestration_id": item.orchestration_id,
                            "action": item.action,
                            "reason": item.reason,
                            "desired_state": item.desired_state,
                            "active_execution_count": item.active_execution_count,
                            "last_controller_heartbeat_at": item.last_controller_heartbeat_at,
                        }
                        for item in directives
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        if not args.watch:
            return 0
        time.sleep(args.interval_seconds)


def _pause_project(args: argparse.Namespace) -> int:
    try:
        store = FileProjectOrchestrationCheckpointStore(
            project_root=Path(args.project_root).expanduser().resolve()
        )
        checkpoint = store.load(args.orchestration_id)
        if checkpoint is None:
            raise ProjectOrchestrationError(
                f"No project checkpoint exists for orchestration '{args.orchestration_id}'."
            )
        checkpoint["desired_state"] = "PAUSED"
        store.save(args.orchestration_id, checkpoint)
        active = checkpoint.get("active_executions")
        records = checkpoint.get("records")
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "pause-project",
                    "orchestration_id": args.orchestration_id,
                    "desired_state": "PAUSED",
                    "active_executions": active if isinstance(active, list) else [],
                    "work_unit_states": checkpoint.get("work_unit_states", {}),
                    "attempts": checkpoint.get("attempts", {}),
                    "strategy_generations": checkpoint.get(
                        "strategy_generations", {}
                    ),
                    "recovery_epoch_counts": checkpoint.get(
                        "recovery_epoch_counts", {}
                    ),
                    "recent_records": (
                        records[-10:] if isinstance(records, list) else []
                    ),
                    "note": (
                        "Pause is graceful: no new work is dispatched after the "
                        "controller observes the request; already active work may "
                        "settle before the invocation returns PAUSED."
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (
        OSError,
        ProjectOrchestrationError,
        ProjectOrchestrationCheckpointError,
        ValueError,
    ) as exc:
        return _print_error(exc)


def _execution_policy(args: argparse.Namespace) -> ExecutionPolicy:
    return ExecutionPolicy(
        autonomy=AutonomyClass(args.autonomy),
        allowed_side_effects=tuple(args.allow_side_effect),
        denied_tools=tuple(args.deny_tool),
    )


def _runtime(args: argparse.Namespace) -> OpenClawAdapter:
    observability = JsonlObservabilitySink(canonical_observability_path())
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise ValueError(
            f"Adaptive project root does not exist or is not a directory: {project_root}"
        )
    config = GatewayConfig(
        url=args.gateway_url,
        token=os.environ.get("OPENCLAW_GATEWAY_TOKEN"),
        password=os.environ.get("OPENCLAW_GATEWAY_PASSWORD"),
        agent_wait_timeout_ms=args.wait_timeout_ms,
    )
    result_store = FileResultStore(project_root=project_root)
    return OpenClawAdapter(
        OpenClawGatewayClient(config, result_store=result_store),
        observability=observability,
    )


def _find_skill_registry(*, required: bool) -> Path | None:
    explicit_root = os.environ.get("ARIEL_AGENT_SKILLS_ROOT")
    candidates: list[Path] = []
    if explicit_root:
        candidates.append(
            Path(explicit_root).expanduser().resolve() / "registry" / "skills.json"
        )

    repository_root = Path(__file__).resolve().parents[2]
    candidates.append(
        repository_root.parent / "ariel-agent-skills" / "registry" / "skills.json"
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    if required:
        raise SkillRegistryError(
            "Ariel Agent Skills registry not found. Set ARIEL_AGENT_SKILLS_ROOT, "
            "pass --skill-registry, or keep ariel-agent-skills as a sibling repository."
        )
    return None


def _print_error(exc: Exception) -> int:
    print(
        json.dumps(
            {
                "ok": False,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def _safe_failure_category(exc: Exception) -> str:
    if isinstance(exc, (ProjectPlanningError, ProjectOrchestrationError)):
        return "planning"
    if isinstance(exc, (OpenClawGatewayError, RunOrchestrationError)):
        return "runtime"
    if isinstance(exc, (SkillRegistryError, SkillResolutionError)):
        return "configuration"
    if isinstance(exc, (OSError, ResultStoreError)):
        return "environment"
    if isinstance(exc, ValueError):
        return "validation"
    return "unknown"


def _safe_failure_code(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, (ProjectPlanningError, ProjectOrchestrationError)):
        if "json" in message:
            return "planner_invalid_json"
        if "plan" in message:
            return "planner_invalid_plan"
        return "planner_failed"
    if isinstance(exc, OpenClawGatewayError):
        return "openclaw_gateway_failed"
    if isinstance(exc, RunOrchestrationError):
        return "orchestration_runtime_failed"
    if isinstance(exc, SkillRegistryError):
        return "skill_registry_failed"
    if isinstance(exc, SkillResolutionError):
        return "skill_resolution_failed"
    if isinstance(exc, ResultStoreError):
        return "result_store_failed"
    if isinstance(exc, OSError):
        return "environment_io_failed"
    if isinstance(exc, ValueError):
        return "validation_failed"
    return "unknown_failure"


if __name__ == "__main__":
    raise SystemExit(main())
