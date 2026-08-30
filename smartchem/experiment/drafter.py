"""E4 -- the procedure drafter and the constraint fitter (the compiler's backend).

Two capstone jobs, both composing E1-E3 and the equipment layer, both under one banner: what comes out is a
COMPOSED, EVIDENCE-GRADED DRAFT over known chemistry -- not a guarantee of a successful synthesis.  Every
claim it makes wears its grade and envelope; it never contradicts a sourced fact and never invents a law.

* **:func:`draft_procedure`** turns a route into the human-readable draft a chemist reads: per-step balanced
  equation, the sourced/UNKNOWN physical accounting (E3), the standard apparatus (the "Bunsen and flasks"
  click), the composability verdict (E1), and -- given charged amounts -- the propagated 100%-efficiency
  ceiling (E2).  Every number wears its bucket, so a chemist can act on what is KNOWN and see exactly where
  the gaps are.

* **the constraint fitter** (:func:`fit_routes` / :func:`rank_routes`) is a compiler backend with a
  TARGET-MACHINE description: a :class:`ConstraintBox` names the bench -- a maximum temperature (a burner
  that only reaches 1200 C), a pressure ceiling (no chemistry above 1.5 bar), the reagents and equipment on
  hand -- and the fitter selects the routes that RUN on that bench and refuses the ones that do not, citing
  the exact bound each violated.  A route whose steps declare conditions outside the box is ``EXCLUDED``; a
  route that cannot be confirmed to fit (an undeclared dimension the box constrains, or a composability gap)
  is ``UNKNOWN`` -- never silently "fits"; a route within the box and composable is ``FITS``.  Ranking floats
  ``FITS`` + sourced above ``UNKNOWN`` above ``EXCLUDED``/``DEGENERATE`` -- exactly as ``evidence_ranking``
  floats a sourced edge above an unranked one.

Universal: any route of certified steps flows through; unsourced dimensions surface as ``UNKNOWN``, never a
crash and never a guess.
"""
from __future__ import annotations

import numbers
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction  # noqa: F401  (used in a string type annotation)
from typing import Mapping

from ..category import Molecule
from ..contracts import Digestible
from ..decompiler import Formula
from ..structure import resolve_structure
from .accounting import PhysicalAccounting, account_route
from .bucket import Bucket
from .ceiling import RouteCeiling, route_ceiling
from .composability import Composability, verify_composability
from .equilibrium import RouteEquilibrium, verify_equilibrium
from .equipment import EquipmentItem, EquipmentKind, equipment_for_step
from .feasibility import RouteFeasibility, verify_feasibility
from .selectivity import RouteSelectivity, SelectivityTable, verify_selectivity
from .step import ExperimentRoute

__all__ = [
    "ConstraintBox",
    "RouteFitStatus",
    "RouteFit",
    "DraftedProcedure",
    "draft_procedure",
    "fit_routes",
    "rank_routes",
]

DRAFT_BANNER = (
    "DRAFT -- a composed, evidence-graded synthesis over known chemistry. NOT a predicted successful "
    "synthesis: it is no guarantee the reaction succeeds, and it asserts no reaction RATE or "
    "time-to-completion (the repo carries no established kinetics model). Every claim it DOES make -- "
    "selectivity, feasibility, the equilibrium extent, the conservation ceiling, sourced conditions -- wears "
    "its epistemic grade and envelope; UNKNOWN marks a genuine gap, never a cleared one, and nothing here "
    "contradicts a sourced fact or invents a law."
)


def _names_of(molecule: Molecule) -> frozenset[str]:
    """The identifiers a molecule can be matched against a reagent inventory by: its formula and any names."""
    ids = {repr(Formula.of(molecule.formula, molecule.charge))}
    named = resolve_structure(molecule)
    if named is not None:
        ids.update(named.all_names)
    return frozenset(ids)


@dataclass(frozen=True)
class ConstraintBox(Digestible):
    """A target-bench description: what temperatures, pressures, reagents and equipment are available.

    Any bound left ``None`` is unconstrained.  ``available_reagents`` is a set of formula strings and/or
    names a step's reactants are matched against (``None`` = every reagent available); ``available_equipment``
    is the set of :class:`~smartchem.experiment.equipment.EquipmentKind` the bench has (``None`` = every kind
    available).
    """

    max_temperature_k: float | None = None
    min_pressure_atm: float | None = None
    max_pressure_atm: float | None = None
    available_reagents: frozenset[str] | None = None
    available_equipment: frozenset[EquipmentKind] | None = None

    def __post_init__(self) -> None:
        for name in ("max_temperature_k", "min_pressure_atm", "max_pressure_atm"):
            v = getattr(self, name)
            if v is not None and (isinstance(v, bool) or not isinstance(v, numbers.Real)):
                raise TypeError(f"{name} must be a real number or None")
        if self.available_reagents is not None and type(self.available_reagents) is not frozenset:
            raise TypeError("available_reagents must be a frozenset of strings or None")
        if self.available_equipment is not None and type(self.available_equipment) is not frozenset:
            raise TypeError("available_equipment must be a frozenset of EquipmentKind or None")


class RouteFitStatus(str, Enum):
    FITS = "FITS"          # within the box on every declared dimension, and composable
    UNKNOWN = "UNKNOWN"    # cannot be confirmed to fit (undeclared constrained dimension, or a comp. gap)
    EXCLUDED = "EXCLUDED"  # exceeds a hard bound of the box, or the route is degenerate


@dataclass(frozen=True)
class RouteFit(Digestible):
    """Whether one route runs on the target bench, with the exact reasons and its composability."""

    route: ExperimentRoute
    status: RouteFitStatus
    exclusions: tuple[str, ...]   # hard box violations / degeneracy
    gaps: tuple[str, ...]         # undeclared constrained dimensions / composability UNKNOWNs
    composability: Composability
    selectivity: RouteSelectivity  # which isomer each step makes (sourced regiochemistry, or a loud gap)
    feasibility: RouteFeasibility  # thermodynamic ΔG verdict per step (DERIVED, or a loud UNKNOWN)
    equilibrium: RouteEquilibrium  # equilibrium extent K=exp(-ΔG/RT) per step (DERIVED, or a loud UNKNOWN)

    @property
    def fits(self) -> bool:
        return self.status is RouteFitStatus.FITS

    def explain(self) -> str:
        lines = [f"route fit: {self.status.value}"]
        for e in self.exclusions:
            lines.append(f"  EXCLUDED: {e}")
        for g in self.gaps:
            lines.append(f"  GAP: {g}")
        if self.selectivity.verdict != "NOT_APPLICABLE":
            lines.append(f"  SELECTIVITY: {self.selectivity.verdict}")
        if self.feasibility.verdict != "UNKNOWN":
            lines.append(f"  FEASIBILITY: {self.feasibility.verdict}")
        if self.equilibrium.verdict != "UNKNOWN":
            lines.append(f"  EQUILIBRIUM: {self.equilibrium.verdict}")
        return "\n".join(lines)


def _step_box_check(step, box: ConstraintBox, equip: tuple[EquipmentItem, ...],
                    idx: int) -> tuple[list[str], list[str]]:
    """(exclusions, gaps) for one step against the box.  A hard over-bound excludes; an undeclared
    dimension the box constrains is a gap (cannot confirm fit), never a silent pass."""
    exclusions: list[str] = []
    gaps: list[str] = []
    env = step.envelope
    tag = f"step {idx + 1}"

    if box.max_temperature_k is not None:
        if env.temperature is None:
            gaps.append(f"{tag}: temperature undeclared, but the bench caps at {box.max_temperature_k} K")
        elif env.temperature.hi > box.max_temperature_k:
            exclusions.append(
                f"{tag}: needs up to {env.temperature.hi} K but the bench caps at {box.max_temperature_k} K"
            )
    if box.max_pressure_atm is not None:
        if env.pressure is None:
            gaps.append(f"{tag}: pressure undeclared, but the bench caps at {box.max_pressure_atm} atm")
        elif env.pressure.hi > box.max_pressure_atm:
            exclusions.append(
                f"{tag}: needs up to {env.pressure.hi} atm but the bench caps at {box.max_pressure_atm} atm"
            )
    if box.min_pressure_atm is not None and env.pressure is not None \
            and env.pressure.lo < box.min_pressure_atm:
        exclusions.append(
            f"{tag}: needs down to {env.pressure.lo} atm but the bench floor is {box.min_pressure_atm} atm"
        )

    if box.available_reagents is not None:
        for r in step.reactants:
            if not (_names_of(r) & box.available_reagents):
                exclusions.append(f"{tag}: reactant {r!r} is not in the available-reagent inventory")

    if box.available_equipment is not None:
        for item in equip:
            if item.bucket is Bucket.UNKNOWN:
                gaps.append(f"{tag}: equipment undetermined (no declared conditions)")
            elif item.kind not in box.available_equipment:
                exclusions.append(
                    f"{tag}: needs {item.name} ({item.kind.value.lower()}), not available on this bench"
                )
    return exclusions, gaps


def fit_route(
    route: ExperimentRoute, box: ConstraintBox, *,
    stability=None, selectivity: SelectivityTable | None = None, thermo=None,
) -> RouteFit:
    """Judge whether one route runs on the target bench described by ``box``."""
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    comp = verify_composability(route) if stability is None else verify_composability(route, stability=stability)
    sel = verify_selectivity(route, table=selectivity)
    feas = verify_feasibility(route, thermo=thermo)
    equi = verify_equilibrium(route, thermo=thermo)

    exclusions: list[str] = []
    gaps: list[str] = []
    if comp.is_degenerate:
        exclusions.extend(f"degenerate: {r}" for r in comp.degenerate_reasons)
    gaps.extend(f"composability gap: {g}" for g in comp.gaps)

    for idx, step in enumerate(route.steps):
        equip = equipment_for_step(step)
        ex, gp = _step_box_check(step, box, equip, idx)
        exclusions.extend(ex)
        gaps.extend(gp)

    if exclusions:
        status = RouteFitStatus.EXCLUDED
    elif gaps:
        status = RouteFitStatus.UNKNOWN
    else:
        status = RouteFitStatus.FITS
    return RouteFit(route, status, tuple(exclusions), tuple(gaps), comp, sel, feas, equi)


def fit_routes(
    routes, box: ConstraintBox, *,
    stability=None, selectivity: SelectivityTable | None = None, thermo=None,
) -> tuple[RouteFit, ...]:
    """Judge every route against the bench ``box`` (order preserved)."""
    return tuple(
        fit_route(r, box, stability=stability, selectivity=selectivity, thermo=thermo) for r in routes
    )


def _route_score(fit: RouteFit) -> tuple:
    """Sort key, lower = better: excluded worst, then composability, then three sourced thermochemical tiers.

    Three sourced correctness tiebreakers ride after composability. Selectivity: a sourced-FAVORED route (it
    makes the major isomer) floats above an unresolved one, above a sourced-DISFAVORED one. Feasibility: a
    thermodynamically FAVORABLE route (ΔG < 0) floats above a borderline/unknown one, above an UNFAVORABLE one
    (ΔG > 0). Equilibrium (the finer magnitude tiebreaker after feasibility's sign): a route that runs
    ESSENTIALLY_COMPLETE at equilibrium floats above a partial one, above one whose equilibrium is NEGLIGIBLE.
    All three are neutral on ignorance -- we reward a sourced positive and penalize a sourced negative, never
    a gap.
    """
    status_rank = {RouteFitStatus.FITS: 0, RouteFitStatus.UNKNOWN: 1, RouteFitStatus.EXCLUDED: 2}
    comp_rank = {"COMPOSABLE": 0, "SINGLE_STEP": 1, "UNKNOWN": 2, "DEGENERATE": 3}
    sel_rank = {"FAVORED": 0, "NOT_APPLICABLE": 1, "UNKNOWN": 1, "DISFAVORED": 2}
    feas_rank = {"FAVORABLE": 0, "BORDERLINE": 1, "UNKNOWN": 1, "UNFAVORABLE": 2}
    eq_rank = {"ESSENTIALLY_COMPLETE": 0, "FAVORABLE": 1, "BALANCED": 2, "UNKNOWN": 2,
               "LIMITED": 3, "NEGLIGIBLE": 4}
    return (
        status_rank[fit.status],
        comp_rank.get(fit.composability.verdict, 4),
        sel_rank.get(fit.selectivity.verdict, 1),
        feas_rank.get(fit.feasibility.verdict, 1),
        eq_rank.get(fit.equilibrium.verdict, 2),
        len(fit.gaps),
        len(fit.exclusions),
    )


def rank_routes(
    routes, box: ConstraintBox | None = None, *,
    stability=None, selectivity: SelectivityTable | None = None, thermo=None,
) -> tuple[RouteFit, ...]:
    """Rank routes best-first for a bench (or, with ``box=None``, an unconstrained bench).

    The north-star litmus: given several candidate routes to the same target, float the ones that FIT and
    are COMPOSABLE and sourced above those with UNKNOWN gaps above those EXCLUDED or DEGENERATE -- and, among
    otherwise-comparable routes, the one whose steps make the SOURCED major isomer and are thermodynamically
    FAVORABLE above those that make the minor isomer or are endergonic -- surfacing what is runnable-and-known.
    """
    effective_box = box if box is not None else ConstraintBox()
    fits = fit_routes(routes, effective_box, stability=stability, selectivity=selectivity, thermo=thermo)
    return tuple(sorted(fits, key=_route_score))


@dataclass(frozen=True)
class DraftedProcedure(Digestible):
    """The full human-readable draft of a route: equations + accounting + equipment + composability + ceiling."""

    route: ExperimentRoute
    composability: Composability
    accounting: PhysicalAccounting
    equipment: tuple[tuple[EquipmentItem, ...], ...]   # one tuple per step
    ceiling: RouteCeiling | None
    selectivity: RouteSelectivity  # which isomer each step makes (sourced regiochemistry, or a loud gap)
    feasibility: RouteFeasibility  # thermodynamic ΔG verdict per step (DERIVED, or a loud UNKNOWN)
    equilibrium: RouteEquilibrium  # equilibrium extent K=exp(-ΔG/RT) per step (DERIVED, or a loud UNKNOWN)

    def render(self) -> str:
        lines = [DRAFT_BANNER, "", f"TARGET: {self.route.final_target!r}", ""]
        for idx, step in enumerate(self.route.steps):
            lines.append(f"STEP {idx + 1}: {step.equation()}")
            for q in self.accounting.per_step[idx].quantities():
                lines.append(f"    {q.render()}")
            lines.append(f"    {self.feasibility.per_step[idx].finding.render()}")
            eq = self.equilibrium.per_step[idx]
            lines.append(f"    {eq.k_finding.render()}")
            if eq.conversion_fraction is not None:
                lines.append(f"    {eq.conversion_finding.render()}")
            sel = self.selectivity.per_step[idx]
            if sel.status.value != "NOT_APPLICABLE":
                lines.append(f"    {sel.finding.render()}")
            lines.append("    equipment:")
            for item in self.equipment[idx]:
                lines.append(f"      - {item.render()}")
            lines.append("")
        lines.append(self.composability.explain())
        lines.append("")
        lines.append(self.feasibility.explain())
        lines.append("")
        lines.append(self.equilibrium.explain())
        if self.selectivity.verdict != "NOT_APPLICABLE":
            lines.append("")
            lines.append(self.selectivity.explain())
        if self.ceiling is not None:
            lines.append("")
            lines.append(self.ceiling.explain())
        return "\n".join(lines)


def draft_procedure(
    route: ExperimentRoute,
    feed: Mapping[Molecule, "int | Fraction"] | None = None,
    *,
    stability=None,
    selectivity: SelectivityTable | None = None,
    thermo=None,
) -> DraftedProcedure:
    """Compose the full drafted procedure for a route: E1 composability, E3 accounting, equipment, E2 ceiling,
    the sourced regiochemical selectivity (which isomer each step makes), the DERIVED thermodynamic
    feasibility (ΔG per step), and the DERIVED equilibrium extent (M2: K = exp(-ΔG/RT) per step).

    ``feed`` (external reactant amounts in mol) turns on the propagated 100%-efficiency ceiling; omit it to
    skip the outcome bound.  ``stability`` / ``selectivity`` / ``thermo`` optionally extend the sourced data
    for any chemical (``thermo`` feeds both the ΔG feasibility and the equilibrium K).
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    comp = verify_composability(route) if stability is None else verify_composability(route, stability=stability)
    sel = verify_selectivity(route, table=selectivity)
    feas = verify_feasibility(route, thermo=thermo)
    equi = verify_equilibrium(route, thermo=thermo)
    accounting = account_route(route)
    equipment = tuple(equipment_for_step(s) for s in route.steps)
    ceiling = None
    if feed is not None:
        ceiling = route_ceiling(route, feed)
    return DraftedProcedure(route, comp, accounting, equipment, ceiling, sel, feas, equi)
