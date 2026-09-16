from __future__ import annotations

from typing import Any, Protocol


class ProjectOrchestrationCheckpointStore(Protocol):
    """Durable operational checkpoint seam for resumable project orchestration."""

    def load(self, orchestration_id: str) -> dict[str, Any] | None:
        """Load the latest validated checkpoint for one orchestration."""
        ...

    def save(self, orchestration_id: str, payload: dict[str, Any]) -> None:
        """Atomically replace the latest checkpoint for one orchestration."""
        ...
