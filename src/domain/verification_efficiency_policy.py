"""Universal, minimal-token validation discipline injected at TaskPackage creation.

This changes worker guidance, not required gates or evaluation semantics.
"""

VERIFICATION_EFFICIENCY_POLICY_MARKER = "ADAPTIVE_VERIFICATION_EFFICIENCY_V1"

VERIFICATION_EFFICIENCY_DIRECTIVES: tuple[str, ...] = (
    VERIFICATION_EFFICIENCY_POLICY_MARKER
    + ": Use minimal risk-based tests during each change; rerun affected tests "
    "after meaningful changes, and required integration/full-suite gates once "
    "at the final source state. Never waive required checks or claim unrun PASS.",
    "Reuse previous PASS evidence only if source, command, dependencies, "
    "configuration, environment and acceptance scope match. On RETURNED, "
    "audit the authoritative reason and existing release artifacts read-only "
    "before rerunning tests or packaging. Reuse identical valid ZIP/manifest; "
    "never force ACCEPTED, fake gates, or reuse after a source change.",
    "Keep read-only audits non-mutating (no shell cleanup/deletion). Report "
    "only an evidence ledger with PASS/FAIL/NOT_RUN/REUSED, source identity, "
    "reference and any blocker; avoid duplicate progress summaries.",
)


def verification_efficiency_policy_directives() -> tuple[str, ...]:
    """Default for every delegated Work Unit, regardless of stack or role."""
    return VERIFICATION_EFFICIENCY_DIRECTIVES
