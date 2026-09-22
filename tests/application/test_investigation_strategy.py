from types import SimpleNamespace

import pytest

from application.investigation_strategy import (
    RecoveryStrategyError,
    RecoveryStrategyRequest,
    RuntimeRecoveryStrategist,
)
from domain.investigation import RecoveryDisposition


class FakeRunner:
    def __init__(self, output: str) -> None:
        self.output = output
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return SimpleNamespace(output=self.output)


def _payload() -> str:
    return """{
      "failure_class": "strategy-exhausted",
      "problem_summary": "The prior implementation paths did not satisfy the acceptance contract.",
      "previous_path_failures": ["path-a repeated the same assumption", "path-b lacked required evidence"],
      "candidate_paths": [
        {
          "id": "path-c",
          "title": "Reconcile contract before implementation",
          "rationale": "Resolve the disputed interface first.",
          "novelty": "Moves uncertainty resolution ahead of code mutation.",
          "prerequisites": ["read canonical contract"],
          "risks": ["may reveal a human decision"],
          "suggested_skills": ["investigation", "debugging"],
          "expected_evidence": ["decision matrix"],
          "external_research": false
        }
      ],
      "recommended_path_id": "path-c",
      "disposition": "REPLAN_WITH_PREREQUISITE",
      "work_graph_guidance": "Create one read-only prerequisite analysis unit before retrying the original work unit.",
      "human_decision_required": false,
      "external_research_required": false,
      "confidence": 0.9
    }"""


def test_recovery_strategist_returns_structured_analysis():
    runner = FakeRunner(_payload())
    strategist = RuntimeRecoveryStrategist(runner=runner)

    result = strategist.analyze(
        RecoveryStrategyRequest(
            project_objective="Finish the project.",
            orchestration_id="orch-1",
            work_unit_id="U6",
            work_unit_objective="Implement the failing contract.",
            state_summary="U6 is RECOVERY_REQUIRED.",
            attempt_history=("strategy 1 returned", "strategy 2 returned"),
        )
    )

    assert result.disposition is RecoveryDisposition.REPLAN_WITH_PREREQUISITE
    assert result.recommended_path_id == "path-c"
    assert result.recommended_path is not None
    assert result.recommended_path.title == "Reconcile contract before implementation"
    assert "RECOVERY STRATEGIST ANALYSIS" in result.planner_guidance()
    request = runner.requests[0]
    assert "investigation" in request.skills
    assert "grill" in request.skills
    assert "grill-me" in request.skills
    assert request.requested_side_effects == ()




def test_recovery_strategist_accepts_additive_json_and_human_question():
    payload = _payload().replace(
        '"external_research_required": false,',
        '"human_question": "Qual comportamento visual você considera aceitável para a próxima tentativa?",\n'
        '      "external_research_required": false,\n'
        '      "provider_note": "additive metadata",'
    )
    result = RuntimeRecoveryStrategist.parse(payload)

    assert "comportamento visual" in result.human_question
    assert "human_question=" in result.planner_guidance()


def test_recovery_strategist_rejects_unknown_recommended_path():
    invalid = _payload().replace('"recommended_path_id": "path-c"', '"recommended_path_id": "path-z"')
    with pytest.raises(RecoveryStrategyError):
        RuntimeRecoveryStrategist.parse(invalid)
