"""OPERATION XIII -- the 2.0 physical-simulation CLAIM-TIER vocabulary (the executable acceptance specification).

Section 1 of the XIII contract is explicit: a dynamical prediction MUST NOT collapse to one success boolean. Every
substantive quantity a physicalization deliverable produces carries an explicit evidential TIER, and a COMPOSITE
claim inherits the WEAKEST tier of its premises (section 13.B: "Conclusions inherit their weakest premise"). If a
model includes one unsourced gas-transfer parameter, the whole dynamic prediction cannot be called experimentally
validated merely because the equilibrium constants are sourced -- the weakest premise (the assumed parameter) caps
the claim.

These are load-bearing tokens -- a caller branches on them -- so they are exact, stable, uppercase strings in the
sandbox's existing SOURCED/DERIVED/UNKNOWN style. They are DISTINCT from the 0-D solver's verdict vocabulary
(`aqueous_equilibrium.VERDICTS`): a solver verdict answers "did the math close under this model?"; a claim tier
answers "what KIND of evidence backs this number?". A result can be SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL
(numerics closed) yet only NUMERICALLY_VERIFIED (no reference solver, no measurement) at the same time.

The ladder (weakest positive claim first):

    STRUCTURALLY_CONSERVING              the state obeys exact conservation / charge balance by construction; nothing
                                         is said about whether the numbers are accurate.
    NUMERICALLY_VERIFIED                 additionally cross-checked by an INDEPENDENT algorithm and/or precision
                                         (a second route, an arbitrary-precision holdout). Still only the SOLVE.
    BENCHMARKED_AGAINST_REFERENCE_SOLVER additionally compared to an external reference solver (PHREEQC/Reaktoro) on
                                         a shared constant lineage -- solver corroboration, NOT measured-chemistry
                                         validation (common-mode provenance; stated every time).
    CALIBRATED_TO_MEASUREMENT            a parameter was fit to an independent MEASURED dataset, fit/validation split
                                         preserved.
    PREDICTIVE_WITHIN_VALIDATED_DOMAIN   additionally predicts a FRESH measured holdout inside a stated domain.

Two sub-ladder floors carry NO positive claim:

    ASSUMED_PARAMETER                    a value supplied by the caller / assumed for a synthetic run, explicitly not
                                         sourced (e.g. a Level-A gas-transfer kLa). UNVERIFIED is its synonym.
    OUT_OF_DOMAIN                        a prediction requested outside its source/activity/numerical/kinetic
                                         applicability domain. REFUSED is its synonym -- a hard floor: no number is
                                         handed back as a prediction out here.
"""
from __future__ import annotations

# ------------------------------------------------------------------ the tokens (exact, stable, caller-branchable)
OUT_OF_DOMAIN = "OUT_OF_DOMAIN"
REFUSED = "REFUSED"                       # synonym of OUT_OF_DOMAIN at the hard floor
ASSUMED_PARAMETER = "ASSUMED_PARAMETER"
UNVERIFIED = "UNVERIFIED"                 # synonym of ASSUMED_PARAMETER
STRUCTURALLY_CONSERVING = "STRUCTURALLY_CONSERVING"
NUMERICALLY_VERIFIED = "NUMERICALLY_VERIFIED"
BENCHMARKED_AGAINST_REFERENCE_SOLVER = "BENCHMARKED_AGAINST_REFERENCE_SOLVER"
CALIBRATED_TO_MEASUREMENT = "CALIBRATED_TO_MEASUREMENT"
PREDICTIVE_WITHIN_VALIDATED_DOMAIN = "PREDICTIVE_WITHIN_VALIDATED_DOMAIN"

CLAIM_TIERS = frozenset({
    OUT_OF_DOMAIN, REFUSED, ASSUMED_PARAMETER, UNVERIFIED, STRUCTURALLY_CONSERVING,
    NUMERICALLY_VERIFIED, BENCHMARKED_AGAINST_REFERENCE_SOLVER, CALIBRATED_TO_MEASUREMENT,
    PREDICTIVE_WITHIN_VALIDATED_DOMAIN,
})

# RANK: higher == a stronger evidential claim.  The two floors share rank 0 (REFUSED/OUT_OF_DOMAIN: no claim) and
# rank 1 (ASSUMED/UNVERIFIED: a value, but no certification).  min-rank over premises implements weakest-premise.
TIER_RANK = {
    OUT_OF_DOMAIN: 0,
    REFUSED: 0,
    ASSUMED_PARAMETER: 1,
    UNVERIFIED: 1,
    STRUCTURALLY_CONSERVING: 2,
    NUMERICALLY_VERIFIED: 3,
    BENCHMARKED_AGAINST_REFERENCE_SOLVER: 4,
    CALIBRATED_TO_MEASUREMENT: 5,
    PREDICTIVE_WITHIN_VALIDATED_DOMAIN: 6,
}

# The canonical token reported at each rank when weakest-premise collapses several synonyms (floors report the
# hard-floor spelling; above the floors the token is unique per rank).
_CANONICAL_AT_RANK = {
    0: OUT_OF_DOMAIN,
    1: ASSUMED_PARAMETER,
    2: STRUCTURALLY_CONSERVING,
    3: NUMERICALLY_VERIFIED,
    4: BENCHMARKED_AGAINST_REFERENCE_SOLVER,
    5: CALIBRATED_TO_MEASUREMENT,
    6: PREDICTIVE_WITHIN_VALIDATED_DOMAIN,
}


class InvalidClaimTierError(ValueError):
    """Raised for an unknown claim-tier token -- a typo in a tier must fail loudly, never be read as a weak claim."""


def rank(tier: str) -> int:
    """The evidential rank of a tier token (higher is stronger).  Unknown tokens raise, never default to a value."""
    try:
        return TIER_RANK[tier]
    except KeyError:
        raise InvalidClaimTierError(
            f"{tier!r} is not a claim tier; expected one of {sorted(CLAIM_TIERS)}") from None


def weakest(*tiers: str) -> str:
    """The weakest-premise tier of a composite claim: the canonical token at the MINIMUM rank over its premises.
    With no premises this canonicalises to ASSUMED_PARAMETER (an empty basis asserts nothing certified -- the rank-1
    floor).  Section 13.B made executable: a dynamic prediction built from sourced constants (would-be BENCHMARKED)
    AND one assumed kLa (ASSUMED_PARAMETER) is ASSUMED_PARAMETER overall -- the assumption caps it."""
    if not tiers:
        return _CANONICAL_AT_RANK[1]
    lo = min(rank(t) for t in tiers)
    return _CANONICAL_AT_RANK[lo]


def is_at_least(tier: str, floor: str) -> bool:
    """True iff `tier` is at least as strong as `floor` (both must be valid tokens)."""
    return rank(tier) >= rank(floor)
