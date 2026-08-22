from dataclasses import dataclass, field
from typing import Tuple


class AgentProfileError(ValueError):
    """Raised when an AgentProfile invariant is violated."""


@dataclass(frozen=True)
class AgentId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise AgentProfileError("AgentId must not be empty.")


@dataclass
class AgentProfile:
    id: AgentId
    role: str
    responsibilities: Tuple[str, ...] = field(default_factory=tuple)
    capabilities: Tuple[str, ...] = field(default_factory=tuple)
    skills: Tuple[str, ...] = field(default_factory=tuple)
    tools: Tuple[str, ...] = field(default_factory=tuple)
    eligible_models: Tuple[str, ...] = field(default_factory=tuple)
    context_requirements: Tuple[str, ...] = field(default_factory=tuple)
    permissions: Tuple[str, ...] = field(default_factory=tuple)
    runtime: str | None = None
    evidence: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.role or not self.role.strip():
            raise AgentProfileError("AgentProfile role must not be empty.")

    @property
    def has_capability(self) -> bool:
        return bool(self.capabilities)

    def supports_capability(self, capability: str) -> bool:
        normalized = capability.strip()
        if not normalized:
            return False
        return normalized in self.capabilities

    def supports_skill(self, skill_id: str) -> bool:
        normalized = skill_id.strip()
        if not normalized:
            return False
        return normalized in self.skills

    def can_use_model(self, model_id: str) -> bool:
        normalized = model_id.strip()
        if not normalized:
            return False
        return not self.eligible_models or normalized in self.eligible_models
