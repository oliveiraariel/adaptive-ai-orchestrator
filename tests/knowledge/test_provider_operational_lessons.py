import json
from pathlib import Path


def load_lessons() -> dict:
    path = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "provider-operational-lessons.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_policy_activation_lesson_contains_full_owner_auth_sequence() -> None:
    payload = load_lessons()
    lessons = {item["id"]: item for item in payload["lessons"]}

    lesson = lessons["adaptive-policy-activation-owner-auth-order"]

    assert lesson["activation_order"] == [
        "update-adaptive-code",
        "inspect-auth-profiles",
        "set-auth-order",
        "verify-auth-order",
        "apply-adaptive-env",
        "restart-gateway",
        "validate-adaptive-policy",
        "start-fresh-owner-session-if-needed",
        "smoke-test",
        "verify-model-status",
        "start-project-work",
    ]
    assert any("auth order set" in step for step in lesson["remediation"])
    assert any("/model status" in step for step in lesson["remediation"])


def test_policy_change_lesson_distinguishes_owner_and_worker_control_planes() -> None:
    payload = load_lessons()
    lessons = {item["id"]: item for item in payload["lessons"]}

    lesson = lessons["policy-change-two-control-planes"]

    assert "different control planes" in lesson["diagnosis"]
    assert any(
        "owner session" in item.lower()
        for item in lesson["remediation"]
    )
