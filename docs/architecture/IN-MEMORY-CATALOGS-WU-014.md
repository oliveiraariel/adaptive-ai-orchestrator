# In-Memory Catalogs — WU-014

Minimal in-memory catalogs for the three profiles introduced in
WU-011 to WU-013.

## Implemented

- `AgentCatalog` / `InMemoryAgentCatalog`
- `SkillCatalog` / `InMemorySkillCatalog`
- `ModelCatalog` / `InMemoryModelCatalog`
- add, get and list operations
- replacement by stable identifier
- isolated catalog state
- infrastructure tests

## Architectural intent

These catalogs are intentionally in-memory.

They provide the smallest useful mechanism for the next Work Units to
query known agents, Skills and models without prematurely introducing
external storage or discovery infrastructure.

The catalogs are treated as internal modules for now. A public or
remote seam will only be introduced when a real variation or external
dependency justifies it.

## Scope

This Work Unit does not implement:

- remote discovery;
- persistence;
- ranking;
- compatibility analysis;
- resource selection.
