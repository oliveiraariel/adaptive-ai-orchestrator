from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


RELEASE_DELIVERY_SCHEMA_VERSION = 1
RELEASE_MANIFEST_MARKER = "ADAPTIVE_RELEASE_MANIFEST"


@dataclass(frozen=True)
class ReleaseDeliveryCheck:
    valid: bool
    reason: str
    manifest_path: str | None = None
    artifact_path: str | None = None
    report_path: str | None = None
    version: str | None = None


def release_delivery_required(
    *, objective: str, scope: str = "", context: Iterable[str] = (), constraints: Iterable[str] = ()
) -> bool:
    from domain.release_artifact_policy import release_artifact_policy_applies

    return release_artifact_policy_applies(
        objective=objective, scope=scope, context=context, constraints=constraints
    )


def release_delivery_work_unit_ids(*, work_units: Iterable[object], constraints: Iterable[str] = ()) -> frozenset[str]:
    ids: set[str] = set()
    for spec in work_units:
        objective = str(getattr(spec, "objective", ""))
        scope = str(getattr(spec, "scope", ""))
        expected = tuple(getattr(spec, "expected_output", ()))
        criteria = tuple(getattr(spec, "acceptance_criteria", ()))
        role = str(getattr(spec, "role", ""))
        if release_delivery_required(
            objective=objective, scope=scope, context=(*expected, *criteria), constraints=constraints
        ) or any(
            marker in f"{role} {objective} {expected}".casefold()
            for marker in ("release", "package", "artifact", "delivery", "publish")
        ):
            ids.add(str(getattr(spec, "id")))
    return frozenset(ids)


def _candidate_paths(raw_result: object, output: str) -> tuple[str, ...]:
    candidates: list[str] = []
    if isinstance(raw_result, dict):
        for key in ("release_manifest", "delivery_manifest", "release_artifact_manifest"):
            value = raw_result.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())
        values = raw_result.get("release_manifests")
        if isinstance(values, list):
            candidates.extend(item.strip() for item in values if isinstance(item, str) and item.strip())
    for line in output.splitlines():
        key, separator, value = line.strip().partition(":")
        if separator and key == RELEASE_MANIFEST_MARKER and value.strip():
            candidates.append(value.strip())
    return tuple(dict.fromkeys(candidates))


def validate_release_delivery(*, raw_result: object, output: str, require_report: bool = True) -> ReleaseDeliveryCheck:
    candidates = _candidate_paths(raw_result, output)
    if len(candidates) != 1:
        return ReleaseDeliveryCheck(False, "release-manifest-canonicality-required")

    manifest_path = Path(candidates[0]).expanduser()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ReleaseDeliveryCheck(False, "release-manifest-unreadable", str(manifest_path))
    if not isinstance(payload, dict) or payload.get("schema_version") != RELEASE_DELIVERY_SCHEMA_VERSION:
        return ReleaseDeliveryCheck(False, "release-manifest-schema-invalid", str(manifest_path))

    required = ("artifact_path", "source_identity", "version", "internal_version", "size_bytes", "sha256")
    if any(
        not isinstance(payload.get(key), str) or not str(payload[key]).strip()
        for key in ("artifact_path", "source_identity", "version", "internal_version", "sha256")
    ):
        return ReleaseDeliveryCheck(False, "release-manifest-fields-missing", str(manifest_path))
    if not isinstance(payload.get("size_bytes"), int) or payload["size_bytes"] < 0:
        return ReleaseDeliveryCheck(False, "release-manifest-size-invalid", str(manifest_path))
    if payload["internal_version"] != payload["version"]:
        return ReleaseDeliveryCheck(False, "release-version-mismatch", str(manifest_path))
    if len(payload["sha256"]) != 64 or any(c not in "0123456789abcdefABCDEF" for c in payload["sha256"]):
        return ReleaseDeliveryCheck(False, "release-manifest-sha256-invalid", str(manifest_path))
    if payload.get("integrity_checked") is not True or payload.get("install_structure_checked") is not True:
        return ReleaseDeliveryCheck(False, "release-manifest-verification-missing", str(manifest_path))
    if not isinstance(payload.get("validations"), list) or not payload["validations"]:
        return ReleaseDeliveryCheck(False, "release-manifest-validations-missing", str(manifest_path))

    artifact = Path(str(payload["artifact_path"]))
    if not artifact.is_absolute():
        artifact = manifest_path.parent / artifact
    if not artifact.is_file():
        return ReleaseDeliveryCheck(False, "release-artifact-missing", str(manifest_path), str(artifact))
    if artifact.suffix.casefold() == ".zip":
        try:
            with zipfile.ZipFile(artifact) as archive:
                if archive.testzip() is not None:
                    return ReleaseDeliveryCheck(False, "release-artifact-integrity-invalid", str(manifest_path), str(artifact))
                if any(
                    name.startswith("/") or ".." in Path(name).parts
                    for name in archive.namelist()
                ):
                    return ReleaseDeliveryCheck(False, "release-artifact-structure-invalid", str(manifest_path), str(artifact))
        except (OSError, zipfile.BadZipFile):
            return ReleaseDeliveryCheck(False, "release-artifact-integrity-invalid", str(manifest_path), str(artifact))
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if artifact.stat().st_size != payload["size_bytes"] or digest.lower() != payload["sha256"].lower():
        return ReleaseDeliveryCheck(False, "release-artifact-integrity-mismatch", str(manifest_path), str(artifact))

    report_value = payload.get("report_path")
    report: Path | None = None
    if require_report:
        if not isinstance(report_value, str) or not report_value.strip():
            return ReleaseDeliveryCheck(False, "release-report-required", str(manifest_path), str(artifact))
        report = Path(report_value)
        if not report.is_absolute():
            report = manifest_path.parent / report
        if not report.is_file():
            return ReleaseDeliveryCheck(False, "release-report-missing", str(manifest_path), str(artifact), str(report))

    return ReleaseDeliveryCheck(True, "release-delivery-verified", str(manifest_path), str(artifact), str(report) if report else None, str(payload["version"]))
