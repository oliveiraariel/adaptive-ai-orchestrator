import pytest

from application.skill_resolution import (
    SkillResolutionError,
    SkillResolutionRequest,
    SkillResolver,
)
from domain.skill_profile import SkillId, SkillProfile


def skill(skill_id: str, *capabilities: str) -> SkillProfile:
    return SkillProfile(
        id=SkillId(skill_id),
        purpose=skill_id,
        capabilities=tuple(capabilities),
    )


def test_resolver_prefers_one_skill_covering_multiple_capabilities() -> None:
    resolver = SkillResolver(
        (
            skill("broad", "cap.a", "cap.b"),
            skill("only-a", "cap.a"),
            skill("only-b", "cap.b"),
        )
    )

    result = resolver.execute(
        SkillResolutionRequest(
            required_capabilities=("cap.a", "cap.b"),
            requested_skill_ids=(),
            agent_id="main",
            runtime="openclaw",
        )
    )

    assert result.skill_ids == ("broad",)
    assert result.covered_capabilities == ("cap.a", "cap.b")


def test_resolver_includes_declared_skill_dependencies() -> None:
    base = skill("base", "cap.base")
    dependent = SkillProfile(
        id=SkillId("dependent"),
        purpose="dependent",
        capabilities=("cap.target",),
        dependencies=("base",),
    )
    resolver = SkillResolver((base, dependent))

    result = resolver.execute(
        SkillResolutionRequest(
            required_capabilities=("cap.target",),
            requested_skill_ids=(),
            agent_id="main",
            runtime="openclaw",
        )
    )

    assert result.skill_ids == ("base", "dependent")


def test_resolver_rejects_unknown_requested_skill() -> None:
    resolver = SkillResolver((skill("known", "cap.a"),))

    with pytest.raises(SkillResolutionError, match="unknown"):
        resolver.execute(
            SkillResolutionRequest(
                required_capabilities=(),
                requested_skill_ids=("missing",),
                agent_id="main",
                runtime="openclaw",
            )
        )
