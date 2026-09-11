from __future__ import annotations

from dataclasses import dataclass

from domain.provider_incident import ProviderIncident


@dataclass(frozen=True)
class RemediationDecision:
    """Safe operational response to a classified provider incident."""

    action: str
    allow_same_model_retry: bool
    fallback_allowed: bool
    cooldown_seconds: int
    requires_human_action: bool
    explanation: str

    def as_payload(self) -> dict[str, object]:
        return {
            "action": self.action,
            "allow_same_model_retry": self.allow_same_model_retry,
            "fallback_allowed": self.fallback_allowed,
            "cooldown_seconds": self.cooldown_seconds,
            "requires_human_action": self.requires_human_action,
            "explanation": self.explanation,
        }


class RemediationPolicy:
    """Map incident semantics to conservative operational remediation.

    Permanent routing/security/cost policy is never mutated here. The policy
    decides only what one runtime failure should do now: retry briefly, fall
    back, block the unhealthy route, or require operator action.
    """

    def decide(self, incident: ProviderIncident) -> RemediationDecision:
        if incident.category == "billing":
            return RemediationDecision(
                action="fallback-or-restore-funded-credential",
                allow_same_model_retry=False,
                fallback_allowed=True,
                cooldown_seconds=600,
                requires_human_action=True,
                explanation=(
                    "Billing/credit exhaustion is structural for the current "
                    "credential; repeated same-model retries waste time and can "
                    "increase noise without changing the outcome."
                ),
            )

        if incident.category == "auth":
            return RemediationDecision(
                action="verify-credential-provenance-then-fallback",
                allow_same_model_retry=False,
                fallback_allowed=True,
                cooldown_seconds=600,
                requires_human_action=True,
                explanation=(
                    "Authentication failures should trigger credential/product/"
                    "endpoint verification rather than blind retries."
                ),
            )

        if incident.category == "configuration":
            return RemediationDecision(
                action="repair-runtime-configuration-or-fallback",
                allow_same_model_retry=False,
                fallback_allowed=True,
                cooldown_seconds=300,
                requires_human_action=True,
                explanation=(
                    "Model-resolution and configuration failures are not expected "
                    "to heal through repeated calls."
                ),
            )

        if incident.category == "quota":
            if incident.subtype in {
                "project_daily_budget",
                "project_monthly_budget",
                "organization_budget",
                "daily_usage_window",
                "weekly_usage_window",
                "monthly_usage_window",
            }:
                return RemediationDecision(
                    action="block-same-route-until-budget-window-or-authorized-change",
                    allow_same_model_retry=False,
                    fallback_allowed=True,
                    cooldown_seconds=600,
                    requires_human_action=True,
                    explanation=(
                        "Budget-window exhaustion is a policy boundary, not a "
                        "transient provider throttle. Same-route retry storms are "
                        "explicitly suppressed."
                    ),
                )

            if incident.subtype == "concurrency":
                return RemediationDecision(
                    action="reduce-concurrency-then-bounded-retry-or-fallback",
                    allow_same_model_retry=True,
                    fallback_allowed=True,
                    cooldown_seconds=30,
                    requires_human_action=False,
                    explanation=(
                        "Concurrency pressure can clear quickly after workers "
                        "finish; one bounded retry is acceptable."
                    ),
                )

            if incident.subtype in {"tpm", "rpm"}:
                return RemediationDecision(
                    action="backoff-reduce-rate-pressure-then-fallback",
                    allow_same_model_retry=True,
                    fallback_allowed=True,
                    cooldown_seconds=60,
                    requires_human_action=False,
                    explanation=(
                        "TPM/RPM throttles are transient but repeated immediate "
                        "retries amplify the same limit."
                    ),
                )

            return RemediationDecision(
                action="bounded-backoff-correlate-quota-evidence-then-fallback",
                allow_same_model_retry=True,
                fallback_allowed=True,
                cooldown_seconds=60,
                requires_human_action=False,
                explanation=(
                    "A generic 429 is a symptom, not a root cause. Treat it as "
                    "unknown quota pressure until budget/TPM/RPM/concurrency "
                    "evidence refines the diagnosis."
                ),
            )

        if incident.category in {"timeout", "unavailable"}:
            return RemediationDecision(
                action="bounded-retry-then-fallback",
                allow_same_model_retry=True,
                fallback_allowed=True,
                cooldown_seconds=30,
                requires_human_action=False,
                explanation=(
                    "Transient transport/provider failures may recover, but retry "
                    "must remain bounded before failover."
                ),
            )

        return RemediationDecision(
            action="surface-incident",
            allow_same_model_retry=False,
            fallback_allowed=False,
            cooldown_seconds=0,
            requires_human_action=True,
            explanation="No automatic remediation rule matched the incident.",
        )
