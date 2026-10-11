from __future__ import annotations

from application.model_quota_continuity import ModelQuotaCooldownStore
from infrastructure.openclaw_gateway_client import (
    GatewayConfig,
    GatewayRun,
    OpenClawGatewayClient,
)


def test_gateway_hands_off_same_work_unit_to_kimi_then_avoids_exhausted_gpt(
    monkeypatch, tmp_path,
) -> None:
    monkeypatch.setenv("ADAPTIVE_ECONOMY_MODEL", "openai/gpt-5.6-terra")
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-primary")
    monkeypatch.setenv("ADAPTIVE_KIMI_ENABLED", "1")
    monkeypatch.setenv("ADAPTIVE_QUOTA_CONTINUITY_PATH", str(tmp_path / "quota.json"))

    client = OpenClawGatewayClient(
        GatewayConfig(
            device_identity_path=str(tmp_path / "identity.json"),
            archive_completed_sessions=False,
            archive_cancelled_sessions=False,
        )
    )
    client._quota_cooldowns.record_quota(
        "openai", "openai/gpt-5.6-terra", "openai:oauth-primary",
        category="quota", subtype="provider_rate_limit_unknown",
    )

    original = GatewayRun(
        run_id="gpt-1",
        session_key="agent:sgfp:orchestrator:unit-1",
        task_payload={
            "task_id": "unit-1",
            "orchestration_id": "orch-1",
            "work_unit_id": "wu-1",
            "context": ["Previously accepted evidence remains valid."],
            "configuration": {
                "agent": "sgfp",
                "model": "openai/gpt-5.6-terra",
                "provider": "openai",
                "auth_profile": "openai:oauth-primary",
                "thinking": "medium",
                "policy_constraints": [],
            },
        },
    )
    kimi = client._build_failover_payload(original, "rate_limit")
    assert kimi is not None
    assert kimi["work_unit_id"] == "wu-1"
    assert kimi["configuration"]["model"] == "moonshot/kimi-k2.7-code"
    assert kimi["adaptive_failover_routes"] == [
        {"model": "openai/gpt-5.6-terra", "auth_profile": "openai:oauth-primary"}
    ]
    assert "new executor session" in kimi["context"][-1]

    # The new Kimi executor fails; do not retry the exhausted GPT OAuth route.
    kimi_run = GatewayRun(
        run_id="kimi-2",
        session_key="agent:sgfp:orchestrator:unit-1:runtime-attempt:2",
        task_payload=kimi,
        runtime_attempt=2,
    )
    alternative = client._build_failover_payload(kimi_run, "unavailable")
    assert alternative is not None
    assert alternative["work_unit_id"] == "wu-1"
    assert alternative["configuration"]["provider"] != "openai"


def test_runtime_retries_receive_distinct_sessions_and_idempotency_keys(
    monkeypatch, tmp_path,
) -> None:
    from infrastructure.result_store import FileResultStore

    store = FileResultStore(root=tmp_path / "results", project_root=tmp_path)
    client = OpenClawGatewayClient(
        GatewayConfig(
            device_identity_path=str(tmp_path / "identity.json"),
            run_identity_path=str(tmp_path / "identities.jsonl"),
            archive_completed_sessions=False,
            archive_cancelled_sessions=False,
        ),
        result_store=store,
    )
    params_seen: list[dict] = []

    def fake_rpc(method: str, params: dict) -> dict:
        if method == "sessions.patch":
            return {"ok": True}
        if method == "agent":
            params_seen.append(params)
            return {"runId": f"run-{len(params_seen)}", "acceptedAt": 123}
        raise AssertionError(method)

    monkeypatch.setattr(client, "_rpc", fake_rpc)
    task = {
        "task_id": "same-task",
        "orchestration_id": "same-orch",
        "work_unit_id": "same-wu",
        "objective": "Implement the remaining checks.",
        "context": [],
        "expected_output": ["verification"],
        "acceptance_criteria": ["tests pass"],
        "configuration": {
            "agent": "sgfp",
            "model": "moonshot/kimi-k2.7-code",
            "provider": "moonshot",
            "auth_profile": "moonshot:api-key",
            "thinking": None,
            "policy_constraints": [],
        },
    }
    first = client._submit_task(task, runtime_attempt=1)
    second = client._submit_task(task, runtime_attempt=2)
    assert client._runs[first].session_key != client._runs[second].session_key
    assert client._runs[first].result_target != client._runs[second].result_target
    assert params_seen[0]["idempotencyKey"] != params_seen[1]["idempotencyKey"]
