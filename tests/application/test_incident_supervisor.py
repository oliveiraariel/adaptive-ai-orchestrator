from application.incident_management import IncidentSentinel
from application.incident_ports import JsonlNotificationOutbox
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


def test_supervision_cycle_publishes_deduplicated_actionable_notification(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    IncidentSentinel(registry).observe_runtime_failure(
        "authoritative result missing after runtime completion",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        runtime="runtime-x",
        blocking=True,
    )
    outbox = JsonlNotificationOutbox(tmp_path / "notifications.jsonl")
    supervisor = IncidentSupervisor(registry, notification_port=outbox)

    directives = supervisor.supervise()
    assert directives
    assert outbox.path.is_file()
    first_count = len(outbox.path.read_text(encoding="utf-8").splitlines())

    supervisor.supervise()
    assert len(outbox.path.read_text(encoding="utf-8").splitlines()) == first_count


def test_supervisor_builds_external_research_request_for_high_pressure_incident(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    IncidentSentinel(registry).observe_runtime_failure(
        "unknown runtime transport contract failure",
        orchestration_id="orch-1",
        work_unit_id="wu-1",
        runtime="runtime-x",
        blocking=True,
    )
    requests = IncidentSupervisor(registry).external_research_requests()
    assert requests
    assert requests[0].incident_id.startswith("INC-")
    assert "authoritative technical evidence" in requests[0].query


class FakeResearchPort:
    def __init__(self):
        self.requests = []

    def research(self, request):
        self.requests.append(request)
        return (f"execution:research-{len(self.requests)}", "source:vendor-doc")


def test_supervisor_executes_research_and_stops_at_attempt_budget(tmp_path):
    registry = FileIncidentRegistry(tmp_path / "incidents")
    incident = IncidentSentinel(registry).observe_runtime_failure(
        "unknown authoritative transport failure",
        orchestration_id="orch",
        work_unit_id="wu",
        runtime="runtime-x",
        blocking=True,
    )
    assert incident is not None
    port = FakeResearchPort()
    supervisor = IncidentSupervisor(
        registry,
        max_research_attempts=2,
    )

    assert supervisor.execute_external_research(port) == (incident.id,)
    assert supervisor.execute_external_research(port) == (incident.id,)
    assert supervisor.execute_external_research(port) == ()

    current = registry.get(incident.id)
    assert current is not None
    assert current.research_attempt_count == 2
    assert "source:vendor-doc" in current.evidence_refs
    directive = supervisor.directives()[0]
    assert directive.action == "research-budget-exhausted"
