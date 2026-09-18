from application.incident_ports import (
    IncidentNotification,
    JsonlNotificationOutbox,
)


def test_notification_outbox_deduplicates_stable_incident_action_key(tmp_path):
    outbox = JsonlNotificationOutbox(tmp_path / "notifications.jsonl")
    notification = IncidentNotification(
        key="INC-1:INVESTIGATING:diagnose-now",
        incident_id="INC-1",
        severity="HIGH",
        status="INVESTIGATING",
        action="diagnose-now",
        message="Active incident requires diagnosis.",
    )
    assert outbox.publish(notification) is True
    assert outbox.publish(notification) is False
    assert len(outbox.path.read_text(encoding="utf-8").splitlines()) == 1
