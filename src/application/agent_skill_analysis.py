from dataclasses import dataclass

from domain.agent_profile import AgentProfile
from domain.skill_profile import SkillProfile
from domain.work_unit import WorkUnit
from infrastructure.catalogs import AgentCatalog, SkillCatalog


@dataclass(frozen=True)
class AgentSkillCandidate:
    agent_id: str
    skill_ids: tuple[str, ...]
    matched_capabilities: tuple[str, ...]
    confidence: float
    eligible_model_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentSkillAnalysisResult:
    candidates: tuple[AgentSkillCandidate, ...]


class AgentSkillAnalysis:
    """Finds agent/skill combinations compatible with a Work Unit."""

    def __init__(
        self,
        agent_catalog: AgentCatalog,
        skill_catalog: SkillCatalog,
    ) -> None:
        self._agent_catalog = agent_catalog
        self._skill_catalog = skill_catalog

    def execute(self, work_unit: WorkUnit) -> AgentSkillAnalysisResult:
        required_capabilities = set(work_unit.required_capabilities)
        if not required_capabilities:
            return AgentSkillAnalysisResult(candidates=())

        candidates: list[AgentSkillCandidate] = []

        for agent in self._agent_catalog.all():
            compatible_skills = self._find_compatible_skills(
                agent=agent,
                required_capabilities=required_capabilities,
            )

            provided_capabilities = set(agent.capabilities)
            for skill in compatible_skills:
                provided_capabilities.update(skill.capabilities)

            if not required_capabilities.issubset(provided_capabilities):
                continue

            matched_capabilities = tuple(
                capability
                for capability in work_unit.required_capabilities
                if capability in provided_capabilities
            )
            skill_ids = tuple(skill.id.value for skill in compatible_skills)

            candidates.append(
                AgentSkillCandidate(
                    agent_id=agent.id.value,
                    skill_ids=skill_ids,
                    matched_capabilities=matched_capabilities,
                    confidence=self._confidence(
                        total_required=len(required_capabilities),
                        matched=len(matched_capabilities),
                        skills_found=len(skill_ids),
                    ),
                    eligible_model_ids=agent.eligible_models,
                )
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate.confidence,
                candidate.agent_id,
            )
        )

        return AgentSkillAnalysisResult(candidates=tuple(candidates))

    def _find_compatible_skills(
        self,
        *,
        agent: AgentProfile,
        required_capabilities: set[str],
    ) -> tuple[SkillProfile, ...]:
        compatible: list[SkillProfile] = []

        for skill in self._skill_catalog.all():
            if not skill.accepts_agent(agent.id.value):
                continue

            if not any(
                capability in required_capabilities
                for capability in skill.capabilities
            ):
                continue

            compatible.append(skill)

        compatible.sort(key=lambda skill: skill.id.value)
        return tuple(compatible)

    @staticmethod
    def _confidence(
        *,
        total_required: int,
        matched: int,
        skills_found: int,
    ) -> float:
        if total_required == 0:
            return 1.0 if skills_found else 0.5

        capability_score = matched / total_required
        skill_bonus = 0.1 if skills_found else 0.0
        return min(1.0, capability_score + skill_bonus)
