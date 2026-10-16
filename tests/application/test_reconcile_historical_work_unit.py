from __future__ import annotations

from pathlib import Path
import hashlib
import json
import zipfile

import pytest

from application.reconcile_historical_work_unit import (
    HistoricalWorkUnitReconciliationError,
    ReconcileHistoricalWorkUnit,
    ReconciliationDecision,
)
from infrastructure.orchestration_control_plane import FileOrchestrationControlPlane
from infrastructure.project_orchestration_checkpoint import FileProjectOrchestrationCheckpointStore
from infrastructure.result_store import FileResultStore


ORCHESTRATION_ID = "orch-44"
USABLE = (
    "WU-DATA-01", "WU-COMP-04", "WU-REC-01", "WU-REC-03", "WU-REC-04",
    "WU-VG-01", "WU-VG-07", "WU-VG-08", "WU-VG-12", "WU-VG-13",
    "WU-VG-15", "WU-VG-16", "WU-VG-17",
)
DOWNSTREAM = (
    "WU-COMP-02", "WU-COMP-03", "WU-REC-02", "WU-VG-02", "WU-VG-03",
    "WU-VG-06", "WU-VG-04", "VERIFY-STAGE11",
)


def _checkpoint(project_root: Path) -> FileProjectOrchestrationCheckpointStore:
    store = FileProjectOrchestrationCheckpointStore(project_root=project_root)
    results = FileResultStore(project_root=project_root)
    states = {f"ACCEPTED-{index:02d}": "COMPLETED" for index in range(22)}
    states.update({work_unit_id: "RECOVERY_REQUIRED" for work_unit_id in USABLE})
    states["AGENDA"] = "REVISION_REQUIRED"
    states.update({work_unit_id: "PLANNED" for work_unit_id in DOWNSTREAM})
    records: list[dict] = []
    refs: dict[str, str] = {}
    for work_unit_id in (*USABLE, "AGENDA"):
        execution_id = f"execution-{work_unit_id}"
        target = results.prepare_target(
            orchestration_id=ORCHESTRATION_ID,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
        )
        if work_unit_id == "AGENDA":
            output = (
                "ADAPTIVE_WORK_STATUS: PARTIAL\n"
                "ADAPTIVE_BLOCKER_TYPE: ENVIRONMENT\n"
                "ADAPTIVE_UNMET_CRITERIA: browser matrix\n"
            )
        else:
            output = (
                "deliverable available\n"
                "ADAPTIVE_WORK_STATUS: COMPLETE\n"
                "ADAPTIVE_BLOCKER_TYPE: NONE\n"
                "ADAPTIVE_UNMET_CRITERIA: NONE\n"
            )
        results.publish(target, content=output)
        refs[work_unit_id] = str(target.manifest_path)
        records.append(
            {
                "work_unit_id": work_unit_id,
                "role": "frontend",
                "wave": 1,
                "attempt": 1,
                "status": states[work_unit_id],
                "skills": [],
                "execution_id": execution_id,
                "external_id": "gateway:test",
                "runtime_status": "COMPLETED",
                "verdict": "RETURNED",
                "output": output,
                "result_ref": str(target.manifest_path),
                "result_authoritative": True,
                "reason": "evaluation-returned",
                "strategy": 1,
            }
        )
    dependencies = [
        {"source_id": "WU-DATA-01", "target_id": target, "required": True, "status": "BLOCKED"}
        for target in DOWNSTREAM[:6]
    ] + [
        {"source_id": "WU-DATA-01", "target_id": "WU-VG-04", "required": True, "status": "BLOCKED"},
        {"source_id": "WU-REC-02", "target_id": "WU-VG-04", "required": True, "status": "BLOCKED"},
        {"source_id": "WU-REC-04", "target_id": "WU-VG-04", "required": True, "status": "BLOCKED"},
        {"source_id": "AGENDA", "target_id": "VERIFY-STAGE11", "required": True, "status": "BLOCKED"},
    ]
    store.save(
        ORCHESTRATION_ID,
        {
            "orchestration_id": ORCHESTRATION_ID,
            "phase": "EXECUTION",
            "desired_state": "PAUSED",
            "terminal": False,
            "active_executions": [],
            "work_unit_states": states,
            "dependency_states": dependencies,
            "records": records,
            "outputs": {}, "output_refs": {}, "revision_feedback": {},
            "recovery_guidance": {}, "recovery_replans_in_epoch": {},
            "recovery_no_progress_counts": {}, "pending_replan": True,
        },
    )
    FileOrchestrationControlPlane(project_root=project_root).mark_quiescent(
        orchestration_id=ORCHESTRATION_ID,
        checkpoint=store.load(ORCHESTRATION_ID) or {},
        reason="test",
    )
    return store


def _service(project_root: Path, store: FileProjectOrchestrationCheckpointStore) -> ReconcileHistoricalWorkUnit:
    return ReconcileHistoricalWorkUnit(
        project_root=project_root,
        checkpoint_store=store,
        control_plane=FileOrchestrationControlPlane(project_root=project_root),
    )


def test_regression_44_work_units_reconciles_13_usable_results_and_unlocks_data_dependents(tmp_path: Path) -> None:
    store = _checkpoint(tmp_path)
    service = _service(tmp_path, store)
    for work_unit_id in USABLE:
        result = service.execute(
            orchestration_id=ORCHESTRATION_ID,
            work_unit_id=work_unit_id,
            decision=ReconciliationDecision.PRACTICAL_TEST_READY,
            reason="worker complete + verified manifest",
            actor="test-policy",
            policy="practical-test-v1",
        )
        assert result.already_reconciled is False

    checkpoint = store.load(ORCHESTRATION_ID) or {}
    assert len(checkpoint["work_unit_states"]) == 44
    assert sum(value == "COMPLETED" for value in checkpoint["work_unit_states"].values()) == 35
    assert checkpoint["work_unit_states"]["AGENDA"] == "REVISION_REQUIRED"
    assert checkpoint["work_unit_states"]["VERIFY-STAGE11"] == "PLANNED"
    assert checkpoint["pending_replan"] is False
    assert len(checkpoint["reconciliation_decisions"]) == 13
    data_edges = [
        edge for edge in checkpoint["dependency_states"]
        if edge["source_id"] == "WU-DATA-01" and edge["target_id"] != "WU-VG-04"
    ]
    assert len(data_edges) == 6
    assert {edge["status"] for edge in data_edges} == {"SATISFIED"}
    vg4_edges = [edge for edge in checkpoint["dependency_states"] if edge["target_id"] == "WU-VG-04"]
    assert [edge["status"] for edge in vg4_edges].count("BLOCKED") == 1  # WU-REC-02


def test_reconciliation_is_idempotent_and_does_not_erase_returned_history(tmp_path: Path) -> None:
    store = _checkpoint(tmp_path)
    service = _service(tmp_path, store)
    first = service.execute(
        orchestration_id=ORCHESTRATION_ID, work_unit_id="WU-VG-17",
        decision=ReconciliationDecision.PRACTICAL_TEST_READY,
        reason="verified", actor="test", policy="test-policy",
    )
    second = service.execute(
        orchestration_id=ORCHESTRATION_ID, work_unit_id="WU-VG-17",
        decision=ReconciliationDecision.PRACTICAL_TEST_READY,
        reason="different prose does not rewrite audit", actor="test", policy="test-policy",
    )
    checkpoint = store.load(ORCHESTRATION_ID) or {}
    assert first.decision_id == second.decision_id
    assert second.already_reconciled is True
    history = [row for row in checkpoint["records"] if row["work_unit_id"] == "WU-VG-17"]
    assert history[-1]["verdict"] == "RETURNED"
    assert len(checkpoint["reconciliation_decisions"]) == 1


def test_reconciliation_can_release_an_administratively_blocked_returned_result(tmp_path: Path) -> None:
    """A strategist stop must not erase an independently verified delivery."""
    store = _checkpoint(tmp_path)
    checkpoint = store.load(ORCHESTRATION_ID) or {}
    checkpoint["work_unit_states"]["WU-VG-07"] = "BLOCKED"
    checkpoint["records"].append(
        {
            "work_unit_id": "WU-VG-07",
            "role": "frontend",
            "wave": 2,
            "attempt": 2,
            "status": "BLOCKED",
            "skills": [],
            "execution_id": None,
            "external_id": None,
            "runtime_status": None,
            "verdict": "BLOCKED",
            "output": None,
            "result_ref": None,
            "result_authoritative": False,
            "reason": "recovery-suspended:strategist-human-question",
            "strategy": 2,
        }
    )
    store.save(ORCHESTRATION_ID, checkpoint)

    result = _service(tmp_path, store).execute(
        orchestration_id=ORCHESTRATION_ID,
        work_unit_id="WU-VG-07",
        decision=ReconciliationDecision.PRACTICAL_TEST_READY,
        reason="prior completed returned result remains integrity-verified",
        actor="test",
        policy="practical-test-v1",
    )

    final = store.load(ORCHESTRATION_ID) or {}
    assert result.already_reconciled is False
    assert final["work_unit_states"]["WU-VG-07"] == "COMPLETED"
    assert final["records"][-2]["verdict"] == "RETURNED"
    assert final["records"][-1]["verdict"] == "BLOCKED"
    assert final["reconciliation_decisions"][-1]["historical_verdict"] == "RETURNED"


def test_reconciliation_accepts_legacy_runtime_execution_id_when_manifest_is_intact(tmp_path: Path) -> None:
    store = _checkpoint(tmp_path)
    checkpoint = store.load(ORCHESTRATION_ID) or {}
    record = next(item for item in checkpoint["records"] if item["work_unit_id"] == "WU-DATA-01")
    # Legacy checkpoints stored the Gateway/runtime execution identity here,
    # while Result Store publication used its own immutable UUID directory.
    record["execution_id"] = "openclaw:gateway:logical:WU-DATA-01"
    store.save(ORCHESTRATION_ID, checkpoint)

    result = _service(tmp_path, store).execute(
        orchestration_id=ORCHESTRATION_ID,
        work_unit_id="WU-DATA-01",
        decision=ReconciliationDecision.PRACTICAL_TEST_READY,
        reason="legacy runtime id; final publication manifest independently verifies",
        actor="test",
        policy="practical-test-v1",
    )

    assert result.source_execution_id == "openclaw:gateway:logical:WU-DATA-01"
    assert (store.load(ORCHESTRATION_ID) or {})["work_unit_states"]["WU-DATA-01"] == "COMPLETED"


def test_partial_or_blocked_historical_result_cannot_be_promoted(tmp_path: Path) -> None:
    store = _checkpoint(tmp_path)
    with pytest.raises(HistoricalWorkUnitReconciliationError, match="not a usable COMPLETE"):
        _service(tmp_path, store).execute(
            orchestration_id=ORCHESTRATION_ID, work_unit_id="AGENDA",
            decision=ReconciliationDecision.PRACTICAL_TEST_READY,
            reason="not enough evidence", actor="test", policy="test-policy",
        )


def test_release_reconciliation_rechecks_canonical_delivery_gate(tmp_path: Path) -> None:
    orchestration_id = "orch-release-reconcile"
    work_unit_id = "release"
    store = FileProjectOrchestrationCheckpointStore(project_root=tmp_path)
    results = FileResultStore(project_root=tmp_path)
    artifact = tmp_path / "release.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr(
            "plugin/plugin.php",
            "<?php\n/*\n * Plugin Name: Example\n * Version: 1.0.3\n */\n",
        )
    report = tmp_path / "report.md"
    report.write_text("release report", encoding="utf-8")
    delivery_manifest = tmp_path / "delivery.json"
    delivery_manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "platform": "wordpress",
                "artifact_path": str(artifact),
                "report_path": str(report),
                "source_identity": "repo@abc",
                "version": "1.0.4",
                "internal_version": "1.0.4",
                "version_source": {"kind": "wordpress-plugin-header"},
                "size_bytes": artifact.stat().st_size,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "integrity_checked": True,
                "install_structure_checked": True,
                "validations": ["zip-check"],
                "publication": {
                    "canonical": True,
                    "atomic": True,
                    "historical_artifacts_preserved": True,
                    "release_identity": "plugin@1.0.4",
                    "staging_path": str(tmp_path / "staging" / "release.zip"),
                },
            }
        ),
        encoding="utf-8",
    )
    target = results.prepare_target(
        orchestration_id=orchestration_id,
        work_unit_id=work_unit_id,
        execution_id="execution-release",
    )
    output = (
        f"ADAPTIVE_RELEASE_MANIFEST: {delivery_manifest}\n"
        "ADAPTIVE_WORK_STATUS: COMPLETE\n"
        "ADAPTIVE_BLOCKER_TYPE: NONE\n"
        "ADAPTIVE_UNMET_CRITERIA: NONE\n"
    )
    results.publish(target, content=output)
    store.save(
        orchestration_id,
        {
            "orchestration_id": orchestration_id,
            "phase": "EXECUTION",
            "desired_state": "PAUSED",
            "terminal": False,
            "active_executions": [],
            "plan": {
                "summary": "release",
                "work_units": [
                    {
                        "id": work_unit_id,
                        "objective": "Create an installable release",
                        "role": "release",
                        "release_delivery": True,
                        "expected_output": ["release"],
                        "acceptance_criteria": ["release"],
                    }
                ],
            },
            "request": {"constraints": []},
            "work_unit_states": {work_unit_id: "RECOVERY_REQUIRED"},
            "records": [
                {
                    "work_unit_id": work_unit_id,
                    "execution_id": "execution-release",
                    "runtime_status": "COMPLETED",
                    "result_authoritative": True,
                    "result_ref": str(target.manifest_path),
                    "verdict": "RETURNED",
                    "status": "RECOVERY_REQUIRED",
                    "output": output,
                }
            ],
            "dependency_states": [],
        },
    )
    FileOrchestrationControlPlane(project_root=tmp_path).mark_quiescent(
        orchestration_id=orchestration_id,
        checkpoint=store.load(orchestration_id) or {},
        reason="test",
    )
    with pytest.raises(HistoricalWorkUnitReconciliationError, match="Release delivery gate"):
        ReconcileHistoricalWorkUnit(
            project_root=tmp_path,
            checkpoint_store=store,
            control_plane=FileOrchestrationControlPlane(project_root=tmp_path),
        ).execute(
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            decision=ReconciliationDecision.ACCEPTED,
            reason="test",
            actor="test",
            policy="test",
        )
