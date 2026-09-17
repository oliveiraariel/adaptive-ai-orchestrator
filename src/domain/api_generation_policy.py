from __future__ import annotations

import re
from typing import Iterable


API_GENERATION_POLICY_MARKER = "ADAPTIVE_API_GENERATION_POLICY_V1"

# This policy is intentionally language-, framework-, and transport-neutral.
# Protocol-specific requirements are conditional so REST assumptions are not
# imposed on GraphQL, gRPC/RPC, webhooks/events, or other API styles.
API_GENERATION_POLICY_CONSTRAINTS: tuple[str, ...] = (
    API_GENERATION_POLICY_MARKER
    + ": mandatory for API creation or externally observable API contract changes; "
    "apply it without replacing project-specific sources of truth.",
    "API governance is language-, framework-, platform-, and transport-neutral. "
    "Identify the actual API style and existing conventions first; do not force REST, HTTP, OpenAPI, or any specific framework when they are not applicable.",
    "Before implementation, discover or define the externally observable API contract sufficiently for the delegated work: operations/messages, inputs, outputs, validation, public errors, authentication/authorization, and compatibility expectations. Do not invent business rules to fill gaps.",
    "Preserve existing consumers and published behavior. Treat versioning and backward compatibility as mandatory considerations when an API already exists; do not introduce a breaking contract change without explicit authority and impact analysis.",
    "Apply protocol-relevant semantics where applicable, including idempotency/retry behavior, concurrency, pagination/filtering, resource or rate limits, serialization/content types, time handling, numeric precision, and enum/nullability rules. Mark non-applicable concerns as such instead of fabricating requirements.",
    "Treat every external input and trust boundary as untrusted. Enforce operation/resource authorization, ownership or tenant isolation where relevant, input validation, secret protection, and sanitized public errors; keep internal diagnostics out of client-visible responses.",
    "Verification for changed API behavior must include the smallest sufficient combination of contract tests and implementation/integration tests, plus negative authorization/validation cases for protected surfaces and regression coverage for preserved behavior. Add protocol-specific or environmental E2E checks when the required runtime is available.",
    "API work is complete only when the changed contract is implemented and wired, required verification passes, security/code review concerns inside scope are resolved, parallel results are integrated/fan-in verified when applicable, and any remaining environmental validation is explicitly classified rather than hidden as local completion.",
)

_ACTION_RE = re.compile(
    r"\b(?:"
    r"create|build|implement|design|develop|add|change|modify|extend|refactor|"
    r"expose|publish|fix|migrate|"
    r"criar|crie|construir|construa|implementar|implemente|projetar|projete|"
    r"desenvolver|desenvolva|adicionar|adicione|alterar|altere|modificar|modifique|"
    r"expandir|expanda|refatorar|refatore|expor|exponha|publicar|publique|"
    r"corrigir|corrija|migrar|migre"
    r")\b",
    re.IGNORECASE,
)

_STRONG_SURFACE_RE = re.compile(
    r"\b(?:endpoint|endpoints|graphql|grpc|webhook|webhooks|rpc|openapi|"
    r"rest\s+api|http\s+api|api\s+contract|contrato\s+de\s+api|"
    r"api\s+schema|schema\s+de\s+api)\b",
    re.IGNORECASE,
)

_API_RE = re.compile(r"\bapis?\b", re.IGNORECASE)

_CREDENTIAL_ONLY_RE = re.compile(
    r"\b(?:api\s+(?:key|token|secret|credential|credentials|client)|"
    r"(?:chave|token|segredo|credencial|credenciais|cliente)\s+(?:da|de)?\s*api)\b",
    re.IGNORECASE,
)

_EXTERNAL_CONSUMPTION_RE = re.compile(
    r"\b(?:consume|call|use|integrate|connect\s+to|consumir|chamar|usar|integrar|"
    r"conectar(?:-se)?\s+(?:a|com))\b",
    re.IGNORECASE,
)

_FORCE_RE = re.compile(
    r"\b(?:api\s+generation|generation\s+of\s+an?\s+api|geração\s+de\s+api|"
    r"nova\s+api|new\s+api)\b",
    re.IGNORECASE,
)


def _joined_text(parts: Iterable[str]) -> str:
    return "\n".join(part for part in parts if isinstance(part, str) and part.strip())


def api_generation_policy_applies(
    *,
    objective: str,
    scope: str = "",
    context: Iterable[str] = (),
    constraints: Iterable[str] = (),
) -> bool:
    """Return whether mandatory API-generation governance applies.

    The detector intentionally distinguishes creating/changing an API surface
    from merely consuming an external API or rotating API credentials. Callers
    can force the policy by including API_GENERATION_POLICY_MARKER in context or
    constraints.
    """

    text = _joined_text((objective, scope, *context, *constraints))
    if not text:
        return False

    if API_GENERATION_POLICY_MARKER.lower() in text.lower():
        return True

    if _FORCE_RE.search(text):
        return True

    if not _ACTION_RE.search(text):
        return False

    if _STRONG_SURFACE_RE.search(text):
        return True

    if not _API_RE.search(text):
        return False

    # Avoid converting credential rotation or ordinary third-party API
    # consumption into API-generation work unless a stronger API surface signal
    # is also present.
    if _CREDENTIAL_ONLY_RE.search(text):
        return False
    if _EXTERNAL_CONSUMPTION_RE.search(text) and not _FORCE_RE.search(text):
        return False

    return True


def enforce_api_generation_policy(
    *,
    objective: str,
    scope: str = "",
    context: Iterable[str] = (),
    constraints: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return constraints with mandatory API governance appended once."""

    existing = tuple(constraints)
    if not api_generation_policy_applies(
        objective=objective,
        scope=scope,
        context=context,
        constraints=existing,
    ):
        return existing

    normalized_existing = {item.strip() for item in existing}
    additions = tuple(
        item
        for item in API_GENERATION_POLICY_CONSTRAINTS
        if item.strip() not in normalized_existing
    )
    return (*existing, *additions)
