"""Data model for the probe-evidence contract auditor.

This subpackage is a **decoupled sibling** of the SmartChem compiler, not a tenth
executor.  It reuses the shared, tamper-evident primitives from
:mod:`smartchem.contracts` (``ClaimKind``, ``EvidenceStatus``, ``Digestible``,
``canonical_digest``) but it never enters the closed executor registry and it
claims **no** SmartChem scientific authority.  Its job is to audit the *epistemic
contract* around an external project's numerical probes — teeth, provenance
independence, source locks, scope, and tier boundary — and either certify that
contract or refuse it.

Layering discipline (mirrors ``ClaimKind`` ⊥ ``EvidenceStatus``): the dataclasses
here validate **structure** (types present, required fields non-empty, canonical
form) and never enforce epistemic hygiene.  The *rules* in :mod:`.rules` enforce
hygiene.  A manifest must be able to *represent* an unlocked value or a toothless
claim so the auditor can catch it; structural validation that rejected those would
blind the auditor to exactly what it exists to find.

The vocabulary reused from ``contracts`` is used **descriptively** here.  A record
tagged ``EvidenceStatus.CALIBRATED`` records what the *probe author declared*; it
is not, and must never be read as, a SmartChem certificate — the SmartChem
approval/verifier seam does not run over an external manifest.  See :mod:`.auditor`
for the invariant that the auditor never *raises* a declared status.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from ..contracts import ClaimKind, Digestible, EvidenceStatus, canonical_digest

__all__ = [
    "MANIFEST_SCHEMA",
    "EvidenceRecord",
    "ProbeManifest",
    "ProvenanceTag",
    "Role",
    "SourceLockedValue",
    "evidence_rank",
]

MANIFEST_SCHEMA = "smartchem.evidence/probe-manifest-v1"


class Role(str, Enum):
    """The epistemic role a probe check plays; deliberately non-interchangeable."""

    CALIBRATION = "CALIBRATION"  # the instrument recovers a known result
    CLAIM = "CLAIM"  # the actual new assertion
    MUTATION = "MUTATION"  # a deliberately-broken variant that must fail (the teeth)
    SCOPE = "SCOPE"  # the explicit boundary of what the green check earns


# Strength ordering for EvidenceStatus, weakest (0) to strongest.  Kept explicit
# and total; :func:`evidence_rank` rejects any status missing from this map so a
# new EvidenceStatus member added to contracts forces a conscious update here
# rather than silently ranking as unknown.  This is the registry-completeness
# discipline applied to an enum.
_EVIDENCE_RANK: dict[EvidenceStatus, int] = {
    EvidenceStatus.UNSUPPORTED: 0,
    EvidenceStatus.STRUCTURAL_TOY: 1,
    EvidenceStatus.EXPERIMENTAL: 2,
    EvidenceStatus.CALIBRATED: 3,
    EvidenceStatus.VALIDATED_WITHIN_REGIME: 4,
    EvidenceStatus.ESTABLISHED: 5,
}


def evidence_rank(status: EvidenceStatus) -> int:
    """Return the total-order strength of ``status`` (higher = stronger)."""
    try:
        return _EVIDENCE_RANK[status]
    except KeyError as error:  # pragma: no cover - guarded by test_evidence_records
        raise KeyError(
            f"evidence rank is undefined for {status!r}; add it to _EVIDENCE_RANK"
        ) from error


def _require_nonempty_str(value: object, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _canonical_json(payload: Mapping[str, object]) -> str:
    """Serialize a numeric-result mapping to deterministic, canonical JSON text.

    Stored as text so the record is immutable, digest-stable, and portable to
    non-Python emitters (the manifest contract is JSON).  ``sort_keys`` makes two
    semantically-equal results serialize identically, so the record digest depends
    on the result's content, never on key order.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("numeric_result must be a JSON object (mapping)")
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True)
class ProvenanceTag(Digestible):
    """A declared provenance for one input feeding a check.

    ``source`` is the *root* provenance token (a conformal factor, an arXiv id, a
    measured dataset, a solver).  Two tags are **common-mode** iff they share a
    ``source``; the provenance-independence rule counts *distinct* sources, so a
    derivation of the same root never buys a second independent bearing.
    """

    source: str
    derivation: str = ""

    def __post_init__(self) -> None:
        _require_nonempty_str(self.source, "source")
        if not isinstance(self.derivation, str):
            raise TypeError("derivation must be a string")


@dataclass(frozen=True)
class SourceLockedValue(Digestible):
    """One cited empirical/reference number and the token it is locked to.

    ``source`` may be empty *structurally* — that is the exact defect the
    source-lock rule refuses.  If construction rejected an empty lock, the auditor
    could never be handed a manifest that fabricates a number, and the rule would
    be untestable.
    """

    label: str
    value: int | float | str | bool
    source: str = ""

    def __post_init__(self) -> None:
        _require_nonempty_str(self.label, "label")
        if not isinstance(self.value, (int, float, str, bool)):
            raise TypeError("value must be a JSON scalar (int, float, str, or bool)")
        if isinstance(self.value, float) and self.value != self.value:
            raise ValueError("value must not be NaN")
        if not isinstance(self.source, str):
            raise TypeError("source must be a string")

    @property
    def is_locked(self) -> bool:
        return bool(self.source.strip())


@dataclass(frozen=True)
class EvidenceRecord(Digestible):
    """The audited unit: one probe *check* and everything the auditor needs.

    Construct via :meth:`build` when you have a numeric-result mapping; the frozen
    field stores it as canonical JSON text.  Structural validation only — the five
    rules in :mod:`.rules` decide whether this record is epistemically sound.
    """

    probe: str
    check: str
    role: Role
    claim_kind: ClaimKind
    evidence_status: EvidenceStatus
    passed: bool
    inputs: tuple[ProvenanceTag, ...] = ()
    empirical_values: tuple[SourceLockedValue, ...] = ()
    numeric_result: str = "{}"
    scope_boundary: str = ""
    pairs_with: tuple[str, ...] = ()
    agreement: bool = False
    discriminator: bool = False

    def __post_init__(self) -> None:
        _require_nonempty_str(self.probe, "probe")
        _require_nonempty_str(self.check, "check")
        if not isinstance(self.role, Role):
            raise TypeError("role must be a Role")
        if not isinstance(self.claim_kind, ClaimKind):
            raise TypeError("claim_kind must be a ClaimKind")
        if not isinstance(self.evidence_status, EvidenceStatus):
            raise TypeError("evidence_status must be an EvidenceStatus")
        for flag in ("passed", "agreement", "discriminator"):
            if type(getattr(self, flag)) is not bool:
                raise TypeError(f"{flag} must be a boolean")
        if not isinstance(self.inputs, tuple) or any(
            type(tag) is not ProvenanceTag for tag in self.inputs
        ):
            raise TypeError("inputs must be a tuple of ProvenanceTag")
        if not isinstance(self.empirical_values, tuple) or any(
            type(value) is not SourceLockedValue for value in self.empirical_values
        ):
            raise TypeError("empirical_values must be a tuple of SourceLockedValue")
        if not isinstance(self.pairs_with, tuple) or any(
            not isinstance(name, str) or not name for name in self.pairs_with
        ):
            raise TypeError("pairs_with must be a tuple of non-empty strings")
        if not isinstance(self.scope_boundary, str):
            raise TypeError("scope_boundary must be a string")
        if not isinstance(self.numeric_result, str):
            raise TypeError("numeric_result must be canonical JSON text")
        try:
            parsed = json.loads(self.numeric_result)
        except json.JSONDecodeError as error:
            raise ValueError("numeric_result must be valid JSON") from error
        if not isinstance(parsed, dict):
            raise ValueError("numeric_result must encode a JSON object")
        # Canonicalize the stored text so the record's digest depends on the result's
        # CONTENT, never on incoming key order or spacing -- the invariant _canonical_json
        # documents.  build() already passes canonical text (this is then a no-op), and a
        # loaded manifest is canonical for the same reason; this closes the gap for the RAW
        # constructor, so a hand-set numeric_result cannot produce a record whose digest
        # disagrees with its own reload.  It makes manifest_to_mapping round-trip exactly for
        # every *constructible* record, not merely loader-produced ones.  (Adversarial probe,
        # 2026-08-07: the raw constructor previously admitted non-canonical text.)
        canonical = _canonical_json(parsed)
        if canonical != self.numeric_result:
            object.__setattr__(self, "numeric_result", canonical)
        # Structural coherence: agreement / discriminator / pairs_with are the
        # payload of a CLAIM.  A record cannot wear another role's immunity while
        # carrying a CLAIM's tell-tale fields (the role-laundering bypass), so a
        # non-CLAIM record bearing any of them is malformed and refused at
        # construction (fail-closed → ManifestError on load).
        if self.role is not Role.CLAIM:
            if self.agreement:
                raise ValueError(
                    "agreement=True is a CLAIM-only property; a non-CLAIM record "
                    "cannot assert an agreement"
                )
            if self.discriminator:
                raise ValueError(
                    "discriminator=True is a CLAIM-only property; only a literal "
                    "CLAIM can gate a promoted tier"
                )
            if self.pairs_with:
                raise ValueError(
                    "pairs_with is a CLAIM-only property; only a CLAIM pairs with a "
                    "MUTATION for teeth"
                )

    @classmethod
    def build(
        cls,
        *,
        probe: str,
        check: str,
        role: Role,
        claim_kind: ClaimKind,
        evidence_status: EvidenceStatus,
        passed: bool,
        inputs: tuple[ProvenanceTag, ...] = (),
        empirical_values: tuple[SourceLockedValue, ...] = (),
        numeric_result: Mapping[str, object] | None = None,
        scope_boundary: str = "",
        pairs_with: tuple[str, ...] = (),
        agreement: bool = False,
        discriminator: bool = False,
    ) -> "EvidenceRecord":
        """Build a record, canonicalizing ``numeric_result`` mapping to JSON text.

        This is a thin structural convenience (it encodes **no** rule logic), so it
        is safe for tests to use; the auditor's own rules are never invoked here.
        """
        return cls(
            probe=probe,
            check=check,
            role=role,
            claim_kind=claim_kind,
            evidence_status=evidence_status,
            passed=passed,
            inputs=tuple(inputs),
            empirical_values=tuple(empirical_values),
            numeric_result=_canonical_json(numeric_result or {}),
            scope_boundary=scope_boundary,
            pairs_with=tuple(pairs_with),
            agreement=agreement,
            discriminator=discriminator,
        )


@dataclass(frozen=True)
class ProbeManifest(Digestible):
    """A canonicalizable, digestible bundle of one probe run's evidence records.

    The tier vocabulary is **not** fine-man-specific: a manifest declares its own
    ``claimed_tier`` against a two-level gate (``floor_tier`` always honest;
    ``promoted_tier`` requires a passed literal discriminator).  Any project can
    reuse the auditor by naming its own floor/promoted tiers — that is the whole
    reusability contract.
    """

    schema: str
    program: str
    claimed_tier: str
    floor_tier: str
    promoted_tier: str
    records: tuple[EvidenceRecord, ...] = ()

    def __post_init__(self) -> None:
        _require_nonempty_str(self.schema, "schema")
        _require_nonempty_str(self.program, "program")
        _require_nonempty_str(self.claimed_tier, "claimed_tier")
        _require_nonempty_str(self.floor_tier, "floor_tier")
        _require_nonempty_str(self.promoted_tier, "promoted_tier")
        if self.floor_tier == self.promoted_tier:
            raise ValueError("floor_tier and promoted_tier must differ")
        if not isinstance(self.records, tuple) or any(
            type(record) is not EvidenceRecord for record in self.records
        ):
            raise TypeError("records must be a tuple of EvidenceRecord")
        keys = [(record.probe, record.check) for record in self.records]
        if len(keys) != len(set(keys)):
            raise ValueError(
                "records must have a unique (probe, check) identity; a duplicate "
                "would make mutation pairing and scope attribution ambiguous"
            )

    @property
    def digest(self) -> str:
        return canonical_digest(self)

    def probes(self) -> tuple[str, ...]:
        """Return the distinct probe names in declaration order (deduplicated)."""
        seen: dict[str, None] = {}
        for record in self.records:
            seen.setdefault(record.probe, None)
        return tuple(seen)

    def claims(self) -> tuple[EvidenceRecord, ...]:
        return tuple(r for r in self.records if r.role is Role.CLAIM)

    def by_check(self, name: str) -> EvidenceRecord | None:
        for record in self.records:
            if record.check == name:
                return record
        return None
