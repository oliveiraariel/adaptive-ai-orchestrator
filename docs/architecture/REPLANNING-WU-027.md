# Replanning — WU-027

Initial implementation of `ReplanProject`.

## Design basis

The Design defines the Replan use case as:

```text
load current Plan
→ load event/change
→ analyze impact
→ identify affected Work Units
→ preserve unaffected work
→ adjust plan
→ re-evaluate resources
→ validate new plan
→ persist version
```

The project-specific Replanning document further states that replanning must
preserve the maximum amount of valid work and modify only what the new state
requires.

## Implemented in this slice

- `PlanRevision`
- `ReplanProjectRequest`
- `ReplanProjectResult`
- `ReplanProject`
- version incrementing;
- preserving unaffected Work Units;
- adding Work Units;
- removing Work Units;
- reopening affected completed Work Units;
- rebuilding the Plan through `PlanWork`;
- recording a trigger;
- recording affected Work Units and changes.

## Deliberate limits

This is the first executable replanning slice.

It does not yet implement:

- sophisticated impact analysis;
- automatic resource re-evaluation;
- human escalation;
- persistence;
- retry/fallback policy;
- event sourcing;
- full change classification.

The next implementation slices can deepen these behaviors when justified.

## Architectural intent

The preferred public shape remains:

```text
replan(projectState, trigger)
→ PlanRevision
```

The internal impact and plan adjustment steps remain inside the application
module rather than being exposed as multiple public modules.
