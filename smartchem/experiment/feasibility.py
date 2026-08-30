"""M1 -- thermodynamic feasibility: the DERIVED ΔG verdict on a reaction step.

The keystone of the corrected governing frame. "Is this reaction feasible?" is not a forbidden prediction:
where sourced standard thermodynamic data (:mod:`smartchem.data.thermo`) covers every species, an ESTABLISHED
model computes the reaction's Gibbs free energy -- ΔH by Hess's law, ΔG = ΔH - TΔS -- and grades it. That is
reproducing known chemistry, exactly as the PySCF oracle *computes* an atomization energy rather than looking
one up. Where the data does not reach, the verdict is a LOUD ``UNKNOWN``, never a fabricated ΔG.

What the verdict means, and what it does NOT
--------------------------------------------
* ``FAVORABLE`` -- ΔG < 0 at the reaction temperature: thermodynamically spontaneous in the written
  direction (a DERIVED/PREDICTED fact, graded below).
* ``UNFAVORABLE`` -- ΔG > 0: endergonic in this direction *at standard state*. This is a sourced
  *disfavour*, NOT a claim of impossibility -- coupling to another reaction, non-standard concentrations, or
  removing a product (Le Chatelier) can still drive it; the equilibrium extent quantifies how far (roadmap
  M2). We say "disfavored", never "cannot happen".
* ``BORDERLINE`` -- |ΔG| within a near-equilibrium band: neither strongly driven nor forbidden.
* ``UNKNOWN`` -- a species has no sourced thermodynamic data: no ΔG is computed.

The epistemic GRADE is separate from the direction:
* ``DERIVED`` -- computed at or near the 298.15 K reference of the sourced data (interpolation).
* ``PREDICTED`` -- extrapolated far from 298.15 K via the constant-ΔH/ΔS approximation (ΔH°, S° held
  temperature-independent). A real, established approximation, but an extrapolation -- so it is flagged.

Two boundaries stated loudly. (1) Thermodynamics answers *whether*, never *how fast*: ΔG is not a rate, and
a favorable ΔG is not a yield -- kinetics is a separate, unbuilt model. (2) The computation is at standard
state (1 bar, pure phases, the data's reference phase); real conditions shift it, and a caller injects their
own sourced data to refine it. Calibrated on known cases: 2H2+O2->2H2O(l) recovers ΔG°=-474 kJ, Haber
recovers -33 kJ and its ~465 K sign-flip -- the instrument reads true before its novel outputs are believed.

Independence: the data is a SEPARATE sourced table, and the stoichiometric coefficients come from
:func:`~smartchem.experiment.ceiling._coefficient_vector` -- the same kernel-cross-checked derivation the
ceiling divides by, so feasibility and the ceiling can never disagree on the balance.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..category import Molecule
from ..conditions import ConditionEnvelope
from ..contracts import Digestible
from ..data.thermo import DEFAULT_THERMO, REFERENCE_TEMPERATURE_K, ThermoRef, ThermoTable
from ..decompiler import Formula
from ..structure import resolve_structure
from .bucket import Bucket, Quantity, unknown
from .ceiling import _coefficient_vector
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "FeasibilityDirection",
    "FeasibilityGrade",
    "StepFeasibility",
    "RouteFeasibility",
    "resolve_thermo",
    "feasibility_of_step",
    "verify_feasibility",
]

#: Within this many kelvin of the data's 298.15 K reference, a ΔG is DERIVED; beyond it, PREDICTED.
NEAR_REFERENCE_K = 100.0
#: |ΔG| below this (kJ/mol) is reported BORDERLINE (near-equilibrium) rather than favored/disfavored.
BORDERLINE_KJ = 5.0


class FeasibilityDirection(str, Enum):
    FAVORABLE = "FAVORABLE"        # ΔG < 0 at T
    UNFAVORABLE = "UNFAVORABLE"    # ΔG > 0 at T (endergonic in this direction, at standard state)
    BORDERLINE = "BORDERLINE"      # |ΔG| within the near-equilibrium band
    UNKNOWN = "UNKNOWN"            # a species has no sourced thermodynamic data


class FeasibilityGrade(str, Enum):
    DERIVED = "DERIVED"            # computed at/near the 298.15 K reference (interpolation)
    PREDICTED = "PREDICTED"        # extrapolated far from 298.15 K (constant ΔH/ΔS), flagged
    UNKNOWN = "UNKNOWN"            # no computation possible


def _formula_str(molecule: Molecule) -> str:
    return repr(Formula.of(molecule.formula, molecule.charge))


def _label(molecule: Molecule) -> str:
    named = resolve_structure(molecule)
    return named.name if named is not None else _formula_str(molecule)


def resolve_thermo(molecule: Molecule, table: ThermoTable = DEFAULT_THERMO) -> ThermoRef | None:
    """The sourced thermo record for ``molecule`` -- named if the registry resolves it, else formula-level
    (unambiguous only), else ``None`` (a loud gap).  Mirrors ``composability.resolve_stability``."""
    named = resolve_structure(molecule)
    if named is not None:
        hit = table.for_named(named.expected_formula, named.name)
        if hit is not None:
            return hit
    return table.for_formula(_formula_str(molecule))


def _temperature_of(step: ExperimentStep) -> float:
    """The step's reaction temperature (K): the declared envelope's midpoint, or the 298.15 K reference."""
    env: ConditionEnvelope = step.envelope
    if env.temperature is not None:
        return (env.temperature.lo + env.temperature.hi) / 2.0
    return REFERENCE_TEMPERATURE_K


@dataclass(frozen=True)
class StepFeasibility(Digestible):
    """The thermodynamic feasibility of one reaction step: a DERIVED ΔG and its graded verdict, or UNKNOWN."""

    direction: FeasibilityDirection
    grade: FeasibilityGrade
    temperature_k: float | None
    delta_h_kj: float | None
    delta_s_j_per_k: float | None
    delta_g_kj: float | None
    reason: str
    finding: Quantity
    missing: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.direction, FeasibilityDirection):
            raise TypeError("direction must be a FeasibilityDirection")
        if not isinstance(self.grade, FeasibilityGrade):
            raise TypeError("grade must be a FeasibilityGrade")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")

    @property
    def is_known(self) -> bool:
        return self.direction is not FeasibilityDirection.UNKNOWN


def feasibility_of_step(
    step: ExperimentStep, *, thermo: ThermoTable = DEFAULT_THERMO, temperature_k: float | None = None
) -> StepFeasibility:
    """The DERIVED ΔG feasibility verdict for one step, over sourced thermodynamic data.

    ``temperature_k`` overrides the reaction temperature (default: the step's declared envelope midpoint, or
    the 298.15 K reference).  A species with no sourced ΔfH°/S° makes the whole verdict UNKNOWN -- loud, never
    a fabricated ΔG.
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    temperature = temperature_k if temperature_k is not None else _temperature_of(step)
    species, nu = _coefficient_vector(step)
    resolved = [(m, n, resolve_thermo(m, thermo)) for m, n in zip(species, nu)]
    missing = tuple(_label(m) for m, _n, r in resolved if r is None)
    if missing:
        return StepFeasibility(
            FeasibilityDirection.UNKNOWN, FeasibilityGrade.UNKNOWN, None, None, None, None,
            f"UNKNOWN: no sourced thermodynamic data for {', '.join(sorted(set(missing)))}; ΔG cannot be "
            f"computed (inject sourced ΔfH°/S° to close this gap)",
            unknown("delta-G-rxn", "kJ/mol", "a reactant/product has no sourced formation enthalpy/entropy"),
            missing,
        )

    # nu is signed reactant(+)/product(-), so ΔX_rxn = products - reactants = -Σ nu_i X_i
    delta_h = -sum(n * r.dhf_kj_per_mol for _m, n, r in resolved)
    delta_s = -sum(n * r.s_j_per_mol_k for _m, n, r in resolved)
    delta_g = delta_h - temperature * delta_s / 1000.0  # S in J/K -> kJ/K

    grade = (
        FeasibilityGrade.DERIVED
        if abs(temperature - REFERENCE_TEMPERATURE_K) <= NEAR_REFERENCE_K
        else FeasibilityGrade.PREDICTED
    )
    if abs(delta_g) < BORDERLINE_KJ:
        direction = FeasibilityDirection.BORDERLINE
    elif delta_g < 0:
        direction = FeasibilityDirection.FAVORABLE
    else:
        direction = FeasibilityDirection.UNFAVORABLE

    extrap = "" if grade is FeasibilityGrade.DERIVED else (
        " [PREDICTED: extrapolated from the 298.15 K reference via constant ΔH/ΔS]"
    )
    disfavour = "" if direction is not FeasibilityDirection.UNFAVORABLE else (
        " (endergonic in this direction at standard state -- disfavored, NOT impossible: coupling / "
        "non-standard conditions / product removal can still drive it)"
    )
    reason = (
        f"{direction.value}: ΔG = {delta_g:.1f} kJ/mol at {temperature:.1f} K "
        f"(ΔH = {delta_h:.1f} kJ, ΔS = {delta_s:.1f} J/K; Hess's law + Gibbs over sourced formation data)"
        f"{disfavour}{extrap} -- thermodynamic feasibility, not a rate"
    )
    finding = Quantity(
        "delta-G-rxn", f"{delta_g:.1f}", "kJ/mol", Bucket.KNOWN_SOURCED,
        f"{grade.value} via Hess's law + ΔG=ΔH-TΔS (established) over sourced ΔfH°/S° at {temperature:.1f} K",
    )
    return StepFeasibility(
        direction, grade, temperature, delta_h, delta_s, delta_g, reason, finding, (),
    )


@dataclass(frozen=True)
class RouteFeasibility(Digestible):
    """The thermodynamic feasibility of a whole route: one :class:`StepFeasibility` per step, and a verdict.

    Verdict precedence (honest, not optimistic): a sourced ``UNFAVORABLE`` step dominates; then any
    ``UNKNOWN`` (missing data) keeps the route from a clean favorable read; then ``BORDERLINE``; a route is
    ``FAVORABLE`` only when every step is favorable.
    """

    route: ExperimentRoute
    per_step: tuple[StepFeasibility, ...]

    def __post_init__(self) -> None:
        if type(self.route) is not ExperimentRoute:
            raise TypeError("route must be an ExperimentRoute")
        if type(self.per_step) is not tuple or any(type(s) is not StepFeasibility for s in self.per_step):
            raise TypeError("per_step must be a tuple of StepFeasibility values")
        if len(self.per_step) != len(self.route.steps):
            raise ValueError(f"expected {len(self.route.steps)} step feasibilities, got {len(self.per_step)}")

    @property
    def verdict(self) -> str:
        d = [s.direction for s in self.per_step]
        if any(x is FeasibilityDirection.UNFAVORABLE for x in d):
            return "UNFAVORABLE"
        if any(x is FeasibilityDirection.UNKNOWN for x in d):
            return "UNKNOWN"
        if any(x is FeasibilityDirection.BORDERLINE for x in d):
            return "BORDERLINE"
        return "FAVORABLE"

    def explain(self) -> str:
        lines = [f"feasibility (thermodynamic ΔG): {self.verdict}"]
        for idx, s in enumerate(self.per_step):
            lines.append(f"  step {idx + 1}: {s.reason}")
        return "\n".join(lines)


def verify_feasibility(
    route: ExperimentRoute, *, thermo: ThermoTable = None, temperature_k: float | None = None
) -> RouteFeasibility:
    """The thermodynamic feasibility of every step of a route, over the sourced (injectable) thermo table."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    tbl = DEFAULT_THERMO if thermo is None else thermo
    per_step = tuple(feasibility_of_step(s, thermo=tbl, temperature_k=temperature_k) for s in route.steps)
    return RouteFeasibility(route, per_step)
