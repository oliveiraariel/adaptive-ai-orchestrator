import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from infrastructure.result_store import FileResultStore, ResultStoreError


def test_result_store_publishes_and_recovers_large_result(tmp_path) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(
        orchestration_id="orch-001",
        work_unit_id="wu-backend",
        execution_id="exec-001",
    )
    content = "BEGIN\n" + ("x" * 15000) + "\nEND"

    stored = store.publish(target, content=content, summary="short summary")

    assert stored.content == content
    assert stored.byte_length == len(content.encode("utf-8"))
    assert stored.sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert stored.summary == "short summary"
    assert target.manifest_path.exists()
    assert not target.result_path.with_name("result.txt.tmp").exists()

    manifest = json.loads(target.manifest_path.read_text(encoding="utf-8"))
    assert manifest["result_bytes"] == len(content.encode("utf-8"))
    assert manifest["result_sha256"] == hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_result_store_manifest_is_completion_sentinel(tmp_path) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(
        orchestration_id="orch-001",
        work_unit_id="wu-001",
        execution_id="exec-001",
    )
    target.result_path.write_text("partial or complete bytes are not authoritative yet", encoding="utf-8")

    assert store.read_result(target) is None


def test_result_store_rejects_integrity_mismatch(tmp_path) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(
        orchestration_id="orch-001",
        work_unit_id="wu-001",
        execution_id="exec-001",
    )
    store.publish(target, content="original")
    target.result_path.write_text("tampered", encoding="utf-8")

    with pytest.raises(ResultStoreError, match="byte length|SHA-256"):
        store.read_result(target)


@pytest.mark.parametrize("field", ["result_bytes", "result_sha256"])
def test_result_store_rejects_missing_integrity_field(tmp_path, field) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(orchestration_id="orch", work_unit_id="wu", execution_id="exec")
    store.publish(target, content="result")
    manifest = json.loads(target.manifest_path.read_text(encoding="utf-8"))
    del manifest[field]
    target.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ResultStoreError, match="result_bytes|result_sha256"):
        store.read_result(target)


@pytest.mark.parametrize(
    "field,value",
    [
        ("result_bytes", 99),
        ("result_sha256", "0" * 64),
        ("result_bytes", True),
        ("result_bytes", -1),
        ("result_sha256", "g" * 64),
        ("result_sha256", "0" * 63),
    ],
)
def test_result_store_rejects_invalid_integrity_field(tmp_path, field, value) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(orchestration_id="orch", work_unit_id="wu", execution_id="exec")
    store.publish(target, content="result")
    manifest = json.loads(target.manifest_path.read_text(encoding="utf-8"))
    manifest[field] = value
    target.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ResultStoreError):
        store.read_result(target)


def test_worker_instructions_require_integrity_and_manifest_last(tmp_path) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(orchestration_id="orch", work_unit_id="wu", execution_id="exec")
    instructions = store.worker_instructions(target)

    assert "result_bytes" in instructions
    assert "result_sha256" in instructions
    assert "UTF-8 byte" in instructions
    assert "SHA-256" in instructions
    assert "manifest.json LAST" in instructions


def test_result_store_rejects_manifest_identity_mismatch(tmp_path) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(
        orchestration_id="orch-001",
        work_unit_id="wu-001",
        execution_id="exec-001",
    )
    target.result_path.write_text("result", encoding="utf-8")
    target.manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "orchestration_id": "other",
                "work_unit_id": "wu-001",
                "execution_id": "exec-001",
                "complete": True,
                "result_file": "result.txt",
                "summary_file": None,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ResultStoreError, match="orchestration_id"):
        store.read_result(target)


def test_result_store_sanitizes_directory_segments_without_changing_manifest_identity(tmp_path) -> None:
    store = FileResultStore(tmp_path)
    target = store.prepare_target(
        orchestration_id="../orch unsafe",
        work_unit_id="wu/unsafe",
        execution_id="exec:001",
    )
    store.publish(target, content="ok")

    assert target.directory.is_relative_to(tmp_path)
    assert ".." not in target.directory.parts
    recovered = store.read_result(target)
    assert recovered is not None
    assert recovered.manifest["orchestration_id"] == "../orch unsafe"


def test_project_local_store_defaults_to_project_adaptive_runs(tmp_path) -> None:
    project = tmp_path / "project-a"
    project.mkdir()

    store = FileResultStore(project_root=project, manage_git_exclude=False)
    target = store.prepare_target(
        orchestration_id="orch-local",
        work_unit_id="wu-local",
        execution_id="exec-local",
    )

    assert store.project_root == project.resolve()
    assert store.root == project.resolve() / ".adaptive" / "runs"
    assert target.directory.is_relative_to(project.resolve() / ".adaptive" / "runs")
    assert target.as_payload()["project_root"] == str(project.resolve())


def test_project_local_stores_are_isolated_between_projects(tmp_path) -> None:
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()

    store_a = FileResultStore(project_root=project_a, manage_git_exclude=False)
    store_b = FileResultStore(project_root=project_b, manage_git_exclude=False)

    target_a = store_a.prepare_target(
        orchestration_id="same-orch",
        work_unit_id="same-wu",
        execution_id="same-exec",
    )
    target_b = store_b.prepare_target(
        orchestration_id="same-orch",
        work_unit_id="same-wu",
        execution_id="same-exec",
    )

    store_a.publish(target_a, content="project-a-result")
    store_b.publish(target_b, content="project-b-result")

    assert target_a.result_path != target_b.result_path
    assert store_a.read_result(target_a).content == "project-a-result"
    assert store_b.read_result(target_b).content == "project-b-result"
    assert not target_a.result_path.is_relative_to(project_b)
    assert not target_b.result_path.is_relative_to(project_a)


def test_project_local_store_excludes_adaptive_state_from_git_without_editing_gitignore(tmp_path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    tracked_gitignore = project / ".gitignore"
    tracked_gitignore.write_text("*.pyc\n", encoding="utf-8")
    before = tracked_gitignore.read_text(encoding="utf-8")

    store = FileResultStore(project_root=project)
    store.prepare_target(
        orchestration_id="orch",
        work_unit_id="wu",
        execution_id="exec",
    )

    exclude = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--git-path", "info/exclude"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    exclude_path = project / exclude if not Path(exclude).is_absolute() else Path(exclude)

    assert "/.adaptive/" in exclude_path.read_text(encoding="utf-8")
    assert tracked_gitignore.read_text(encoding="utf-8") == before
