from __future__ import annotations

import re
from typing import Iterable


RELEASE_ARTIFACT_POLICY_MARKER = "ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1"

# This policy governs packaging/installable release artifacts without assuming
# a particular language, framework, archive format, or deployment platform.
RELEASE_ARTIFACT_POLICY_DIRECTIVES: tuple[str, ...] = (
    RELEASE_ARTIFACT_POLICY_MARKER
    + ": mandatory when creating or regenerating an installable/deployable release artifact; apply it without replacing project-specific release conventions.",
    "Package the authoritative intended source state. Identify the repository/worktree, branch or ref, HEAD when available, and working-tree state before packaging. If intentional WIP is included, report that fact explicitly; never silently package a stale commit or an older artifact.",
    "Before packaging, run the smallest sufficient project-defined validation set relevant to the artifact, such as build, tests, lint/syntax, contract/composition, or smoke checks where they actually exist. Do not invent framework-specific commands and do not report a gate as PASS unless it was executed against the packaged source state.",
    "For a fix, hotfix, or environmental retest, create a fresh artifact after the validated change. Do not reuse an older archive or ambiguously overwrite it in a way that prevents source-to-artifact traceability.",
    "Honor the project's artifact naming convention. If none exists, use a unique descriptive name containing artifact/purpose and a UTC/local-date-time discriminator appropriate to the environment; artifact identity must ultimately be confirmed by source identity and checksum, not filename alone.",
    "Package runtime-required files and production dependencies only. Exclude source-control metadata, environment files, secrets, tests, caches, temporary files, local state, and development-only tooling or documentation unless the target runtime explicitly requires them.",
    "Validate installable structure for the actual platform: required root layout, entrypoint/manifests, production autoload/dependencies, and runtime assets. Avoid accidental extra directory nesting and do not impose WordPress, Composer, npm, or any other stack-specific layout when it is not applicable.",
    "Validate artifact integrity with the format-appropriate archive/package check, verify required runtime files are present and forbidden sensitive/development material is absent, then compute and report SHA-256 and artifact size.",
    "Release-artifact evidence must report source branch/ref and HEAD when available, working-tree state, validation results actually executed, artifact filename/path, package root and main entrypoint/manifest when applicable, size, SHA-256, integrity-check result, and whether it is ready for environmental retest.",
    "Packaging authority does not imply authority to merge, publish, deploy, install, activate, upload to production, or perform destructive environment mutations. Treat those as separate authority gates.",
    "Distinguish local artifact readiness from real environmental validation. An archive may be ready for retest while installation, activation, runtime, database, browser, network, or platform-specific validation remains pending.",
)

_ACTION_RE = re.compile(
    r"\b(?:"
    r"generate|create|build|package|assemble|prepare|rebuild|regenerate|repackage|"
    r"gerar|gere|criar|crie|construir|construa|montar|monte|empacotar|empacote|"
    r"preparar|prepare|recriar|recrie|regenerar|regenere|reempacotar|reempacote"
    r")\b",
    re.IGNORECASE,
)

_ARTIFACT_RE = re.compile(
    r"\b(?:"
    r"zip|archive|release\s+artifact|installable\s+package|deployment\s+package|"
    r"plugin\s+package|theme\s+package|runtime\s+bundle|release\s+bundle|"
    r"pacote\s+zip|arquivo\s+zip|artefato\s+de\s+release|artefato\s+de\s+lan[cç]amento|"
    r"pacote\s+instal[aá]vel|pacote\s+de\s+instala[cç][aã]o|pacote\s+de\s+plugin|"
    r"pacote\s+do\s+plugin|pacote\s+de\s+tema|bundle\s+de\s+runtime"
    r")\b",
    re.IGNORECASE,
)

_FORCE_RE = re.compile(
    r"\b(?:release\s+artifact\s+governance|release\s+artifact\s+policy|"
    r"pol[ií]tica\s+de\s+artefato\s+de\s+release|governan[cç]a\s+de\s+pacote)\b",
    re.IGNORECASE,
)


def _joined_text(parts: Iterable[str]) -> str:
    return "\n".join(part for part in parts if isinstance(part, str) and part.strip())


def release_artifact_policy_applies(
    *,
    objective: str,
    scope: str = "",
    context: Iterable[str] = (),
    constraints: Iterable[str] = (),
) -> bool:
    """Return whether mandatory release-artifact packaging governance applies."""

    text = _joined_text((objective, scope, *context, *constraints))
    if not text:
        return False

    if RELEASE_ARTIFACT_POLICY_MARKER.lower() in text.lower():
        return True
    if _FORCE_RE.search(text):
        return True

    return bool(_ACTION_RE.search(text) and _ARTIFACT_RE.search(text))


def release_artifact_policy_directives(
    *,
    objective: str,
    scope: str = "",
    context: Iterable[str] = (),
    constraints: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return mandatory release-artifact directives for packaging work."""

    if not release_artifact_policy_applies(
        objective=objective,
        scope=scope,
        context=context,
        constraints=constraints,
    ):
        return ()
    return RELEASE_ARTIFACT_POLICY_DIRECTIVES


def enforce_release_artifact_policy(
    *,
    objective: str,
    scope: str = "",
    context: Iterable[str] = (),
    constraints: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return constraints with mandatory packaging governance appended once."""

    existing = tuple(constraints)
    additions = release_artifact_policy_directives(
        objective=objective,
        scope=scope,
        context=context,
        constraints=existing,
    )
    if not additions:
        return existing

    normalized_existing = {item.strip() for item in existing}
    return (
        *existing,
        *(
            item
            for item in additions
            if item.strip() not in normalized_existing
        ),
    )
