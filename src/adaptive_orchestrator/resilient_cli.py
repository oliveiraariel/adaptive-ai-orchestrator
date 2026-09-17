from __future__ import annotations

from typing import Sequence

from adaptive_orchestrator import cli as _cli
from adaptive_orchestrator.resilient_project_orchestration import (
    RunResilientProjectOrchestration,
)


# Keep the mature CLI parsing/output surface intact while replacing only the
# project orchestration composition root. Single-Work-Unit run/dispatch/wait
# behavior remains unchanged.
_cli.RunContinuousProjectOrchestration = RunResilientProjectOrchestration


def main(argv: Sequence[str] | None = None) -> int:
    return _cli.main(argv)
