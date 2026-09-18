from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, Sequence

from application.problem_solving_learning import ProblemSolvingKnowledgeBase
from application.run_orchestration import RunOrchestration, RunOrchestrationRequest
from domain.investigation import (
    CandidateRecoveryPath,
    RecoveryDisposition,
    RecoveryStrategyAnalysis,
)


class RecoveryStrategyError(ValueError):
    """Raised when recovery analysis cannot produce a safe structured strategy."""


@dataclass(frozen=True)
class RecoveryStrategyRequest:
    project_objective: str
    orchestration_id: str
    work_unit_id: str
    work_unit_objective: str
    state_summary: str
    attempt_history: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    agent: str = "main"
    recovery_epoch: int = 1

    def __post_init__(self) -> None:
        if not self.project_objective.strip():
            raise RecoveryStrategyError("project_objective must not be blank")
        if not self.work_unit_id.strip():
            raise RecoveryStrategyError("work_unit_id must not be blank")
        if not self.work_unit_objective.strip():
            raise RecoveryStrategyError("work_unit_objective must not be blank")
        if self.recovery_epoch < 1:
            raise RecoveryStrategyError("recovery_epoch must be at least 1")


class RecoveryStrategist(Protocol):
    def analyze(self, request: RecoveryStrategyRequest) -> RecoveryStrategyAnalysis:
        ...


class RuntimeRecoveryStrategist:
    """Read-only high-reasoning recovery analyst.

    The strategist does not dispatch, mutate the project, or own incident state.
    It analyzes failed approaches and returns structured alternatives to the
    orchestrator, which remains authoritative for planning and dispatch.
    """

    def __init__(
        self,
        *,
        runner: RunOrchestration,
        knowledge_base: ProblemSolvingKnowledgeBase | None = None,
    ) -> None:
        self._runner = runner
        self._knowledge = knowledge_base or ProblemSolvingKnowledgeBase.load_default()

    def analyze(self, request: RecoveryStrategyRequest) -> RecoveryStrategyAnalysis:
        experience = self._knowledge.render_guidance(
            "\n".join(
                (
                    request.project_objective,
                    request.work_unit_objective,
                    request.state_summary,
                    *request.attempt_history,
                    *request.constraints,
                )
            )
        )
        result = self._runner.execute(
            RunOrchestrationRequest(
                objective=self._prompt(request, experience),
                agent=request.agent,
                skills=(
                    "investigation",
                    "debugging",
                    "technical-research",
                    "work-decomposition",
                ),
                scope="Read-only recovery strategy analysis. Do not modify project files.",
                context=(
                    f"Adaptive orchestration id: {request.orchestration_id}",
                    f"Target Work Unit: {request.work_unit_id}",
                    f"Recovery epoch: {request.recovery_epoch}",
                ),
                constraints=(
                    *request.constraints,
                    "Do not execute the proposed fix.",
                    "Do not dispatch other workers or invoke Adaptive recursively.",
                    "Do not repeat an exhausted approach unless new evidence materially changes it.",
                    "Separate project facts from hypotheses and preserve uncertainty explicitly.",
                    "Return only one JSON object. No Markdown fences.",
                ),
                expected_output=("structured recovery strategy JSON",),
                acceptance_criteria=("runtime-completed",),
            )
        )
        return self.parse(result.output)

    @staticmethod
    def parse(raw: str) -> RecoveryStrategyAnalysis:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RecoveryStrategyError("Recovery strategist returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RecoveryStrategyError("Recovery strategist result must be an object")

        required = {
            "failure_class",
            "problem_summary",
            "previous_path_failures",
            "candidate_paths",
            "recommended_path_id",
            "disposition",
            "work_graph_guidance",
            "human_decision_required",
            "external_research_required",
            "confidence",
        }
        if set(payload) != required:
            raise RecoveryStrategyError("Recovery strategist JSON has an unexpected shape")

        for key in ("failure_class", "problem_summary", "recommended_path_id", "disposition", "work_graph_guidance"):
            if not isinstance(payload[key], str):
                raise RecoveryStrategyError(f"{key} must be a string")
        if not isinstance(payload["previous_path_failures"], list) or any(
            not isinstance(item, str) for item in payload["previous_path_failures"]
        ):
            raise RecoveryStrategyError("previous_path_failures must be a list of strings")
        if not isinstance(payload["candidate_paths"], list):
            raise RecoveryStrategyError("candidate_paths must be a list")
        if not isinstance(payload["human_decision_required"], bool):
            raise RecoveryStrategyError("human_decision_required must be boolean")
        if not isinstance(payload["external_research_required"], bool):
            raise RecoveryStrategyError("external_research_required must be boolean")
        confidence = payload["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise RecoveryStrategyError("confidence must be numeric")
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise RecoveryStrategyError("confidence must be between 0 and 1")

        try:
            disposition = RecoveryDisposition(payload["disposition"])
        except ValueError as exc:
            raise RecoveryStrategyError("disposition is unsupported") from exc

        candidates: list[CandidateRecoveryPath] = []
        seen: set[str] = set()
        for row in payload["candidate_paths"]:
            if not isinstance(row, dict):
                raise RecoveryStrategyError("candidate path must be an object")
            required_path = {
                "id",
                "title",
                "rationale",
                "novelty",
                "prerequisites",
                "risks",
                "suggested_skills",
                "expected_evidence",
                "external_research",
            }
            if set(row) != required_path:
                raise RecoveryStrategyError("candidate path has an unexpected shape")
            for key in ("id", "title", "rationale", "novelty"):
                if not isinstance(row[key], str) or not row[key].strip():
                    raise RecoveryStrategyError(f"candidate path {key} must be non-empty")
            if row["id"] in seen:
                raise RecoveryStrategyError("candidate path ids must be unique")
            seen.add(row["id"])
            list_fields: dict[str, tuple[str, ...]] = {}
            for key in ("prerequisites", "risks", "suggested_skills", "expected_evidence"):
                value = row[key]
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise RecoveryStrategyError(f"candidate path {key} must be a list of strings")
                list_fields[key] = tuple(item.strip() for item in value if item.strip())
            if not isinstance(row["external_research"], bool):
                raise RecoveryStrategyError("candidate path external_research must be boolean")
            candidates.append(
                CandidateRecoveryPath(
                    id=row["id"].strip(),
                    title=row["title"].strip(),
                    rationale=row["rationale"].strip(),
                    novelty=row["novelty"].strip(),
                    prerequisites=list_fields["prerequisites"],
                    risks=list_fields["risks"],
                    suggested_skills=list_fields["suggested_skills"],
                    expected_evidence=list_fields["expected_evidence"],
                    external_research=row["external_research"],
                )
            )

        recommended = payload["recommended_path_id"].strip()
        if recommended and recommended not in seen:
            raise RecoveryStrategyError("recommended_path_id must reference a candidate path")
        if not recommended and candidates and disposition not in {
            RecoveryDisposition.WAIT_HUMAN,
            RecoveryDisposition.PAUSE,
            RecoveryDisposition.NO_NOVEL_PATH,
        }:
            raise RecoveryStrategyError("a recovery disposition with candidate paths needs a recommendation")

        return RecoveryStrategyAnalysis(
            failure_class=payload["failure_class"].strip(),
            problem_summary=payload["problem_summary"].strip(),
            previous_path_failures=tuple(
                item.strip() for item in payload["previous_path_failures"] if item.strip()
            ),
            candidate_paths=tuple(candidates),
            recommended_path_id=recommended,
            disposition=disposition,
            work_graph_guidance=payload["work_graph_guidance"].strip(),
            human_decision_required=payload["human_decision_required"],
            external_research_required=payload["external_research_required"],
            confidence=confidence,
        )

    @staticmethod
    def _prompt(request: RecoveryStrategyRequest, experience: Sequence[str] | str) -> str:
        learned = experience if isinstance(experience, str) else "\n".join(experience)
        return (
            "You are Adaptive's Recovery Strategist. A Work Unit has returned, "
            "exhausted one or more strategies, or reached a technical blocked state "
            "that is not merely waiting on another dependency. Reanalyze the problem "
            "from first principles and propose materially different safe paths. "
            "You are an analyst only: return organization and options to the "
            "orchestrator; do not implement or dispatch.\n\n"
            f"PROJECT OBJECTIVE:\n{request.project_objective}\n\n"
            f"WORK UNIT {request.work_unit_id}:\n{request.work_unit_objective}\n\n"
            f"CURRENT STATE:\n{request.state_summary}\n\n"
            "PREVIOUS ATTEMPTS / PATHS:\n"
            + ("\n".join(f"- {item}" for item in request.attempt_history) or "- none recorded")
            + "\n\n"
            + (f"RELEVANT VALIDATED/PROVISIONAL ADAPTIVE LEARNING:\n{learned}\n\n" if learned else "")
            + "Return exactly this JSON shape:\n"
            + '{"failure_class":"...","problem_summary":"...",'
              '"previous_path_failures":["..."],"candidate_paths":['
              '{"id":"path-c","title":"...","rationale":"...","novelty":"...",'
              '"prerequisites":[],"risks":[],"suggested_skills":["debugging"],'
              '"expected_evidence":[],"external_research":false}],'
              '"recommended_path_id":"path-c",'
              '"disposition":"REPLAN_WITH_PREREQUISITE",'
              '"work_graph_guidance":"...",'
              '"human_decision_required":false,'
              '"external_research_required":false,"confidence":0.8}'
        )
