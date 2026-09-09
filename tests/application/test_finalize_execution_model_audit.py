import json

from application.finalize_execution import FinalizeExecution, FinalizeExecutionRequest
from domain.evaluation import EvaluationVerdict
from domain.work_unit import WorkUnit, WorkUnitId
from infrastructure.claim_registry import InMemoryClaimRegistry
from infrastructure.model_routing_audit import ModelRoutingAuditLog


def test_final_verdict_is_persisted_with_execution_id(tmp_path) -> None:
    work_unit = WorkUnit(id=WorkUnitId("wu-a"), objective="Execute A")
    work_unit.mark_ready()
    work_unit.start()
    registry = InMemoryClaimRegistry()
    claim = registry.acquire(work_unit_id="wu-a", claimant_id="scheduler")
    assert claim is not None
    claim = registry.bind_execution(claim, execution_id="openclaw:run-001")
    path = tmp_path / "routing.jsonl"

    FinalizeExecution(
        registry,
        audit_log=ModelRoutingAuditLog(path),
    ).execute(
        FinalizeExecutionRequest(
            work_unit=work_unit,
            claim=claim,
            verdict=EvaluationVerdict.ACCEPTED,
            dependencies=(),
        )
    )

    event = json.loads(path.read_text(encoding="utf-8").strip())
    assert event["event"] == "evaluation-finalized"
    assert event["execution_id"] == "openclaw:run-001"
    assert event["verdict"] == "ACCEPTED"
    assert event["work_unit_state"] == "COMPLETED"
