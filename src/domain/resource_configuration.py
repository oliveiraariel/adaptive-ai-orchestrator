from dataclasses import dataclass, field
from typing import Tuple


class ResourceConfigurationError(ValueError):
    """Raised when a ResourceConfiguration invariant is violated."""


@dataclass(frozen=True)
class ResourceConfiguration:
    agent: str
    skills: Tuple[str, ...] = field(default_factory=tuple)
    model: str | None = None
    provider: str | None = None
    thinking: str | None = None
    tools: Tuple[str, ...] = field(default_factory=tuple)
    runtime: str | None = None
    policy_constraints: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.agent or not self.agent.strip():
            raise ResourceConfigurationError(
                "ResourceConfiguration agent must not be empty."
            )

        if self.model is not None and not self.model.strip():
            raise ResourceConfigurationError(
                "ResourceConfiguration model must not be blank when provided."
            )

        if self.provider is not None and not self.provider.strip():
            raise ResourceConfigurationError(
                "ResourceConfiguration provider must not be blank when provided."
            )

        if self.thinking is not None and not self.thinking.strip():
            raise ResourceConfigurationError(
                "ResourceConfiguration thinking must not be blank when provided."
            )

        if self.runtime is not None and not self.runtime.strip():
            raise ResourceConfigurationError(
                "ResourceConfiguration runtime must not be blank when provided."
            )
