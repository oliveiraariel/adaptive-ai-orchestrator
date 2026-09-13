import json

from adaptive_orchestrator import cli


class MultiFakeGatewayClient:
    last_config = None
    counter = 0

    def __init__(self, config):
        type(self).last_config = config

    def submit(self, task_payload):
        type(self).counter += 1
        return f"gateway:multi-{type(self).counter}"

    def get_status(self, external_id):
        return "COMPLETED"

    def retrieve_result(self, external_id):
        return {"status": "ok", "output": f"done:{external_id}"}

    def cancel(self, external_id):
        return None


def test_cli_orchestrate_executes_static_parallel_plan(monkeypatch, tmp_path, capsys) -> None:
    MultiFakeGatewayClient.counter = 0
    monkeypatch.setattr(cli, "OpenClawGatewayClient", MultiFakeGatewayClient)

    registry = tmp_path / "skills.json"
    registry.write_text(
        json.dumps({"schema_version": 1, "skills": []}),
        encoding="utf-8",
    )
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "summary": "two independent workers",
                "work_units": [
                    {
                        "id": "a",
                        "objective": "Execute a",
                        "expected_output": ["result"],
                        "acceptance_criteria": ["runtime-completed"],
                    },
                    {
                        "id": "b",
                        "objective": "Execute b",
                        "expected_output": ["result"],
                        "acceptance_criteria": ["runtime-completed"],
                    },
                ],
                "dependencies": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "orchestrate",
            "--objective",
            "Execute two independent test workers.",
            "--plan-file",
            str(plan),
            "--skill-registry",
            str(registry),
            "--max-concurrency",
            "2",
        ]
    )

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "COMPLETED"
    assert payload["work_unit_count"] == 2
    assert payload["max_parallelism_observed"] == 2
    assert payload["stop_reasons"] == []
    assert payload["requires_human_decision"] is False
    assert payload["waves"][0]["selected_work_unit_ids"] == ["a", "b"]
