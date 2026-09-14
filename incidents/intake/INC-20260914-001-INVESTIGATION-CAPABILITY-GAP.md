# INC-20260914-001 — Investigation capability gap

**Type:** capability gap / improvement investigation  
**Origin:** human guidance during implementation of Incident, Proactive Resolution & Learning v1  
**Lifecycle intent:** first official project incident handled by the new incident lifecycle  
**Current phase:** basic lifecycle structure only; final design and consolidation intentionally deferred

## Why this incident exists

Adaptive was originally intended to learn from day-to-day engineering experience.
The current incident lifecycle now gives defects and meaningful gaps persistent identity,
history, resolution pressure, learning promotion and dissemination.

The next missing capability is a governed **Investigation capability**, potentially
implemented partly as an `Investigation Skill`, that can be invoked when Adaptive,
a sentinel, a worker, or a human detects a defect or meaningful improvement opportunity.

This capability must not become the owner of the incident lifecycle. Adaptive core
remains authoritative for incident identity, persistence, pressure, lifecycle state,
learning promotion, dissemination and closure.

## Intended future behavior

A future investigation flow should be able to:

1. receive an incident or improvement investigation from Adaptive;
2. inspect existing Adaptive learned knowledge before repeating work;
3. use the selected specialist Skills and model knowledge;
4. perform bounded local diagnosis and experiments;
5. research external authoritative sources when policy permits;
6. preserve evidence and progress so an active investigation is not mistaken for a
   stalled or finished search;
7. return candidate solutions to the orchestrator for implementation and validation;
8. continue until a governed stop condition is reached rather than stopping simply
   because one worker/session ended.

## Decisions intentionally left open

These questions are **not resolved by the current implementation** and must remain
visible while this incident is active:

- Should extensive investigation be performed directly by the orchestrator, by one or
  more specialized workers, by an Investigation Skill, or by a hybrid arrangement?
- What evidence proves that a long investigation is still making progress and must not
  be closed prematurely?
- Which heartbeat/progress semantics distinguish an active search from a stalled search?
- When should Adaptive escalate the search to another worker, model, strategy, Skill,
  experiment, or external source?
- When should external research start automatically?
- Which attempt, cost, time, novelty, evidence, and diminishing-return budgets should
  constrain the investigation?
- At what point may Adaptive declare that no currently implementable, testable and
  passing solution was found?
- Which terminal/non-terminal state should represent that outcome: `BLOCKED`,
  `EXHAUSTED`, a new state, or another governed disposition?
- When must a human decision be requested?
- Under which future evidence may the investigation be reopened automatically?

## Current implementation boundary

For the current phase, only the **basic incident lifecycle and intake path** should be
finished. The Investigation Skill/capability itself, extensive-search ownership,
search-liveness semantics, exhaustion policy and final consolidation will be designed
in a later iteration with human guidance.

## Closure criteria for this incident

Do **not** consider this incident complete merely because this intake record exists.

It may be closed only after a later design/implementation cycle has, at minimum:

- decided the architecture boundary between Adaptive core and the Investigation Skill;
- specified who owns and executes extensive investigation;
- specified durable search/progress/liveness evidence;
- specified bounded escalation and exhaustion/stop semantics;
- implemented the chosen capability;
- validated it through representative incident-resolution tests;
- made an explicit learning/dissemination decision;
- passed the knowledge consistency check.

Until then, this record is an intentional active obligation and a real lifecycle test
case for the Adaptive system itself.
