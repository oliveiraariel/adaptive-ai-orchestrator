# Agent & Skill Analysis — WU-015

Initial application module for analysing whether declared Agents and
Skills are compatible with a Work Unit.

## Flow

```text
Work Unit
→ required capabilities
→ eligible agents
→ compatible Skills
→ confidence
→ candidates
```

## Implemented

- `AgentSkillCandidate`
- `AgentSkillAnalysisResult`
- `AgentSkillAnalysis`
- capability matching
- agent compatibility through Skill profiles
- confidence calculation
- deterministic candidate ordering
- application tests

## Architectural intent

The analysis keeps the selection pipeline behind one application interface.
It does not expose internal candidate-resolution stages as public modules.

The use case does not choose a ModelProfile. Model selection remains a
separate concern for the Resource Selection stage.

## Scope

This Work Unit does not implement:

- model selection;
- final ResourceConfiguration;
- Policy evaluation;
- runtime selection;
- delegation;
- empirical agent performance scoring.
