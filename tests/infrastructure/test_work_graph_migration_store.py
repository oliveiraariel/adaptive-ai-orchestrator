from __future__ import annotations

import json

import pytest

from application.work_graph_migration import WorkGraphMigrationError
from infrastructure.work_graph_migration_store import FileWorkGraphMigrationStore


def test_receipt_is_immutable_and_idempotent(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)
    receipt = {"migration_id": "m1", "ok": True}

    first = store.write_receipt(
        orchestration_id="orch",
        migration_id="m1",
        spec_digest="a" * 64,
        receipt=receipt,
    )
    second = store.write_receipt(
        orchestration_id="orch",
        migration_id="m1",
        spec_digest="a" * 64,
        receipt=receipt,
    )

    assert first == second
    assert json.loads((tmp_path / first).read_text(encoding="utf-8")) == receipt

    with pytest.raises(WorkGraphMigrationError, match="different content"):
        store.write_receipt(
            orchestration_id="orch",
            migration_id="m1",
            spec_digest="a" * 64,
            receipt={"migration_id": "m1", "ok": False},
        )


def test_apply_lock_prevents_concurrent_migration(tmp_path) -> None:
    store = FileWorkGraphMigrationStore(project_root=tmp_path)

    with store.apply_lock("orch"):
        with pytest.raises(WorkGraphMigrationError, match="already in progress"):
            with store.apply_lock("orch"):
                pass

    with store.apply_lock("orch"):
        pass
