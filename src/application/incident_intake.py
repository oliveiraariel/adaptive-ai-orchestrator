from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from domain.incident import Incident, IncidentSeverity, IncidentStatus
from infrastructure.incident_registry import FileIncidentRegistry


class IncidentIntakeError(ValueError):
    pass


def register_project_incident_intake(
    project_root: Path,
    registry: FileIncidentRegistry,
) -> tuple[Incident, ...]:
    """Promote versioned project incident declarations into live operational state.

    Repository declarations are intake inputs, never authoritative lifecycle state.
    Registration is idempotent: once a declaration has been associated with any
    persisted incident (including a terminal one), normal command execution does not
    recreate or increment it merely because the declaration still exists.
    """

    intake_root = project_root.expanduser().resolve() / "incidents" / "intake"
    if not intake_root.is_dir():
        return ()

    registered: list[Incident] = []
    for path in sorted(intake_root.glob("*.json")):
        payload = _load_declaration(path)
        if not payload["enabled"]:
            continue

        declaration_ref = f"intake:{payload['declaration_id']}"
        existing = next(
            (
                incident
                for incident in registry.list_all()
                if declaration_ref in incident.evidence_refs
            ),
            None,
        )
        if existing is not None:
            registered.append(existing)
            continue

        incident = registry.create_or_recur(
            category=payload["category"],
            component=payload["component"],
            symptom=payload["symptom"],
            severity=payload["severity"],
            source="project-intake",
            project_id=payload["project_id"],
            blocking=payload["blocking"],
            topics=payload["topics"],
        )
        if incident is None:
            raise IncidentIntakeError(
                f"Incident intake declaration was rejected as unsafe: {path}"
            )

        evidence_refs = [declaration_ref]
        if payload["evidence_ref"]:
            evidence_refs.append(f"repo:{payload['evidence_ref']}")

        updated = replace(
            incident,
            status=IncidentStatus.TRIAGED,
            evidence_refs=tuple(dict.fromkeys((*incident.evidence_refs, *evidence_refs))),
        ).touch()
        registry.save(updated)
        registry.append_event(
            updated.id,
            "project_intake_registered",
            {
                "declaration_id": payload["declaration_id"],
                "evidence_ref": payload["evidence_ref"],
            },
        )
        registered.append(updated)

    return tuple(registered)


def _load_declaration(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IncidentIntakeError(f"Cannot load incident intake {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise IncidentIntakeError(f"Incident intake root must be an object: {path}")
    if raw.get("schema_version") != 1:
        raise IncidentIntakeError(f"Unsupported incident intake schema: {path}")

    declaration_id = _required_string(raw, "declaration_id", path)
    category = _required_string(raw, "category", path)
    component = _required_string(raw, "component", path)
    symptom = _required_string(raw, "symptom", path)
    project_id = _required_string(raw, "project_id", path)

    try:
        severity = IncidentSeverity(str(raw.get("severity", "MEDIUM")).upper())
    except ValueError as exc:
        raise IncidentIntakeError(f"Invalid severity in incident intake: {path}") from exc

    topics_raw = raw.get("topics", [])
    if not isinstance(topics_raw, list) or not all(
        isinstance(item, str) and item.strip() for item in topics_raw
    ):
        raise IncidentIntakeError(f"topics must be a list of non-empty strings: {path}")

    evidence_ref = str(raw.get("evidence_ref", "")).strip()
    return {
        "declaration_id": declaration_id,
        "enabled": bool(raw.get("enabled", True)),
        "category": category,
        "component": component,
        "symptom": symptom,
        "severity": severity,
        "project_id": project_id,
        "blocking": bool(raw.get("blocking", False)),
        "topics": tuple(item.strip() for item in topics_raw),
        "evidence_ref": evidence_ref,
    }


def _required_string(payload: dict[str, object], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IncidentIntakeError(f"{key} must be a non-empty string: {path}")
    return value.strip()
