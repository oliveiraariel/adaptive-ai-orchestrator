# Work Graph Migration / Normalization

## Purpose

Adaptive normally treats a persisted Work Graph as durable execution history. Ordinary
replanning is deliberately additive: it may add remediation Work Units and dependency
edges, but it must not rename or reinterpret existing nodes.

That rule is correct for normal recovery, but it leaves one operational gap. A Planner
can persist an aggregate node even when the operator supplied explicit Work Unit
identities. After execution has started, later replanning cannot safely split the
aggregate without rewriting history.

Work Graph Migration closes that gap. It is a governed, forward-only operation for a
non-terminal persisted orchestration whose graph must be normalized without losing its
identity, checkpoints, Result Store evidence, recovery history, or WIP.

Typical trigger:

1. the original request contains explicit Work Unit identities;
2. the persisted graph collapsed several of them into aggregate nodes;
3. historical results are still useful and must remain immutable;
4. ordinary additive replan cannot recover the required scheduling granularity.

Migration is not a general graph editor and is not a shortcut around normal replanning.

## Design principles

The design follows the same safety shape used by mature durable-workflow migration
systems: the operator supplies an explicit migration plan, the system validates the
mapping against the current durable state before mutation, and the running instance is
changed only while it is quiescent. Adaptive adds a stricter forward-only constraint:
historical Work Units are never deleted or rewritten.

The core invariants are:

- **same orchestration identity** — migration never creates a replacement orchestration;
- **paused + quiescent apply boundary** — dry-run and apply require
  desired_state=PAUSED and zero active executions;
- **optimistic concurrency** — apply requires the SHA-256 fingerprint returned by the
  preceding dry-run, so any intervening graph/state change fails closed;
- **additive topology** — existing Work Unit definitions, states, dependencies,
  records, outputs and Result Store references remain intact;
- **new edges target new nodes only** — migration cannot retroactively impose a new
  prerequisite on work that already ran;
- **explicit evidence lineage** — a new normalized Work Unit may start COMPLETED only
  when the migration declares historical source Work Units and evidence references;
- **no forged execution** — evidence-backed migrated completion does not manufacture a
  worker execution record; its provenance is the immutable migration artifact;
- **scheduling supersession is metadata** — an aggregate historical node can be marked
  superseded_for_scheduling while retaining its original state and result;
- **no stranded dependents** — a historical node may not be superseded when an
  unsatisfied required edge from it still blocks a non-superseded historical node;
- **bounded graph** — max_work_units is checked before mutation;
- **acyclic graph** — the merged plan is validated by the same domain plan parser used
  by normal execution;
- **idempotent apply** — a migration_id can be applied again only with equivalent
  semantic migration content; it never duplicates Work Units or dependencies;
- **forward correction** — a bad migration is corrected by another additive migration.
  Historical migration records are never edited or removed.

## Activation boundary

Migration is enabled only when all of the following hold:

- the orchestration exists;
- checkpoint phase is EXECUTION;
- the checkpoint is non-terminal;
- the project has been gracefully paused;
- active_executions is empty;
- the migration fits inside max_work_units;
- every historical lineage source exists;
- every requested superseded node exists and is inactive;
- the merged Work Graph passes normal graph validation.

This boundary matters. A migration must never race a worker that was dispatched using
the old graph.

## Planner prevention

Migration repairs historical graphs. New projects should avoid the defect in the first
place.

Adaptive now treats explicit governance IDs as durable identities:

- callers can pass repeated --required-work-unit-id <id> values;
- ProjectOrchestrationRequest and the durable checkpoint persist
  required_work_unit_ids;
- as a compatibility fallback, literal WU-* IDs found in the authoritative project
  objective/scope are detected;
- arbitrary retrieved context is not scanned for required IDs, because historical
  notes may mention Work Units that are not part of the current request;
- the Planner response is rejected if it omits one of those IDs;
- an aggregate/fan-in node may still be created, but only in addition to the
  required individual nodes;
- static --plan-file execution is guarded by the same executor invariant.

If the explicit catalog itself exceeds max_work_units, planning fails before worker
dispatch rather than silently collapsing the catalog.

## Migration document

Protocol: work-graph-migration/1.

Canonical schema:

    specifications/protocols/work-graph-migration-v1.schema.json

Each new entry has three parts:

- spec: a normal PlannedWorkUnit specification;
- initial_state: only PLANNED or COMPLETED;
- lineage: historical Work Unit IDs, evidence references and a concise evidence
  summary.

COMPLETED is an evidence-backed migration state, not a synthetic worker result. Both
historical_source_ids and evidence_refs must be non-empty.

Dependencies use the existing Adaptive direction:

    source_id -> target_id

meaning source must complete before target becomes eligible.

A migration edge may point to a newly-created target only. This is what prevents
retroactive mutation of historical execution semantics.

## Two-phase operator flow

First pause the project and wait until active work settles:

    adaptive-orchestrator pause-project \
      --orchestration-id <id> \
      --project-root <project>

Confirm:

    adaptive-orchestrator project-status \
      --orchestration-id <id> \
      --project-root <project>

The status must be non-terminal, desired_state=PAUSED, with zero active executions.

Run the exact migration plan as a dry-run:

    adaptive-orchestrator migrate-work-graph \
      --orchestration-id <id> \
      --project-root <project> \
      --plan-file migration.json \
      --dry-run

The command returns checkpoint_fingerprint_before. Put that value in
expected_checkpoint_fingerprint in the same migration document.

Run dry-run again if the document changed materially. Then apply:

    adaptive-orchestrator migrate-work-graph \
      --orchestration-id <id> \
      --project-root <project> \
      --plan-file migration.json \
      --apply

Finally inspect status and resume the same orchestration:

    adaptive-orchestrator project-status \
      --orchestration-id <id> \
      --project-root <project>

    adaptive-orchestrator resume-project \
      --orchestration-id <id> \
      --project-root <project>

The supervisor may then continue to guard the same durable identity normally.

## Persistence and audit

Apply atomically replaces the authoritative checkpoint through the existing checkpoint
store. The checkpoint records:

- work_graph_migrations: append-only migration records;
- superseded_work_unit_ids: historical nodes excluded from future scheduling.

Each migration record contains:

- migration ID and reason;
- before/after checkpoint fingerprints;
- migration plan digest;
- added and superseded Work Unit IDs;
- before/after pending-replan state;
- the normalized migration document;
- timestamp and audit-artifact path.

An immutable companion artifact is created under:

    .adaptive/work-graph-migrations/<orchestration-hash>/<migration-hash>.json

If the checkpoint commit succeeds but artifact creation is interrupted, reapplying the
same migration ID/content reconstructs the missing artifact without mutating the graph
again.

## Recovery interaction

A RECOVERY_REQUIRED aggregate can remain historically RECOVERY_REQUIRED after
normalization. If it is listed in superseded_work_unit_ids, the scheduler, recovery
selection and operational terminal calculation ignore it while retaining it in durable
history.

When every currently recovery-required historical node has been superseded, stale
pending_replan pressure is cleared by migration. The normalized graph then resumes
from its own eligible Work Units.

The Planner state summary still renders superseded historical nodes and labels them
superseded_for_scheduling=true; this preserves context without allowing the Planner to
mistake them for work that should be retried.

## Failure handling

Migration fails closed when:

- the project is running instead of paused;
- any worker is active;
- the checkpoint changed after dry-run;
- a new ID collides with history;
- a lineage source is unknown;
- a completed migrated node lacks evidence;
- a new dependency targets a historical node;
- supersession would strand an operational historical dependent;
- the graph exceeds its budget;
- the merged graph is invalid or cyclic;
- a migration ID was previously used for different content.

Do not manually edit .adaptive/orchestrations/*.json to work around these checks.

## Operational diagnostic that should trigger migration

A practical signal is:

- user/request catalog contains explicit Work Unit IDs;
- persisted graph contains fewer/different aggregate IDs;
- evidence can be mapped from aggregate history to the missing requested IDs;
- ordinary replan repeatedly preserves the aggregate graph because it correctly refuses
  to rewrite existing node identity.

At that point, repeated replan is no longer productive. Pause, reconcile evidence,
build a versioned migration plan, dry-run it, apply it, and resume.

## Non-goals

Work Graph Migration does not:

- edit completed worker output;
- rewrite Result Store manifests;
- mutate arbitrary historical dependency semantics;
- reopen completed Work Units;
- infer acceptance from names alone;
- create evidence that does not exist;
- replace normal Recovery Loop behavior;
- bypass human approval, side-effect policy, or project governance;
- provide destructive rollback.

It is specifically a durable normalization mechanism for a real persisted graph whose
historical topology no longer represents the governance granularity that must be
scheduled going forward.
