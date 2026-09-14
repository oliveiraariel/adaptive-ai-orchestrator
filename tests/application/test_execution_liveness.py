import pytest

from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.execution_liveness import (
    ExecutionLiveness,
    ExecutionLivenessMonitor,
    ExecutionLivenessState,
    ExecutionLivenessTimeout,
)


class MemoryLivenessStore:
    def __init__(self) -> None:
        self.snapshots: dict[str, ExecutionLiveness] = {}
        self.history: list[ExecutionLiveness] = []

    def read(self, external_id: str) -> ExecutionLiveness | None:
        return self.snapshots.get(external_id)

    def write(self, snapshot: ExecutionLiveness) -> None:
        self.snapshots[snapshot.external_id] = snapshot
        self.history.append(snapshot)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def wall(self) -> float:
        return 1_800_000_000.0 + self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


class SequenceRuntime:
    def __init__(self, sequence: list[object]) -> None:
        self.sequence = list(sequence)
        self.status_calls = 0
        self.retrieve_calls = 0
        self.cancel_calls = 0

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        self.status_calls += 1
        item = self.sequence.pop(0)
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, AgentRuntimeStatus)
        return item

    def retrieve_result(self, execution: ExecutionReference) -> AgentRuntimeResult:
        self.retrieve_calls += 1
        return AgentRuntimeResult(
            execution=ExecutionReference(
                id=execution.id,
                runtime=execution.runtime,
                external_id=execution.external_id,
                status=AgentRuntimeStatus.COMPLETED,
            ),
            raw_result={"output": "done"},
        )

    def submit(self, task):  # pragma: no cover - must never be used by monitor
        raise AssertionError("liveness observation must never redispatch")

    def recover_execution(self, external_id):  # pragma: no cover
        raise AssertionError("monitor receives an already recovered execution")

    def cancel(self, execution):
        self.cancel_calls += 1
        raise AssertionError("liveness timeout must not cancel automatically")


def execution() -> ExecutionReference:
    return ExecutionReference(
        id="execution-001",
        runtime="fake",
        external_id="external-001",
        status=AgentRuntimeStatus.SUBMITTED,
    )


def test_monitor_emits_runtime_confirmed_heartbeats_until_completion() -> None:
    runtime = SequenceRuntime(
        [
            AgentRuntimeStatus.RUNNING,
            AgentRuntimeStatus.RUNNING,
            AgentRuntimeStatus.COMPLETED,
        ]
    )
    store = MemoryLivenessStore()
    clock = FakeClock()
    emitted = []

    result = ExecutionLivenessMonitor(
        runtime=runtime,
        store=store,
        heartbeat_interval_seconds=30,
        liveness_timeout_seconds=90,
        hard_deadline_seconds=600,
        monotonic=clock.monotonic,
        wall_clock=clock.wall,
        sleep=clock.sleep,
    ).wait(execution(), on_heartbeat=emitted.append)

    assert result.raw_result == {"output": "done"}
    assert runtime.retrieve_calls == 1
    assert runtime.cancel_calls == 0
    assert [item.state for item in emitted] == [
        ExecutionLivenessState.RUNNING,
        ExecutionLivenessState.RUNNING,
        ExecutionLivenessState.COMPLETED,
    ]
    assert [item.heartbeat_sequence for item in emitted] == [1, 2, 3]
    assert store.read("external-001").state is ExecutionLivenessState.COMPLETED


def test_monitor_marks_suspect_after_three_missed_30_second_observations() -> None:
    runtime = SequenceRuntime(
        [
            RuntimeError("observer transport unavailable"),
            RuntimeError("observer transport unavailable"),
            RuntimeError("observer transport unavailable"),
            RuntimeError("observer transport unavailable"),
            AgentRuntimeStatus.RUNNING,
            AgentRuntimeStatus.COMPLETED,
        ]
    )
    store = MemoryLivenessStore()
    clock = FakeClock()
    emitted = []
    pulses = []

    result = ExecutionLivenessMonitor(
        runtime=runtime,
        store=store,
        heartbeat_interval_seconds=30,
        liveness_timeout_seconds=90,
        hard_deadline_seconds=240,
        monotonic=clock.monotonic,
        wall_clock=clock.wall,
        sleep=clock.sleep,
    ).wait(
        execution(),
        on_heartbeat=emitted.append,
        on_observer_pulse=lambda execution, silence: pulses.append(
            (execution.external_id, silence)
        ),
    )

    assert result.raw_result == {"output": "done"}
    assert [silence for _, silence in pulses] == [0.0, 30.0, 60.0, 90.0]
    assert all(external_id == "external-001" for external_id, _ in pulses)
    assert ExecutionLivenessState.SUSPECT in [item.state for item in emitted]
    suspect = next(
        item for item in emitted if item.state is ExecutionLivenessState.SUSPECT
    )
    assert suspect.source == "runtime-status-unavailable"
    assert runtime.retrieve_calls == 1
    assert runtime.cancel_calls == 0


def test_hard_deadline_stops_observer_without_cancel_or_redispatch() -> None:
    runtime = SequenceRuntime(
        [RuntimeError("transport unavailable")] * 10
    )
    store = MemoryLivenessStore()
    clock = FakeClock()

    with pytest.raises(ExecutionLivenessTimeout, match="not cancelled or redispatched"):
        ExecutionLivenessMonitor(
            runtime=runtime,
            store=store,
            heartbeat_interval_seconds=30,
            liveness_timeout_seconds=90,
            hard_deadline_seconds=120,
            monotonic=clock.monotonic,
            wall_clock=clock.wall,
            sleep=clock.sleep,
        ).wait(execution())

    assert runtime.retrieve_calls == 0
    assert runtime.cancel_calls == 0
    assert store.read("external-001").state is ExecutionLivenessState.SUSPECT


def test_monitor_rejects_incoherent_liveness_windows() -> None:
    store = MemoryLivenessStore()
    runtime = SequenceRuntime([AgentRuntimeStatus.COMPLETED])

    with pytest.raises(ValueError, match="at least one heartbeat"):
        ExecutionLivenessMonitor(
            runtime=runtime,
            store=store,
            heartbeat_interval_seconds=30,
            liveness_timeout_seconds=20,
            hard_deadline_seconds=600,
        )

    with pytest.raises(ValueError, match="at least the liveness timeout"):
        ExecutionLivenessMonitor(
            runtime=runtime,
            store=store,
            heartbeat_interval_seconds=30,
            liveness_timeout_seconds=90,
            hard_deadline_seconds=60,
        )
