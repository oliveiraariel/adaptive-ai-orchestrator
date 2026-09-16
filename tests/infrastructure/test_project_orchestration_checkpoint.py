import json

import pytest

from infrastructure.project_orchestration_checkpoint import (
    FileProjectOrchestrationCheckpointStore,
    ProjectOrchestrationCheckpointError,
)


def test_checkpoint_round_trip_is_atomic_and_identity_scoped(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)

    store.save("orch-001", {"value": 1, "active_executions": []})
    assert store.load("orch-001") == {"value": 1, "active_executions": []}

    path = store.path_for("orch-001")
    envelope = json.loads(path.read_text(encoding="utf-8"))
    assert envelope["schema_version"] == 1
    assert envelope["orchestration_id"] == "orch-001"
    assert not path.with_name(f".{path.name}.tmp").exists()


def test_checkpoint_missing_returns_none(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)

    assert store.load("missing") is None


def test_checkpoint_rejects_identity_mismatch(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    path = store.path_for("orch-001")
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "orchestration_id": "other",
                "state": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ProjectOrchestrationCheckpointError,
        match="identity mismatch",
    ):
        store.load("orch-001")


def test_checkpoint_rejects_corrupt_json(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    store = FileProjectOrchestrationCheckpointStore(project_root=project)
    path = store.path_for("orch-001")
    path.parent.mkdir(parents=True)
    path.write_text("{bad-json", encoding="utf-8")

    with pytest.raises(
        ProjectOrchestrationCheckpointError,
        match="unreadable",
    ):
        store.load("orch-001")
