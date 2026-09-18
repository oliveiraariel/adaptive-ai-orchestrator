from types import SimpleNamespace

import pytest

from application.learning_analysis import (
    LearningAnalysisError,
    RuntimeSuccessfulRetestLearningAnalyst,
    SuccessfulRetestLearningRequest,
)
from domain.incident import LearningScope


class FakeRunner:
    def __init__(self, output: str) -> None:
        self.output = output
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return SimpleNamespace(output=self.output)


def _payload(*, scope: str = "GENERALIZABLE", promote: bool = True) -> str:
    promote_json = "true" if promote else "false"
    return f"""{{
  "problem_summary": "Retest originally failed because the runtime state was interpreted from stale conversational evidence.",
  "root_cause": "Correlated persisted liveness was not consulted before recovery.",
  "solution_summary": "Reconcile execution identity, lease and heartbeat before deciding whether to redispatch.",
  "learning_statement": "Prefer correlated persistent liveness evidence over conversational claims when deciding worker activity.",
  "scope": "{scope}",
  "target_hints": ["adaptive:problem-solving", "skills:debugging"],
  "confidence": 0.94,
  "should_promote": {promote_json},
  "evidence_rationale": "The failing path and accepted retest differ exactly at the liveness reconciliation step."
}}"""


def test_learning_curator_returns_structured_scope_and_targets():
    runner = FakeRunner(_payload())
    analyst = RuntimeSuccessfulRetestLearningAnalyst(runner=runner)

    result = analyst.analyze(
        SuccessfulRetestLearningRequest(
            project_objective="Finish recovery safely.",
            project_id="adaptive",
            orchestration_id="orch-1",
            work_unit_id="U7",
            work_unit_objective="Reconcile returned work.",
            previous_attempts=("attempt 1 returned because stale state was trusted",),
            accepted_result_summary="Retest passed after correlated state reconciliation.",
            validation_refs=("work-unit:U7:accepted",),
        )
    )

    assert result.scope is LearningScope.GENERALIZABLE
    assert result.should_promote is True
    assert "skills:debugging" in result.target_hints
    request = runner.requests[0]
    assert "investigation" in request.skills
    assert "testing" in request.skills
    assert request.requested_side_effects == ()


def test_learning_curator_rejects_undecided_scope():
    raw = _payload(scope="UNDECIDED")
    with pytest.raises(LearningAnalysisError):
        RuntimeSuccessfulRetestLearningAnalyst.parse(raw)


def test_learning_curator_can_explicitly_keep_lesson_local():
    result = RuntimeSuccessfulRetestLearningAnalyst.parse(
        _payload(scope="LOCAL_ONLY", promote=False)
    )
    assert result.scope is LearningScope.LOCAL_ONLY
    assert result.should_promote is False
