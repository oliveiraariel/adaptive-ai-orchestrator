# Execution Integrity Field Learning — 2026-09-13

## Context

This note captures operational learning from sustained SGFP work through OpenClaw + Adaptive AI Orchestrator on 2026-09-12 and 2026-09-13. The incidents were useful because they exposed failures that ordinary happy-path unit tests do not reveal: stale runtime state, premature worker completion, ambiguous blockers, oversized delegated checklists, incomplete acceptance evidence, and handoff drift.

The purpose is not to preserve chat history. It is to convert observed failure modes into deterministic orchestrator rules, skill guidance, and regression obligations.

## Observed failure modes

### 1. Persisted RUNNING was mistaken for real execution

A historical or persisted orchestration/session state remained visible as RUNNING while no worker/subagent was actually active and no final report was being produced.

**Lesson:** persisted status is not sufficient runtime truth. Active worker/run identity and terminal runtime evidence must outrank a stale dashboard label.

**Required behavior:**
- reconcile known execution/run/session identity before redispatch;
- never create a replacement worker merely because a caller timed out;
- surface stale/orphan state explicitly instead of reporting healthy RUNNING;
- preserve recovery identifiers.

### 2. Repeated orphan/stale attempts needed a circuit breaker

The same task was attempted repeatedly without an active worker and without a final result.

**Lesson:** automatic repetition can amplify uncertainty and duplicate work.

**Required behavior:**
- bounded attempts;
- after the configured attempt budget, stop automatic redispatch;
- classify the stop reason;
- require a human decision for direct fallback/recovery when governance requires it.

### 3. Runtime completion was confused with semantic task completion

Workers returned after completing only part of a checklist. Some outputs explicitly said that work remained, yet the surrounding flow could still treat runtime completion as success.

**Lesson:** "the worker stopped" and "the objective is complete" are different facts.

**Required behavior:**
- terminal success requires explicit completion evidence;
- partial output must not satisfy downstream dependencies;
- ACCEPTED_WITH_CONDITIONS is not equivalent to completed work;
- a structured worker completion footer should distinguish COMPLETE, PARTIAL and BLOCKED.

### 4. Missing implementation dependencies were misclassified as blockers

Workers stopped because a service lacked an AccountRepository, TransactionManager, wiring, or similar dependency even when the delegated scope explicitly authorized the minimal production change needed to add it.

**Lesson:** work that is authorized and technically executable is not a blocker.

**Genuine blockers include:** human decision, missing authority, unavailable environment/runtime, or an external dependency outside the delegated scope.

**Not blockers:** ordinary implementation, wiring, test creation, or architecture adjustments already authorized by the Work Unit.

### 5. Large checklists encouraged premature stopping

Broad prompts containing many independent obligations repeatedly produced a small subset of the requested work followed by a partial report.

**Lesson:** decomposition quality affects completion reliability.

**Required behavior:**
- split large independent checklists into bounded Work Units/lots;
- keep one Work Unit small enough to finish and verify in one execution;
- use explicit fan-in when later verification depends on several units;
- do not micro-fragment trivial work, but do not delegate a long independent backlog as one unit.

### 6. Acceptance evidence needed objective counters and named tests

Claims such as "coverage added" were weak when the test count did not change or when no exact test method could be named.

**Lesson:** evidence should be checkable against the requested delta.

**Useful evidence patterns:**
- before/after test and assertion counts;
- exact test method names;
- exact files changed;
- explicit mapping criterion -> test/evidence;
- explanation when the count legitimately does not change because existing tests already cover the criterion.

### 7. Environment failures initially looked like code failures

PHPUnit was blocked first by missing mbstring, then by local Composer availability/configuration. Once the environment was repaired, the suite exposed a much smaller set of real test/code issues.

**Lesson:** preflight environment/tool availability before interpreting execution failure as implementation failure.

**Required behavior:**
- classify environment/tool/runtime/test/code separately;
- use project-local tools when available;
- avoid speculative production changes to satisfy an environment failure.

### 8. Test defects and production defects must be separated

Examples included PHPUnit attempting to mock final classes, stale fixtures, and one real StagedBackupDecoder defect.

**Lesson:** a red suite is evidence of a problem, not automatically evidence of a production-code defect.

**Required behavior:** diagnose each failure and label it test defect, production defect, environment defect, or unresolved before changing code.

### 9. Handoffs can contain contradictory historical truth

The SGFP handoff accumulated old blocks stating that Stage 11 had not started, PHPUnit was unavailable, and an older HEAD was current. A new checkpoint was correct but could still be undermined by earlier text labeled authoritative.

**Lesson:** continuity documents need one unmistakable current-authority pointer while preserving history.

**Required behavior:**
- current authoritative state at the top;
- branch + exact HEAD;
- WIP preservation rules;
- verified test baseline;
- exact next action;
- historical blocks explicitly marked non-current.

### 10. Human intervention improved outcome when it converted ambiguity into executable constraints

Useful interventions were not generic "try again" prompts. They:
- proved local/remote Git state before merging;
- repaired the PHPUnit environment before blaming code;
- converted giant checklists into small closed lots;
- stated that missing authorized dependencies were work, not blockers;
- required concrete evidence such as test-count growth and named test methods;
- created a controlled fallback policy after Adaptive bridge failures;
- forced a precise HANDOFF checkpoint before session end.

**Lesson:** the orchestrator should internalize these forms of intervention so the user does not have to repeatedly restate them.

## Implemented rules

This field learning is implemented across:
- project planning/decomposition rules;
- worker completion integrity parsing;
- finalization semantics;
- retry/circuit-breaker reasons;
- bridge/result-reporting guidance;
- testing, debugging, lifecycle, and handoff skills.

The system should still fail closed on genuine authority or human-decision boundaries. The goal is not "never stop"; it is "stop only for a real classified reason, and never call partial work complete."
