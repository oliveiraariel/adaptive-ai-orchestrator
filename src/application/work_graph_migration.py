from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from application.continuous_project_orchestration import RunContinuousProjectOrchestration
from application.project_orchestration_checkpoint import ProjectOrchestrationCheckpointStore
from domain.work_unit import WorkUnitState
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


class WorkGraphMigrationError(RuntimeError):
    """Raised when a persisted Work Graph cannot be migrated safely."""


@dataclass(frozen=True)
class WorkGraphMigrationResult:
    orchestration_id: str
    migration_id: str
    mode: str
    checkpoint_fingerprint_before: str
    checkpoint_fingerprint_after: str | None
    added_work_unit_ids: tuple[str, ...]
    superseded_work_unit_ids: tuple[str, ...]
    total_work_unit_count: int
    max_work_units: int
    pending_replan_after: bool
    artifact_path: str | None = None
    idempotent: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "mode": self.mode,
            "orchestration_id": self.orchestration_id,
            "migration_id": self.migration_id,
            "checkpoint_fingerprint_before": self.checkpoint_fingerprint_before,
            "checkpoint_fingerprint_after": self.checkpoint_fingerprint_after,
            "added_work_unit_ids": list(self.added_work_unit_ids),
            "superseded_work_unit_ids": list(self.superseded_work_unit_ids),
            "total_work_unit_count": self.total_work_unit_count,
            "max_work_units": self.max_work_units,
            "pending_replan_after": self.pending_replan_after,
            "artifact_path": self.artifact_path,
            "idempotent": self.idempotent,
        }


class WorkGraphMigrationService:
    """Additively normalize a non-terminal persisted Work Graph.

    The migration is deliberately narrower than normal replanning:
    - existing Work Unit definitions, states, dependencies, records and results are
      never removed or rewritten;
    - new Work Units are appended with explicit initial states and evidence lineage;
    - new dependency edges may target only newly-created Work Units;
    - historical aggregate nodes may be excluded from future scheduling through
      separate checkpoint metadata rather than destructive state rewriting;
    - apply is allowed only while the project is durably PAUSED and has no active
      executions.

    The checkpoint remains the scheduling authority. An immutable audit artifact is
    written after the atomic checkpoint update and can be reconstructed idempotently
    from the migration record retained inside the checkpoint.
    """

    SCHEMA_VERSION = "work-graph-migration/1"
    HISTORY_FIELD = "work_graph_migrations"
    SUPERSEDED_FIELD = "superseded_work_unit_ids"

    def __init__(
        self,
        *,
        project_root: Path,
        checkpoint_store: ProjectOrchestrationCheckpointStore | None = None,
    ) -> None:
        root = project_root.expanduser().resolve()
        if not root.is_dir():
            raise WorkGraphMigrationError(
                f"Adaptive project root does not exist or is not a directory: {root}"
            )
        self.project_root = root
        self.checkpoints = checkpoint_store or FileProjectOrchestrationCheckpointStore(
            project_root=root
        )
        self.artifact_root = root / ".adaptive" / "work-graph-migrations"

    def preview(
        self,
        *,
        orchestration_id: str,
        migration: Mapping[str, Any],
    ) -> WorkGraphMigrationResult:
        checkpoint = self._load_checkpoint(orchestration_id)
        normalized = self._normalize_migration(
            orchestration_id=orchestration_id,
            migration=migration,
            require_expected_fingerprint=False,
        )
        existing = self._existing_migration(checkpoint, normalized["migration_id"])
        if existing is not None:
            return self._idempotent_result(
                checkpoint=checkpoint,
                normalized=normalized,
                existing=existing,
                mode="work-graph-migration-dry-run",
            )

        candidate, added_ids, superseded_ids = self._build_candidate(
            checkpoint=checkpoint,
            normalized=normalized,
        )
        before = self.checkpoint_fingerprint(checkpoint)
        after = self.checkpoint_fingerprint(candidate)
        request = self._require_object(checkpoint, "request")
        max_work_units = self._require_positive_int(request, "max_work_units")
        return WorkGraphMigrationResult(
            orchestration_id=orchestration_id,
            migration_id=normalized["migration_id"],
            mode="work-graph-migration-dry-run",
            checkpoint_fingerprint_before=before,
            checkpoint_fingerprint_after=after,
            added_work_unit_ids=tuple(added_ids),
            superseded_work_unit_ids=tuple(superseded_ids),
            total_work_unit_count=len(self._require_object(candidate, "work_unit_states")),
            max_work_units=max_work_units,
            pending_replan_after=bool(candidate.get("pending_replan", False)),
        )

    def apply(
        self,
        *,
        orchestration_id: str,
        migration: Mapping[str, Any],
    ) -> WorkGraphMigrationResult:
        checkpoint = self._load_checkpoint(orchestration_id)
        normalized = self._normalize_migration(
            orchestration_id=orchestration_id,
            migration=migration,
            require_expected_fingerprint=True,
        )
        existing = self._existing_migration(checkpoint, normalized["migration_id"])
        if existing is not None:
            result = self._idempotent_result(
                checkpoint=checkpoint,
                normalized=normalized,
                existing=existing,
                mode="work-graph-migration-apply",
            )
            self._ensure_artifact(existing)
            return result

        self._validate_apply_safety(checkpoint)

        before = self.checkpoint_fingerprint(checkpoint)
        expected = normalized["expected_checkpoint_fingerprint"]
        if expected != before:
            raise WorkGraphMigrationError(
                "Migration checkpoint fingerprint mismatch. Re-run dry-run against "
                "the current paused checkpoint before applying."
            )

        candidate, added_ids, superseded_ids = self._build_candidate(
            checkpoint=checkpoint,
            normalized=normalized,
        )
        after = self.checkpoint_fingerprint(candidate)
        applied_at = datetime.now(timezone.utc).isoformat()
        plan_digest = self._digest(normalized)
        artifact_rel = self._artifact_relative_path(
            orchestration_id=orchestration_id,
            migration_id=normalized["migration_id"],
        )
        record = {
            "schema_version": self.SCHEMA_VERSION,
            "migration_id": normalized["migration_id"],
            "orchestration_id": orchestration_id,
            "reason": normalized["reason"],
            "plan_digest": plan_digest,
            "checkpoint_fingerprint_before": before,
            "checkpoint_fingerprint_after": after,
            "added_work_unit_ids": list(added_ids),
            "superseded_work_unit_ids": list(superseded_ids),
            "pending_replan_before": bool(checkpoint.get("pending_replan", False)),
            "pending_replan_after": bool(candidate.get("pending_replan", False)),
            "artifact_path": artifact_rel,
            "applied_at": applied_at,
            "migration": normalized,
        }
        history = list(self._history(candidate))
        history.append(record)
        candidate[self.HISTORY_FIELD] = history

        # The checkpoint store already writes atomically via temporary + replace.
        self.checkpoints.save(orchestration_id, candidate)
        self._ensure_artifact(record)

        request = self._require_object(candidate, "request")
        max_work_units = self._require_positive_int(request, "max_work_units")
        return WorkGraphMigrationResult(
            orchestration_id=orchestration_id,
            migration_id=normalized["migration_id"],
            mode="work-graph-migration-apply",
            checkpoint_fingerprint_before=before,
            checkpoint_fingerprint_after=after,
            added_work_unit_ids=tuple(added_ids),
            superseded_work_unit_ids=tuple(superseded_ids),
            total_work_unit_count=len(self._require_object(candidate, "work_unit_states")),
            max_work_units=max_work_units,
            pending_replan_after=bool(candidate.get("pending_replan", False)),
            artifact_path=artifact_rel,
        )

    def _load_checkpoint(self, orchestration_id: str) -> dict[str, Any]:
        value = orchestration_id.strip()
        if not value:
            raise WorkGraphMigrationError("orchestration_id must not be empty.")
        checkpoint = self.checkpoints.load(value)
        if checkpoint is None:
            raise WorkGraphMigrationError(
                f"No project checkpoint exists for orchestration '{value}'."
            )
        if checkpoint.get("phase") != "EXECUTION":
            raise WorkGraphMigrationError(
                "Work Graph migration requires an EXECUTION-phase checkpoint."
            )
        if checkpoint.get("terminal") is True:
            raise WorkGraphMigrationError(
                "Work Graph migration is allowed only for non-terminal orchestrations."
            )
        return checkpoint

    def _normalize_migration(
        self,
        *,
        orchestration_id: str,
        migration: Mapping[str, Any],
        require_expected_fingerprint: bool,
    ) -> dict[str, Any]:
        if not isinstance(migration, Mapping):
            raise WorkGraphMigrationError("Migration document must be a JSON object.")
        allowed = {
            "schema_version",
            "migration_id",
            "orchestration_id",
            "reason",
            "expected_checkpoint_fingerprint",
            "new_work_units",
            "dependencies",
            "supersede_for_scheduling",
        }
        unknown = set(migration) - allowed
        if unknown:
            raise WorkGraphMigrationError(
                "Migration document contains unknown field(s): "
                + ", ".join(sorted(str(item) for item in unknown))
            )
        if migration.get("schema_version") != self.SCHEMA_VERSION:
            raise WorkGraphMigrationError(
                f"Migration schema_version must be '{self.SCHEMA_VERSION}'."
            )
        migration_id = self._require_nonempty_string(migration, "migration_id")
        declared_orchestration = self._require_nonempty_string(
            migration, "orchestration_id"
        )
        if declared_orchestration != orchestration_id:
            raise WorkGraphMigrationError(
                "Migration orchestration_id does not match the selected checkpoint."
            )
        reason = self._require_nonempty_string(migration, "reason")
        expected = migration.get("expected_checkpoint_fingerprint")
        if expected is not None and (
            not isinstance(expected, str) or len(expected) != 64
        ):
            raise WorkGraphMigrationError(
                "expected_checkpoint_fingerprint must be a 64-character SHA-256 hex string."
            )
        if require_expected_fingerprint and not expected:
            raise WorkGraphMigrationError(
                "Apply requires expected_checkpoint_fingerprint from a prior dry-run."
            )

        raw_units = migration.get("new_work_units")
        if not isinstance(raw_units, list) or not raw_units:
            raise WorkGraphMigrationError(
                "Migration must add at least one new Work Unit."
            )
        normalized_units = [
            self._normalize_new_work_unit(item) for item in raw_units
        ]
        ids = [item["spec"]["id"] for item in normalized_units]
        if len(ids) != len(set(ids)):
            raise WorkGraphMigrationError(
                "Migration new Work Unit ids must be unique."
            )

        raw_dependencies = migration.get("dependencies", [])
        if not isinstance(raw_dependencies, list):
            raise WorkGraphMigrationError("Migration dependencies must be an array.")
        dependencies = [
            self._normalize_dependency(item) for item in raw_dependencies
        ]

        raw_superseded = migration.get("supersede_for_scheduling", [])
        if not isinstance(raw_superseded, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in raw_superseded
        ):
            raise WorkGraphMigrationError(
                "supersede_for_scheduling must be an array of non-empty Work Unit ids."
            )
        superseded = list(dict.fromkeys(item.strip() for item in raw_superseded))

        return {
            "schema_version": self.SCHEMA_VERSION,
            "migration_id": migration_id,
            "orchestration_id": orchestration_id,
            "reason": reason,
            "expected_checkpoint_fingerprint": expected,
            "new_work_units": normalized_units,
            "dependencies": dependencies,
            "supersede_for_scheduling": superseded,
        }

    def _normalize_new_work_unit(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise WorkGraphMigrationError(
                "Each new_work_units entry must be an object."
            )
        allowed = {"spec", "initial_state", "lineage"}
        unknown = set(raw) - allowed
        if unknown:
            raise WorkGraphMigrationError(
                "New Work Unit entry contains unknown field(s): "
                + ", ".join(sorted(str(item) for item in unknown))
            )
        spec = raw.get("spec")
        if not isinstance(spec, Mapping):
            raise WorkGraphMigrationError("New Work Unit spec must be an object.")
        # Reuse the authoritative checkpoint plan parser for exact PlannedWorkUnit
        # validation by embedding this spec in a minimal temporary plan.
        try:
            parsed = RunContinuousProjectOrchestration._plan_from_payload(
                {
                    "summary": "migration validation",
                    "work_units": [dict(spec)],
                    "dependencies": [],
                }
            )
        except Exception as exc:
            raise WorkGraphMigrationError(
                f"New Work Unit spec is invalid: {exc}"
            ) from exc
        canonical_spec = RunContinuousProjectOrchestration._plan_to_payload(parsed)[
            "work_units"
        ][0]

        initial_state = self._require_nonempty_string(raw, "initial_state")
        if initial_state not in {
            WorkUnitState.PLANNED.value,
            WorkUnitState.COMPLETED.value,
        }:
            raise WorkGraphMigrationError(
                "Migrated Work Units may start only as PLANNED or COMPLETED."
            )

        lineage = raw.get("lineage")
        if not isinstance(lineage, Mapping):
            raise WorkGraphMigrationError(
                "Each migrated Work Unit must declare lineage."
            )
        lineage_allowed = {
            "historical_source_ids",
            "evidence_refs",
            "evidence_summary",
        }
        lineage_unknown = set(lineage) - lineage_allowed
        if lineage_unknown:
            raise WorkGraphMigrationError(
                "Lineage contains unknown field(s): "
                + ", ".join(sorted(str(item) for item in lineage_unknown))
            )
        historical = self._require_string_array(lineage, "historical_source_ids")
        evidence = self._require_string_array(lineage, "evidence_refs")
        summary = self._require_nonempty_string(lineage, "evidence_summary")
        if initial_state == WorkUnitState.COMPLETED.value and (
            not historical or not evidence
        ):
            raise WorkGraphMigrationError(
                f"Completed migrated Work Unit '{canonical_spec['id']}' requires "
                "historical_source_ids and evidence_refs."
            )
        return {
            "spec": canonical_spec,
            "initial_state": initial_state,
            "lineage": {
                "historical_source_ids": historical,
                "evidence_refs": evidence,
                "evidence_summary": summary,
            },
        }

    @staticmethod
    def _normalize_dependency(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise WorkGraphMigrationError(
                "Each migration dependency must be an object."
            )
        allowed = {"source_id", "target_id", "required", "condition"}
        unknown = set(raw) - allowed
        if unknown:
            raise WorkGraphMigrationError(
                "Migration dependency contains unknown field(s): "
                + ", ".join(sorted(str(item) for item in unknown))
            )
        source = raw.get("source_id")
        target = raw.get("target_id")
        required = raw.get("required")
        condition = raw.get("condition")
        if not isinstance(source, str) or not source.strip():
            raise WorkGraphMigrationError("Dependency source_id must not be blank.")
        if not isinstance(target, str) or not target.strip():
            raise WorkGraphMigrationError("Dependency target_id must not be blank.")
        if source == target:
            raise WorkGraphMigrationError("Dependency cannot target itself.")
        if not isinstance(required, bool):
            raise WorkGraphMigrationError("Dependency required must be boolean.")
        if condition is not None and not isinstance(condition, str):
            raise WorkGraphMigrationError(
                "Dependency condition must be a string or null."
            )
        return {
            "source_id": source.strip(),
            "target_id": target.strip(),
            "required": required,
            "condition": condition,
        }

    def _build_candidate(
        self,
        *,
        checkpoint: dict[str, Any],
        normalized: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        candidate = deepcopy(checkpoint)
        plan_raw = self._require_object(candidate, "plan")
        plan = RunContinuousProjectOrchestration._plan_from_payload(plan_raw)
        canonical_plan = RunContinuousProjectOrchestration._plan_to_payload(plan)
        existing_ids = {item["id"] for item in canonical_plan["work_units"]}
        states = self._require_object(candidate, "work_unit_states")
        if set(states) != existing_ids:
            raise WorkGraphMigrationError(
                "Checkpoint Work Unit states do not match the persisted plan."
            )

        new_units = normalized["new_work_units"]
        new_ids = [item["spec"]["id"] for item in new_units]
        collisions = sorted(existing_ids.intersection(new_ids))
        if collisions:
            raise WorkGraphMigrationError(
                "Migration attempts to redefine existing Work Unit(s): "
                + ", ".join(collisions)
            )

        request = self._require_object(candidate, "request")
        max_work_units = self._require_positive_int(request, "max_work_units")
        if len(existing_ids) + len(new_ids) > max_work_units:
            raise WorkGraphMigrationError(
                "Migration would exceed max_work_units: "
                f"{len(existing_ids)} existing + {len(new_ids)} new > {max_work_units}."
            )

        superseded_existing = set(self._superseded(candidate))
        requested_superseded = normalized["supersede_for_scheduling"]
        unknown_superseded = sorted(set(requested_superseded) - existing_ids)
        if unknown_superseded:
            raise WorkGraphMigrationError(
                "Cannot supersede unknown historical Work Unit(s): "
                + ", ".join(unknown_superseded)
            )
        active = candidate.get("active_executions")
        active_ids = {
            str(item.get("work_unit_id"))
            for item in active
            if isinstance(active, list) and isinstance(item, dict)
        } if isinstance(active, list) else set()
        unsafe_superseded = sorted(set(requested_superseded).intersection(active_ids))
        if unsafe_superseded:
            raise WorkGraphMigrationError(
                "Cannot supersede Work Unit(s) with active executions: "
                + ", ".join(unsafe_superseded)
            )

        for item in new_units:
            lineage = item["lineage"]
            unknown_lineage = sorted(
                set(lineage["historical_source_ids"]) - existing_ids
            )
            if unknown_lineage:
                raise WorkGraphMigrationError(
                    f"Migrated Work Unit '{item['spec']['id']}' references unknown "
                    "historical source(s): " + ", ".join(unknown_lineage)
                )

        known_after = existing_ids | set(new_ids)
        for edge in normalized["dependencies"]:
            if edge["source_id"] not in known_after:
                raise WorkGraphMigrationError(
                    f"Migration dependency references unknown source '{edge['source_id']}'."
                )
            if edge["target_id"] not in set(new_ids):
                raise WorkGraphMigrationError(
                    "Migration dependencies may target only newly-created Work Units; "
                    f"'{edge['target_id']}' is historical."
                )
            if edge["source_id"] in set(requested_superseded) | superseded_existing:
                raise WorkGraphMigrationError(
                    "A newly-created Work Unit cannot depend on a superseded historical "
                    f"source '{edge['source_id']}'."
                )

        canonical_plan["work_units"].extend(
            deepcopy(item["spec"]) for item in new_units
        )
        existing_edges = {
            (item["source_id"], item["target_id"], bool(item["required"]))
            for item in canonical_plan["dependencies"]
        }
        for edge in normalized["dependencies"]:
            key = (edge["source_id"], edge["target_id"], edge["required"])
            if key in existing_edges:
                raise WorkGraphMigrationError(
                    "Migration dependency duplicates an existing edge: "
                    f"{edge['source_id']}->{edge['target_id']}."
                )
            canonical_plan["dependencies"].append(deepcopy(edge))
            existing_edges.add(key)

        # Validate the full merged graph with the same domain contract used by
        # ordinary project execution.
        merged_plan = RunContinuousProjectOrchestration._plan_from_payload(
            canonical_plan
        )
        candidate["plan"] = RunContinuousProjectOrchestration._plan_to_payload(
            merged_plan
        )

        initial_states = {
            item["spec"]["id"]: item["initial_state"] for item in new_units
        }
        states.update(initial_states)

        self._extend_int_map(candidate, "attempts", new_ids, 0)
        self._extend_int_map(candidate, "strategy_generations", new_ids, 1)
        self._extend_int_map(candidate, "recovery_epoch_counts", new_ids, 0)
        self._extend_int_map(candidate, "recovery_replans_in_epoch", new_ids, 0)

        for name in ("outputs", "output_refs", "revision_feedback"):
            mapping = candidate.get(name)
            if mapping is None:
                candidate[name] = {}
            elif not isinstance(mapping, dict):
                raise WorkGraphMigrationError(
                    f"Checkpoint field '{name}' must be an object."
                )

        dep_states = candidate.get("dependency_states")
        if not isinstance(dep_states, list):
            raise WorkGraphMigrationError(
                "Checkpoint dependency_states must be an array."
            )
        for edge in normalized["dependencies"]:
            source_state = states.get(edge["source_id"])
            status = (
                "SATISFIED"
                if source_state == WorkUnitState.COMPLETED.value
                else "BLOCKED"
            )
            dep_states.append(
                {
                    "source_id": edge["source_id"],
                    "target_id": edge["target_id"],
                    "required": edge["required"],
                    "status": status,
                }
            )

        # A migrated unit may be declared COMPLETED only if all of its required
        # prerequisites are already satisfied in the candidate checkpoint.
        status_by_edge = {
            (
                item.get("source_id"),
                item.get("target_id"),
                bool(item.get("required", True)),
            ): item.get("status")
            for item in dep_states
            if isinstance(item, dict)
        }
        for work_unit_id, initial_state in initial_states.items():
            if initial_state != WorkUnitState.COMPLETED.value:
                continue
            blocking = [
                edge
                for edge in candidate["plan"]["dependencies"]
                if edge["target_id"] == work_unit_id
                and edge["required"]
                and status_by_edge.get(
                    (edge["source_id"], edge["target_id"], True)
                ) != "SATISFIED"
            ]
            if blocking:
                raise WorkGraphMigrationError(
                    f"Completed migrated Work Unit '{work_unit_id}' has unsatisfied "
                    "required prerequisites."
                )

        merged_superseded = list(
            dict.fromkeys(
                [
                    *self._superseded(candidate),
                    *requested_superseded,
                ]
            )
        )
        candidate[self.SUPERSEDED_FIELD] = merged_superseded

        # Stale replanning pressure may be cleared only when every currently
        # RECOVERY_REQUIRED historical node is explicitly superseded.
        recovery_ids = {
            work_unit_id
            for work_unit_id, state in checkpoint["work_unit_states"].items()
            if state == WorkUnitState.RECOVERY_REQUIRED.value
        }
        if recovery_ids and recovery_ids.issubset(set(merged_superseded)):
            candidate["pending_replan"] = False

        return candidate, new_ids, merged_superseded

    @staticmethod
    def _validate_apply_safety(checkpoint: Mapping[str, Any]) -> None:
        if checkpoint.get("desired_state") != "PAUSED":
            raise WorkGraphMigrationError(
                "Apply requires desired_state=PAUSED. Use pause-project and wait "
                "for active executions to settle before migration."
            )
        active = checkpoint.get("active_executions")
        if not isinstance(active, list):
            raise WorkGraphMigrationError(
                "Checkpoint active_executions must be an array."
            )
        if active:
            raise WorkGraphMigrationError(
                "Apply requires zero active executions."
            )

    def _existing_migration(
        self,
        checkpoint: Mapping[str, Any],
        migration_id: str,
    ) -> dict[str, Any] | None:
        matches = [
            item
            for item in self._history(checkpoint)
            if item.get("migration_id") == migration_id
        ]
        if len(matches) > 1:
            raise WorkGraphMigrationError(
                f"Checkpoint contains duplicate migration id '{migration_id}'."
            )
        return matches[0] if matches else None

    def _idempotent_result(
        self,
        *,
        checkpoint: dict[str, Any],
        normalized: dict[str, Any],
        existing: dict[str, Any],
        mode: str,
    ) -> WorkGraphMigrationResult:
        if existing.get("plan_digest") != self._digest(normalized):
            raise WorkGraphMigrationError(
                f"Migration id '{normalized['migration_id']}' already exists with "
                "different content."
            )
        request = self._require_object(checkpoint, "request")
        max_work_units = self._require_positive_int(request, "max_work_units")
        return WorkGraphMigrationResult(
            orchestration_id=normalized["orchestration_id"],
            migration_id=normalized["migration_id"],
            mode=mode,
            checkpoint_fingerprint_before=str(
                existing.get("checkpoint_fingerprint_before") or ""
            ),
            checkpoint_fingerprint_after=str(
                existing.get("checkpoint_fingerprint_after") or ""
            ),
            added_work_unit_ids=tuple(existing.get("added_work_unit_ids") or ()),
            superseded_work_unit_ids=tuple(
                existing.get("superseded_work_unit_ids") or ()
            ),
            total_work_unit_count=len(
                self._require_object(checkpoint, "work_unit_states")
            ),
            max_work_units=max_work_units,
            pending_replan_after=bool(
                existing.get("pending_replan_after", checkpoint.get("pending_replan", False))
            ),
            artifact_path=str(existing.get("artifact_path") or "") or None,
            idempotent=True,
        )

    @classmethod
    def checkpoint_fingerprint(cls, checkpoint: Mapping[str, Any]) -> str:
        material = {
            "plan": checkpoint.get("plan"),
            "work_unit_states": checkpoint.get("work_unit_states"),
            "dependency_states": checkpoint.get("dependency_states"),
            "pending_replan": bool(checkpoint.get("pending_replan", False)),
            "terminal": bool(checkpoint.get("terminal", False)),
            "desired_state": str(checkpoint.get("desired_state") or ""),
            "active_executions": checkpoint.get("active_executions"),
            cls.SUPERSEDED_FIELD: checkpoint.get(cls.SUPERSEDED_FIELD, []),
        }
        return cls._digest(material)

    @staticmethod
    def _digest(value: Any) -> str:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _artifact_relative_path(
        self,
        *,
        orchestration_id: str,
        migration_id: str,
    ) -> str:
        orchestration_hash = hashlib.sha256(
            orchestration_id.encode("utf-8")
        ).hexdigest()
        migration_hash = hashlib.sha256(migration_id.encode("utf-8")).hexdigest()
        path = (
            Path(".adaptive")
            / "work-graph-migrations"
            / orchestration_hash
            / f"{migration_hash}.json"
        )
        return path.as_posix()

    def _ensure_artifact(self, record: Mapping[str, Any]) -> None:
        artifact_rel = record.get("artifact_path")
        if not isinstance(artifact_rel, str) or not artifact_rel:
            raise WorkGraphMigrationError(
                "Migration record is missing artifact_path."
            )
        path = self.project_root / artifact_rel
        body = (
            json.dumps(
                dict(record),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise WorkGraphMigrationError(
                    "Existing migration artifact is unreadable."
                ) from exc
            if existing != body:
                raise WorkGraphMigrationError(
                    "Immutable migration artifact exists with different content."
                )
            return
        except OSError as exc:
            raise WorkGraphMigrationError(
                "Unable to create immutable migration artifact."
            ) from exc
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            raise WorkGraphMigrationError(
                "Unable to persist immutable migration artifact."
            ) from exc

    @classmethod
    def _history(cls, checkpoint: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
        raw = checkpoint.get(cls.HISTORY_FIELD, [])
        if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
            raise WorkGraphMigrationError(
                f"Checkpoint field '{cls.HISTORY_FIELD}' must be an array of objects."
            )
        return tuple(raw)

    @classmethod
    def _superseded(cls, checkpoint: Mapping[str, Any]) -> tuple[str, ...]:
        raw = checkpoint.get(cls.SUPERSEDED_FIELD, [])
        if not isinstance(raw, list) or any(
            not isinstance(item, str) or not item.strip() for item in raw
        ):
            raise WorkGraphMigrationError(
                f"Checkpoint field '{cls.SUPERSEDED_FIELD}' must be an array of ids."
            )
        return tuple(dict.fromkeys(item.strip() for item in raw))

    @staticmethod
    def _extend_int_map(
        checkpoint: dict[str, Any],
        name: str,
        ids: Sequence[str],
        default: int,
    ) -> None:
        mapping = checkpoint.get(name)
        if mapping is None:
            mapping = {}
            checkpoint[name] = mapping
        if not isinstance(mapping, dict):
            raise WorkGraphMigrationError(
                f"Checkpoint field '{name}' must be an object."
            )
        for work_unit_id in ids:
            mapping[work_unit_id] = default

    @staticmethod
    def _require_object(payload: Mapping[str, Any], name: str) -> dict[str, Any]:
        value = payload.get(name)
        if not isinstance(value, dict):
            raise WorkGraphMigrationError(
                f"Field '{name}' must be a JSON object."
            )
        return value

    @staticmethod
    def _require_nonempty_string(payload: Mapping[str, Any], name: str) -> str:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise WorkGraphMigrationError(
                f"Field '{name}' must be a non-empty string."
            )
        return value.strip()

    @staticmethod
    def _require_string_array(payload: Mapping[str, Any], name: str) -> list[str]:
        value = payload.get(name)
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise WorkGraphMigrationError(
                f"Field '{name}' must be an array of non-empty strings."
            )
        return [item.strip() for item in value]

    @staticmethod
    def _require_positive_int(payload: Mapping[str, Any], name: str) -> int:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise WorkGraphMigrationError(
                f"Field '{name}' must be a positive integer."
            )
        return value
