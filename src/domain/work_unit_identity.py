from __future__ import annotations

import re
from typing import Iterable


_EXPLICIT_WORK_UNIT_ID = re.compile(r"\bWU-[A-Z0-9]+(?:-[A-Z0-9]+)*\b", re.IGNORECASE)


class WorkUnitIdentityError(ValueError):
    """Raised when an explicit governance identity declaration is invalid."""


def extract_explicit_work_unit_ids(*texts: str) -> tuple[str, ...]:
    """Return literal WU-* ids authored in authoritative request text.

    Detection is intentionally limited to text a caller identifies as authoritative
    request material (normally objective/scope). Retrieved context is not scanned
    automatically because historical notes may mention Work Units that are not part
    of the current requested graph.
    """

    found: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if not isinstance(text, str):
            continue
        for match in _EXPLICIT_WORK_UNIT_ID.finditer(text):
            value = match.group(0).upper()
            if value in seen:
                continue
            seen.add(value)
            found.append(value)
    return tuple(found)


def merge_required_work_unit_ids(
    declared: Iterable[str],
    detected: Iterable[str],
) -> tuple[str, ...]:
    """Merge structured and text-detected governance ids without losing order."""

    result: list[str] = []
    seen: set[str] = set()
    for raw in (*tuple(declared), *tuple(detected)):
        if not isinstance(raw, str) or not raw.strip():
            raise WorkUnitIdentityError(
                "Required Work Unit ids must be non-empty strings."
            )
        value = raw.strip()
        key = value.upper()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)
