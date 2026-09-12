from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProblemSolvingKnowledgeError(ValueError):
    """Raised when governed problem-solving knowledge is malformed."""


@dataclass(frozen=True)
class ProblemSolvingLesson:
    id: str
    title: str
    triggers: tuple[str, ...]
    strategy: str
    steps: tuple[str, ...]
    safeguards: tuple[str, ...] = ()
    success_signals: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "ProblemSolvingLesson":
        def required_text(field: str) -> str:
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ProblemSolvingKnowledgeError(
                    f"Problem-solving lesson field '{field}' must be non-empty text."
                )
            return value.strip()

        def text_tuple(field: str, *, required: bool = False) -> tuple[str, ...]:
            value = payload.get(field, [])
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise ProblemSolvingKnowledgeError(
                    f"Problem-solving lesson field '{field}' must be a list of non-empty strings."
                )
            result = tuple(item.strip() for item in value)
            if required and not result:
                raise ProblemSolvingKnowledgeError(
                    f"Problem-solving lesson field '{field}' must not be empty."
                )
            return result

        return cls(
            id=required_text("id"),
            title=required_text("title"),
            triggers=text_tuple("triggers", required=True),
            strategy=required_text("strategy"),
            steps=text_tuple("steps", required=True),
            safeguards=text_tuple("safeguards"),
            success_signals=text_tuple("success_signals"),
        )

    def score(self, text: str) -> int:
        haystack = text.casefold()
        return sum(
            1
            for trigger in self.triggers
            if trigger.casefold() in haystack
        )

    def as_prompt_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "title": self.title,
            "strategy": self.strategy,
            "steps": list(self.steps),
        }
        if self.safeguards:
            payload["safeguards"] = list(self.safeguards)
        if self.success_signals:
            payload["success_signals"] = list(self.success_signals)
        return payload


@dataclass(frozen=True)
class ProblemSolvingKnowledge:
    """Approved reusable reasoning strategies selected by deterministic evidence.

    The knowledge base does not self-modify. New lessons must be promoted into
    the governed JSON file after evidence/review, preventing one transient
    incident from becoming a permanent planning rule.
    """

    lessons: tuple[ProblemSolvingLesson, ...] = ()

    @classmethod
    def from_file(cls, path: Path) -> "ProblemSolvingKnowledge":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProblemSolvingKnowledgeError(
                f"Could not load problem-solving knowledge from '{path}'."
            ) from exc

        if not isinstance(payload, dict):
            raise ProblemSolvingKnowledgeError(
                "Problem-solving knowledge root must be a JSON object."
            )
        entries = payload.get("lessons")
        if not isinstance(entries, list):
            raise ProblemSolvingKnowledgeError(
                "Problem-solving knowledge requires a lessons list."
            )

        approved: list[ProblemSolvingLesson] = []
        seen_ids: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ProblemSolvingKnowledgeError(
                    "Each problem-solving lesson must be an object."
                )
            if entry.get("status", "approved") != "approved":
                continue
            lesson = ProblemSolvingLesson.from_mapping(entry)
            if lesson.id in seen_ids:
                raise ProblemSolvingKnowledgeError(
                    f"Duplicate problem-solving lesson id: {lesson.id}."
                )
            seen_ids.add(lesson.id)
            approved.append(lesson)

        return cls(tuple(approved))

    @classmethod
    def from_default_repository_file(cls) -> "ProblemSolvingKnowledge":
        path = (
            Path(__file__).resolve().parents[2]
            / "knowledge"
            / "problem-solving-lessons.json"
        )
        if not path.is_file():
            return cls()
        return cls.from_file(path)

    def relevant(
        self,
        text: str,
        *,
        limit: int = 3,
    ) -> tuple[ProblemSolvingLesson, ...]:
        if limit < 1:
            return ()
        ranked = sorted(
            (
                (lesson.score(text), lesson.id, lesson)
                for lesson in self.lessons
            ),
            key=lambda item: (-item[0], item[1]),
        )
        return tuple(
            lesson
            for score, _, lesson in ranked[:limit]
            if score > 0
        )

    def prompt_block(self, text: str, *, limit: int = 3) -> str:
        lessons = self.relevant(text, limit=limit)
        if not lessons:
            return ""
        encoded = json.dumps(
            [lesson.as_prompt_payload() for lesson in lessons],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return (
            "APPROVED PROBLEM-SOLVING LESSONS:\n"
            "Use these as reusable strategy guidance when applicable. They do not "
            "override project facts, governance, security, or human-only decisions.\n"
            f"{encoded}"
        )
