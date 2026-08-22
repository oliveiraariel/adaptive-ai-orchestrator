import pytest

from domain.agent_profile import AgentId, AgentProfile, AgentProfileError


def make_agent() -> AgentProfile:
    return AgentProfile(
        id=AgentId("agent-001"),
        role="software-engineering-agent",
        responsibilities=("implementation", "verification"),
        capabilities=("python", "testing"),
        skills=("tdd", "code-review"),
        tools=("git",),
        eligible_models=("model-a", "model-b"),
        context_requirements=("project-context",),
        permissions=("read-repository", "write-repository"),
        runtime="openclaw",
        evidence=("profile-declaration-001",),
    )


def test_agent_requires_id() -> None:
    with pytest.raises(AgentProfileError):
        AgentId("")


def test_agent_requires_role() -> None:
    with pytest.raises(AgentProfileError):
        AgentProfile(
            id=AgentId("agent-001"),
            role="",
        )


def test_agent_profile_preserves_declared_fields() -> None:
    agent = make_agent()

    assert agent.role == "software-engineering-agent"
    assert agent.responsibilities == ("implementation", "verification")
    assert agent.capabilities == ("python", "testing")
    assert agent.skills == ("tdd", "code-review")
    assert agent.tools == ("git",)
    assert agent.eligible_models == ("model-a", "model-b")
    assert agent.context_requirements == ("project-context",)
    assert agent.permissions == ("read-repository", "write-repository")
    assert agent.runtime == "openclaw"
    assert agent.evidence == ("profile-declaration-001",)


def test_agent_reports_capabilities() -> None:
    agent = make_agent()

    assert agent.has_capability
    assert agent.supports_capability("python")
    assert agent.supports_capability("testing")
    assert not agent.supports_capability("java")


def test_agent_reports_skills() -> None:
    agent = make_agent()

    assert agent.supports_skill("tdd")
    assert agent.supports_skill("code-review")
    assert not agent.supports_skill("database-migration")


def test_agent_can_use_declared_model() -> None:
    agent = make_agent()

    assert agent.can_use_model("model-a")
    assert agent.can_use_model("model-b")
    assert not agent.can_use_model("model-c")


def test_empty_model_allowlist_means_no_explicit_model_restriction() -> None:
    agent = AgentProfile(
        id=AgentId("agent-002"),
        role="general-agent",
    )

    assert agent.can_use_model("any-model")
