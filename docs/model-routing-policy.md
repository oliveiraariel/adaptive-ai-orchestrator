# Adaptive AI Orchestrator — Model and Thinking Routing Policy

## Purpose

This policy controls both which LLM Adaptive assigns to each delegated OpenClaw execution and how much reasoning effort the execution should receive. It is intentionally simple, deterministic, auditable, and enforced in code rather than relying only on prompts.

The goals are:

1. reserve the strongest model for analytical, managerial, architectural, governance, high-stakes, security and code-review responsibilities;
2. use the economical model for routine or mechanical work, including first-pass code and test implementation when a stronger model is not justified;
3. give substantive coding and testing `high` reasoning even when the economical model is selected;
4. keep routine non-code work at `medium` reasoning;
5. escalate code/test work to a code-specialist model when a prior attempt requires revision or when the task is explicitly corrective/remedial;
6. preserve explicit model and compatible thinking choices supplied by the caller;
7. keep an append-only history of model selection, thinking selection, execution status, elapsed time and final evaluation verdict.

## Default routing matrix

| Tier / task class | Default model | Thinking | Intended use |
| --- | --- | --- | --- |
| `strong` | `openai/gpt-5.6-sol` | `high` | Planning, architecture, governance, high-stakes analysis, managerial/strategic work, security review, code review and similar high-responsibility tasks |
| `economy` — code/test | `openai/gpt-5.6-luna` | `high` | First-pass implementation, coding and testing when Sol is unnecessary |
| `economy` — routine non-code | `openai/gpt-5.6-luna` | `medium` | Routine/mechanical work that does not justify deeper reasoning |
| `code-specialist` | `moonshot/kimi-k2.7-code` | provider-native | Corrective/remedial code or test work and code/test retries after an earlier attempt needs revision |
| `explicit` | caller supplied | caller supplied when compatible; otherwise task-derived | Intentional model/thinking override supplied by the caller |

The defaults can be changed without changing source code:

- `ADAPTIVE_STRONG_MODEL`
- `ADAPTIVE_ECONOMY_MODEL`
- `ADAPTIVE_CODE_SPECIALIST_MODEL`
- `ADAPTIVE_STRONG_THINKING`
- `ADAPTIVE_CODE_THINKING`
- `ADAPTIVE_ROUTINE_THINKING`

The default values are `high`, `high`, and `medium` for strong, coding, and routine reasoning respectively.

## Routing precedence

The runtime applies the rules in this order:

1. **Explicit model override** — if a model is explicitly supplied, Adaptive preserves it. A compatible explicit `thinking` value is also preserved. If thinking is omitted, Adaptive still derives reasoning effort from the task class.
2. **Strong-responsibility work** — planning/replanning, architecture, governance, analytical/managerial/strategic responsibilities, code review, security review/audit and clearly high-stakes decisions use GPT-5.6 Sol with `high` reasoning.
3. **Code/test remediation or retry** — code/test work on attempt 2 or later, or work explicitly describing remediation, failing tests, bug repair, refactoring, Clean Code, Single Responsibility or similar corrective work uses Kimi K2.7 Code. Adaptive does not send an OpenClaw thinking override for this model because its reasoning behavior is provider-native.
4. **Routine first-pass code/test work** — uses GPT-5.6 Luna with `high` reasoning.
5. **Routine non-code work** — uses GPT-5.6 Luna with `medium` reasoning.

Strong-responsibility classification has priority over the code-specialist rule. For example, a code-review Work Unit is a review responsibility and therefore uses Sol/High rather than being treated as mechanical code generation.

## Why model and thinking are separate decisions

Selecting a capable model does not by itself guarantee the intended reasoning effort. Adaptive therefore treats model selection and thinking selection as separate routing dimensions.

```text
Work Unit
    -> classify responsibility/task type
    -> select model
    -> select thinking policy
    -> dispatch both through the runtime boundary
```

Examples:

```text
routine non-code
    -> GPT-5.6 Luna / medium

first-pass coding or tests
    -> GPT-5.6 Luna / high

architecture / governance / security / code review
    -> GPT-5.6 Sol / high

code/test revision or remediation
    -> Kimi K2.7 Code / provider-native reasoning
```

This preserves the Adaptive principle: use deeper reasoning where it materially improves engineering work without forcing every low-risk mechanical task to run at the same effort level.

## Kimi K2.7 Code handling

`moonshot/kimi-k2.7-code` is treated as a provider-native reasoning model. Adaptive records the thinking policy as provider-native and leaves the runtime `thinking` value unset.

This is deliberate: the orchestrator must not manufacture a `high`, `xhigh`, or other OpenClaw reasoning override for Kimi K2.7 Code. Model routing remains explicit and auditable, while reasoning behavior is left to the provider/runtime contract for that model.

## Escalation behavior

A routine implementation starts on GPT-5.6 Luna with `high` thinking.

If that same code/test Work Unit reaches another attempt, Adaptive routes the next attempt to Kimi K2.7 Code automatically. Explicit remedial tasks can go directly to the code-specialist model even on their first attempt.

```text
routine implementation
    -> Luna / high
    -> accepted: finish
    -> revision/failure: retry
         -> Kimi K2.7 Code / provider-native reasoning
```

Important analytical or review work does not downgrade to an economy model merely because it contains code-related terms:

```text
architecture / governance / code review / high-stakes analysis
    -> Sol / high
```

## Enforcement point

The policy is enforced in `OpenClawAdapter.submit()` immediately before Adaptive sends a task to OpenClaw.

This is deliberate. The planner and project scheduler may leave `model`, `provider`, and `thinking` unspecified, but the runtime boundary always resolves the applicable model and reasoning policy before dispatch. Therefore the policy is not dependent on a project prompt remembering to request a model or a thinking level.

The routed `ResourceConfiguration` carries the resolved `thinking` value together with the model/provider selection.

## OpenClaw Gateway transport

For OpenAI Luna/Sol executions, Adaptive sends the resolved reasoning level using the OpenClaw Gateway `agent` RPC `thinking` parameter. Model selection continues to be applied through the existing session model override.

Adaptive intentionally does **not** patch privileged session thinking state. This means the Gateway client can retain its existing `operator.read` + `operator.write` scopes rather than requesting `operator.admin` solely to set reasoning effort.

When the resolved thinking policy is provider-native (currently Kimi K2.7 Code), the `thinking` parameter is omitted from the `agent` RPC.

## Audit history

The default append-only history is stored at:

```text
~/.local/state/adaptive-ai-orchestrator/model-routing-history.jsonl
```

The path can be changed with:

```text
ADAPTIVE_MODEL_ROUTING_LOG
```

Each line is one JSON object. The file is created with restrictive permissions when supported by the filesystem.

The routing audit now records both model and reasoning policy. Relevant fields include:

- `model`
- `provider`
- `tier`
- `reason`
- `thinking`
- `thinking_reason`
- `attempt`
- `escalated_from`

For provider-native reasoning, `thinking` is `null` and `thinking_reason` explains why Adaptive intentionally omitted an override.

### `routing-selected`

Written before dispatch. It records the selected model/provider, model tier/reason, thinking level/reason, attempt number and any escalation source. If this event cannot be written, Adaptive does not start the execution unlogged.

### `model-dispatch` and `runtime-result`

These record the execution id, actual routed model, routed thinking policy, runtime outcome and elapsed time. Runtime errors and cancellation receive their own audit events.

### `evaluation-finalized`

Written after Adaptive evaluates the result. It records the execution id, final verdict and resulting Work Unit state.

Because the events share the execution id, the history can answer questions such as:

- which model and thinking level completed a Work Unit on the first attempt;
- which model required a second attempt;
- when a Luna/High implementation was escalated to Kimi;
- which model had runtime failures;
- which model received `ACCEPTED`, `RETURNED`, `REJECTED` or `BLOCKED` verdicts;
- approximate elapsed execution time per model and Work Unit.

Repeated attempts are additionally identifiable through `work_unit_id` and `attempt`.

## Examples

| Work Unit | Expected route |
| --- | --- |
| Define application architecture | GPT-5.6 Sol / High |
| Analyze governance/gates | GPT-5.6 Sol / High |
| Perform backend code review | GPT-5.6 Sol / High |
| Implement a routine PHP repository, attempt 1 | GPT-5.6 Luna / High |
| Generate routine unit tests, attempt 1 | GPT-5.6 Luna / High |
| Perform routine non-code file organization | GPT-5.6 Luna / Medium |
| Retry the same implementation after revision | Kimi K2.7 Code / provider-native |
| Fix failing tests and refactor for Single Responsibility | Kimi K2.7 Code / provider-native |
| Explicit `openai/gpt-5.6-sol` + `xhigh` diagnostic run | Explicit Sol / XHigh |

## Interpretation of the history

The log provides evidence; it does not claim that one model or one reasoning level is universally better based on one execution. Useful comparisons should consider task type, responsibility tier, reasoning effort, number of attempts, final verdict and elapsed time together.

A practical future report can aggregate the JSONL history by model, thinking level and task class to show first-pass acceptance rate, escalation frequency, blocked/rejected outcomes and execution time. The routing policy itself remains intentionally simple until accumulated evidence justifies changing it.
