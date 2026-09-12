# Adaptive Problem-Solving Learning

## Purpose

Adaptive can now reuse successful **problem-solving strategies**, not only provider/runtime troubleshooting knowledge.

The goal is to reduce dependence on a stronger model or a carefully hand-written owner prompt for recurring reasoning patterns such as:

- implementation repeatedly blocked by unresolved architecture or contract ambiguity;
- structured planner output failing because the requested plan is too broad;
- a smaller analysis/decision Work Unit unlocking later implementation.

This layer guides **how to decompose and recover**, while project requirements, architecture, security policy and human approval boundaries remain authoritative.

## Runtime flow

```text
project objective / current execution state
        |
        v
validated problem-solving knowledge
        +
repeated accepted runtime experience
        |
        v
RuntimeProjectPlanner
        |
        +--> normal bounded Work Graph
        |
        +--> one bounded recovery attempt after structured planning failure

accepted worker result
        |
        | optional explicit ADAPTIVE_LEARNING_CANDIDATE signal
        v
sanitized append-only runtime candidate store
        |
        v
repeated independent observations
        |
        v
provisional advisory guidance
```

## Validated strategy knowledge

Repository-governed strategies live at:

```text
knowledge/problem-solving-strategies.json
```

An operator can override the catalog for testing with:

```text
ADAPTIVE_PROBLEM_SOLVING_KNOWLEDGE=/path/to/problem-solving-strategies.json
```

Validated strategies may be injected automatically into planning when their triggers match the project objective, context, constraints or replanning state.

The initial catalog includes two lessons learned from real execution:

### Resolve blockers before implementation

When implementation is repeatedly blocked by unresolved ambiguity, Adaptive should stop retrying speculative code and first create a bounded read-only DECISION/RESEARCH Work Unit that:

1. reconciles canonical requirements, use cases, architecture, handoff and implementation;
2. classifies each blocker as:
   - existing project decision;
   - technical decision not yet materialized;
   - genuine business-rule ambiguity;
   - environment/tooling limitation;
3. applies existing decisions;
4. proposes the smallest safe technical choice only when business behavior is unchanged;
5. asks the human only for genuine business decisions;
6. produces an explicit decision matrix / implementation contract;
7. resumes implementation in a separate Work Unit.

### Simplify after structured planning failure

If strict planner output is malformed or otherwise fails schema validation, Adaptive does not blindly repeat the same broad prompt.

It performs one bounded recovery attempt:

- exactly one smallest safe Work Unit for initial planning;
- at most one new Work Unit during replanning;
- read-only blocker-resolution work is preferred when uncertainty is the cause;
- schema validation remains mandatory;
- a second failure is surfaced rather than bypassed through ungoverned execution.

## Runtime learning candidates

Accepted workers may emit one explicit final-line signal:

```text
ADAPTIVE_LEARNING_CANDIDATE: {"strategy_id":"...","trigger":"...","action":"...","result":"..."}
```

Workers are instructed to emit it only when a **non-obvious reusable strategy materially turned a blocker into progress**.

The store records only the four bounded fields above plus safe execution identifiers and timestamp. It does not persist raw worker output.

Default location:

```text
~/.local/state/adaptive-ai-orchestrator/problem-solving-candidates.jsonl
```

Override:

```text
ADAPTIVE_PROBLEM_SOLVING_LOG=/custom/path/problem-solving-candidates.jsonl
```

## Conservative aggregation

A single worker self-report does **not** become permanent policy.

A runtime candidate becomes eligible for provisional planner guidance only after the same `strategy_id` is observed in at least two distinct accepted orchestrations and is relevant to the current planning context.

Provisional experience is clearly labeled as advisory.

Repository-validated strategies remain the stronger source of experience knowledge.

This gives Adaptive a useful middle ground:

```text
one observation
    -> candidate only

repeated independent accepted observations
    -> provisional advisory experience

reviewed/promoted repository knowledge
    -> validated strategy
```

## Safety boundaries

Problem-solving learning must not:

- store prompts, user conversations or arbitrary source-code content;
- store chain-of-thought or model reasoning;
- store credentials, tokens or secrets;
- silently rewrite requirements or business rules;
- convert one transient success into permanent policy;
- weaken planner schema validation;
- bypass project governance or the Adaptive bridge;
- authorize side effects beyond the Work Unit contract.

The learning signal parser is fail-closed: malformed, oversized or sensitive-looking candidate payloads are discarded.

## Why this matters for smaller/economy models

The planner no longer has to rediscover every useful decomposition tactic from raw model capability alone.

When relevant, it receives concise, governed process guidance such as:

```text
blocked implementation
    -> isolate ambiguity
    -> decision/research WU
    -> reconcile canonical sources
    -> decision matrix
    -> implementation WU
```

That makes high-quality orchestration behavior more reproducible across weaker or cheaper models without hard-coding project-specific business decisions.
