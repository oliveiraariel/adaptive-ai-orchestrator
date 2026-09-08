from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "bootstrap" / "lib" / "e2e_evidence.py"
SPEC = importlib.util.spec_from_file_location("e2e_evidence", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_accepts_machine_style_evidence() -> None:
    text = '''
    {"status":"COMPLETED","max_parallelism_observed":3,
     "output":"ADAPTIVE_MULTIAGENT_FANIN_OK"}
    '''
    result = MODULE.validate_evidence(text)
    assert result["ok"] is True
    assert result["max_parallelism_observed"] == 3


def test_accepts_humanized_assistant_evidence() -> None:
    text = '''
    Adaptive multi-agent validation completed successfully.
    - Project status: `COMPLETED`
    - Max parallelism observed: `3`
    - Completed Work Units: worker-a, worker-b, worker-c, fan-in
    - Fan-in: ADAPTIVE_MULTIAGENT_FANIN_OK
    All results were accepted.
    '''
    result = MODULE.validate_evidence(text)
    assert result["ok"] is True
    assert result["max_parallelism_observed"] == 3


def test_rejects_missing_parallel_evidence() -> None:
    text = '''
    Project status: COMPLETED
    Fan-in: ADAPTIVE_MULTIAGENT_FANIN_OK
    '''
    result = MODULE.validate_evidence(text)
    assert result["ok"] is False
    assert result["fan_in_present"] is True
    assert result["max_parallelism_observed"] == 0


def test_rejects_incomplete_project_even_with_markers() -> None:
    text = '''
    Project status: BLOCKED
    Max parallelism observed: 3
    Fan-in: ADAPTIVE_MULTIAGENT_FANIN_OK
    '''
    result = MODULE.validate_evidence(text)
    assert result["ok"] is False
    assert result["status_completed"] is False
