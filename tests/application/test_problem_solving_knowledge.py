import json
from pathlib import Path

import pytest

from application.problem_solving_knowledge import (
    ProblemSolvingKnowledge,
    ProblemSolvingKnowledgeError,
)


def knowledge_file() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "problem-solving-lessons.json"
    )


def test_default_knowledge_contains_observed_recovery_patterns() -> None:
    knowledge = ProblemSolvingKnowledge.from_file(knowledge_file())
    ids = {lesson.id for lesson in knowledge.lessons}

    assert "resolve-blockers-before-retrying-implementation" in ids
    assert "recover-structured-planning-by-minimizing-the-graph" in ids


def test_relevant_selects_blocker_resolution_for_architectural_block() -> None:
    knowledge = ProblemSolvingKnowledge.from_file(knowledge_file())

    lessons = knowledge.relevant(
        "Implementation is blocked by an architectural contract ambiguity."
    )

    assert lessons
    assert lessons[0].id == "resolve-blockers-before-retrying-implementation"


def test_relevant_selects_planning_recovery_for_invalid_json() -> None:
    knowledge = ProblemSolvingKnowledge.from_file(knowledge_file())

    lessons = knowledge.relevant(
        "Planner returned invalid JSON and raised ProjectPlanningError."
    )

    ids = {lesson.id for lesson in lessons}
    assert "recover-structured-planning-by-minimizing-the-graph" in ids


def test_prompt_block_is_empty_for_unrelated_work() -> None:
    knowledge = ProblemSolvingKnowledge.from_file(knowledge_file())

    assert knowledge.prompt_block("Rename one CSS class.") == ""


def test_unapproved_lessons_are_not_loaded(tmp_path: Path) -> None:
    path = tmp_path / "knowledge.json"
    path.write_text(
        json.dumps(
            {
                "lessons": [
                    {
                        "id": "candidate",
                        "status": "candidate",
                        "title": "Candidate",
                        "triggers": ["failure"],
                        "strategy": "Do something.",
                        "steps": ["One step."],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    knowledge = ProblemSolvingKnowledge.from_file(path)

    assert knowledge.lessons == ()


def test_duplicate_approved_ids_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "knowledge.json"
    lesson = {
        "id": "duplicate",
        "status": "approved",
        "title": "Duplicate",
        "triggers": ["failure"],
        "strategy": "Do something.",
        "steps": ["One step."],
    }
    path.write_text(
        json.dumps({"lessons": [lesson, lesson]}),
        encoding="utf-8",
    )

    with pytest.raises(ProblemSolvingKnowledgeError, match="Duplicate"):
        ProblemSolvingKnowledge.from_file(path)
