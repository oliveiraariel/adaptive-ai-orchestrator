import json

from infrastructure.openclaw_gateway_client import OpenClawGatewayClient


def test_worker_message_includes_selected_resource_configuration() -> None:
    message = OpenClawGatewayClient._build_message(
        {
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

    assert decoded["configuration"]["agent"] == "sgfp"
    assert decoded["configuration"]["skills"] == [
        "web-frontend-design",
        "implementation",
    ]
