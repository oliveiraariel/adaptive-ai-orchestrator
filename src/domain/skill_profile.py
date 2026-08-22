from dataclasses import dataclass, field
from typing import Tuple


class SkillProfileError(ValueError):
    """Raised when a SkillProfile invariant is violated."""


@dataclass(frozen=True)
class SkillId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise SkillProfileError("SkillId must not be empty.")


@dataclass
class SkillProfile:
    id: SkillId
    purpose: str
    capabilities: Tuple[str, ...] = field(default_factory=tuple)
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    outputs: Tuple[str, ...] = field(default_factory=tuple)
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    compatible_agents: Tuple[str, ...] = field(default_factory=tuple)
    compatible_models: Tuple[str, ...] = field(default_factory=tuple)
    compatible_runtimes: Tuple[str, ...] = field(default_factory=tuple)
    version: str = "1.0"
    evidence: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.purpose or not self.purpose.strip():
            raise SkillProfileError("SkillProfile purpose must not be empty.")
        if not self.version or not self.version.strip():
            raise SkillProfileError("SkillProfile version must not be empty.")

    def provides_capability(self, capability: str) -> bool:
        normalized = capability.strip()
        if not normalized:
            return False
        return normalized in self.capabilities

    def accepts_agent(self, agent_id: str) -> bool:
        normalized = agent_id.strip()
        if not normalized:
            return False
        return not self.compatible_agents or normalized in self.compatible_agents

    def accepts_model(self, model_id: str) -> bool:
        normalized = model_id.strip()
        if not normalized:
            return False
        return not self.compatible_models or normalized in self.compatible_models

    def accepts_runtime(self, runtime: str) -> bool:
        normalized = runtime.strip()
        if not normalized:
            return False
        return not self.compatible_runtimes or normalized in self.compatible_runtimes
