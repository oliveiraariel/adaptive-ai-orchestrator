import json

from application.worker_protocol import build_worker_protocol
from infrastructure.openclaw_gateway_client import OpenClawGatewayClient


def test_worker_message_includes_selected_resource_configuration() -> None:
    message = OpenClawGatewayClient._build_message(
        {
            "worker_protocol": build_worker_protocol(
                orchestration_id="orch-1",
                work_unit_id="wu-frontend",
                execution_id="exec-1",
                result_store={
                    "directory": "/tmp/result",
                    "result_file": "/tmp/result/result.txt",
                    "summary_file": "/tmp/result/summary.md",
                    "manifest_file": "/tmp/result/manifest.json",
                },
            ),
            "task_id": "task-1",
            "work_unit_id": "wu-frontend",
            "objective": "Implement responsive account screen",
            "scope": "frontend",
            "context": [],
            "inputs": [],
            "artifacts": [],
            "decisions": [],
            "dependencies": [],
            "constraints": [],
            "expected_output": ["implementation"],
            "acceptance_criteria": ["runtime-completed"],
            "configuration": {
                "agent": "sgfp",
                "skills": ["web-frontend-design", "implementation"],
                "model": None,
                "provider": None,
                "tools": [],
                "runtime": "openclaw",
                "policy_constraints": [],
            },
        }
    )

    decoded = json.loads(message)

    assert message.startswith('{"worker_protocol":')
    assert decoded["worker_protocol"]["mandatory"] is True
    assert decoded["configuration"]["agent"] == "sgfp"
    assert decoded["configuration"]["skills"] == [
        "web-frontend-design",
        "implementation",
    ]
