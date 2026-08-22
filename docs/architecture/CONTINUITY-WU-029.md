# Continuity — WU-029

Initial domain representation of project continuity state.

## Purpose

The continuity record preserves enough structured state to resume a project
without treating a new session as a new project.

## Implemented

- `ContinuityRecord`
- `ContinuityStatus`
- project identity
- current Plan version
- current and pending Work Units
- decisions
- evidence
- open issues
- risks
- context
- immutable plan-version updates
- pause/resume/completion state
- domain tests

## Architectural intent

Continuity is treated as project state, not as an ad-hoc chat transcript.

The record preserves prior valid context so later orchestration can resume
from the current state instead of rebuilding the project from scratch.

## Scope

This Work Unit does not implement:

- persistent storage;
- chat/session adapters;
- automatic context compression;
- history indexing;
- knowledge retrieval;
- cross-project continuity.

Those concerns require later Work Units when their concrete seams are justified.
