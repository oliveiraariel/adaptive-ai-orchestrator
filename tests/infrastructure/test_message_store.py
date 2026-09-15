import hashlib
import json

import pytest

from application.message_protocol import (
    PROTOCOL_NAME,
    build_message_reference,
    render_reference_message,
    validate_message_reference,
)
from infrastructure.message_store import FileMessageStore, MessageStoreError


def test_message_store_publishes_large_payload_by_small_reference(tmp_path) -> None:
    store = FileMessageStore(root=tmp_path / "messages")
    payload = {
        "summary": "large planner output",
        "work_units": [{"id": "wu-1", "objective": "x" * 20000}],
        "dependencies": [],
    }

    stored = store.publish_json(
        sender="planner",
        recipient="adaptive",
        message_type="planner.plan",
        schema_name="planner-output",
        correlation_id="orch-001",
        payload=payload,
    )

    assert stored.json() == payload
    assert stored.byte_length > 20000
    wire = store.reference_message(stored.reference)
    assert len(wire.encode("utf-8")) < 1600
    assert "x" * 100 not in wire
    assert stored.reference["protocol"] == PROTOCOL_NAME
    assert stored.reference["message_type"] == "planner.plan"


def test_message_reference_is_self_verifying() -> None:
    reference = build_message_reference(
        message_id="msg-1",
        correlation_id="orch-1",
        sender="planner",
        recipient="adaptive",
        message_type="planner.plan",
        manifest="/tmp/msg-1/manifest.json",
        manifest_sha256="a" * 64,
    )

    assert validate_message_reference(reference) == reference

    tampered = dict(reference)
    tampered["recipient"] = "worker"
    with pytest.raises(ValueError, match="hash"):
        validate_message_reference(tampered)


def test_message_store_rejects_payload_integrity_mismatch(tmp_path) -> None:
    store = FileMessageStore(root=tmp_path / "messages")
    stored = store.publish_text(
        sender="worker",
        recipient="adaptive",
        message_type="worker.result",
        schema_name="worker-result",
        correlation_id="orch-1",
        content="original",
    )
    manifest = stored.manifest
    payload_path = (
        tmp_path
        / "messages"
        / manifest["message_id"]
        / manifest["payload"]["file"]
    )
    payload_path.write_text("tampered", encoding="utf-8")

    with pytest.raises(MessageStoreError, match="byte length|SHA-256"):
        store.read_reference(stored.reference)


def test_message_store_publishes_reference_to_recipient_inbox_last(tmp_path) -> None:
    store = FileMessageStore(root=tmp_path / "messages")
    stored = store.publish_text(
        sender="sentinel",
        recipient="adaptive",
        message_type="incident.signal",
        schema_name="incident-message",
        correlation_id="inc-1",
        content="incident",
    )

    inbox = store.list_inbox("adaptive")
    assert inbox == (stored.reference,)
    assert stored.manifest["complete"] is True


def test_external_message_is_invisible_until_adaptive_finalizes(tmp_path) -> None:
    store = FileMessageStore(root=tmp_path / "messages")
    target = store.prepare_target(
        sender="agent:worker-1",
        recipient="adaptive",
        message_type="worker.result",
        schema_name="worker-result",
        correlation_id="orch-1",
        content_type="text/plain",
    )
    target.payload_path.write_text("complete worker result", encoding="utf-8")

    assert store.list_inbox("adaptive") == ()

    stored = store.finalize_external(target)

    assert stored.content == "complete worker result"
    assert store.list_inbox("adaptive") == (stored.reference,)


def test_json_external_message_must_be_valid_before_publication(tmp_path) -> None:
    store = FileMessageStore(root=tmp_path / "messages")
    target = store.prepare_target(
        sender="planner",
        recipient="adaptive",
        message_type="planner.plan",
        schema_name="planner-output",
        correlation_id="orch-1",
        content_type="application/json",
    )
    target.payload_path.write_text('{"summary":"cut"', encoding="utf-8")

    with pytest.raises(MessageStoreError, match="invalid"):
        store.finalize_external(target)

    assert store.list_inbox("adaptive") == ()


def test_reference_wire_message_contains_only_control_plane_metadata() -> None:
    reference = build_message_reference(
        message_id="msg-2",
        correlation_id="orch-2",
        sender="adaptive",
        recipient="agent:worker",
        message_type="work.assignment",
        manifest="/project/.adaptive/messages/msg-2/manifest.json",
        manifest_sha256=hashlib.sha256(b"manifest").hexdigest(),
    )

    message = render_reference_message(reference)

    assert "control-plane metadata only" in message
    assert "authoritative payload" in message
    assert '"type":"adaptive.message.ref"' in message
