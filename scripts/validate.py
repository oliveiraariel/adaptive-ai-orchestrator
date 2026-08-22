#!/usr/bin/env python3
"""Run the project's final practical validation suite."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    command = [sys.executable, "-m", "pytest", "tests"]

    print("Running final practical validation:")
    print(" ".join(command))
    print()

    completed = subprocess.run(command, check=False)

    if completed.returncode == 0:
        print()
        print("PRACTICAL VALIDATION: PASS")
    else:
        print()
        print(
            "PRACTICAL VALIDATION: FAIL "
            f"(exit code {completed.returncode})"
        )

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
