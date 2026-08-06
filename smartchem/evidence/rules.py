"""The five auditor rules, each a pure function over a :class:`ProbeManifest`.

Each rule transplants one already-built SmartChem discipline and returns a
:class:`RuleResult`.  A rule never mutates the manifest and never re-executes a
probe — in the decoupled JSON contract it audits the *recorded* outcomes.  That
boundary is real and is printed on every certificate: the teeth verdict trusts the
recorded mutation outcome; a coupled (in-process) emitter that actually re-ran the
mutation would strengthen it.

Rule → discipline map:

* teeth                 ⇐ the DERIVED-MENU LAW (an option must be the image of a
                          declared invariant under a declared operation)
* provenance-independence ⇐ the independent-verifier / no-shared-code maxim
                          ("a check derived from its own subject checks nothing")
* source-lock           ⇐ refusal over an unearned answer (never fabricate a number)
* scope                 ⇐ casualty / omission lists on every certificate
* tier-boundary         ⇐ ClaimKind ⊥ EvidenceStatus (the governing invariant)
"""
from __future__ import annotations

from ..contracts import ClaimKind, EvidenceStatus
from .certificate import AuditOutcome, RuleResult
from .records import ProbeManifest, Role, evidence_rank

__all__ = [
    "RULES",
    "rule_provenance_independence",
    "rule_scope",
    "rule_source_lock",
    "rule_teeth",
    "rule_tier_boundary",
]


def _key(probe: str, check: str) -> str:
    return f"{probe}::{check}"


def _dedupe(items: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def rule_teeth(manifest: ProbeManifest) -> RuleResult:
    """Every CLAIM must be paired with a MUTATION that demonstrably breaks it.

    The §8 defense.  A CLAIM naming no mutation, or naming a mutation that is
    absent, mis-roled, or recorded as ``passed == False`` (the deliberately-broken
    variant did *not* break the claim — a generic identity), has no teeth → REFUSE.
    """
    index = {(r.probe, r.check): r for r in manifest.records}
    offending: list[str] = []
    details: list[str] = []
    for claim in manifest.claims():
        ck = _key(claim.probe, claim.check)
        if not claim.pairs_with:
            offending.append(ck)
            details.append(f"{ck}: CLAIM names no paired MUTATION (no teeth)")
            continue
        for name in claim.pairs_with:
            mutation = index.get((claim.probe, name))
            if mutation is None or mutation.role is not Role.MUTATION:
                offending.append(ck)
                details.append(
                    f"{ck}: paired mutation {name!r} is absent or not a MUTATION"
                )
            elif not mutation.passed:
                offending.append(ck)
                details.append(
                    f"{ck}: paired mutation {name!r} did not break the claim "
                    "(passed=False → no teeth)"
                )
    if offending:
        return RuleResult("teeth", AuditOutcome.REFUSE, "; ".join(details), _dedupe(offending))
    return RuleResult(
        "teeth",
        AuditOutcome.PASS,
        "every CLAIM is paired with a MUTATION recorded as demonstrating teeth",
    )


def rule_provenance_independence(manifest: ProbeManifest) -> RuleResult:
    """A CLAIM resting on <2 distinct provenance sources is policed by its strength.

    Shared (or single) provenance is possible common-mode: the "two sides" may be
    identities of the *same single input* and agree for any consistent input (the
    §8 generic identity).  The trigger is **structural**, not the self-declared
    ``agreement`` flag — a strong claim leaning on fewer than two independent
    bearings is a common-mode over-report even if it declines to call itself an
    agreement (that self-labelling dodge was a demonstrated bypass).

    * ≥2 distinct declared sources → satisfied.
    * <2 sources and evidence above structural-toy → REFUSE (single-bearing
      over-report; the §8 shape).
    * <2 sources, structural-toy, and an explicit ``agreement`` → FLAG if a scope
      boundary acknowledges the common mode, else REFUSE.
    * <2 sources, structural-toy, no agreement asserted → honestly weak, no action.

    Boundary: independence is checked over *declared* ``source`` tokens.  The auditor
    cannot detect two tokens that alias the same underlying root (an emitter honesty
    obligation); that is stated on the certificate banner.
    """
    offending: list[str] = []
    flagged: list[str] = []
    details: list[str] = []
    toy_rank = evidence_rank(EvidenceStatus.STRUCTURAL_TOY)
    for claim in manifest.claims():
        ck = _key(claim.probe, claim.check)
        sources = sorted({tag.source for tag in claim.inputs})
        if len(sources) >= 2:
            continue
        if evidence_rank(claim.evidence_status) > toy_rank:
            offending.append(ck)
            details.append(
                f"{ck}: CLAIM rests on {len(sources)} distinct provenance source "
                f"{sources} yet declares {claim.evidence_status.value} above "
                "structural-toy (single-bearing / common-mode over-report)"
            )
        elif not claim.agreement:
            continue
        elif not claim.scope_boundary.strip():
            offending.append(ck)
            details.append(
                f"{ck}: agreement CLAIM is common-mode {sources} and carries no "
                "scope_boundary acknowledging it"
            )
        else:
            flagged.append(ck)
            details.append(
                f"{ck}: agreement CLAIM is common-mode {sources}; honestly held at "
                "structural-toy with an acknowledging scope boundary"
            )
    if offending:
        return RuleResult(
            "provenance-independence",
            AuditOutcome.REFUSE,
            "; ".join(details),
            _dedupe(offending),
        )
    if flagged:
        return RuleResult(
            "provenance-independence",
            AuditOutcome.FLAG,
            "; ".join(details),
            _dedupe(flagged),
        )
    return RuleResult(
        "provenance-independence",
        AuditOutcome.PASS,
        "agreement claims draw on independent provenance (or none is asserted)",
    )


def rule_source_lock(manifest: ProbeManifest) -> RuleResult:
    """Every cited empirical/reference number must carry a non-empty source lock."""
    offending: list[str] = []
    details: list[str] = []
    for record in manifest.records:
        for value in record.empirical_values:
            if not value.is_locked:
                ck = _key(record.probe, record.check)
                offending.append(ck)
                details.append(f"{ck}: empirical value {value.label!r} has no source lock")
    if offending:
        return RuleResult(
            "source-lock", AuditOutcome.REFUSE, "; ".join(details), _dedupe(offending)
        )
    return RuleResult(
        "source-lock",
        AuditOutcome.PASS,
        "every cited empirical value is locked to a source token",
    )


def rule_scope(manifest: ProbeManifest) -> RuleResult:
    """Every CLAIM carries a scope boundary; every probe has ≥1 SCOPE record."""
    offending: list[str] = []
    details: list[str] = []
    for claim in manifest.claims():
        if not claim.scope_boundary.strip():
            ck = _key(claim.probe, claim.check)
            offending.append(ck)
            details.append(f"{ck}: CLAIM has no scope_boundary")
    probes_with_scope = {r.probe for r in manifest.records if r.role is Role.SCOPE}
    for probe in manifest.probes():
        if probe not in probes_with_scope:
            offending.append(f"{probe}::*")
            details.append(f"probe {probe!r} has no SCOPE record")
    if offending:
        return RuleResult(
            "scope", AuditOutcome.REFUSE, "; ".join(details), _dedupe(offending)
        )
    return RuleResult(
        "scope",
        AuditOutcome.PASS,
        "every CLAIM is scoped and every probe declares its boundary",
    )


def rule_tier_boundary(manifest: ProbeManifest) -> RuleResult:
    """A promoted tier requires a passed, literal, discriminator CLAIM.

    Generalizes fine-man's one governing boundary ("no green check outside a passed
    Milestone-4 discriminator may be reported as legitimized") to any two-level tier
    vocabulary: the floor tier is always honest; the promoted tier is gated on a
    ``role == CLAIM``, ``claim_kind == LITERAL``, ``discriminator``, ``passed`` record.
    """
    claimed = manifest.claimed_tier
    if claimed == manifest.floor_tier:
        return RuleResult(
            "tier-boundary",
            AuditOutcome.PASS,
            f"floor tier {claimed!r} requires no discriminator",
        )
    if claimed == manifest.promoted_tier:
        toy_rank = evidence_rank(EvidenceStatus.STRUCTURAL_TOY)
        discriminators = [
            r
            for r in manifest.records
            if r.role is Role.CLAIM
            and r.claim_kind is ClaimKind.LITERAL
            and r.discriminator
            and r.passed
            and evidence_rank(r.evidence_status) > toy_rank
        ]
        if discriminators:
            return RuleResult(
                "tier-boundary",
                AuditOutcome.PASS,
                f"promoted tier {claimed!r} is backed by passed literal discriminator "
                f"{discriminators[0].check!r}",
            )
        return RuleResult(
            "tier-boundary",
            AuditOutcome.REFUSE,
            f"manifest claims promoted tier {claimed!r} without a passed literal-claim "
            f"discriminator carrying evidence above structural-toy; the honest tier is "
            f"{manifest.floor_tier!r}",
            ("<manifest>",),
        )
    return RuleResult(
        "tier-boundary",
        AuditOutcome.REFUSE,
        f"claimed_tier {claimed!r} is neither the floor {manifest.floor_tier!r} nor "
        f"the promoted {manifest.promoted_tier!r} tier",
        ("<manifest>",),
    )


# Fixed evaluation order; the auditor runs all of them and never short-circuits, so
# a refused manifest still reports every rule's verdict.
RULES = (
    rule_teeth,
    rule_provenance_independence,
    rule_source_lock,
    rule_scope,
    rule_tier_boundary,
)
