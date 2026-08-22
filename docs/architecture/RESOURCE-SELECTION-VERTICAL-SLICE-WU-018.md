# Resource Selection Vertical Slice — WU-018

Third vertical slice of the Adaptive AI Orchestrator.

## Composition

```text
Work Unit
+
Agent Profile
+
Skill Profile
+
Model Profile
+
In-Memory Catalogs
+
Agent & Skill Analysis
+
Resource Selection
    ↓
ResourceConfiguration
```

## Proven behavior

The slice demonstrates that the Orchestrator can:

1. read required capabilities from a Work Unit;
2. identify a compatible Agent;
3. identify compatible Skills;
4. find an available compatible Model;
5. produce a concrete `ResourceConfiguration`;
6. refuse to produce a configuration when model compatibility is not satisfied.

## Architectural boundary

The slice keeps the Resource Selection pipeline behind the single
application operation represented by `ResourceSelection`.

No external provider, runtime adapter, persistence mechanism, or Policy
engine is introduced here.

## Exit criterion

The Orchestrator can select a candidate execution configuration without
depending on OpenClaw or another external runtime.
