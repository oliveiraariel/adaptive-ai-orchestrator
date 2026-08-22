from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class ContinuityError(ValueError):
    """Raised when a continuity record invariant is violated."""


class ContinuityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class ContinuityRecord:
    project_id: str
    status: ContinuityStatus = ContinuityStatus.ACTIVE
    current_plan_version: int | None = None
    current_work_unit_ids: Tuple[str, ...] = field(default_factory=tuple)
    pending_work_unit_ids: Tuple[str, ...] = field(default_factory=tuple)
    decisions: Tuple[str, ...] = field(default_factory=tuple)
    evidence: Tuple[str, ...] = field(default_factory=tuple)
    open_issues: Tuple[str, ...] = field(default_factory=tuple)
    risks: Tuple[str, ...] = field(default_factory=tuple)
    context: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.project_id.strip():
            raise ContinuityError("ContinuityRecord project_id must not be empty.")

        if (
            self.current_plan_version is not None
            and self.current_plan_version < 1
        ):
            raise ContinuityError(
                "ContinuityRecord current_plan_version must be at least 1."
            )

    def update_plan_version(self, version: int) -> "ContinuityRecord":
        if version < 1:
            raise ContinuityError("Plan version must be at least 1.")

        return ContinuityRecord(
            project_id=self.project_id,
            status=self.status,
            current_plan_version=version,
            current_work_unit_ids=self.current_work_unit_ids,
            pending_work_unit_ids=self.pending_work_unit_ids,
            decisions=self.decisions,
            evidence=self.evidence,
            open_issues=self.open_issues,
            risks=self.risks,
            context=self.context,
        )

    def resume(self) -> "ContinuityRecord":
        return ContinuityRecord(
            project_id=self.project_id,
            status=ContinuityStatus.ACTIVE,
            current_plan_version=self.current_plan_version,
            current_work_unit_ids=self.current_work_unit_ids,
            pending_work_unit_ids=self.pending_work_unit_ids,
            decisions=self.decisions,
            evidence=self.evidence,
            open_issues=self.open_issues,
            risks=self.risks,
            context=self.context,
        )

    def pause(self) -> "ContinuityRecord":
        return ContinuityRecord(
            project_id=self.project_id,
            status=ContinuityStatus.PAUSED,
            current_plan_version=self.current_plan_version,
            current_work_unit_ids=self.current_work_unit_ids,
            pending_work_unit_ids=self.pending_work_unit_ids,
            decisions=self.decisions,
            evidence=self.evidence,
            open_issues=self.open_issues,
            risks=self.risks,
            context=self.context,
        )

    def complete(self) -> "ContinuityRecord":
        return ContinuityRecord(
            project_id=self.project_id,
            status=ContinuityStatus.COMPLETED,
            current_plan_version=self.current_plan_version,
            current_work_unit_ids=self.current_work_unit_ids,
            pending_work_unit_ids=self.pending_work_unit_ids,
            decisions=self.decisions,
            evidence=self.evidence,
            open_issues=self.open_issues,
            risks=self.risks,
            context=self.context,
        )
