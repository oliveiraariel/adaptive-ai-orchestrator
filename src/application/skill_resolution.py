from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from domain.skill_profile import SkillProfile


class SkillResolutionError(ValueError):
    """Raised when no safe compatible skill set can satisfy a Work Unit."""


@dataclass(frozen=True)
class SkillResolutionRequest:
    required_capabilities: tuple[str, ...]
    requested_skill_ids: tuple[str, ...]
    agent_id: str
    runtime: str


@dataclass(frozen=True)
class SkillResolutionResult:
    skill_ids: tuple[str, ...]
    covered_capabilities: tuple[str, ...]


class SkillResolver:
    """Select the smallest deterministic skill set that covers requirements.

    Requested skills are treated as preferences, not permission to bypass
    compatibility. Remaining capabilities are covered greedily by the skill
    that covers the most uncovered capabilities; deterministic tie-breaking
    keeps planning reproducible and avoids loading unnecessary skill context.
    """

    def __init__(self, profiles: Sequence[SkillProfile]) -> None:
        self._profiles = tuple(profiles)
        self._by_id = {profile.id.value: profile for profile in profiles}
        if len(self._by_id) != len(self._profiles):
            raise SkillResolutionError("Skill profile ids must be unique.")

    def execute(self, request: SkillResolutionRequest) -> SkillResolutionResult:
        required = tuple(dict.fromkeys(request.required_capabilities))
        required_set = set(required)
        selected: list[SkillProfile] = []

        for skill_id in request.requested_skill_ids:
            profile = self._by_id.get(skill_id)
            if profile is None:
                raise SkillResolutionError(f"Requested skill '{skill_id}' is unknown.")
            self._ensure_compatible(profile, request)
            if profile not in selected:
                selected.append(profile)

        covered = self._covered(selected)
        uncovered = required_set - covered

        compatible = [
            profile
            for profile in self._profiles
            if self._compatible(profile, request)
        ]

        while uncovered:
            candidates = [
                profile
                for profile in compatible
                if profile not in selected
                and uncovered.intersection(profile.capabilities)
            ]
            if not candidates:
                missing = ", ".join(sorted(uncovered))
                raise SkillResolutionError(
                    f"No compatible skill set covers required capabilities: {missing}."
                )

            candidates.sort(
                key=lambda profile: (
                    -len(uncovered.intersection(profile.capabilities)),
                    profile.id.value,
                )
            )
            chosen = candidates[0]
            selected.append(chosen)
            uncovered = required_set - self._covered(selected)

        self._include_dependencies(selected, request)
        selected.sort(key=lambda profile: profile.id.value)
        covered = self._covered(selected)

        return SkillResolutionResult(
            skill_ids=tuple(profile.id.value for profile in selected),
            covered_capabilities=tuple(
                capability for capability in required if capability in covered
            ),
        )

    def _include_dependencies(
        self,
        selected: list[SkillProfile],
        request: SkillResolutionRequest,
    ) -> None:
        index = 0
        seen = {profile.id.value for profile in selected}
        while index < len(selected):
            profile = selected[index]
            index += 1
            for dependency_id in profile.dependencies:
                if dependency_id in seen:
                    continue
                dependency = self._by_id.get(dependency_id)
                if dependency is None:
                    raise SkillResolutionError(
                        f"Skill '{profile.id.value}' depends on unknown skill "
                        f"'{dependency_id}'."
                    )
                self._ensure_compatible(dependency, request)
                selected.append(dependency)
                seen.add(dependency_id)

    @staticmethod
    def _covered(profiles: Sequence[SkillProfile]) -> set[str]:
        covered: set[str] = set()
        for profile in profiles:
            covered.update(profile.capabilities)
        return covered

    @staticmethod
    def _compatible(
        profile: SkillProfile,
        request: SkillResolutionRequest,
    ) -> bool:
        return profile.accepts_agent(request.agent_id) and profile.accepts_runtime(
            request.runtime
        )

    @classmethod
    def _ensure_compatible(
        cls,
        profile: SkillProfile,
        request: SkillResolutionRequest,
    ) -> None:
        if not cls._compatible(profile, request):
            raise SkillResolutionError(
                f"Skill '{profile.id.value}' is incompatible with agent "
                f"'{request.agent_id}' or runtime '{request.runtime}'."
            )
