from dataclasses import dataclass, field
from typing import Tuple


class ModelProfileError(ValueError):
    """Raised when a ModelProfile invariant is violated."""


@dataclass(frozen=True)
class ModelId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ModelProfileError("ModelId must not be empty.")


@dataclass
class ModelProfile:
    id: ModelId
    name: str
    version: str
    provider: str
    capabilities: Tuple[str, ...] = field(default_factory=tuple)
    context: int | None = None
    cost: str | None = None
    latency: str | None = None
    availability: str | None = None
    restrictions: Tuple[str, ...] = field(default_factory=tuple)
    evidence: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ModelProfileError("ModelProfile name must not be empty.")
        if not self.version or not self.version.strip():
            raise ModelProfileError("ModelProfile version must not be empty.")
        if not self.provider or not self.provider.strip():
            raise ModelProfileError("ModelProfile provider must not be empty.")
        if self.context is not None and self.context < 0:
            raise ModelProfileError("ModelProfile context must not be negative.")

    def supports_capability(self, capability: str) -> bool:
        normalized = capability.strip()
        if not normalized:
            return False
        return normalized in self.capabilities

    def has_restriction(self, restriction: str) -> bool:
        normalized = restriction.strip()
        if not normalized:
            return False
        return normalized in self.restrictions
