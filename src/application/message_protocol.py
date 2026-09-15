from __future__ import annotations

import hashlib
import json
import re
from typing import Any


PROTOCOL_NAME = "adaptive-message-exchange-protocol"
PROTOCOL_VERSION = 1
REFERENCE_TYPE = "adaptive.message.ref"

# These are the first-class participants documented by AMEP v1. The protocol
# remains extensible: adapters may use additional non-blank component ids.
STANDARD_PARTICIPANTS = (
    "owner",
    "bridge",
    "adaptive",
    "planner",
    "worker",
    "evaluator",
    "sentinel",
)

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_message_reference(
    *,
    message_id: str,
    correlation_id: str,
    sender: str,
    recipient: str,
    message_type: str,
    manifest: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Build the small control-plane reference that travels between components."""

    values = {
        "message_id": message_id,
        "correlation_id": correlation_id,
        "sender": sender,
        "recipient": recipient,
        "message_type": message_type,
        "manifest": manifest,
    }
    for key, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"AMEP reference {key} must be a non-empty string.")
    if not isinstance(manifest_sha256, str) or not _SHA256.fullmatch(manifest_sha256):
        raise ValueError("AMEP reference manifest_sha256 must be 64 hexadecimal characters.")

    reference: dict[str, Any] = {
        "type": REFERENCE_TYPE,
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        **values,
        "manifest_sha256": manifest_sha256.lower(),
    }
    reference["reference_sha256"] = hashlib.sha256(_canonical_json(reference)).hexdigest()
    return reference


def validate_message_reference(reference: object) -> dict[str, Any]:
    """Fail closed when a control-plane AMEP reference is malformed or altered."""

    if not isinstance(reference, dict):
        raise ValueError("AMEP reference must be an object.")
    if reference.get("type") != REFERENCE_TYPE:
        raise ValueError("AMEP reference type is unsupported.")
    if reference.get("protocol") != PROTOCOL_NAME:
        raise ValueError("AMEP protocol name is unsupported.")
    if reference.get("version") != PROTOCOL_VERSION:
        raise ValueError("AMEP protocol version is unsupported.")

    for key in (
        "message_id",
        "correlation_id",
        "sender",
        "recipient",
        "message_type",
        "manifest",
    ):
        value = reference.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"AMEP reference {key} must be a non-empty string.")

    digest = reference.get("manifest_sha256")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ValueError("AMEP reference manifest_sha256 is invalid.")

    reference_digest = reference.get("reference_sha256")
    if not isinstance(reference_digest, str) or not _SHA256.fullmatch(reference_digest):
        raise ValueError("AMEP reference reference_sha256 is invalid.")

    payload = dict(reference)
    payload.pop("reference_sha256", None)
    expected = hashlib.sha256(_canonical_json(payload)).hexdigest()
    if reference_digest.lower() != expected:
        raise ValueError("AMEP reference hash does not match its content.")
    return reference


def render_reference_message(reference: object) -> str:
    """Render the compact wire message; the payload itself never travels in chat."""

    validated = validate_message_reference(reference)
    compact = json.dumps(validated, ensure_ascii=False, separators=(",", ":"))
    return (
        "MANDATORY ADAPTIVE MESSAGE EXCHANGE PROTOCOL (AMEP v1). "
        "The complete authoritative message is file-backed; this chat message is "
        "control-plane metadata only. Read and verify the manifest referenced by "
        "the JSON below, then read the payload declared by that manifest before "
        "acting. Do not treat chat/history as the authoritative payload.\n"
        + compact
    )
