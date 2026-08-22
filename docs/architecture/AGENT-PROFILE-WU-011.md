# Agent Profile — WU-011

Initial domain representation of an agent that may execute Work Units.

## Implemented

- `AgentId`
- `AgentProfile`
- declared role and responsibilities
- capabilities
- skills
- tools
- eligible models
- context requirements
- permissions
- runtime metadata
- evidence
- basic capability/skill/model checks
- domain tests

## Domain rule

The profile represents declared capability and configuration.

It must remain distinct from empirical execution history. Evidence is
recorded as provenance for the declaration; historical performance belongs
to later evaluation and telemetry concerns.

## Scope

This Work Unit does not implement agent discovery, catalogs, model
selection, runtime integration, empirical scoring, or delegation.
