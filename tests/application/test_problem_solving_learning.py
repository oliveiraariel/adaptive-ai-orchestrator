import json
from pathlib import Path
from types import SimpleNamespace

from application.problem_solving_learning import (
    LEARNING_MARKER,
    ProblemSolvingKnowledgeBase,
    ProblemSolvingLearningStore,
    ProblemSolvingStrategy,
)
from application.runtime_project_planner import (
    ProjectPlanningRequest,
    RuntimeProjectPlanner,
)


def work_unit_payload(unit_id: str = "resolve-blocker") -> str:
    return json.dumps(
        {
            "summary": "one safe unit",
            "work_units": [
                {
                    "id": unit_id,
                    "objective": "Resolve the blocker",
                    "role": "analyst",
                    "scope": "read-only",
                    "kind": "DECISION",
                    "required_capabilities": [],
                    "requested_skills": [],
                    "tools": [],
                    "inputs": [],
                    "expected_output": ["decision contract"],
                    "acceptance_criteria": ["runtime-completed"],
                    "requested_side_effects": [],
                    "write_paths": [],
                    "priority": 1,
                    "criticality": 0,
                    "parallel_safe": True,
                }
            ],
            "dependencies": [],
        }
    )


class QueueRunner:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return SimpleNamespace(output=self.outputs.pop(0))


def strategy_base(store: ProblemSolvingLearningStore) -> ProblemSolvingKnowledgeBase:
    return ProblemSolvingKnowledgeBase(
        (
            ProblemSolvingStrategy(
                id="resolve-blockers-before-implementation",
                title="Resolve blockers first",
                triggers=("blocked", "architectural ambiguity"),
                guidance=(
                    "Create a read-only blocker-resolution Work Unit before implementation.",
                ),
                safety=("Do not invent business rules.",),
            ),
        ),
        learning_store=store,
    )


def test_validated_strategy_is_injected_into_planner_prompt(tmp_path: Path) -> None:
    store = ProblemSolvingLearningStore(tmp_path / "learning.jsonl")
    runner = QueueRunner([work_unit_payload()])
    planner = RuntimeProjectPlanner(
        runner=runner,
        skill_profiles=(),
        knowledge_base=strategy_base(store),
    )

    planner.plan(
        ProjectPlanningRequest(
            objective="Implementation is blocked by architectural ambiguity.",
            max_work_units=4,
        )
    )

    prompt = runner.requests[0].objective
    assert "ADAPTIVE EXPERIENCE GUIDANCE" in prompt
    assert "resolve-blockers-before-implementation" in prompt
    assert "read-only blocker-resolution Work Unit" in prompt


def test_invalid_structured_plan_retries_once_with_one_work_unit(tmp_path: Path) -> None:
    store = ProblemSolvingLearningStore(tmp_path / "learning.jsonl")
    runner = QueueRunner(["not-json", work_unit_payload()])
    planner = RuntimeProjectPlanner(
        runner=runner,
        skill_profiles=(),
        knowledge_base=strategy_base(store),
    )

    plan = planner.plan(
        ProjectPlanningRequest(
            objective="Continue backend implementation safely.",
            max_work_units=8,
        )
    )

    assert len(runner.requests) == 2
    assert len(plan.work_units) == 1
    assert "exactly ONE smallest safe Work Unit" in runner.requests[1].objective
    records = [
        json.loads(line)
        for line in store.path.read_text(encoding="utf-8").splitlines()
    ]
    assert records[-1]["strategy_id"] == "simplify-after-structured-planning-failure"


def test_accepted_worker_signal_is_sanitized_and_persisted(tmp_path: Path) -> None:
    store = ProblemSolvingLearningStore(tmp_path / "learning.jsonl")
    output = (
        "Completed safely.\n"
        + LEARNING_MARKER
        + ' {"strategy_id":"resolve-contract-first","trigger":"implementation blocked by unclear contract",'
        + '"action":"resolve the contract in a read-only decision unit before coding",'
        + '"result":"implementation became unambiguous"}'
    )

    assert store.record_worker_signal(
        output,
        orchestration_id="orch-1",
        work_unit_id="wu-1",
    )

    record = json.loads(store.path.read_text(encoding="utf-8").strip())
    assert record["strategy_id"] == "resolve-contract-first"
    assert record["orchestration_id"] == "orch-1"
    assert "Completed safely" not in store.path.read_text(encoding="utf-8")


def test_sensitive_learning_signal_is_rejected(tmp_path: Path) -> None:
    store = ProblemSolvingLearningStore(tmp_path / "learning.jsonl")
    output = (
        LEARNING_MARKER
        + ' {"strategy_id":"bad-signal","trigger":"auth failure",'
        + '"action":"use bearer secret=value",'
        + '"result":"worked"}'
    )

    assert not store.record_worker_signal(
        output,
        orchestration_id="orch-1",
        work_unit_id="wu-1",
    )
    assert not store.path.exists()


def test_repeated_independent_successes_become_provisional_guidance(tmp_path: Path) -> None:
    store = ProblemSolvingLearningStore(tmp_path / "learning.jsonl")
    for orchestration_id in ("orch-1", "orch-2"):
        assert store.record(
            strategy_id="resolve-contract-first",
            trigger="implementation blocked by unclear contract",
            action="resolve the contract before coding",
            result="implementation became unambiguous",
            orchestration_id=orchestration_id,
            work_unit_id="decision",
            source="accepted-worker-result",
        )

    base = ProblemSolvingKnowledgeBase((), learning_store=store)
    guidance = base.render_guidance(
        "The implementation is blocked by an unclear contract."
    )

    assert "PROVISIONAL REPEATED EXPERIENCE" in guidance
    assert "resolve-contract-first" in guidance
