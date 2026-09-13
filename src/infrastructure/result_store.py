from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ResultStoreError(RuntimeError):
    """Raised when a persisted Adaptive result violates the store contract."""


_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_segment(value: str, *, fallback: str) -> str:
    normalized = _SAFE_SEGMENT.sub("-", value.strip()).strip("-._")
    return normalized[:120] or fallback


@dataclass(frozen=True)
class ResultStoreTarget:
    root: Path
    orchestration_id: str
    work_unit_id: str
    execution_id: str
    project_root: Path | None = None

    @property
    def directory(self) -> Path:
        return (
            self.root
            / _safe_segment(self.orchestration_id, fallback="orchestration")
            / _safe_segment(self.work_unit_id, fallback="work-unit")
            / _safe_segment(self.execution_id, fallback="execution")
        )

    @property
    def result_path(self) -> Path:
        return self.directory / "result.txt"

    @property
    def summary_path(self) -> Path:
        return self.directory / "summary.md"

    @property
    def manifest_path(self) -> Path:
        return self.directory / "manifest.json"

    def as_payload(self) -> dict[str, str | int | None]:
        return {
            "schema_version": 1,
            "orchestration_id": self.orchestration_id,
            "work_unit_id": self.work_unit_id,
            "execution_id": self.execution_id,
            "project_root": str(self.project_root) if self.project_root is not None else None,
            "directory": str(self.directory),
            "result_file": str(self.result_path),
            "summary_file": str(self.summary_path),
            "manifest_file": str(self.manifest_path),
        }


@dataclass(frozen=True)
class StoredResult:
    content: str
    sha256: str
    byte_length: int
    summary: str | None
    manifest: dict[str, Any]


class FileResultStore:
    """Durable file-backed handoff channel for Adaptive worker results.

    Runtime conversations remain useful for progress and human-readable summaries,
    but the authoritative machine-readable result is published here. The manifest
    is the completion sentinel and must be written last.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        project_root: str | Path | None = None,
        manage_git_exclude: bool = True,
    ) -> None:
        configured_root = (
            os.environ.get("ADAPTIVE_RESULT_STORE")
            if root is None and project_root is None
            else None
        )
        configured_project = (
            os.environ.get("ADAPTIVE_PROJECT_ROOT")
            if root is None and project_root is None
            else None
        )

        resolved_project: Path | None = None
        if project_root is not None or configured_project:
            resolved_project = Path(project_root or configured_project or ".").expanduser().resolve()
            if not resolved_project.is_dir():
                raise ResultStoreError(
                    f"Adaptive project root does not exist or is not a directory: {resolved_project}"
                )

        if root is not None:
            resolved_root = Path(root).expanduser().resolve()
        elif configured_root:
            resolved_root = Path(configured_root).expanduser().resolve()
        else:
            if resolved_project is None:
                resolved_project = Path.cwd().resolve()
            resolved_root = resolved_project / ".adaptive" / "runs"

        self.project_root = resolved_project
        self.root = resolved_root

        if root is None and not configured_root:
            assert self.project_root is not None
            expected = (self.project_root / ".adaptive" / "runs").resolve()
            if self.root.resolve() != expected:
                raise ResultStoreError("Project-local result store escaped the project root.")
            if manage_git_exclude:
                self._ensure_git_exclude(self.project_root)

    def prepare_target(
        self,
        *,
        orchestration_id: str,
        work_unit_id: str,
        execution_id: str,
    ) -> ResultStoreTarget:
        target = ResultStoreTarget(
            root=self.root,
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            execution_id=execution_id,
            project_root=self.project_root,
        )
        root = self.root.resolve()
        directory = target.directory.resolve()
        if not directory.is_relative_to(root):
            raise ResultStoreError("Result target escaped the configured result-store root.")
        target.directory.mkdir(parents=True, exist_ok=True)
        return target

    def publish(
        self,
        target: ResultStoreTarget,
        *,
        content: str,
        summary: str | None = None,
    ) -> StoredResult:
        """Publish a result atomically; useful for deterministic runtimes/tests."""

        if not isinstance(content, str):
            raise ResultStoreError("Result content must be UTF-8 text.")
        target.directory.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(target.result_path, content)
        if summary is not None:
            self._atomic_write_text(target.summary_path, summary)

        raw = content.encode("utf-8")
        manifest = {
            "schema_version": 1,
            "orchestration_id": target.orchestration_id,
            "work_unit_id": target.work_unit_id,
            "execution_id": target.execution_id,
            "complete": True,
            "result_file": target.result_path.name,
            "summary_file": target.summary_path.name if summary is not None else None,
            "result_bytes": len(raw),
            "result_sha256": hashlib.sha256(raw).hexdigest(),
        }
        self._atomic_write_text(
            target.manifest_path,
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
        stored = self.read_result(target)
        if stored is None:  # pragma: no cover - defensive invariant
            raise ResultStoreError("Published result is not recoverable.")
        return stored

    def read_result(self, target: ResultStoreTarget) -> StoredResult | None:
        """Return a verified complete result, or None while no manifest exists."""

        if not target.manifest_path.exists():
            return None

        try:
            manifest = json.loads(target.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ResultStoreError("Result manifest is unreadable or invalid JSON.") from exc
        if not isinstance(manifest, dict):
            raise ResultStoreError("Result manifest root must be an object.")

        expected = {
            "orchestration_id": target.orchestration_id,
            "work_unit_id": target.work_unit_id,
            "execution_id": target.execution_id,
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise ResultStoreError(f"Result manifest {key} does not match the execution target.")
        if manifest.get("schema_version") != 1:
            raise ResultStoreError("Unsupported result manifest schema_version.")
        if manifest.get("complete") is not True:
            raise ResultStoreError("Result manifest is not marked complete.")

        result_name = manifest.get("result_file")
        if result_name != target.result_path.name:
            raise ResultStoreError("Result manifest must reference result.txt.")
        try:
            content = target.result_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ResultStoreError("Result manifest exists but result.txt is unavailable.") from exc

        raw = content.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        expected_bytes = manifest.get("result_bytes")
        if expected_bytes is not None and expected_bytes != len(raw):
            raise ResultStoreError("Result byte length does not match manifest.")
        expected_digest = manifest.get("result_sha256")
        if expected_digest is not None and expected_digest != digest:
            raise ResultStoreError("Result SHA-256 does not match manifest.")

        summary: str | None = None
        summary_name = manifest.get("summary_file")
        if summary_name is not None:
            if summary_name != target.summary_path.name:
                raise ResultStoreError("Result manifest must reference summary.md.")
            try:
                summary = target.summary_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise ResultStoreError("Manifest references summary.md but it is unavailable.") from exc

        return StoredResult(
            content=content,
            sha256=digest,
            byte_length=len(raw),
            summary=summary,
            manifest=manifest,
        )

    @staticmethod
    def worker_instructions(target: ResultStoreTarget) -> str:
        payload = target.as_payload()
        manifest_example = {
            "schema_version": 1,
            "orchestration_id": target.orchestration_id,
            "work_unit_id": target.work_unit_id,
            "execution_id": target.execution_id,
            "complete": True,
            "result_file": "result.txt",
            "summary_file": "summary.md",
        }
        return (
            "Adaptive authoritative-result contract. This transport-only write is explicitly "
            "authorized inside the project's private .adaptive runtime area and is not a source "
            "or product-file modification. Put the COMPLETE authoritative "
            "result requested by the task in the result store, not in chat/history. "
            f"Project root: {payload['project_root'] or 'not-declared'}. "
            f"Directory: {payload['directory']}. Do not write result-store data outside this directory. "
            f"Write {payload['result_file']}.tmp first, then atomically rename it to "
            f"{payload['result_file']}. Optionally publish a concise summary through "
            f"{payload['summary_file']}.tmp -> {payload['summary_file']}. "
            "Finally write manifest.json.tmp and atomically rename it to manifest.json LAST. "
            "The manifest must be JSON matching this identity and complete=true: "
            f"{json.dumps(manifest_example, ensure_ascii=False, separators=(',', ':'))}. "
            "Do not fabricate completion if the result file was not written. After publication, "
            "keep the conversational reply short (for example ADAPTIVE_RESULT_WRITTEN) because "
            "conversation text is progress/summary only and is not the authoritative payload."
        )

    @staticmethod
    def _ensure_git_exclude(project_root: Path) -> None:
        """Keep project-local runtime state out of Git without editing tracked files."""

        try:
            completed = subprocess.run(
                ["git", "-C", str(project_root), "rev-parse", "--git-path", "info/exclude"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return
        if completed.returncode != 0:
            return

        raw_path = completed.stdout.strip()
        if not raw_path:
            return
        exclude_path = Path(raw_path)
        if not exclude_path.is_absolute():
            exclude_path = (project_root / exclude_path).resolve()

        rule = "/.adaptive/"
        try:
            exclude_path.parent.mkdir(parents=True, exist_ok=True)
            current = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
            existing = {
                line.strip()
                for line in current.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
            if rule in existing or ".adaptive/" in existing:
                return
            prefix = "" if not current or current.endswith("\n") else "\n"
            with exclude_path.open("a", encoding="utf-8") as handle:
                handle.write(prefix + "# Adaptive AI Orchestrator project-local runtime state\n" + rule + "\n")
        except OSError:
            # Git exclusion is hygiene, not a result-delivery prerequisite.
            return

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, path)
