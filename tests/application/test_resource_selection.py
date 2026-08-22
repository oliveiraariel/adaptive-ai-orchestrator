from application.agent_skill_analysis import AgentSkillAnalysis
from application.resource_selection import ResourceSelection, ResourceSelectionRequest
from domain.agent_profile import AgentId, AgentProfile
from domain.model_profile import ModelId, ModelProfile
from domain.skill_profile import SkillId, SkillProfile
from domain.work_unit import WorkUnit, WorkUnitId
from infrastructure.catalogs import (
    InMemoryAgentCatalog,
    InMemoryModelCatalog,
    InMemorySkillCatalog,
)


def make_work_unit() -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId("wu-001"),
        objective="Select execution resources",
        required_capabilities=("testing",),
    )


def make_agent() -> AgentProfile:
    return AgentProfile(
        id=AgentId("agent-001"),
        role="engineering-agent",
        capabilities=("testing",),
    )


def make_skill(model_ids: tuple[str, ...] = ()) -> SkillProfile:
    return SkillProfile(
        id=SkillId("tdd"),
        purpose="test-driven development",
        capabilities=("testing",),
        compatible_agents=("agent-001",),
        compatible_models=model_ids,
        compatible_runtimes=("openclaw",),
    )


def make_model(model_id: str, provider: str) -> ModelProfile:
    return ModelProfile(
        id=ModelId(model_id),
        name=model_id,
        version="1.0",
        provider=provider,
    )


def make_selection(
    model_ids: tuple[str, ...] = (),
) -> tuple[
    InMemoryAgentCatalog,
    InMemorySkillCatalog,
    InMemoryModelCatalog,
    ResourceSelection,
]:
    agents = InMemoryAgentCatalog()
    skills = InMemorySkillCatalog()
    models = InMemoryModelCatalog()

    agents.add(make_agent())
    skills.add(make_skill(model_ids))

    selection = ResourceSelection(
        agent_skill_analysis=AgentSkillAnalysis(agents, skills),
        skill_catalog=skills,
        model_catalog=models,
    )
    return agents, skills, models, selection


def test_selects_compatible_model_for_agent_candidate() -> None:
    _, _, models, selection = make_selection(("model-001",))
    models.add(make_model("model-001", "provider-001"))

    result = selection.execute(ResourceSelectionRequest(make_work_unit()))

    assert result.configuration is not None
    assert result.configuration.agent == "agent-001"
    assert result.configuration.skills == ("tdd",)
    assert result.configuration.model == "model-001"
    assert result.configuration.provider == "provider-001"
    assert result.configuration.runtime == "openclaw"


def test_returns_no_configuration_when_no_model_is_available() -> None:
    _, _, _, selection = make_selection(("model-001",))

    result = selection.execute(ResourceSelectionRequest(make_work_unit()))

    assert result.configuration is None


def test_selects_deterministically_by_model_id_when_multiple_models_are_compatible() -> None:
    _, _, models, selection = make_selection()
    models.add(make_model("model-b", "provider-b"))
    models.add(make_model("model-a", "provider-a"))

    result = selection.execute(ResourceSelectionRequest(make_work_unit()))

    assert result.configuration is not None
    assert result.configuration.model == "model-a"


def test_skill_model_compatibility_can_filter_models() -> None:
    _, _, models, selection = make_selection(("model-b",))
    models.add(make_model("model-a", "provider-a"))
    models.add(make_model("model-b", "provider-b"))

    result = selection.execute(ResourceSelectionRequest(make_work_unit()))

    assert result.configuration is not None
    assert result.configuration.model == "model-b"


def test_agent_skill_analysis_and_resource_selection_share_same_skill_catalog() -> None:
    agents, skills, models, selection = make_selection(("model-001",))
    agents.add(
        AgentProfile(
            id=AgentId("agent-002"),
            role="other-agent",
            capabilities=("testing",),
        )
    )
    skills.add(
        SkillProfile(
            id=SkillId("special"),
            purpose="specialized testing",
            capabilities=("testing",),
            compatible_agents=("agent-002",),
            compatible_models=("model-001",),
            compatible_runtimes=("openclaw",),
        )
    )
    models.add(make_model("model-001", "provider-001"))

    result = selection.execute(ResourceSelectionRequest(make_work_unit()))

    assert result.configuration is not None
    assert result.configuration.agent in {"agent-001", "agent-002"}
