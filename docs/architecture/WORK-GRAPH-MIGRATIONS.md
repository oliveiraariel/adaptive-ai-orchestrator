# Work Graph Migration / Normalization

## Purpose

Adaptive normally treats the persisted Work Graph as authoritative and replanning as additive. That is safe for ordinary recovery, but it leaves one important gap: an early Planner can aggregate a user-supplied catalog of explicit Work Unit ids into broader historical nodes. Once those aggregate nodes have executed, ordinary replanning cannot safely rewrite history to recover the missing granularity.

Work Graph Migration is the governed repair path for that situation. It is not a general graph editor. It is a narrow, fail-closed migration mechanism for non-terminal orchestrations whose durable graph no longer represents the granularity required by the approved project contract.

## Design influences

The workflow intentionally follows well-established migration and infrastructure change patterns:

- versioned migrations with immutable applied history and checksums, as used by database migration systems such as Flyway;
- explicit dry-run / plan then apply, as used by Terraform;
- state locking plus an optimistic state precondition so an apply cannot silently target a checkpoint that changed after review;
- append-only evidence lineage rather than rewriting historical execution records.

These ideas are adapted to Adaptive's checkpointed Work Graph and Recovery Loop.

## Core invariants

1. Historical Work Units are immutable. A migration cannot remove, rename, replace, or rewrite an existing Work Unit.
2. Historical edges are immutable. Existing dependencies remain represented in the persisted plan. A migration may add an edge only when at least one endpoint is a newly materialized Work Unit.
3. Apply only while paused and quiescent. desired_state must be PAUSED, the checkpoint must be non-terminal, active_executions must be empty, and controller liveness must explicitly be non-ACTIVE so no previous controller can later overwrite the migrated graph. Fresh ACTIVE, stale ACTIVE, and missing liveness all fail closed.
4. Dry-run before apply. The dry-run reports the exact checkpoint digest, before/after graph digests, new Work Units, accepted-by-lineage units, recovery targets, and blockers.
5. Optimistic checkpoint precondition. Apply requires the checkpoint_digest emitted by the preceding dry-run. If the durable checkpoint changed, apply fails and a new dry-run is required.
6. Versioned, idempotent migration identity. migration_id + spec_digest identifies one migration. Reapplying the same migration is a no-op. Reusing the same id with different content fails closed.
7. Immutable audit receipt. Applied migrations write an immutable receipt under .adaptive/graph-migrations/<orchestration-hash>/.
8. Evidence-backed completion only. A newly materialized Work Unit may begin as COMPLETED only when it declares explicit evidence_lineage to at least one historically COMPLETED Work Unit. Otherwise it begins PLANNED.
9. Recovery transition is explicit. A historical RECOVERY_REQUIRED Work Unit can move to REVISION_REQUIRED only when the migration explicitly names it in resume_recovery_targets and adds at least one new required prerequisite edge new-unit -> recovery-unit.
10. Pending replan is consumed conservatively. consume_pending_replan=true is allowed only if every currently RECOVERY_REQUIRED Work Unit is covered by the migration's recovery targets.
11. Normal graph validation still applies. The combined graph must remain acyclic and stay within max_work_units.
12. Runtime refresh preserves migration metadata. Ordinary checkpoint saves preserve graph_migrations and work_unit_evidence_lineage.

## Migration contract

Schema: specifications/protocols/work-graph-migration-v1.schema.json

Minimal shape:

~~~json
{
  "schema_version": "work-graph-migration/1",
  "migration_id": "normalize-example-v1",
  "reason": "restore explicit Work Unit granularity",
  "work_units": [
    {
      "id": "WU-EXAMPLE-01",
      "objective": "Validate the explicit requirement",
      "role": "worker",
      "scope": "",
      "kind": "EXECUTION",
      "required_capabilities": [],
      "requested_skills": [],
      "tools": [],
      "inputs": [],
      "expected_output": ["agent response"],
      "acceptance_criteria": ["runtime-completed"],
      "requested_side_effects": [],
      "write_paths": [],
      "priority": 0,
      "criticality": 0,
      "parallel_safe": true,
      "initial_state": "PLANNED",
      "evidence_lineage": []
    }
  ],
  "dependencies": [],
  "resume_recovery_targets": [],
  "consume_pending_replan": false
}
~~~

## Operator workflow

### 1. Pause the orchestration

~~~bash
adaptive-orchestrator pause-project --orchestration-id <id> --project-root <project>
~~~

Wait until no active execution remains and the controller heartbeat has closed to a non-ACTIVE state (normally TERMINAL with PAUSED status). The migration command reports controller quiescence and refuses apply when liveness is ACTIVE (fresh or stale) or missing.

### 2. Dry-run the migration

~~~bash
adaptive-orchestrator migrate-work-graph --orchestration-id <id> --project-root <project> --plan migration.json
~~~

The output includes checkpoint_digest, before_graph_digest, after_graph_digest, new_work_unit_ids, initially_completed_work_unit_ids, resumed_recovery_targets, apply_ready, and blockers.

### 3. Apply exactly the reviewed state

~~~bash
adaptive-orchestrator migrate-work-graph --orchestration-id <id> --project-root <project> --plan migration.json --apply --expected-checkpoint-digest <digest-from-dry-run>
~~~

Apply acquires a per-orchestration migration lease, reloads the checkpoint, checks the precondition digest, applies the additive graph delta, saves the checkpoint atomically, and writes the immutable migration receipt.

### 4. Inspect

~~~bash
adaptive-orchestrator project-status --orchestration-id <id> --project-root <project>
~~~

project-status exposes migration count/ids and evidence-lineage coverage.

### 5. Resume

~~~bash
adaptive-orchestrator resume-project --orchestration-id <id>
~~~

The normal scheduler then executes the newly materialized eligible frontier.

## Planner prevention rule

Migration is a repair capability, not the preferred normal path. The Runtime Planner now deterministically extracts explicit WU-* identifiers from the top-level project objective. Every such identifier must appear as an independent Work Unit in the initial plan. Aggregators and fan-in units may coexist, but cannot replace explicitly named Work Units.

Historical WU references present only in context or constraints are intentionally not treated as mandatory new nodes; only the top-level objective establishes this identity-preservation invariant.

If the first Planner response collapses explicit ids, Adaptive rejects it with EXPLICIT_WORK_UNIT_IDS_MISSING and gives the Planner one governed recovery attempt to return the full explicit catalog. A second omission fails closed.

## When to use migration

Use it when all of the following hold:

- the orchestration is still non-terminal;
- historical nodes/results must remain authoritative;
- approved explicit Work Units are missing from the persisted graph;
- ordinary additive replan cannot recover the required identity/dependency model without rewriting historical meaning;
- there are no active workers and the project can be paused safely.

Do not use migration to bypass failed tests, reopen terminal projects, fabricate acceptance, change business rules, or edit historical results.
