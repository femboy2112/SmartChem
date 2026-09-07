"""DURATION-STABILITY-01: a duration-aware survival verdict over SOURCED decomposition kinetics.

E1's shipped composability check is INSTANTANEOUS.  ``StabilityRef.survives_temperature``
(:mod:`smartchem.data.stability`) asks only whether an exposure temperature stays below a decomposition
ONSET; it is silent on how LONG an intermediate is held (ROUND 15 shipped only the DIAGNOSTIC half -- the
serial-hold minutes, an observation, never a verdict).  This module adds the time axis where -- and ONLY
where -- it can be done on KNOWN physics: given a compound whose FIRST-ORDER decomposition Arrhenius
``(Ea, A)`` is SOURCED (:mod:`smartchem.data.kinetics`), it reproduces the surviving fraction over a hold
by first-order decay ``f = exp(-k t)``, with ``k = A·exp(-Ea/RT)`` -- the SAME rate law
:mod:`smartchem.experiment.kinetics` uses -- and reads a duration-aware verdict off it.

Anti-fabrication (section 10.4), the load-bearing discipline.  A rate is used ONLY where it is SOURCED for
this exact compound, matched on CANONICAL STRUCTURE (never formula -- a same-formula isomer never borrows
another's rate), and ONLY as the sole reactant of a first-order record (a decomposition, not a formation:
direction matters).  Where no rate is sourced -- the common case; no paracetamol or DOW-bromine intermediate
has a sourced decomposition rate, and Br2 has none at all -- the verdict is a LOUD ``UNKNOWN``, never a
fabricated survival.  The decomposition kinetics table is deliberately tiny (calibration only): the one
compound this reproduces non-vacuously today is N2O5 (the classic first-order gas-phase decomposition,
whose measured k the engine already recovers to ~7%).

Boundaries, stated loudly.  (1) This is a STANDALONE primitive; it is NOT yet wired into
:func:`~smartchem.experiment.composability._judge_transition`'s COMPOSABLE/DEGENERATE flip -- that needs a
route intermediate that actually carries a sourced decomposition rate plus a unit-locked hold duration
(``ConditionEnvelope.duration`` now requires minutes; this primitive requires explicitly converted seconds).
The duration remains unconsumed by core E1. The DOW-Br2 payoff requires compatible kinetics: the recovered
Warshay NASA TN D-3502 primary measures collider-dependent initial dissociation, not the concentration-free
first-order hold law here (see ``docs/research/SOURCING_RECON_2026-09-07.md``).
(2) The verdict is a kinetic TENDENCY under the SOURCED Arrhenius fit (W3): never a claim about the real
process, its true rate, or which cleavage Nature takes.  (3) The 99%-/50%-remaining band edges are a
DECLARED interpretive policy (essentially-intact vs majority-destroyed, with an explicit grey band), stated
here, not hidden in a magic number.  (4) RATE-CONVENTION ASSUMPTION (evil-morty, a latent trap for a future
extender): the surviving fraction ``exp(-k t)`` assumes the sourced ``k`` is the PER-SPECIES rate
(``-d[A]/dt = k[A]``) -- which BOTH seeded records pin explicitly in their provenance.  The reactant
COEFFICIENT is not consulted (a first-order reactant's survival is coefficient-free under that convention);
a future record whose ``k`` were sourced under the REACTION-rate convention (half, for a ``2 A ->`` step)
would make the fraction off by the stoichiometric factor.  The module cannot detect the convention from the
data, so this is a documented boundary, not a silent guess (see the tracked debt in ROADMAP.md).  (5) The
"first-order" family here is first-order REACTANT CONSUMPTION -- a decomposition is the primary case, but a
first-order isomerization (cyclopropane -> propene) also consumes its reactant first-order, so it resolves
too; the physics of the surviving fraction is identical, only the fate of the consumed reactant differs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..contracts import Digestible, canonical_digest
from ..data.kinetics import DEFAULT_KINETICS, KineticRef, KineticTable
from ..smiles import parse_smiles

__all__ = [
    "STABILITY_HORIZON_SCHEMA",
    "GAS_CONSTANT_J_PER_MOL_K",
    "SurvivalVerdict",
    "StabilityHorizon",
    "decomposition_rate_for",
    "surviving_fraction",
    "survival_verdict",
    "stability_horizon",
]

STABILITY_HORIZON_SCHEMA = "smartchem.experiment.stability_horizon/duration-survival-v1"

#: Molar gas constant R, J/(mol K).  NIST CODATA 2018.  Restated here (rather than importing the L1 rate
#: engine, which would drag feasibility/ceiling/step) so this stays import-light; ``test_stability_horizon``
#: pins it equal to ``smartchem.experiment.kinetics.GAS_CONSTANT_J_PER_MOL_K`` so the two copies never drift.
GAS_CONSTANT_J_PER_MOL_K = 8.314462618
_LN10 = math.log(10.0)
#: 10**x overflows a float near x ~ 308; past this the surviving fraction is 0 (fully decomposed) with no inf.
_FLOAT_LOG_LIMIT = 300.0

#: The declared interpretive band edges on the surviving fraction over the hold (W3 tendency, not a real-
#: process claim): >= 99% remaining is essentially intact; <= 50% remaining is majority-destroyed; between
#: is a disclosed MARGINAL concern.  Stated, not a magic number buried in the verdict logic.
_INTACT_FRACTION = 0.99
_DEGENERATE_FRACTION = 0.50


class SurvivalVerdict(str, Enum):
    """The duration-aware stability verdict for a held intermediate (str-valued so it digests/serialises)."""

    SURVIVES = "SURVIVES"      # >= 99% remaining over the hold under the sourced Arrhenius fit
    MARGINAL = "MARGINAL"      # between 50% and 99% remaining -- a disclosed concern, neither clean nor dead
    DEGRADES = "DEGRADES"      # <= 50% remaining -- the intermediate is majority-destroyed over the hold
    UNKNOWN = "UNKNOWN"        # no sourced first-order decomposition rate for this compound -> fail-closed


def decomposition_rate_for(molecule, *, kinetics: KineticTable = DEFAULT_KINETICS) -> "KineticRef | None":
    """The SOURCED first-order decomposition rate for ``molecule``, or ``None`` (fail-closed) if none.

    Matches ONLY a record that is (a) first order (``s^-1``: a concentration-free decay), and (b) has
    ``molecule`` as its SOLE reactant species -- i.e. the compound consumed FIRST-ORDER (a decomposition is
    the primary case; a first-order isomerization consumes its reactant the same way and also resolves).
    Direction-specific: the molecule appearing as a PRODUCT, or as one of several reactants, does not answer
    its rate.  The match is on CANONICAL STRUCTURE (:func:`~smartchem.contracts.canonical_digest` of the
    molecule's canonical form), never the formula, so a same-formula isomer never inherits this rate."""
    target = canonical_digest(molecule.canonical())
    for rec in kinetics.records:
        if not rec.is_first_order:
            continue                                          # decay f = exp(-k t) is a FIRST-ORDER law only
        if len(rec.reactant_smiles) != 1:
            continue                                          # a single reactant species = a unimolecular decomposition
        smiles, _coeff = rec.reactant_smiles[0]
        if canonical_digest(parse_smiles(smiles).canonical()) == target:
            return rec
    return None


def surviving_fraction(rec: KineticRef, temperature_k: float, hold_seconds: float) -> float:
    """The fraction of ``rec``'s reactant surviving a ``hold_seconds`` hold at ``temperature_k`` by
    first-order decay ``exp(-k t)``, ``k = A·exp(-Ea/RT)``.  Robust to a huge ``k·t`` (returns 0.0, fully
    decomposed, never ``inf``).  Raises on a non-first-order record or a non-positive temperature/hold."""
    if not rec.is_first_order:
        raise ValueError("surviving_fraction models first-order decay only (a_units must be s^-1)")
    if temperature_k <= 0:
        raise ValueError("temperature must be a positive absolute temperature (K)")
    if hold_seconds <= 0:
        raise ValueError("hold_seconds must be a positive duration")
    if not (math.isfinite(rec.ea_kj_per_mol) and math.isfinite(rec.log10_a)):
        # the data layer accepts a non-finite (Ea, A) (no isfinite guard on KineticRef); fail closed here
        # rather than emit a silent NaN fraction (evil-morty).
        raise ValueError("the sourced Arrhenius parameters (Ea, log10 A) must be finite")
    log10_k = rec.log10_a - (rec.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * temperature_k * _LN10)
    log10_kt = log10_k + math.log10(hold_seconds)
    if log10_kt >= _FLOAT_LOG_LIMIT:
        return 0.0                                            # k*t astronomically large -> fully decomposed
    return math.exp(-(10.0 ** log10_kt))


def survival_verdict(fraction: float) -> SurvivalVerdict:
    """The band verdict for a surviving fraction: >= 99% SURVIVES, <= 50% DEGRADES, else MARGINAL.  The SINGLE
    source of the interpretive band edges, shared by the standalone horizon and E1's duration gate, so the two
    can never drift to different band policies (the recurring shared-term hazard)."""
    if fraction >= _INTACT_FRACTION:
        return SurvivalVerdict.SURVIVES
    if fraction <= _DEGENERATE_FRACTION:
        return SurvivalVerdict.DEGRADES
    return SurvivalVerdict.MARGINAL


@dataclass(frozen=True)
class StabilityHorizon(Digestible):
    """A duration-aware stability reading for one compound held ``hold_seconds`` at ``temperature_k``.

    ``fraction_remaining`` is the surviving fraction (``None`` when no rate is sourced -> ``verdict`` is
    ``UNKNOWN``, fail-closed).  ``grade`` is ``DERIVED`` when the temperature is inside the sourced Arrhenius
    fit window, ``PREDICTED`` when extrapolated outside it (flagged), ``UNKNOWN`` when no rate -- mirroring
    the L1 rate engine's grade.  ``is_sourced`` is COMPUTED from whether a rate was found, never a stored
    flag a caller could forge."""

    schema: str
    compound_digest: str
    temperature_k: float
    hold_seconds: float
    fraction_remaining: "float | None"
    verdict: SurvivalVerdict
    grade: str
    reason: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if self.schema != STABILITY_HORIZON_SCHEMA:
            raise ValueError(f"schema must be {STABILITY_HORIZON_SCHEMA!r}")
        if (self.fraction_remaining is None) is not (self.verdict is SurvivalVerdict.UNKNOWN):
            raise ValueError("fraction_remaining is None iff the verdict is UNKNOWN (fail-closed coherence)")
        if self.fraction_remaining is not None and not (0.0 <= self.fraction_remaining <= 1.0):
            raise ValueError("fraction_remaining must lie in [0, 1]")

    @property
    def is_sourced(self) -> bool:
        """True iff a fraction was computed from a matched rate (``fraction_remaining is not None``).

        COMPUTED from the reading, so it can never DISAGREE with the reading the way a separately-stored flag
        could (the R18 declarative-auditor lesson).  It is NOT a guard against a caller who hand-authors a
        wholly fabricated horizon -- that is the caller's own lie, not a value this module borrowed or
        vouches for; the ``stability_horizon`` factory is the only thing that promises a sourced reading."""
        return self.fraction_remaining is not None


def stability_horizon(
    molecule, temperature_k: float, hold_seconds: float, *, kinetics: KineticTable = DEFAULT_KINETICS
) -> StabilityHorizon:
    """The duration-aware stability verdict for ``molecule`` held ``hold_seconds`` at ``temperature_k``.

    Fail-closed: with no sourced first-order decomposition rate the verdict is ``UNKNOWN`` and
    ``fraction_remaining`` is ``None`` -- never a fabricated survival."""
    if temperature_k <= 0:
        raise ValueError("temperature must be a positive absolute temperature (K)")
    if hold_seconds <= 0:
        raise ValueError("hold_seconds must be a positive duration")
    digest = canonical_digest(molecule.canonical())
    rec = decomposition_rate_for(molecule, kinetics=kinetics)
    if rec is None:
        return StabilityHorizon(
            STABILITY_HORIZON_SCHEMA, digest, float(temperature_k), float(hold_seconds), None,
            SurvivalVerdict.UNKNOWN, "UNKNOWN",
            "UNKNOWN: no sourced first-order decomposition rate for this compound; a survival fraction is "
            "NEVER fabricated (section 10.4) -- inject a sourced KineticRef to close this gap",
        )
    fraction = surviving_fraction(rec, temperature_k, hold_seconds)
    verdict = survival_verdict(fraction)
    lo, hi = rec.temperature_range_k
    in_window = lo <= temperature_k <= hi
    grade = "DERIVED" if in_window else "PREDICTED"
    extrap = "" if in_window else (
        f" [PREDICTED: {temperature_k:.0f} K is outside the sourced fit window {lo:.0f}-{hi:.0f} K -- "
        f"extrapolated via constant Ea/A]"
    )
    reason = (
        f"{verdict.value}: {fraction * 100:.1f}% of the compound remains after {hold_seconds:g} s at "
        f"{temperature_k:.1f} K, by first-order consumption exp(-k t) with k = A·exp(-Ea/RT) over the SOURCED "
        f"Arrhenius fit of '{rec.name}' (Ea = {rec.ea_kj_per_mol:.1f} kJ/mol, log10 A = {rec.log10_a:.2f})"
        f"{extrap} -- a kinetic tendency under the sourced fit, NOT a claim about the real process or its "
        f"true rate (W3)"
    )
    return StabilityHorizon(
        STABILITY_HORIZON_SCHEMA, digest, float(temperature_k), float(hold_seconds), fraction, verdict,
        grade, reason,
    )
