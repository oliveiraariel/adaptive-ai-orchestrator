# Adaptive AI Orchestrator — Economy-First Model, Auth and Failover Policy

## Purpose

Adaptive uses a cost-aware, role-aware policy with two automatic model families:

- **Kimi K2.7 Code** for high-complexity work while the Moonshot route is funded
  and operational;
- **GPT-5.6 Luna via OpenAI OAuth** for medium/low-complexity work and as the
  cost-safe fallback when K2.7 cannot run.

Premium models remain manually available but are excluded from automatic
routing:

- **Kimi K3**;
- **GPT-5.6 Sol**.

The policy intentionally optimizes sustainable project execution before maximum
model strength.

## Active routing matrix

| Responsibility | Automatic model | Thinking | Auth |
| --- | --- | --- | --- |
| Owner/orchestration with high-complexity planning or systemic analysis | `moonshot/kimi-k2.7-code` | provider-native | Moonshot API key |
| Systemic/high-level architecture | `moonshot/kimi-k2.7-code` | provider-native | Moonshot API key |
| Critical/high-complexity analysis | `moonshot/kimi-k2.7-code` | provider-native | Moonshot API key |
| Code review / architecture applied to code | `moonshot/kimi-k2.7-code` | provider-native | Moonshot API key |
| Complex implementation/tests | `moonshot/kimi-k2.7-code` | provider-native | Moonshot API key |
| Retry/remediation/substantial refactor | `moonshot/kimi-k2.7-code` | provider-native | Moonshot API key |
| Routine first-pass implementation/tests | `openai/gpt-5.6-luna` | `low` | explicit OpenAI OAuth profile |
| Routine/mechanical non-code work | `openai/gpt-5.6-luna` | `low` | explicit OpenAI OAuth profile |

High-complexity signals include transactional/atomic behavior, rollback,
authorization/authentication, security, concurrency, financial consistency,
migrations, cross-cutting multi-file work, state machines and idempotency.

## Premium-model policy

The following models are excluded from automatic Adaptive routing:

```text
moonshot/kimi-k3
openai/gpt-5.6-sol
```

They may remain in the OpenClaw model catalog and may still be selected manually
by the operator. Availability in OpenClaw and permission for automatic Adaptive
routing are separate concerns.

## OpenAI OAuth is explicit and fail-closed

The economy route is not merely:

```text
openai/gpt-5.6-luna
```

It is operationally:

```text
openai/gpt-5.6-luna
+ explicit OpenAI OAuth auth profile
+ low reasoning
```

The OAuth profile ID is supplied through:

```text
ADAPTIVE_OPENAI_OAUTH_PROFILE=<openclaw-auth-profile-id>
```

Adaptive propagates that profile into OpenClaw's model selection using the
supported `provider/model@profile` form.

Policy-routed Luna work includes:

```text
adaptive-auth-product:openai-oauth
```

If that constraint is present but no explicit auth profile is configured, the
Gateway fails **before dispatch** instead of silently allowing OpenClaw to select
a paid OpenAI Platform API-key profile.

This protects the intended cost policy:

```text
ChatGPT/OAuth usage
!=
OpenAI Platform API-key billing
```

## Kimi authentication

The default K2.7 auth profile is:

```text
ADAPTIVE_KIMI_AUTH_PROFILE=moonshot:api-key
```

It remains configurable because OpenClaw profile IDs are local installation
identities.

## Operational failover

Adaptive keeps at most one model-level operational fallback attempt.

The automatic route is intentionally asymmetric:

```text
HIGH COMPLEXITY

K2.7 Code
    |
    | billing / quota / auth / timeout / unavailable
    v
GPT-5.6 Luna OAuth Low
```

For medium/low work:

```text
GPT-5.6 Luna OAuth Low
    |
    | operational failure
    v
surface failure
```

Luna **does not automatically escalate to paid Kimi**. This prevents routine
tasks from silently increasing paid-provider spend.

K3 and Sol are never automatic fallback candidates.

## "K2.7 only when balance/availability exists"

Adaptive does not query a Moonshot billing dashboard before every task.

Instead:

1. high-complexity work selects K2.7;
2. Runtime Intelligence classifies provider failures;
3. billing/quota/unavailability evidence marks the route unhealthy;
4. the current execution may fall back once to Luna OAuth Low;
5. the temporary provider-health circuit prevents repeated blind dispatches.

Therefore K2.7 remains the preferred high-complexity route while healthy, but an
unfunded/unavailable route is not retried indefinitely.

## Model selection precedence

The runtime applies rules in this order:

1. preserve an explicit caller-selected model only when it is not disabled;
2. route explicit code-review/code-level-architecture responsibilities to K2.7;
3. route orchestration/planning/governance/systemic/high-complexity work to K2.7;
4. route code/test retry or remediation to K2.7;
5. route complex first-pass code/test work to K2.7;
6. route routine first-pass code/test work to Luna OAuth Low;
7. route routine/mechanical non-code work to Luna OAuth Low.

K2.7 keeps provider-native reasoning. Adaptive does not inject a generic
reasoning level into that route.

## Environment defaults

```text
ADAPTIVE_STRONG_MODEL=moonshot/kimi-k2.7-code
ADAPTIVE_ECONOMY_MODEL=openai/gpt-5.6-luna
ADAPTIVE_CODE_SPECIALIST_MODEL=moonshot/kimi-k2.7-code

ADAPTIVE_STRONG_THINKING=low
ADAPTIVE_CRITICAL_THINKING=low
ADAPTIVE_CODE_THINKING=low
ADAPTIVE_ROUTINE_THINKING=low

ADAPTIVE_KIMI_AUTH_PROFILE=moonshot:api-key
ADAPTIVE_OPENAI_OAUTH_PROFILE=<required local OpenClaw OAuth profile id>

ADAPTIVE_DISABLED_MODELS=moonshot/kimi-k3,openai/gpt-5.6-sol
```

`ADAPTIVE_STRONG_MODEL` is retained for compatibility even though the default
strong/high-complexity route and code-specialist route now point to the same
K2.7 model.

## Enforcement points

Primary routing is enforced in:

```text
OpenClawAdapter.submit()
    -> ModelRoutingPolicy
```

The adapter propagates:

- model;
- provider;
- auth profile;
- thinking;
- routing constraints.

OpenClaw dispatch is enforced in:

```text
OpenClawGatewayClient._submit_task()
```

For an explicit auth profile, the Gateway patches the session model as:

```text
provider/model@auth-profile
```

Operational failover is enforced in:

```text
OpenClawGatewayClient.retrieve_result()
```

Provider failures are classified through Adaptive Runtime Intelligence before
fallback is considered.

## Audit and observability

Model routing continues to write append-only history at:

```text
~/.local/state/adaptive-ai-orchestrator/model-routing-history.jsonl
```

The audit records whether an auth profile was configured and the auth product
class, but it does not need to persist the profile identifier itself.

Provider incident telemetry remains at:

```text
~/.local/state/adaptive-ai-orchestrator/provider-incidents.jsonl
```

## Cost-policy intent

```text
high complexity
    -> K2.7 Code when healthy/funded
    -> Luna OAuth Low on operational failure

medium / low complexity
    -> Luna OAuth Low

Kimi K3
    -> manual only

GPT-5.6 Sol
    -> manual only

Luna failure
    -> do not silently escalate to a paid Kimi route
```

This policy can be revisited using acceptance rate, retries, task complexity,
provider availability, OAuth quota, actual paid spend and elapsed time.
