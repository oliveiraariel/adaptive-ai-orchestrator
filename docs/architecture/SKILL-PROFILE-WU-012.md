# Skill Profile — WU-012

Initial domain representation of a Skill known to the Orchestrator.

## Implemented

- `SkillId`
- `SkillProfile`
- purpose
- capabilities
- inputs and outputs
- dependencies
- compatible agents
- compatible models
- compatible runtimes
- version
- evidence
- basic compatibility checks
- domain tests

## Architectural boundary

The profile is a representation used by the Orchestrator to reason about
Skills. It does not implement the Skill itself.

Advanced concepts identified for a future Skill Architecture, such as
invocation policy, composition, provenance and runtime-specific metadata,
are intentionally not expanded here. They belong to later work unless a
concrete Work Unit requires them.

## Scope

This Work Unit does not implement:

- Skill catalog;
- Skill discovery;
- Skill invocation;
- Skill composition engine;
- runtime-specific execution;
- empirical performance history.
