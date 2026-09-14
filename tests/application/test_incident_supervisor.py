from application.incident_management import IncidentSentinel
from application.incident_supervisor import IncidentSupervisor
from infrastructure.incident_registry import FileIncidentRegistry


def test_active_incident_is_rendered_as_planner_obligation(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    IncidentSentinel(registry).observe_runtime_failure(
        "runtime completed but result missing",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        runtime="runtime-x",
        blocking=True,
    )
    text = IncidentSupervisor(registry).render_planner_obligations()
    assert "ACTIVE ADAPTIVE INCIDENT OBLIGATIONS" in text
    assert "persistent orchestration obligations" in text
    assert "runtime completed but result missing" in text
    assert "pressure=" in text
