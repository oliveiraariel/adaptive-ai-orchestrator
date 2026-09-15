# Adaptive communication protocols

Machine-significant Adaptive component communication uses **AMEP v1**.

Normative architecture: docs/architecture/ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md

Schemas here define stable transport envelopes. Payload-specific contracts may evolve independently under versioned names.

Rules:
1. never change an existing schema version incompatibly;
2. add a new version for breaking changes;
3. keep implementation validators and schema examples aligned;
4. transport schemas do not replace payload/domain validation.
