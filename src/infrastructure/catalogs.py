from domain.agent_profile import AgentId, AgentProfile
from domain.model_profile import ModelId, ModelProfile
from domain.skill_profile import SkillId, SkillProfile


class AgentCatalog:
    """Small in-memory catalog for declared Agent Profiles."""

    def add(self, agent: AgentProfile) -> None:
        raise NotImplementedError

    def get(self, agent_id: AgentId) -> AgentProfile | None:
        raise NotImplementedError

    def all(self) -> tuple[AgentProfile, ...]:
        raise NotImplementedError


class SkillCatalog:
    """Small in-memory catalog for declared Skill Profiles."""

    def add(self, skill: SkillProfile) -> None:
        raise NotImplementedError

    def get(self, skill_id: SkillId) -> SkillProfile | None:
        raise NotImplementedError

    def all(self) -> tuple[SkillProfile, ...]:
        raise NotImplementedError


class ModelCatalog:
    """Small in-memory catalog for declared Model Profiles."""

    def add(self, model: ModelProfile) -> None:
        raise NotImplementedError

    def get(self, model_id: ModelId) -> ModelProfile | None:
        raise NotImplementedError

    def all(self) -> tuple[ModelProfile, ...]:
        raise NotImplementedError


class InMemoryAgentCatalog(AgentCatalog):
    def __init__(self) -> None:
        self._agents: dict[str, AgentProfile] = {}

    def add(self, agent: AgentProfile) -> None:
        self._agents[agent.id.value] = agent

    def get(self, agent_id: AgentId) -> AgentProfile | None:
        return self._agents.get(agent_id.value)

    def all(self) -> tuple[AgentProfile, ...]:
        return tuple(self._agents.values())


class InMemorySkillCatalog(SkillCatalog):
    def __init__(self) -> None:
        self._skills: dict[str, SkillProfile] = {}

    def add(self, skill: SkillProfile) -> None:
        self._skills[skill.id.value] = skill

    def get(self, skill_id: SkillId) -> SkillProfile | None:
        return self._skills.get(skill_id.value)

    def all(self) -> tuple[SkillProfile, ...]:
        return tuple(self._skills.values())


class InMemoryModelCatalog(ModelCatalog):
    def __init__(self) -> None:
        self._models: dict[str, ModelProfile] = {}

    def add(self, model: ModelProfile) -> None:
        self._models[model.id.value] = model

    def get(self, model_id: ModelId) -> ModelProfile | None:
        return self._models.get(model_id.value)

    def all(self) -> tuple[ModelProfile, ...]:
        return tuple(self._models.values())
