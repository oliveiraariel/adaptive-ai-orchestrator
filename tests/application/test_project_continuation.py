from application.project_continuation import CreateProjectSuccessor, ProjectContinuationError
from application.investigation_strategy import RecoveryStrategyRequest, RuntimeRecoveryStrategist


class Store:
    def __init__(self, state):
        self.states = {"old": state}
    def load(self, orchestration_id):
        return self.states.get(orchestration_id)
    def save(self, orchestration_id, payload):
        self.states[orchestration_id] = payload


def _terminal():
    return {
        "terminal": True, "active_executions": [],
        "request": {"objective": "finish", "context": [], "max_work_units": 8},
        "plan": {"summary": "plan", "work_units": [
            {"id": "accepted", "objective": "done"}, {"id": "pending", "objective": "remaining"}],
            "dependencies": [{"source_id": "accepted", "target_id": "pending", "required": True}]},
        "work_unit_states": {"accepted": "COMPLETED", "pending": "BLOCKED"},
        "output_refs": {"accepted": "result-ref"},
    }


def test_terminal_successor_is_idempotent_and_reuses_only_accepted_work():
    store = Store(_terminal())
    service = CreateProjectSuccessor(checkpoint_store=store)
    first = service.execute(predecessor_orchestration_id="old", clarification="use approved rule", actor="human")
    second = service.execute(predecessor_orchestration_id="old", clarification="use approved rule", actor="human")
    assert first.successor_orchestration_id == second.successor_orchestration_id
    assert second.already_exists is True
    assert first.reused_work_unit_ids == ("accepted",)
    assert first.pending_work_unit_ids == ("pending",)
    successor = store.load(first.successor_orchestration_id)
    assert successor["terminal"] is False
    assert successor["plan"]["work_units"][0]["id"] == "pending"
    assert successor["continuation"]["accepted_result_refs"] == {"accepted": "result-ref"}
    assert store.load("old")["terminal"] is True


def test_terminal_successor_preserves_release_delivery_obligation():
    state = _terminal()
    state["plan"]["work_units"][1]["release_delivery"] = True
    store = Store(state)

    result = CreateProjectSuccessor(checkpoint_store=store).execute(
        predecessor_orchestration_id="old",
        clarification="deliver the remaining package",
        actor="human",
    )

    successor = store.load(result.successor_orchestration_id)
    assert successor["plan"]["work_units"][0]["release_delivery"] is True


def test_nonterminal_predecessor_is_rejected():
    state = _terminal(); state["terminal"] = False
    try:
        CreateProjectSuccessor(checkpoint_store=Store(state)).execute(
            predecessor_orchestration_id="old", clarification="answer", actor="human")
    except ProjectContinuationError as exc:
        assert "terminal" in str(exc)
    else:
        raise AssertionError("expected terminal guard")


def test_recovery_prompt_exposes_authoritative_decision_before_wait_human():
    request = RecoveryStrategyRequest(
        project_objective="finish", orchestration_id="o", work_unit_id="w",
        work_unit_objective="work", state_summary="blocked",
        authoritative_decisions=("Previsto includes PENDENTE and EFETIVADO.",),
    )
    prompt = RuntimeRecoveryStrategist._prompt(request, "")
    assert "AUTHORITATIVE DECISIONS" in prompt
    assert "Previsto includes PENDENTE and EFETIVADO." in prompt
    assert "Before emitting WAIT_HUMAN" in prompt
