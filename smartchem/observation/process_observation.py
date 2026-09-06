"""ProcessObservationIR -- a read-only evidence-ingress layer (contract P1).

The durable, computational form of the poor-man ethos: *affordable chemistry is not a cheap
reagent list; it is a whole-path capability claim -- material identity, controllable operations,
measurement, containment, separation, verification and responsible closure all present or
explicitly blocked.*  See ``docs/research/PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md``.

A :class:`ProcessObservationIR` is an immutable *source-fragment* record: what one source actually
shows or states about ONE run, under ONE context, with explicit gaps.  It is **not** a procedure,
an instruction list, a safety clearance, or an authority to perform an operation.  This module is a
read-only sibling of the compiler (like :mod:`smartchem.evidence`): it reuses
:mod:`smartchem.contracts` digest primitives and reads :class:`ReactionDirection`, but it never
enters the closed executor registry, never mutates a compiler record, and is never imported back by
the compiler.

The non-negotiable invariants (contract sec. "Non-negotiable invariants"), enforced here in code:

1. **No Frankenprocedure.**  Claims from different ``run_context_id`` values stay separate
   fragments; :func:`merge_observations` REFUSES a cross-context splice (there is no merged
   operational bundle to hand back) -- only a reviewed transport bridge (P2) could license one.
2. **Direction is load-bearing.**  A fragment for a decomposition cannot fill an assembly record
   merely because an edge reverses; :func:`projection_gate` refuses on a direction mismatch first.
3. **Unknown stays unknown.**  Absent context fields default to ``None`` (an honest UNKNOWN); an
   UNKNOWN claim may carry no value; the capability bundles fail CLOSED to GAP, never a soft yes.
4. **Evidence never promotes by itself.**  This IR carries NO readiness/safety field -- it is
   structurally incapable of emitting SAFE / PROCEED_UNATTENDED or lifting a route's tier.
5. **Observables have scope.**  Every claim declares both what it supports AND what it does not
   establish; a rapid screen cannot silently become "identity confirmed".
6. **Evidence affects identity.**  Source fragment, scope, transport and claims all feed the
   identity digest, so a changed observation cannot masquerade as the same artifact.  The
   ``provenance_digest`` is a *computed* property, never a stored field -- a stored digest could be
   handed in inconsistent with the content and fail OPEN.
7. **No scalar truth score.**  Claim status, transport disposition, and the five bucket findings
   are independent enum axes; nothing collapses them to one number.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..contracts import Digestible
from ..decompiler_conditions import ReactionDirection
from ..provenance import SourceReview

__all__ = [
    "PROCESS_OBSERVATION_SCHEMA",
    "ClaimStatus",
    "ObservationPhase",
    "TransportDisposition",
    "SourceRole",
    "CapabilityBucket",
    "BucketStatus",
    "ProjectionDisposition",
    "SourceFragment",
    "ObservationClaim",
    "ContextScope",
    "Transport",
    "ProcessObservationIR",
    "BucketFinding",
    "ProjectionReadout",
    "FrankenprocedureError",
    "capability_bundle",
    "capability_hard_blockers",
    "operationally_complete",
    "merge_observations",
    "projection_gate",
]

PROCESS_OBSERVATION_SCHEMA = "smartchem.observation/process-observation-v1alpha1"


class ClaimStatus(str, Enum):
    """The *kind* of assertion a claim is -- a provenance axis, deliberately NOT a strength axis.

    This is orthogonal to :class:`smartchem.contracts.EvidenceStatus` (how strong the evidence is);
    conflating the two would violate invariant 7 (no scalar truth score).
    """

    OBSERVED = "OBSERVED"
    QUOTED = "QUOTED"
    DERIVED = "DERIVED"
    UNKNOWN = "UNKNOWN"


#: The three positive (non-UNKNOWN) claim kinds -- the only kinds a projection may ever license.
_POSITIVE_CLAIMS = frozenset({ClaimStatus.OBSERVED, ClaimStatus.QUOTED, ClaimStatus.DERIVED})


class ObservationPhase(str, Enum):
    """Classification only -- it makes an omitted stage visible; it is NOT an action sequence.

    A source can honestly say "ANALYSIS was observed, but the WASTE path is not documented" rather
    than letting a visual success masquerade as a complete route.
    """

    SETUP = "SETUP"
    CHARGE = "CHARGE"
    ADDITION = "ADDITION"
    REACTION = "REACTION"
    QUENCH = "QUENCH"
    WORKUP = "WORKUP"
    ISOLATION = "ISOLATION"
    PURIFICATION = "PURIFICATION"
    ANALYSIS = "ANALYSIS"
    WASTE = "WASTE"


#: Canonical stage order, used only to present a same-context view (never to synthesise a sequence).
_PHASE_ORDER = {p: i for i, p in enumerate(ObservationPhase)}


class TransportDisposition(str, Enum):
    """How well a fragment's context transports to a target context (fail-closed default UNKNOWN)."""

    EXACT = "EXACT"
    PARTIAL = "PARTIAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNKNOWN = "UNKNOWN"


class SourceRole(str, Enum):
    """The source family (from the contract's research source map).

    ``CREATOR`` material may appear as a demonstrated source record but -- until reviewer-accepted --
    cannot enter a validated corpus or bypass a capability gate (an acceptance probe).
    """

    CREATOR = "CREATOR"
    INSTITUTIONAL = "INSTITUTIONAL"
    REGULATORY = "REGULATORY"
    METROLOGY = "METROLOGY"
    UNKNOWN = "UNKNOWN"


class CapabilityBucket(str, Enum):
    """The five whole-path capability bundles (poor-man buckets, reframed)."""

    MATERIAL = "MATERIAL"
    CAPABILITY = "CAPABILITY"
    VERIFICATION = "VERIFICATION"
    CLOSURE = "CLOSURE"
    SCALE = "SCALE"


class BucketStatus(str, Enum):
    """Three-way bundle finding, mirroring :class:`ProcessFitStatus` (EXCLUDED/UNKNOWN/FITS).

    There is deliberately NO "CLEARED"/"SAFE" value: EVIDENCED means *this observation documents
    evidence for this bundle*, never *the bench is cleared* (the same discipline as
    :class:`smartchem.experiment.handling.CareLevel`, whose ``PROCEED_UNATTENDED`` is
    reserved-but-never-emitted).
    """

    EVIDENCED = "EVIDENCED"  # positively documented by the observation (like FITS)
    GAP = "GAP"  # not documented -> honest UNKNOWN (like a process gap); the fail-closed default
    BLOCKED = "BLOCKED"  # a known contradiction / missing engineered control (like EXCLUDED)


class ProjectionDisposition(str, Enum):
    """Whether a one-way projection into a compiler record WOULD be licensed (fail-closed).

    This is a read-only READOUT (P1); it never performs the enrichment (that needs the reviewed
    transport bridge of P2).  Every value but ``LICENSED_*`` is a refusal.
    """

    LICENSED_EXACT = "LICENSED_EXACT"
    LICENSED_PARTIAL = "LICENSED_PARTIAL"
    REFUSED_DIRECTION = "REFUSED_DIRECTION"
    REFUSED_IDENTITY = "REFUSED_IDENTITY"
    REFUSED_UNREVIEWED = "REFUSED_UNREVIEWED"
    REFUSED_TRANSPORT = "REFUSED_TRANSPORT"


@dataclass(frozen=True)
class SourceFragment(Digestible):
    """One immutable source locator + review state + optional context fixings.

    An ACCEPTED review must name a reviewer (a *who*): acceptance without attribution is refused, a
    fail-closed strengthening of the existing binary :class:`SourceReview`.
    """

    locator: str
    source_role: SourceRole
    review: SourceReview = SourceReview.UNREVIEWED
    publication_or_capture_date: str | None = None
    source_version_or_content_digest: str | None = None
    quote_or_timecode: str | None = None
    reviewer: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.locator, str) or not self.locator.strip():
            raise ValueError("a source fragment needs a non-empty locator")
        object.__setattr__(self, "locator", self.locator.strip())
        if not isinstance(self.source_role, SourceRole):
            raise TypeError("source_role must be a SourceRole")
        if not isinstance(self.review, SourceReview):
            raise TypeError("review must be a SourceReview")
        for name in (
            "publication_or_capture_date",
            "source_version_or_content_digest",
            "quote_or_timecode",
            "reviewer",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be a non-empty string when present (else omit it)")
            if isinstance(value, str):
                object.__setattr__(self, name, value.strip())
        if self.review is SourceReview.ACCEPTED and not self.reviewer:
            raise ValueError(
                "an ACCEPTED source fragment must name a reviewer -- acceptance without attribution "
                "is refused (fail-closed)"
            )

    @property
    def accepted(self) -> bool:
        """Reviewer-accepted AND attributed: the only state a projection may treat as reviewed."""
        return self.review is SourceReview.ACCEPTED and bool(self.reviewer)


@dataclass(frozen=True)
class ObservationClaim(Digestible):
    """One scoped claim.  Invariant 5: it declares BOTH what it supports and what it does not.

    Invariant 3: an UNKNOWN claim may carry no value_and_unit -- unknown stays unknown, it cannot
    smuggle a positive number under an UNKNOWN status.
    """

    status: ClaimStatus
    subject: str
    what_it_supports: str
    what_it_does_not_establish: str
    value_and_unit: str | None = None
    uncertainty_or_resolution: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ClaimStatus):
            raise TypeError("status must be a ClaimStatus")
        for name in ("subject", "what_it_supports", "what_it_does_not_establish"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"a claim needs a non-empty {name} (invariant 5: observables have scope)")
            object.__setattr__(self, name, value.strip())
        for name in ("value_and_unit", "uncertainty_or_resolution"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be a non-empty string when present (else omit it)")
            if isinstance(value, str):
                object.__setattr__(self, name, value.strip())
        if self.status is ClaimStatus.UNKNOWN and self.value_and_unit is not None:
            raise ValueError(
                "an UNKNOWN claim cannot carry a value_and_unit (invariant 3: unknown stays unknown)"
            )

    @property
    def is_positive(self) -> bool:
        """OBSERVED / QUOTED / DERIVED -- the only claim kinds a projection may license."""
        return self.status in _POSITIVE_CLAIMS


@dataclass(frozen=True)
class ContextScope(Digestible):
    """The run's declared context.  Every field is optional; an absent field is an honest UNKNOWN
    (invariant 3), never inferred into a positive."""

    material_identity_and_assay: str | None = None
    scale_and_geometry: str | None = None
    apparatus_capabilities: str | None = None
    medium_and_atmosphere: str | None = None
    controlled_intervals: str | None = None

    def __post_init__(self) -> None:
        for f in (
            "material_identity_and_assay",
            "scale_and_geometry",
            "apparatus_capabilities",
            "medium_and_atmosphere",
            "controlled_intervals",
        ):
            value = getattr(self, f)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{f} must be a non-empty string when present (else leave it UNKNOWN)")
            if isinstance(value, str):
                object.__setattr__(self, f, value.strip())


@dataclass(frozen=True)
class Transport(Digestible):
    """How a fragment's context transports.  Fail-closed default: UNKNOWN with no bridge.

    An EXACT transport carries no mismatch; a PARTIAL transport MUST name a reviewed bridge (only a
    reviewed bridge explicitly licenses a specific field); an OUT_OF_SCOPE transport must say why.
    """

    disposition: TransportDisposition = TransportDisposition.UNKNOWN
    mismatches: tuple[str, ...] = ()
    reviewed_bridge_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, TransportDisposition):
            raise TypeError("disposition must be a TransportDisposition")
        if type(self.mismatches) is not tuple or any(
            not isinstance(m, str) or not m.strip() for m in self.mismatches
        ):
            raise TypeError("mismatches must be a tuple of non-empty strings")
        object.__setattr__(self, "mismatches", tuple(sorted({m.strip() for m in self.mismatches})))
        if self.reviewed_bridge_id is not None and (
            not isinstance(self.reviewed_bridge_id, str) or not self.reviewed_bridge_id.strip()
        ):
            raise ValueError("reviewed_bridge_id must be a non-empty string when present")
        if isinstance(self.reviewed_bridge_id, str):
            object.__setattr__(self, "reviewed_bridge_id", self.reviewed_bridge_id.strip())
        if self.disposition is TransportDisposition.EXACT and self.mismatches:
            raise ValueError("an EXACT transport cannot list mismatches")
        if self.disposition is TransportDisposition.PARTIAL and not self.reviewed_bridge_id:
            raise ValueError(
                "a PARTIAL transport must name a reviewed_bridge_id -- only a reviewed bridge "
                "licenses a specific field (contract sec. 'One-way projection')"
            )
        if self.disposition is TransportDisposition.OUT_OF_SCOPE and not self.mismatches:
            raise ValueError("an OUT_OF_SCOPE transport must name at least one mismatch")


@dataclass(frozen=True)
class ProcessObservationIR(Digestible):
    """An immutable source-fragment record for ONE run under ONE context, with explicit gaps.

    ``reaction_identity`` is the *structural* identity of the reaction the fragment documents (the
    caller passes the resonance-identity key, not a formula signature) -- the strong match, so a
    same-formula isomer's fragment cannot pass an identity check the compiler's own
    ``assembly_conditions`` cascade would refuse.  Carries NO readiness or safety field by design
    (invariant 4): it structurally cannot promote a route.
    """

    observation_id: str
    reaction_identity: str
    reaction_direction: ReactionDirection
    run_context_id: str
    phase: ObservationPhase
    source_fragment: SourceFragment
    claims: tuple[ObservationClaim, ...] = ()
    context_scope: ContextScope = field(default_factory=ContextScope)
    transport: Transport = field(default_factory=Transport)
    explicit_unknowns: tuple[str, ...] = ()
    schema_version: str = PROCESS_OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PROCESS_OBSERVATION_SCHEMA:
            raise ValueError(
                f"unknown ProcessObservationIR schema {self.schema_version!r}; expected {PROCESS_OBSERVATION_SCHEMA!r}"
            )
        for name in ("observation_id", "reaction_identity", "run_context_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"a process observation needs a non-empty {name}")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.reaction_direction, ReactionDirection):
            raise TypeError("reaction_direction must be a ReactionDirection")
        if not isinstance(self.phase, ObservationPhase):
            raise TypeError("phase must be an ObservationPhase")
        if type(self.source_fragment) is not SourceFragment:
            raise TypeError("source_fragment must be a SourceFragment")
        if type(self.claims) is not tuple or any(type(c) is not ObservationClaim for c in self.claims):
            raise TypeError("claims must be a tuple of ObservationClaim")
        # Sort claims by content digest: reordering the SAME claims is not a change (stable identity),
        # but adding/removing/mutating any claim moves the digest (invariant 6).
        object.__setattr__(self, "claims", tuple(sorted(self.claims, key=lambda c: c.digest)))
        if type(self.context_scope) is not ContextScope:
            raise TypeError("context_scope must be a ContextScope")
        if type(self.transport) is not Transport:
            raise TypeError("transport must be a Transport")
        if type(self.explicit_unknowns) is not tuple or any(
            not isinstance(u, str) or not u.strip() for u in self.explicit_unknowns
        ):
            raise TypeError("explicit_unknowns must be a tuple of non-empty strings")
        object.__setattr__(self, "explicit_unknowns", tuple(sorted({u.strip() for u in self.explicit_unknowns})))

    @property
    def provenance_digest(self) -> str:
        """Invariant 6: the identity digest over ALL compare-visible fields (source fragment, scope,
        transport, claims).  Computed, NEVER stored -- a stored digest could be handed in
        inconsistent with the content and fail OPEN (see ``EvidenceRecord.__post_init__``)."""
        return self.digest


# --------------------------------------------------------------------------------------------------
# Capability bundles -- whole-path planning findings over ONE observation (contract P1).
# --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class BucketFinding(Digestible):
    """One whole-path capability finding.  ``supporting_subjects`` is empty for GAP/BLOCKED."""

    bucket: CapabilityBucket
    status: BucketStatus
    detail: str
    supporting_subjects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.bucket, CapabilityBucket):
            raise TypeError("bucket must be a CapabilityBucket")
        if not isinstance(self.status, BucketStatus):
            raise TypeError("status must be a BucketStatus")
        if not isinstance(self.detail, str) or not self.detail.strip():
            raise ValueError("a bucket finding needs a non-empty detail")
        object.__setattr__(self, "detail", self.detail.strip())
        if type(self.supporting_subjects) is not tuple or any(
            not isinstance(s, str) or not s.strip() for s in self.supporting_subjects
        ):
            raise TypeError("supporting_subjects must be a tuple of non-empty strings")
        object.__setattr__(self, "supporting_subjects", tuple(sorted({s.strip() for s in self.supporting_subjects})))
        # A positive finding must cite what evidenced it; a non-positive one must not pretend to.
        if self.status is BucketStatus.EVIDENCED and not self.supporting_subjects:
            raise ValueError("an EVIDENCED finding must cite the claim/scope subjects that support it")
        if self.status is not BucketStatus.EVIDENCED and self.supporting_subjects:
            raise ValueError("only an EVIDENCED finding may cite supporting subjects")


def _match(text: str | None, keywords: frozenset[str]) -> bool:
    return bool(text) and any(k in text.casefold() for k in keywords)


#: Negation / absence cues.  A claim whose SUPPORTING text carries one of these does NOT grant an
#: EVIDENCED verdict -- a source honestly narrating a MISSING control ("no containment", "unverified
#: identity", "waste dumped with no treatment") must never be read as positive evidence FOR that
#: control (evil-morty fold: the old bare-substring ``_match`` counted "no containment" as containment
#: and inverted every safety verdict).  Fail-closed: an ambiguous or partly-negative claim yields a GAP,
#: never a false positive -- under-crediting a genuine positive ("no impurities") is the safe direction.
_NEGATION_CUES = frozenset({
    "no ", "not ", "n't", "without", "lack", "absent", "none", "missing", "failed",
    "unverified", "unknown", "unlabeled", "unlabelled", "untreated", "unreacted", "no treatment",
})


def _claim_supports(claim: "ObservationClaim", keywords: frozenset[str]) -> bool:
    """Does a claim POSITIVELY support a capability keyword?  It must match the keyword in its subject or
    what-it-supports text AND carry no negation/absence cue ANYWHERE in that combined text -- so a claim
    whose subject cleanly names a capability but whose body DENIES it (subject "containment", supports
    "there was NO containment") never counts as evidence FOR it (evil-morty fold: the veto scans the WHOLE
    support text, not one field, or a clean subject would smuggle a negated body past an OR).  Fail-closed:
    an ambiguous or partly-negative claim yields no support -- under-crediting a genuine positive is safe.
    Hazard DETECTION deliberately stays on the bare :func:`_match` (generous -- over-detecting a hazard is
    the safe direction); only EVIDENCE-granting uses this."""
    text = f"{claim.subject}\n{claim.what_it_supports}"
    return _match(text, keywords) and not _match(text, _NEGATION_CUES)


_MATERIAL_KW = frozenset({"material", "identity", "assay", "grade", "purity", "composition", "hydrate", "reagent"})
_CAPABILITY_KW = frozenset({"containment", "control", "separation", "measurement", "measure", "filtration",
                            "distillation", "temperature control", "pressure", "vent", "fume", "ventilation"})
_HAZARD_KW = frozenset({"toxic", "corrosive", "flammable", "explosive", "hazard", "off-gas", "offgas",
                        "chlorine", "bromine", "acid vapour", "acid vapor"})
_VERIFICATION_KW = frozenset({"acceptance", "endpoint", "observable", "verify", "verification", "assay",
                              "identity confirmed", "yield", "purity", "analysis", "spectrum", "melting point"})
_CALIBRATION_KW = frozenset({"calibration", "calibrated", "qc", "quality control", "standard", "reference"})
_CLOSURE_KW = frozenset({"waste", "disposal", "decontamination", "byproduct", "emission", "neutralise",
                         "neutralize", "quench", "closure", "review required"})
_REVIEW_KW = frozenset({"review required", "review_required", "permit", "regulated", "authorization", "authorisation"})
_SCALE_KW = frozenset({"scale", "geometry", "volume", "mass", "quantity"})


def capability_bundle(obs: ProcessObservationIR) -> tuple[BucketFinding, ...]:
    """Read-only whole-path capability findings over ONE observation (contract P1).

    Each of the five bundles asks whether THIS observation *documents* evidence for it, returning
    EVIDENCED / GAP / BLOCKED -- fail-closed: absence is a GAP (an honest UNKNOWN), never a soft yes,
    and it NEVER lifts a route's readiness (invariant 4).  A bundle is EVIDENCED only when a matching
    context-scope field is present AND a positive-status claim supports it -- so a generic apparatus
    NAME alone is a GAP, not a capability (the contract's forbidden equipment-name-equals-capability
    shortcut).  This makes omitted stages visible without inventing a bench model (that is P2).

    One observation covers one phase, so it typically EVIDENCES the bundles its phase/claims cover and
    GAPs the rest -- exactly the intended value ("analysis was observed, waste path undocumented").
    """
    positive = tuple(c for c in obs.claims if c.is_positive)
    scope = obs.context_scope
    hazard_present = (
        _match(scope.medium_and_atmosphere, _HAZARD_KW)
        or any(_match(c.subject, _HAZARD_KW) or _match(c.what_it_supports, _HAZARD_KW) for c in obs.claims)
    )
    findings: list[BucketFinding] = []

    def supporters(keywords: frozenset[str]) -> tuple[str, ...]:
        # negation-aware over the WHOLE support text (evil-morty fold): a claim whose body denies the
        # capability ("no containment") never grants it, even when its subject names the capability cleanly.
        return tuple(c.subject for c in positive if _claim_supports(c, keywords))

    # MATERIAL -----------------------------------------------------------------------------------
    mat = supporters(_MATERIAL_KW)
    if scope.material_identity_and_assay and mat:
        findings.append(BucketFinding(CapabilityBucket.MATERIAL, BucketStatus.EVIDENCED,
                                      "material identity/assay documented and supported by a claim", mat))
    else:
        findings.append(BucketFinding(CapabilityBucket.MATERIAL, BucketStatus.GAP,
                                      "material identity/assay not evidenced (scope or supporting claim absent)"))

    # CAPABILITY ---------------------------------------------------------------------------------
    cap = supporters(_CAPABILITY_KW)
    if hazard_present and not cap:
        findings.append(BucketFinding(CapabilityBucket.CAPABILITY, BucketStatus.BLOCKED,
                                      "a hazard is present but no containment/control/separation/measurement "
                                      "capability is evidenced (an apparatus name is not a capability)"))
    elif scope.apparatus_capabilities and cap:
        findings.append(BucketFinding(CapabilityBucket.CAPABILITY, BucketStatus.EVIDENCED,
                                      "a specific capability function is documented and supported by a claim", cap))
    else:
        findings.append(BucketFinding(CapabilityBucket.CAPABILITY, BucketStatus.GAP,
                                      "no qualified capability evidenced (a generic apparatus name is not a capability)"))

    # VERIFICATION -------------------------------------------------------------------------------
    # Fail-closed (evil-morty fold): a NUMERIC conclusion is UNVERIFIED unless calibration/QC is
    # POSITIVELY evidenced.  The old check blocked only an EXPLICITLY-flagged unknown calibration, so a
    # SILENTLY-omitted one (the overwhelmingly common case) fell through to EVIDENCED -- the contract's
    # probe requires a missing OR stale OR failed record to downgrade to UNVERIFIED, all of which land in
    # BLOCKED here because none of them produces a positive calibration claim.
    ver = supporters(_VERIFICATION_KW)
    numeric_subjects = tuple(c.subject for c in positive if c.value_and_unit)
    calibration_support = supporters(_CALIBRATION_KW)
    if numeric_subjects:
        if calibration_support:
            findings.append(BucketFinding(CapabilityBucket.VERIFICATION, BucketStatus.EVIDENCED,
                                          "a numeric conclusion backed by positive calibration/QC evidence",
                                          tuple(sorted(set(numeric_subjects + calibration_support)))))
        else:
            findings.append(BucketFinding(CapabilityBucket.VERIFICATION, BucketStatus.BLOCKED,
                                          "a numeric conclusion rests on missing/unverified calibration/QC -> UNVERIFIED"))
    elif ver:
        findings.append(BucketFinding(CapabilityBucket.VERIFICATION, BucketStatus.EVIDENCED,
                                      "a qualitative acceptance/observable claim with declared limits is documented", ver))
    else:
        findings.append(BucketFinding(CapabilityBucket.VERIFICATION, BucketStatus.GAP,
                                      "no evidence-backed acceptance/observable documented"))

    # CLOSURE ------------------------------------------------------------------------------------
    review_required = any(_match(c.subject, _REVIEW_KW) or _match(c.what_it_supports, _REVIEW_KW) for c in obs.claims) \
        or any(_match(u, _REVIEW_KW) for u in obs.explicit_unknowns)
    clo = supporters(_CLOSURE_KW)
    if review_required:
        findings.append(BucketFinding(CapabilityBucket.CLOSURE, BucketStatus.BLOCKED,
                                      "a review/permit dependency is named: REVIEW_REQUIRED"))
    elif (obs.phase is ObservationPhase.WASTE and clo) or clo:
        findings.append(BucketFinding(CapabilityBucket.CLOSURE, BucketStatus.EVIDENCED,
                                      "byproduct/emission/waste/decontamination closure documented", clo))
    else:
        findings.append(BucketFinding(CapabilityBucket.CLOSURE, BucketStatus.GAP,
                                      "closure (waste/emissions/decontamination) not documented"))

    # SCALE --------------------------------------------------------------------------------------
    scale_mismatch = any(_match(m, _SCALE_KW) for m in obs.transport.mismatches) or (
        obs.transport.disposition is TransportDisposition.OUT_OF_SCOPE
    )
    if scope.scale_and_geometry and scale_mismatch:
        findings.append(BucketFinding(CapabilityBucket.SCALE, BucketStatus.BLOCKED,
                                      "declared scale/geometry falls outside the source's validated envelope: "
                                      "SCALE_UNVALIDATED"))
    elif scope.scale_and_geometry:
        findings.append(BucketFinding(CapabilityBucket.SCALE, BucketStatus.EVIDENCED,
                                      "scale/geometry documented within the source envelope",
                                      ("scale_and_geometry",)))
    else:
        findings.append(BucketFinding(CapabilityBucket.SCALE, BucketStatus.GAP,
                                      "scale/geometry not documented"))

    return tuple(findings)


def capability_hard_blockers(findings: tuple[BucketFinding, ...]) -> tuple[str, ...]:
    """The BLOCKED findings, rendered as hard-blocker strings.

    These speak the SAME currency as :attr:`smartchem.experiment.affordability.CostVector.hard_blockers`,
    which dominates any price in ``dominates()``.  So a route cheap in reagents but capability-BLOCKED
    is not poor-man-preferred -- a hard blocker outranks cash.  This *maps* a finding to that
    vocabulary; it does not wire into the live compile path (that is P2).
    """
    return tuple(sorted(
        f"{f.bucket.value}_{f.status.value}: {f.detail}"
        for f in findings
        if f.status is BucketStatus.BLOCKED
    ))


def operationally_complete(findings: tuple[BucketFinding, ...]) -> bool:
    """A route cannot be marked operationally complete unless the CLOSURE bundle is EVIDENCED.

    Fail-closed (an acceptance probe: delete the waste/decontamination record -> not complete).
    """
    return any(
        f.bucket is CapabilityBucket.CLOSURE and f.status is BucketStatus.EVIDENCED
        for f in findings
    )


# --------------------------------------------------------------------------------------------------
# No-Frankenprocedure merge (invariant 1) + one-way projection readout (invariants 1 & 2).
# --------------------------------------------------------------------------------------------------

class FrankenprocedureError(ValueError):
    """Raised when observations from different run contexts are combined without a reviewed bridge."""


def merge_observations(observations: tuple[ProcessObservationIR, ...]) -> tuple[ProcessObservationIR, ...]:
    """Return a phase-ordered *view* of fragments that share ONE run context.

    Invariant 1 (no Frankenprocedure): fragments from different ``run_context_id`` values cannot be
    combined into one operational bundle -- this REFUSES the cross-context splice outright (there is
    no merged bundle object to hand back); only a reviewed transport bridge (P2) could license it.
    Within a single context it returns the fragments sorted by canonical phase order -- a view, never
    a synthesised procedure (the phases stay separate records).
    """
    obs = tuple(observations)
    if not obs:
        raise ValueError("no observations to merge")
    if any(type(o) is not ProcessObservationIR for o in obs):
        raise TypeError("merge_observations takes ProcessObservationIR values")
    contexts = {o.run_context_id for o in obs}
    if len(contexts) != 1:
        raise FrankenprocedureError(
            f"cannot merge observations from different run contexts {sorted(contexts)} -- a "
            "cross-context splice needs a reviewed transport bridge (P2), not an inferred merge"
        )
    # evil-morty fold: run_context_id is a self-declared string; a shared label alone is not enough.
    # One run context is ONE reaction in ONE direction (fragments differ only by phase), so the fragments
    # must AGREE on reaction_identity and reaction_direction -- else two unrelated reactions (or a
    # decomposition + an assembly) would splice into one bundle under a forged shared label, bypassing
    # invariants 1 (no Frankenprocedure) and 2 (direction is load-bearing) from inside a single context.
    identities = {o.reaction_identity for o in obs}
    directions = {o.reaction_direction for o in obs}
    if len(identities) != 1 or len(directions) != 1:
        raise FrankenprocedureError(
            "observations sharing one run context must agree on reaction_identity and reaction_direction "
            f"(got identities {sorted(identities)}, directions {sorted(d.value for d in directions)}) -- "
            "differing fragments are separate runs, not one bundle"
        )
    return tuple(sorted(obs, key=lambda o: (_PHASE_ORDER[o.phase], o.observation_id)))


@dataclass(frozen=True)
class ProjectionReadout(Digestible):
    """A read-only readout of whether a one-way projection into a compiler record WOULD be licensed.

    ``licensed_fields`` names the positive claim subjects a projection would be allowed to fill; it is
    empty on any refusal, and never includes an UNKNOWN claim's subject (omitted facts stay omitted).
    """

    disposition: ProjectionDisposition
    reason: str
    licensed_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, ProjectionDisposition):
            raise TypeError("disposition must be a ProjectionDisposition")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("a projection readout needs a non-empty reason")
        object.__setattr__(self, "reason", self.reason.strip())
        if type(self.licensed_fields) is not tuple or any(
            not isinstance(s, str) or not s.strip() for s in self.licensed_fields
        ):
            raise TypeError("licensed_fields must be a tuple of non-empty strings")
        object.__setattr__(self, "licensed_fields", tuple(sorted({s.strip() for s in self.licensed_fields})))
        licensed = self.disposition in {ProjectionDisposition.LICENSED_EXACT, ProjectionDisposition.LICENSED_PARTIAL}
        if not licensed and self.licensed_fields:
            raise ValueError("only a LICENSED_* readout may name licensed fields")

    @property
    def licensed(self) -> bool:
        return self.disposition in {ProjectionDisposition.LICENSED_EXACT, ProjectionDisposition.LICENSED_PARTIAL}


def projection_gate(
    obs: ProcessObservationIR,
    *,
    target_identity: str,
    target_direction: ReactionDirection,
) -> ProjectionReadout:
    """Read-only readout of whether ``obs`` may enrich a target compiler record (invariants 1, 2, 5).

    Mirrors the compiler's own ``assembly_conditions`` cascade, refusing on the FIRST failing gate:

    1. **direction** -- ``obs.reaction_direction`` must equal ``target_direction`` (load-bearing: a
       decomposition fragment cannot fill an assembly record even though the edge reverses).
    2. **identity** -- ``obs.reaction_identity`` must equal the target's *structural* identity (the
       caller passes the resonance-identity key, so a same-formula isomer cannot pass).
    3. **review** -- the source fragment must be reviewer-accepted AND attributed (creator-video-only
       evidence, until reviewed, cannot bypass the gate).
    4. **transport** -- EXACT licenses directly; a PARTIAL with a reviewed bridge licenses the
       specific fields; OUT_OF_SCOPE / UNKNOWN is refused.

    On success ``licensed_fields`` names the POSITIVE claim subjects a projection could fill -- never
    an UNKNOWN claim's subject.  This NEVER mutates anything (P1 is read-only evidence-ingress).
    """
    if not isinstance(target_direction, ReactionDirection):
        raise TypeError("target_direction must be a ReactionDirection")
    if not isinstance(target_identity, str) or not target_identity.strip():
        raise ValueError("target_identity must be a non-empty structural identity key")
    target_identity = target_identity.strip()

    if obs.reaction_direction is not target_direction:
        return ProjectionReadout(
            ProjectionDisposition.REFUSED_DIRECTION,
            f"fragment direction {obs.reaction_direction.value} != target {target_direction.value} "
            "(direction is load-bearing)",
        )
    if obs.reaction_identity != target_identity:
        return ProjectionReadout(
            ProjectionDisposition.REFUSED_IDENTITY,
            "fragment reaction identity does not match the target's structural identity",
        )
    if not obs.source_fragment.accepted:
        return ProjectionReadout(
            ProjectionDisposition.REFUSED_UNREVIEWED,
            "source fragment is not reviewer-accepted-and-attributed (cannot bypass the gate)",
        )
    licensed = tuple(c.subject for c in obs.claims if c.is_positive)
    if obs.transport.disposition is TransportDisposition.EXACT:
        return ProjectionReadout(ProjectionDisposition.LICENSED_EXACT,
                                 "identity, direction and context match with EXACT transport", licensed)
    if obs.transport.disposition is TransportDisposition.PARTIAL and obs.transport.reviewed_bridge_id:
        return ProjectionReadout(ProjectionDisposition.LICENSED_PARTIAL,
                                 f"reviewed PARTIAL bridge {obs.transport.reviewed_bridge_id} licenses the "
                                 "specific fields", licensed)
    return ProjectionReadout(
        ProjectionDisposition.REFUSED_TRANSPORT,
        f"transport is {obs.transport.disposition.value} without a reviewed bridge",
    )
