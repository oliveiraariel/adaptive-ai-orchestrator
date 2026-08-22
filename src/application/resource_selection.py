from dataclasses import dataclass

from application.agent_skill_analysis import AgentSkillAnalysis
from domain.model_profile import ModelProfile
from domain.resource_configuration import ResourceConfiguration
from domain.skill_profile import SkillProfile, SkillId
from domain.work_unit import WorkUnit
from infrastructure.catalogs import ModelCatalog, SkillCatalog


@dataclass(frozen=True)
class ResourceSelectionRequest:
    work_unit: WorkUnit


@dataclass(frozen=True)
class ResourceSelectionResult:
    configuration: ResourceConfiguration | None


class ResourceSelection:
    """Selects one compatible resource configuration for a Work Unit."""

    def __init__(
        self,
        agent_skill_analysis: AgentSkillAnalysis,
        skill_catalog: SkillCatalog,
        model_catalog: ModelCatalog,
    ) -> None:
        self._agent_skill_analysis = agent_skill_analysis
        self._skill_catalog = skill_catalog
        self._model_catalog = model_catalog

    def execute(
        self,
        request: ResourceSelectionRequest,
    ) -> ResourceSelectionResult:
        analysis = self._agent_skill_analysis.execute(request.work_unit)

        for candidate in analysis.candidates:
            skills = self._load_skills(candidate.skill_ids)
            compatible_model = self._select_model(
                agent_id=candidate.agent_id,
                skills=skills,
            )

            if compatible_model is None:
                continue

            runtime = self._select_runtime(skills)

            return ResourceSelectionResult(
                configuration=ResourceConfiguration(
                    agent=candidate.agent_id,
                    skills=tuple(skill.id.value for skill in skills),
                    model=compatible_model.id.value,
                    provider=compatible_model.provider,
                    runtime=runtime,
                )
            )

        return ResourceSelectionResult(configuration=None)

    def _load_skills(
        self,
        skill_ids: tuple[str, ...],
    ) -> tuple[SkillProfile, ...]:
        skills: list[SkillProfile] = []

        for skill_id in skill_ids:
            skill = self._skill_catalog.get(SkillId(skill_id))
            if skill is not None:
                skills.append(skill)

        return tuple(skills)

    def _select_model(
        self,
        *,
        agent_id: str,
        skills: tuple[SkillProfile, ...],
    ) -> ModelProfile | None:
        compatible = [
            model
            for model in self._model_catalog.all()
            if self._model_is_compatible(
                model=model,
                agent_id=agent_id,
                skills=skills,
            )
        ]

        compatible.sort(key=lambda model: model.id.value)
        return compatible[0] if compatible else None

    @staticmethod
    def _model_is_compatible(
        *,
        model: ModelProfile,
        agent_id: str,
        skills: tuple[SkillProfile, ...],
    ) -> bool:
        return all(
            skill.accepts_model(model.id.value)
            and (not skill.compatible_agents or agent_id in skill.compatible_agents)
            for skill in skills
        )

    @staticmethod
    def _select_runtime(
        skills: tuple[SkillProfile, ...],
    ) -> str | None:
        runtime_candidates = {
            runtime
            for skill in skills
            for runtime in skill.compatible_runtimes
        }

        if len(runtime_candidates) == 1:
            return next(iter(runtime_candidates))

        return None
