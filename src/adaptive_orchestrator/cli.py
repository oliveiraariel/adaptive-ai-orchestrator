from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Sequence

from application.run_orchestration import (
    RunOrchestration,
    RunOrchestrationError,
    RunOrchestrationRequest,
)
from domain.evaluation import EvaluationVerdict
from domain.execution_policy import AutonomyClass, ExecutionPolicy
from infrastructure.claim_registry import InMemoryClaimRegistry
from infrastructure.openclaw_adapter import OpenClawAdapter
from infrastructure.openclaw_gateway_client import (
    GatewayConfig,
    OpenClawGatewayClient,
    OpenClawGatewayError,
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
    run.add_argument("--objective", required=True)
    run.add_argument("--agent", default="main")
    run.add_argument("--skill", action="append", default=[])
    run.add_argument("--model")
    run.add_argument("--provider")
    run.add_argument("--tool", action="append", default=[])
    run.add_argument("--scope", default="")
    run.add_argument("--context", action="append", default=[])
    run.add_argument("--input", action="append", default=[])
    run.add_argument("--constraint", action="append", default=[])
    run.add_argument("--expected-output", action="append", default=[])
    run.add_argument("--accept", action="append", default=[])
    run.add_argument("--side-effect", action="append", default=[])
    run.add_argument("--allow-side-effect", action="append", default=[])
    run.add_argument("--deny-tool", action="append", default=[])
    run.add_argument(
        "--autonomy",
        choices=[item.value for item in AutonomyClass],
        default=AutonomyClass.AUTONOMOUS.value,
    )
    run.add_argument("--human-approved", action="store_true")
    run.add_argument(
        "--gateway-url",
        default=os.environ.get("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789"),
    )
    run.add_argument(
        "--wait-timeout-ms",
        type=int,
        default=int(os.environ.get("ADAPTIVE_GATEWAY_WAIT_TIMEOUT_MS", "120000")),
    )

    doctor = commands.add_parser(
        "doctor",
        help="Report inbound bridge prerequisites without revealing secrets.",
    )
    doctor.add_argument(
        "--gateway-url",
        default=os.environ.get("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789"),
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _doctor(args.gateway_url)

    if args.command == "run":
        return _run(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _doctor(gateway_url: str) -> int:
    payload = {
        "ok": True,
        "adaptive_version": __version__,
        "gateway_url": gateway_url,
        "gateway_token_available": bool(os.environ.get("OPENCLAW_GATEWAY_TOKEN")),
        "gateway_password_available": bool(
            os.environ.get("OPENCLAW_GATEWAY_PASSWORD")
        ),
        "auth_note": (
            "Credentials are read from OPENCLAW_GATEWAY_TOKEN or "
            "OPENCLAW_GATEWAY_PASSWORD and are never printed."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run(args: argparse.Namespace) -> int:
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    password = os.environ.get("OPENCLAW_GATEWAY_PASSWORD")

    policy = ExecutionPolicy(
        autonomy=AutonomyClass(args.autonomy),
        allowed_side_effects=tuple(args.allow_side_effect),
        denied_tools=tuple(args.deny_tool),
    )

    config = GatewayConfig(
        url=args.gateway_url,
        token=token,
        password=password,
        agent_wait_timeout_ms=args.wait_timeout_ms,
    )

    try:
        runtime = OpenClawAdapter(OpenClawGatewayClient(config))
        result = RunOrchestration(
            runtime=runtime,
            claim_registry=InMemoryClaimRegistry(),
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

    accepted = result.verdict in {
        EvaluationVerdict.ACCEPTED,
        EvaluationVerdict.ACCEPTED_WITH_CONDITIONS,
    }
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


if __name__ == "__main__":
    raise SystemExit(main())
