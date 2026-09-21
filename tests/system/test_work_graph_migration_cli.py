from __future__ import annotations

import json

from adaptive_orchestrator.cli import main
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


def _work_unit(work_unit_id: str) -> dict:
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


def _checkpoint() -> dict:
    return {
        "orchestration_id": "orch-cli",
        "phase": "EXECUTION",
        "desired_state": "PAUSED",
        "terminal": False,
        "request": {
            "objective": "test",
            "max_work_units": 4,
        },
        "plan": {
            "summary": "historical",
            "work_units": [_work_unit("HIST"), _work_unit("AGENDA")],
            "dependencies": [],
        },
        "work_unit_states": {
            "HIST": "COMPLETED",
            "AGENDA": "RECOVERY_REQUIRED",
        },
        "dependency_states": [],
        "attempts": {"HIST": 1, "AGENDA": 2},
        "strategy_generations": {"HIST": 1, "AGENDA": 2},
        "outputs": {"HIST": "done"},
        "output_refs": {"HIST": ".adaptive/runs/hist/result.txt"},
        "revision_feedback": {},
        "records": [],
        "dispatch_records": [],
        "max_parallelism_observed": 1,
        "replan_count": 3,
        "dispatch_generation": 2,
        "pending_replan": True,
        "replan_feedback": "pending",
        "recovery_epoch_counts": {"HIST": 0, "AGENDA": 1},
        "recovery_replans_in_epoch": {"HIST": 0, "AGENDA": 1},
        "recovery_guidance": {"AGENDA": "old"},
        "active_executions": [],
    }


def _migration() -> dict:
    item = _work_unit("WU-01")
    item.update(
        {
            "initial_state": "PLANNED",
            "evidence_lineage": [],
        }
    )
    return {
        "schema_version": "work-graph-migration/1",
        "migration_id": "cli-normalize-v1",
        "reason": "materialize missing explicit node",
        "work_units": [item],
        "dependencies": [
            {
                "source_id": "WU-01",
                "target_id": "AGENDA",
                "required": True,
                "condition": None,
            }
        ],
        "resume_recovery_targets": ["AGENDA"],
        "consume_pending_replan": True,
    }


def test_cli_dry_run_then_apply_is_digest_guarded_and_idempotent(
    tmp_path,
    capsys,
) -> None:
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save("orch-cli", _checkpoint())
    plan_path = tmp_path / "migration.json"
    plan_path.write_text(json.dumps(_migration()), encoding="utf-8")

    code = main(
        [
            "migrate-work-graph",
            "--orchestration-id",
            "orch-cli",
            "--project-root",
            str(tmp_path),
            "--plan",
            str(plan_path),
        ]
    )
    assert code == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["operation"] == "dry-run"
    assert dry_run["apply_ready"] is True
    digest = dry_run["checkpoint_digest"]

    code = main(
        [
            "migrate-work-graph",
            "--orchestration-id",
            "orch-cli",
            "--project-root",
            str(tmp_path),
            "--plan",
            str(plan_path),
            "--apply",
            "--expected-checkpoint-digest",
            digest,
        ]
    )
    assert code == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["operation"] == "apply"
    assert applied["already_applied"] is False
    assert applied["work_unit_count"] == 3
    assert applied["pending_replan"] is False
    assert applied["desired_state"] == "PAUSED"

    checkpoint = store.load("orch-cli")
    assert checkpoint is not None
    assert checkpoint["work_unit_states"]["WU-01"] == "PLANNED"
    assert checkpoint["work_unit_states"]["AGENDA"] == "REVISION_REQUIRED"
    assert checkpoint["graph_migrations"][0]["migration_id"] == "cli-normalize-v1"

    receipt_path = tmp_path / applied["artifact_ref"]
    assert receipt_path.is_file()

    code = main(
        [
            "migrate-work-graph",
            "--orchestration-id",
            "orch-cli",
            "--project-root",
            str(tmp_path),
            "--plan",
            str(plan_path),
            "--apply",
            "--expected-checkpoint-digest",
            "ignored-for-idempotent-reapply",
        ]
    )
    assert code == 0
    repeated = json.loads(capsys.readouterr().out)
    assert repeated["already_applied"] is True


def test_cli_apply_requires_dry_run_digest(tmp_path, capsys) -> None:
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save("orch-cli", _checkpoint())
    plan_path = tmp_path / "migration.json"
    plan_path.write_text(json.dumps(_migration()), encoding="utf-8")

    code = main(
        [
            "migrate-work-graph",
            "--orchestration-id",
            "orch-cli",
            "--project-root",
            str(tmp_path),
            "--plan",
            str(plan_path),
            "--apply",
        ]
    )

    assert code != 0
    assert "expected-checkpoint-digest" in capsys.readouterr().err
