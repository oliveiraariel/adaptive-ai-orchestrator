from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RecoveryDisposition(str, Enum):
    RETRY_DIFFERENT_STRATEGY = "RETRY_DIFFERENT_STRATEGY"
    REPLAN_WITH_PREREQUISITE = "REPLAN_WITH_PREREQUISITE"
    EXTERNAL_RESEARCH = "EXTERNAL_RESEARCH"
    WAIT_HUMAN = "WAIT_HUMAN"
    PAUSE = "PAUSE"
    NO_NOVEL_PATH = "NO_NOVEL_PATH"


@dataclass(frozen=True)
class CandidateRecoveryPath:
    id: str
    title: str
    rationale: str
    novelty: str
    prerequisites: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    suggested_skills: tuple[str, ...] = ()
    expected_evidence: tuple[str, ...] = ()
    external_research: bool = False


@dataclass(frozen=True)
class RecoveryStrategyAnalysis:
    failure_class: str
    problem_summary: str
    previous_path_failures: tuple[str, ...]
    candidate_paths: tuple[CandidateRecoveryPath, ...]
    recommended_path_id: str
    disposition: RecoveryDisposition
    work_graph_guidance: str
    human_decision_required: bool
    external_research_required: bool
    confidence: float

    @property
    def recommended_path(self) -> CandidateRecoveryPath | None:
        for candidate in self.candidate_paths:
            if candidate.id == self.recommended_path_id:
                return candidate
        return None

    def planner_guidance(self) -> str:
        lines = [
            "RECOVERY STRATEGIST ANALYSIS:",
            f"failure_class={self.failure_class}",
            f"problem_summary={self.problem_summary}",
            f"disposition={self.disposition.value}",
            f"recommended_path_id={self.recommended_path_id or '(none)'}",
            f"human_decision_required={str(self.human_decision_required).lower()}",
            f"external_research_required={str(self.external_research_required).lower()}",
            f"confidence={self.confidence:.2f}",
        ]
        if self.previous_path_failures:
            lines.append("previous_path_failures:")
            lines.extend(f"- {item}" for item in self.previous_path_failures)
        if self.candidate_paths:
            lines.append("candidate_paths:")
            for candidate in self.candidate_paths:
                lines.append(
                    f"- {candidate.id}: {candidate.title}; novelty={candidate.novelty}; "
                    f"external_research={str(candidate.external_research).lower()}"
                )
        lines.append("work_graph_guidance:")
        lines.append(self.work_graph_guidance)
        return "\n".join(lines)
