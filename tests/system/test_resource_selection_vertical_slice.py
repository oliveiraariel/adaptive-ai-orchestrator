from application.agent_skill_analysis import AgentSkillAnalysis
from application.resource_selection import (
    ResourceSelection,
    ResourceSelectionRequest,
)
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
        id=WorkUnitId("wu-resource-001"),
        objective="Select resources for a testing task",
        required_capabilities=("testing",),
    )


def make_resource_selection() -> ResourceSelection:
    agents = InMemoryAgentCatalog()
    skills = InMemorySkillCatalog()
    models = InMemoryModelCatalog()

    agents.add(
        AgentProfile(
            id=AgentId("agent-testing"),
            role="testing-agent",
            capabilities=("testing",),
        )
    )

    skills.add(
        SkillProfile(
            id=SkillId("tdd"),
            purpose="Test-driven development",
            capabilities=("testing",),
            compatible_agents=("agent-testing",),
            compatible_models=("model-testing",),
            compatible_runtimes=("openclaw",),
        )
    )

    models.add(
        ModelProfile(
            id=ModelId("model-testing"),
            name="Testing Model",
            version="1.0",
            provider="provider-testing",
            capabilities=("testing",),
            availability="available",
        )
    )

    analysis = AgentSkillAnalysis(
        agent_catalog=agents,
        skill_catalog=skills,
    )

    return ResourceSelection(
        agent_skill_analysis=analysis,
        skill_catalog=skills,
        model_catalog=models,
    )


def test_resource_selection_vertical_slice_produces_configuration() -> None:
    selection = make_resource_selection()

    result = selection.execute(
        ResourceSelectionRequest(
            work_unit=make_work_unit(),
        )
    )

    assert result.configuration is not None
    assert result.configuration.agent == "agent-testing"
    assert result.configuration.skills == ("tdd",)
    assert result.configuration.model == "model-testing"
    assert result.configuration.provider == "provider-testing"
    assert result.configuration.runtime == "openclaw"


def test_resource_selection_vertical_slice_returns_none_when_model_is_incompatible() -> None:
    agents = InMemoryAgentCatalog()
    skills = InMemorySkillCatalog()
    models = InMemoryModelCatalog()

    agents.add(
        AgentProfile(
            id=AgentId("agent-testing"),
            role="testing-agent",
            capabilities=("testing",),
        )
    )

    skills.add(
        SkillProfile(
            id=SkillId("tdd"),
            purpose="Test-driven development",
            capabilities=("testing",),
            compatible_agents=("agent-testing",),
            compatible_models=("different-model",),
            compatible_runtimes=("openclaw",),
        )
    )

    models.add(
        ModelProfile(
            id=ModelId("model-testing"),
            name="Testing Model",
            version="1.0",
            provider="provider-testing",
        )
    )

    selection = ResourceSelection(
        agent_skill_analysis=AgentSkillAnalysis(
            agent_catalog=agents,
            skill_catalog=skills,
        ),
        skill_catalog=skills,
        model_catalog=models,
    )

    result = selection.execute(
        ResourceSelectionRequest(
            work_unit=make_work_unit(),
        )
    )

    assert result.configuration is None
