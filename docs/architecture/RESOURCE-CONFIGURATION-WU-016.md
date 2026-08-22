# Resource Configuration — WU-016

Initial domain representation of a concrete candidate or selected resource
configuration for a Work Unit.

## Implemented

- `ResourceConfiguration`
- agent
- Skills
- model
- provider
- tools
- runtime
- policy constraints
- basic invariants
- domain tests

## Architectural intent

`ResourceConfiguration` represents a configuration, not the process that
selects it.

Selection logic remains in the Resource Selection use case and is not
duplicated in this domain object.

The model stays technology-neutral: values identify resources known to the
Orchestrator without embedding provider or runtime SDK types.

## Scope

This Work Unit does not implement:

- resource ranking;
- policy evaluation;
- compatibility analysis;
- model selection;
- runtime invocation;
- persistence.
