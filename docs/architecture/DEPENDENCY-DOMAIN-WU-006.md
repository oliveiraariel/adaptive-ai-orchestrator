# Dependency Domain — WU-006

Initial domain representation for dependencies between project Work Units.

## Implemented

- `Dependency`
- `DependencyType`
- `DependencyStatus`
- required/optional blocking semantics
- satisfaction and blocking transitions
- basic invariants
- domain tests

## Scope

This Work Unit does not implement graph construction, cycle detection,
plan generation, or readiness calculation across a collection of Work Units.

Those concerns remain for subsequent planning Work Units.
