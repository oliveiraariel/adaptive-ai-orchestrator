# Adaptive Runtime Intelligence

## Purpose

Adaptive Runtime Intelligence extends model routing with operational diagnosis.

Routing answers:

> Which model should execute this Work Unit?

Runtime Intelligence answers:

> Is that route actually healthy and correctly configured now? If not, what
> failed, how confident are we about the cause, what is the safest remediation,
> and what evidence should be retained for future governed learning?

The subsystem is deliberately conservative. Runtime incidents may influence the
current execution and temporary provider health, but they do **not** silently
rewrite permanent routing, security or cost policy.

## Components

```text
ModelRoutingPolicy
        |
        v
RuntimePreflight
        |
        v
OpenClawGatewayClient
        |
        +--> IncidentClassifier
        |         |
        |         v
        |   RemediationPolicy
        |         |
        |         v
        |   ProviderHealthPolicy
        |
        +--> ProviderTelemetryStore
```

### `IncidentClassifier`

Transforms raw provider/runtime failures into a structured
`ProviderIncident`.

The classifier explicitly avoids the common anti-pattern:

```text
HTTP 429 -> "rate limit" -> retry blindly
```

Instead it distinguishes, when evidence is available:

- project daily budget;
- project monthly budget;
- organization budget;
- TPM;
- RPM;
- concurrency;
- unknown provider throttle;
- billing/credits;
- authentication;
- timeout;
- provider unavailability;
- model/configuration resolution.

A generic 429 remains `provider_rate_limit_unknown` until stronger evidence
exists. This is intentional: HTTP status is a symptom, not always a root cause.

### `RemediationPolicy`

Maps incidents to safe runtime actions.

Examples:

| Incident | Same-model retry | Fallback | Human action |
| --- | --- | --- | --- |
| project daily/monthly budget exhausted | no | yes | yes |
| insufficient credits | no | yes | yes |
| invalid credential | no | yes | yes |
| TPM/RPM pressure | bounded | yes | no |
| concurrency pressure | bounded | yes | no |
| generic 429 | bounded | yes | no |
| timeout/provider overload | bounded | yes | no |
| model-resolution/configuration error | no | yes | yes |

No remediation rule permanently changes model policy.

### `ProviderHealthPolicy`

Provides a temporary in-memory circuit breaker.

```text
CLOSED
  |
  | repeated operational failures
  v
OPEN
  |
  | cooldown elapsed
  v
HALF_OPEN
  |
  | one successful probe
  v
CLOSED
```

Non-retryable structural incidents open the route immediately. Retryable
incidents open after a bounded threshold. This state is intentionally not
persisted across process lifetimes.

### `RuntimePreflight`

Performs read-only integrity checks using a `RuntimeSnapshot`.

Current checks include:

- credential provider mismatch;
- credential product/model-route mismatch;
- Kimi Platform vs Kimi Code route confusion;
- OpenClaw core/provider-plugin version mismatch;
- authored provider catalog shadowing a bundled/discovered model;
- large native-context vs small effective-session-context mismatch.

Blocking findings are configuration errors. Warnings are diagnostic evidence and
must not trigger destructive mutation automatically.

### `ProviderTelemetryStore`

Writes sanitized structured incidents to:

```text
~/.local/state/adaptive-ai-orchestrator/provider-incidents.jsonl
```

Override with:

```text
ADAPTIVE_PROVIDER_INCIDENT_LOG=/custom/path/provider-incidents.jsonl
```

The store records structured incident/remediation fields, not raw credentials.

## Credential provenance is a first-class concept

A model name is not enough to choose an authentication route.

Examples:

```text
Kimi Platform
  provider/route : moonshot/kimi-*
  billing        : pay-as-you-go credits
  endpoint family: Moonshot Platform

Kimi Code
  provider/route : kimi/*
  billing        : membership/subscription
  endpoint family: Kimi Code
```

Likewise:

```text
OpenAI Platform API key
!=
ChatGPT/Codex OAuth subscription access
```

`CredentialProfile` therefore tracks:

- provider;
- product;
- auth type;
- billing mode;
- endpoint family;
- allowed model-route prefixes.

Raw secret material must never be stored in this profile or telemetry.

## Operational lessons encoded from real troubleshooting

### 1. Provider route and credential product must agree

Symptom:

```text
Unknown model: kimi/k3
```

A plausible cause is not merely "the model does not exist." The credential may
belong to Kimi Platform while the selected route belongs to Kimi Code.

Diagnostic order:

1. identify credential product;
2. identify selected provider/model route;
3. identify endpoint family;
4. validate compatibility;
5. only then investigate model retirement/availability.

### 2. Missing model does not imply broken plugin

A bundled provider can advertise K3 while an authored provider model list hides
it from the effective catalog.

Diagnostic order:

1. inspect core version;
2. inspect plugin `packageVersion`, `builtWithOpenClawVersion`,
   `status`, and `activated`;
3. compare plugin model catalog with effective `models list --refresh`;
4. inspect authored `models.providers.<provider>.models`;
5. inspect allowlist;
6. mutate/reinstall only when evidence justifies it.

### 3. Authored provider catalogs can shadow discovery

This configuration is powerful:

```text
models.providers.moonshot.models
```

It is not equivalent to per-model runtime parameters.

If an authored list contains only K2.7, discovery can effectively expose only
that declared subset. A safe output-token cap instead belongs in per-model
runtime settings such as:

```text
agents.defaults.models["moonshot/kimi-k3"].params.maxTokens
```

This preserves the provider catalog while constraining response budget.

### 4. Context window and max output are independent

```text
contextWindow = how much context the route can accept
maxTokens     = maximum response/output budget
```

Reducing `maxTokens` can lower rate/cost pressure without reducing a 1M native
context window.

### 5. Generic 429 requires correlation

Before concluding "TPM exceeded", correlate:

- project daily budget;
- project monthly budget;
- organization budget;
- TPM;
- RPM;
- concurrency;
- provider temporary throttle;
- usage-window policy.

Structural budget exhaustion should suppress repeated same-route retries.

### 6. Retry storms are themselves an operational risk

Repeated automatic attempts can:

- consume rate-window capacity;
- increase provider load;
- increase latency;
- create additional billable/cache work;
- hide the original root cause.

Adaptive therefore records a structured incident and can open a temporary
circuit instead of treating retries as universally harmless.

### 7. Preserve valuable historical sessions

A long-running owner session should not be discarded simply because its current
model route fails.

Before creating a new session:

1. identify whether failure is session-specific or provider/configuration-wide;
2. test a clean session only as a diagnostic isolator when necessary;
3. preserve historical state when a model switch can safely reuse it;
4. verify effective context after the switch.

### 8. Context metadata can be stale after a live switch

A selected model can advertise a ~1M native context while the active session
still reports or preflights against an older ~200k budget.

Adaptive flags this as `context-window-mismatch` so operators inspect:

- session `contextTokens`;
- configured context caps;
- live-switch pending state;
- catalog metadata;
- runtime refresh behavior.

## Current model policy

The Runtime Intelligence layer is subordinate to the active economy-first
routing policy:

```text
high complexity / orchestration / systemic architecture
    -> moonshot/kimi-k2.7-code
    -> provider-native reasoning
    -> paid Moonshot route only while healthy/funded

medium / low complexity
    -> openai/gpt-5.6-luna
    -> low
    -> explicit OpenAI OAuth profile

K2.7 operational failure
    -> openai/gpt-5.6-luna
    -> low / OAuth

Luna operational failure
    -> surface failure
    -> no automatic escalation to paid Kimi

moonshot/kimi-k3
openai/gpt-5.6-sol
    -> manual only / excluded from automatic routing
```

A policy-routed Luna dispatch is marked with
`adaptive-auth-product:openai-oauth`. If no explicit OAuth auth profile is
configured, the Gateway fails before dispatch rather than silently selecting a
paid OpenAI Platform API-key profile.

## Governed operational learning

Runtime Intelligence is designed around a promotion pipeline:

```text
incident
  -> evidence
  -> structured classification
  -> safe remediation
  -> telemetry
  -> recurring pattern
  -> proposed operational lesson
  -> tests/review
  -> governed promotion into code/knowledge
```

This prevents one transient incident from teaching the system a permanent false
rule.

The machine-readable lessons currently live at:

```text
knowledge/provider-operational-lessons.json
```

They are operational knowledge, not executable permission to mutate security,
billing, routing or provider configuration.

## Safety boundaries

Adaptive Runtime Intelligence must not:

- expose or persist raw API keys;
- automatically buy credits or subscriptions;
- silently raise provider budgets;
- silently widen concurrency or rate limits;
- silently rewrite permanent routing policy;
- reinstall/update providers solely from one weak symptom;
- treat every 429 as TPM;
- treat a ChatGPT subscription as OpenAI API credit;
- treat Kimi Platform and Kimi Code credentials as interchangeable.

## Testing strategy

The subsystem has deterministic tests for:

- generic 429 vs project-budget evidence;
- TPM/RPM/concurrency distinction;
- OpenAI insufficient credits;
- unknown-model/configuration incidents;
- Kimi Platform vs Kimi Code credential routes;
- provider catalog shadowing;
- stale effective context;
- plugin/core version mismatch;
- budget remediation;
- circuit-breaker opening/half-open/reset;
- sanitized provider telemetry;
- structured OpenClaw failover metadata.

Future live tests can add provider-specific evidence adapters without changing
these domain rules.
