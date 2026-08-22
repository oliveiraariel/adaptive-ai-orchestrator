# Model Profile — WU-013

Initial domain representation of a model known to the Orchestrator.

## Implemented

- `ModelId`
- `ModelProfile`
- name and version
- provider
- capabilities
- context information
- cost
- latency
- availability
- restrictions
- evidence
- basic capability/restriction checks
- domain tests

## Boundary

`ModelProfile` describes a model available to the Orchestrator.

It does not invoke a provider, perform model selection, estimate costs
dynamically, or connect to a runtime.

Those concerns belong to later Work Units.

## Scope

This Work Unit does not implement:

- model catalog;
- provider adapters;
- model selection;
- dynamic availability monitoring;
- runtime execution.
