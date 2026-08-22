# Resource Selection — WU-017

Initial application use case for selecting a concrete resource configuration.

## Design alignment

The Design defines `SelectResource` as:

```text
load Work Unit
→ identify capabilities
→ query AgentCatalog
→ query SkillCatalog
→ query ModelCatalog
→ apply Policy
→ evaluate alternatives
→ produce ResourceConfiguration
```

This Work Unit implements the currently justified subset:

```text
Work Unit
→ Agent & Skill Analysis
→ Skill/Model compatibility
→ deterministic model selection
→ ResourceConfiguration
```

The Policy stage is intentionally not invented before a concrete Policy
model/use case is required.

## Implemented

- `ResourceSelectionRequest`
- `ResourceSelectionResult`
- `ResourceSelection`
- reuse of Agent & Skill Analysis
- SkillCatalog lookup
- ModelCatalog lookup
- Skill/Model compatibility filtering
- deterministic candidate selection
- `ResourceConfiguration` production
- application tests

## Architectural intent

The public shape remains a single application operation:

```text
SelectResource
→ ResourceConfiguration
```

The internal candidate reasoning remains hidden.

No provider adapter, runtime discovery, persistence or multi-objective
optimization is introduced in this slice.
