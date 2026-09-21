from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from application.planner_output_contract import (
    PLANNER_OUTPUT_SCHEMA_V1,
    planner_output_schema,
)
from application.problem_solving_learning import ProblemSolvingKnowledgeBase
from application.incident_supervisor import IncidentSupervisor
from application.run_orchestration import (
    RunOrchestration,
    RunOrchestrationError,
    RunOrchestrationRequest,
)
from application.structured_output_contract import (
    StructuredOutputContractError,
    validate_structured_json,
)
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

    def replan(
        self,
        request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        state_summary: str,
    ) -> ProjectExecutionPlan:
        ...


class RuntimeProjectPlanner:
    """Use governed runtime calls to create and safely expand a Work Graph.

    Planner output is data, not executable code. Every graph is schema-validated,
    bounded, and later subjected to dependency, policy, skill, and workspace-
    conflict checks before any worker is dispatched.
    """

    def __init__(
        self,
        *,
        runner: RunOrchestration,
        skill_profiles: Sequence[SkillProfile],
        knowledge_base: ProblemSolvingKnowledgeBase | None = None,
        incident_supervisor: IncidentSupervisor | None = None,
    ) -> None:
        self._runner = runner
        self._skill_profiles = tuple(skill_profiles)
        self._knowledge = knowledge_base or ProblemSolvingKnowledgeBase.load_default()
        self._incident_supervisor = incident_supervisor or IncidentSupervisor()

    def plan(self, request: ProjectPlanningRequest) -> ProjectExecutionPlan:
        required_ids = self._explicit_work_unit_ids(request)
        if len(required_ids) > request.max_work_units:
            raise ProjectPlanningError(
                "Explicit Work Unit identifiers in the objective exceed max_work_units: "
                + ", ".join(required_ids)
            )
        try:
            result = self._run_planner(
                request=request,
                objective=self._build_initial_prompt(request),
            )
            plan = self.parse(result, max_work_units=request.max_work_units)
            self._validate_explicit_work_unit_ids(plan, required_ids)
            return plan
        except (ProjectPlanningError, RunOrchestrationError) as exc:
            if isinstance(exc, RunOrchestrationError) and not self._is_contract_failure(exc):
                raise
            failure = str(exc)

        recovered = self._run_planner(
            request=request,
            objective=self._build_initial_recovery_prompt(
                request=request,
                failure=failure,
                required_ids=required_ids,
            ),
        )
        recovery_limit = request.max_work_units if required_ids else 1
        plan = self.parse(recovered, max_work_units=recovery_limit)
        self._validate_explicit_work_unit_ids(plan, required_ids)
        self._knowledge.record_planner_recovery(
            error=failure,
            result=(
                "Recovered with the full explicit Work Unit catalog."
                if required_ids
                else "Recovered with one bounded Work Unit."
            ),
        )
        return plan

    @staticmethod
    def _is_contract_failure(exc: RunOrchestrationError) -> bool:
        message = str(exc)
        return (
            "RESULT_SCHEMA_VALIDATION_FAILED" in message
            or "AMEP application/json payload is invalid" in message
        )

    def replan(
        self,
        request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        state_summary: str,
    ) -> ProjectExecutionPlan:
        """Return a full revised plan while preserving existing Work Unit identity.

        Replanning is deliberately additive at the orchestration boundary. The
        executor ignores attempted edits to existing Work Units and only admits
        genuinely new Work Units and dependency edges after validation. This
        prompt makes that contract explicit so normal runs remain economical.
        """

        if not state_summary.strip():
            raise ProjectPlanningError("Replanning requires a non-empty state summary.")
        try:
            result = self._run_planner(
                request=request,
                objective=self._build_replan_prompt(
                    request=request,
                    current_plan=current_plan,
                    state_summary=state_summary,
                ),
            )
            return self.parse(result, max_work_units=request.max_work_units)
        except (ProjectPlanningError, RunOrchestrationError) as exc:
            if isinstance(exc, RunOrchestrationError) and not self._is_contract_failure(exc):
                raise
            failure = str(exc)

        recovered = self._run_planner(
            request=request,
            objective=self._build_replan_recovery_prompt(
                request=request,
                current_plan=current_plan,
                state_summary=state_summary,
                failure=failure,
            ),
        )
        plan = self.parse(recovered, max_work_units=request.max_work_units)
        existing = {item.id for item in current_plan.work_units}
        new_ids = [item.id for item in plan.work_units if item.id not in existing]
        if len(new_ids) > 1:
            raise ProjectPlanningError(
                "Planner recovery may add at most one new Work Unit."
            )
        self._knowledge.record_planner_recovery(
            error=failure,
            result=(
                "Recovered replanning with no more than one new bounded Work Unit."
            ),
        )
        return plan

    def _run_planner(
        self,
        *,
        request: ProjectPlanningRequest,
        objective: str,
    ) -> str:
        result = self._runner.execute(
            RunOrchestrationRequest(
                objective=objective,
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
                request_message_type="planner.request",
                request_schema_name="planner-request",
                result_message_type="planner.plan",
                result_schema_name="planner-output",
                result_content_type="application/json",
            )
        )
        return result.output

    def _build_initial_prompt(self, request: ProjectPlanningRequest) -> str:
        experience = self._experience_guidance(request)
        explicit_ids = self._explicit_work_unit_ids(request)
        explicit_section = (
            "MANDATORY EXPLICIT WORK UNIT IDS:\n"
            + "\n".join(f"- {item}" for item in explicit_ids)
            + "\nThese identifiers were supplied explicitly by the project request. "
            "Each must remain an independent Work Unit id in the persisted graph; "
            "aggregators may be added, but may not replace or absorb them.\n\n"
            if explicit_ids
            else ""
        )
        return (
            "You are the planning layer of Adaptive AI Orchestrator. Analyze the "
            "project objective and current context, then produce the smallest safe "
            "acyclic Work Graph that can make meaningful progress.\n\n"
            f"PROJECT OBJECTIVE:\n{request.objective}\n\n"
            f"SCOPE:\n{request.scope or '(not separately specified)'}\n\n"
            f"MAX WORK UNITS: {request.max_work_units}\n"
            f"MAX SIMULTANEOUS WORKERS: {request.max_concurrency}\n\n"
            f"{explicit_section}"
            f"{experience + chr(10) + chr(10) if experience else ''}"
            f"{self._planning_rules()}\n\n"
            f"AVAILABLE SKILLS:\n{self._skill_catalog_json()}\n\n"
            "OUTPUT JSON SCHEMA (return one JSON instance that validates against this schema; do not return the schema itself):\n"
            f"{self._schema_json()}"
        )

    def _build_replan_prompt(
        self,
        *,
        request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        state_summary: str,
    ) -> str:
        experience = self._experience_guidance(request, extra=state_summary)
        return (
            "You are the bounded replanning and recovery layer of Adaptive AI "
            "Orchestrator. Replanning can be requested either because a worker "
            "explicitly discovered necessary missing work or because one Work Unit "
            "entered RECOVERY_REQUIRED after multiple distinct worker strategies "
            "exhausted their bounded attempts, or because the delegated plan/scope "
            "itself is invalid (for example wrong/nonexistent write paths). Return "
            "the full plan, preserving every "
            "existing Work Unit id and its meaning exactly. Add only work that is "
            "necessary to achieve the original objective. Do not expand for optional "
            "polish, speculative refactors, or nice-to-have ideas.\n\n"
            f"ORIGINAL PROJECT OBJECTIVE:\n{request.objective}\n\n"
            f"CURRENT PLAN:\n{self._serialize_plan(current_plan)}\n\n"
            f"CURRENT EXECUTION STATE:\n{state_summary}\n\n"
            f"MAX WORK UNITS TOTAL: {request.max_work_units}\n"
            f"MAX SIMULTANEOUS WORKERS: {request.max_concurrency}\n\n"
            f"{experience + chr(10) + chr(10) if experience else ''}"
            "REPLANNING RULES:\n"
            "- Preserve all existing Work Unit ids and semantics; do not remove, rename, or rewrite them.\n"
            "- Existing accepted work remains accepted. Do not create duplicate replacement units for completed work.\n"
            "- Add new Work Units only for necessary newly discovered or recovery work.\n"
            "- RECOVERY_REQUIRED means either distinct worker strategies were exhausted or the delegated plan/scope itself is invalid; do not merely schedule the same Work Unit again unchanged.\n"
            "- When local remediation, diagnosis, corrected scope discovery, or prerequisite work can unblock a RECOVERY_REQUIRED Work Unit, add the smallest bounded new Work Unit(s). Dependency direction is source_id -> target_id, where source must complete first. Therefore recovery MUST point new-remediation -> original-recovery-unit. Never point original-recovery-unit -> new-remediation, because that makes remediation unreachable while the original remains RECOVERY_REQUIRED.\n"
            "- Preserve the original RECOVERY_REQUIRED Work Unit so it can be retried only after the new prerequisite is accepted.\n"
            "- New required dependency edges must be real prerequisites and must keep the graph acyclic.\n"
            "- If a new corrective Work Unit fully satisfies the exact acceptance surface of a returned/recovery Work Unit so that rerunning the original is unnecessary, set reconciles_work_unit_id on the corrective unit to the original id and include the required corrective -> original edge. Use this only for exact evidence-backed reconciliation; otherwise leave it null and retest the original normally.\n"
            "- Prefer direct remediation, fan-in, integration, or verification over duplicating already completed analysis.\n"
            "- If no safe graph change can make progress, return the current plan unchanged rather than inventing work.\n"
            f"{self._planning_rules()}\n\n"
            f"AVAILABLE SKILLS:\n{self._skill_catalog_json()}\n\n"
            "OUTPUT JSON SCHEMA (return one JSON instance that validates against this schema; do not return the schema itself):\n"
            f"{self._schema_json()}"
        )

    def _build_initial_recovery_prompt(
        self,
        *,
        request: ProjectPlanningRequest,
        failure: str,
        required_ids: tuple[str, ...] = (),
    ) -> str:
        experience = self._experience_guidance(
            request,
            extra=f"planning failure: {failure}",
        )
        recovery_instruction = (
            "The previous Adaptive planning response omitted one or more explicit "
            "Work Unit identifiers supplied by the project request. Return a full "
            "corrected plan containing every mandatory identifier as an independent "
            "Work Unit. Aggregators may be added but may not replace them.\n\n"
            if required_ids
            else (
                "The previous Adaptive planning response failed strict structured "
                "validation. Do not repeat the broad plan unchanged. Recover with "
                "exactly ONE smallest safe Work Unit that makes meaningful progress. "
                "If unresolved ambiguity blocks implementation, prefer one read-only "
                "DECISION or RESEARCH Work Unit that reconciles canonical sources and "
                "produces an explicit blocker/decision contract before code changes.\n\n"
            )
        )
        explicit_section = (
            "MANDATORY EXPLICIT WORK UNIT IDS:\n"
            + "\n".join(f"- {item}" for item in required_ids)
            + "\n\n"
            if required_ids
            else ""
        )
        return (
            recovery_instruction
            + explicit_section
            f"PROJECT OBJECTIVE:\n{request.objective}\n\n"
            f"SCOPE:\n{request.scope or '(not separately specified)'}\n\n"
            f"VALIDATION FAILURE:\n{failure}\n\n"
            f"{experience + chr(10) + chr(10) if experience else ''}"
            "RECOVERY RULES:\n"
            + (
                "- Return the full bounded plan and preserve every mandatory explicit Work Unit id.\n"
                if required_ids
                else "- Return exactly one Work Unit and no dependencies.\n"
            )
            "- Keep the Work Unit bounded, independently verifiable and safe.\n"
            "- Planning remains read-only; do not modify project files.\n"
            "- Do not invent business rules or bypass project governance.\n"
            "- Return only one strict JSON object; no Markdown fences.\n\n"
            f"AVAILABLE SKILLS:\n{self._skill_catalog_json()}\n\n"
            "OUTPUT JSON SCHEMA (return a validating JSON instance; do not return the schema itself):\n"
            f"{self._schema_json()}"
        )

    def _build_replan_recovery_prompt(
        self,
        *,
        request: ProjectPlanningRequest,
        current_plan: ProjectExecutionPlan,
        state_summary: str,
        failure: str,
    ) -> str:
        experience = self._experience_guidance(
            request,
            extra=f"{state_summary}\nplanning failure: {failure}",
        )
        return (
            "The previous Adaptive replanning response failed strict structured "
            "validation. Preserve the entire existing plan exactly and recover "
            "conservatively. Add AT MOST ONE new bounded Work Unit, and only if it "
            "is genuinely necessary. If a Work Unit is RECOVERY_REQUIRED, prefer "
            "one concrete remediation, corrected-scope discovery, or diagnostic prerequisite and connect it as "
            "a required dependency into that original Work Unit. If uncertainty "
            "blocks implementation, that single new unit should resolve the blocker "
            "before more code work.\n\n"
            f"ORIGINAL PROJECT OBJECTIVE:\n{request.objective}\n\n"
            f"CURRENT PLAN:\n{self._serialize_plan(current_plan)}\n\n"
            f"CURRENT EXECUTION STATE:\n{state_summary}\n\n"
            f"VALIDATION FAILURE:\n{failure}\n\n"
            f"{experience + chr(10) + chr(10) if experience else ''}"
            "RECOVERY RULES:\n"
            "- Preserve every existing Work Unit id and meaning.\n"
            "- Add zero or one genuinely necessary Work Unit.\n"
            "- Keep required dependencies acyclic and real.\n"
            "- Do not invent business rules or optional polish.\n"
            "- Return only one strict JSON object; no Markdown fences.\n\n"
            f"AVAILABLE SKILLS:\n{self._skill_catalog_json()}\n\n"
            "OUTPUT JSON SCHEMA (return a validating JSON instance; do not return the schema itself):\n"
            f"{self._schema_json()}"
        )

    def _experience_guidance(
        self,
        request: ProjectPlanningRequest,
        *,
        extra: str = "",
    ) -> str:
        text = "\n".join(
            (
                request.objective,
                request.scope,
                *request.context,
                *request.constraints,
                extra,
            )
        )
        guidance = self._knowledge.render_guidance(text)
        incident_obligations = self._incident_supervisor.render_planner_obligations()
        sections = [item for item in (guidance, incident_obligations) if item]
        if not sections:
            return ""
        return (
            "\n".join(sections)
            + "\nTreat learned experience and active-incident obligations as process "
            "guidance only. They do not override project facts, approved requirements, "
            "security policy, side-effect authority, or human approval boundaries."
        )

    @staticmethod
    def _explicit_work_unit_ids(
        request: ProjectPlanningRequest,
    ) -> tuple[str, ...]:
        text = "\n".join(
            (
                request.objective,
                request.scope,
                *request.context,
                *request.constraints,
            )
        )
        found = re.findall(
            r"(?<![A-Za-z0-9])WU-[A-Za-z0-9][A-Za-z0-9-]*(?![A-Za-z0-9-])",
            text,
            flags=re.IGNORECASE,
        )
        ordered: list[str] = []
        seen: set[str] = set()
        for value in found:
            canonical = value.upper()
            if canonical in seen:
                continue
            seen.add(canonical)
            ordered.append(canonical)
        return tuple(ordered)

    @staticmethod
    def _validate_explicit_work_unit_ids(
        plan: ProjectExecutionPlan,
        required_ids: Sequence[str],
    ) -> None:
        if not required_ids:
            return
        planned = {item.id.upper() for item in plan.work_units}
        missing = [item for item in required_ids if item.upper() not in planned]
        if missing:
            raise ProjectPlanningError(
                "EXPLICIT_WORK_UNIT_IDS_MISSING: planner must preserve explicitly "
                "named Work Unit ids as independent nodes: " + ", ".join(missing)
            )

    @staticmethod
    def _planning_rules() -> str:
        return (
            "PLANNING RULES:\n"
            "- Respect project governance, gates, approved architecture and facts in context.\n"
            "- Do not invent requirements merely to complete the graph.\n"
            "- Use project-discovery/research/decision units only when uncertainty materially blocks work.\n"
            "- Do not serialize frontend and backend by habit. Add a blocking edge only for a real prerequisite.\n"
            "- Dependency direction is strict: source_id is the prerequisite that must complete before target_id can become eligible. Read source_id -> target_id as 'source before target'.\n"
            "- Once a contract/interface is stable enough, allow independent backend, frontend, testing, review, or other units to share the ready frontier.\n"
            "- Parallel work may be backend/backend, frontend/frontend, frontend/backend, research/research, or other combinations.\n"
            "- Prefer a few independently valuable Work Units over token-expensive micro-fragmentation. There is no fixed worker pool; workers exist only for useful ready units.\n"
            "- When the objective contains a long checklist of independent obligations, split it into bounded closed Work Units/lots that can each be completed and verified in one execution; do not hide an independent backlog inside one giant Work Unit merely to avoid fragmentation.\n"
            "- If the request explicitly names Work Unit ids (for example WU-ABC-01), preserve every named id as an independent Work Unit. Aggregators or fan-in units may coexist, but must never replace or absorb explicitly named units.\n"
            "- Missing implementation details, wiring, tests, repositories, ports, or transactions that are already authorized by a Work Unit are work inside that unit, not a blocker or HUMAN_ACTION boundary.\n"
            "- Reserve HUMAN_ACTION or blocked planning for genuine missing human decisions/authority or external prerequisites that an authorized worker cannot satisfy.\n"
            "- Give every write-capable unit precise repository-relative write_paths. If write scope is unknown or shared broadly, set parallel_safe=false.\n"
            "- Read-only units use requested_side_effects=[] and write_paths=[]. File-editing units request filesystem.write. Do not request deploy/publication/destructive effects unless the user objective explicitly authorizes them.\n"
            "- Use acceptance_criteria=[\"runtime-completed\"] unless a literal machine-verifiable marker is truly available. Put semantic verification into explicit testing/review/integration Work Units instead of pretending string matching proves correctness.\n"
            "- Include fan-in integration or verification units when multiple parallel results must be reconciled.\n"
            "- reconciles_work_unit_id is normally null. Use it only for an evidence-backed corrective unit that can formally satisfy an already-returned/recovery unit without rerunning it, and always pair it with a required corrective -> original dependency edge.\n"
            "- HUMAN_ACTION is for genuine human-only or approval-required work; do not fabricate an agent for it.\n"
            "- requested_skills may contain only ids from AVAILABLE SKILLS. required_capabilities should describe what the Work Unit needs; the orchestrator may minimize the final skill set."
        )

    def _skill_catalog_json(self) -> str:
        catalog = [
            {
                "id": profile.id.value,
                "capabilities": list(profile.capabilities),
                "purpose": profile.purpose,
            }
            for profile in self._skill_profiles
            if profile.id.value != "adaptive-orchestrator-bridge"
        ]
        return json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _schema_json() -> str:
        return json.dumps(
            PLANNER_OUTPUT_SCHEMA_V1,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _serialize_plan(plan: ProjectExecutionPlan) -> str:
        payload = {
            "summary": plan.summary,
            "work_units": [
                {
                    "id": item.id,
                    "objective": item.objective,
                    "role": item.role,
                    "scope": item.scope,
                    "kind": item.kind.value,
                    "required_capabilities": list(item.required_capabilities),
                    "requested_skills": list(item.requested_skills),
                    "tools": list(item.tools),
                    "inputs": list(item.inputs),
                    "expected_output": list(item.expected_output),
                    "acceptance_criteria": list(item.acceptance_criteria),
                    "requested_side_effects": list(item.requested_side_effects),
                    "write_paths": list(item.write_paths),
                    "priority": item.priority,
                    "criticality": item.criticality,
                    "parallel_safe": item.parallel_safe,
                    "reconciles_work_unit_id": item.reconciles_work_unit_id,
                }
                for item in plan.work_units
            ],
            "dependencies": [
                {
                    "source_id": item.source_id,
                    "target_id": item.target_id,
                    "required": item.required,
                    "condition": item.condition,
                }
                for item in plan.dependencies
            ],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def parse(cls, text: str, *, max_work_units: int) -> ProjectExecutionPlan:
        try:
            payload, _ = validate_structured_json(
                text,
                planner_output_schema(max_work_units),
            )
        except StructuredOutputContractError as exc:
            raise ProjectPlanningError(str(exc)) from exc
        if not isinstance(payload, dict):
            raise ProjectPlanningError("Planner root value must be a JSON object.")
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
            reconciles_work_unit_id=(
                str(entry["reconciles_work_unit_id"]).strip()
                if entry.get("reconciles_work_unit_id") is not None
                else None
            ),
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
