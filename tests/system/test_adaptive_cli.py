import json

from adaptive_orchestrator import cli


class FakeGatewayClient:
    last_config = None
    last_result_store = None

    def __init__(self, config, **kwargs):
        type(self).last_config = config
        type(self).last_result_store = kwargs.get("result_store")

    def submit(self, task_payload):
        return "gateway:fake-run"

    def get_status(self, external_id):
        return "COMPLETED"

    def retrieve_result(self, external_id):
        return {"status": "ok", "output": "CLI_OK"}

    def cancel(self, external_id):
        return None


def test_cli_run_invokes_adaptive_core_and_returns_json(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "do-not-print-this")
    monkeypatch.setattr(cli, "OpenClawGatewayClient", FakeGatewayClient)

    exit_code = cli.main(
        [
            "run",
            "--objective",
            "Return CLI_OK.",
            "--agent",
            "main",
            "--accept",
            "CLI_OK",
            "--project-root",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["verdict"] == "ACCEPTED"
    assert payload["work_unit_state"] == "COMPLETED"
    assert payload["output"] == "CLI_OK"
    assert "do-not-print-this" not in captured.out
    assert FakeGatewayClient.last_config.token == "do-not-print-this"
    assert FakeGatewayClient.last_result_store.root == tmp_path.resolve() / ".adaptive" / "runs"


def test_cli_doctor_never_prints_gateway_secret(monkeypatch, capsys) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "secret-value")

    exit_code = cli.main(["doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["gateway_token_available"] is True
    assert "secret-value" not in captured.out


def test_cli_returns_nonzero_when_acceptance_is_not_met(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(cli, "OpenClawGatewayClient", FakeGatewayClient)

    exit_code = cli.main(
        [
            "run",
            "--objective",
            "Return a result.",
            "--accept",
            "MISSING_MARKER",
            "--project-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 3
    assert payload["ok"] is False
    assert payload["verdict"] == "RETURNED"
    assert payload["work_unit_state"] == "REVISION_REQUIRED"
