import pytest

from domain.skill_profile import SkillId, SkillProfile, SkillProfileError


def make_skill() -> SkillProfile:
    return SkillProfile(
        id=SkillId("tdd"),
        purpose="Drive development through a test-first workflow.",
        capabilities=("testing", "implementation"),
        inputs=("work-unit",),
        outputs=("code", "tests", "evidence"),
        dependencies=("codebase-context",),
        compatible_agents=("agent-001", "agent-002"),
        compatible_models=("model-a", "model-b"),
        compatible_runtimes=("openclaw",),
        version="1.0",
        evidence=("skill-spec-001",),
    )


def test_skill_requires_id() -> None:
    with pytest.raises(SkillProfileError):
        SkillId("")


def test_skill_requires_purpose() -> None:
    with pytest.raises(SkillProfileError):
        SkillProfile(
            id=SkillId("tdd"),
            purpose="",
        )


def test_skill_requires_version() -> None:
    with pytest.raises(SkillProfileError):
        SkillProfile(
            id=SkillId("tdd"),
            purpose="Test-driven development.",
            version="",
        )


def test_skill_profile_preserves_declared_fields() -> None:
    skill = make_skill()

    assert skill.purpose.startswith("Drive development")
    assert skill.capabilities == ("testing", "implementation")
    assert skill.inputs == ("work-unit",)
    assert skill.outputs == ("code", "tests", "evidence")
    assert skill.dependencies == ("codebase-context",)
    assert skill.compatible_agents == ("agent-001", "agent-002")
    assert skill.compatible_models == ("model-a", "model-b")
    assert skill.compatible_runtimes == ("openclaw",)
    assert skill.version == "1.0"
    assert skill.evidence == ("skill-spec-001",)


def test_skill_reports_capability() -> None:
    skill = make_skill()

    assert skill.provides_capability("testing")
    assert skill.provides_capability("implementation")
    assert not skill.provides_capability("database")


def test_empty_agent_allowlist_means_no_explicit_agent_restriction() -> None:
    skill = SkillProfile(
        id=SkillId("generic"),
        purpose="Generic skill.",
    )

    assert skill.accepts_agent("any-agent")


def test_declared_agent_compatibility_is_enforced() -> None:
    skill = make_skill()

    assert skill.accepts_agent("agent-001")
    assert not skill.accepts_agent("agent-999")


def test_declared_model_compatibility_is_enforced() -> None:
    skill = make_skill()

    assert skill.accepts_model("model-a")
    assert not skill.accepts_model("model-z")


def test_declared_runtime_compatibility_is_enforced() -> None:
    skill = make_skill()

    assert skill.accepts_runtime("openclaw")
    assert not skill.accepts_runtime("other-runtime")
