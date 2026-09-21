from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from application.structured_output_contract import (
    StructuredOutputContractError,
    validate_structured_json,
)
from application.work_graph_migration_contract import work_graph_migration_schema
from domain.project_execution_plan import (
    PlannedDependency,
    PlannedWorkUnit,
    ProjectExecutionPlan,
    ProjectExecutionPlanError,
)
from domain.work_unit import WorkUnitKind


class WorkGraphMigrationError(ValueError):
    """Raised when a Work Graph migration would violate orchestration invariants."""


@dataclass(frozen=True)
class EvidenceLineage:
    source_work_unit_id: str
    result_ref: str | None = None
    note: str = ""


@dataclass(frozen=True)
class MigrationWorkUnit:
    spec: PlannedWorkUnit
    initial_state: str = "PLANNED"
    evidence_lineage: tuple[EvidenceLineage, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkGraphMigrationSpec:
    migration_id: str
    reason: str
    work_units: tuple[MigrationWorkUnit, ...]
    dependencies: tuple[PlannedDependency, ...]
    resume_recovery_targets: tuple[str, ...] = field(default_factory=tuple)
    consume_pending_replan: bool = False
    schema_version: str = "work-graph-migration/1"
    canonical_json: str = ""

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkGraphMigrationPreview:
    migration_id: str
    spec_digest: str
    checkpoint_digest: str
    before_graph_digest: str
    after_graph_digest: str
    before_work_unit_count: int
    after_work_unit_count: int
    new_work_unit_ids: tuple[str, ...]
    initially_completed_work_unit_ids: tuple[str, ...]
    resumed_recovery_targets: tuple[str, ...]
    added_dependency_count: int
    apply_ready: bool
    apply_blockers: tuple[str, ...]
    already_applied: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "spec_digest": self.spec_digest,
            "checkpoint_digest": self.checkpoint_digest,
            "before_graph_digest": self.before_graph_digest,
            "after_graph_digest": self.after_graph_digest,
            "before_work_unit_count": self.before_work_unit_count,
            "after_work_unit_count": self.after_work_unit_count,
            "new_work_unit_ids": list(self.new_work_unit_ids),
            "initially_completed_work_unit_ids": list(
                self.initially_completed_work_unit_ids
            ),
            "resumed_recovery_targets": list(self.resumed_recovery_targets),
            "added_dependency_count": self.added_dependency_count,
            "apply_ready": self.apply_ready,
            "apply_blockers": list(self.apply_blockers),
            "already_applied": self.already_applied,
        }


def canonical_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def checkpoint_digest(checkpoint: Mapping[str, Any]) -> str:
    return canonical_digest(checkpoint)


def graph_snapshot(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "plan": deepcopy(checkpoint.get("plan")),
        "work_unit_states": deepcopy(checkpoint.get("work_unit_states")),
        "dependency_states": deepcopy(checkpoint.get("dependency_states")),
        "pending_replan": bool(checkpoint.get("pending_replan", False)),
        "replan_feedback": str(checkpoint.get("replan_feedback") or ""),
    }


def graph_digest(checkpoint: Mapping[str, Any]) -> str:
    return canonical_digest(graph_snapshot(checkpoint))


def parse_work_graph_migration(
    text: str,
    *,
    max_new_work_units: int,
) -> WorkGraphMigrationSpec:
    try:
        payload, canonical = validate_structured_json(
            text,
            work_graph_migration_schema(max_new_work_units),
        )
    except StructuredOutputContractError as exc:
        raise WorkGraphMigrationError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise WorkGraphMigrationError("Migration root must be an object.")

    work_units = tuple(_migration_work_unit(item) for item in payload["work_units"])
    ids = [item.spec.id for item in work_units]
    if len(ids) != len(set(ids)):
        raise WorkGraphMigrationError("Migration Work Unit ids must be unique.")

    dependencies = tuple(
        _planned_dependency(item) for item in payload["dependencies"]
    )
    resume_targets = tuple(str(item).strip() for item in payload["resume_recovery_targets"])
    if len(resume_targets) != len(set(resume_targets)):
        raise WorkGraphMigrationError("resume_recovery_targets must be unique.")

    return WorkGraphMigrationSpec(
        migration_id=str(payload["migration_id"]).strip(),
        reason=str(payload["reason"]).strip(),
        work_units=work_units,
        dependencies=dependencies,
        resume_recovery_targets=resume_targets,
        consume_pending_replan=bool(payload["consume_pending_replan"]),
        schema_version=str(payload["schema_version"]),
        canonical_json=canonical,
    )


class WorkGraphMigrationService:
    """Plan and apply additive, evidence-backed migrations to paused Work Graphs.

    Existing Work Units and existing dependency edges are immutable. Migration
    may add new Work Units and new edges touching at least one new Work Unit.
    A RECOVERY_REQUIRED historical Work Unit may be resumed only when the
    migration adds a new required prerequisite into it.
    """

    def preview(
        self,
        *,
        orchestration_id: str,
        checkpoint: Mapping[str, Any],
        spec: WorkGraphMigrationSpec,
    ) -> WorkGraphMigrationPreview:
        existing_migration = self._existing_migration(checkpoint, spec.migration_id)
        if existing_migration is not None:
            previous_digest = str(existing_migration.get("spec_digest") or "")
            if previous_digest != spec.digest:
                raise WorkGraphMigrationError(
                    f"Migration id '{spec.migration_id}' was already applied with "
                    "a different spec digest."
                )
            states = self._states(checkpoint)
            return WorkGraphMigrationPreview(
                migration_id=spec.migration_id,
                spec_digest=spec.digest,
                checkpoint_digest=checkpoint_digest(checkpoint),
                before_graph_digest=graph_digest(checkpoint),
                after_graph_digest=graph_digest(checkpoint),
                before_work_unit_count=len(states),
                after_work_unit_count=len(states),
                new_work_unit_ids=(),
                initially_completed_work_unit_ids=(),
                resumed_recovery_targets=(),
                added_dependency_count=0,
                apply_ready=True,
                apply_blockers=(),
                already_applied=True,
            )

        simulated = self._build_migrated_checkpoint(
            orchestration_id=orchestration_id,
            checkpoint=checkpoint,
            spec=spec,
            artifact_ref=None,
            applied_at=None,
            include_migration_record=False,
        )
        blockers = self._apply_blockers(checkpoint)
        before_states = self._states(checkpoint)
        return WorkGraphMigrationPreview(
            migration_id=spec.migration_id,
            spec_digest=spec.digest,
            checkpoint_digest=checkpoint_digest(checkpoint),
            before_graph_digest=graph_digest(checkpoint),
            after_graph_digest=graph_digest(simulated),
            before_work_unit_count=len(before_states),
            after_work_unit_count=len(self._states(simulated)),
            new_work_unit_ids=tuple(item.spec.id for item in spec.work_units),
            initially_completed_work_unit_ids=tuple(
                item.spec.id
                for item in spec.work_units
                if item.initial_state == "COMPLETED"
            ),
            resumed_recovery_targets=spec.resume_recovery_targets,
            added_dependency_count=len(spec.dependencies),
            apply_ready=not blockers,
            apply_blockers=blockers,
        )

    def apply(
        self,
        *,
        orchestration_id: str,
        checkpoint: Mapping[str, Any],
        spec: WorkGraphMigrationSpec,
        expected_checkpoint_digest: str,
        artifact_ref: str,
        applied_at: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        existing_migration = self._existing_migration(checkpoint, spec.migration_id)
        if existing_migration is not None:
            previous_digest = str(existing_migration.get("spec_digest") or "")
            if previous_digest != spec.digest:
                raise WorkGraphMigrationError(
                    f"Migration id '{spec.migration_id}' was already applied with "
                    "a different spec digest."
                )
            receipt = deepcopy(existing_migration.get("receipt"))
            if not isinstance(receipt, dict):
                receipt = self._receipt_from_existing(
                    orchestration_id=orchestration_id,
                    checkpoint=checkpoint,
                    spec=spec,
                    artifact_ref=artifact_ref,
                )
            return deepcopy(dict(checkpoint)), receipt, True

        actual_digest = checkpoint_digest(checkpoint)
        if expected_checkpoint_digest != actual_digest:
            raise WorkGraphMigrationError(
                "Checkpoint changed after dry-run. Re-run the migration preview "
                "and apply only the newly reported checkpoint_digest."
            )
        blockers = self._apply_blockers(checkpoint)
        if blockers:
            raise WorkGraphMigrationError(
                "Migration apply requires a paused, quiescent, non-terminal "
                "orchestration: " + "; ".join(blockers)
            )

        timestamp = applied_at or datetime.now(timezone.utc).isoformat()
        migrated = self._build_migrated_checkpoint(
            orchestration_id=orchestration_id,
            checkpoint=checkpoint,
            spec=spec,
            artifact_ref=artifact_ref,
            applied_at=timestamp,
            include_migration_record=False,
        )
        before_snapshot = graph_snapshot(checkpoint)
        after_snapshot = graph_snapshot(migrated)
        receipt = {
            "schema_version": "work-graph-migration-receipt/1",
            "migration_id": spec.migration_id,
            "orchestration_id": orchestration_id,
            "reason": spec.reason,
            "spec_digest": spec.digest,
            "before_checkpoint_digest": actual_digest,
            "before_graph_digest": canonical_digest(before_snapshot),
            "after_graph_digest": canonical_digest(after_snapshot),
            "artifact_ref": artifact_ref,
            "applied_at": timestamp,
            "new_work_unit_ids": [item.spec.id for item in spec.work_units],
            "initially_completed_work_unit_ids": [
                item.spec.id
                for item in spec.work_units
                if item.initial_state == "COMPLETED"
            ],
            "resumed_recovery_targets": list(spec.resume_recovery_targets),
            "added_dependencies": [
                _planned_dependency_to_payload(item) for item in spec.dependencies
            ],
            "evidence_lineage": {
                item.spec.id: [
                    {
                        "source_work_unit_id": evidence.source_work_unit_id,
                        "result_ref": evidence.result_ref,
                        "note": evidence.note,
                    }
                    for evidence in item.evidence_lineage
                ]
                for item in spec.work_units
                if item.evidence_lineage
            },
            "before": before_snapshot,
            "after": after_snapshot,
        }
        migration_entry = {
            "schema_version": spec.schema_version,
            "migration_id": spec.migration_id,
            "spec_digest": spec.digest,
            "artifact_ref": artifact_ref,
            "applied_at": timestamp,
            "before_graph_digest": receipt["before_graph_digest"],
            "after_graph_digest": receipt["after_graph_digest"],
            "receipt": receipt,
        }
        history = migrated.get("graph_migrations")
        if not isinstance(history, list):
            history = []
        migrated["graph_migrations"] = [*history, migration_entry]
        return migrated, receipt, False

    def _build_migrated_checkpoint(
        self,
        *,
        orchestration_id: str,
        checkpoint: Mapping[str, Any],
        spec: WorkGraphMigrationSpec,
        artifact_ref: str | None,
        applied_at: str | None,
        include_migration_record: bool,
    ) -> dict[str, Any]:
        if checkpoint.get("terminal") is True:
            raise WorkGraphMigrationError(
                "Terminal orchestrations cannot be structurally migrated."
            )
        if checkpoint.get("phase") != "EXECUTION":
            raise WorkGraphMigrationError(
                "Work Graph migration requires an EXECUTION checkpoint with a persisted plan."
            )
        if checkpoint.get("orchestration_id") not in {None, orchestration_id}:
            raise WorkGraphMigrationError("Checkpoint orchestration identity mismatch.")

        plan_raw = checkpoint.get("plan")
        if not isinstance(plan_raw, dict):
            raise WorkGraphMigrationError("Checkpoint is missing a persisted plan.")
        current_units_raw = plan_raw.get("work_units")
        current_deps_raw = plan_raw.get("dependencies")
        if not isinstance(current_units_raw, list) or not isinstance(current_deps_raw, list):
            raise WorkGraphMigrationError("Checkpoint plan is malformed.")

        states = self._states(checkpoint)
        existing_ids = {
            str(item.get("id"))
            for item in current_units_raw
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if existing_ids != set(states):
            raise WorkGraphMigrationError(
                "Checkpoint plan/state Work Unit identities do not match."
            )

        new_ids = {item.spec.id for item in spec.work_units}
        overlap = sorted(existing_ids & new_ids)
        if overlap:
            raise WorkGraphMigrationError(
                "Migration is additive and cannot replace existing Work Units: "
                + ", ".join(overlap)
            )

        request_raw = checkpoint.get("request")
        if not isinstance(request_raw, dict):
            raise WorkGraphMigrationError("Checkpoint is missing the orchestration request.")
        max_work_units = request_raw.get("max_work_units")
        if isinstance(max_work_units, bool) or not isinstance(max_work_units, int):
            raise WorkGraphMigrationError("Checkpoint max_work_units is invalid.")
        if len(existing_ids) + len(new_ids) > max_work_units:
            raise WorkGraphMigrationError(
                f"Migration would create {len(existing_ids) + len(new_ids)} Work Units; "
                f"limit is {max_work_units}."
            )

        combined_known = existing_ids | new_ids
        old_edges = {
            (
                str(item.get("source_id")),
                str(item.get("target_id")),
                bool(item.get("required", True)),
            )
            for item in current_deps_raw
            if isinstance(item, dict)
        }
        seen_new_edges: set[tuple[str, str, bool]] = set()
        for dependency in spec.dependencies:
            edge = (
                dependency.source_id,
                dependency.target_id,
                dependency.required,
            )
            if edge in old_edges or edge in seen_new_edges:
                raise WorkGraphMigrationError(
                    "Migration dependency duplicates an existing or new edge: "
                    f"{dependency.source_id}->{dependency.target_id}."
                )
            if dependency.source_id not in combined_known or dependency.target_id not in combined_known:
                raise WorkGraphMigrationError(
                    "Migration dependency references an unknown Work Unit."
                )
            if (
                dependency.source_id not in new_ids
                and dependency.target_id not in new_ids
            ):
                raise WorkGraphMigrationError(
                    "Migration cannot alter topology only between historical Work Units; "
                    "every new edge must touch at least one newly materialized Work Unit."
                )
            seen_new_edges.add(edge)

        recovery_ids = {
            work_unit_id
            for work_unit_id, state in states.items()
            if state == "RECOVERY_REQUIRED"
        }
        resume_targets = set(spec.resume_recovery_targets)
        unknown_resume = sorted(resume_targets - existing_ids)
        if unknown_resume:
            raise WorkGraphMigrationError(
                "Recovery resume target does not exist historically: "
                + ", ".join(unknown_resume)
            )
        invalid_resume = sorted(resume_targets - recovery_ids)
        if invalid_resume:
            raise WorkGraphMigrationError(
                "Recovery resume target is not RECOVERY_REQUIRED: "
                + ", ".join(invalid_resume)
            )
        for target in sorted(resume_targets):
            if not any(
                dependency.required
                and dependency.source_id in new_ids
                and dependency.target_id == target
                for dependency in spec.dependencies
            ):
                raise WorkGraphMigrationError(
                    f"Recovery target '{target}' requires at least one new required "
                    "prerequisite edge into the historical Work Unit."
                )
        if spec.consume_pending_replan:
            unresolved = sorted(recovery_ids - resume_targets)
            if unresolved:
                raise WorkGraphMigrationError(
                    "consume_pending_replan cannot clear replanning while other "
                    "RECOVERY_REQUIRED Work Units remain: " + ", ".join(unresolved)
                )

        for item in spec.work_units:
            if item.initial_state == "COMPLETED":
                if not item.evidence_lineage:
                    raise WorkGraphMigrationError(
                        f"Completed migrated Work Unit '{item.spec.id}' requires "
                        "explicit evidence_lineage."
                    )
                sources = {
                    evidence.source_work_unit_id
                    for evidence in item.evidence_lineage
                }
                unknown_sources = sorted(sources - existing_ids)
                if unknown_sources:
                    raise WorkGraphMigrationError(
                        f"Evidence lineage for '{item.spec.id}' references unknown "
                        "historical Work Units: " + ", ".join(unknown_sources)
                    )
                if not any(states.get(source) == "COMPLETED" for source in sources):
                    raise WorkGraphMigrationError(
                        f"Completed migrated Work Unit '{item.spec.id}' requires "
                        "lineage to at least one historically COMPLETED Work Unit."
                    )
            else:
                for evidence in item.evidence_lineage:
                    if evidence.source_work_unit_id not in existing_ids:
                        raise WorkGraphMigrationError(
                            f"Evidence lineage for '{item.spec.id}' references unknown "
                            f"historical Work Unit '{evidence.source_work_unit_id}'."
                        )

        existing_specs = tuple(
            _planned_work_unit_from_payload(item)
            for item in current_units_raw
            if isinstance(item, dict)
        )
        existing_deps = tuple(
            _planned_dependency(item)
            for item in current_deps_raw
            if isinstance(item, dict)
        )
        try:
            ProjectExecutionPlan(
                summary=str(plan_raw.get("summary") or "migrated-work-graph"),
                work_units=(
                    *existing_specs,
                    *(item.spec for item in spec.work_units),
                ),
                dependencies=(*existing_deps, *spec.dependencies),
            )
        except ProjectExecutionPlanError as exc:
            raise WorkGraphMigrationError(str(exc)) from exc

        migrated = deepcopy(dict(checkpoint))
        migrated_plan = deepcopy(plan_raw)
        migrated_plan["work_units"] = [
            *deepcopy(current_units_raw),
            *[_planned_work_unit_to_payload(item.spec) for item in spec.work_units],
        ]
        migrated_plan["dependencies"] = [
            *deepcopy(current_deps_raw),
            *[_planned_dependency_to_payload(item) for item in spec.dependencies],
        ]
        migrated["plan"] = migrated_plan

        state_map = dict(states)
        for item in spec.work_units:
            state_map[item.spec.id] = item.initial_state
        for target in resume_targets:
            state_map[target] = "REVISION_REQUIRED"
        migrated["work_unit_states"] = state_map

        attempts = _int_map(migrated, "attempts", existing_ids)
        strategies = _int_map(migrated, "strategy_generations", existing_ids)
        epochs = _int_map_optional(migrated, "recovery_epoch_counts", existing_ids, 0)
        recovery_replans = _int_map_optional(
            migrated, "recovery_replans_in_epoch", existing_ids, 0
        )
        for item in spec.work_units:
            attempts[item.spec.id] = 0
            strategies[item.spec.id] = 1
            epochs[item.spec.id] = 0
            recovery_replans[item.spec.id] = 0
        for target in resume_targets:
            attempts[target] = 0
            strategies[target] = 1
            recovery_replans[target] = 0
        migrated["attempts"] = attempts
        migrated["strategy_generations"] = strategies
        migrated["recovery_epoch_counts"] = epochs
        migrated["recovery_replans_in_epoch"] = recovery_replans

        recovery_guidance = migrated.get("recovery_guidance")
        if not isinstance(recovery_guidance, dict):
            recovery_guidance = {}
        recovery_guidance = dict(recovery_guidance)
        for target in resume_targets:
            recovery_guidance.pop(target, None)
        migrated["recovery_guidance"] = recovery_guidance

        revision_feedback = migrated.get("revision_feedback")
        if not isinstance(revision_feedback, dict):
            revision_feedback = {}
        revision_feedback = dict(revision_feedback)
        for target in resume_targets:
            revision_feedback[target] = (
                f"Work Graph migration '{spec.migration_id}' materialized explicit "
                "prerequisite Work Units. Preserve historical WIP/evidence and retry "
                "only after those prerequisites are accepted."
            )
        migrated["revision_feedback"] = revision_feedback

        dependency_states = migrated.get("dependency_states")
        if not isinstance(dependency_states, list):
            raise WorkGraphMigrationError("Checkpoint dependency_states is malformed.")
        existing_dep_state_keys = {
            (
                str(item.get("source_id")),
                str(item.get("target_id")),
                bool(item.get("required", True)),
            )
            for item in dependency_states
            if isinstance(item, dict)
        }
        if existing_dep_state_keys != old_edges:
            raise WorkGraphMigrationError(
                "Checkpoint dependency state identities do not match the persisted plan."
            )
        new_dependency_states = deepcopy(dependency_states)
        for dependency in spec.dependencies:
            source_completed = state_map.get(dependency.source_id) == "COMPLETED"
            new_dependency_states.append(
                {
                    "source_id": dependency.source_id,
                    "target_id": dependency.target_id,
                    "required": dependency.required,
                    "status": "SATISFIED" if source_completed else "BLOCKED",
                }
            )
        migrated["dependency_states"] = new_dependency_states

        records = migrated.get("records")
        if not isinstance(records, list):
            raise WorkGraphMigrationError("Checkpoint records is malformed.")
        records = deepcopy(records)
        dispatch_generation = migrated.get("dispatch_generation", 0)
        if isinstance(dispatch_generation, bool) or not isinstance(dispatch_generation, int):
            dispatch_generation = 0
        for item in spec.work_units:
            if item.initial_state != "COMPLETED":
                continue
            refs = [
                evidence.result_ref
                for evidence in item.evidence_lineage
                if evidence.result_ref
            ]
            records.append(
                {
                    "work_unit_id": item.spec.id,
                    "role": item.spec.role,
                    "wave": dispatch_generation,
                    "attempt": 0,
                    "status": "COMPLETED",
                    "skills": list(item.spec.requested_skills),
                    "execution_id": None,
                    "external_id": None,
                    "runtime_status": None,
                    "verdict": "ACCEPTED",
                    "output": (
                        "Accepted by governed Work Graph migration from explicit "
                        "historical evidence lineage."
                    ),
                    "result_ref": refs[0] if refs else None,
                    "result_authoritative": bool(refs),
                    "reason": f"graph-migration:{spec.migration_id}:evidence-lineage",
                    "strategy": 1,
                }
            )
        migrated["records"] = records

        lineage_map = migrated.get("work_unit_evidence_lineage")
        if not isinstance(lineage_map, dict):
            lineage_map = {}
        lineage_map = deepcopy(lineage_map)
        for item in spec.work_units:
            if not item.evidence_lineage:
                continue
            lineage_map[item.spec.id] = [
                {
                    "source_work_unit_id": evidence.source_work_unit_id,
                    "result_ref": evidence.result_ref,
                    "note": evidence.note,
                    "migration_id": spec.migration_id,
                }
                for evidence in item.evidence_lineage
            ]
        migrated["work_unit_evidence_lineage"] = lineage_map

        if spec.consume_pending_replan:
            migrated["pending_replan"] = False
            migrated["replan_feedback"] = (
                f"Consumed by governed Work Graph migration '{spec.migration_id}'."
            )

        if include_migration_record:
            # Reserved for callers that need to attach a record during simulation.
            migrated.setdefault("graph_migrations", [])

        return migrated

    @staticmethod
    def _states(checkpoint: Mapping[str, Any]) -> dict[str, str]:
        raw = checkpoint.get("work_unit_states")
        if not isinstance(raw, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in raw.items()
        ):
            raise WorkGraphMigrationError("Checkpoint work_unit_states is malformed.")
        return dict(raw)

    @staticmethod
    def _existing_migration(
        checkpoint: Mapping[str, Any],
        migration_id: str,
    ) -> dict[str, Any] | None:
        history = checkpoint.get("graph_migrations")
        if history is None:
            return None
        if not isinstance(history, list):
            raise WorkGraphMigrationError("Checkpoint graph_migrations is malformed.")
        matches = [
            item
            for item in history
            if isinstance(item, dict) and item.get("migration_id") == migration_id
        ]
        if len(matches) > 1:
            raise WorkGraphMigrationError(
                f"Checkpoint contains duplicate migration id '{migration_id}'."
            )
        return matches[0] if matches else None

    @staticmethod
    def _apply_blockers(checkpoint: Mapping[str, Any]) -> tuple[str, ...]:
        blockers: list[str] = []
        if checkpoint.get("terminal") is True:
            blockers.append("terminal=true")
        if checkpoint.get("desired_state") != "PAUSED":
            blockers.append("desired_state must be PAUSED")
        active = checkpoint.get("active_executions")
        if not isinstance(active, list):
            blockers.append("active_executions is malformed")
        elif active:
            blockers.append("active_executions must be empty")
        return tuple(blockers)

    @staticmethod
    def _receipt_from_existing(
        *,
        orchestration_id: str,
        checkpoint: Mapping[str, Any],
        spec: WorkGraphMigrationSpec,
        artifact_ref: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": "work-graph-migration-receipt/1",
            "migration_id": spec.migration_id,
            "orchestration_id": orchestration_id,
            "reason": spec.reason,
            "spec_digest": spec.digest,
            "artifact_ref": artifact_ref,
            "already_applied": True,
            "after": graph_snapshot(checkpoint),
        }


def _migration_work_unit(raw: object) -> MigrationWorkUnit:
    if not isinstance(raw, dict):
        raise WorkGraphMigrationError("Each migration Work Unit must be an object.")
    try:
        kind = WorkUnitKind(str(raw["kind"]).upper())
    except (KeyError, ValueError) as exc:
        raise WorkGraphMigrationError("Migration Work Unit kind is invalid.") from exc
    evidence_raw = raw.get("evidence_lineage")
    if not isinstance(evidence_raw, list):
        raise WorkGraphMigrationError("evidence_lineage must be a list.")
    evidence = tuple(
        EvidenceLineage(
            source_work_unit_id=str(item["source_work_unit_id"]).strip(),
            result_ref=(
                str(item["result_ref"]).strip()
                if item.get("result_ref") is not None
                else None
            ),
            note=str(item.get("note") or ""),
        )
        for item in evidence_raw
        if isinstance(item, dict)
    )
    if len(evidence) != len(evidence_raw):
        raise WorkGraphMigrationError("evidence_lineage contains an invalid item.")

    spec = PlannedWorkUnit(
        id=str(raw["id"]).strip(),
        objective=str(raw["objective"]).strip(),
        role=str(raw["role"]).strip(),
        scope=str(raw.get("scope") or ""),
        kind=kind,
        required_capabilities=_string_tuple(raw, "required_capabilities"),
        requested_skills=_string_tuple(raw, "requested_skills"),
        tools=_string_tuple(raw, "tools"),
        inputs=_string_tuple(raw, "inputs"),
        expected_output=_string_tuple(raw, "expected_output"),
        acceptance_criteria=_string_tuple(raw, "acceptance_criteria"),
        requested_side_effects=_string_tuple(raw, "requested_side_effects"),
        write_paths=_string_tuple(raw, "write_paths"),
        priority=int(raw["priority"]),
        criticality=int(raw["criticality"]),
        parallel_safe=bool(raw["parallel_safe"]),
        reconciles_work_unit_id=(
            str(raw["reconciles_work_unit_id"]).strip()
            if raw.get("reconciles_work_unit_id") is not None
            else None
        ),
    )
    return MigrationWorkUnit(
        spec=spec,
        initial_state=str(raw["initial_state"]),
        evidence_lineage=evidence,
    )


def _planned_work_unit_from_payload(raw: Mapping[str, Any]) -> PlannedWorkUnit:
    try:
        kind = WorkUnitKind(str(raw.get("kind", "EXECUTION")).upper())
    except ValueError as exc:
        raise WorkGraphMigrationError("Historical plan contains invalid Work Unit kind.") from exc
    return PlannedWorkUnit(
        id=str(raw.get("id") or ""),
        objective=str(raw.get("objective") or ""),
        role=str(raw.get("role") or "worker"),
        scope=str(raw.get("scope") or ""),
        kind=kind,
        required_capabilities=_string_tuple(raw, "required_capabilities"),
        requested_skills=_string_tuple(raw, "requested_skills"),
        tools=_string_tuple(raw, "tools"),
        inputs=_string_tuple(raw, "inputs"),
        expected_output=_string_tuple(
            raw, "expected_output", default=("agent response",)
        ),
        acceptance_criteria=_string_tuple(
            raw, "acceptance_criteria", default=("runtime-completed",)
        ),
        requested_side_effects=_string_tuple(raw, "requested_side_effects"),
        write_paths=_string_tuple(raw, "write_paths"),
        priority=_nonnegative_int(raw.get("priority", 0), "priority"),
        criticality=_nonnegative_int(raw.get("criticality", 0), "criticality"),
        parallel_safe=bool(raw.get("parallel_safe", True)),
        reconciles_work_unit_id=(
            str(raw["reconciles_work_unit_id"]).strip()
            if raw.get("reconciles_work_unit_id") is not None
            else None
        ),
    )


def _planned_dependency(raw: Mapping[str, Any]) -> PlannedDependency:
    return PlannedDependency(
        source_id=str(raw.get("source_id") or "").strip(),
        target_id=str(raw.get("target_id") or "").strip(),
        required=bool(raw.get("required", True)),
        condition=(
            str(raw["condition"])
            if raw.get("condition") is not None
            else None
        ),
    )


def _planned_work_unit_to_payload(item: PlannedWorkUnit) -> dict[str, Any]:
    return {
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


def _planned_dependency_to_payload(item: PlannedDependency) -> dict[str, Any]:
    return {
        "source_id": item.source_id,
        "target_id": item.target_id,
        "required": item.required,
        "condition": item.condition,
    }


def _string_tuple(
    raw: Mapping[str, Any],
    key: str,
    *,
    default: tuple[str, ...] = (),
) -> tuple[str, ...]:
    value = raw.get(key)
    if value is None:
        return default
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise WorkGraphMigrationError(f"Field '{key}' must be a list.")
    result = tuple(str(item).strip() for item in value)
    if any(not item for item in result):
        raise WorkGraphMigrationError(f"Field '{key}' contains a blank value.")
    return result or default


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WorkGraphMigrationError(f"Field '{name}' must be a non-negative integer.")
    return value


def _int_map(
    checkpoint: Mapping[str, Any],
    key: str,
    expected_ids: set[str],
) -> dict[str, int]:
    raw = checkpoint.get(key)
    if not isinstance(raw, dict) or set(raw) != expected_ids:
        raise WorkGraphMigrationError(
            f"Checkpoint field '{key}' does not match historical Work Units."
        )
    result: dict[str, int] = {}
    for item_id, value in raw.items():
        result[str(item_id)] = _nonnegative_int(value, key)
    return result


def _int_map_optional(
    checkpoint: Mapping[str, Any],
    key: str,
    expected_ids: set[str],
    default: int,
) -> dict[str, int]:
    raw = checkpoint.get(key)
    if raw is None:
        return {item_id: default for item_id in expected_ids}
    return _int_map(checkpoint, key, expected_ids)
