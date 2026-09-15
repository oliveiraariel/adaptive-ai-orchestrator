# Adaptive communication protocols

Machine-significant Adaptive component communication uses **AMEP v1**.

Normative architecture: docs/architecture/ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md

Schemas here define stable transport envelopes and governed payload contracts.

Current schemas:
- `amep-message-ref-v1.schema.json` — compact control-plane reference;
- `amep-manifest-v1.schema.json` — durable message manifest;
- `planner-output-v1.schema.json` — mandatory Planner → Adaptive work-graph document.

Rules:
1. never change an existing schema version incompatibly;
2. add a new version for breaking changes;
3. keep implementation validators and schema documents aligned;
4. transport validation does not replace payload/domain validation;
5. a governed payload is not accepted as a component result unless it validates against its versioned schema.
