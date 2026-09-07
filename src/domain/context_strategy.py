from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class ContextPolicyError(ValueError):
    """Raised when context-transfer invariants are violated."""


class ContextStrategy(str, Enum):
    MINIMAL_INLINE = "MINIMAL_INLINE"
    POINTERS = "POINTERS"
    HYBRID = "HYBRID"
    FRESH = "FRESH"


@dataclass(frozen=True)
class ContextPolicy:
    """Describes how execution context should cross an agent boundary.

    The policy is intentionally metadata only. Runtime adapters decide how a
    pointer is resolved, how a fresh context is created, or how inline context
    is transported.
    """

    strategy: ContextStrategy = ContextStrategy.MINIMAL_INLINE
    pointers: Tuple[str, ...] = field(default_factory=tuple)
    contains_sensitive_data: bool = False
    redaction_applied: bool = False

    def __post_init__(self) -> None:
        if any(not pointer.strip() for pointer in self.pointers):
            raise ContextPolicyError("Context pointers must not be blank.")

        if self.strategy is ContextStrategy.POINTERS and not self.pointers:
            raise ContextPolicyError(
                "POINTERS strategy requires at least one context pointer."
            )

        if self.contains_sensitive_data and not self.redaction_applied:
            raise ContextPolicyError(
                "Sensitive context cannot cross an execution boundary without "
                "an explicit redaction declaration."
            )
