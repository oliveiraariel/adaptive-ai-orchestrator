# Practical Validation — WU-037

Final practical validation gate for the Adaptive AI Orchestrator prototype.

## Purpose

This Work Unit does not add a new orchestration capability.

Its purpose is to establish one reproducible command that validates the
current implementation as a whole.

## Validation command

With the project's virtual environment active:

```bash
PYTHONPATH=src python scripts/validate.py
```

The runner executes:

```text
python -m pytest tests
```

and reports:

```text
PRACTICAL VALIDATION: PASS
```

only when the complete test suite exits successfully.

## Validation layers already present

The final suite includes:

```text
domain tests
application tests
infrastructure tests
vertical-slice tests
end-to-end tests
architecture verification
traceability verification
failure/recovery tests
final practical-validation smoke checks
```

## Practical acceptance

Before declaring the prototype complete, the final validation should confirm:

1. the full test suite passes;
2. architecture verification passes;
3. traceability verification passes;
4. the end-to-end orchestration test passes;
5. the working tree is intentionally reviewed before commit;
6. the final documentation and continuity records are updated.

## Explicit limitation

This gate validates the current prototype and its automated evidence.

It does not establish production readiness for:

- real OpenClaw connectivity;
- persistent storage;
- security hardening;
- operational deployment;
- concurrency;
- distributed execution;
- production observability.

Those remain future engineering work, not hidden completion criteria.

## Final project gate

The SDD definition of done requires work to be:

```text
specified
+
implemented
+
verified
+
reviewed
+
traceable
```

with architecture conformance, tests/evals and documentation updates when
applicable.

This Work Unit is the final executable verification point for the current
implementation scope.
