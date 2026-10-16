"""Cross-project verification discipline injected into every delegated Work Unit.

This rule optimizes verification *frequency*, never the required acceptance
criteria. It intentionally does not execute commands or claim to cache tests.
"""

VERIFICATION_EFFICIENCY_POLICY_MARKER = "ADAPTIVE_VERIFICATION_EFFICIENCY_V1"

VERIFICATION_EFFICIENCY_DIRECTIVES: tuple[str, ...] = (
    VERIFICATION_EFFICIENCY_POLICY_MARKER
    + ": Apply risk-based verification to every Work Unit. A test or gate is "
    "mandatory when required by acceptance criteria, risk, or the project policy; "
    "do not omit such gates to save time.",
    "For a focused change, begin with the smallest regression reproducing the "
    "defect and relevant static/syntax checks. During implementation rerun only "
    "tests affected by a meaningful code/configuration change. Do not run a full "
    "suite after each minor step; perform required full/integration gates at the "
    "final integration boundary, normally once for the final source state.",
    "Treat prior PASS as reusable evidence only when the exact source state, "
    "test command, dependencies, environment, configuration and acceptance "
    "scope remain equivalent. If any of these changed materially, or the "
    "previous result is untrusted, rerun the affected gate. Never claim "
    "an unexecuted gate passed.",
    "For a RETURNED/release reconciliation with unchanged source and a valid "
    "canonical ZIP/report/manifest, first audit authoritative verdict and "
    "manifest metadata read-only. Reuse valid evidence; do not regenerate "
    "artifacts, bump version or repeat all tests solely due to a missing "
    "structured delivery field. Never force ACCEPTED or edit checkpoints.",
    "In read-only inspection do not run shell cleanup, deletion or destructive "
    "temporary-directory routines. Prefer inspecting existing artifacts "
    "without mutation. If a test requires ephemeral files, use an explicitly "
    "authorized isolated scratch directory and document its cleanup boundary.",
    "Report only a concise evidence ledger (gate, exact source fingerprint, "
    "result PASS/FAIL/NOT_RUN/REUSED, last execution reference and reason "
    "for reuse), plus actual blockers and release identity. Do not reproduce "
    "long previously accepted results or emit duplicate status summaries.",
)


def verification_efficiency_policy_directives() -> tuple[str, ...]:
    """Invariant guidance, independent of language, framework or Work Unit role."""
    return VERIFICATION_EFFICIENCY_DIRECTIVES
