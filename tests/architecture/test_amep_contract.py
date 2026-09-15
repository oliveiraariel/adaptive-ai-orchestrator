import json
from pathlib import Path

from application.message_protocol import (
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    STANDARD_PARTICIPANTS,
)
from application.worker_protocol import build_worker_protocol


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_amep_normative_artifacts_exist_and_match_runtime_contract() -> None:
    architecture = (
        REPO_ROOT / "docs/architecture/ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md"
    )
    ref_schema_path = (
        REPO_ROOT / "specifications/protocols/amep-message-ref-v1.schema.json"
    )
    manifest_schema_path = (
        REPO_ROOT / "specifications/protocols/amep-manifest-v1.schema.json"
    )

    assert architecture.is_file()
    assert ref_schema_path.is_file()
    assert manifest_schema_path.is_file()

    ref_schema = json.loads(ref_schema_path.read_text(encoding="utf-8"))
    manifest_schema = json.loads(manifest_schema_path.read_text(encoding="utf-8"))

    assert ref_schema["properties"]["protocol"]["const"] == PROTOCOL_NAME
    assert ref_schema["properties"]["version"]["const"] == PROTOCOL_VERSION
    assert manifest_schema["properties"]["protocol"]["const"] == PROTOCOL_NAME
    assert (
        manifest_schema["properties"]["protocol_version"]["const"]
        == PROTOCOL_VERSION
    )


def test_worker_protocol_cannot_hide_the_mandatory_amep_contract() -> None:
    protocol = build_worker_protocol(
        orchestration_id="orch",
        work_unit_id="wu",
        execution_id="exec",
        result_store={
            "directory": "/tmp/run",
            "result_file": "/tmp/run/result.txt",
            "summary_file": "/tmp/run/summary.md",
            "manifest_file": "/tmp/run/manifest.json",
        },
    )

    exchange = protocol["message_exchange_contract"]
    assert exchange == {
        "name": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "mandatory": True,
        "large_payloads_by_reference": True,
        "chat_authoritative": False,
        "request_delivery": "AMEP_MESSAGE_REF",
        "authoritative_payload_location": "project-local-message-store",
        "result_bridge": "adaptive-result-store-to-AMEP",
    }


def test_project_context_and_manifest_make_amep_default_knowledge() -> None:
    context = (REPO_ROOT / "CONTEXT.md").read_text(encoding="utf-8")
    manifest = (REPO_ROOT / "PROJECT-KNOWLEDGE-MANIFEST.yaml").read_text(
        encoding="utf-8"
    )

    assert "ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md" in context
    assert "ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md" in manifest
    assert "communication_protocols:" in manifest
    assert "default_retrieval: true" in manifest


def test_all_core_adaptive_participants_are_named_by_amep() -> None:
    expected = {
        "owner",
        "bridge",
        "adaptive",
        "planner",
        "worker",
        "evaluator",
        "sentinel",
    }

    assert expected <= set(STANDARD_PARTICIPANTS)
