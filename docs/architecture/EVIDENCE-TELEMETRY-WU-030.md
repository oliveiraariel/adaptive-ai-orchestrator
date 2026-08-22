# Evidence / Telemetry — WU-030

Initial domain representation for evidence captured during orchestration.

## Purpose

Evidence provides a normalized record of observations that can support:

- result evaluation;
- decisions;
- continuity;
- replanning;
- future learning.

The object also preserves provenance so observations are not detached from
their source.

## Implemented

- `EvidenceRecord`
- `EvidenceType`
- source
- content
- confidence
- timestamp
- references
- metadata
- domain invariants
- domain tests

## Architectural intent

This Work Unit models the evidence itself.

It does not create a telemetry backend, event bus, log adapter, or external
observability system. Those are infrastructure concerns and require a
separate seam only when a concrete need is established.

## Scope

This Work Unit does not implement:

- telemetry collection;
- event streaming;
- persistence;
- metrics aggregation;
- automatic provenance resolution;
- LearningCandidate creation.
