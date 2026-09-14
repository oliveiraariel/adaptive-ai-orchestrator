# Project Incident Intake

This directory contains **versioned incident declarations**, not live runtime state.

Its purpose is to let a project preserve a known defect, capability gap, or improvement
investigation across machines and sessions before Adaptive has an operational
`IncidentRegistry` entry for it.

## Contract

- `*.json` files are machine-readable intake declarations.
- A declaration is idempotently promoted into Adaptive's persistent operational
  `IncidentRegistry` when project incident intake is registered.
- The live incident remains under the normal state directory
  (`~/.local/state/adaptive-ai-orchestrator/incidents/` by default).
- Static repository files never become authoritative live state by themselves.
- The declaration may point to a bounded Markdown evidence/intention document.
- Closing or waiving a live incident does not delete its historical intake declaration.
- An unchanged declaration must not recreate a closed incident on every execution.

This boundary keeps project intent versioned while leaving lifecycle ownership,
state transitions, pressure, research, validation, learning, dissemination and closure
inside Adaptive core.
