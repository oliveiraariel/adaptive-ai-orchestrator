from application.agent_skill_analysis import AgentSkillAnalysis
from domain.agent_profile import AgentId, AgentProfile
from domain.skill_profile import SkillId, SkillProfile
from domain.work_unit import WorkUnit, WorkUnitId
from infrastructure.catalogs import InMemoryAgentCatalog, InMemorySkillCatalog


def make_work_unit() -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId("wu-001"),
        objective="Implement orchestration logic",
        required_capabilities=("python", "testing"),
    )


def make_agent(
    agent_id: str,
    capabilities: tuple[str, ...],
) -> AgentProfile:
    return AgentProfile(
        id=AgentId(agent_id),
        role="engineering-agent",
        capabilities=capabilities,
    )


def make_skill(
    skill_id: str,
    capabilities: tuple[str, ...],
    compatible_agents: tuple[str, ...] = (),
) -> SkillProfile:
    return SkillProfile(
        id=SkillId(skill_id),
        purpose=f"Purpose of {skill_id}",
        capabilities=capabilities,
        compatible_agents=compatible_agents,
    )


def make_analysis() -> tuple[
    InMemoryAgentCatalog,
    InMemorySkillCatalog,
    AgentSkillAnalysis,
]:
    agents = InMemoryAgentCatalog()
    skills = InMemorySkillCatalog()

    return agents, skills, AgentSkillAnalysis(agents, skills)


def test_matching_agent_is_returned_with_compatible_skills() -> None:
    agents, skills, analysis = make_analysis()

    agent = make_agent("agent-001", ("python", "testing"))
    skill = make_skill("tdd", ("testing",), ("agent-001",))

    agents.add(agent)
    skills.add(skill)

    result = analysis.execute(make_work_unit())

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.agent_id == "agent-001"
    assert candidate.skill_ids == ("tdd",)
    assert candidate.matched_capabilities == ("python", "testing")
    assert candidate.confidence == 1.0


def test_agent_missing_required_capability_is_excluded() -> None:
    agents, skills, analysis = make_analysis()

    agents.add(make_agent("agent-001", ("python",)))

    result = analysis.execute(make_work_unit())

    assert result.candidates == ()


def test_compatible_skill_can_supply_capability_missing_from_agent_profile() -> None:
    agents, skills, analysis = make_analysis()

    agents.add(make_agent("agent-001", ("python",)))
    skills.add(
        make_skill(
            "tdd",
            ("testing",),
            compatible_agents=("agent-001",),
        )
    )

    result = analysis.execute(make_work_unit())

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.agent_id == "agent-001"
    assert candidate.skill_ids == ("tdd",)
    assert candidate.matched_capabilities == ("python", "testing")


def test_incompatible_skill_is_not_selected() -> None:
    agents, skills, analysis = make_analysis()

    agents.add(make_agent("agent-001", ("python", "testing")))
    skills.add(
        make_skill(
            "tdd",
            ("testing",),
            compatible_agents=("agent-002",),
        )
    )

    result = analysis.execute(make_work_unit())

    assert result.candidates[0].skill_ids == ()


def test_candidates_are_ranked_by_confidence() -> None:
    agents, skills, analysis = make_analysis()

    agents.add(make_agent("agent-low", ("python", "testing")))
    agents.add(make_agent("agent-high", ("python", "testing")))

    skills.add(make_skill("tdd", ("testing",)))

    result = analysis.execute(make_work_unit())

    assert [candidate.agent_id for candidate in result.candidates] == [
        "agent-high",
        "agent-low",
    ]


def test_no_required_capabilities_returns_no_agent_candidates_without_skills() -> None:
    work_unit = WorkUnit(
        id=WorkUnitId("wu-002"),
        objective="Generic work",
    )
    agents, skills, analysis = make_analysis()

    agents.add(make_agent("agent-001", ("python",)))

    result = analysis.execute(work_unit)

    assert result.candidates == ()
