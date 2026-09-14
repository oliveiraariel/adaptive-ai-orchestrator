from application.worker_protocol import (
    PROTOCOL_COMPLETION_STATE,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    build_worker_protocol,
    validate_worker_protocol,
)


def make_protocol():
    return build_worker_protocol(
        orchestration_id="orch-001",
        work_unit_id="wu-001",
        execution_id="exec-001",
        result_store={
            "directory": "/tmp/project/.adaptive/runs/orch/wu/exec",
            "result_file": "/tmp/project/.adaptive/runs/orch/wu/exec/result.txt",
            "summary_file": "/tmp/project/.adaptive/runs/orch/wu/exec/summary.md",
            "manifest_file": "/tmp/project/.adaptive/runs/orch/wu/exec/manifest.json",
        },
    )


def test_worker_protocol_is_mandatory_and_result_transport_is_not_skill_owned():
    protocol = make_protocol()

    assert protocol["name"] == PROTOCOL_NAME
    assert protocol["version"] == PROTOCOL_VERSION
    assert protocol["mandatory"] is True
    assert "skills" in protocol["non_overridable_by"]
    assert protocol["result_contract"]["authoritative_channel"] == "adaptive-result-store"
    assert protocol["result_contract"]["chat_authoritative"] is False
    assert protocol["result_contract"]["worker_writes_manifest"] is False
    assert protocol["result_contract"]["adaptive_finalizes_manifest"] is True
    assert (
        protocol["result_contract"]["completion_requires"]
        == PROTOCOL_COMPLETION_STATE
    )
    assert protocol["incident_contract"]["worker_may_report_defect_signal"] is True
    assert protocol["incident_contract"]["worker_owns_incident_lifecycle"] is False
    assert protocol["incident_contract"]["adaptive_owns_incident_lifecycle"] is True
    assert protocol["incident_contract"]["adaptive_owns_learning_promotion"] is True


def test_worker_protocol_contract_hash_is_self_verifying():
    protocol = make_protocol()

    assert len(protocol["contract_sha256"]) == 64
    assert validate_worker_protocol(protocol) == protocol


def test_worker_protocol_hash_fails_closed_after_tampering():
    protocol = make_protocol()
    protocol["result_contract"]["chat_authoritative"] = True

    try:
        validate_worker_protocol(protocol)
    except ValueError as exc:
        assert "contract_sha256" in str(exc)
    else:
        raise AssertionError("Expected tampered protocol to fail closed.")
