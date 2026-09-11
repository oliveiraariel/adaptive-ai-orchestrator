from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from domain.provider_incident import ProviderIncident


@dataclass
class _CircuitState:
    failures: int = 0
    state: str = "closed"
    opened_at: float | None = None
    cooldown_seconds: int = 0


@dataclass(frozen=True)
class ProviderHealthDecision:
    allowed: bool
    state: str
    reason: str


class ProviderHealthPolicy:
    """In-memory temporary circuit breaker for provider/model routes.

    This is deliberately non-persistent: an operational incident must not
    silently rewrite permanent routing policy. Durable learning is captured in
    telemetry/docs and promoted separately through governance.
    """

    def __init__(self, *, failure_threshold: int = 3) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self._failure_threshold = failure_threshold
        self._states: dict[tuple[str, str], _CircuitState] = {}

    def can_attempt(
        self,
        provider: str,
        model: str,
        *,
        now: float | None = None,
    ) -> ProviderHealthDecision:
        key = self._key(provider, model)
        state = self._states.get(key)
        if state is None or state.state == "closed":
            return ProviderHealthDecision(True, "closed", "route-healthy")

        now_value = monotonic() if now is None else now
        if state.state == "open":
            opened_at = state.opened_at or now_value
            if now_value - opened_at >= state.cooldown_seconds:
                state.state = "half_open"
                return ProviderHealthDecision(
                    True,
                    "half_open",
                    "cooldown-elapsed-single-probe-allowed",
                )
            return ProviderHealthDecision(
                False,
                "open",
                "temporary-circuit-breaker-open",
            )

        # half_open allows one probe. The caller should immediately record
        # success/failure for that probe before dispatching additional work.
        return ProviderHealthDecision(
            True,
            "half_open",
            "half-open-probe",
        )

    def record_failure(
        self,
        incident: ProviderIncident,
        *,
        cooldown_seconds: int,
        now: float | None = None,
    ) -> ProviderHealthDecision:
        key = self._key(incident.provider, incident.model)
        state = self._states.setdefault(key, _CircuitState())
        state.failures += 1
        now_value = monotonic() if now is None else now

        immediate_open = not incident.retryable
        if immediate_open or state.failures >= self._failure_threshold:
            state.state = "open"
            state.opened_at = now_value
            state.cooldown_seconds = max(0, cooldown_seconds)
            return ProviderHealthDecision(
                False,
                "open",
                (
                    "non-retryable-incident"
                    if immediate_open
                    else "failure-threshold-reached"
                ),
            )

        return ProviderHealthDecision(
            True,
            state.state,
            "failure-recorded-below-threshold",
        )

    def record_success(self, provider: str, model: str) -> None:
        self._states[self._key(provider, model)] = _CircuitState()

    def state_for(self, provider: str, model: str) -> str:
        return self._states.get(self._key(provider, model), _CircuitState()).state

    @staticmethod
    def _key(provider: str, model: str) -> tuple[str, str]:
        return (provider.strip().casefold(), model.strip().casefold())
