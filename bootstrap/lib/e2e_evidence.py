#!/usr/bin/env python3
"""Validate semantic evidence from the OpenClaw -> Adaptive inbound E2E.

The validator intentionally accepts both machine-style keys and humanized
assistant wording. The runtime contract is semantic: a completed project, the
required minimum observed parallelism, and the fan-in marker must all be
present. Formatting differences such as ``max_parallelism_observed`` versus
``Max parallelism observed`` must not create false negatives.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

FAN_IN_MARKER = "ADAPTIVE_MULTIAGENT_FANIN_OK"


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _walk_strings(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _load_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    return "\n".join(_walk_strings(parsed))


def _normalized(text: str) -> str:
    return re.sub(r"[_\-]+", " ", text).lower()


def _parallelism_values(text: str) -> list[int]:
    values: list[int] = []
    patterns = (
        r"max[_\s-]*parallelism[_\s-]*observed\s*[:=]\s*`?(\d+)",
        r"maximum[_\s-]*parallelism[_\s-]*observed\s*[:=]\s*`?(\d+)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            values.append(int(match.group(1)))
    return values


def validate_evidence(text: str, minimum_parallelism: int = 3) -> dict[str, Any]:
    normalized = _normalized(text)
    parallelism_values = _parallelism_values(text)
    max_parallelism = max(parallelism_values, default=0)

    status_completed = bool(
        re.search(r"(?:project\s+)?status\s*[:=]\s*`?completed\b", normalized)
        or re.search(r'"status"\s*:\s*"completed"', text, flags=re.IGNORECASE)
        or re.search(r"\bcompleted\s+work\s+units\b", normalized)
    )
    fan_in_present = FAN_IN_MARKER in text
    parallelism_ok = max_parallelism >= minimum_parallelism

    return {
        "ok": status_completed and fan_in_present and parallelism_ok,
        "status_completed": status_completed,
        "fan_in_present": fan_in_present,
        "max_parallelism_observed": max_parallelism,
        "minimum_parallelism": minimum_parallelism,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--minimum-parallelism", type=int, default=3)
    args = parser.parse_args(argv)

    combined = "\n".join(_load_text(path) for path in args.paths if path.exists())
    result = validate_evidence(combined, args.minimum_parallelism)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
