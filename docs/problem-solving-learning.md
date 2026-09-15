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

The catalog includes validated lessons learned from real execution, including:

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


### Trace machine-result transport before retrying work

When an execution appears to complete but the consumer receives malformed,
truncated, summarized, or missing output, Adaptive must first determine whether
the defect is in the result path rather than in the model or task.

The reusable diagnostic pattern is:

1. preserve run/execution identity;
2. compare producer and consumer representations;
3. use BEGIN/END markers, length, and SHA-256;
4. distinguish progress/history from terminal summary and authoritative result;
5. repair transport/persistence if the producer created a complete result;
6. only retry/replan after the result path is understood.

This prevents a transport defect from being misclassified as generic planner
invalid JSON.

### Separate control plane from result plane

OpenClaw is used for dispatch, liveness, progress, bounded waiting, cancellation,
and short terminal summaries. Large authoritative results move through Adaptive's
durable project-local Result Store.

Dependent workers receive result references rather than copied large payloads.
This keeps agent-to-agent coordination independent from chat/progress size limits
and reduces avoidable context growth.

### Reconcile the same run before redispatch

A wait timeout does not by itself prove execution failure. Adaptive preserves run
identity, reconciles the same execution within a bounded budget, and only creates
another execution after the previous state is known.

### Validate transports with SMALL / MEDIUM / LARGE

Transport changes are validated progressively:

- SMALL proves the basic contract;
- MEDIUM exposes boundary/summarization problems;
- LARGE (>12k) proves independence from historical presentation limits.

If MEDIUM fails, escalation stops until that boundary is diagnosed.


### Prove runtime provenance before dependency repair

When a runtime reports an apparently missing Python dependency, Adaptive should not immediately reinstall the package or blame the model.

The reusable diagnostic pattern is:

1. preserve the original traceback;
2. identify the exact failing process and parent/launcher;
3. prove repository, branch, HEAD, configured interpreter and effective interpreter;
4. compare `sys.prefix`, `sys.base_prefix`, `sys.path`, `PYTHONPATH`, `PYTHONHOME` and virtualenv state at the failing boundary;
5. reproduce the import through the exact launcher/executable/environment;
6. inspect interpreter symlink/path canonicalization before changing dependencies;
7. avoid global installs that merely mask runtime provenance defects;
8. add a fail-closed prerequisite preflight using the same executable/environment as the real launch.

This strategy was promoted after the 2026-09-15 Planner/Bridge incident, where `jsonschema` was installed in the authorized venv but a real Bridge child reported it missing before Planner execution. The historical transient environment could not be reconstructed exactly later, so the permanent lesson explicitly separates confirmed evidence from suspected mechanism. The Bridge was hardened to preserve the logical venv interpreter path and to validate `adaptive_orchestrator`, `jsonschema`, `websockets` and `cryptography` before starting Adaptive.

### Use explicit plan-only mode for Planner validation

When the goal is to validate Planner behavior without executing the planned project, Adaptive should not overload executor limits to suppress dispatch.

In particular:

- `max_waves` remains an executor bound with its own invariant;
- plan-only behavior is explicit;
- the real `RuntimeProjectPlanner` still runs through the governed runtime;
- strict JSON, `planner-output/1` and semantic validation remain mandatory;
- a `ProjectExecutionPlan` is returned;
- generated project Work Units are not dispatched;
- successful planning is not reported as successful project execution.

The 2026-09-15 real smoke first tried `max_waves=0`, which was correctly rejected by the executor contract. The new explicit `--plan-only` mode then allowed the real Planner to produce a valid three-Work-Unit plan while dispatching zero generated Work Units.

The full forensic record for both strategies is:

```text
docs/incidents/2026-09-15-planner-bridge-runtime-and-plan-only.md
```

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
