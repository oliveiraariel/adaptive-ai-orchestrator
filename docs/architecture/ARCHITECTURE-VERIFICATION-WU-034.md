# Architecture Verification — WU-034

Verification of the implemented code against the architectural boundaries
defined for the Adaptive AI Orchestrator.

## Design basis

The architecture requires the dependency direction to point toward the core:

```text
Interface / Infrastructure
        ↓
Application
        ↓
Domain
```

It explicitly prohibits the Domain from depending on OpenClaw, SQL, provider
SDKs, or other concrete external details.

Ports are contracts defined by the internal side of the system; concrete
adapters belong to Infrastructure.

## Verification implemented

The architecture tests verify that:

- `domain/`, `application/` and `infrastructure/` exist;
- Domain does not import Application;
- Domain does not import Infrastructure;
- Domain does not reference runtime-specific integration symbols;
- Application does not import the concrete OpenClaw adapter;
- the OpenClaw adapter remains isolated in Infrastructure;
- Application depends on the internal `AgentRuntime` seam;
- Domain/Application do not directly import representative external SDKs.

## Scope

This is structural verification, not a proof of every architectural
property.

It does not yet inspect:

- every dependency edge;
- every package boundary;
- runtime deployment topology;
- dynamic imports;
- configuration-level coupling;
- architectural quality beyond the encoded rules.

Those can be strengthened in later hardening work if the final validation
shows a concrete need.
