from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

from application.agent_runtime import (
    AgentRuntime,
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)


class ExecutionLivenessState(str, Enum):
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    SUSPECT = "SUSPECT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ExecutionLiveness:
    external_id: str
    execution_id: str
    runtime: str
    state: ExecutionLivenessState
    heartbeat_sequence: int
    started_at: float
    last_heartbeat_at: float
    last_progress_at: float
    source: str


class ExecutionLivenessStore(Protocol):
    def read(self, external_id: str) -> ExecutionLiveness | None:
        """Read the most recent durable liveness snapshot."""
        ...

    def write(self, snapshot: ExecutionLiveness) -> None:
        """Atomically persist one liveness snapshot."""
        ...


class ExecutionLivenessTimeout(RuntimeError):
    """Raised when the observer reaches its hard deadline without completion."""


HeartbeatCallback = Callable[[ExecutionLiveness], None]


class ExecutionLivenessMonitor:
    """Observe one existing execution without redispatching it.

    Heartbeats are based on successful runtime status observations. Silence on
    the observation channel is therefore not treated as execution death. After
    the liveness timeout the execution becomes SUSPECT, but it is never
    redispatched or cancelled automatically. The hard deadline only stops the
    observer; a later observer may recover the same external execution.
    """

    def __init__(
        self,
        *,
        runtime: AgentRuntime,
        store: ExecutionLivenessStore,
        heartbeat_interval_seconds: float = 30.0,
        liveness_timeout_seconds: float = 90.0,
        hard_deadline_seconds: float = 600.0,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive.")
        if liveness_timeout_seconds < heartbeat_interval_seconds:
            raise ValueError(
                "liveness_timeout_seconds must be at least one heartbeat interval."
            )
        if hard_deadline_seconds < liveness_timeout_seconds:
            raise ValueError(
                "hard_deadline_seconds must be at least the liveness timeout."
            )
        self._runtime = runtime
        self._store = store
        self._heartbeat_interval = heartbeat_interval_seconds
        self._liveness_timeout = liveness_timeout_seconds
        self._hard_deadline = hard_deadline_seconds
        self._monotonic = monotonic
        self._wall_clock = wall_clock
        self._sleep = sleep

    def wait(
        self,
        execution: ExecutionReference,
        *,
        on_heartbeat: HeartbeatCallback | None = None,
    ) -> AgentRuntimeResult:
        started_monotonic = self._monotonic()
        existing = self._store.read(execution.external_id)
        started_at = (
            existing.started_at if existing is not None else self._wall_clock()
        )
        sequence = existing.heartbeat_sequence if existing is not None else 0
        last_progress_at = (
            existing.last_progress_at if existing is not None else started_at
        )
        previous_state = existing.state if existing is not None else None
        last_runtime_confirmation = started_monotonic

        if existing is None:
            snapshot = ExecutionLiveness(
                external_id=execution.external_id,
                execution_id=execution.id,
                runtime=execution.runtime,
                state=ExecutionLivenessState.SUBMITTED,
                heartbeat_sequence=sequence,
                started_at=started_at,
                last_heartbeat_at=self._wall_clock(),
                last_progress_at=last_progress_at,
                source="observer-start",
            )
            self._store.write(snapshot)

        while True:
            now_monotonic = self._monotonic()
            elapsed = now_monotonic - started_monotonic
            if elapsed >= self._hard_deadline:
                sequence += 1
                snapshot = self._snapshot(
                    execution=execution,
                    state=ExecutionLivenessState.SUSPECT,
                    sequence=sequence,
                    started_at=started_at,
                    last_progress_at=last_progress_at,
                    source="hard-deadline",
                )
                self._store.write(snapshot)
                self._emit(on_heartbeat, snapshot)
                raise ExecutionLivenessTimeout(
                    "Execution observer reached its hard deadline; the existing "
                    "run was not cancelled or redispatched."
                )

            try:
                runtime_status = self._runtime.get_status(execution)
            except Exception:
                silence = self._monotonic() - last_runtime_confirmation
                if silence >= self._liveness_timeout:
                    sequence += 1
                    snapshot = self._snapshot(
                        execution=execution,
                        state=ExecutionLivenessState.SUSPECT,
                        sequence=sequence,
                        started_at=started_at,
                        last_progress_at=last_progress_at,
                        source="runtime-status-unavailable",
                    )
                    self._store.write(snapshot)
                    self._emit(on_heartbeat, snapshot)
                self._sleep_until_next(started_monotonic)
                continue

            last_runtime_confirmation = self._monotonic()
            state = self._map_status(runtime_status)
            now_wall = self._wall_clock()
            if state != previous_state:
                last_progress_at = now_wall
                previous_state = state
            sequence += 1
            snapshot = ExecutionLiveness(
                external_id=execution.external_id,
                execution_id=execution.id,
                runtime=execution.runtime,
                state=state,
                heartbeat_sequence=sequence,
                started_at=started_at,
                last_heartbeat_at=now_wall,
                last_progress_at=last_progress_at,
                source="runtime-status",
            )
            self._store.write(snapshot)
            self._emit(on_heartbeat, snapshot)

            if state in {
                ExecutionLivenessState.COMPLETED,
                ExecutionLivenessState.FAILED,
                ExecutionLivenessState.CANCELLED,
            }:
                result = self._runtime.retrieve_result(execution)
                terminal_state = self._map_status(result.execution.status)
                if terminal_state != state:
                    sequence += 1
                    terminal = self._snapshot(
                        execution=result.execution,
                        state=terminal_state,
                        sequence=sequence,
                        started_at=started_at,
                        last_progress_at=self._wall_clock(),
                        source="runtime-result",
                    )
                    self._store.write(terminal)
                    self._emit(on_heartbeat, terminal)
                return result

            self._sleep_until_next(started_monotonic)

    def _sleep_until_next(self, started_monotonic: float) -> None:
        remaining = self._hard_deadline - (self._monotonic() - started_monotonic)
        if remaining <= 0:
            return
        self._sleep(min(self._heartbeat_interval, remaining))

    def _snapshot(
        self,
        *,
        execution: ExecutionReference,
        state: ExecutionLivenessState,
        sequence: int,
        started_at: float,
        last_progress_at: float,
        source: str,
    ) -> ExecutionLiveness:
        return ExecutionLiveness(
            external_id=execution.external_id,
            execution_id=execution.id,
            runtime=execution.runtime,
            state=state,
            heartbeat_sequence=sequence,
            started_at=started_at,
            last_heartbeat_at=self._wall_clock(),
            last_progress_at=last_progress_at,
            source=source,
        )

    @staticmethod
    def _emit(
        callback: HeartbeatCallback | None,
        snapshot: ExecutionLiveness,
    ) -> None:
        if callback is not None:
            callback(snapshot)

    @staticmethod
    def _map_status(status: AgentRuntimeStatus) -> ExecutionLivenessState:
        return ExecutionLivenessState(status.value)
