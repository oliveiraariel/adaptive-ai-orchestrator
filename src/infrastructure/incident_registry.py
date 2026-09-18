from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from threading import RLock
from typing import Iterable
from uuid import uuid4

from domain.incident import Incident, IncidentSeverity, IncidentStatus, utc_now


_SENSITIVE = (
    "authorization:",
    "bearer ",
    "api_key",
    "api-key",
    "password=",
    "secret=",
    "sk-",
)
_SPACE_RE = re.compile(r"\s+")


def canonical_incident_root() -> Path:
    override = os.environ.get("ADAPTIVE_INCIDENT_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    state_home = os.environ.get("XDG_STATE_HOME", "").strip()
    root = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return root / "adaptive-ai-orchestrator" / "incidents"


class IncidentRegistryError(RuntimeError):
    pass


class FileIncidentRegistry:
    """Persistent operational incident registry.

    The registry stores bounded summaries and references, not raw prompts, source
    payloads, credentials, chain-of-thought, or arbitrary worker output.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or canonical_incident_root()
        self._lock = RLock()

    def create_or_recur(
        self,
        *,
        category: str,
        component: str,
        symptom: str,
        severity: IncidentSeverity,
        source: str,
        project_id: str = "",
        orchestration_id: str = "",
        work_unit_id: str = "",
        execution_id: str = "",
        runtime: str = "",
        repository: str = "",
        workspace: str = "",
        project_version: str = "",
        branch: str = "",
        baseline: str = "",
        session_id: str = "",
        adapter: str = "",
        remediation_target: str = "",
        validation_target: str = "",
        source_of_truth_refs: Iterable[str] = (),
        blocking: bool = False,
        topics: Iterable[str] = (),
    ) -> Incident | None:
        safe = {
            "category": self._safe(category, 80),
            "component": self._safe(component, 120),
            "symptom": self._safe(symptom, 500),
            "source": self._safe(source, 80),
            "project_id": self._safe(project_id, 120),
            "orchestration_id": self._safe(orchestration_id, 160),
            "work_unit_id": self._safe(work_unit_id, 160),
            "execution_id": self._safe(execution_id, 200),
            "runtime": self._safe(runtime, 80),
            "repository": self._safe(repository, 240),
            "workspace": self._safe(workspace, 240),
            "project_version": self._safe(project_version, 120),
            "branch": self._safe(branch, 160),
            "baseline": self._safe(baseline, 160),
            "session_id": self._safe(session_id, 160),
            "adapter": self._safe(adapter, 120),
            "remediation_target": self._safe(remediation_target, 240),
            "validation_target": self._safe(validation_target, 240),
        }
        if not safe["category"] or not safe["component"] or not safe["symptom"] or not safe["source"]:
            return None
        fingerprint = self._fingerprint(
            safe["category"],
            safe["component"],
            safe["symptom"],
            safe["project_id"],
        )
        with self._lock:
            existing = self.find_active_by_fingerprint(fingerprint)
            if existing is not None:
                updated = existing.touch(
                    recurrence_count=existing.recurrence_count + 1,
                    severity=max(existing.severity, severity, key=self._severity_rank),
                    blocking=existing.blocking or blocking,
                    orchestration_id=safe["orchestration_id"] or existing.orchestration_id,
                    work_unit_id=safe["work_unit_id"] or existing.work_unit_id,
                    execution_id=safe["execution_id"] or existing.execution_id,
                    runtime=safe["runtime"] or existing.runtime,
                    repository=safe["repository"] or existing.repository,
                    workspace=safe["workspace"] or existing.workspace,
                    project_version=safe["project_version"] or existing.project_version,
                    branch=safe["branch"] or existing.branch,
                    baseline=safe["baseline"] or existing.baseline,
                    session_id=safe["session_id"] or existing.session_id,
                    adapter=safe["adapter"] or existing.adapter,
                    remediation_target=safe["remediation_target"] or existing.remediation_target,
                    validation_target=safe["validation_target"] or existing.validation_target,
                    source_of_truth_refs=tuple(dict.fromkeys((*existing.source_of_truth_refs, *self._safe_refs(source_of_truth_refs)))),
                    topics=tuple(dict.fromkeys((*existing.topics, *self._safe_topics(topics)))),
                )
                self.save(updated)
                self.append_event(updated.id, "incident_recurred", {
                    "recurrence_count": updated.recurrence_count,
                    "source": safe["source"],
                })
                return updated

            incident = Incident(
                id=f"INC-{utc_now()[:10].replace('-', '')}-{uuid4().hex[:10]}",
                fingerprint=fingerprint,
                title=f"{safe['component']}: {safe['category']}",
                category=safe["category"],
                component=safe["component"],
                symptom=safe["symptom"],
                severity=severity,
                source=safe["source"],
                project_id=safe["project_id"],
                orchestration_id=safe["orchestration_id"],
                work_unit_id=safe["work_unit_id"],
                execution_id=safe["execution_id"],
                runtime=safe["runtime"],
                repository=safe["repository"],
                workspace=safe["workspace"],
                project_version=safe["project_version"],
                branch=safe["branch"],
                baseline=safe["baseline"],
                session_id=safe["session_id"],
                adapter=safe["adapter"],
                remediation_target=safe["remediation_target"],
                validation_target=safe["validation_target"],
                source_of_truth_refs=self._safe_refs(source_of_truth_refs),
                blocking=blocking,
                topics=self._safe_topics(topics),
            )
            self.save(incident)
            self.append_event(incident.id, "incident_detected", {
                "category": incident.category,
                "component": incident.component,
                "severity": incident.severity.value,
                "source": incident.source,
            })
            return incident

    def save(self, incident: Incident) -> None:
        directory = self.root / incident.id
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = directory / "incident.json"
        tmp = directory / "incident.json.tmp"
        tmp.write_text(
            json.dumps(incident.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)

    def get(self, incident_id: str) -> Incident | None:
        path = self.root / incident_id / "incident.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            return Incident.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return None

    def list_all(self) -> tuple[Incident, ...]:
        incidents: list[Incident] = []
        if not self.root.is_dir():
            return ()
        for item in self.root.iterdir():
            if not item.is_dir():
                continue
            incident = self.get(item.name)
            if incident is not None:
                incidents.append(incident)
        incidents.sort(key=lambda item: (item.detected_at, item.id))
        return tuple(incidents)

    def list_active(self) -> tuple[Incident, ...]:
        incidents = [incident for incident in self.list_all() if incident.is_active]
        incidents.sort(key=lambda item: (-self._severity_rank(item.severity), item.detected_at, item.id))
        return tuple(incidents)


    def find_active_by_work_unit(
        self,
        *,
        orchestration_id: str,
        work_unit_id: str,
    ) -> Incident | None:
        for incident in self.list_active():
            if (
                incident.orchestration_id == orchestration_id
                and incident.work_unit_id == work_unit_id
            ):
                return incident
        return None

    def read_events(self, incident_id: str) -> tuple[dict[str, object], ...]:
        path = self.root / incident_id / "timeline.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ()
        events: list[dict[str, object]] = []
        for raw in lines:
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                events.append(item)
        return tuple(events)

    def find_active_by_fingerprint(self, fingerprint: str) -> Incident | None:
        for incident in self.list_active():
            if incident.fingerprint == fingerprint:
                return incident
        return None

    def append_event(self, incident_id: str, event_type: str, fields: dict[str, object] | None = None) -> None:
        incident = self.get(incident_id)
        if incident is None and event_type != "incident_detected":
            raise IncidentRegistryError(f"Unknown incident: {incident_id}")
        directory = self.root / incident_id
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload: dict[str, object] = {
            "timestamp": utc_now(),
            "event_type": self._safe(event_type, 80),
        }
        for key, value in (fields or {}).items():
            if isinstance(value, (bool, int, float)):
                payload[str(key)[:80]] = value
            elif isinstance(value, str):
                clean = self._safe(value, 500)
                if clean:
                    payload[str(key)[:80]] = clean
        with (directory / "timeline.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")

    @staticmethod
    def _fingerprint(category: str, component: str, symptom: str, project_id: str) -> str:
        normalized = "|".join(
            _SPACE_RE.sub(" ", value.casefold().strip())
            for value in (category, component, symptom, project_id)
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _severity_rank(severity: IncidentSeverity) -> int:
        return {
            IncidentSeverity.LOW: 1,
            IncidentSeverity.MEDIUM: 2,
            IncidentSeverity.HIGH: 3,
            IncidentSeverity.CRITICAL: 4,
        }[severity]

    @classmethod
    def _safe(cls, value: str, limit: int) -> str:
        if not isinstance(value, str):
            return ""
        clean = _SPACE_RE.sub(" ", value.strip())[:limit]
        lowered = clean.casefold()
        if any(fragment in lowered for fragment in _SENSITIVE):
            return ""
        return clean

    @classmethod
    def _safe_refs(cls, values: Iterable[str]) -> tuple[str, ...]:
        refs = []
        for value in values:
            clean = cls._safe(str(value), 300)
            if clean and clean not in refs:
                refs.append(clean)
        return tuple(refs[:32])

    @classmethod
    def _safe_topics(cls, values: Iterable[str]) -> tuple[str, ...]:
        topics = []
        for value in values:
            clean = cls._safe(str(value), 80)
            if clean and clean not in topics:
                topics.append(clean)
        return tuple(topics[:16])
