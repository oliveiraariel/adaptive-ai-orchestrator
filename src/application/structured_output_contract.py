from __future__ import annotations

import json
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


class StructuredOutputContractError(ValueError):
    """Raised when model output violates a declared structured-output contract."""


def validate_structured_json(
    text: str,
    schema: Mapping[str, Any],
) -> tuple[Any, str]:
    """Parse, validate and canonicalize one strict JSON document.

    The boundary is intentionally fail-closed: Markdown fences, leading/trailing
    prose and partial JSON extraction are not accepted. The caller may preserve
    the raw text separately for incident evidence before invoking this function.
    """

    if not isinstance(text, str):
        raise StructuredOutputContractError("Structured output must be UTF-8 text.")
    if not isinstance(schema, Mapping):
        raise StructuredOutputContractError("Structured output schema must be an object.")

    try:
        Draft202012Validator.check_schema(dict(schema))
    except SchemaError as exc:
        raise StructuredOutputContractError(
            f"Structured output schema is invalid: {exc.message}"
        ) from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputContractError(
            "Structured output is not one strict JSON document: "
            f"{exc.msg} at line {exc.lineno} column {exc.colno}."
        ) from exc

    validator = Draft202012Validator(dict(schema))
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        first = errors[0]
        path = "$"
        for part in first.absolute_path:
            path += f"[{part}]" if isinstance(part, int) else f".{part}"
        raise StructuredOutputContractError(
            f"Structured output violates schema at {path}: {first.message}"
        )

    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return payload, canonical
