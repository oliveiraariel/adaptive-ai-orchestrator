# WIP Preservation — Incident / Investigation Lifecycle

**Status:** protected work in progress  
**Owner directive date:** 2026-09-14  
**Tracked issue:** #38  
**Draft PR:** #39

## Owner directive

This work is intentionally unfinished.

Until the repository owner explicitly asks the orchestrator to resume, redesign,
finalize, or remove this capability, agents and automated maintenance must **preserve
the WIP artifacts and their incident-related integration changes**.

Do not delete, rename, move, collapse, "clean up", supersede, or semantically repurpose
the protected artifacts below merely because the Investigation Skill is not complete.

Do not revert the incident-related portions of existing integration files.

Allowed without a new owner directive:
- read and inspect;
- run tests and validation;
- report conflicts or defects;
- reference these artifacts in handoff/context.

If unrelated work conflicts with these artifacts, surface the conflict instead of
silently removing or rewriting this WIP.

## Why these artifacts exist

They implement the basic Adaptive Incident, Proactive Resolution & Learning lifecycle
and preserve the first official lifecycle case:

`INC-20260914-001-INVESTIGATION-CAPABILITY-GAP`

That case exists specifically so a later owner-directed session can continue the design
of an Investigation Skill/capability for bugs, defects and improvement investigations.

The later design still needs stronger provenance/context fields, search ownership,
search-liveness/progress semantics, escalation rules, exhaustion/stop policy, human
intervention rules and reopening semantics.

## Protected newly introduced structure

~~~text
adaptive-ai-orchestrator/
├── incidents/
│   └── intake/
│       ├── README.md
│       ├── WIP-PRESERVATION.md
│       ├── INC-20260914-001-INVESTIGATION-CAPABILITY-GAP.json
│       └── INC-20260914-001-INVESTIGATION-CAPABILITY-GAP.md
├── docs/
│   └── architecture/
│       └── INCIDENT-PROACTIVE-LEARNING-PROTOCOL-V1.md
├── src/
│   ├── domain/
│   │   └── incident.py
│   ├── application/
│   │   ├── incident_intake.py
│   │   ├── incident_management.py
│   │   ├── incident_ports.py
│   │   ├── incident_research.py
│   │   ├── incident_supervisor.py
│   │   └── knowledge_consistency.py
│   └── infrastructure/
│       └── incident_registry.py
└── tests/
    └── application/
        ├── test_incident_intake.py
        ├── test_incident_management.py
        ├── test_incident_ports.py
        ├── test_incident_research.py
        ├── test_incident_supervisor.py
        └── test_knowledge_consistency.py
~~~

## Existing integration files with protected incident-related changes

These files existed before this WIP. They are not globally frozen, but the
incident/result-lifecycle changes introduced by Draft PR #39 must not be removed or
rewritten without an explicit owner-directed continuation/finalization of this work:

~~~text
PROJECT-KNOWLEDGE-MANIFEST.yaml
docs/architecture/ADAPTIVE-RESULT-STORE.md
docs/architecture/ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md
docs/architecture/ORCHESTRATOR-CONTINUITY-AND-LEARNING.md
docs/problem-solving-learning.md
knowledge/problem-solving-strategies.json
src/adaptive_orchestrator/cli.py
src/application/continuous_project_orchestration.py
src/application/run_orchestration.py
src/application/run_project_orchestration.py
src/application/runtime_project_planner.py
src/application/worker_protocol.py
src/infrastructure/openclaw_gateway_client.py
tests/application/test_problem_solving_learning.py
tests/application/test_run_project_orchestration.py
tests/application/test_worker_protocol.py
tests/system/test_adaptive_cli.py
~~~

## Resume condition

Resume design or implementation only when the repository owner explicitly asks the
orchestrator to continue/finalize Issue #38 or the Investigation Skill/capability.

When that happens, begin by reading:
1. Issue #38;
2. Draft PR #39;
3. this file;
4. `INC-20260914-001-INVESTIGATION-CAPABILITY-GAP.md`;
5. `INCIDENT-PROACTIVE-LEARNING-PROTOCOL-V1.md`.

This file is a preservation guardrail, not proof that the live incident is active.
Operational lifecycle state remains owned by Adaptive IncidentRegistry.
