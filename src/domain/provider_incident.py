from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


IncidentCategory = Literal[
    "billing",
    "quota",
    "auth",
    "timeout",
    "unavailable",
    "configuration",
]

IncidentScope = Literal[
    "provider",
    "organization",
    "project",
    "credential",
    "model",
    "session",
    "configuration",
]

FindingSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class CredentialProfile:
    """Operational provenance for one provider credential.

    Provider/model names alone are not enough to determine whether a credential
    is valid for a route. Kimi Platform and Kimi Code, for example, use
    different products, endpoints and billing models even though both expose
    Kimi-family models. OpenAI API keys and ChatGPT/Codex OAuth are similarly
    distinct credential families.
    """

    provider: str
    product: str
    auth_type: str
    billing_mode: str
    endpoint_family: str
    allowed_model_prefixes: tuple[str, ...] = field(default_factory=tuple)

    def allows_model(self, model: str) -> bool:
        if not self.allowed_model_prefixes:
            return True
        normalized = model.strip().casefold()
        return any(
            normalized.startswith(prefix.strip().casefold())
            for prefix in self.allowed_model_prefixes
            if prefix.strip()
        )


@dataclass(frozen=True)
class IncidentEvidence:
    """Optional evidence used to refine an operational incident diagnosis."""

    status_code: int | None = None
    project_daily_budget_exhausted: bool | None = None
    project_monthly_budget_exhausted: bool | None = None
    organization_budget_exhausted: bool | None = None
    tpm_exhausted: bool | None = None
    rpm_exhausted: bool | None = None
    concurrency_exhausted: bool | None = None
    credential_profile: CredentialProfile | None = None


@dataclass(frozen=True)
class ProviderIncident:
    """Structured operational diagnosis for one provider/model failure."""

    provider: str
    model: str
    category: IncidentCategory
    subtype: str
    scope: IncidentScope
    retryable: bool
    confidence: float
    evidence: tuple[str, ...]
    recommended_action: str
    status_code: int | None = None

    @property
    def failover_reason(self) -> str:
        """Compatibility reason consumed by the existing failover policy."""
        if self.category == "quota":
            return "rate_limit"
        if self.category == "configuration":
            return "unavailable"
        return self.category

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "provider": self.provider,
            "model": self.model,
            "category": self.category,
            "subtype": self.subtype,
            "scope": self.scope,
            "retryable": self.retryable,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "recommended_action": self.recommended_action,
            "failover_reason": self.failover_reason,
        }
        if self.status_code is not None:
            payload["status_code"] = self.status_code
        return payload


@dataclass(frozen=True)
class RuntimeSnapshot:
    """Read-only runtime facts used by preflight integrity checks."""

    provider: str
    model: str
    native_context_tokens: int | None = None
    effective_context_tokens: int | None = None
    plugin_models: tuple[str, ...] = field(default_factory=tuple)
    effective_catalog_models: tuple[str, ...] = field(default_factory=tuple)
    authored_provider_models: tuple[str, ...] = field(default_factory=tuple)
    core_version: str | None = None
    plugin_version: str | None = None
    credential_profile: CredentialProfile | None = None


@dataclass(frozen=True)
class PreflightFinding:
    code: str
    severity: FindingSeverity
    message: str
    recommended_action: str

    @property
    def blocks_execution(self) -> bool:
        return self.severity == "error"
