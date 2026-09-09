# Adaptive AI Orchestrator — Model Routing Policy

## Purpose

This policy controls which LLM Adaptive assigns to each delegated OpenClaw execution. It is intentionally simple, deterministic, auditable, and enforced in code rather than relying only on prompts.

The goals are:

1. reserve the strongest model for analytical, managerial, architectural, governance, high-stakes, security and code-review responsibilities;
2. use the economical model for routine or mechanical work, including first-pass code and test implementation when a stronger model is not justified;
3. escalate code/test work to a code-specialist model when a prior attempt requires revision or when the task is explicitly corrective/remedial;
4. keep an append-only history of model selection, execution status, elapsed time and final evaluation verdict;
5. preserve an explicit model chosen by the caller as an intentional override.

## Default model tiers

| Tier | Default model | Intended use |
| --- | --- | --- |
| `strong` | `openai/gpt-5.6-sol` | Planning, architecture, governance, high-stakes analysis, managerial/strategic work, security review, code review and similar high-responsibility tasks |
| `economy` | `openai/gpt-5.6-luna` | Routine/mechanical work and first-pass implementation/testing when the stronger model is unnecessary |
| `code-specialist` | `moonshot/kimi-k2.7-code` | Corrective/remedial code or test work and code/test retries after an earlier attempt needs revision |
| `explicit` | caller supplied | Intentional model override supplied by the caller |

The defaults can be changed without changing source code:

- `ADAPTIVE_STRONG_MODEL`
- `ADAPTIVE_ECONOMY_MODEL`
- `ADAPTIVE_CODE_SPECIALIST_MODEL`

## Routing precedence

The runtime applies the rules in this order:

1. **Explicit model override** — if a model is explicitly supplied, Adaptive preserves it.
2. **Strong-responsibility work** — planning/replanning, architecture, governance, analytical/managerial/strategic responsibilities, code review, security review/audit and clearly high-stakes decisions use the strong model.
3. **Code/test remediation or retry** — code/test work on attempt 2 or later, or work explicitly describing remediation, failing tests, bug repair, refactoring, Clean Code, Single Responsibility or similar corrective work uses the code-specialist model.
4. **Routine work** — everything else uses the economy model.

Strong-responsibility classification has priority over the code-specialist rule. For example, a code-review Work Unit is a review responsibility and therefore uses the strong model rather than being treated as mechanical code generation.

## Escalation behavior

A routine implementation can start on `openai/gpt-5.6-luna`.

If that same code/test Work Unit reaches another attempt, Adaptive routes the next attempt to `moonshot/kimi-k2.7-code` automatically. Explicit remedial tasks can go directly to the code-specialist model even on their first attempt.

This supports the intended operating pattern:

```text
routine implementation
    -> Luna
    -> accepted: finish
    -> revision/failure: retry
         -> Kimi K2.7 Code
```

Important analytical or review work does not downgrade to an economy model merely because it contains code-related terms:

```text
architecture / governance / code review / high-stakes analysis
    -> GPT-5.6 Sol
```

## Enforcement point

The policy is enforced in `OpenClawAdapter.submit()` immediately before Adaptive sends a task to OpenClaw.

This is deliberate. The planner and project scheduler may leave `model` and `provider` unspecified, but the runtime boundary always resolves a concrete model before dispatch. Therefore the policy is not dependent on a project prompt remembering to request a model.

The same runtime boundary also preserves explicit model selections, so direct diagnostic or specialist runs remain possible.

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

The audit trail records three important stages:

### `routing-selected`

Written before dispatch. It records the selected model, provider, tier, reason, attempt number and any escalation source. If this event cannot be written, Adaptive does not start the execution unlogged.

### `model-dispatch` and `runtime-result`

These record the execution id, actual routed model, runtime outcome and elapsed time. Runtime errors and cancellation receive their own audit events.

### `evaluation-finalized`

Written after Adaptive evaluates the result. It records the execution id, final verdict and resulting Work Unit state.

Because `model-dispatch`, `runtime-result` and `evaluation-finalized` share the execution id, the history can answer questions such as:

- which model completed a Work Unit on the first attempt;
- which model required a second attempt;
- when a Luna implementation was escalated to Kimi;
- which model had runtime failures;
- which model received `ACCEPTED`, `RETURNED`, `REJECTED` or `BLOCKED` verdicts;
- approximate elapsed execution time per model and Work Unit.

Repeated attempts are additionally identifiable through `work_unit_id` and `attempt`.

## Examples

| Work Unit | Expected route |
| --- | --- |
| Define application architecture | GPT-5.6 Sol |
| Analyze governance/gates | GPT-5.6 Sol |
| Perform backend code review | GPT-5.6 Sol |
| Implement a routine PHP repository, attempt 1 | GPT-5.6 Luna |
| Generate routine unit tests, attempt 1 | GPT-5.6 Luna |
| Retry the same implementation after revision | Kimi K2.7 Code |
| Fix failing tests and refactor for Single Responsibility | Kimi K2.7 Code |
| Explicit `--model moonshot/kimi-k2.7-code` diagnostic run | Explicit Kimi override |

## Interpretation of the history

The log provides evidence; it does not claim that one model is universally better based on one execution. Useful comparisons should consider task type, responsibility tier, number of attempts, final verdict and elapsed time together.

A practical future report can aggregate the JSONL history by model and task class to show first-pass acceptance rate, escalation frequency, blocked/rejected outcomes and execution time. The routing policy itself remains intentionally simple until the accumulated evidence justifies changing it.
