from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkerCompletionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class WorkerBlockerType(str, Enum):
    NONE = "NONE"
    HUMAN_DECISION = "HUMAN_DECISION"
    AUTHORITY = "AUTHORITY"
    ENVIRONMENT = "ENVIRONMENT"
    RUNTIME = "RUNTIME"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    UNKNOWN = "UNKNOWN"


_GENUINE_BLOCKERS = {
    WorkerBlockerType.HUMAN_DECISION,
    WorkerBlockerType.AUTHORITY,
    WorkerBlockerType.ENVIRONMENT,
    WorkerBlockerType.RUNTIME,
    WorkerBlockerType.EXTERNAL_DEPENDENCY,
}


@dataclass(frozen=True)
class WorkerCompletionSignal:
    status: WorkerCompletionStatus
    blocker_type: WorkerBlockerType = WorkerBlockerType.NONE
    unmet_criteria: tuple[str, ...] = ()
    structured: bool = False

    @property
    def is_genuine_blocker(self) -> bool:
        return (
            self.status is WorkerCompletionStatus.BLOCKED
            and self.blocker_type in _GENUINE_BLOCKERS
        )

    @property
    def is_terminal_success(self) -> bool:
        return (
            self.status is WorkerCompletionStatus.COMPLETE
            and not self.unmet_criteria
        )


def parse_worker_completion(output: str) -> WorkerCompletionSignal:
    """Parse the deterministic completion footer emitted by project workers.

    The footer is deliberately small and provider-neutral:

    ADAPTIVE_WORK_STATUS: COMPLETE|PARTIAL|BLOCKED
    ADAPTIVE_BLOCKER_TYPE: NONE|HUMAN_DECISION|AUTHORITY|ENVIRONMENT|RUNTIME|EXTERNAL_DEPENDENCY
    ADAPTIVE_UNMET_CRITERIA: NONE|criterion one; criterion two

    Missing markers preserve backwards compatibility by returning UNKNOWN.
    A worker cannot create a terminal success while simultaneously declaring
    unmet criteria. Likewise, BLOCKED without a recognized external blocker is
    not treated as a genuine stop condition by the orchestrator.
    """

    values: dict[str, str] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().upper()
        if normalized_key in {
            "ADAPTIVE_WORK_STATUS",
            "ADAPTIVE_BLOCKER_TYPE",
            "ADAPTIVE_UNMET_CRITERIA",
        }:
            values[normalized_key] = value.strip()

    raw_status = values.get("ADAPTIVE_WORK_STATUS")
    if raw_status is None:
        return WorkerCompletionSignal(status=WorkerCompletionStatus.UNKNOWN)

    try:
        status = WorkerCompletionStatus(raw_status.strip().upper())
    except ValueError:
        status = WorkerCompletionStatus.UNKNOWN

    raw_blocker = values.get("ADAPTIVE_BLOCKER_TYPE", "NONE").strip().upper()
    try:
        blocker_type = WorkerBlockerType(raw_blocker)
    except ValueError:
        blocker_type = WorkerBlockerType.UNKNOWN

    raw_unmet = values.get("ADAPTIVE_UNMET_CRITERIA", "NONE").strip()
    if not raw_unmet or raw_unmet.upper() == "NONE":
        unmet: tuple[str, ...] = ()
    else:
        unmet = tuple(
            item.strip()
            for item in raw_unmet.split(";")
            if item.strip()
        )

    if status is WorkerCompletionStatus.COMPLETE and unmet:
        status = WorkerCompletionStatus.PARTIAL

    return WorkerCompletionSignal(
        status=status,
        blocker_type=blocker_type,
        unmet_criteria=unmet,
        structured=True,
    )
