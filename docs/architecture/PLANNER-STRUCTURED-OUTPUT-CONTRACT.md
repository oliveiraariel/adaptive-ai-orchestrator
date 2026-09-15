# Planner Structured Output Contract v1

## Status

Mandatory machine-output contract for the Adaptive Planner.

## Problem

A model response is untrusted text. Prompting a model to "return JSON" is not a protocol guarantee.
The Planner must therefore be treated as a producer behind a contract boundary: its raw model
output may be preserved for diagnosis, but Adaptive must not accept it as a plan unless it is one
strict JSON document that validates against the versioned Planner schema and then satisfies the
domain graph invariants.

## Contract identity

AMEP message type:

`planner.plan`

Schema identity:

`planner-output/1`

Formal JSON Schema:

`specifications/protocols/planner-output-v1.schema.json`

The runtime copy of the schema is defined in
`src/application/planner_output_contract.py` and is registered through
`src/application/message_schema_registry.py`.

## Coercive lifecycle

The contract is enforced automatically; a caller does not opt into it with prompt wording.

1. Adaptive constructs the Planner request and includes the canonical schema in the Planner prompt.
2. The Planner result declares `planner.plan` / `planner-output/1` and JSON content type.
3. The runtime preserves the raw worker result through the existing Result Store/AMEP evidence path.
4. At the Adaptive orchestration boundary, `result_schema_name=planner-output` resolves to the
   registered JSON Schema.
5. The output must be exactly one JSON document. Markdown fences, explanatory prose and partial
   object extraction are rejected.
6. JSON Schema validation is fail-closed, including `additionalProperties=false`.
7. Valid JSON is canonicalized deterministically before it is exposed upward.
8. `RuntimeProjectPlanner` then applies semantic/domain validation: Work Unit budget, skills,
   dependency references, graph acyclicity and other invariants.
9. Only after both structural and semantic validation may a `ProjectExecutionPlan` exist.
10. A first contract failure may trigger the existing single bounded Planner recovery attempt.
    Repeated failure remains terminal and is available to the circuit breaker/self-healing layer.

Therefore an LLM may physically emit malformed text, but it cannot make that text become an
accepted Planner document. The trusted producer is the Adaptive contract gateway, not the model.

## Raw evidence versus canonical message

Raw model output and canonical machine messages are deliberately distinct:

- raw output is operational evidence and must not be destroyed merely because it is invalid;
- canonical Planner data is accepted only after schema validation;
- invalid output must never be silently repaired into a different plan;
- normalization is limited to deterministic JSON canonicalization after successful validation.

This preserves the AMEP principle that transport evidence remains diagnosable while preventing
untrusted model text from crossing a machine boundary as authoritative data.

## Why prompt-only enforcement is insufficient

Provider/model structured-output features are useful prevention, but they are not the authority.
Provider adapters can omit, transform or fail to propagate response-format constraints. Adaptive
therefore validates at its own boundary even when constrained decoding or tool-schema generation
is available.

A future runtime adapter may additionally use provider-native structured output or OpenClaw's
schema-bound structured-output tooling. Such support is defense in depth; it must not replace the
Adaptive validator.

## Failure classes

- invalid UTF-8 / unavailable payload: transport failure;
- malformed JSON: structured-output syntax failure;
- valid JSON that violates `planner-output/1`: contract/schema failure;
- schema-valid plan with invalid dependencies/graph semantics: Planner semantic failure;
- repeated equivalent failure after bounded recovery: circuit-breaker input.

## Test obligations

At minimum:

- strict valid Planner JSON passes;
- Markdown-fenced JSON fails;
- prose-wrapped JSON fails;
- unknown fields fail;
- wrong JSON types fail;
- run-specific Work Unit budget fails when exceeded;
- formal schema document matches runtime schema;
- orchestration rejects a `planner-output` result that violates the schema;
- Planner traffic declares `application/json`;
- semantic dependency-cycle validation remains active.

## Skill boundary

This contract is runtime infrastructure, not an agent skill. Skills may guide planning quality but
cannot weaken or override the schema, parser, AMEP identity or semantic validator.
