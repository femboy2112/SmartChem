"""M2 -- equilibrium extent: the DERIVED ``K = exp(-ΔG/RT)`` and how far a reaction goes at equilibrium.

With M1's ΔG in hand, the equilibrium constant is one established relation away -- ``K = exp(-ΔG/RT)`` (the
van't Hoff / reaction-isotherm relation) -- and it turns a *sign* (favorable / unfavorable) into an *extent*:
how completely the reaction proceeds before it stalls at equilibrium.  That is the DERIVED bound the roadmap
calls *tighter than E2's 100% conservation ceiling*: the ceiling assumes 100% conversion, thermodynamics says
equilibrium caps it at some fraction, and where ΔG is sourced we can say which.  Still known chemistry, not
new: we reproduce the equilibrium constant an established model gives, exactly as M1 reproduces ΔG.

What M2 emits, and what it does NOT
-----------------------------------
* **K (the equilibrium constant)** -- ``exp(-ΔG/RT)`` at the reaction temperature.  Reported as ``log10 K``
  too, so an astronomically favorable reaction (water synthesis, log10 K ~ 83) does not overflow a float into
  a fabricated ``inf``: the magnitude is carried honestly.
* **The equilibrium EXTENT verdict** -- an assumption-free reading of K on the standard chemist's decade
  scale: ``ESSENTIALLY_COMPLETE`` (K >= 1e3, the conservation ceiling is thermodynamically approachable) /
  ``FAVORABLE`` (products dominate) / ``BALANCED`` (K ~ 1, comparable amounts) / ``LIMITED`` (reactants
  dominate) / ``NEGLIGIBLE`` (K <= 1e-3, the reaction barely proceeds -- the ceiling wildly overstates it) /
  ``UNKNOWN`` (no ΔG).  This needs no activity model: it is the direct meaning of K's magnitude.
* **The equilibrium CONVERSION fraction** -- a concrete "yield in the equilibrium sense" -- computed ONLY
  where it is exactly and unambiguously solvable: a reaction with **no net change in moles** of its balanced
  species (Δn = 0), under a declared ideal reference (ideal activities, stoichiometric equimolar charge, no
  initial product).  There the reference concentration cancels and the conversion has an exact closed form,
  ``α = t/(1+t)`` with ``t = (K / C_stoich)^(1/M)``.  Where Δn != 0 the conversion depends on a reference
  concentration/pressure and the initial state, so it is a LOUD ``UNKNOWN`` (K and the extent verdict are
  still DERIVED) -- never a fabricated fraction.  This is the same honesty as E1's pressure residue.

Boundaries, stated loudly. (1) Equilibrium is *extent*, never *rate*: a reaction can be thermodynamically
``ESSENTIALLY_COMPLETE`` and kinetically frozen (diamond is thermodynamically favored to become graphite).
K says *how far*, never *how fast* -- kinetics is unbuilt (roadmap L1).  (2) The conversion's ideal reference
is a stated idealisation; real activities shift it, and a caller injects sourced data to refine it.
Calibrated on known cases: Haber recovers K ~ 6e5 at 298 K and its collapse below 1 at 700 K; a symmetric
Δn=0 reaction at K=1 converts exactly half.

Independence: M2 does not recompute ΔG.  It calls :func:`~smartchem.experiment.feasibility.feasibility_of_step`
for the sourced ΔG, its grade, and its temperature -- so feasibility and equilibrium can never disagree on the
thermodynamics, and the stoichiometry is the same kernel-cross-checked coefficient vector the ceiling divides
by (:func:`~smartchem.experiment.ceiling._coefficient_vector`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ..contracts import Digestible
from ..data.thermo import DEFAULT_THERMO, ThermoTable
from .bucket import Bucket, Quantity, unknown
from .ceiling import _coefficient_vector
from .feasibility import FeasibilityGrade, feasibility_of_step
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "GAS_CONSTANT_J_PER_MOL_K",
    "EquilibriumExtent",
    "StepEquilibrium",
    "RouteEquilibrium",
    "equilibrium_of_step",
    "verify_equilibrium",
]

#: The molar gas constant R (J/mol/K), CODATA -- the one constant K = exp(-ΔG/RT) needs.
GAS_CONSTANT_J_PER_MOL_K = 8.314462618
#: math.exp overflows / underflows near |x| ~ 709; past this we read the limit (K -> inf / 0) exactly.
_EXP_LIMIT = 700.0


class EquilibriumExtent(str, Enum):
    """How far a reaction proceeds at equilibrium, read off K's magnitude (the standard decade scale)."""

    ESSENTIALLY_COMPLETE = "ESSENTIALLY_COMPLETE"  # K >= 1e3: the 100% ceiling is thermodynamically approachable
    FAVORABLE = "FAVORABLE"                        # 1e1 <= K < 1e3: products dominate at equilibrium
    BALANCED = "BALANCED"                          # 1e-1 < K < 1e1: comparable amounts (K ~ 1, ΔG ~ 0)
    LIMITED = "LIMITED"                            # 1e-3 < K <= 1e-1: reactants dominate
    NEGLIGIBLE = "NEGLIGIBLE"                       # K <= 1e-3: the reaction barely proceeds
    UNKNOWN = "UNKNOWN"                            # no sourced ΔG -> no K


#: log10 K decade thresholds for the extent bands (symmetric about K = 1).
_LOG10_COMPLETE = 3.0    # K >= 1e3
_LOG10_FAVORABLE = 1.0   # K >= 1e1
_LOG10_BALANCED = -1.0   # K >  1e-1
_LOG10_LIMITED = -3.0    # K >  1e-3


def _extent_of(log10_k: float) -> EquilibriumExtent:
    if log10_k >= _LOG10_COMPLETE:
        return EquilibriumExtent.ESSENTIALLY_COMPLETE
    if log10_k >= _LOG10_FAVORABLE:
        return EquilibriumExtent.FAVORABLE
    if log10_k > _LOG10_BALANCED:
        return EquilibriumExtent.BALANCED
    if log10_k > _LOG10_LIMITED:
        return EquilibriumExtent.LIMITED
    return EquilibriumExtent.NEGLIGIBLE


def _format_k(log10_k: float) -> str:
    """A readable rendering of K that never overflows: the number if it fits, else its order of magnitude."""
    if abs(log10_k) < 300.0:
        return f"{10.0 ** log10_k:.3g}"
    sign = "" if log10_k > 0 else "-"
    return f"{sign}1e{log10_k:.1f} (order of magnitude; log10 K = {log10_k:.2f})"


def _ideal_conversion(step: ExperimentStep, log10_k: float) -> tuple[float | None, str]:
    """The equilibrium conversion fraction α for the Δn=0 ideal reference case, or ``(None, why)``.

    For a reaction with no net mole change over its balanced species, under ideal activities and a
    stoichiometric equimolar charge with no initial product, the reference concentration cancels and::

        (ξ/(c-ξ))^M = K / C_stoich   =>   α = ξ/c = t/(1+t),  t = (K/C_stoich)^(1/M)

    where ``M = Σ reactant coefficients`` and ``C_stoich = Π b_j^b_j / Π a_i^a_i`` (product/reactant
    coefficient factors).  Δn != 0 makes K carry a reference-state dependence, so no fraction is returned.
    """
    _species, nu = _coefficient_vector(step)
    if sum(nu) != 0:  # Σnu = -(moles_products - moles_reactants); Σnu=0 <=> Δn=0
        delta_n = -sum(nu)
        return None, (
            f"net mole change Δn = {delta_n:+d} != 0: the equilibrium conversion depends on a reference "
            f"concentration/pressure and the initial state; inject a declared activity model to compute it"
        )
    reactant_coeffs = [n for n in nu if n > 0]           # a_i
    product_coeffs = [-n for n in nu if n < 0]           # b_j
    m = sum(reactant_coeffs)                             # M = Σ a_i = Σ b_j (since Δn=0)
    if m <= 0:
        return None, "no net reactant coefficient; the conversion reference is undefined"
    # ln Q = ln K - ln C_stoich, with ln K = log10_k * ln(10) and ln C_stoich = Σ b ln b - Σ a ln a
    ln_c_stoich = sum(b * math.log(b) for b in product_coeffs) - sum(a * math.log(a) for a in reactant_coeffs)
    ln_q = log10_k * math.log(10.0) - ln_c_stoich
    x = ln_q / m                                         # ln t, t = (K/C_stoich)^(1/M)
    if x > _EXP_LIMIT:
        return 1.0, "Δn=0 ideal reference (equimolar stoichiometric charge, ideal activities): K -> complete"
    if x < -_EXP_LIMIT:
        return 0.0, "Δn=0 ideal reference (equimolar stoichiometric charge, ideal activities): K -> zero"
    t = math.exp(x)
    return t / (1.0 + t), "Δn=0 ideal reference: ideal activities, stoichiometric equimolar charge, no product"


@dataclass(frozen=True)
class StepEquilibrium(Digestible):
    """The equilibrium extent of one step: K (and log10 K), the extent verdict, and -- where exactly
    solvable -- the ideal-reference conversion fraction.  Or a loud UNKNOWN when ΔG is not sourced."""

    extent: EquilibriumExtent
    grade: FeasibilityGrade
    temperature_k: float | None
    delta_g_kj: float | None
    log10_k: float | None
    conversion_fraction: float | None
    k_finding: Quantity
    conversion_finding: Quantity
    reason: str
    missing: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.extent, EquilibriumExtent):
            raise TypeError("extent must be an EquilibriumExtent")
        if not isinstance(self.grade, FeasibilityGrade):
            raise TypeError("grade must be a FeasibilityGrade")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")

    @property
    def is_known(self) -> bool:
        return self.extent is not EquilibriumExtent.UNKNOWN


def equilibrium_of_step(
    step: ExperimentStep, *, thermo: ThermoTable = DEFAULT_THERMO, temperature_k: float | None = None,
    derive: bool = True,
) -> StepEquilibrium:
    """The DERIVED equilibrium constant and extent for one step, over sourced (and, when ``derive``, the
    default, group-additivity-derived) thermodynamic data.

    Reuses :func:`~smartchem.experiment.feasibility.feasibility_of_step` for ΔG, its grade, and the reaction
    temperature (so M1 and M2 never disagree -- ``derive`` is threaded straight through for exactly that
    reason), then ``K = exp(-ΔG/RT)``.  A species whose ΔfH°/S° is neither sourced nor derivable makes the
    whole verdict UNKNOWN -- loud, never a fabricated K.
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    feas = feasibility_of_step(step, thermo=thermo, temperature_k=temperature_k, derive=derive)
    if feas.delta_g_kj is None:  # no sourced ΔG -> no K
        return StepEquilibrium(
            EquilibriumExtent.UNKNOWN, FeasibilityGrade.UNKNOWN, feas.temperature_k, None, None, None,
            unknown("equilibrium-constant-K", "", "a reactant/product has no sourced formation enthalpy/entropy"),
            unknown("equilibrium-conversion", "fraction", "K is unknown, so the equilibrium extent is unknown"),
            f"UNKNOWN: {feas.reason.split(':', 1)[-1].strip()} -- K = exp(-ΔG/RT) cannot be computed",
            feas.missing,
        )

    temperature = feas.temperature_k
    # ln K = -ΔG / (R T); ΔG in kJ -> J. log10 K stays finite even when K overflows a float.
    log10_k = -(feas.delta_g_kj * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * temperature * math.log(10.0))
    extent = _extent_of(log10_k)
    grade = feas.grade

    conversion, conv_note = _ideal_conversion(step, log10_k)

    k_finding = Quantity(
        "equilibrium-constant-K", _format_k(log10_k), "", Bucket.KNOWN_SOURCED,
        f"{grade.value} via K = exp(-ΔG/RT) (established) at {temperature:.1f} K over sourced ΔfH°/S° "
        f"(log10 K = {log10_k:.2f})",
    )
    if conversion is None:
        conversion_finding = unknown("equilibrium-conversion", "fraction", conv_note)
    else:
        conversion_finding = Quantity(
            "equilibrium-conversion", f"{conversion:.3f}", "fraction", Bucket.KNOWN_SOURCED,
            f"{grade.value}: {conv_note} -- an ideal-model equilibrium fraction, NOT an expected "
            "isolated/practical yield",
        )

    extrap = "" if grade is FeasibilityGrade.DERIVED else (
        " [PREDICTED: extrapolated from the 298.15 K reference via constant ΔH/ΔS]"
    )
    conv_str = (
        f"; ideal-model equilibrium conversion ~{conversion * 100:.0f}% ({conv_note})"
        if conversion is not None
        else f"; conversion UNKNOWN ({conv_note})"
    )
    reason = (
        f"{extent.value}: K = {_format_k(log10_k)} at {temperature:.1f} K "
        f"(log10 K = {log10_k:.2f}; from ΔG = {feas.delta_g_kj:.1f} kJ/mol via K = exp(-ΔG/RT))"
        f"{conv_str}{extrap} -- ideal-model equilibrium extent, NOT a rate and NOT an expected "
        "isolated/practical yield (standard section 9.5)"
    )
    return StepEquilibrium(
        extent, grade, temperature, feas.delta_g_kj, log10_k, conversion, k_finding, conversion_finding,
        reason, (),
    )


@dataclass(frozen=True)
class RouteEquilibrium(Digestible):
    """The equilibrium extent of a whole route: one :class:`StepEquilibrium` per step, and a verdict.

    Verdict precedence (honest, bottleneck-dominated): the least-complete SOURCED step caps the route, so a
    ``NEGLIGIBLE`` step dominates, then ``LIMITED``; then any ``UNKNOWN`` (missing ΔG) keeps the route from a
    clean complete read; then ``BALANCED``, ``FAVORABLE``; a route is ``ESSENTIALLY_COMPLETE`` only when every
    step is.  A sourced thermodynamic bottleneck is worse news than a gap, exactly as in feasibility.
    """

    route: ExperimentRoute
    per_step: tuple[StepEquilibrium, ...]

    def __post_init__(self) -> None:
        if type(self.route) is not ExperimentRoute:
            raise TypeError("route must be an ExperimentRoute")
        if type(self.per_step) is not tuple or any(type(s) is not StepEquilibrium for s in self.per_step):
            raise TypeError("per_step must be a tuple of StepEquilibrium values")
        if len(self.per_step) != len(self.route.steps):
            raise ValueError(f"expected {len(self.route.steps)} step equilibria, got {len(self.per_step)}")

    @property
    def verdict(self) -> str:
        e = [s.extent for s in self.per_step]
        for worst in (EquilibriumExtent.NEGLIGIBLE, EquilibriumExtent.LIMITED, EquilibriumExtent.UNKNOWN,
                      EquilibriumExtent.BALANCED, EquilibriumExtent.FAVORABLE):
            if any(x is worst for x in e):
                return worst.value
        return EquilibriumExtent.ESSENTIALLY_COMPLETE.value

    def explain(self) -> str:
        lines = [f"equilibrium (thermodynamic extent, K = exp(-ΔG/RT)): {self.verdict}"]
        for idx, s in enumerate(self.per_step):
            lines.append(f"  step {idx + 1}: {s.reason}")
        return "\n".join(lines)


def verify_equilibrium(
    route: ExperimentRoute, *, thermo: ThermoTable = None, temperature_k: float | None = None,
    derive: bool = True,
) -> RouteEquilibrium:
    """The equilibrium extent of every step of a route, over the sourced (injectable) thermo table plus (when
    ``derive``, the default) the group-additivity gas-phase fallback -- threaded to match M1."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    tbl = DEFAULT_THERMO if thermo is None else thermo
    per_step = tuple(
        equilibrium_of_step(s, thermo=tbl, temperature_k=temperature_k, derive=derive) for s in route.steps
    )
    return RouteEquilibrium(route, per_step)
