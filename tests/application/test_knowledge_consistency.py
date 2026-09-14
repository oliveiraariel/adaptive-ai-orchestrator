from pathlib import Path

from application.knowledge_consistency import (
    ConsistencyRule,
    KnowledgeConsistencySentinel,
)


def test_consistency_sentinel_requires_and_forbids_exact_governed_fragments(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "contract.md").write_text(
        "Adaptive owns manifest.\nRESULT_VERIFIED is authoritative.\n",
        encoding="utf-8",
    )
    rule = ConsistencyRule(
        id="manifest-owner",
        description="owner",
        relative_paths=("docs/contract.md",),
        required_fragments=("Adaptive owns manifest.",),
        forbidden_fragments=("worker writes manifest",),
    )
    report = KnowledgeConsistencySentinel(tmp_path).check((rule,))
    assert report.passed is True
    assert report.findings == ()
    assert report.evidence_refs


def test_consistency_sentinel_fails_on_stale_statement(tmp_path: Path):
    (tmp_path / "contract.md").write_text(
        "worker writes manifest\n",
        encoding="utf-8",
    )
    rule = ConsistencyRule(
        id="manifest-owner",
        description="owner",
        relative_paths=("contract.md",),
        required_fragments=("Adaptive owns manifest.",),
        forbidden_fragments=("worker writes manifest",),
    )
    report = KnowledgeConsistencySentinel(tmp_path).check((rule,))
    assert report.passed is False
    assert len(report.findings) == 2
