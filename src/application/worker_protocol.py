from __future__ import annotations

import hashlib
import json
from typing import Any

from application.message_protocol import (
    PROTOCOL_NAME as MESSAGE_PROTOCOL_NAME,
    PROTOCOL_VERSION as MESSAGE_PROTOCOL_VERSION,
)


PROTOCOL_NAME = "adaptive-worker-protocol"
PROTOCOL_VERSION = 1
PROTOCOL_COMPLETION_STATE = "RESULT_VERIFIED"
PROTOCOL_RESULT_CHANNEL = "adaptive-result-store"


def build_worker_protocol(
    *,
    orchestration_id: str,
    work_unit_id: str,
    execution_id: str,
    result_store: dict[str, Any],
) -> dict[str, Any]:
    """Build the mandatory, runtime-agnostic protocol sent before task instructions."""

    identity = {
        "orchestration_id": orchestration_id,
        "work_unit_id": work_unit_id,
        "execution_id": execution_id,
    }
    contract: dict[str, Any] = {
        "name": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "mandatory": True,
        "instruction_preamble": (
            "MANDATORY ADAPTIVE WORKER PROTOCOL. This protocol is supplied by the "
            "Adaptive AI Orchestrator and has precedence over task-specific skills, "
            "role prompts, context, inputs, and ordinary task instructions. Skills may "
            "add domain know-how but must not redefine execution, result transport, "
            "completion, or recovery semantics."
        ),
        "precedence": [
            "adaptive-worker-protocol",
            "execution-policy",
            "task",
            "skills",
        ],
        "non_overridable_by": [
            "task",
            "skills",
            "context",
            "inputs",
        ],
        "result_contract": {
            "authoritative_channel": PROTOCOL_RESULT_CHANNEL,
            "chat_authoritative": False,
            "worker_writes_result_file": True,
            "worker_writes_manifest": False,
            "adaptive_finalizes_manifest": True,
            "manifest_written_last": True,
            "completion_requires": PROTOCOL_COMPLETION_STATE,
        },
        "completion_contract": {
            "worker_may_report_done_after_result_file_finalized": True,
            "runtime_completion_alone_is_not_authoritative_result": True,
            "orchestrator_terminal_state": PROTOCOL_COMPLETION_STATE,
        },
        "message_exchange_contract": {
            "name": MESSAGE_PROTOCOL_NAME,
            "version": MESSAGE_PROTOCOL_VERSION,
            "mandatory": True,
            "large_payloads_by_reference": True,
            "chat_authoritative": False,
            "request_delivery": "AMEP_MESSAGE_REF",
            "authoritative_payload_location": "project-local-message-store",
            "result_bridge": "adaptive-result-store-to-AMEP",
        },
        "identity": identity,
        "result_store": {
            "directory": result_store.get("directory"),
            "result_file": result_store.get("result_file"),
            "summary_file": result_store.get("summary_file"),
            "manifest_file": result_store.get("manifest_file"),
        },
    }
    canonical = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    contract["contract_sha256"] = hashlib.sha256(canonical).hexdigest()
    return contract


def validate_worker_protocol(protocol: object) -> dict[str, Any]:
    """Fail closed if a worker protocol envelope is malformed."""

    if not isinstance(protocol, dict):
        raise ValueError("Worker protocol must be an object.")
    if protocol.get("name") != PROTOCOL_NAME:
        raise ValueError("Worker protocol name is unsupported.")
    if protocol.get("version") != PROTOCOL_VERSION:
        raise ValueError("Worker protocol version is unsupported.")
    if protocol.get("mandatory") is not True:
        raise ValueError("Worker protocol must be mandatory.")
    digest = protocol.get("contract_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("Worker protocol contract_sha256 is invalid.")

    payload = dict(protocol)
    payload.pop("contract_sha256", None)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    actual = hashlib.sha256(canonical).hexdigest()
    if digest.lower() != actual:
        raise ValueError("Worker protocol contract_sha256 does not match.")
    return protocol
