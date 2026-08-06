"""Mode B contract: load a probe manifest from JSON (the decoupled integration).

The JSON schema *is* the contract between an external project and this auditor —
neither repo imports the other.  Loading is strict and fail-closed: an unknown
role, a missing required field, a non-scalar empirical value, or a NaN/Infinity
anywhere raises :class:`ManifestError` rather than degrading silently.  A malformed
manifest is a refused audit, never a partial one.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from ..contracts import ClaimKind, EvidenceStatus
from .records import (
    MANIFEST_SCHEMA,
    EvidenceRecord,
    ProbeManifest,
    ProvenanceTag,
    Role,
    SourceLockedValue,
)

__all__ = ["ManifestError", "load_manifest", "load_manifest_dir", "manifest_from_mapping"]


class ManifestError(ValueError):
    """A manifest could not be parsed into a well-formed :class:`ProbeManifest`."""


def _reject_constant(token: str) -> float:  # pragma: no cover - exercised via loads
    raise ManifestError(f"manifest JSON must not contain non-finite constant {token!r}")


def _require(data: Mapping[str, object], key: str, where: str) -> object:
    if key not in data:
        raise ManifestError(f"{where} is missing required field {key!r}")
    return data[key]


def _as_mapping(value: object, where: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ManifestError(f"{where} must be a JSON object")
    return value


def _enum(enum_cls, value: object, where: str):
    if not isinstance(value, str):
        raise ManifestError(f"{where} must be a string")
    try:
        return enum_cls(value)
    except ValueError as error:
        allowed = ", ".join(member.value for member in enum_cls)
        raise ManifestError(f"{where} {value!r} is not one of: {allowed}") from error


def _provenance(value: object, where: str) -> ProvenanceTag:
    data = _as_mapping(value, where)
    source = _require(data, "source", where)
    if not isinstance(source, str):
        raise ManifestError(f"{where}.source must be a string")
    derivation = data.get("derivation", "")
    if not isinstance(derivation, str):
        raise ManifestError(f"{where}.derivation must be a string")
    try:
        return ProvenanceTag(source=source, derivation=derivation)
    except (TypeError, ValueError) as error:
        raise ManifestError(f"{where}: {error}") from error


def _source_locked(value: object, where: str) -> SourceLockedValue:
    data = _as_mapping(value, where)
    label = _require(data, "label", where)
    number = _require(data, "value", where)
    source = data.get("source", "")
    if isinstance(number, bool) or not isinstance(number, (int, float, str)):
        # bool excluded deliberately: a cited empirical value is a number or string.
        raise ManifestError(f"{where}.value must be a number or string")
    if not isinstance(source, str):
        raise ManifestError(f"{where}.source must be a string")
    try:
        return SourceLockedValue(label=label, value=number, source=source)
    except (TypeError, ValueError) as error:
        raise ManifestError(f"{where}: {error}") from error


def _record(value: object, index: int) -> EvidenceRecord:
    where = f"records[{index}]"
    data = _as_mapping(value, where)
    numeric_result = data.get("numeric_result", {})
    if not isinstance(numeric_result, Mapping):
        raise ManifestError(f"{where}.numeric_result must be a JSON object")
    pairs_with = data.get("pairs_with", [])
    if not isinstance(pairs_with, list) or any(not isinstance(n, str) for n in pairs_with):
        raise ManifestError(f"{where}.pairs_with must be a list of strings")
    inputs_raw = data.get("inputs", [])
    values_raw = data.get("empirical_values", [])
    if not isinstance(inputs_raw, list):
        raise ManifestError(f"{where}.inputs must be a list")
    if not isinstance(values_raw, list):
        raise ManifestError(f"{where}.empirical_values must be a list")
    try:
        return EvidenceRecord.build(
            probe=_require(data, "probe", where),
            check=_require(data, "check", where),
            role=_enum(Role, _require(data, "role", where), f"{where}.role"),
            claim_kind=_enum(
                ClaimKind, _require(data, "claim_kind", where), f"{where}.claim_kind"
            ),
            evidence_status=_enum(
                EvidenceStatus,
                _require(data, "evidence_status", where),
                f"{where}.evidence_status",
            ),
            passed=_bool(_require(data, "passed", where), f"{where}.passed"),
            inputs=tuple(
                _provenance(item, f"{where}.inputs[{i}]") for i, item in enumerate(inputs_raw)
            ),
            empirical_values=tuple(
                _source_locked(item, f"{where}.empirical_values[{i}]")
                for i, item in enumerate(values_raw)
            ),
            numeric_result=numeric_result,
            scope_boundary=data.get("scope_boundary", ""),
            pairs_with=tuple(pairs_with),
            agreement=_bool(data.get("agreement", False), f"{where}.agreement"),
            discriminator=_bool(data.get("discriminator", False), f"{where}.discriminator"),
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, ManifestError):
            raise
        raise ManifestError(f"{where}: {error}") from error


def _bool(value: object, where: str) -> bool:
    if type(value) is not bool:
        raise ManifestError(f"{where} must be a JSON boolean")
    return value


def manifest_from_mapping(data: Mapping[str, object]) -> ProbeManifest:
    """Build a :class:`ProbeManifest` from an already-parsed JSON mapping."""
    data = _as_mapping(data, "manifest")
    schema = _require(data, "schema", "manifest")
    if schema != MANIFEST_SCHEMA:
        raise ManifestError(
            f"manifest schema {schema!r} is not the expected {MANIFEST_SCHEMA!r}"
        )
    records_raw = _require(data, "records", "manifest")
    if not isinstance(records_raw, list):
        raise ManifestError("manifest.records must be a JSON list")
    records = tuple(_record(item, i) for i, item in enumerate(records_raw))
    try:
        return ProbeManifest(
            schema=schema,
            program=_require(data, "program", "manifest"),
            claimed_tier=_require(data, "claimed_tier", "manifest"),
            floor_tier=_require(data, "floor_tier", "manifest"),
            promoted_tier=_require(data, "promoted_tier", "manifest"),
            records=records,
        )
    except (TypeError, ValueError) as error:
        raise ManifestError(f"manifest: {error}") from error


def load_manifest(path: str | Path) -> ProbeManifest:
    """Load and validate one manifest JSON file, fail-closed on any malformation."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        # A missing/unreadable manifest is a load failure, not an internal crash:
        # surface it as a ManifestError so the CLI honours its documented exit-code
        # contract (2 = "could not be loaded"), symmetric with the JSON-decode guard below.
        raise ManifestError(f"{path}: cannot read manifest: {error}") from error
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as error:
        raise ManifestError(f"{path}: invalid JSON: {error}") from error
    return manifest_from_mapping(data)


def load_manifest_dir(path: str | Path) -> tuple[ProbeManifest, ...]:
    """Load every ``*.json`` manifest under a directory, sorted by filename."""
    directory = Path(path)
    if not directory.is_dir():
        raise ManifestError(f"{path} is not a directory")
    files = sorted(directory.glob("*.json"))
    if not files:
        raise ManifestError(f"{path} contains no *.json manifests")
    return tuple(load_manifest(file) for file in files)
