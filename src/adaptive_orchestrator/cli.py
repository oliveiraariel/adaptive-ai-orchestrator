from __future__ import annotations

import argparse
import json
import os
import sys
from uuid import uuid4
from application.observability import JsonlObservabilitySink, canonical_observability_path
from pathlib import Path
from typing import Sequence

from application.continuous_project_orchestration import (
    RunContinuousProjectOrchestration,
)
from application.run_orchestration import (
    RunOrchestration,
    RunOrchestrationError,
    RunOrchestrationRequest,
)
from application.run_project_orchestration import (
    ProjectOrchestrationError,
    ProjectOrchestrationRequest,
    ProjectRunStatus,
)
from application.runtime_project_planner import (
    ProjectPlanningError,
    RuntimeProjectPlanner,
)
from application.skill_resolution import SkillResolutionError
from domain.evaluation import EvaluationVerdict
from domain.execution_policy import AutonomyClass, ExecutionPolicy
from infrastructure.claim_registry import InMemoryClaimRegistry
from infrastructure.openclaw_adapter import OpenClawAdapter
from infrastructure.openclaw_gateway_client import (
    GatewayConfig,
    OpenClawGatewayClient,
    OpenClawGatewayError,
)
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

    orchestrate = commands.add_parser(
        "orchestrate",
        help=(
            "Plan and continuously execute a synchronized multi-Work-Unit project "
            "graph with bounded parallel workers."
        ),
    )
    _add_project_arguments(orchestrate)

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
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--max-work-units", type=int, default=24)
    parser.add_argument("--max-waves", type=int, default=24)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--max-replans", type=int, default=2)
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _doctor(args.gateway_url)
    if args.command == "run":
        return _run(args)
    if args.command == "orchestrate":
        return _orchestrate(args)

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
    runtime = _runtime(args)
    observability = JsonlObservabilitySink(canonical_observability_path(), args.session_id)

    try:
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

        plan = None
        if args.plan_file:
            plan_path = Path(args.plan_file).expanduser().resolve()
            plan = RuntimeProjectPlanner.parse(
                plan_path.read_text(encoding="utf-8"),
                max_work_units=args.max_work_units,
            )

        result = RunContinuousProjectOrchestration(
            runtime=runtime,
            claim_registry=claims,
            planner=planner,
            skill_profiles=profiles,
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
                max_replans=args.max_replans,
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
        ValueError,
    ) as exc:
        if isinstance(exc, (ProjectPlanningError, ProjectOrchestrationError)):
            observability.emit(
                "orchestration_completed", orchestration_id=orchestration_id,
                status="FAILED", failure_category="planning",
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
                        "reason": record.reason,
                    }
                    for record in result.records
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if completed else 3


def _execution_policy(args: argparse.Namespace) -> ExecutionPolicy:
    return ExecutionPolicy(
        autonomy=AutonomyClass(args.autonomy),
        allowed_side_effects=tuple(args.allow_side_effect),
        denied_tools=tuple(args.deny_tool),
    )


def _runtime(args: argparse.Namespace) -> OpenClawAdapter:
    observability = JsonlObservabilitySink(canonical_observability_path())
    config = GatewayConfig(
        url=args.gateway_url,
        token=os.environ.get("OPENCLAW_GATEWAY_TOKEN"),
        password=os.environ.get("OPENCLAW_GATEWAY_PASSWORD"),
        agent_wait_timeout_ms=args.wait_timeout_ms,
    )
    return OpenClawAdapter(OpenClawGatewayClient(config), observability=observability)


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


def _safe_failure_code(exc: Exception) -> str:
    message = str(exc).lower()
    if "json" in message:
        return "planner_invalid_json"
    if "plan" in message:
        return "planner_invalid_plan"
    return "planner_failed"


if __name__ == "__main__":
    raise SystemExit(main())
