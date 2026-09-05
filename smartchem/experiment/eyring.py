"""L1 (Eyring / transition-state theory) -- the rate constant ``k = (kB*T/h)*exp(-ΔG‡/RT)``, the SECOND rate
provider.

The sibling of :mod:`smartchem.experiment.kinetics`.  Where that provider reproduces ``k`` from a sourced
Arrhenius pair ``(Ea, A)``, this one reproduces it from sourced transition-state activation parameters
``(ΔH‡, ΔS‡)`` via the Eyring equation (established transition-state theory, Eyring 1935 / Evans & Polanyi
1935): ``ΔG‡ = ΔH‡ - T*ΔS‡`` then ``k = (kB*T/h)*exp(-ΔG‡/RT)``.  The two are INDEPENDENT bearings on the
SAME observable ``k`` -- ONE rate axis, TWO providers -- so this module deliberately SHARES the regime bands,
grade, canonical-structure keying, and overflow-safe ``log10`` machinery of the Arrhenius provider rather
than forking them, and adds only the two physical constants the prefactor needs.  Where both providers cover
a reaction, :func:`rate_agreement` cross-checks the two computed ``k``'s (the "two blind paths to one number"
discipline); neither is ever derived from the other.

Boundaries, stated loudly (identical to the Arrhenius provider). (1) ORTHOGONAL to and never altering the
epistemic grade.  (2) ``k`` is reproduced ONLY where ``(ΔH‡, ΔS‡)`` are SOURCED for this exact
(direction-specific) reaction; the engine never predicts a barrier -- not from bond energies, not from an
Arrhenius ``Ea/A`` (that would be circular), and not from ground-state formation data (a transition state has
no formation enthalpy) -- a miss is a LOUD ``UNKNOWN``, and which cleavage Nature takes is the permanent W3
wall.  Calibrated on a reaction whose measured rate the engine must recover before its outputs are believed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..contracts import Digestible
from ..data.eyring import DEFAULT_EYRING, EyringRef, EyringTable
from .bucket import Bucket, Quantity, unknown
from .feasibility import _temperature_of
from .kinetics import (
    GAS_CONSTANT_J_PER_MOL_K,
    RateGrade,
    RateRegime,
    StepKinetics,
    _FLOAT_LOG_LIMIT,
    _LN10,
    _LOG10_LN2,
    _format_magnitude,
    _regime_of,
    _reaction_evidence_key_or_none,
    record_evidence_key,
    worst_regime,
)
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "BOLTZMANN_J_PER_K",
    "PLANCK_J_S",
    "StepEyring",
    "RouteEyring",
    "eyring_of_step",
    "verify_eyring",
    "rate_agreement",
]

#: Boltzmann constant kB (J/K) and Planck constant h (J*s) -- SI-2019 EXACT-by-definition values (not
#: measured, so not a recalled-physics hazard), the two constants the Eyring prefactor kB*T/h needs and that
#: the Arrhenius provider (which needs only R) did not.
BOLTZMANN_J_PER_K = 1.380649e-23
PLANCK_J_S = 6.62607015e-34
#: log10 of the prefactor coefficient kB/h (= 2.0836...e10 s^-1 K^-1); the full prefactor kB*T/h is added as
#: ``_LOG10_KB_OVER_H + log10(T)`` so an enormous rate never overflows a float (the same honesty as Arrhenius).
_LOG10_KB_OVER_H = math.log10(BOLTZMANN_J_PER_K / PLANCK_J_S)


def _resolve_barrier(barriers: EyringTable, step: ExperimentStep) -> EyringRef | None:
    """The sourced record whose canonical reaction structure matches this step's, direction-specific, or None.

    Resolves against the ONE unified section-9.1 key (:func:`~smartchem.experiment.kinetics.reaction_evidence_key`
    / :func:`~smartchem.experiment.kinetics.record_evidence_key`, EVD-KEY-01), so an isomer never inherits another
    reaction's barrier and the Eyring and Arrhenius providers key evidence identically.  EVD-KEY-CTX-01: matched by
    the ``applies_to`` LOOKUP (``"phase"`` context SUBSUMED), so a barrier measured in one phase is not borrowed by
    a step declared in a conflicting one.
    """
    key = _reaction_evidence_key_or_none(step)
    if key is None:
        return None
    for rec in barriers.records:
        if record_evidence_key(rec).applies_to(key):
            return rec
    return None


@dataclass(frozen=True)
class StepEyring(Digestible):
    """The rate of one reaction step from transition-state theory: a DERIVED ``k`` and its regime, or UNKNOWN.

    Shares :class:`~smartchem.experiment.kinetics.RateRegime` / ``RateGrade`` with the Arrhenius provider (one
    rate axis); carries the activation parameters it used (``ΔH‡``, ``ΔS‡``, and the ``ΔG‡`` at the step
    temperature) instead of the Arrhenius ``(Ea, A)``.
    """

    regime: RateRegime
    grade: RateGrade
    temperature_k: float | None
    dh_dagger_kj_per_mol: float | None
    ds_dagger_j_per_mol_k: float | None
    dg_dagger_kj_per_mol: float | None
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


def eyring_of_step(
    step: ExperimentStep, *, barriers: EyringTable = DEFAULT_EYRING, temperature_k: float | None = None
) -> StepEyring:
    """The transition-state rate constant and regime for one step, over sourced activation parameters.

    Looks the step's exact (direction-specific) reaction up in the barrier table; a miss makes the whole
    verdict a LOUD ``UNKNOWN`` rate -- never a fabricated ``k``, never a barrier guessed or borrowed.
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    temperature = temperature_k if temperature_k is not None else _temperature_of(step)
    if temperature <= 0:
        raise ValueError("temperature must be a positive absolute temperature (K); k = (kB*T/h)*exp(-ΔG‡/RT) "
                         "is undefined at or below 0 K")
    rec = _resolve_barrier(barriers, step)
    if rec is None:
        if _reaction_evidence_key_or_none(step) is None:
            reason = (
                "UNKNOWN: no net chemical transformation after cancelling identical species; "
                "the reaction-rate model does not describe handling or physical changes of unchanged species"
            )
            return StepEyring(
                RateRegime.UNKNOWN, RateGrade.UNKNOWN, temperature, None, None, None, None, None, "",
                unknown("rate-constant-k-eyring", "", reason), reason, (step.equation(),),
            )
        return StepEyring(
            RateRegime.UNKNOWN, RateGrade.UNKNOWN, temperature, None, None, None, None, None, "",
            unknown("rate-constant-k-eyring", "", "no sourced ΔH‡/ΔS‡ for this exact reaction"),
            "UNKNOWN: no sourced transition-state (ΔH‡, ΔS‡) for this reaction, so k = (kB·T/h)·exp(-ΔG‡/RT) "
            "cannot be computed (inject a sourced EyringRef to close this gap); a barrier is NEVER guessed "
            "from bond energies nor back-computed from Arrhenius (Ea, A) (W3)",
            (step.equation(),),
        )

    # ΔG‡(T) = ΔH‡ - T·ΔS‡ (ΔS‡ in J -> kJ); log10 k = log10(kB·T/h) - ΔG‡·1000/(R·T·ln10).
    dg_dagger = rec.dh_dagger_kj_per_mol - temperature * rec.ds_dagger_j_per_mol_k / 1000.0
    log10_k = (
        _LOG10_KB_OVER_H + math.log10(temperature)
        - (dg_dagger * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * temperature * _LN10)
    )
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
        f"extrapolated via constant ΔH‡/ΔS‡]"
    )
    hl_str = (
        _format_magnitude(log10_half_life, "s")
        if half_life_s is not None or abs(log10_half_life) >= _FLOAT_LOG_LIMIT
        else f"{half_life_s:.3g} s"
    )
    k_str = _format_magnitude(log10_k, rec.a_units)
    reason = (
        f"{regime.value}: k = {k_str} at {temperature:.1f} K (log10 k = {log10_k:.2f}; from "
        f"ΔH‡ = {rec.dh_dagger_kj_per_mol:.1f} kJ/mol, ΔS‡ = {rec.ds_dagger_j_per_mol_k:.1f} J/mol/K "
        f"=> ΔG‡ = {dg_dagger:.1f} kJ/mol via k = (kB·T/h)·exp(-ΔG‡/RT)); half-life ~ {hl_str}{conc_note}"
        f"{extrap} -- rate under the SOURCED Eyring fit; NOT a claim of which cleavage Nature takes nor its "
        f"true rate under real conditions (W3)"
    )
    k_finding = Quantity(
        "rate-constant-k-eyring", _format_magnitude(log10_k, "").strip() or f"1e{log10_k:.2f}", rec.a_units,
        Bucket.KNOWN_SOURCED,
        f"{grade.value} via k = (kB·T/h)·exp(-ΔG‡/RT) (Eyring/TST, established) at {temperature:.1f} K over "
        f"sourced (ΔH‡, ΔS‡): {rec.provenance}",
    )
    return StepEyring(
        regime, grade, temperature, rec.dh_dagger_kj_per_mol, rec.ds_dagger_j_per_mol_k, dg_dagger,
        log10_k, half_life_s, rec.a_units, k_finding, reason, (),
    )


def rate_agreement(kin: StepKinetics, eyr: StepEyring) -> str | None:
    """A cross-check note when BOTH providers computed ``k`` for the same step -- two INDEPENDENT bearings.

    Returns ``None`` when either provider had no sourced data (nothing to cross-check).  When both fired,
    compares their ``log10 k``: agreement within ~1 decade CORROBORATES (two independent sourced routes to
    one number), a wider gap is FLAGGED, never hidden -- the repo's relational-check discipline, but on the
    ABSOLUTE values each provider computed independently, not a shared term.
    """
    if not (kin.is_known and eyr.is_known) or kin.log10_k is None or eyr.log10_k is None:
        return None
    gap = abs(kin.log10_k - eyr.log10_k)
    if gap <= 1.0:
        return (
            f"rate cross-check: the Arrhenius and Eyring providers AGREE within {gap:.2f} decades on log10 k "
            f"({kin.log10_k:.2f} vs {eyr.log10_k:.2f}) -- two independent sourced bearings corroborate"
        )
    return (
        f"rate cross-check: the Arrhenius and Eyring providers DISAGREE by {gap:.2f} decades on log10 k "
        f"({kin.log10_k:.2f} vs {eyr.log10_k:.2f}) -- FLAGGED; the two sourced fits are not consistent here"
    )


@dataclass(frozen=True)
class RouteEyring(Digestible):
    """The transition-state rate of a whole route: one :class:`StepEyring` per step, bottleneck-dominated."""

    route: ExperimentRoute
    per_step: tuple[StepEyring, ...]

    def __post_init__(self) -> None:
        if type(self.route) is not ExperimentRoute:
            raise TypeError("route must be an ExperimentRoute")
        if type(self.per_step) is not tuple or any(type(s) is not StepEyring for s in self.per_step):
            raise TypeError("per_step must be a tuple of StepEyring values")
        if len(self.per_step) != len(self.route.steps):
            raise ValueError(f"expected {len(self.route.steps)} step eyring, got {len(self.per_step)}")

    @property
    def verdict(self) -> str:
        return worst_regime(s.regime for s in self.per_step).value

    def explain(self) -> str:
        lines = [f"eyring (rate, k = (kB·T/h)·exp(-ΔG‡/RT); slowest step dominates): {self.verdict}"]
        for idx, s in enumerate(self.per_step):
            lines.append(f"  step {idx + 1}: {s.reason}")
        return "\n".join(lines)


def verify_eyring(
    route: ExperimentRoute, *, barriers: EyringTable = None, temperature_k: float | None = None
) -> RouteEyring:
    """The transition-state rate of every step of a route, over the sourced (injectable) barrier table."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    tbl = DEFAULT_EYRING if barriers is None else barriers
    per_step = tuple(eyring_of_step(s, barriers=tbl, temperature_k=temperature_k) for s in route.steps)
    return RouteEyring(route, per_step)
