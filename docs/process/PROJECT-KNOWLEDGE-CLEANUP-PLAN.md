# Project Knowledge Cleanup Plan

## Immediate goals

1. eliminate confirmed current-state drift;
2. add the missing root resume entrypoint;
3. introduce machine-readable authority/retrieval classification;
4. logically quarantine legacy and historical knowledge without deleting it;
5. avoid premature physical moves before reference/impact analysis.

## Immediate changes

### Create

- `CONTEXT.md`
- `PROJECT-KNOWLEDGE-MANIFEST.yaml`
- `docs/process/PROJECT-KNOWLEDGE-GOVERNANCE.md`

### Update

- `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md`
  - remove stale Gateway-pending status;
  - set next gate to `WU-055 — Runtime Event Monitoring`;
  - distinguish Phase 2 and Gateway validation test snapshots;
  - update continuity version.

## Do not change yet

- `MASTER-SPECIFICATION*`
- `docs/process/history/skill/**`
- large capability docs
- Work Unit file locations
- citation markers
- architecture/requirements status labels

These require targeted review or impact analysis.

## Legacy handling

For now:

```text
retain in place
→ classify as legacy
→ exclude from default retrieval
→ consult only explicitly
```

After reviewing the latest Master Specification:

```text
legacy concept
→ classify
→ already absorbed / future Skill / future reference / incompatible
→ adopt only through governed current artifacts
```

## Historical handling

Keep historical plans/snapshots for traceability but mark `default_retrieval: false` in the manifest.

Potential future physical relocation into history/archive folders should happen only after checking internal links and references.

## Next review

The next legacy-focused review should inspect the newest `MASTER-SPECIFICATION-v0.3.md` and create a legacy knowledge catalog without changing current Orchestrator authority.
