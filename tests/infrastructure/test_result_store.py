import hashlib
import json

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
