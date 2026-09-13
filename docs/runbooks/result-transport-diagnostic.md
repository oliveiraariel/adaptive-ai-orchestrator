# Runbook: Diagnose agent result transport and handoff

Use this runbook when a worker appears to finish but Adaptive receives malformed,
truncated, summarized, missing, or unrecoverable output.

## Goal

Determine whether the defect is in:

1. result production;
2. wait/lifecycle observation;
3. result persistence;
4. presentation formatting;
5. result retrieval;
6. downstream fan-in.

Do not redispatch the original work until the existing run/result state is known.

## Step 1 — freeze side effects

For transport diagnosis, keep the governed project read-only unless the test is
specifically validating an authorized result-store write.

Do not use a production project mutation as a transport probe.

## Step 2 — preserve execution identity first

Immediately record:

- orchestration ID;
- Work Unit ID;
- execution ID;
- runtime run ID;
- session ID/key when available;
- timestamps.

A wait timeout without a preserved run ID is much harder to reconcile.

## Step 3 — classify the channel

For each representation, answer:

| Channel | Intended role | Authoritative? |
|---|---|---|
| progress/history | human progress/presentation | no |
| terminal reply | short final human summary | no |
| Result Store manifest/result | machine result | yes, after validation |

Do not promote a channel to authoritative merely because its name contains
`result`, `final`, or `terminal`.

## Step 4 — prove integrity at boundaries

Use a deterministic payload containing:

- unique BEGIN marker;
- unique END marker;
- known byte/character length;
- SHA-256.

At each boundary record:

- representation source;
- length;
- BEGIN present?;
- END present?;
- truncation marker present?;
- SHA-256;
- stable identity/reference;
- recoverable after completion?

If the producer has a full payload but the consumer does not, the defect is
transport/persistence, not model quality.

## Step 5 — staged payload ladder

Run:

### SMALL

Use a compact result well below known presentation limits.

### MEDIUM

Use a result large enough to expose summarization/transport differences but still
cheap to inspect.

### LARGE

Use >12k characters so a historical 8k presentation boundary cannot accidentally
pass.

**Stop rule:** if MEDIUM fails integrity, do not run LARGE. Diagnose MEDIUM first.

## Step 6 — wait timeout handling

A wait timeout is an observation result, not automatically an execution failure.

On wait timeout:

1. keep the same run ID;
2. query/reconcile the same run;
3. respect the global reconciliation budget;
4. do not create a second execution yet;
5. cancel only through the explicit cancellation operation when intended.

Classify separately:

- wait timed out;
- run still active;
- run terminal;
- result persisted;
- result recoverable.

## Step 7 — Result Store checks

For an authoritative Adaptive result, verify:

- path is below `<project>/.adaptive/runs/`;
- orchestration/Work Unit/execution identity matches;
- `manifest.json` exists;
- `complete=true`;
- referenced `result_file` exists;
- byte length matches;
- SHA-256 matches;
- no `.tmp` file is being treated as complete.

The manifest is the completion sentinel and is published last.

## Step 8 — fan-in checks

For a downstream dependent Work Unit:

- verify `TaskPackage.artifacts` contains the dependency manifest reference;
- verify downstream context contains the small reference/instruction;
- verify the large dependency body is absent from downstream conversation context;
- verify the worker can read the manifest and referenced result file when needed.

If the dependency body is copied inline despite an authoritative result reference,
classify it as a fan-in regression.

## Step 9 — rejected shortcuts

Do not:

- raise UI/progress size limits as the primary fix;
- reconstruct JSON from a truncated representation;
- relax schema validation;
- treat terminal summary as machine result;
- retry the same side-effecting work before run reconciliation;
- permanently edit hashed/generated third-party dist bundles;
- store one project's result data in Adaptive's source repository.

## Step 10 — evidence required for PASS

Transport is PASS only when the real runtime path proves:

- authoritative result published;
- stable reference preserved;
- hash/length/completeness valid;
- >12k result recovered intact;
- progress may truncate without affecting machine result;
- terminal summary may be short without affecting machine result;
- dependency fan-in passes a reference rather than the payload;
- project source files remain unchanged during read-only validation.

## Failure classifications

Use the most specific available classification:

- `PLANNER_OUTPUT_TRUNCATED`;
- `MACHINE_RESULT_UNAVAILABLE`;
- `MACHINE_RESULT_INCOMPLETE`;
- `MACHINE_RESULT_INTEGRITY_FAILURE`;
- `TERMINAL_REPLY_IS_SUMMARY`;
- `PROGRESS_CHANNEL_NOT_AUTHORITATIVE`;
- `WAIT_TIMEOUT_RECONCILIATION_REQUIRED`;
- `RESULT_STORE_PUBLICATION_FAILURE`;
- `RESULT_STORE_IDENTITY_MISMATCH`;
- `RESULT_STORE_INTEGRITY_MISMATCH`;
- `FAN_IN_REFERENCE_REGRESSION`;
- `UNKNOWN_RESULT_TRANSPORT_FAILURE`.

Do not collapse a known transport defect into generic `invalid JSON`.
