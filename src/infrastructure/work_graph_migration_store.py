from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from application.work_graph_migration import WorkGraphMigrationError


class FileWorkGraphMigrationStore:
    """Immutable migration receipts plus a per-orchestration apply lease."""

    def __init__(
        self,
        *,
        project_root: Path,
        stale_lock_seconds: float = 300.0,
    ) -> None:
        root = project_root.expanduser().resolve()
        if not root.is_dir():
            raise WorkGraphMigrationError(
                f"Adaptive project root does not exist or is not a directory: {root}"
            )
        if stale_lock_seconds <= 0:
            raise ValueError("stale_lock_seconds must be positive.")
        self.project_root = root
        self.root = root / ".adaptive" / "graph-migrations"
        self.stale_lock_seconds = stale_lock_seconds

    @staticmethod
    def _orchestration_digest(orchestration_id: str) -> str:
        value = orchestration_id.strip()
        if not value:
            raise WorkGraphMigrationError("orchestration_id must not be empty.")
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _safe_migration_id(migration_id: str) -> str:
        value = "".join(
            character if character.isalnum() or character in {"-", "_", "."} else "-"
            for character in migration_id.strip()
        ).strip("-")
        if not value:
            raise WorkGraphMigrationError("migration_id must contain a safe identifier.")
        return value[:128]

    def receipt_path(
        self,
        *,
        orchestration_id: str,
        migration_id: str,
        spec_digest: str,
    ) -> Path:
        directory = self.root / self._orchestration_digest(orchestration_id)
        name = (
            f"{self._safe_migration_id(migration_id)}--"
            f"{spec_digest[:16]}.json"
        )
        return directory / name

    def artifact_ref(
        self,
        *,
        orchestration_id: str,
        migration_id: str,
        spec_digest: str,
    ) -> str:
        path = self.receipt_path(
            orchestration_id=orchestration_id,
            migration_id=migration_id,
            spec_digest=spec_digest,
        )
        return str(path.relative_to(self.project_root)).replace("\\", "/")

    def controller_liveness(
        self,
        orchestration_id: str,
    ) -> dict[str, Any] | None:
        digest = self._orchestration_digest(orchestration_id)
        path = (
            self.project_root
            / ".adaptive"
            / "orchestration-liveness"
            / f"{digest}.json"
        )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise WorkGraphMigrationError(
                "Controller liveness record cannot be read safely."
            ) from exc
        if not isinstance(payload, dict):
            raise WorkGraphMigrationError(
                "Controller liveness record is malformed."
            )
        if payload.get("orchestration_id") != orchestration_id:
            raise WorkGraphMigrationError(
                "Controller liveness record identity mismatch."
            )
        return payload

    def controller_quiescence(
        self,
        orchestration_id: str,
        *,
        stale_after_seconds: float = 45.0,
    ) -> tuple[bool, str]:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive.")
        payload = self.controller_liveness(orchestration_id)
        if payload is None:
            return True, "controller-liveness-missing"
        state = str(payload.get("controller_state") or "")
        last = payload.get("last_heartbeat_at")
        if state != "ACTIVE":
            return True, f"controller-state:{state or 'unknown'}"
        if isinstance(last, bool) or not isinstance(last, (int, float)):
            return False, "controller-active-with-invalid-heartbeat"
        age = time.time() - float(last)
        if age <= stale_after_seconds:
            return False, f"controller-active-heartbeat-fresh:{age:.1f}s"
        return True, f"controller-active-heartbeat-stale:{age:.1f}s"

    def write_receipt(
        self,
        *,
        orchestration_id: str,
        migration_id: str,
        spec_digest: str,
        receipt: Mapping[str, Any],
    ) -> str:
        path = self.receipt_path(
            orchestration_id=orchestration_id,
            migration_id=migration_id,
            spec_digest=spec_digest,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = (
            json.dumps(
                dict(receipt),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError:
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise WorkGraphMigrationError(
                    "Existing migration receipt cannot be read."
                ) from exc
            if existing != serialized:
                raise WorkGraphMigrationError(
                    "Immutable migration receipt already exists with different content."
                )
            return str(path.relative_to(self.project_root)).replace("\\", "/")
        except OSError as exc:
            raise WorkGraphMigrationError(
                "Migration receipt could not be created."
            ) from exc

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            raise WorkGraphMigrationError(
                "Migration receipt could not be written durably."
            ) from exc
        return str(path.relative_to(self.project_root)).replace("\\", "/")

    @contextmanager
    def apply_lock(self, orchestration_id: str) -> Iterator[None]:
        directory = self.root / self._orchestration_digest(orchestration_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / ".apply.lock"
        now = time.time()

        try:
            stat = path.stat()
        except FileNotFoundError:
            stat = None
        except OSError as exc:
            raise WorkGraphMigrationError(
                "Migration apply lock cannot be inspected."
            ) from exc

        if stat is not None:
            if now - stat.st_mtime <= self.stale_lock_seconds:
                raise WorkGraphMigrationError(
                    "Another Work Graph migration apply is already in progress."
                )
            try:
                path.unlink()
            except OSError as exc:
                raise WorkGraphMigrationError(
                    "Stale migration apply lock cannot be cleared."
                ) from exc

        payload = {
            "pid": os.getpid(),
            "acquired_at": now,
            "expires_at": now + self.stale_lock_seconds,
            "orchestration_id": orchestration_id,
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise WorkGraphMigrationError(
                "Another Work Graph migration apply is already in progress."
            ) from exc
        except OSError as exc:
            raise WorkGraphMigrationError(
                "Migration apply lock could not be acquired."
            ) from exc

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(payload, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
            yield
        finally:
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                current = None
            if isinstance(current, dict) and current.get("pid") == os.getpid():
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
