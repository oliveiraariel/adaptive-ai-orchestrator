# Autonomous Project Execution Policy

## Purpose

Adaptive should be operated from **functional intent**, not from technical control-plane prompts.

A user should be able to say, for example:

> Corrija a tela Compromisso para usar Data do Compromisso e ajuste a recorrência.

Adaptive is responsible for turning that intent into the project mechanics required to deliver it safely.

## Default operating contract

The user supplies:

- functional objective;
- business rules;
- explicit scope constraints;
- product decisions that only a human can make.

Adaptive owns:

1. context recovery;
2. current-state inspection;
3. Work Graph construction and normalization;
4. Work Unit decomposition;
5. dependency discovery;
6. model/skill/worker selection;
7. bounded parallel execution;
8. validation and evidence capture;
9. retry and strategy diversification;
10. recovery and replanning;
11. suspension of only the Work Unit that exhausts recovery;
12. continued execution of independent work;
13. supervisor/liveness recovery;
14. checkpoint and Result Store continuity.

The following are implementation details and should **not** be required in normal user prompts:

- resume-project;
- supervisor leases;
- pending_replan;
- Result Store reconciliation;
- controller liveness;
- recovery epochs;
- worker retry budgets;
- concurrency tuning;
- checkpoint migration mechanics.

They remain observable and operable for diagnostics, but they are not part of the normal product interface.

## Concurrency policy

Project concurrency has provenance.

### AUTO

AUTO is the default.

`max_concurrency` is a normal safety ceiling, not a requirement to keep that many workers active. Adaptive chooses useful concurrency from the READY frontier.

When one active worker crosses the soft-stall observation window, AUTO may temporarily use a bounded overflow slot for an independent READY Work Unit. The original execution is not duplicated or cancelled merely because it is slow.

This gives the scheduler a work-conserving property:

> If executable independent work and safe runtime capacity exist, Adaptive should not remain idle.

### FIXED

FIXED is an explicit operator/business constraint.

When FIXED is selected, `max_concurrency` is a hard ceiling and no stall overflow is permitted.

### Legacy checkpoints

Older checkpoints persisted only an integer `max_concurrency` and did not record whether it came from a deliberate constraint or an implementation default.

Those checkpoints are interpreted as AUTO on resume. A legacy value below the current autonomous floor is upgraded to the current AUTO default so old serial orchestration state cannot permanently throttle a large project.

Any new deliberate serial constraint must be persisted explicitly as FIXED.

## Worker progress observation

A dispatched worker is not assumed to be productive merely because it is RUNNING.

The controller periodically returns from result waiting to:

- observe active worker age;
- recompute READY work;
- refill free capacity;
- detect soft-stalled workers;
- use bounded AUTO overflow when independent work exists.

Soft-stall observation is a throughput mechanism, not a semantic failure verdict. The worker retains its identity and Result Store target and may still complete normally.

Hard runtime timeout and recovery remain responsible for deciding when a worker execution has actually failed.

## Recovery bulkhead

Recovery is scoped to the affected Work Unit.

A Work Unit may be:

- retried;
- retried with a materially different strategy;
- structurally replanned when a real prerequisite exists;
- researched externally when policy allows;
- reconciled from authoritative prior evidence;
- suspended after bounded recovery exhaustion.

Its true downstream dependents remain gated. Independent READY work continues.

`pending_replan=true` means control-plane work is owed. It is not a global project stop flag.

## Human intervention

Adaptive asks for human intervention only when the next decision is genuinely human, for example:

- ambiguous business rule;
- destructive operation requiring approval;
- missing credential/permission;
- mutually valid product alternatives requiring selection;
- governed recovery frontier genuinely exhausted.

Routine scheduler, retry, recovery, liveness and concurrency decisions are internal responsibilities.

## Product criterion

A technical prompt should be treated as a diagnostic tool, not as a normal operating dependency.

Whenever progress requires the user to manually tell Adaptive how to manipulate its own controller, scheduler, recovery loop or checkpoint, that behavior should be considered a missing system capability and moved into code or policy.
