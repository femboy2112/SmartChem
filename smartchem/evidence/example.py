"""A worked, certifying reference manifest — the Mode-B authoring template.

An external project adopting the auditor faces one question first: *what does a
conformant, certifying manifest look like?*  This module answers it with a single
built-and-validated :class:`~smartchem.evidence.records.ProbeManifest`, deliberately
**not** fine-man-specific, that exercises every epistemic role a probe suite needs:

* a **CALIBRATION** — the instrument recovers a known result before its novel readings
  are believed;
* a **CLAIM** — the actual assertion, paired with a mutation and standing on two
  independent-provenance bearings;
* a **MUTATION** — the deliberately-broken variant that gives the claim teeth;
* a **SCOPE** — the explicit boundary of what the green check does *not* earn.

The ``verify-probes --example`` command serializes this value (via
:func:`~smartchem.evidence.manifest_io.manifest_to_mapping`) to stdout, so a consumer runs
``smartchem-verify-probes --example > my-probes.json``, edits the strings, and re-audits.
Because the template is built from typed records validated at construction and is asserted
to CERTIFY by the test-suite, the emitted starting point is guaranteed sound — never a
schema guess that has quietly rotted out of sync.
"""
from __future__ import annotations

from ..contracts import ClaimKind, EvidenceStatus
from .records import (
    MANIFEST_SCHEMA,
    EvidenceRecord,
    ProbeManifest,
    ProvenanceTag,
    Role,
    SourceLockedValue,
)

__all__ = ["example_manifest"]


def example_manifest() -> ProbeManifest:
    """Return a generic, schema-conformant manifest that CERTIFIES.

    The values are placeholders a real adopter replaces (the probe name, the cited
    sources, the numeric results); the *shape* is the reusable contract.  Every field is
    populated through the typed builders, so this is validated the moment it is built.
    """
    probe = "example_probe"
    calibration = EvidenceRecord.build(
        probe=probe,
        check="instrument_recovers_known_value",
        role=Role.CALIBRATION,
        claim_kind=ClaimKind.LITERAL,
        evidence_status=EvidenceStatus.CALIBRATED,
        passed=True,
        empirical_values=(
            SourceLockedValue(
                label="known_reference_value",
                value=0.25,
                source="reference:doi-or-arxiv-id",
            ),
        ),
        numeric_result={"recovered_within_tol": True, "tol": 1e-09},
    )
    claim = EvidenceRecord.build(
        probe=probe,
        check="primary_claim_agrees",
        role=Role.CLAIM,
        claim_kind=ClaimKind.ANALOGUE,
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
        passed=True,
        agreement=True,
        inputs=(
            ProvenanceTag(
                source="reference:doi-or-arxiv-id",
                derivation="the cited reference result",
            ),
            ProvenanceTag(
                source="independent:second-method",
                derivation="an independent second bearing on the same quantity",
            ),
        ),
        empirical_values=(
            SourceLockedValue(
                label="comparison_value",
                value=2.0,
                source="reference:second-doi-or-arxiv-id",
            ),
        ),
        scope_boundary="toy regime only; the regime this claim does NOT cover is named here",
        pairs_with=("broken_variant_must_fail",),
        numeric_result={"estimate": 2.0, "residual": 3e-07},
    )
    mutation = EvidenceRecord.build(
        probe=probe,
        check="broken_variant_must_fail",
        role=Role.MUTATION,
        claim_kind=ClaimKind.ANALOGUE,
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
        passed=True,
        numeric_result={"deliberately_broken_variant_behaves_as_required": True},
    )
    scope = EvidenceRecord.build(
        probe=probe,
        check="declared_scope",
        role=Role.SCOPE,
        claim_kind=ClaimKind.ANALOGUE,
        evidence_status=EvidenceStatus.STRUCTURAL_TOY,
        passed=True,
        scope_boundary="floor tier only; what the green check does NOT earn is named here",
    )
    return ProbeManifest(
        schema=MANIFEST_SCHEMA,
        program="example-project",
        claimed_tier="floor",
        floor_tier="floor",
        promoted_tier="legitimized",
        records=(calibration, claim, mutation, scope),
    )
