from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from application.message_protocol import (
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    build_message_reference,
    render_reference_message,
    validate_message_reference,
)


class MessageStoreError(RuntimeError):
    """Raised when an AMEP message violates integrity or storage invariants."""


_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_segment(value: str, *, fallback: str) -> str:
    normalized = _SAFE_SEGMENT.sub("-", value.strip()).strip("-._")
    return normalized[:160] or fallback


@dataclass(frozen=True)
class MessageTarget:
    root: Path
    inbox_root: Path
    message_id: str
    correlation_id: str
    sender: str
    recipient: str
    message_type: str
    schema_name: str
    schema_version: str
    content_type: str
    reply_to: str | None = None
    project_root: Path | None = None

    @property
    def directory(self) -> Path:
        return self.root / _safe_segment(self.message_id, fallback="message")

    @property
    def payload_name(self) -> str:
        if self.content_type == "application/json":
            return "payload.json"
        if self.content_type == "text/markdown":
            return "payload.md"
        return "payload.txt"

    @property
    def payload_path(self) -> Path:
        return self.directory / self.payload_name

    @property
    def manifest_path(self) -> Path:
        return self.directory / "manifest.json"

    @property
    def reference_path(self) -> Path:
        return self.directory / "reference.json"

    @property
    def events_dir(self) -> Path:
        return self.directory / "events"

    @property
    def inbox_path(self) -> Path:
        return (
            self.inbox_root
            / _safe_segment(self.recipient, fallback="recipient")
            / f"{_safe_segment(self.message_id, fallback='message')}.ref.json"
        )


@dataclass(frozen=True)
class StoredMessage:
    content: str
    sha256: str
    byte_length: int
    manifest: dict[str, Any]
    reference: dict[str, Any]

    def json(self) -> object:
        if self.manifest.get("payload", {}).get("content_type") != "application/json":
            raise MessageStoreError("AMEP payload is not application/json.")
        try:
            return json.loads(self.content)
        except json.JSONDecodeError as exc:
            raise MessageStoreError("AMEP JSON payload is invalid.") from exc


class FileMessageStore:
    """Project-local durable data plane for Adaptive component communication.

    AMEP separates the large authoritative payload from the small control-plane
    reference. Payload and manifest are written atomically; the reference/inbox
    entry is published last. Chat/runtime messages carry only the reference.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        project_root: str | Path | None = None,
        manage_git_exclude: bool = True,
    ) -> None:
        configured_root = (
            os.environ.get("ADAPTIVE_MESSAGE_STORE")
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
                raise MessageStoreError(
                    f"Adaptive project root does not exist or is not a directory: {resolved_project}"
                )

        if root is not None:
            resolved_root = Path(root).expanduser().resolve()
        elif configured_root:
            resolved_root = Path(configured_root).expanduser().resolve()
        else:
            if resolved_project is None:
                resolved_project = Path.cwd().resolve()
            resolved_root = resolved_project / ".adaptive" / "messages"

        self.project_root = resolved_project
        self.root = resolved_root
        self.inbox_root = self.root.parent / "inbox"

        if root is None and not configured_root:
            assert self.project_root is not None
            expected = (self.project_root / ".adaptive" / "messages").resolve()
            if self.root.resolve() != expected:
                raise MessageStoreError("Project-local Message Store escaped the project root.")
            if manage_git_exclude:
                self._ensure_git_exclude(self.project_root)

    def prepare_target(
        self,
        *,
        sender: str,
        recipient: str,
        message_type: str,
        schema_name: str,
        schema_version: str = "1",
        correlation_id: str,
        content_type: str = "application/json",
        message_id: str | None = None,
        reply_to: str | None = None,
    ) -> MessageTarget:
        for name, value in {
            "sender": sender,
            "recipient": recipient,
            "message_type": message_type,
            "schema_name": schema_name,
            "schema_version": schema_version,
            "correlation_id": correlation_id,
        }.items():
            if not isinstance(value, str) or not value.strip():
                raise MessageStoreError(f"AMEP {name} must be a non-empty string.")
        if content_type not in {"application/json", "text/plain", "text/markdown"}:
            raise MessageStoreError("AMEP content_type is unsupported.")

        identifier = message_id or f"msg_{uuid.uuid4().hex}"
        target = MessageTarget(
            root=self.root,
            inbox_root=self.inbox_root,
            message_id=identifier,
            correlation_id=correlation_id,
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            schema_name=schema_name,
            schema_version=schema_version,
            content_type=content_type,
            reply_to=reply_to,
            project_root=self.project_root,
        )
        directory = target.directory.resolve()
        if not directory.is_relative_to(self.root.resolve()):
            raise MessageStoreError("AMEP target escaped the Message Store root.")
        target.directory.mkdir(parents=True, exist_ok=True)
        target.events_dir.mkdir(parents=True, exist_ok=True)
        return target

    def publish_json(
        self,
        *,
        sender: str,
        recipient: str,
        message_type: str,
        schema_name: str,
        payload: object,
        correlation_id: str,
        schema_version: str = "1",
        reply_to: str | None = None,
    ) -> StoredMessage:
        try:
            content = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise MessageStoreError("AMEP JSON payload is not serializable.") from exc
        target = self.prepare_target(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            schema_name=schema_name,
            schema_version=schema_version,
            correlation_id=correlation_id,
            content_type="application/json",
            reply_to=reply_to,
        )
        self._atomic_write_text(target.payload_path, content)
        return self.finalize_external(target)

    def publish_text(
        self,
        *,
        sender: str,
        recipient: str,
        message_type: str,
        schema_name: str,
        content: str,
        correlation_id: str,
        schema_version: str = "1",
        content_type: str = "text/plain",
        reply_to: str | None = None,
    ) -> StoredMessage:
        if not isinstance(content, str):
            raise MessageStoreError("AMEP text payload must be a string.")
        target = self.prepare_target(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            schema_name=schema_name,
            schema_version=schema_version,
            correlation_id=correlation_id,
            content_type=content_type,
            reply_to=reply_to,
        )
        self._atomic_write_text(target.payload_path, content)
        return self.finalize_external(target)

    def finalize_external(self, target: MessageTarget) -> StoredMessage:
        """Finalize an externally-written payload; Adaptive owns manifest/ref metadata."""

        try:
            content = target.payload_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise MessageStoreError("AMEP external writer completed without final payload.") from exc
        except (OSError, UnicodeError) as exc:
            raise MessageStoreError("AMEP payload is unavailable or invalid UTF-8.") from exc

        if target.content_type == "application/json":
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                raise MessageStoreError("AMEP application/json payload is invalid.") from exc

        raw = content.encode("utf-8")
        payload_sha = hashlib.sha256(raw).hexdigest()
        manifest: dict[str, Any] = {
            "protocol": PROTOCOL_NAME,
            "protocol_version": PROTOCOL_VERSION,
            "message_id": target.message_id,
            "correlation_id": target.correlation_id,
            "sender": target.sender,
            "recipient": target.recipient,
            "message_type": target.message_type,
            "schema": {
                "name": target.schema_name,
                "version": target.schema_version,
            },
            "payload": {
                "file": target.payload_name,
                "content_type": target.content_type,
                "bytes": len(raw),
                "sha256": payload_sha,
            },
            "reply_to": target.reply_to,
            "complete": True,
            "created_at_unix_ns": time.time_ns(),
        }
        manifest_text = json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self._atomic_write_text(target.manifest_path, manifest_text)
        manifest_sha = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()

        reference = build_message_reference(
            message_id=target.message_id,
            correlation_id=target.correlation_id,
            sender=target.sender,
            recipient=target.recipient,
            message_type=target.message_type,
            manifest=str(target.manifest_path),
            manifest_sha256=manifest_sha,
        )
        reference_text = json.dumps(
            reference,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self._atomic_write_text(target.reference_path, reference_text)
        # Inbox publication is the final visibility step.
        target.inbox_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(target.inbox_path, reference_text)
        self._record_event(target, "PUBLISHED", target.sender)

        return self.read_reference(reference)

    def read_reference(self, reference: object) -> StoredMessage:
        try:
            validated = validate_message_reference(reference)
        except ValueError as exc:
            raise MessageStoreError(str(exc)) from exc

        manifest_path = Path(validated["manifest"]).expanduser().resolve()
        if not manifest_path.is_relative_to(self.root.resolve()):
            raise MessageStoreError("AMEP manifest path escaped the configured Message Store.")

        try:
            manifest_text = manifest_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise MessageStoreError("AMEP manifest is unavailable or invalid UTF-8.") from exc

        manifest_sha = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
        if manifest_sha != validated["manifest_sha256"].lower():
            raise MessageStoreError("AMEP manifest SHA-256 does not match the reference.")

        try:
            manifest = json.loads(manifest_text)
        except json.JSONDecodeError as exc:
            raise MessageStoreError("AMEP manifest is invalid JSON.") from exc
        if not isinstance(manifest, dict):
            raise MessageStoreError("AMEP manifest root must be an object.")
        if manifest.get("protocol") != PROTOCOL_NAME:
            raise MessageStoreError("AMEP manifest protocol is unsupported.")
        if manifest.get("protocol_version") != PROTOCOL_VERSION:
            raise MessageStoreError("AMEP manifest protocol_version is unsupported.")
        if manifest.get("complete") is not True:
            raise MessageStoreError("AMEP manifest is not complete.")

        for key in (
            "message_id",
            "correlation_id",
            "sender",
            "recipient",
            "message_type",
        ):
            if manifest.get(key) != validated.get(key):
                raise MessageStoreError(f"AMEP manifest {key} does not match reference.")

        schema = manifest.get("schema")
        if not isinstance(schema, dict):
            raise MessageStoreError("AMEP manifest schema metadata is missing.")
        if not isinstance(schema.get("name"), str) or not schema["name"].strip():
            raise MessageStoreError("AMEP schema name is invalid.")
        if not isinstance(schema.get("version"), str) or not schema["version"].strip():
            raise MessageStoreError("AMEP schema version is invalid.")

        payload = manifest.get("payload")
        if not isinstance(payload, dict):
            raise MessageStoreError("AMEP manifest payload metadata is missing.")
        filename = payload.get("file")
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise MessageStoreError("AMEP payload file name is invalid.")
        payload_path = manifest_path.parent / filename
        if not payload_path.resolve().is_relative_to(manifest_path.parent.resolve()):
            raise MessageStoreError("AMEP payload path escaped its message directory.")
        try:
            content = payload_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise MessageStoreError("AMEP payload is unavailable or invalid UTF-8.") from exc

        raw = content.encode("utf-8")
        expected_bytes = payload.get("bytes")
        expected_sha = payload.get("sha256")
        if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes < 0:
            raise MessageStoreError("AMEP payload bytes metadata is invalid.")
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha):
            raise MessageStoreError("AMEP payload sha256 metadata is invalid.")
        actual_sha = hashlib.sha256(raw).hexdigest()
        if len(raw) != expected_bytes:
            raise MessageStoreError("AMEP payload byte length does not match manifest.")
        if actual_sha != expected_sha.lower():
            raise MessageStoreError("AMEP payload SHA-256 does not match manifest.")

        content_type = payload.get("content_type")
        if content_type == "application/json":
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                raise MessageStoreError("AMEP JSON payload is invalid.") from exc

        return StoredMessage(
            content=content,
            sha256=actual_sha,
            byte_length=len(raw),
            manifest=manifest,
            reference=validated,
        )

    def list_inbox(self, recipient: str) -> tuple[dict[str, Any], ...]:
        directory = self.inbox_root / _safe_segment(recipient, fallback="recipient")
        if not directory.exists():
            return ()
        references: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.ref.json")):
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
                references.append(validate_message_reference(candidate))
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                continue
        return tuple(references)

    def acknowledge(self, reference: object, *, component: str, event: str = "CONSUMED") -> None:
        stored = self.read_reference(reference)
        target = self._target_from_manifest(stored.manifest)
        self._record_event(target, event.upper(), component)

    @staticmethod
    def reference_message(reference: object) -> str:
        return render_reference_message(reference)

    @staticmethod
    def external_writer_instructions(target: MessageTarget) -> str:
        return (
            "AMEP v1 authoritative payload rule. Write the COMPLETE message payload "
            f"to {target.payload_path}.tmp first, then atomically rename it to "
            f"{target.payload_path} only when final. Do not create or modify "
            "manifest.json, reference.json, or inbox entries; Adaptive finalizes "
            "integrity metadata and publishes the MESSAGE_REF after runtime completion. "
            "Chat/history is progress-only and is not authoritative."
        )

    def _target_from_manifest(self, manifest: dict[str, Any]) -> MessageTarget:
        schema = manifest["schema"]
        payload = manifest["payload"]
        return MessageTarget(
            root=self.root,
            inbox_root=self.inbox_root,
            message_id=manifest["message_id"],
            correlation_id=manifest["correlation_id"],
            sender=manifest["sender"],
            recipient=manifest["recipient"],
            message_type=manifest["message_type"],
            schema_name=schema["name"],
            schema_version=schema["version"],
            content_type=payload["content_type"],
            reply_to=manifest.get("reply_to"),
            project_root=self.project_root,
        )

    def _record_event(self, target: MessageTarget, event: str, component: str) -> None:
        target.events_dir.mkdir(parents=True, exist_ok=True)
        event_id = f"{time.time_ns()}-{_safe_segment(event.lower(), fallback='event')}.json"
        payload = {
            "protocol": PROTOCOL_NAME,
            "protocol_version": PROTOCOL_VERSION,
            "message_id": target.message_id,
            "event": event,
            "component": component,
            "timestamp_unix_ns": time.time_ns(),
        }
        self._atomic_write_text(
            target.events_dir / event_id,
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)

    @staticmethod
    def _ensure_git_exclude(project_root: Path) -> None:
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
            return
