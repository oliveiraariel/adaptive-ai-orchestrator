from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ConsistencyRule:
    id: str
    description: str
    relative_paths: tuple[str, ...]
    required_fragments: tuple[str, ...] = ()
    forbidden_fragments: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsistencyFinding:
    rule_id: str
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class ConsistencyReport:
    passed: bool
    evidence_refs: tuple[str, ...]
    findings: tuple[ConsistencyFinding, ...]


class KnowledgeConsistencySentinel:
    """Deterministically check promoted invariants against governed text artifacts."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()

    def check(self, rules: Iterable[ConsistencyRule]) -> ConsistencyReport:
        findings: list[ConsistencyFinding] = []
        evidence: list[str] = []
        for rule in rules:
            for relative in rule.relative_paths:
                path = (self.repository_root / relative).resolve()
                if not path.is_relative_to(self.repository_root):
                    findings.append(
                        ConsistencyFinding(rule.id, relative, 0, "path escapes repository root")
                    )
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    findings.append(
                        ConsistencyFinding(rule.id, relative, 0, "required file is unreadable")
                    )
                    continue

                for fragment in rule.required_fragments:
                    if fragment not in text:
                        findings.append(
                            ConsistencyFinding(
                                rule.id,
                                relative,
                                0,
                                f"required fragment missing: {fragment[:120]}",
                            )
                        )
                    else:
                        line = text[: text.index(fragment)].count("\n") + 1
                        evidence.append(f"{relative}:L{line}:{rule.id}:required")

                for fragment in rule.forbidden_fragments:
                    offset = text.find(fragment)
                    if offset >= 0:
                        line = text[:offset].count("\n") + 1
                        findings.append(
                            ConsistencyFinding(
                                rule.id,
                                relative,
                                line,
                                f"forbidden stale fragment present: {fragment[:120]}",
                            )
                        )
                    else:
                        evidence.append(f"{relative}:{rule.id}:forbidden-absent")

        return ConsistencyReport(
            passed=not findings,
            evidence_refs=tuple(dict.fromkeys(evidence)),
            findings=tuple(findings),
        )


def worker_protocol_consistency_rules() -> tuple[ConsistencyRule, ...]:
    return (
        ConsistencyRule(
            id="adaptive-owns-result-manifest",
            description="Result Store docs must preserve Adaptive-owned manifest finalization.",
            relative_paths=("docs/architecture/ADAPTIVE-RESULT-STORE.md",),
            required_fragments=(
                "The worker **must not create or edit**",
                "Adaptive\n  -> reads final result.txt",
                "Runtime `COMPLETED` alone does not satisfy the authoritative completion contract.",
            ),
            forbidden_fragments=(
                "write `manifest.json.tmp`",
                "atomically rename the manifest to `manifest.json` **last**",
                "byte length when supplied",
                "SHA-256 when supplied",
            ),
        ),
        ConsistencyRule(
            id="worker-protocol-contract-ownership",
            description="Worker Protocol docs must keep machine integrity under Adaptive ownership.",
            relative_paths=("docs/architecture/WORKER-PROTOCOL-V1-RESULT-TRANSPORT.md",),
            required_fragments=(
                "worker_writes_manifest: false",
                "adaptive_finalizes_manifest: true",
                "completion_requires: RESULT_VERIFIED",
                "Runtime `COMPLETED` alone is not authoritative completion.",
            ),
        ),
    )
