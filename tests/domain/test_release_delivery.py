import hashlib
import json
import zipfile
from pathlib import Path

from domain.release_delivery import validate_release_delivery


def _manifest(tmp_path: Path, *, report: bool = True, corrupt: bool = False) -> tuple[dict, Path]:
    artifact = tmp_path / "release.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("plugin/main.php", "<?php\n")
    report_path = tmp_path / "release-report.md"
    if report:
        report_path.write_text("validated release", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    payload = {
        "schema_version": 1,
        "artifact_path": str(artifact),
        "report_path": str(report_path) if report else None,
        "source_identity": "repo@abc123",
        "version": "1.2.4",
        "internal_version": "1.2.4",
        "size_bytes": artifact.stat().st_size,
        "sha256": ("0" * 64) if corrupt else digest,
        "integrity_checked": True,
        "install_structure_checked": True,
        "validations": ["zipfile.testzip", "plugin-version-check"],
        "environment_ready": True,
    }
    manifest = tmp_path / "delivery-manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return payload, manifest


def test_valid_zip_and_report_are_accepted(tmp_path: Path) -> None:
    _, manifest = _manifest(tmp_path)
    result = validate_release_delivery(
        raw_result={"release_manifest": str(manifest)}, output=""
    )
    assert result.valid
    assert result.version == "1.2.4"


def test_missing_report_is_rejected(tmp_path: Path) -> None:
    _, manifest = _manifest(tmp_path, report=False)
    result = validate_release_delivery(
        raw_result={"release_manifest": str(manifest)}, output=""
    )
    assert result.reason == "release-report-required"


def test_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    _, manifest = _manifest(tmp_path, corrupt=True)
    result = validate_release_delivery(
        raw_result={"release_manifest": str(manifest)}, output=""
    )
    assert result.reason == "release-artifact-integrity-mismatch"


def test_corrupt_zip_is_rejected_even_when_manifest_claims_integrity(tmp_path: Path) -> None:
    _, manifest = _manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifact = Path(payload["artifact_path"])
    artifact.write_bytes(b"not a zip")
    payload["size_bytes"] = artifact.stat().st_size
    payload["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = validate_release_delivery(
        raw_result={"release_manifest": str(manifest)}, output=""
    )
    assert result.reason == "release-artifact-integrity-invalid"


def test_internal_version_mismatch_is_rejected(tmp_path: Path) -> None:
    _, manifest = _manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["internal_version"] = "1.2.3"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = validate_release_delivery(
        raw_result={"release_manifest": str(manifest)}, output=""
    )
    assert result.reason == "release-version-mismatch"


def test_multiple_candidates_are_rejected_without_canonical_delivery(tmp_path: Path) -> None:
    # Two distinct declarations model the ambiguous multi-ZIP situation.
    _, manifest = _manifest(tmp_path)
    result = validate_release_delivery(
        raw_result={"release_manifests": [str(manifest), str(manifest) + ".other"]},
        output="",
    )
    assert result.reason == "release-manifest-canonicality-required"
