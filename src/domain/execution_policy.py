from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class ExecutionPolicyError(ValueError):
    """Raised when execution-policy invariants are violated."""


class AutonomyClass(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"
    AUTONOMOUS_WITH_REVIEW = "AUTONOMOUS_WITH_REVIEW"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    HUMAN_EXECUTION_REQUIRED = "HUMAN_EXECUTION_REQUIRED"
    FORBIDDEN = "FORBIDDEN"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"
    REQUIRE_HUMAN_EXECUTION = "REQUIRE_HUMAN_EXECUTION"
    DENY = "DENY"


@dataclass(frozen=True)
class ExecutionPolicy:
    """Runtime-neutral authority and side-effect policy for one delegated task.

    An empty ``allowed_side_effects`` tuple means that the task declares no
    authorized side effects. Read-only work therefore remains safe by default.
    ``denied_tools`` is a deny-list because an empty allow-list would make
    existing runtime configurations unusable by default.
    """

    autonomy: AutonomyClass = AutonomyClass.AUTONOMOUS
    allowed_side_effects: Tuple[str, ...] = field(default_factory=tuple)
    denied_tools: Tuple[str, ...] = field(default_factory=tuple)
    require_independent_review: bool = False

    def __post_init__(self) -> None:
        if any(not item.strip() for item in self.allowed_side_effects):
            raise ExecutionPolicyError(
                "Allowed side-effect identifiers must not be blank."
            )
        if any(not item.strip() for item in self.denied_tools):
            raise ExecutionPolicyError("Denied tool identifiers must not be blank.")

    @property
    def independent_review_required(self) -> bool:
        return (
            self.require_independent_review
            or self.autonomy is AutonomyClass.AUTONOMOUS_WITH_REVIEW
        )

    def decide(
        self,
        *,
        human_approved: bool,
        requested_side_effects: Tuple[str, ...] = (),
        requested_tools: Tuple[str, ...] = (),
    ) -> PolicyDecision:
        if any(tool in self.denied_tools for tool in requested_tools):
            return PolicyDecision.DENY

        allowed_effects = set(self.allowed_side_effects)
        if any(effect not in allowed_effects for effect in requested_side_effects):
            return PolicyDecision.DENY

        if self.autonomy is AutonomyClass.FORBIDDEN:
            return PolicyDecision.DENY

        if self.autonomy is AutonomyClass.HUMAN_EXECUTION_REQUIRED:
            return PolicyDecision.REQUIRE_HUMAN_EXECUTION

        if (
            self.autonomy is AutonomyClass.HUMAN_APPROVAL_REQUIRED
            and not human_approved
        ):
            return PolicyDecision.REQUIRE_HUMAN_APPROVAL

        return PolicyDecision.ALLOW
