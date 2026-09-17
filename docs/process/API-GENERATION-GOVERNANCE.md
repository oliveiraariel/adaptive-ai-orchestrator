# Mandatory API Generation Governance v1

## Status

This policy is a cross-project Adaptive AI Orchestrator rule for work that **creates an API or changes an externally observable API contract**.

Runtime marker:

```text
ADAPTIVE_API_GENERATION_POLICY_V1
```

The policy is intentionally independent of programming language, framework, hosting platform, protocol and transport.

## Feasibility re-evaluation

A reusable API standard is viable, but only if the mandatory part is expressed as **behavioral and verification invariants**, not as a fixed technology recipe.

A documentation-only prompt is insufficient because workers can enter the Adaptive through different project prompts and Work Units. Conversely, hard-coding REST, HTTP, OpenAPI, controllers, JSON, a specific framework, or a specific test runner would make the rule invalid for GraphQL, gRPC/RPC, webhooks/events and future API styles.

The adopted design therefore has two layers:

1. **Runtime enforcement** at the common `TaskPackage` boundary. API creation/contract-change work receives the mandatory policy automatically.
2. **Human-readable project guidance** in `docs/prompts/INICIAR-PROJETO-API.md`, which is the preferred entry prompt when the objective is explicitly API work.

Project-specific requirements, approved architecture and canonical contracts remain authoritative. The global policy adds minimum engineering obligations; it does not replace domain facts or invent business rules.

## Activation scope

The policy applies when the delegated objective/scope/context indicates creation or modification of an externally observable API surface, including examples such as:

- REST or other HTTP APIs;
- GraphQL schemas/resolvers exposed as an API;
- gRPC or other RPC service contracts;
- webhook endpoints;
- existing endpoint or API-contract changes;
- new public or internal service interfaces whose behavior is consumed across a trust/process boundary.

The policy does **not** automatically classify ordinary consumption of a third-party API, provider integration as a client, or API-key/credential rotation as API generation. Those tasks keep their own security and integration obligations without being forced through the API-generation contract.

The marker `ADAPTIVE_API_GENERATION_POLICY_V1` can be supplied explicitly when the intent is known but not obvious from the Work Unit wording.

## Mandatory cross-stack invariants

When active, the Adaptive must require the delegated work to account for the following, with protocol-specific items marked not applicable when appropriate rather than fabricated:

### 1. Discover before imposing technology

Determine the actual API style, existing stack, project conventions, canonical requirements and current consumer contract. Do not force REST, HTTP, OpenAPI or any framework merely because they are common choices.

### 2. Externally observable contract

Before implementation is considered sufficiently defined, identify or preserve the relevant contract surface:

- operations, messages or callable behavior;
- request/input shape and validation;
- response/output shape;
- public error behavior;
- authentication and authorization expectations;
- compatibility/versioning expectations.

Do not recreate specifications merely for ceremony when an authoritative contract already exists.

### 3. Compatibility and consumer preservation

For an existing API, treat backward compatibility and versioning impact as mandatory considerations. A breaking contract change requires explicit authority and impact analysis rather than being introduced as an implementation convenience.

### 4. Protocol-relevant semantics

Evaluate only where applicable:

- idempotency and retries;
- concurrency/conflict behavior;
- pagination/filtering/query limits;
- resource/rate limits;
- serialization/content types;
- date/time and timezone semantics;
- numeric precision;
- enum/nullability/optional-field behavior.

These are conditional concerns, not a mandate to add features that the product does not require.

### 5. Security and trust boundaries

Treat external input and trust boundaries as untrusted. Where relevant, enforce:

- authentication;
- operation/resource authorization;
- ownership or tenant isolation;
- input validation;
- secret/credential protection;
- sanitized public errors that do not expose internal diagnostics, database details or stack information.

### 6. Verification

Changed API behavior must be supported by the smallest sufficient verification set, normally combining:

- contract-focused tests;
- implementation/integration tests;
- negative authorization and validation cases for protected surfaces;
- regression coverage for behavior that must remain stable;
- protocol-specific/environmental E2E validation when the required runtime is actually available.

Do not claim an environmental gate passed when only local/static/unit evidence exists.

### 7. Completion and fan-in

API work is locally complete only when the changed contract is implemented and wired, required verification passes, in-scope security/code-review findings are resolved, and parallel work has converged through explicit integration/fan-in where applicable.

Remaining environment-dependent checks must be classified explicitly instead of being hidden behind a generic `DONE` status.

## Release artifacts produced by API work

API governance does not prescribe how a ZIP, plugin package, runtime bundle, or other installable artifact must be assembled. When the delegated work also **creates or regenerates a release artifact**, the separate runtime policy `ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1` applies automatically at the same `TaskPackage` boundary.

This separation is intentional: API governance protects contracts and trust boundaries, while release-artifact governance protects source-to-package traceability, runtime-only composition, archive integrity, checksum evidence, and the distinction between packaging and deployment authority.

See `docs/process/RELEASE-ARTIFACT-GOVERNANCE.md`.

## Interaction with project governance

This global policy is additive. The precedence is:

```text
approved project facts / explicit human authority
        ↓
project-specific governance and canonical contracts
        ↓
ADAPTIVE_API_GENERATION_POLICY_V1 minimum obligations
        ↓
framework/tool-specific implementation choices
```

A project may be stricter. It must not silently weaken security, compatibility or verification obligations merely because a framework makes a shortcut convenient.

If two authoritative project sources conflict or a material business/API decision is missing, the Adaptive must surface the conflict or obtain the necessary decision instead of inventing a rule.

## Non-goals

This policy does not prescribe:

- REST over GraphQL/gRPC/RPC/events;
- HTTP when the interface is not HTTP-based;
- OpenAPI for every API style;
- JSON as the universal representation;
- a programming language;
- a web framework;
- database technology;
- deployment platform;
- a fixed architecture pattern;
- a fixed number of workers or tests.

## Implementation boundary

The mandatory enforcement lives in `src/domain/api_generation_policy.py` and is applied by `TaskPackage` before delegated execution. This location is deliberate: project prompts remain useful entry points, but the invariant does not depend on a user remembering to invoke one particular prompt.

The detector must remain conservative enough to distinguish **creating/changing an API surface** from merely **consuming an external API**. Future changes to the detector or policy require regression tests covering both activation and non-activation cases.
