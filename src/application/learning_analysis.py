from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from application.problem_solving_learning import ProblemSolvingKnowledgeBase
from application.run_orchestration import RunOrchestration, RunOrchestrationRequest
from domain.incident import LearningScope
from domain.learning_analysis import SuccessfulRetestLearningAnalysis


class LearningAnalysisError(ValueError):
    """Raised when structured successful-retest learning analysis is invalid."""


@dataclass(frozen=True)
class SuccessfulRetestLearningRequest:
    project_objective: str
    project_id: str
    orchestration_id: str
    work_unit_id: str
    work_unit_objective: str
    previous_attempts: tuple[str, ...]
    accepted_result_summary: str
    validation_refs: tuple[str, ...]
    agent: str = "main"

    def __post_init__(self) -> None:
        if not self.work_unit_id.strip():
            raise LearningAnalysisError("work_unit_id must not be blank")
        if not self.work_unit_objective.strip():
            raise LearningAnalysisError("work_unit_objective must not be blank")
        if not self.previous_attempts:
            raise LearningAnalysisError(
                "successful retest learning requires at least one prior unsuccessful attempt"
            )
        if not self.validation_refs:
            raise LearningAnalysisError("validation_refs must not be empty")


class SuccessfulRetestLearningAnalyst(Protocol):
    def analyze(
        self,
        request: SuccessfulRetestLearningRequest,
    ) -> SuccessfulRetestLearningAnalysis:
        ...


class RuntimeSuccessfulRetestLearningAnalyst:
    """High-reasoning, read-only learning curator invoked after a retest succeeds.

    It recommends what was learned and where that lesson is useful. Adaptive
    remains authoritative for persistence, promotion, target filtering,
    dissemination, consistency checking and closure.
    """

    _allowed_scopes = {
        item.value: item
        for item in LearningScope
        if item is not LearningScope.UNDECIDED
    }

    def __init__(
        self,
        *,
        runner: RunOrchestration,
        knowledge_base: ProblemSolvingKnowledgeBase | None = None,
    ) -> None:
        self._runner = runner
        self._knowledge = (
            knowledge_base or ProblemSolvingKnowledgeBase.load_default()
        )

    def analyze(
        self,
        request: SuccessfulRetestLearningRequest,
    ) -> SuccessfulRetestLearningAnalysis:
        learned = self._knowledge.render_guidance(
            "\n".join(
                (
                    request.project_objective,
                    request.work_unit_objective,
                    *request.previous_attempts,
                    request.accepted_result_summary,
                )
            ),
            skills=("investigation", "debugging", "testing"),
            project_id=request.project_id,
        )
        result = self._runner.execute(
            RunOrchestrationRequest(
                objective=self._prompt(request, learned),
                agent=request.agent,
                skills=(
                    "investigation",
                    "debugging",
                    "testing",
                    "engineering-lifecycle",
                ),
                scope=(
                    "Read-only successful-retest learning analysis. "
                    "Do not modify repositories or Skills."
                ),
                context=(
                    f"Adaptive orchestration id: {request.orchestration_id}",
                    f"Work Unit: {request.work_unit_id}",
                    f"Project id: {request.project_id or '(unspecified)'}",
                ),
                constraints=(
                    "Do not implement code, edit a Skill, dispatch workers, or close an incident.",
                    "Infer only what is supported by the before/after evidence.",
                    "A successful retest validates the remediation in this context; do not universalize project-specific facts.",
                    "Return only one JSON object without Markdown fences.",
                ),
                expected_output=("structured successful-retest learning JSON",),
                acceptance_criteria=("runtime-completed",),
            )
        )
        return self.parse(result.output)

    @classmethod
    def parse(cls, raw: str) -> SuccessfulRetestLearningAnalysis:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LearningAnalysisError("Learning analyst returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise LearningAnalysisError("Learning analyst output must be an object")

        required = {
            "problem_summary",
            "root_cause",
            "solution_summary",
            "learning_statement",
            "scope",
            "target_hints",
            "confidence",
            "should_promote",
            "evidence_rationale",
        }
        if set(payload) != required:
            raise LearningAnalysisError("Learning analyst JSON has an unexpected shape")

        for key in (
            "problem_summary",
            "root_cause",
            "solution_summary",
            "learning_statement",
            "scope",
            "evidence_rationale",
        ):
            if not isinstance(payload[key], str):
                raise LearningAnalysisError(f"{key} must be a string")

        problem = payload["problem_summary"].strip()
        solution = payload["solution_summary"].strip()
        lesson = payload["learning_statement"].strip()
        if not problem or not solution or not lesson:
            raise LearningAnalysisError(
                "problem_summary, solution_summary and learning_statement must be non-empty"
            )

        try:
            scope = cls._allowed_scopes[payload["scope"].strip().upper()]
        except KeyError as exc:
            raise LearningAnalysisError("scope is unsupported") from exc

        hints = payload["target_hints"]
        if not isinstance(hints, list) or any(
            not isinstance(item, str) for item in hints
        ):
            raise LearningAnalysisError("target_hints must be a list of strings")

        confidence = payload["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise LearningAnalysisError("confidence must be numeric")
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise LearningAnalysisError("confidence must be between 0 and 1")
        if not isinstance(payload["should_promote"], bool):
            raise LearningAnalysisError("should_promote must be boolean")

        return SuccessfulRetestLearningAnalysis(
            problem_summary=problem[:500],
            root_cause=payload["root_cause"].strip()[:500],
            solution_summary=solution[:500],
            learning_statement=lesson[:500],
            scope=scope,
            target_hints=tuple(
                item.strip()[:120] for item in hints if item.strip()
            ),
            confidence=confidence,
            should_promote=payload["should_promote"],
            evidence_rationale=payload["evidence_rationale"].strip()[:500],
        )

    @staticmethod
    def _prompt(
        request: SuccessfulRetestLearningRequest,
        learned_guidance: str = "",
    ) -> str:
        prior = "\n".join(f"- {item}" for item in request.previous_attempts)
        refs = "\n".join(f"- {item}" for item in request.validation_refs)
        return (
            "You are Adaptive's Learning Curator. A Work Unit that previously "
            "failed, returned, or required revision has now passed its retest. "
            "Analyze the before/after evidence and decide what reusable learning, "
            "if any, should be incorporated. Distinguish project-specific facts "
            "from generalizable process, runtime/provider, architectural, testing, "
            "debugging, or security lessons. Recommend only role-relevant Skill "
            "targets. Adaptive will validate and apply the recommendation.\n\n"
            f"PROJECT OBJECTIVE:\n{request.project_objective}\n\n"
            f"WORK UNIT:\n{request.work_unit_id}: {request.work_unit_objective}\n\n"
            f"PREVIOUS UNSUCCESSFUL ATTEMPTS:\n{prior}\n\n"
            f"ACCEPTED RETEST RESULT:\n{request.accepted_result_summary[:4000]}\n\n"
            f"VALIDATION REFERENCES:\n{refs}\n\n"
            + (
                "RELEVANT EXISTING ADAPTIVE LEARNING:\n"
                + learned_guidance
                + "\n\n"
                if learned_guidance
                else ""
            )
            + (
                "Treat existing learning as comparison context: decide whether "
                "the retest confirms, narrows, extends, or does not add a "
                "reusable lesson. Do not duplicate a broader lesson merely by "
                "rephrasing it.\n\n"
            )
            + "Return exactly this JSON shape:\n"
            '{"problem_summary":"...","root_cause":"...",'
            '"solution_summary":"...","learning_statement":"...",'
            '"scope":"PROJECT_SPECIFIC|RUNTIME_SPECIFIC|PROVIDER_SPECIFIC|'
            'GENERALIZABLE|ARCHITECTURAL|SECURITY_CRITICAL|LOCAL_ONLY",'
            '"target_hints":["adaptive:problem-solving","skills:debugging"],'
            '"confidence":0.85,"should_promote":true,'
            '"evidence_rationale":"brief evidence-based rationale"}'
        )
