"""L1 -- reaction kinetics: the Arrhenius rate constant ``k = A·exp(-Ea/RT)``, the RATE dimension.

The one outcome the epistemic grade deliberately never touches.  L2 grades a reaction's *footing* (KNOWN /
DERIVED / ...) -- whether it is a real, legitimate transformation -- and says nothing about *how fast* it goes.
But a KNOWN or DERIVED reaction can be kinetically FROZEN (diamond is thermodynamically favored to become
graphite and never does), and the compiler must be able to SAY so.  This module adds that: where a reaction's
Arrhenius parameters ``(Ea, A)`` are SOURCED, an ESTABLISHED model (the Arrhenius equation) reproduces its rate
constant ``k`` and reads off a rate regime; where they are not, the verdict is a LOUD ``UNKNOWN`` rate, never a
fabricated ``k``.  Reproducing known chemistry on sourced inputs, exactly as M1 reproduces ΔG -- here for the
rate instead of the free energy.

What this emits, and what it does NOT
-------------------------------------
* **k (the rate constant)** -- ``A·exp(-Ea/RT)`` at the reaction temperature, reported as ``log10 k`` too so an
  enormous pre-exponential never overflows a float into a fabricated ``inf`` (the same honesty M2 uses for K).
* **The rate REGIME** -- an assumption-light reading of ``k`` as a timescale, on the standard decade scale:
  ``FAST`` (half-life < 1 s) / ``MODERATE`` (< 1 hour) / ``SLOW`` (< 1 year) / ``FROZEN`` (>= 1 year: the
  "kinetically frozen" signal) / ``UNKNOWN`` (no sourced ``(Ea, A)``).  For a FIRST-ORDER reaction the half-life
  ``t½ = ln2/k`` is concentration-free and exact.  For a higher order the timescale needs a concentration, so
  the half-life is computed at a DECLARED 1 mol/L reference (an idealisation, stated loudly -- the same honesty
  M2 uses for the Δn!=0 conversion) rather than fabricated as if concentration-free.
* **The epistemic GRADE of the rate** -- ``DERIVED`` when the reaction temperature is INSIDE the sourced
  Arrhenius fit's validity window, ``PREDICTED`` when it is extrapolated outside it (flagged), mirroring M1.

Boundaries, stated loudly. (1) The rate dimension is ORTHOGONAL to and NEVER alters the epistemic grade: a
reaction stays KNOWN/DERIVED on its thermodynamic/attestation footing even when its rate regime is ``FROZEN``
or ``UNKNOWN``.  L2 gains the ability to say "known-but-kinetically-frozen"; it does not gain the ability to
predict a rate it has no source for.  (2) ``k`` is reproduced ONLY where ``(Ea, A)`` are SOURCED for this exact
(direction-specific) reaction; the engine never predicts a barrier, never decides which cleavage Nature takes,
and never ranks competing pathways by rate -- that forbidden new-physics selection is the permanent W3 wall.
Calibrated on a reaction whose measured rate the engine must recover before its novel outputs are believed.

Independence: the data is a SEPARATE sourced table (:mod:`smartchem.data.kinetics`), and the reaction is keyed
by :func:`~smartchem.experiment.ceiling._coefficient_vector` -- the same kernel-cross-checked balance
feasibility and the ceiling use -- so the rate lookup can never disagree with the stoichiometry.  The reaction
temperature is resolved by feasibility's :func:`~smartchem.experiment.feasibility._temperature_of`, so M1 and
L1 read the same temperature off a step.
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass
from enum import Enum

from ..contracts import Digestible, canonical_digest
from ..data.kinetics import DEFAULT_KINETICS, KineticRef, KineticTable
from ..evidence_key import ReactionEvidenceKey, phase_context
from ..smiles import parse_smiles
from .bucket import Bucket, Quantity, unknown
from .ceiling import _coefficient_vector
from .feasibility import _temperature_of
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "GAS_CONSTANT_J_PER_MOL_K",
    "RateRegime",
    "RateGrade",
    "StepKinetics",
    "RouteKinetics",
    "reaction_key_of",
    "reaction_evidence_key",
    "record_evidence_key",
    "kinetics_of_step",
    "verify_kinetics",
    "worst_regime",
]

#: The molar gas constant R (J/mol/K), CODATA -- the one constant k = A·exp(-Ea/RT) needs.
GAS_CONSTANT_J_PER_MOL_K = 8.314462618
_LN10 = math.log(10.0)
#: 10**x overflows a float near x ~ 308; past this we carry the order of magnitude instead of a number.
_FLOAT_LOG_LIMIT = 300.0

#: log10 half-life (seconds) band edges: 1 s, 1 hour, 1 (Julian) year.
_LOG10_HL_ONE_SECOND = 0.0
_LOG10_HL_ONE_HOUR = math.log10(3600.0)          # ~ 3.556
_LOG10_HL_ONE_YEAR = math.log10(3.15576e7)        # ~ 7.499
_LOG10_LN2 = math.log10(math.log(2.0))            # ~ -0.159


class RateRegime(str, Enum):
    """How fast a reaction proceeds, read off k as a timescale (the standard decade scale)."""

    FAST = "FAST"          # half-life < 1 s
    MODERATE = "MODERATE"  # 1 s <= half-life < 1 hour
    SLOW = "SLOW"          # 1 hour <= half-life < 1 year
    FROZEN = "FROZEN"      # half-life >= 1 year: kinetically frozen
    UNKNOWN = "UNKNOWN"    # no sourced (Ea, A) -> no k


class RateGrade(str, Enum):
    """The epistemic grade of a computed rate (separate from the regime), mirroring M1's grade."""

    DERIVED = "DERIVED"        # reaction temperature INSIDE the sourced Arrhenius fit window (interpolation)
    PREDICTED = "PREDICTED"    # extrapolated outside the fit window, flagged
    UNKNOWN = "UNKNOWN"        # no sourced (Ea, A)


def _regime_of(log10_half_life_s: float) -> RateRegime:
    if log10_half_life_s < _LOG10_HL_ONE_SECOND:
        return RateRegime.FAST
    if log10_half_life_s < _LOG10_HL_ONE_HOUR:
        return RateRegime.MODERATE
    if log10_half_life_s < _LOG10_HL_ONE_YEAR:
        return RateRegime.SLOW
    return RateRegime.FROZEN


#: Bottleneck precedence for aggregating a route/DAG's rate: the slowest step dominates (a FROZEN step stalls
#: the synthesis), then SLOW, then any UNKNOWN gap, then MODERATE; FAST only when every step is.
_REGIME_PRECEDENCE = (
    RateRegime.FROZEN, RateRegime.SLOW, RateRegime.UNKNOWN, RateRegime.MODERATE, RateRegime.FAST,
)


def worst_regime(regimes) -> RateRegime:
    """The slowest-step-dominated regime over several steps -- the route/DAG rate verdict (empty -> UNKNOWN)."""
    present = tuple(regimes)
    for worst in _REGIME_PRECEDENCE:
        if any(r is worst for r in present):
            return worst
    return RateRegime.UNKNOWN


def _format_magnitude(log10_value: float, unit: str) -> str:
    """A readable rendering that never overflows: the number if it fits, else its order of magnitude."""
    if abs(log10_value) < _FLOAT_LOG_LIMIT:
        body = f"{10.0 ** log10_value:.3g}"
    else:
        sign = "" if log10_value > 0 else "-"
        body = f"{sign}1e{log10_value:.1f} (order of magnitude)"
    return f"{body} {unit}".strip()


def _canonical_side(pairs) -> tuple:
    """One side of a reaction as a sorted tuple of ``(canonical-structure-digest, coefficient)`` pairs.

    The digest is ``canonical_digest(m.canonical())`` -- the same structural identity :mod:`smartchem.data.
    autoload` keys on -- so two constitutional isomers with the same formula get DIFFERENT keys and one can
    never inherit the other's sourced rate.
    """
    return tuple(sorted((canonical_digest(m.canonical()), int(c)) for m, c in pairs))


def reaction_evidence_key(step: ExperimentStep) -> ReactionEvidenceKey:
    """The section-9.1 :class:`~smartchem.evidence_key.ReactionEvidenceKey` of a step's reaction (EVD-KEY-01).

    Built from the same signed coefficient vector feasibility uses (so the rate lookup can never disagree with the
    balance) and keyed by canonical STRUCTURE, not formula -- a same-formula isomer is a different reaction.  This
    is the ONE unified key the standard names; the kinetics and Eyring providers both resolve records against it.

    EVD-KEY-CTX-01: the step's DECLARED medium (:attr:`~smartchem.conditions.ConditionEnvelope.medium`) populates
    the section-9.1 ``"phase"`` context (via :func:`~smartchem.evidence_key.phase_context`), so a step declared in
    an explicit phase only resolves a record measured in that phase; a phase-unspecified step is context-free and
    resolves as it always did.
    """
    species, nu = _coefficient_vector(step)
    return ReactionEvidenceKey.from_molecules(
        ((m, n) for m, n in zip(species, nu) if n > 0),
        ((m, -n) for m, n in zip(species, nu) if n < 0),
        context=phase_context(step.envelope.medium),
    )


def reaction_key_of(step: ExperimentStep) -> tuple[tuple, tuple]:
    """The canonical, direction-specific ``(reactants, products)`` STRUCTURE signature of a step's reaction.

    The ``(reactants, products)`` VIEW of :func:`reaction_evidence_key` -- each side a sorted tuple of
    ``(structure-digest, coefficient)`` pairs -- kept for callers that want the bare tuple.  It is exactly
    ``reaction_evidence_key(step).sides``, so the tuple and the unified key can never disagree.
    """
    return reaction_evidence_key(step).sides


@functools.lru_cache(maxsize=None)
def _side_key_from_smiles(smiles_pairs: tuple) -> tuple:
    """The canonical structure key of a record side named by SMILES (memoised: SMILES parse is not free)."""
    return _canonical_side((parse_smiles(s), c) for s, c in smiles_pairs)


def record_evidence_key(rec: "object") -> ReactionEvidenceKey:
    """The section-9.1 :class:`ReactionEvidenceKey` of a sourced record (KineticRef/EyringRef) from its SMILES form.

    EVD-KEY-CTX-01: the record's SOURCED ``phase`` (if any) populates the ``"phase"`` context, so the LOOKUP
    (:meth:`~smartchem.evidence_key.ReactionEvidenceKey.applies_to`) withholds a gas-phase rate from a step
    declared in a conflicting phase.  A record with no (or an unrecognised) ``phase`` is context-free and answers
    any phase, exactly as records did before this field existed.
    """
    return ReactionEvidenceKey.of(
        _side_key_from_smiles(rec.reactant_smiles), _side_key_from_smiles(rec.product_smiles),
        context=phase_context(getattr(rec, "phase", "")),
    )


def _record_key(rec: KineticRef) -> tuple[tuple, tuple]:
    """The canonical ``(reactants, products)`` structure key of a sourced record -- ``record_evidence_key(rec).sides``."""
    return record_evidence_key(rec).sides


def _resolve_record(kinetics: KineticTable, step: ExperimentStep) -> KineticRef | None:
    """The sourced record whose canonical reaction structure matches this step's, direction-specific, or None.

    EVD-KEY-CTX-01: matched by the ``applies_to`` LOOKUP (structure+direction+stoichiometry exact, ``"phase"``
    context SUBSUMED), not raw ``==``, so a record's phase and the step's declared phase must not conflict.
    """
    key = reaction_evidence_key(step)
    for rec in kinetics.records:
        if record_evidence_key(rec).applies_to(key):
            return rec
    return None


@dataclass(frozen=True)
class StepKinetics(Digestible):
    """The rate of one reaction step: a DERIVED rate constant k and its regime, or a loud UNKNOWN."""

    regime: RateRegime
    grade: RateGrade
    temperature_k: float | None
    ea_kj_per_mol: float | None
    log10_a: float | None
    log10_k: float | None
    half_life_s: float | None
    a_units: str
    k_finding: Quantity
    reason: str
    missing: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.regime, RateRegime):
            raise TypeError("regime must be a RateRegime")
        if not isinstance(self.grade, RateGrade):
            raise TypeError("grade must be a RateGrade")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")

    @property
    def is_known(self) -> bool:
        return self.regime is not RateRegime.UNKNOWN


def kinetics_of_step(
    step: ExperimentStep, *, kinetics: KineticTable = DEFAULT_KINETICS, temperature_k: float | None = None,
    losses: tuple = (),
) -> StepKinetics:
    """The Arrhenius rate constant and regime for one step, over sourced kinetic data.

    Looks the step's exact (direction-specific) reaction up in the table; a miss makes the whole verdict a
    LOUD ``UNKNOWN`` rate -- never a fabricated k, never a barrier guessed from bond energies.

    ``losses`` (EVD-KEY-01): if a section-5.3 BLOCKER forbids the ``"kinetics"`` claim class -- the target dropped a
    feature the rate depends on (a kinetic isotope effect, a stereospecific rate) -- a SOURCED k MUST NOT survive
    (section 5.3): the rate is a loud UNKNOWN naming the blocker, never a fabricated-by-omission KNOWN_SOURCED.
    """
    from ..identity import blocking_losses
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    temperature = temperature_k if temperature_k is not None else _temperature_of(step)
    if temperature <= 0:
        raise ValueError("temperature must be a positive absolute temperature (K); k = A*exp(-Ea/RT) is "
                         "undefined at or below 0 K")
    kin_blockers = blocking_losses(tuple(losses), "kinetics")
    if kin_blockers:
        b = kin_blockers[0]
        return StepKinetics(
            RateRegime.UNKNOWN, RateGrade.UNKNOWN, temperature, None, None, None, None, "",
            unknown("rate-constant-k", "", f"section-5.3 blocker: {b.feature} forbids a sourced kinetics claim"),
            f"UNKNOWN: a section-5.3 BLOCKER ({b.feature}) forbids a sourced kinetics claim on this identity -- a "
            f"kinetic isotope effect / stereospecific rate depends on the dropped feature, so a sourced k must not "
            f"survive it (section 5.3)",
            (step.equation(),),
        )
    rec = _resolve_record(kinetics, step)
    if rec is None:
        return StepKinetics(
            RateRegime.UNKNOWN, RateGrade.UNKNOWN, temperature, None, None, None, None, "",
            unknown("rate-constant-k", "", "no sourced Arrhenius (Ea, A) for this exact reaction"),
            "UNKNOWN: no sourced Arrhenius (Ea, A) for this reaction, so k = A·exp(-Ea/RT) cannot be computed "
            "(inject a sourced KineticRef to close this gap); a rate is NEVER guessed from bond energies (W3)",
            (step.equation(),),
        )

    # log10 k = log10 A - Ea/(R T ln10); Ea in kJ -> J.  Stays finite even when k overflows a float.
    log10_k = rec.log10_a - (rec.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * temperature * _LN10)
    # Half-life: t½ = ln2/k for first order.  For higher order this is the pseudo-first-order half-life at a
    # DECLARED 1 mol/L reference (k_eff = k at C=1 numerically), an idealisation -- stated, not hidden.
    log10_half_life = _LOG10_LN2 - log10_k
    regime = _regime_of(log10_half_life)
    half_life_s = 10.0 ** log10_half_life if abs(log10_half_life) < _FLOAT_LOG_LIMIT else None

    lo, hi = rec.temperature_range_k
    in_window = lo <= temperature <= hi
    grade = RateGrade.DERIVED if in_window else RateGrade.PREDICTED

    conc_note = (
        "" if rec.is_first_order
        else " at a 1 mol/L reference concentration (declared idealisation; a real timescale depends on "
             "concentration)"
    )
    extrap = "" if in_window else (
        f" [PREDICTED: {temperature:.0f} K is outside the sourced fit window {lo:.0f}-{hi:.0f} K -- "
        f"extrapolated via constant Ea/A]"
    )
    hl_str = (
        _format_magnitude(log10_half_life, "s")
        if half_life_s is not None or abs(log10_half_life) >= _FLOAT_LOG_LIMIT
        else f"{half_life_s:.3g} s"
    )
    k_str = _format_magnitude(log10_k, rec.a_units)
    reason = (
        f"{regime.value}: k = {k_str} at {temperature:.1f} K "
        f"(log10 k = {log10_k:.2f}; from Ea = {rec.ea_kj_per_mol:.1f} kJ/mol, log10 A = {rec.log10_a:.2f} via "
        f"k = A·exp(-Ea/RT)); half-life ~ {hl_str}{conc_note}{extrap} -- rate under the SOURCED Arrhenius fit; "
        f"NOT a claim of which cleavage Nature takes nor its true rate under real conditions (W3)"
    )
    k_finding = Quantity(
        "rate-constant-k", _format_magnitude(log10_k, "").strip() or f"1e{log10_k:.2f}", rec.a_units,
        Bucket.KNOWN_SOURCED,
        f"{grade.value} via k = A·exp(-Ea/RT) (Arrhenius, established) at {temperature:.1f} K over sourced "
        f"(Ea, A): {rec.provenance}",
    )
    return StepKinetics(
        regime, grade, temperature, rec.ea_kj_per_mol, rec.log10_a, log10_k, half_life_s, rec.a_units,
        k_finding, reason, (),
    )


@dataclass(frozen=True)
class RouteKinetics(Digestible):
    """The rate of a whole route: one :class:`StepKinetics` per step, and a bottleneck-dominated verdict.

    Verdict precedence (honest, slowest-step-dominated): a ``FROZEN`` step stalls the whole synthesis and
    dominates; then ``SLOW``; then any ``UNKNOWN`` (missing kinetic data) keeps the route from a clean fast
    read; then ``MODERATE``; a route is ``FAST`` only when every step is.  The slowest step is the rate
    bottleneck, exactly as the least-favorable step dominates feasibility.
    """

    route: ExperimentRoute
    per_step: tuple[StepKinetics, ...]

    def __post_init__(self) -> None:
        if type(self.route) is not ExperimentRoute:
            raise TypeError("route must be an ExperimentRoute")
        if type(self.per_step) is not tuple or any(type(s) is not StepKinetics for s in self.per_step):
            raise TypeError("per_step must be a tuple of StepKinetics values")
        if len(self.per_step) != len(self.route.steps):
            raise ValueError(f"expected {len(self.route.steps)} step kinetics, got {len(self.per_step)}")

    @property
    def verdict(self) -> str:
        return worst_regime(s.regime for s in self.per_step).value

    def explain(self) -> str:
        lines = [f"kinetics (rate, k = A·exp(-Ea/RT); slowest step dominates): {self.verdict}"]
        for idx, s in enumerate(self.per_step):
            lines.append(f"  step {idx + 1}: {s.reason}")
        return "\n".join(lines)


def verify_kinetics(
    route: ExperimentRoute, *, kinetics: KineticTable = None, temperature_k: float | None = None, losses: tuple = (),
) -> RouteKinetics:
    """The Arrhenius rate of every step of a route, over the sourced (injectable) kinetic table.

    ``losses`` (EVD-KEY-01): a section-5.3 BLOCKER for ``"kinetics"`` downgrades every step's sourced rate to UNKNOWN.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    tbl = DEFAULT_KINETICS if kinetics is None else kinetics
    per_step = tuple(
        kinetics_of_step(s, kinetics=tbl, temperature_k=temperature_k, losses=losses) for s in route.steps
    )
    return RouteKinetics(route, per_step)
