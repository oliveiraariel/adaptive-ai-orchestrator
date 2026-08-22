# Initialize Project — WU-005

First vertical slice of the Adaptive AI Orchestrator.

## Flow

```text
Initialize Project
→ Create Work Unit
→ Store State
→ Read State
```

## Implemented

- application use case for project initialization;
- application use case for Work Unit creation;
- application read use case;
- integration with the in-memory Project repository;
- end-to-end tests for the slice.

## Scope

This slice intentionally does not implement:

- planning;
- dependency resolution;
- agent/skill analysis;
- resource selection;
- delegation;
- evaluation;
- replanning;
- external persistence;
- runtime integration.

Those belong to later Work Units.
