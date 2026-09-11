from __future__ import annotations

from domain.provider_incident import IncidentEvidence, ProviderIncident


class IncidentClassifier:
    """Classify provider/runtime failures without collapsing every 429 to one cause.

    The classifier is intentionally deterministic. It consumes the provider
    error plus optional out-of-band evidence (budget/quota dashboards, runtime
    telemetry, credential provenance) and emits a structured diagnosis with a
    confidence score and an explicit remediation hint.
    """

    def classify(
        self,
        error: BaseException | str,
        *,
        provider: str,
        model: str,
        evidence: IncidentEvidence | None = None,
    ) -> ProviderIncident | None:
        message = str(error).strip()
        normalized = message.casefold()
        evidence = evidence or IncidentEvidence()
        status_code = evidence.status_code or self._infer_status_code(normalized)

        # Strong out-of-band budget evidence must outrank a generic HTTP 429.
        if evidence.project_daily_budget_exhausted is True:
            return self._incident(
                provider,
                model,
                category="quota",
                subtype="project_daily_budget",
                scope="project",
                retryable=False,
                confidence=0.99,
                evidence=("project-daily-budget-exhausted", self._status_evidence(status_code)),
                recommended_action="wait-or-raise-project-daily-budget",
                status_code=status_code,
            )
        if evidence.project_monthly_budget_exhausted is True:
            return self._incident(
                provider,
                model,
                category="quota",
                subtype="project_monthly_budget",
                scope="project",
                retryable=False,
                confidence=0.99,
                evidence=("project-monthly-budget-exhausted", self._status_evidence(status_code)),
                recommended_action="wait-or-raise-project-monthly-budget",
                status_code=status_code,
            )
        if evidence.organization_budget_exhausted is True:
            return self._incident(
                provider,
                model,
                category="quota",
                subtype="organization_budget",
                scope="organization",
                retryable=False,
                confidence=0.99,
                evidence=("organization-budget-exhausted", self._status_evidence(status_code)),
                recommended_action="restore-organization-budget-or-use-funded-provider",
                status_code=status_code,
            )
        if evidence.tpm_exhausted is True:
            return self._quota_incident(
                provider,
                model,
                subtype="tpm",
                scope="project",
                confidence=0.98,
                recommended_action="backoff-reduce-request-token-pressure-or-fallback",
                status_code=status_code,
            )
        if evidence.rpm_exhausted is True:
            return self._quota_incident(
                provider,
                model,
                subtype="rpm",
                scope="project",
                confidence=0.98,
                recommended_action="backoff-reduce-request-rate-or-fallback",
                status_code=status_code,
            )
        if evidence.concurrency_exhausted is True:
            return self._quota_incident(
                provider,
                model,
                subtype="concurrency",
                scope="project",
                confidence=0.98,
                recommended_action="reduce-active-workers-or-fallback",
                status_code=status_code,
            )

        # Explicit billing/credit errors are different from transient rate limits.
        billing_terms = (
            "insufficient credits",
            "insufficient credit",
            "no credits remaining",
            "credit balance",
            "balance too low",
            "payment required",
            "quota balance",
            "billing hard limit",
            "billing limit",
        )
        if any(term in normalized for term in billing_terms):
            return self._incident(
                provider,
                model,
                category="billing",
                subtype="insufficient_funds",
                scope="credential",
                retryable=False,
                confidence=0.98,
                evidence=("billing-or-credit-message", self._status_evidence(status_code)),
                recommended_action="restore-funded-credential-or-fallback",
                status_code=status_code,
            )

        # Budget windows sometimes arrive as 429 with product-specific wording.
        if "daily" in normalized and any(
            term in normalized for term in ("limit", "quota", "budget", "usage")
        ):
            return self._incident(
                provider,
                model,
                category="quota",
                subtype="daily_usage_window",
                scope="project",
                retryable=False,
                confidence=0.9,
                evidence=("daily-limit-message", self._status_evidence(status_code)),
                recommended_action="wait-for-window-or-raise-authorized-daily-budget",
                status_code=status_code,
            )
        if any(term in normalized for term in ("weekly limit", "monthly limit", "monthly quota")):
            subtype = "weekly_usage_window" if "weekly" in normalized else "monthly_usage_window"
            return self._incident(
                provider,
                model,
                category="quota",
                subtype=subtype,
                scope="project",
                retryable=False,
                confidence=0.9,
                evidence=(f"{subtype}-message", self._status_evidence(status_code)),
                recommended_action="wait-for-window-or-fallback",
                status_code=status_code,
            )

        # More specific rate dimensions outrank the generic 429 bucket.
        if "tpm" in normalized or "tokens per minute" in normalized:
            return self._quota_incident(
                provider,
                model,
                subtype="tpm",
                scope="project",
                confidence=0.92,
                recommended_action="backoff-reduce-request-token-pressure-or-fallback",
                status_code=status_code,
            )
        if "rpm" in normalized or "requests per minute" in normalized:
            return self._quota_incident(
                provider,
                model,
                subtype="rpm",
                scope="project",
                confidence=0.92,
                recommended_action="backoff-reduce-request-rate-or-fallback",
                status_code=status_code,
            )
        if "concurrency" in normalized:
            return self._quota_incident(
                provider,
                model,
                subtype="concurrency",
                scope="project",
                confidence=0.92,
                recommended_action="reduce-active-workers-or-fallback",
                status_code=status_code,
            )

        auth_terms = (
            "authentication",
            "unauthorized",
            "invalid api key",
            "invalid key",
            "login required",
            "forbidden",
            "401",
            "403",
        )
        if any(term in normalized for term in auth_terms):
            return self._incident(
                provider,
                model,
                category="auth",
                subtype="credential_rejected",
                scope="credential",
                retryable=False,
                confidence=0.95,
                evidence=("authentication-message", self._status_evidence(status_code)),
                recommended_action="verify-credential-provenance-endpoint-and-scope",
                status_code=status_code,
            )

        unknown_model_terms = (
            "unknown model",
            "model not found",
            "configured model is unavailable",
            "model is unavailable",
            "not offered on this account",
        )
        if any(term in normalized for term in unknown_model_terms):
            return self._incident(
                provider,
                model,
                category="configuration",
                subtype="model_resolution",
                scope="model",
                retryable=False,
                confidence=0.94,
                evidence=("model-resolution-message", self._status_evidence(status_code)),
                recommended_action="inspect-provider-route-catalog-allowlist-and-credential-product",
                status_code=status_code,
            )

        timeout_terms = ("timed out", "timeout")
        if any(term in normalized for term in timeout_terms):
            return self._incident(
                provider,
                model,
                category="timeout",
                subtype="request_timeout",
                scope="provider",
                retryable=True,
                confidence=0.9,
                evidence=("timeout-message", self._status_evidence(status_code)),
                recommended_action="bounded-retry-then-fallback",
                status_code=status_code,
            )

        unavailable_terms = (
            "overloaded",
            "at capacity",
            "temporarily unavailable",
            "service unavailable",
            "server error",
            "502",
            "503",
            "504",
        )
        if any(term in normalized for term in unavailable_terms):
            return self._incident(
                provider,
                model,
                category="unavailable",
                subtype="provider_unavailable",
                scope="provider",
                retryable=True,
                confidence=0.9,
                evidence=("provider-unavailable-message", self._status_evidence(status_code)),
                recommended_action="bounded-retry-then-fallback",
                status_code=status_code,
            )

        rate_limit_terms = (
            "rate limit",
            "rate_limit",
            "too many requests",
            "slow down",
            "429",
            "throttl",
            "resource exhausted",
            "usage limit",
            "quota limit",
        )
        if status_code == 429 or any(term in normalized for term in rate_limit_terms):
            return self._incident(
                provider,
                model,
                category="quota",
                subtype="provider_rate_limit_unknown",
                scope="provider",
                retryable=True,
                confidence=0.65,
                evidence=("generic-rate-limit-evidence", self._status_evidence(status_code)),
                recommended_action="bounded-backoff-correlate-budget-tpm-rpm-concurrency-then-fallback",
                status_code=status_code,
            )

        return None

    @staticmethod
    def _infer_status_code(message: str) -> int | None:
        for code in (401, 403, 402, 429, 500, 502, 503, 504):
            if str(code) in message:
                return code
        return None

    @staticmethod
    def _status_evidence(status_code: int | None) -> str:
        return f"http-{status_code}" if status_code is not None else "http-status-unknown"

    def _quota_incident(
        self,
        provider: str,
        model: str,
        *,
        subtype: str,
        scope: str,
        confidence: float,
        recommended_action: str,
        status_code: int | None,
    ) -> ProviderIncident:
        return self._incident(
            provider,
            model,
            category="quota",
            subtype=subtype,
            scope=scope,
            retryable=True,
            confidence=confidence,
            evidence=(f"{subtype}-quota-evidence", self._status_evidence(status_code)),
            recommended_action=recommended_action,
            status_code=status_code,
        )

    @staticmethod
    def _incident(
        provider: str,
        model: str,
        *,
        category: str,
        subtype: str,
        scope: str,
        retryable: bool,
        confidence: float,
        evidence: tuple[str, ...],
        recommended_action: str,
        status_code: int | None,
    ) -> ProviderIncident:
        clean_evidence = tuple(item for item in evidence if item)
        return ProviderIncident(
            provider=provider,
            model=model,
            category=category,  # type: ignore[arg-type]
            subtype=subtype,
            scope=scope,  # type: ignore[arg-type]
            retryable=retryable,
            confidence=max(0.0, min(1.0, confidence)),
            evidence=clean_evidence,
            recommended_action=recommended_action,
            status_code=status_code,
        )
