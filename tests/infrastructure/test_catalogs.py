from domain.agent_profile import AgentId, AgentProfile
from domain.model_profile import ModelId, ModelProfile
from domain.skill_profile import SkillId, SkillProfile
from infrastructure.catalogs import (
    InMemoryAgentCatalog,
    InMemoryModelCatalog,
    InMemorySkillCatalog,
)


def make_agent(agent_id: str) -> AgentProfile:
    return AgentProfile(id=AgentId(agent_id), role="agent")


def make_skill(skill_id: str) -> SkillProfile:
    return SkillProfile(id=SkillId(skill_id), purpose="skill purpose")


def make_model(model_id: str) -> ModelProfile:
    return ModelProfile(
        id=ModelId(model_id),
        name="Model",
        version="1.0",
        provider="provider",
    )


def test_agent_catalog_add_get_and_list() -> None:
    catalog = InMemoryAgentCatalog()
    agent = make_agent("agent-001")

    catalog.add(agent)

    assert catalog.get(agent.id) is agent
    assert catalog.all() == (agent,)


def test_agent_catalog_replaces_same_id() -> None:
    catalog = InMemoryAgentCatalog()
    first = make_agent("agent-001")
    second = AgentProfile(id=AgentId("agent-001"), role="updated")

    catalog.add(first)
    catalog.add(second)

    assert catalog.get(first.id) is second
    assert catalog.all() == (second,)


def test_skill_catalog_add_get_and_list() -> None:
    catalog = InMemorySkillCatalog()
    skill = make_skill("tdd")

    catalog.add(skill)

    assert catalog.get(skill.id) is skill
    assert catalog.all() == (skill,)


def test_model_catalog_add_get_and_list() -> None:
    catalog = InMemoryModelCatalog()
    model = make_model("model-001")

    catalog.add(model)

    assert catalog.get(model.id) is model
    assert catalog.all() == (model,)


def test_catalogs_are_independent() -> None:
    agents = InMemoryAgentCatalog()
    skills = InMemorySkillCatalog()
    models = InMemoryModelCatalog()

    agent = make_agent("agent-001")
    skill = make_skill("tdd")
    model = make_model("model-001")

    agents.add(agent)
    skills.add(skill)
    models.add(model)

    assert agents.all() == (agent,)
    assert skills.all() == (skill,)
    assert models.all() == (model,)


def test_missing_items_return_none() -> None:
    agents = InMemoryAgentCatalog()
    skills = InMemorySkillCatalog()
    models = InMemoryModelCatalog()

    assert agents.get(AgentId("missing")) is None
    assert skills.get(SkillId("missing")) is None
    assert models.get(ModelId("missing")) is None
