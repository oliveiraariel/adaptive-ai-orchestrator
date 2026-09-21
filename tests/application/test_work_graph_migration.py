from __future__ import annotations

import json

import pytest

from application.work_graph_migration import (
    WorkGraphMigrationError,
    WorkGraphMigrationService,
    checkpoint_digest,
    parse_work_graph_migration,
)


def _planned_work_unit(work_unit_id: str) -> dict:
    return {
        "id": work_unit_id,
        "objective": f"Objective for {work_unit_id}",
        "role": "worker",
        "scope": "",
        "kind": "EXECUTION",
        "required_capabilities": [],
        "requested_skills": [],
        "tools": [],
        "inputs": [],
        "expected_output": ["agent response"],
        "acceptance_criteria": ["runtime-completed"],
        "requested_side_effects": [],
        "write_paths": [],
        "priority": 0,
        "criticality": 0,
        "parallel_safe": True,
        "reconciles_work_unit_id": None,
    }


def _checkpoint(*, desired_state: str = "PAUSED") -> dict:
    return {
        "orchestration_id": "orch-1",
        "phase": "EXECUTION",
        "desired_state": desired_state,
        "terminal": False,
        "request": {
            "objective": "test",
            "max_work_units": 8,
        },
        "plan": {
            "summary": "historical graph",
            "work_units": [
                _planned_work_unit("HIST"),
                _planned_work_unit("AGENDA"),
                _planned_work_unit("VERIFY"),
            ],
            "dependencies": [
                {
                    "source_id": "AGENDA",
                    "target_id": "VERIFY",
                    "required": True,
                    "condition": None,
                }
            ],
        },
        "work_unit_states": {
            "HIST": "COMPLETED",
            "AGENDA": "RECOVERY_REQUIRED",
            "VERIFY": "PLANNED",
        },
        "dependency_states": [
            {
                "source_id": "AGENDA",
                "target_id": "VERIFY",
                "required": True,
                "status": "BLOCKED",
            }
        ],
        "attempts": {"HIST": 1, "AGENDA": 2, "VERIFY": 0},
        "strategy_generations": {"HIST": 1, "AGENDA": 2, "VERIFY": 1},
        "outputs": {"HIST": "historical evidence"},
        "output_refs": {"HIST": ".adaptive/runs/hist/result.txt"},
        "revision_feedback": {},
        "records": [],
        "dispatch_records": [],
        "max_parallelism_observed": 1,
        "replan_count": 7,
        "dispatch_generation": 3,
        "pending_replan": True,
        "replan_feedback": "historical recovery pending",
        "recovery_epoch_counts": {"HIST": 0, "AGENDA": 1, "VERIFY": 0},
        "recovery_replans_in_epoch": {"HIST": 0, "AGENDA": 2, "VERIFY": 0},
        "recovery_guidance": {"AGENDA": "old guidance"},
        "active_executions": [],
    }


def _migration_payload() -> dict:
    completed = _planned_work_unit("WU-ACCEPTED")
    completed.update(
        {
            "initial_state": "COMPLETED",
            "evidence_lineage": [
                {
                    "source_work_unit_id": "HIST",
                    "result_ref": ".adaptive/runs/hist/result.txt",
                    "note": "historical result proves this acceptance surface",
                }
            ],
        }
    )
    pending = _planned_work_unit("WU-PENDING")
    pending.update(
        {
            "initial_state": "PLANNED",
            "evidence_lineage": [],
        }
    )
    return {
        "schema_version": "work-graph-migration/1",
        "migration_id": "normalize-v1",
        "reason": "restore explicit Work Unit granularity",
        "work_units": [completed, pending],
        "dependencies": [
            {
                "source_id": "WU-ACCEPTED",
                "target_id": "WU-PENDING",
                "required": True,
                "condition": None,
            },
            {
                "source_id": "WU-PENDING",
                "target_id": "AGENDA",
                "required": True,
                "condition": None,
            },
        ],
        "resume_recovery_targets": ["AGENDA"],
        "consume_pending_replan": True,
    }


def _spec(payload: dict | None = None):
    return parse_work_graph_migration(
        json.dumps(payload or _migration_payload()),
        max_new_work_units=8,
    )


def test_preview_is_additive_and_reports_quiescent_apply_readiness() -> None:
    checkpoint = _checkpoint()
    preview = WorkGraphMigrationService().preview(
        orchestration_id="orch-1",
        checkpoint=checkpoint,
        spec=_spec(),
    )

    assert preview.before_work_unit_count == 3
    assert preview.after_work_unit_count == 5
    assert preview.new_work_unit_ids == ("WU-ACCEPTED", "WU-PENDING")
    assert preview.initially_completed_work_unit_ids == ("WU-ACCEPTED",)
    assert preview.resumed_recovery_targets == ("AGENDA",)
    assert preview.added_dependency_count == 2
    assert preview.apply_ready is True
    assert preview.already_applied is False
    assert preview.before_graph_digest != preview.after_graph_digest


def test_apply_preserves_historical_nodes_and_materializes_evidence_backed_units() -> None:
    checkpoint = _checkpoint()
    spec = _spec()
    service = WorkGraphMigrationService()

    migrated, receipt, already_applied = service.apply(
        orchestration_id="orch-1",
        checkpoint=checkpoint,
        spec=spec,
        expected_checkpoint_digest=checkpoint_digest(checkpoint),
        artifact_ref=".adaptive/graph-migrations/test.json",
        applied_at="2026-09-21T12:00:00+00:00",
    )

    assert already_applied is False
    assert [item["id"] for item in migrated["plan"]["work_units"][:3]] == [
        "HIST",
        "AGENDA",
        "VERIFY",
    ]
    assert migrated["plan"]["dependencies"][0] == checkpoint["plan"]["dependencies"][0]
    assert migrated["work_unit_states"]["HIST"] == "COMPLETED"
    assert migrated["work_unit_states"]["AGENDA"] == "REVISION_REQUIRED"
    assert migrated["work_unit_states"]["WU-ACCEPTED"] == "COMPLETED"
    assert migrated["work_unit_states"]["WU-PENDING"] == "PLANNED"
    assert migrated["pending_replan"] is False
    assert migrated["attempts"]["WU-PENDING"] == 0
    assert migrated["strategy_generations"]["WU-PENDING"] == 1
    assert "AGENDA" not in migrated["recovery_guidance"]

    dependency_states = {
        (item["source_id"], item["target_id"]): item["status"]
        for item in migrated["dependency_states"]
    }
    assert dependency_states[("WU-ACCEPTED", "WU-PENDING")] == "SATISFIED"
    assert dependency_states[("WU-PENDING", "AGENDA")] == "BLOCKED"

    accepted_records = [
        item
        for item in migrated["records"]
        if item["work_unit_id"] == "WU-ACCEPTED"
    ]
    assert accepted_records[-1]["verdict"] == "ACCEPTED"
    assert accepted_records[-1]["execution_id"] is None
    assert accepted_records[-1]["reason"].startswith("graph-migration:")

    assert migrated["work_unit_evidence_lineage"]["WU-ACCEPTED"][0][
        "source_work_unit_id"
    ] == "HIST"
    assert migrated["graph_migrations"][0]["migration_id"] == "normalize-v1"
    assert receipt["before"]["work_unit_states"]["AGENDA"] == "RECOVERY_REQUIRED"
    assert receipt["after"]["work_unit_states"]["AGENDA"] == "REVISION_REQUIRED"


def test_apply_is_idempotent_for_same_migration_id_and_digest() -> None:
    checkpoint = _checkpoint()
    spec = _spec()
    service = WorkGraphMigrationService()

    migrated, first_receipt, _ = service.apply(
        orchestration_id="orch-1",
        checkpoint=checkpoint,
        spec=spec,
        expected_checkpoint_digest=checkpoint_digest(checkpoint),
        artifact_ref=".adaptive/graph-migrations/test.json",
        applied_at="2026-09-21T12:00:00+00:00",
    )
    repeated, second_receipt, already_applied = service.apply(
        orchestration_id="orch-1",
        checkpoint=migrated,
        spec=spec,
        expected_checkpoint_digest="ignored-on-idempotent-reapply",
        artifact_ref=".adaptive/graph-migrations/test.json",
    )

    assert already_applied is True
    assert repeated == migrated
    assert second_receipt == first_receipt
    assert len(repeated["graph_migrations"]) == 1


def test_same_migration_id_with_different_spec_fails_closed() -> None:
    checkpoint = _checkpoint()
    service = WorkGraphMigrationService()
    spec = _spec()
    migrated, _, _ = service.apply(
        orchestration_id="orch-1",
        checkpoint=checkpoint,
        spec=spec,
        expected_checkpoint_digest=checkpoint_digest(checkpoint),
        artifact_ref=".adaptive/graph-migrations/test.json",
    )

    changed = _migration_payload()
    changed["reason"] = "different migration"
    with pytest.raises(WorkGraphMigrationError, match="different spec digest"):
        service.preview(
            orchestration_id="orch-1",
            checkpoint=migrated,
            spec=_spec(changed),
        )


def test_completed_new_work_unit_requires_historical_evidence_lineage() -> None:
    payload = _migration_payload()
    payload["work_units"][0]["evidence_lineage"] = []
    with pytest.raises(WorkGraphMigrationError, match="requires explicit evidence_lineage"):
        WorkGraphMigrationService().preview(
            orchestration_id="orch-1",
            checkpoint=_checkpoint(),
            spec=_spec(payload),
        )


def test_migration_cannot_replace_existing_work_unit_or_old_to_old_topology() -> None:
    duplicate = _migration_payload()
    duplicate["work_units"][0]["id"] = "HIST"
    with pytest.raises(WorkGraphMigrationError, match="cannot replace existing"):
        WorkGraphMigrationService().preview(
            orchestration_id="orch-1",
            checkpoint=_checkpoint(),
            spec=_spec(duplicate),
        )

    old_edge = _migration_payload()
    old_edge["dependencies"].append(
        {
            "source_id": "HIST",
            "target_id": "VERIFY",
            "required": True,
            "condition": None,
        }
    )
    with pytest.raises(WorkGraphMigrationError, match="historical Work Units"):
        WorkGraphMigrationService().preview(
            orchestration_id="orch-1",
            checkpoint=_checkpoint(),
            spec=_spec(old_edge),
        )


def test_apply_requires_paused_quiescent_checkpoint_and_matching_digest() -> None:
    service = WorkGraphMigrationService()
    running = _checkpoint(desired_state="RUNNING")
    preview = service.preview(
        orchestration_id="orch-1",
        checkpoint=running,
        spec=_spec(),
    )
    assert preview.apply_ready is False
    assert "desired_state must be PAUSED" in preview.apply_blockers

    with pytest.raises(WorkGraphMigrationError, match="paused, quiescent"):
        service.apply(
            orchestration_id="orch-1",
            checkpoint=running,
            spec=_spec(),
            expected_checkpoint_digest=checkpoint_digest(running),
            artifact_ref=".adaptive/graph-migrations/test.json",
        )

    paused = _checkpoint()
    with pytest.raises(WorkGraphMigrationError, match="Checkpoint changed after dry-run"):
        service.apply(
            orchestration_id="orch-1",
            checkpoint=paused,
            spec=_spec(),
            expected_checkpoint_digest="stale",
            artifact_ref=".adaptive/graph-migrations/test.json",
        )
