# Adaptive AI Orchestrator — Model, Thinking and Failover Policy

## Purpose

Adaptive uses a role-aware model policy: the orchestration model keeps the
global project picture, the code specialist handles deep implementation work,
and the economy model handles routine execution.

The active automatic policy is:

- **Kimi K3** (`moonshot/kimi-k3`) for orchestration, project discovery, planning,
  decomposition, governance, synthesis/fan-in and systemic/high-level
  architecture;
- **Moonshot Kimi K3 uses `max` reasoning** on the direct Moonshot route;
  OpenClaw 2026.9.4 enforces this provider contract;
- **Kimi K2.7 Code** (`moonshot/kimi-k2.7-code`) for code review, code-level
  architecture, complex implementation, substantial refactors, retries and
  remediation;
- **GPT-5.6 Luna** (`openai/gpt-5.6-luna`) for routine/mechanical work and
  routine first-pass code/tests at `medium` reasoning;
- **GPT-5.6 Sol is excluded from automatic Adaptive routing by default**.

The OpenClaw owner session may also be pinned manually to `moonshot/kimi-k3` with
`max` reasoning on the direct Moonshot route. That owner-session choice is
distinct from worker routing, but it intentionally matches the default
orchestration role.

## Default routing matrix

| Responsibility | Default model | Thinking |
| --- | --- | --- |
| Owner/orchestrator, project discovery, planning, decomposition, governance, synthesis/fan-in | `moonshot/kimi-k3` | `max` |
| Systemic/high-level architecture and broad project analysis | `moonshot/kimi-k3` | `max` |
| Critical systemic decision, high-stakes analysis, security architecture | `moonshot/kimi-k3` | `max` |
| Code review or architecture applied directly to code | `moonshot/kimi-k2.7-code` | provider-native |
| Complex first-pass implementation or tests | `moonshot/kimi-k2.7-code` | provider-native |
| Retry, remediation, failing tests, substantial refactor | `moonshot/kimi-k2.7-code` | provider-native |
| Routine first-pass implementation or tests | `openai/gpt-5.6-luna` | `medium` |
| Routine/mechanical non-code work | `openai/gpt-5.6-luna` | `medium` |

Examples of complex-code signals include transactional/atomic work, rollback,
authorization/authentication, concurrency, financial consistency, migrations,
multi-file cross-cutting changes, state machines and idempotency.

The architectural split is intentional:

```text
systemic / high-level architecture
    -> Kimi K3

architecture applied directly to code / code review
    -> Kimi K2.7 Code
```

## Operational failover

Adaptive keeps one operational fallback attempt per execution.

The default routes are:

```text
Luna routine work
    -> K2.7 Code

K3 orchestration/systemic work
    -> K2.7 Code

K2.7 Code specialist work
    -> Luna
```

This means a K3 provider failure does not demote orchestration directly to the
economy model; it first moves to the code-capable K2.7 route.

Failover-worthy categories include:

- billing / insufficient credits;
- rate limit / quota window / throttling;
- authentication failure;
- timeout;
- provider overload or unavailability;
- model unavailable / not found in the active provider route.

Semantic quality failures are **not** operational failover triggers. Acceptance
criteria failures and revision requests remain Adaptive evaluation/replanning
concerns.

The same Adaptive-owned OpenClaw session key is reused during failover. The
fallback receives recovery context instructing it to inspect transcript and
repository state, preserve completed work and continue idempotently.

## Model selection precedence

The runtime applies rules in this order:

1. preserve a caller-selected model when it is not disabled;
2. route explicit code-review/code-level-architecture responsibilities to
   K2.7 Code;
3. route orchestration/planning/governance/systemic architecture to K3;
4. retain critical-systemic classification while Moonshot K3 remains at provider-required `max`;
5. route code/test retry or remediation to K2.7 Code;
6. route complex first-pass code/test to K2.7 Code;
7. route routine first-pass code/test to Luna / `medium`;
8. route routine non-code work to Luna / `medium`.

K2.7 Code keeps provider-native reasoning and Adaptive does not inject a
generic reasoning level for it.

## Sol policy

`openai/gpt-5.6-sol` is excluded from automatic routing by default:

```text
ADAPTIVE_DISABLED_MODELS=openai/gpt-5.6-sol
```

This does not prevent a user from keeping Sol available in OpenClaw's manual
model allowlist. OpenClaw model availability and Adaptive automatic routing are
separate controls.

## Environment overrides

Current defaults:

```text
ADAPTIVE_STRONG_MODEL=moonshot/kimi-k3
ADAPTIVE_ECONOMY_MODEL=openai/gpt-5.6-luna
ADAPTIVE_CODE_SPECIALIST_MODEL=moonshot/kimi-k2.7-code

ADAPTIVE_STRONG_THINKING=max
ADAPTIVE_CRITICAL_THINKING=max
ADAPTIVE_CODE_THINKING=medium
ADAPTIVE_ROUTINE_THINKING=medium

ADAPTIVE_DISABLED_MODELS=openai/gpt-5.6-sol
```

`ADAPTIVE_STRONG_MODEL` now represents the orchestration/systemic model. The
existing environment variable name is retained for compatibility even though
its role is more specific than the historical "strong model" label.

## Enforcement points

Task classification and primary routing are enforced in
`OpenClawAdapter.submit()` through `ModelRoutingPolicy`.

Operational provider failover is enforced in
`OpenClawGatewayClient.retrieve_result()`, because billing/rate/auth/provider
failures become visible only after an OpenClaw run executes.

Provider failures are first classified by Adaptive Runtime Intelligence into
structured incident categories/subtypes and passed through remediation and
temporary provider-health policy. See [Adaptive Runtime Intelligence](runtime-intelligence.md).

## Audit and observability

Routing history remains append-only at:

```text
~/.local/state/adaptive-ai-orchestrator/model-routing-history.jsonl
```

Relevant audit fields include model, provider, tier, thinking, failover source,
failover target, failure reason, runtime attempt and final runtime status.

## Cost-policy intent

The policy optimizes for:

```text
global understanding / orchestration -> Moonshot K3 max
critical systemic work              -> Moonshot K3 max
deep code work                      -> K2.7 Code
routine work                        -> Luna medium
operational failure                 -> one role-compatible fallback
Sol                                 -> manual availability only, disabled automatically
```

The policy can be revisited using acceptance rate, retries, elapsed time,
context usage and actual/estimated cost.
