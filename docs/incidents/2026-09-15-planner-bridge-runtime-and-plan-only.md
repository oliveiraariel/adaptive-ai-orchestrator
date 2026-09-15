# Incident: Planner contract, Bridge runtime provenance, and safe plan-only validation

**Date:** 2026-09-15  
**Status:** corrected and validated through the real OpenClaw -> Bridge -> Adaptive -> Planner path  
**Scope:** Planner structured output, OpenClaw/Adaptive Bridge provenance, Python runtime prerequisites, safe Planner-only validation

## Executive summary

A real SGFP multiagent run initially failed before fan-out with a Planner JSON error. The visible symptom suggested a model-formatting problem, but the investigation showed that several independent boundaries had to be proven before the Planner could be blamed:

1. the Planner output contract itself;
2. the Adaptive checkout and Python provenance used by OpenClaw;
3. the Bridge child-process runtime and its dependencies;
4. a safe way to execute the real Planner without dispatching the generated Work Units.

The final architecture now fails closed at each of those boundaries:

```text
OpenClaw
  -> Adaptive Orchestrator Bridge
  -> runtime prerequisite preflight
  -> Adaptive
  -> RuntimeProjectPlanner
  -> planner.request
  -> model
  -> planner.plan
  -> strict JSON
  -> planner-output/1 JSON Schema
  -> canonicalization
  -> semantic validation
  -> ProjectExecutionPlan
  -> optional --plan-only stop before Work Unit dispatch
```

The final real smoke test passed: the Planner executed through the runtime, produced a schema-valid and semantically valid ProjectExecutionPlan with three Work Units, and plan-only mode dispatched zero generated Work Units.

## Initial symptom

The operational goal was to resume SGFP Stage 11 through the governed path:

```text
OpenClaw -> Adaptive Bridge -> Adaptive -> Planner -> Work Units
```

The first blocker appeared before fan-out as malformed/invalid Planner JSON.

At that point, plausible causes included:

- model output;
- provider-native structured-output projection;
- OpenClaw provider adapter;
- OpenClaw response parsing;
- transport truncation;
- AMEP/result transport;
- Adaptive schema/parser behavior;
- wrong checkout/runtime provenance.

The key lesson was that **"Planner returned invalid JSON" is a symptom, not a root-cause classification**.

## Investigation and corrections

### 1. Make Planner output a governed machine contract

Prompt wording such as "return JSON" was not treated as sufficient.

Adaptive introduced a mandatory Planner output contract:

- message type: `planner.plan`;
- schema: `planner-output/1`;
- content type: `application/json`;
- JSON Schema Draft 2020-12;
- fail-closed strict JSON parsing;
- deterministic canonicalization;
- semantic validation after schema validation;
- raw result preservation for diagnostics;
- one bounded governed recovery attempt for recognized contract failures.

The trusted boundary became:

```text
raw model output
  -> strict JSON
  -> planner-output/1
  -> canonical JSON
  -> semantic graph validation
  -> ProjectExecutionPlan
```

Markdown fences, prose wrapping, partial-object extraction, unknown fields, invalid types, budget violations, and graph-semantic failures are not accepted as a plan.

This was implemented in Adaptive PR #43.

### 2. Prove repository and process provenance before blaming the Planner

The first real smoke did not reach the Planner because the local Adaptive checkout was stale. After synchronizing the repository, a second provenance gate showed that `ADAPTIVE_ORCHESTRATOR_ROOT` was visible in the terminal but not inside the running OpenClaw Gateway.

Process inspection showed that the Gateway was managed by:

```text
systemd --user
  -> openclaw-gateway.service
```

Therefore, shell-local `export` commands did not change the environment of the already-running service.

A user-level systemd drop-in made the runtime selection persistent:

```text
~/.config/systemd/user/openclaw-gateway.service.d/adaptive.conf
```

with explicit:

- `ADAPTIVE_ORCHESTRATOR_ROOT`;
- `ADAPTIVE_ORCHESTRATOR_PYTHON`.

After restart, the process environment, Bridge root, repository branch, HEAD, and Python path all matched the intended Adaptive checkout.

### 3. Investigate the apparent missing `jsonschema` dependency

The next real smoke failed during Adaptive import with:

```text
ModuleNotFoundError: No module named 'jsonschema'
```

The immediate-looking explanation was "jsonschema is not installed", but direct inspection proved otherwise:

- `jsonschema 4.26.0` was installed in the Adaptive virtualenv;
- direct import through the configured `.venv/bin/python` passed;
- the configured and effective Python paths matched during later diagnostics;
- normal and sanitized Bridge-child environment probes both found the same site-packages and imported `jsonschema`.

The preserved traceback proved that the historical failure occurred in the **first Adaptive subprocess launched by the Bridge**, during import of `application.structured_output_contract`, before any Planner/provider execution.

The exact transient environment state of that failed process could not be reconstructed later. The incident therefore does **not** claim that dependency installation alone was the root cause.

However, reconciliation found stale Bridge code that canonicalized the configured interpreter with `Path.resolve()`. For virtualenv Python symlinks, resolving the physical target can erase the logical virtualenv interpreter path and is unsafe for deterministic runtime provenance. That stale behavior was excluded when the Bridge work was rebased onto current main, preserving the authorized `.venv/bin/python` path.

The durable correction was not a global package install. The Bridge gained a deterministic, fail-closed runtime prerequisite preflight that uses the **same executable and environment intended for the real Adaptive launch** and validates:

- `adaptive_orchestrator`;
- `jsonschema`;
- `websockets`;
- `cryptography`.

If the preflight fails, Adaptive is not started and the Bridge returns a sanitized `BRIDGE_RUNTIME_PREFLIGHT_FAILED` diagnostic instead of allowing an ambiguous bootstrap failure.

This was implemented in ariel-agent-skills PR #15.

### 4. Do not overload executor limits to simulate a dry run

To validate only the Planner, the smoke initially attempted:

```text
--max-waves 0
```

The Adaptive request contract correctly rejected it because `max_waves` is an executor bound with valid range 1..256.

Changing that invariant to make zero mean "planning only" would have mixed two unrelated semantics:

```text
max_waves = executor dispatch-generation limit
plan-only = do not enter the Work Unit executor
```

The safe correction was an explicit `--plan-only` mode.

In plan-only mode Adaptive still:

1. initializes the real runtime;
2. invokes `RuntimeProjectPlanner`;
3. performs the real Planner request;
4. enforces strict JSON/schema/semantic validation;
5. creates a `ProjectExecutionPlan`;
6. returns machine-readable plan metadata.

It then stops **before** `RunContinuousProjectOrchestration.execute()`, so generated project Work Units are not dispatched.

This was implemented in Adaptive PR #44.

## Final real smoke proof

The final read-only smoke used the merged behavior from the Planner contract, Bridge preflight, and plan-only mode.

Observed result:

- Adaptive provenance: PASS;
- Bridge provenance: PASS;
- Bridge runtime preflight: PASS;
- runtime Python: authorized Adaptive virtualenv;
- `jsonschema`: loaded from Adaptive virtualenv;
- Planner runtime executed: YES;
- provider/model reached: YES;
- contract: `planner.request -> planner.plan`, `planner-output/1`, `application/json`;
- strict JSON syntax: PASS;
- JSON Schema: PASS;
- semantic validation: PASS;
- ProjectExecutionPlan: created;
- Work Units generated: 3;
- dependencies: none;
- generated Work Units dispatched: 0;
- SGFP tracked code modified: none.

This proved the full diagnostic chain without using SGFP implementation work as the test payload.

## Rejected or unsafe shortcuts

### Reinstall `jsonschema` globally

Rejected. The package was already installed in the authorized venv. A global installation would mask a runtime-provenance or launcher defect and weaken environment isolation.

### Blame the model immediately

Rejected. The failure occurred before the Planner/model in several smoke attempts, and prior incidents had already shown that malformed downstream JSON can originate in transport or presentation layers.

### Apply old stashed Planner/Bridge code wholesale

Rejected. Historical WIP was preserved but not blindly applied over the synchronized main branches.

### Use `max_waves=0` as a plan-only switch

Rejected. It violated a valid executor invariant and conflated execution-budget semantics with execution suppression.

### Run SGFP Work Units merely to prove the Planner

Rejected. The validation target was the Planner contract, not SGFP behavior. The new explicit plan-only mode made the proof read-only and bounded.

## Permanent lessons

1. **A visible symptom is not a root-cause classification.** "Invalid JSON", "missing module", and "timeout" each require boundary-specific evidence.
2. **Provenance is part of correctness.** Repository, branch, HEAD, executable, service environment, and child-process runtime must be proven before interpreting failures.
3. **A package being installed does not prove the failing process can import it.** Diagnose the exact child process and its import path.
4. **Do not repair an apparent dependency failure by installing globally when an isolated environment is authoritative.**
5. **Preserve the logical virtualenv interpreter path.** Avoid path canonicalization that can collapse a venv Python symlink into a system interpreter path.
6. **Preflight runtime prerequisites with the same executable and environment as the real launch.**
7. **Fail closed before entering Adaptive when Bridge prerequisites are not satisfied.**
8. **Keep Planner output schema enforcement inside Adaptive, even when provider/OpenClaw structured-output features exist.**
9. **Do not overload an existing execution-limit parameter to invent a diagnostic mode.** Introduce an explicit semantic mode.
10. **Planner execution and generated Work Unit execution are different events.** A safe plan-only proof must execute the former and prevent the latter.
11. **Use the real production path for the final proof.** Unit tests and synthetic probes are necessary but not sufficient.
12. **Preserve evidence and WIP before repair.** Do not use destructive Git cleanup during incident diagnosis.

## Reusable self-healing sequence

For a similar future incident:

```text
DETECT
-> PRESERVE EVIDENCE
-> PROVE PROVENANCE
-> CLASSIFY THE FAILING BOUNDARY
-> REPRODUCE THROUGH THE EXACT RUNTIME
-> APPLY THE SMALLEST SAFE REPAIR
-> ADD A FAIL-CLOSED PRECHECK OR CONTRACT
-> VERIFY WITH TARGETED TESTS
-> VERIFY THROUGH THE REAL RUNTIME PATH
-> PROMOTE THE GENERAL LESSON TO GOVERNED KNOWLEDGE
-> RESUME THE ORIGINAL GOAL
```

## Related changes

- Adaptive PR #43: schema-bound Planner output contract;
- ariel-agent-skills PR #15: deterministic Bridge runtime prerequisite preflight;
- Adaptive PR #44: safe `--plan-only` orchestration mode.
