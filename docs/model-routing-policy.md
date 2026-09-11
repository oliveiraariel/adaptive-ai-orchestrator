# Adaptive AI Orchestrator — Model, Thinking and Failover Policy

## Purpose

Adaptive uses a deliberately small active model set to control cost while keeping
strong engineering performance.

The active policy is:

- **Kimi K2.7 Code** for strong/complex responsibilities, complex first-pass
  code, architecture, governance, security, code review, retries and
  remediation;
- **GPT-5.6 Luna** for routine/mechanical work and routine first-pass code;
- **Luna always runs at `medium` reasoning** under this policy;
- **Kimi K2.7 Code uses provider-native reasoning**;
- **GPT-5.6 Sol is disabled from automatic Adaptive routing**.

The policy remains deterministic and auditable at the runtime boundary.

## Default routing matrix

| Task class | Default model | Thinking |
| --- | --- | --- |
| Planning, architecture, governance, security, high-stakes analysis, code review | `moonshot/kimi-k2.7-code` | provider-native |
| Complex first-pass implementation or tests | `moonshot/kimi-k2.7-code` | provider-native |
| Retry, remediation, failing tests, substantial refactor | `moonshot/kimi-k2.7-code` | provider-native |
| Routine first-pass implementation or tests | `openai/gpt-5.6-luna` | `medium` |
| Routine/mechanical non-code work | `openai/gpt-5.6-luna` | `medium` |

Examples of complexity signals include transactional/atomic work, rollback,
authorization/authentication, concurrency, financial consistency, migrations,
multi-file cross-cutting changes, state machines and idempotency.

## Sol policy

`openai/gpt-5.6-sol` is excluded from automatic routing by default.

The default denylist is controlled by:

```text
ADAPTIVE_DISABLED_MODELS=openai/gpt-5.6-sol
```

This prevents an old explicit Sol override from silently reintroducing Sol into
normal Adaptive execution. The denylist can be changed intentionally through the
environment when the operating policy changes in the future.

## Operational failover

Adaptive/OpenClaw uses a two-model operational failover pair:

```text
Luna  <->  Kimi K2.7 Code
```

If the selected model fails before producing a usable result because of an
operational provider problem, the Gateway client automatically continues the
same worker session with the other active model.

Failover-worthy categories are:

- billing / insufficient credits;
- rate limit / quota window / throttling;
- authentication failure;
- timeout;
- provider overload or unavailability;
- model unavailable / not found in the active provider route.

Semantic quality failures are **not** operational failover triggers. For
example, failing acceptance criteria or a result that needs revision remains an
Adaptive evaluation/replanning concern.

### Luna to Kimi

Typical example:

```text
routine first-pass code
    -> Luna / medium
    -> OpenAI billing exhausted
    -> same worker session switches to Kimi K2.7 Code
    -> provider-native reasoning
    -> continue from existing transcript/repository state
```

### Kimi to Luna

The reverse route is also available for operational failures:

```text
architecture / complex code
    -> Kimi K2.7 Code
    -> Moonshot rate limit / provider unavailable
    -> same worker session switches to Luna / medium
```

If the second model also fails, the execution remains failed/blocked. Adaptive
never introduces Sol as a hidden third fallback.

## Continuation safety

Operational failover does not start a new logical Work Unit.

The same Adaptive-owned OpenClaw session key is reused. The fallback dispatch:

1. switches the session model;
2. uses a distinct runtime idempotency key;
3. adds recovery context instructing the worker to inspect transcript and
   repository state first;
4. preserves already-completed work and side effects;
5. instructs the worker not to blindly repeat completed actions;
6. continues idempotently from the interrupted point.

This is important for repository-writing Work Units.

## Model selection precedence

The runtime applies the rules in this order:

1. a caller-selected model is preserved only if it is not disabled;
2. strong responsibilities route to Kimi;
3. code/test retry or remediation routes to Kimi;
4. complex first-pass code/test routes to Kimi;
5. routine first-pass code/test routes to Luna / medium;
6. routine non-code work routes to Luna / medium.

Kimi K2.7 Code always keeps provider-native reasoning. Adaptive does not invent
OpenClaw `high` or `xhigh` values for it.

## Environment overrides

The active model ids can still be changed without modifying source:

```text
ADAPTIVE_STRONG_MODEL
ADAPTIVE_ECONOMY_MODEL
ADAPTIVE_CODE_SPECIALIST_MODEL
ADAPTIVE_STRONG_THINKING
ADAPTIVE_CODE_THINKING
ADAPTIVE_ROUTINE_THINKING
ADAPTIVE_DISABLED_MODELS
```

Current defaults are:

```text
ADAPTIVE_STRONG_MODEL=moonshot/kimi-k2.7-code
ADAPTIVE_ECONOMY_MODEL=openai/gpt-5.6-luna
ADAPTIVE_CODE_SPECIALIST_MODEL=moonshot/kimi-k2.7-code

ADAPTIVE_STRONG_THINKING=medium
ADAPTIVE_CODE_THINKING=medium
ADAPTIVE_ROUTINE_THINKING=medium

ADAPTIVE_DISABLED_MODELS=openai/gpt-5.6-sol
```

For Kimi K2.7 Code, provider-native reasoning overrides the generic thinking
value.

## Enforcement points

Task classification and primary model routing are enforced in
`OpenClawAdapter.submit()` through `ModelRoutingPolicy`.

Operational provider failover is enforced in
`OpenClawGatewayClient.retrieve_result()`, because provider billing/rate/auth
failures become visible only after the OpenClaw run has executed.

The Gateway client keeps the application-level execution identity stable while
moving the original execution reference onto the successful runtime candidate.

## Audit and observability

The append-only model-routing history remains:

```text
~/.local/state/adaptive-ai-orchestrator/model-routing-history.jsonl
```

When failover occurs, Adaptive records a `model-failover` event and the final
`runtime-result` records the model that actually completed the Work Unit.

Relevant fields include:

- `from_model`;
- `to_model`;
- `to_provider`;
- `failure_reason`;
- `runtime_attempt`;
- final `model`, `provider`, `thinking` and runtime status.

This allows later comparison by **accepted Work Unit cost**, not only by
per-token price.

## Cost-policy intent

The policy intentionally optimizes for:

```text
routine work -> cheap Luna / medium
complex work -> Kimi directly
Luna failure/revision -> Kimi
provider operational failure -> automatic cross-provider failover
Sol -> disabled
```

The policy can be revisited later using accumulated routing history, acceptance
rate, number of attempts, elapsed time and actual/estimated cost.
