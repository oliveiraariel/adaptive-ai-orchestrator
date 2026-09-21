import json

import pytest

from adaptive_orchestrator import cli
from application.continuous_project_orchestration import RunContinuousProjectOrchestration
from application.run_project_orchestration import ProjectOrchestrationRequest
from application.work_graph_migration import (
    WorkGraphMigrationError,
    WorkGraphMigrationService,
)
from domain.project_execution_plan import PlannedWorkUnit, ProjectExecutionPlan
from domain.work_unit import WorkUnitKind
from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
)


def _planned_spec(unit_id: str, objective: str | None = None) -> dict:
    unit = PlannedWorkUnit(
        id=unit_id,
        objective=objective or f"Execute {unit_id}",
        role="worker",
        kind=WorkUnitKind.EXECUTION,
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
        parallel_safe=False,
    )
    plan = ProjectExecutionPlan(summary="spec", work_units=(unit,))
    return RunContinuousProjectOrchestration._plan_to_payload(plan)["work_units"][0]


def _checkpoint(
    orchestration_id: str,
    *,
    desired_state: str = "PAUSED",
    max_work_units: int = 8,
    active_executions: list[dict] | None = None,
) -> dict:
    historical = (
        PlannedWorkUnit(
            id="OLD-DATA",
            objective="Historical data aggregate",
            role="worker",
            expected_output=("result",),
            acceptance_criteria=("runtime-completed",),
        ),
        PlannedWorkUnit(
            id="OLD-AGENDA",
            objective="Historical agenda aggregate",
            role="worker",
            expected_output=("result",),
            acceptance_criteria=("runtime-completed",),
        ),
    )
    plan = ProjectExecutionPlan(summary="historical plan", work_units=historical)
    request = ProjectOrchestrationRequest(
        objective="Normalize a historical Work Graph.",
        orchestration_id=orchestration_id,
        max_work_units=max_work_units,
        plan=plan,
    )
    return {
        "orchestration_id": orchestration_id,
        "phase": "EXECUTION",
        "desired_state": desired_state,
        "terminal": False,
        "request": RunContinuousProjectOrchestration._request_to_payload(request),
        "plan": RunContinuousProjectOrchestration._plan_to_payload(plan),
        "work_unit_states": {
            "OLD-DATA": "COMPLETED",
            "OLD-AGENDA": "RECOVERY_REQUIRED",
        },
        "dependency_states": [],
        "attempts": {"OLD-DATA": 1, "OLD-AGENDA": 2},
        "strategy_generations": {"OLD-DATA": 1, "OLD-AGENDA": 2},
        "outputs": {"OLD-DATA": "historical result"},
        "output_refs": {"OLD-DATA": "/results/old-data/manifest.json"},
        "revision_feedback": {},
        "records": [],
        "dispatch_records": [],
        "max_parallelism_observed": 1,
        "replan_count": 7,
        "dispatch_generation": 3,
        "pending_replan": True,
        "replan_feedback": "historical aggregate recovery",
        "recovery_epoch_counts": {"OLD-DATA": 0, "OLD-AGENDA": 1},
        "recovery_replans_in_epoch": {"OLD-DATA": 0, "OLD-AGENDA": 1},
        "recovery_guidance": {},
        "active_executions": active_executions or [],
    }


def _migration(
    orchestration_id: str,
    *,
    expected_fingerprint: str | None = None,
    migration_id: str = "normalize-explicit-wus-v1",
) -> dict:
    return {
        "schema_version": "work-graph-migration/1",
        "migration_id": migration_id,
        "orchestration_id": orchestration_id,
        "reason": "Restore explicit Work Unit governance identities.",
        "expected_checkpoint_fingerprint": expected_fingerprint,
        "new_work_units": [
            {
                "spec": _planned_spec("WU-MC-01"),
                "initial_state": "COMPLETED",
                "lineage": {
                    "historical_source_ids": ["OLD-DATA"],
                    "evidence_refs": ["/results/old-data/manifest.json"],
                    "evidence_summary": "Historical evidence proves this criterion.",
                },
            },
            {
                "spec": _planned_spec("WU-DATA-01"),
                "initial_state": "PLANNED",
                "lineage": {
                    "historical_source_ids": ["OLD-DATA"],
                    "evidence_refs": [],
                    "evidence_summary": "Historical aggregate was partial; revalidation required.",
                },
            },
            {
                "spec": _planned_spec("WU-COMP-02"),
                "initial_state": "PLANNED",
                "lineage": {
                    "historical_source_ids": ["OLD-DATA"],
                    "evidence_refs": [],
                    "evidence_summary": "Depends on accepted daily-date contract.",
                },
            },
        ],
        "dependencies": [
            {
                "source_id": "WU-DATA-01",
                "target_id": "WU-COMP-02",
                "required": True,
                "condition": None,
            }
        ],
        "supersede_for_scheduling": ["OLD-AGENDA"],
    }


def _store(tmp_path, checkpoint: dict) -> FileProjectOrchestrationCheckpointStore:
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    store.save(checkpoint["orchestration_id"], checkpoint)
    return store


def test_preview_is_read_only_and_returns_checkpoint_fingerprint(tmp_path) -> None:
    orchestration_id = "orch-migrate-preview"
    checkpoint = _checkpoint(orchestration_id)
    store = _store(tmp_path, checkpoint)
    service = WorkGraphMigrationService(project_root=tmp_path)

    result = service.preview(
        orchestration_id=orchestration_id,
        migration=_migration(orchestration_id),
    )

    assert result.mode == "work-graph-migration-dry-run"
    assert result.added_work_unit_ids == ("WU-MC-01", "WU-DATA-01", "WU-COMP-02")
    assert result.total_work_unit_count == 5
    assert len(result.checkpoint_fingerprint_before) == 64
    assert result.checkpoint_fingerprint_after is not None
    assert store.load(orchestration_id) == checkpoint


def test_apply_requires_paused_quiescent_checkpoint(tmp_path) -> None:
    orchestration_id = "orch-migrate-safety"
    _store(tmp_path, _checkpoint(orchestration_id, desired_state="RUNNING"))
    service = WorkGraphMigrationService(project_root=tmp_path)
    migration = _migration(
        orchestration_id,
        expected_fingerprint="0" * 64,
    )

    with pytest.raises(WorkGraphMigrationError, match="desired_state=PAUSED"):
        service.apply(orchestration_id=orchestration_id, migration=migration)
    with pytest.raises(WorkGraphMigrationError, match="desired_state=PAUSED"):
        service.preview(
            orchestration_id=orchestration_id,
            migration=_migration(orchestration_id),
        )

    active = [
        {
            "work_unit_id": "OLD-AGENDA",
            "generation": 1,
            "execution_id": "execution:agenda",
            "external_id": "external:agenda",
            "runtime": "fake",
        }
    ]
    _store(
        tmp_path,
        _checkpoint(
            orchestration_id,
            desired_state="PAUSED",
            active_executions=active,
        ),
    )
    with pytest.raises(WorkGraphMigrationError, match="zero active executions"):
        service.apply(orchestration_id=orchestration_id, migration=migration)
    with pytest.raises(WorkGraphMigrationError, match="zero active executions"):
        service.preview(
            orchestration_id=orchestration_id,
            migration=_migration(orchestration_id),
        )


def test_apply_adds_normalized_nodes_preserves_history_and_is_idempotent(tmp_path) -> None:
    orchestration_id = "orch-migrate-apply"
    store = _store(tmp_path, _checkpoint(orchestration_id))
    service = WorkGraphMigrationService(project_root=tmp_path)
    preview = service.preview(
        orchestration_id=orchestration_id,
        migration=_migration(orchestration_id),
    )
    migration = _migration(
        orchestration_id,
        expected_fingerprint=preview.checkpoint_fingerprint_before,
    )

    result = service.apply(
        orchestration_id=orchestration_id,
        migration=migration,
    )

    assert result.idempotent is False
    assert result.pending_replan_after is False
    state = store.load(orchestration_id)
    assert state is not None
    assert state["work_unit_states"]["OLD-DATA"] == "COMPLETED"
    assert state["work_unit_states"]["OLD-AGENDA"] == "RECOVERY_REQUIRED"
    assert state["work_unit_states"]["WU-MC-01"] == "COMPLETED"
    assert state["work_unit_states"]["WU-DATA-01"] == "PLANNED"
    assert state["work_unit_states"]["WU-COMP-02"] == "PLANNED"
    assert state["outputs"]["OLD-DATA"] == "historical result"
    assert state["output_refs"]["OLD-DATA"] == "/results/old-data/manifest.json"
    assert state["superseded_work_unit_ids"] == ["OLD-AGENDA"]
    assert state["pending_replan"] is False

    edge = next(
        item
        for item in state["dependency_states"]
        if item["source_id"] == "WU-DATA-01"
        and item["target_id"] == "WU-COMP-02"
    )
    assert edge["status"] == "BLOCKED"

    history = state["work_graph_migrations"]
    assert len(history) == 1
    assert history[0]["migration"]["new_work_units"][0]["lineage"][
        "evidence_refs"
    ] == ["/results/old-data/manifest.json"]
    artifact = tmp_path / history[0]["artifact_path"]
    assert artifact.is_file()

    second = service.apply(
        orchestration_id=orchestration_id,
        migration=migration,
    )
    assert second.idempotent is True
    state_again = store.load(orchestration_id)
    assert state_again is not None
    assert len(state_again["work_graph_migrations"]) == 1
    assert [
        item["id"] for item in state_again["plan"]["work_units"]
    ].count("WU-DATA-01") == 1


def test_same_migration_id_with_different_content_fails_closed(tmp_path) -> None:
    orchestration_id = "orch-migrate-digest"
    _store(tmp_path, _checkpoint(orchestration_id))
    service = WorkGraphMigrationService(project_root=tmp_path)
    preview = service.preview(
        orchestration_id=orchestration_id,
        migration=_migration(orchestration_id),
    )
    migration = _migration(
        orchestration_id,
        expected_fingerprint=preview.checkpoint_fingerprint_before,
    )
    service.apply(orchestration_id=orchestration_id, migration=migration)

    changed = json.loads(json.dumps(migration))
    changed["reason"] = "Different semantic migration."
    with pytest.raises(WorkGraphMigrationError, match="different content"):
        service.apply(orchestration_id=orchestration_id, migration=changed)


def test_completed_migrated_work_requires_evidence_lineage(tmp_path) -> None:
    orchestration_id = "orch-migrate-evidence"
    _store(tmp_path, _checkpoint(orchestration_id))
    service = WorkGraphMigrationService(project_root=tmp_path)
    migration = _migration(orchestration_id)
    migration["new_work_units"][0]["lineage"]["evidence_refs"] = []

    with pytest.raises(WorkGraphMigrationError, match="requires historical_source_ids"):
        service.preview(orchestration_id=orchestration_id, migration=migration)


def test_migration_cannot_redefine_historical_dependency_topology(tmp_path) -> None:
    orchestration_id = "orch-migrate-historical-edge"
    _store(tmp_path, _checkpoint(orchestration_id))
    service = WorkGraphMigrationService(project_root=tmp_path)
    migration = _migration(orchestration_id)
    migration["dependencies"] = [
        {
            "source_id": "WU-DATA-01",
            "target_id": "OLD-AGENDA",
            "required": True,
            "condition": None,
        }
    ]

    with pytest.raises(WorkGraphMigrationError, match="target only newly-created"):
        service.preview(orchestration_id=orchestration_id, migration=migration)


def test_migration_enforces_work_unit_budget(tmp_path) -> None:
    orchestration_id = "orch-migrate-budget"
    _store(tmp_path, _checkpoint(orchestration_id, max_work_units=4))
    service = WorkGraphMigrationService(project_root=tmp_path)

    with pytest.raises(WorkGraphMigrationError, match="exceed max_work_units"):
        service.preview(
            orchestration_id=orchestration_id,
            migration=_migration(orchestration_id),
        )


def test_cli_dry_run_then_apply_and_project_status_hide_superseded_history(
    tmp_path, capsys
) -> None:
    orchestration_id = "orch-migrate-cli"
    _store(tmp_path, _checkpoint(orchestration_id))
    plan_path = tmp_path / "migration.json"
    plan_path.write_text(
        json.dumps(_migration(orchestration_id)),
        encoding="utf-8",
    )

    code = cli.main(
        [
            "migrate-work-graph",
            "--orchestration-id",
            orchestration_id,
            "--project-root",
            str(tmp_path),
            "--plan-file",
            str(plan_path),
            "--dry-run",
        ]
    )
    assert code == 0
    dry_run = json.loads(capsys.readouterr().out)
    migration = _migration(
        orchestration_id,
        expected_fingerprint=dry_run["checkpoint_fingerprint_before"],
    )
    plan_path.write_text(json.dumps(migration), encoding="utf-8")

    code = cli.main(
        [
            "migrate-work-graph",
            "--orchestration-id",
            orchestration_id,
            "--project-root",
            str(tmp_path),
            "--plan-file",
            str(plan_path),
            "--apply",
        ]
    )
    assert code == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["idempotent"] is False

    code = cli.main(
        [
            "project-status",
            "--orchestration-id",
            orchestration_id,
            "--project-root",
            str(tmp_path),
        ]
    )
    assert code == 0
    status = json.loads(capsys.readouterr().out)
    assert status["work_unit_count"] == 5
    assert status["operational_work_unit_count"] == 4
    assert status["superseded_work_unit_ids"] == ["OLD-AGENDA"]
    assert status["work_graph_migration_count"] == 1
    assert "OLD-AGENDA" not in status["recovery_required_work_unit_ids"]


def test_supersession_rejects_stranded_historical_dependent(tmp_path) -> None:
    orchestration_id = "orch-migrate-stranded"
    checkpoint = _checkpoint(orchestration_id)
    checkpoint["plan"]["work_units"].append(_planned_spec("OLD-VERIFY"))
    checkpoint["plan"]["dependencies"].append(
        {
            "source_id": "OLD-AGENDA",
            "target_id": "OLD-VERIFY",
            "required": True,
            "condition": None,
        }
    )
    checkpoint["work_unit_states"]["OLD-VERIFY"] = "PLANNED"
    checkpoint["attempts"]["OLD-VERIFY"] = 0
    checkpoint["strategy_generations"]["OLD-VERIFY"] = 1
    checkpoint["recovery_epoch_counts"]["OLD-VERIFY"] = 0
    checkpoint["recovery_replans_in_epoch"]["OLD-VERIFY"] = 0
    checkpoint["dependency_states"].append(
        {
            "source_id": "OLD-AGENDA",
            "target_id": "OLD-VERIFY",
            "required": True,
            "status": "BLOCKED",
        }
    )
    _store(tmp_path, checkpoint)
    service = WorkGraphMigrationService(project_root=tmp_path)

    migration = _migration(orchestration_id)
    with pytest.raises(WorkGraphMigrationError, match="would strand operational"):
        service.preview(orchestration_id=orchestration_id, migration=migration)

    migration["supersede_for_scheduling"] = ["OLD-AGENDA", "OLD-VERIFY"]
    preview = service.preview(
        orchestration_id=orchestration_id,
        migration=migration,
    )
    assert preview.superseded_work_unit_ids == ("OLD-AGENDA", "OLD-VERIFY")
