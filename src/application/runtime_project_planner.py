from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from application.run_orchestration import RunOrchestration, RunOrchestrationRequest
from domain.project_execution_plan import (
    PlannedDependency,
    PlannedWorkUnit,
    ProjectExecutionPlan,
    ProjectExecutionPlanError,
)
from domain.skill_profile import SkillProfile
from domain.work_unit import WorkUnitKind


class ProjectPlanningError(ValueError):
    """Raised when the planning provider cannot produce a safe structured plan."""


@dataclass(frozen=True)
class ProjectPlanningRequest:
    objective: str
    scope: str = ""
    context: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    agent: str = "main"
    max_work_units: int = 24
    max_concurrency: int = 4

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ProjectPlanningError("Project objective must not be blank.")
        if self.max_work_units < 1:
            raise ProjectPlanningError("max_work_units must be at least 1.")
        if self.max_concurrency < 1:
            raise ProjectPlanningError("max_concurrency must be at least 1.")


class ProjectPlanner(Protocol):
    def plan(self, request: ProjectPlanningRequest) -> ProjectExecutionPlan:
        ...


class RuntimeProjectPlanner:
    """Use a governed runtime call to turn a broad objective into a Work Graph.

    The planner returns data, not executable code. The returned graph is parsed,
    schema-validated, bounded, and later subjected to dependency, policy, skill,
    and workspace-conflict checks before any worker is dispatched.
    """

    def __init__(
        self,
        *,
        runner: RunOrchestration,
        skill_profiles: Sequence[SkillProfile],
    ) -> None:
        self._runner = runner
        self._skill_profiles = tuple(skill_profiles)

    def plan(self, request: ProjectPlanningRequest) -> ProjectExecutionPlan:
        prompt = self._build_prompt(request)
        result = self._runner.execute(
            RunOrchestrationRequest(
                objective=prompt,
                agent=request.agent,
                skills=(
                    "engineering-lifecycle",
                    "project-discovery",
                    "work-decomposition",
                ),
                scope=request.scope,
                context=request.context,
                constraints=(
                    *request.constraints,
                    "Planning is read-only. Do not modify project files.",
                    "Return only the requested JSON object; no Markdown fences.",
                ),
                expected_output=("strict JSON project execution plan",),
                acceptance_criteria=("runtime-completed",),
            )
        )
        return self.parse(result.output, max_work_units=request.max_work_units)

    def _build_prompt(self, request: ProjectPlanningRequest) -> str:
        catalog = [
            {
                "id": profile.id.value,
                "capabilities": list(profile.capabilities),
                "purpose": profile.purpose,
            }
            for profile in self._skill_profiles
            if profile.id.value != "adaptive-orchestrator-bridge"
        ]
        schema = {
            "summary": "short plan rationale",
            "work_units": [
                {
                    "id": "stable-short-id",
                    "objective": "one independently verifiable objective",
                    "role": "logical specialist role",
                    "scope": "bounded scope",
                    "kind": "EXECUTION|DECISION|RESEARCH|PROTOTYPE|HUMAN_ACTION",
                    "required_capabilities": ["capability.id"],
                    "requested_skills": ["skill-id"],
                    "tools": [],
                    "inputs": [],
                    "expected_output": ["artifact/evidence"],
                    "acceptance_criteria": ["runtime-completed"],
                    "requested_side_effects": ["filesystem.write"],
                    "write_paths": ["relative/path/prefix"],
                    "priority": 10,
                    "criticality": 0,
                    "parallel_safe": True,
                }
            ],
            "dependencies": [
                {
                    "source_id": "producer-id",
                    "target_id": "consumer-id",
                    "required": True,
                    "condition": None,
                }
            ],
        }
        return (
            "You are the planning layer of Adaptive AI Orchestrator. Analyze the "
            "project objective and current context, then produce the smallest safe "
            "acyclic Work Graph that can make meaningful progress.\n\n"
            f"PROJECT OBJECTIVE:\n{request.objective}\n\n"
            f"SCOPE:\n{request.scope or '(not separately specified)'}\n\n"
            f"MAX WORK UNITS: {request.max_work_units}\n"
            f"MAX SIMULTANEOUS WORKERS: {request.max_concurrency}\n\n"
            "PLANNING RULES:\n"
            "- Respect project governance, gates, approved architecture and facts in context.\n"
            "- Do not invent requirements merely to complete the graph.\n"
            "- Use project-discovery/research/decision units only when uncertainty materially blocks work.\n"
            "- Do not serialize frontend and backend by habit. Add a blocking edge only for a real prerequisite.\n"
            "- Once a contract/interface is stable enough, allow independent backend, frontend, testing, review, or other units to share the ready frontier.\n"
            "- Parallel work may be backend/backend, frontend/frontend, frontend/backend, research/research, or other combinations.\n"
            "- Prefer a few independently valuable Work Units over token-expensive micro-fragmentation. There is no fixed worker pool; workers exist only for useful ready units.\n"
            "- Give every write-capable unit precise repository-relative write_paths. If write scope is unknown or shared broadly, set parallel_safe=false.\n"
            "- Read-only units use requested_side_effects=[] and write_paths=[]. File-editing units request filesystem.write. Do not request deploy/publication/destructive effects unless the user objective explicitly authorizes them.\n"
            "- Use acceptance_criteria=[\"runtime-completed\"] unless a literal machine-verifiable marker is truly available. Put semantic verification into explicit testing/review/integration Work Units instead of pretending string matching proves correctness.\n"
            "- Include fan-in integration or verification units when multiple parallel results must be reconciled.\n"
            "- HUMAN_ACTION is for genuine human-only or approval-required work; do not fabricate an agent for it.\n"
            "- requested_skills may contain only ids from AVAILABLE SKILLS. required_capabilities should describe what the Work Unit needs; the orchestrator may minimize the final skill set.\n\n"
            f"AVAILABLE SKILLS:\n{json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))}\n\n"
            "OUTPUT SCHEMA EXAMPLE (return one JSON object with this shape):\n"
            f"{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}"
        )

    @classmethod
    def parse(cls, text: str, *, max_work_units: int) -> ProjectExecutionPlan:
        payload = cls._decode_json_object(text)
        summary = payload.get("summary")
        entries = payload.get("work_units")
        dependency_entries = payload.get("dependencies", [])

        if not isinstance(summary, str) or not summary.strip():
            raise ProjectPlanningError("Planner output requires non-empty summary.")
        if not isinstance(entries, list) or not entries:
            raise ProjectPlanningError("Planner output requires a non-empty work_units list.")
        if len(entries) > max_work_units:
            raise ProjectPlanningError(
                f"Planner produced {len(entries)} Work Units; limit is {max_work_units}."
            )
        if not isinstance(dependency_entries, list):
            raise ProjectPlanningError("Planner dependencies must be a list.")

        work_units = tuple(cls._parse_work_unit(entry) for entry in entries)
        dependencies = tuple(
            cls._parse_dependency(entry) for entry in dependency_entries
        )
        try:
            return ProjectExecutionPlan(
                summary=summary,
                work_units=work_units,
                dependencies=dependencies,
            )
        except ProjectExecutionPlanError as exc:
            raise ProjectPlanningError(str(exc)) from exc

    @staticmethod
    def _decode_json_object(text: str) -> dict:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                candidate = "\n".join(lines[1:-1])
                if candidate.lstrip().startswith("json"):
                    candidate = candidate.lstrip()[4:].lstrip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start < 0 or end <= start:
                raise ProjectPlanningError("Planner did not return a JSON object.")
            try:
                payload = json.loads(candidate[start : end + 1])
            except json.JSONDecodeError as exc:
                raise ProjectPlanningError(f"Planner returned invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ProjectPlanningError("Planner root value must be a JSON object.")
        return payload

    @classmethod
    def _parse_work_unit(cls, entry: object) -> PlannedWorkUnit:
        if not isinstance(entry, dict):
            raise ProjectPlanningError("Each planned Work Unit must be an object.")
        try:
            kind = WorkUnitKind(str(entry.get("kind", "EXECUTION")).upper())
        except ValueError as exc:
            raise ProjectPlanningError(
                f"Unsupported Work Unit kind: {entry.get('kind')!r}."
            ) from exc

        work_unit_id = cls._required_string(entry, "id")
        objective = cls._required_string(entry, "objective")
        role = str(entry.get("role", "worker")).strip() or "worker"
        scope = str(entry.get("scope", ""))

        return PlannedWorkUnit(
            id=work_unit_id,
            objective=objective,
            role=role,
            scope=scope,
            kind=kind,
            required_capabilities=cls._string_tuple(entry, "required_capabilities"),
            requested_skills=cls._string_tuple(entry, "requested_skills"),
            tools=cls._string_tuple(entry, "tools"),
            inputs=cls._string_tuple(entry, "inputs"),
            expected_output=cls._string_tuple(
                entry, "expected_output", default=("agent response",)
            ),
            acceptance_criteria=cls._string_tuple(
                entry, "acceptance_criteria", default=("runtime-completed",)
            ),
            requested_side_effects=cls._string_tuple(
                entry, "requested_side_effects"
            ),
            write_paths=cls._string_tuple(entry, "write_paths"),
            priority=cls._non_negative_int(entry, "priority", default=0),
            criticality=cls._non_negative_int(entry, "criticality", default=0),
            parallel_safe=cls._bool(entry, "parallel_safe", default=True),
        )

    @classmethod
    def _parse_dependency(cls, entry: object) -> PlannedDependency:
        if not isinstance(entry, dict):
            raise ProjectPlanningError("Each planned dependency must be an object.")
        condition = entry.get("condition")
        if condition is not None and not isinstance(condition, str):
            raise ProjectPlanningError("Dependency condition must be a string or null.")
        return PlannedDependency(
            source_id=cls._required_string(entry, "source_id"),
            target_id=cls._required_string(entry, "target_id"),
            required=cls._bool(entry, "required", default=True),
            condition=condition,
        )

    @staticmethod
    def _required_string(entry: dict, field: str) -> str:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ProjectPlanningError(f"Planner field '{field}' must be non-empty string.")
        return value.strip()

    @staticmethod
    def _string_tuple(
        entry: dict,
        field: str,
        *,
        default: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        value = entry.get(field)
        if value is None:
            return default
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise ProjectPlanningError(
                f"Planner field '{field}' must be a list of non-empty strings."
            )
        return tuple(item.strip() for item in value) or default

    @staticmethod
    def _non_negative_int(entry: dict, field: str, *, default: int) -> int:
        value = entry.get(field, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ProjectPlanningError(
                f"Planner field '{field}' must be a non-negative integer."
            )
        return value

    @staticmethod
    def _bool(entry: dict, field: str, *, default: bool) -> bool:
        value = entry.get(field, default)
        if not isinstance(value, bool):
            raise ProjectPlanningError(f"Planner field '{field}' must be boolean.")
        return value
