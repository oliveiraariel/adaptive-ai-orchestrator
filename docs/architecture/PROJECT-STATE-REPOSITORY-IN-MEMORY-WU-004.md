# Project State Repository — WU-004

Initial persistence adapter for Project state.

## Implemented

- minimal repository contract
- in-memory adapter
- save
- get
- replacement of existing state
- repository isolation
- infrastructure tests

## Scope

This Work Unit does not implement filesystem, database persistence,
serialization, concurrency control, or external runtime integration.

The domain remains independent of the storage mechanism.
