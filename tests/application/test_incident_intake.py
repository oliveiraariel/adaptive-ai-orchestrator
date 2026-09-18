import json

from application.incident_intake import register_project_incident_intake
from domain.incident import IncidentStatus
from infrastructure.incident_registry import FileIncidentRegistry


def _write_intake(project_root, *, declaration_id="INC-TEST-001"):
    intake = project_root / "incidents" / "intake"
    intake.mkdir(parents=True)
    evidence = intake / f"{declaration_id}.md"
    evidence.write_text("# Intent\n", encoding="utf-8")
    declaration = intake / f"{declaration_id}.json"
    declaration.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "declaration_id": declaration_id,
                "enabled": True,
                "category": "capability-gap",
                "component": "investigation",
                "symptom": "governed investigation capability is not finalized",
                "severity": "MEDIUM",
                "project_id": "adaptive-ai-orchestrator",
                "blocking": False,
                "topics": ["investigation", "learning"],
                "evidence_ref": f"incidents/intake/{declaration_id}.md",
            }
        ),
        encoding="utf-8",
    )


def test_project_intake_becomes_triaged_operational_incident(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_intake(project_root)
    registry = FileIncidentRegistry(tmp_path / "state")

    registered = register_project_incident_intake(project_root, registry)

    assert len(registered) == 1
    incident = registered[0]
    assert incident.status is IncidentStatus.TRIAGED
    assert incident.category == "capability-gap"
    assert "intake:INC-TEST-001" in incident.evidence_refs
    assert "repo:incidents/intake/INC-TEST-001.md" in incident.evidence_refs
    assert len(registry.list_active()) == 1


def test_project_intake_is_idempotent_and_does_not_increment_recurrence(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_intake(project_root)
    registry = FileIncidentRegistry(tmp_path / "state")

    first = register_project_incident_intake(project_root, registry)[0]
    second = register_project_incident_intake(project_root, registry)[0]

    assert second.id == first.id
    assert second.recurrence_count == 1
    assert len(registry.list_all()) == 1


def test_closed_intake_declaration_is_not_recreated(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    _write_intake(project_root)
    registry = FileIncidentRegistry(tmp_path / "state")

    incident = register_project_incident_intake(project_root, registry)[0]
    registry.save(incident.with_status(IncidentStatus.CLOSED))

    registered = register_project_incident_intake(project_root, registry)

    assert len(registered) == 1
    assert registered[0].id == incident.id
    assert registered[0].status is IncidentStatus.CLOSED
    assert registry.list_active() == ()
    assert len(registry.list_all()) == 1
