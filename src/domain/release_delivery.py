from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


RELEASE_DELIVERY_SCHEMA_VERSION = 1
RELEASE_MANIFEST_MARKER = "ADAPTIVE_RELEASE_MANIFEST"
RELEASE_DELIVERY_MANIFEST_FIELDS = (
    "schema_version", "platform", "artifact_path", "report_path",
    "source_identity", "version", "internal_version", "version_source",
    "size_bytes", "sha256", "integrity_checked", "install_structure_checked",
    "validations", "publication",
)


def release_delivery_worker_directives() -> tuple[str, ...]:
    return (
        f"{RELEASE_MANIFEST_MARKER}: emit exactly one line with the absolute path to the final canonical delivery manifest.",
        "The delivery manifest is JSON schema version 1 and must include: "
        + ", ".join(RELEASE_DELIVERY_MANIFEST_FIELDS)
        + ". Its publication object must include canonical=true, atomic=true, "
        "historical_artifacts_preserved=true, release_identity, and staging_path.",
        "The manifest's version_source must identify an inspectable internal version. "
        "For WordPress use platform=wordpress and kind=wordpress-plugin-header; "
        "for other platforms use kind=zip-entry or file with path and regex pattern. "
        "Do not emit intermediate packages as the canonical artifact.",
    )


@dataclass(frozen=True)
class ReleaseDeliveryCheck:
    valid: bool
    reason: str
    manifest_path: str | None = None
    artifact_path: str | None = None
    report_path: str | None = None
    version: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None


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
        explicit = getattr(spec, "release_delivery", False) is True
        legacy_release_role = str(getattr(spec, "role", "")).casefold() in {
            "release", "packaging", "integration-release", "release-manager"
        }
        if explicit or (
            legacy_release_role
            and release_delivery_required(
            objective=objective, scope=scope, context=(*expected, *criteria), constraints=constraints
            )
        ):
            ids.add(str(getattr(spec, "id")))
    return frozenset(ids)


def release_delivery_required_for_checkpoint(
    checkpoint: dict, work_unit_id: str
) -> bool:
    plan = checkpoint.get("plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("work_units"), list):
        return False
    request = checkpoint.get("request")
    constraints = tuple(request.get("constraints", ())) if isinstance(request, dict) else ()
    for spec in plan["work_units"]:
        if not isinstance(spec, dict) or spec.get("id") != work_unit_id:
            continue
        if spec.get("release_delivery") is True:
            return True
        role = str(spec.get("role") or "").casefold()
        return role in {"release", "packaging", "integration-release", "release-manager"} and release_delivery_required(
            objective=str(spec.get("objective") or ""),
            scope=str(spec.get("scope") or ""),
            context=tuple(spec.get("expected_output", ())) + tuple(spec.get("acceptance_criteria", ())),
            constraints=constraints,
        )
    return False


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


def _internal_version(
    *, artifact: Path, manifest_path: Path, payload: dict
) -> tuple[str | None, str | None]:
    source = payload.get("version_source")
    if not isinstance(source, dict):
        return None, "release-version-source-missing"
    kind = str(source.get("kind") or "").strip().casefold()
    platform = str(payload.get("platform") or "generic").strip().casefold()
    if platform == "wordpress" and kind == "wordpress-plugin-header":
        try:
            with zipfile.ZipFile(artifact) as archive:
                versions: list[str] = []
                for name in archive.namelist():
                    if not name.casefold().endswith(".php"):
                        continue
                    text = archive.read(name).decode("utf-8", errors="replace")
                    if re.search(r"^\s*\**\s*Plugin Name\s*:", text, re.MULTILINE | re.IGNORECASE):
                        match = re.search(
                            r"^\s*\**\s*Version\s*:\s*([^\s*]+)",
                            text,
                            re.MULTILINE | re.IGNORECASE,
                        )
                        if match:
                            versions.append(match.group(1).strip())
                if len(set(versions)) != 1:
                    return None, "release-wordpress-version-unverifiable"
                return versions[0], None
        except (OSError, zipfile.BadZipFile):
            return None, "release-artifact-integrity-invalid"

    path_value = source.get("path")
    pattern = source.get("pattern")
    if kind not in {"zip-entry", "file"} or not isinstance(path_value, str) or not path_value.strip() or not isinstance(pattern, str) or not pattern:
        return None, "release-version-source-invalid"
    try:
        if artifact.suffix.casefold() == ".zip" and kind == "zip-entry":
            with zipfile.ZipFile(artifact) as archive:
                text = archive.read(path_value).decode("utf-8", errors="replace")
        else:
            source_path = Path(path_value)
            if not source_path.is_absolute():
                source_path = manifest_path.parent / source_path
            text = source_path.read_text(encoding="utf-8")
        match = re.search(pattern, text, re.MULTILINE)
    except (OSError, UnicodeError, KeyError, zipfile.BadZipFile, re.error):
        return None, "release-version-source-unreadable"
    if match is None or not match.groups():
        return None, "release-version-unmatched"
    return match.group(1).strip(), None


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
    publication = payload.get("publication")
    if (
        not isinstance(publication, dict)
        or publication.get("canonical") is not True
        or publication.get("atomic") is not True
        or publication.get("historical_artifacts_preserved") is not True
        or not isinstance(publication.get("release_identity"), str)
        or not publication["release_identity"].strip()
        or not isinstance(publication.get("staging_path"), str)
        or not publication["staging_path"].strip()
    ):
        return ReleaseDeliveryCheck(False, "release-publication-contract-invalid", str(manifest_path))
    if len(payload["sha256"]) != 64 or any(c not in "0123456789abcdefABCDEF" for c in payload["sha256"]):
        return ReleaseDeliveryCheck(False, "release-manifest-sha256-invalid", str(manifest_path))
    if payload.get("integrity_checked") is not True or payload.get("install_structure_checked") is not True:
        return ReleaseDeliveryCheck(False, "release-manifest-verification-missing", str(manifest_path))
    if not isinstance(payload.get("validations"), list) or not payload["validations"]:
        return ReleaseDeliveryCheck(False, "release-manifest-validations-missing", str(manifest_path))

    artifact = Path(str(payload["artifact_path"]))
    if not artifact.is_absolute():
        artifact = manifest_path.parent / artifact
    staging = Path(str(publication["staging_path"]))
    if not staging.is_absolute():
        staging = manifest_path.parent / staging
    if staging.resolve() == artifact.resolve():
        return ReleaseDeliveryCheck(False, "release-staging-is-canonical-artifact", str(manifest_path), str(artifact))
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
    internal_version, version_error = _internal_version(
        artifact=artifact, manifest_path=manifest_path, payload=payload
    )
    if version_error:
        return ReleaseDeliveryCheck(False, version_error, str(manifest_path), str(artifact))
    if internal_version != payload["version"]:
        return ReleaseDeliveryCheck(False, "release-version-mismatch", str(manifest_path), str(artifact))
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

    return ReleaseDeliveryCheck(
        True,
        "release-delivery-verified",
        str(manifest_path),
        str(artifact),
        str(report) if report else None,
        str(payload["version"]),
        artifact.stat().st_size,
        digest,
    )
