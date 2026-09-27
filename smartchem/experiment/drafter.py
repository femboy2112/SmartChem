"""E4 -- the route-dossier renderer and constraint fitter (the compiler's backend).

Two capstone jobs, both composing E1-E3 and the equipment layer, both under one banner: what comes out is a
COMPOSED, EVIDENCE-GRADED DRAFT over known chemistry -- not a guarantee of a successful synthesis.  Every
claim it makes wears its grade and envelope; it never contradicts a sourced fact and never invents a law.

* **:func:`draft_route_dossier`** turns a route into the human-readable evidence dossier a chemist reviews:
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
  is ``UNKNOWN`` -- never silently "fits"; a route within a box that actually constrains something is
  ``FITS``; and a route judged against an EMPTY box (no bench constraint at all) is ``UNCONSTRAINED`` --
  nothing was assessed, so it is NOT a pass (standard section 11: ``UNCONSTRAINED`` MUST NOT render as
  ``FITS``).  Ranking floats ``FITS`` + sourced above ``UNKNOWN`` above ``EXCLUDED``/``DEGENERATE`` -- exactly
  as ``evidence_ranking`` floats a sourced edge above an unranked one.

Universal: any route of certified steps flows through; unsourced dimensions surface as ``UNKNOWN``, never a
crash and never a guess.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction  # noqa: F401  (used in a string type annotation)
from typing import Mapping

from ..category import Molecule
from ..constraints import PhysicalBounds
from ..process_constraints import ProcessBounds, evaluate_process
from ..contracts import Digestible
from ..data.kinetics import KineticTable
from ..decompiler import Formula
from ..structure import resolve_structure
from .accounting import PhysicalAccounting, account_route
from .bond_enthalpy import disconnection_favorability_rank
from .bucket import Bucket
from .ceiling import RouteCeiling, route_ceiling
from .composability import Composability, verify_composability
from .equilibrium import RouteEquilibrium, verify_equilibrium
from .equipment import EquipmentItem, EquipmentKind, equipment_for_step
from .feasibility import RouteFeasibility, verify_feasibility
from .functorial_physics import PhysicsProduct, route_net_delta_g
from .handling import RouteHandling, verify_handling
from .kinetics import RouteKinetics, verify_kinetics
from .order import non_dominated_layers
from .readiness import PROCESS_SPECIFIED, ObligationStatus, RouteReadiness, evaluate_route
from .selectivity import RouteSelectivity, SelectivityTable, verify_selectivity
from .step import ExperimentRoute

__all__ = [
    "ConstraintBox",
    "RouteFitStatus",
    "RouteFit",
    "ProcedureReadiness",
    "RouteDossier",
    "draft_route_dossier",
    "DraftedProcedure",
    "draft_procedure",
    "fit_routes",
    "rank_routes",
]

DRAFT_BANNER = (
    "ROUTE EVIDENCE DOSSIER -- a composed, evidence-graded formal candidate. NOT a predicted successful "
    "synthesis: it is no guarantee the reaction succeeds, and it asserts no reaction RATE or "
    "time-to-completion (the repo carries no established kinetics model). Every claim it DOES make -- "
    "selectivity, feasibility, the equilibrium extent, the conservation ceiling, sourced conditions -- wears "
    "its epistemic grade and envelope; UNKNOWN marks a genuine gap, never a cleared one, and nothing here "
    "contradicts a sourced fact or invents a law."
)


class ProcedureReadiness(str, Enum):
    """Legacy bench-readiness vocabulary -- kept for import back-compat only, NOT what
    :class:`RouteDossier` reports anymore.

    Pre-0.8, this was the whole story, and ``RouteDossier.readiness`` returned a hard-coded
    ``FORMAL_CANDIDATE`` no route could ever earn or lose (the READY-TIER-01 wall). v0.8 Real Route
    Dossiers replaces that wall with the shared, DERIVED obligation ladder in
    :mod:`smartchem.experiment.readiness` (``evaluate_route`` / ``RouteReadiness``) -- one engine,
    read here and by ``smartchem.service`` alike, never a second vocabulary invented locally. This
    enum's four values don't even line up with that ladder's tiers (``REACTION_VOUCHED`` /
    ``CONDITIONS_SUPPORTED`` / ``PROCESS_SPECIFIED`` have no member here), which is the tell that it
    was always a placeholder, not a real progression. Left defined so nothing that still imports it
    breaks; do not grow it further and do not wire it back onto ``RouteDossier``.
    """

    FORMAL_CANDIDATE = "FORMAL_CANDIDATE"
    LITERATURE_SUPPORTED = "LITERATURE_SUPPORTED"
    BENCH_DRAFT = "BENCH_DRAFT"
    BLOCKED = "BLOCKED"


_MISSING_BENCH_FIELDS = (
    "scale and material amounts/assays",
    "addition order and rate, agitation, and endpoint",
    "quench, workup, isolation, purification, and analytical acceptance",
    "waste routing, equipment ratings, and experiment-specific emergency controls",
)


def _names_of(molecule: Molecule) -> frozenset[str]:
    """The identifiers a molecule can be matched against a reagent inventory by: its formula and any names."""
    ids = {repr(Formula.of(molecule.formula, molecule.charge))}
    named = resolve_structure(molecule)
    if named is not None:
        ids.update(named.all_names)
    return frozenset(ids)


def _chemist_label(molecule: Molecule) -> str:
    formula = repr(Formula.of(molecule.formula, molecule.charge))
    named = resolve_structure(molecule)
    if named is None:
        return formula
    details = [named.name, formula]
    if named.iupac and named.iupac.casefold() != named.name.casefold():
        details.append(f"IUPAC {named.iupac}")
    if named.cas:
        details.append(f"CAS {named.cas}")
    return " | ".join(details)


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
    process: ProcessBounds = field(default_factory=ProcessBounds.unconstrained)

    def __post_init__(self) -> None:
        if type(self.process) is not ProcessBounds:
            raise TypeError("process must be a ProcessBounds")
        # CONSTR-VAL-01 T/P validation is delegated to the shared PhysicalBounds leaf (CLI-CAN-02): the
        # finite/positive/ordered rules live in ONE place, and constructing it raises the identical
        # TypeError/ValueError.  ConstraintBox keeps its flat fields, so its digest and every consumer are unchanged.
        PhysicalBounds.of(
            max_temperature_k=self.max_temperature_k,
            min_pressure_atm=self.min_pressure_atm,
            max_pressure_atm=self.max_pressure_atm,
        )
        if self.available_reagents is not None and type(self.available_reagents) is not frozenset:
            raise TypeError("available_reagents must be a frozenset of strings or None")
        if self.available_equipment is not None and type(self.available_equipment) is not frozenset:
            raise TypeError("available_equipment must be a frozenset of EquipmentKind or None")

    @property
    def physical_bounds(self) -> PhysicalBounds:
        """The section-11 T/P bounds as the shared :class:`~smartchem.constraints.PhysicalBounds` leaf."""
        return PhysicalBounds.of(
            max_temperature_k=self.max_temperature_k,
            min_pressure_atm=self.min_pressure_atm,
            max_pressure_atm=self.max_pressure_atm,
        )

    @classmethod
    def of_bounds(cls, bounds: PhysicalBounds, process: ProcessBounds | None = None) -> "ConstraintBox":
        """A bench box carrying only the shared section-11 T/P ``bounds`` (no reagent/equipment inventory).

        The ONE place a :class:`~smartchem.constraints.PhysicalBounds` becomes a bench box, so the service's
        ranked dossiers and the ``compile`` dossier fit against a byte-identical box (CLI-CAN-02 brick 2; the
        inverse of :attr:`physical_bounds`)."""
        return cls(
            max_temperature_k=bounds.max_temperature_k,
            min_pressure_atm=bounds.min_pressure_atm,
            max_pressure_atm=bounds.max_pressure_atm,
            process=process if process is not None else ProcessBounds.unconstrained(),
        )

    @property
    def constrains_anything(self) -> bool:
        """True iff the box declares at least one real bench constraint.

        An all-``None`` box constrains nothing; a route judged against it is ``UNCONSTRAINED`` (nothing was
        assessed), never ``FITS`` (standard section 11: ``UNCONSTRAINED`` MUST NOT render as a pass).
        """
        return self.process.constrains_anything or any(
            getattr(self, name) is not None
            for name in ("max_temperature_k", "min_pressure_atm", "max_pressure_atm",
                         "available_reagents", "available_equipment")
        )


class RouteFitStatus(str, Enum):
    # NOTE: the standard (section 11) names these ASSESSED_FIT / UNKNOWN_FIT / UNCONSTRAINED / EXCLUDED / BLOCKED;
    # SmartChem keeps the shorter FITS/UNKNOWN names for now (a user-visible rename is deferred to the shared-
    # response work under the section 18 migration-alias discipline). BLOCKED belongs to the readiness/safety
    # layer and is not modeled here yet.
    FITS = "FITS"                    # a box that ACTUALLY constrains something, and the route is within it everywhere declared
    UNKNOWN = "UNKNOWN"              # cannot be confirmed to fit (undeclared constrained dimension, or a comp. gap)
    EXCLUDED = "EXCLUDED"            # exceeds a hard bound of the box, or the route is degenerate
    UNCONSTRAINED = "UNCONSTRAINED"  # the bench box declares NO constraint -- nothing to fit, so NOT a pass (section 11)


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
    kinetics: RouteKinetics        # rate regime per step (bottleneck-dominated); ranking-only, NEVER a grade

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
        if self.kinetics.verdict != "UNKNOWN":
            lines.append(f"  RATE: {self.kinetics.verdict}")
        return "\n".join(lines)


def _step_box_check(step, box: ConstraintBox, equip: tuple[EquipmentItem, ...],
                    idx: int) -> tuple[list[str], list[str]]:
    """(exclusions, gaps) for one step against the box.  A hard over-bound excludes; an undeclared
    dimension the box constrains is a gap (cannot confirm fit), never a silent pass."""
    exclusions: list[str] = []
    gaps: list[str] = []
    env = step.envelope
    tag = f"step {idx + 1}"

    # Reaction conditions alone cannot bound a hotter workup or a vacuum isolation.
    # With operator process limits, require extrema over the whole operation set.
    if box.process.constrains_anything:
        requirements = env.process
        for name, op, label in (
            ("max_temperature_k", "max", "peak_temperature_k"),
            ("min_pressure_atm", "min", "min_pressure_atm"),
            ("max_pressure_atm", "max", "max_pressure_atm"),
        ):
            bound = getattr(box, name)
            if bound is None:
                continue
            value = None if requirements is None else getattr(requirements, label)
            if value is None:
                gaps.append(f"{tag}: whole-process {label} including workup is undeclared")
            elif (op == "max" and value > bound) or (op == "min" and value < bound):
                exclusions.append(f"{tag}: whole-process {label} {value:g} violates {name} {bound:g}")

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
    if box.min_pressure_atm is not None:
        # The floor gets the SAME undeclared-dimension GAP the two ceilings above have (red-team HIGH fold): a route
        # whose step leaves pressure undeclared cannot be CONFIRMED to sit above a pressure floor, so it is a GAP
        # (UNKNOWN-fit), never a silent FITS on a constrained dimension (section 11).
        if env.pressure is None:
            gaps.append(f"{tag}: pressure undeclared, but the bench floor is {box.min_pressure_atm} atm")
        elif env.pressure.lo < box.min_pressure_atm:
            exclusions.append(
                f"{tag}: needs down to {env.pressure.lo} atm but the bench floor is {box.min_pressure_atm} atm"
            )

    if box.available_reagents is not None:
        for r in step.reactants:
            formula = repr(Formula.of(r.formula, r.charge))
            names = _names_of(r) - {formula}
            if names & box.available_reagents:
                continue  # a registered name identifies this exact constitutional structure
            if formula in box.available_reagents:
                gaps.append(
                    f"{tag}: reactant {r!r} matches only formula {formula} in the available-reagent "
                    "inventory; structural identity is unresolved (a formula does not identify an isomer)"
                )
            else:
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
    kinetics: KineticTable | None = None, losses: tuple = (), phases: "dict[Molecule, str] | None" = None,
) -> RouteFit:
    """Judge whether one route runs on the target bench described by ``box``.

    ``losses`` (EVD-KEY-01): a section-5.3 BLOCKER downgrades the sourced selectivity/kinetics verdicts feeding the
    ranking, so a loss-bearing target never floats on a sourced verdict the dropped feature forbids.

    ``phases`` (ITEM5-PHASE-RANK-01): the optional ``{Molecule: "gas"|"liquid"|...}`` phase declaration is forwarded
    to :func:`verify_feasibility` (default ``None``, byte-stable for single-phase routes), so a route carrying a
    dual-phase species (e.g. Br2, liquid ΔfH°=0 vs gas +30.91) is scored on the DECLARED phase rather than fail-closed
    to UNKNOWN.  This threads BOTH the worst-node feasibility SIGN and the additive net-ΔG magnitude the ranker reads
    (``feasibility.net_delta_g_kj`` is a property over these per-step results).  The equilibrium axis is deliberately
    NOT phase-threaded (``verify_equilibrium`` has no ``phases``): a dual-phase species fail-closes its equilibrium
    extent to UNKNOWN, the same sound R37 boundary that made only feasibility phase-aware.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    comp = verify_composability(route) if stability is None else verify_composability(route, stability=stability)
    sel = verify_selectivity(route, table=selectivity, losses=losses)
    feas = verify_feasibility(route, thermo=thermo, phases=phases)
    equi = verify_equilibrium(route, thermo=thermo)
    kin = verify_kinetics(route, kinetics=kinetics, losses=losses)  # ORTHOGONAL rate; ranking tiebreaker only

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

    process_fit = evaluate_process(tuple(step.envelope for step in route.steps), box.process)
    exclusions.extend(process_fit.exclusions)
    gaps.extend(process_fit.gaps)

    if exclusions:
        status = RouteFitStatus.EXCLUDED
    elif gaps:
        status = RouteFitStatus.UNKNOWN
    elif box.constrains_anything:
        status = RouteFitStatus.FITS
    else:
        # an empty box constrains nothing, so there is nothing to fit: UNCONSTRAINED, never a silent FITS
        # (FIT-SEM-01; standard section 11).  The route's composability/thermo verdicts still ride along.
        status = RouteFitStatus.UNCONSTRAINED
    return RouteFit(route, status, tuple(exclusions), tuple(gaps), comp, sel, feas, equi, kin)


def fit_routes(
    routes, box: ConstraintBox, *,
    stability=None, selectivity: SelectivityTable | None = None, thermo=None,
    kinetics: KineticTable | None = None, losses: tuple = (), phases: "dict[Molecule, str] | None" = None,
) -> tuple[RouteFit, ...]:
    """Judge every route against the bench ``box`` (order preserved).  ``phases`` (ITEM5-PHASE-RANK-01) is forwarded
    verbatim to each :func:`fit_route` (each route's feasibility filters the dict to its own species)."""
    return tuple(
        fit_route(r, box, stability=stability, selectivity=selectivity, thermo=thermo, kinetics=kinetics,
                  losses=losses, phases=phases)
        for r in routes
    )


@dataclass(frozen=True)
class DAGBenchFit:
    """Whether one convergent DAG runs on the target bench: the COMBINED section-11 verdict (DAG-BENCH-01).

    The convergent analogue of :class:`RouteFit`, composed from the SAME three axes a linear ``fit_route``
    combines, only re-shaped for a DAG: E1 composability across every producer->consumer EDGE
    (:func:`~smartchem.experiment.dag.dag_composability`, degeneracy excludes / an UNKNOWN handoff is a gap), the
    per-step PHYSICAL box (the identical :func:`_step_box_check` the linear route runs -- a step's T/P/reagent/
    equipment requirement is order-agnostic, so it transfers to a DAG node verbatim), and the CRITICAL-PATH-aware
    PROCESS axis (:func:`~smartchem.experiment.dag.dag_process_fit`, whose FITS is the SERIAL-sum ceiling and so is
    achievable one-step-at-a-time by a single operator -- the concurrency-schedulability boundary bites the UNKNOWN
    band, NEVER a FITS).  ``status`` folds the three exactly as ``fit_route`` does: EXCLUDED if any hard exclusion,
    else UNKNOWN if any gap, else FITS iff the box constrains something, else UNCONSTRAINED.

    BOUNDARY (serial-hold stability, a strengthening over a linear FITS): a convergent-DAG FITS certifies
    serial-achievability on the MODELED axes (time/attention/equipment), but a serial schedule of a convergent DAG
    HOLDS an early branch's intermediate through the full elapsed time of its sibling branches before the join consumes
    it -- a longer hold than any adjacent linear handoff.  ``dag_composability`` (E1) is time-blind (it judges only the
    adjacent-handoff conditions), so that serial-hold stability is UNVERIFIED here; it is unmodeled until the stability
    model grows a time / max-hold axis.  A plain record (not a
    :class:`~smartchem.contracts.Digestible`): it is an internal computation result the thin
    :class:`~smartchem.service.RankedDAGSummary` projects off, never itself a payload term."""

    status: RouteFitStatus
    exclusions: tuple[str, ...]
    gaps: tuple[str, ...]
    composability: object  # DAGComposability (kept off the top-level import to preserve the drafter->dag one-way edge)
    # DAG-THERMO-01: the four SOURCED per-reaction thermochemical verdicts, aggregated worst-node-dominated over the
    # DAG's nodes (:func:`~smartchem.experiment.dag.dag_thermo_rollup`), reaching parity with RouteFit's sel/feas/eq/kin.
    # RANKING-ONLY, never a grade: ``_dag_score`` orders otherwise-tied DAGs on them, but they NEVER change ``status``
    # (exactly as the linear ``fit_route`` leaves ``status`` independent of its thermo verdicts).  Defaulted to the
    # neutral "UNKNOWN" so a hand-built/stub DAGBenchFit stays valid; ``dag_bench_fit`` always computes them for real.
    selectivity_verdict: str = "UNKNOWN"
    feasibility_verdict: str = "UNKNOWN"
    equilibrium_verdict: str = "UNKNOWN"
    kinetics_verdict: str = "UNKNOWN"

    @property
    def fits(self) -> bool:
        return self.status is RouteFitStatus.FITS


def dag_bench_fit(
    dag, box: ConstraintBox, *,
    stability=None, selectivity=None, thermo=None, kinetics=None, losses: tuple = (),
    phases: "dict[Molecule, str] | None" = None,
) -> DAGBenchFit:
    """Judge whether one convergent DAG runs on the target bench ``box`` -- the COMBINED section-11 admission.

    Mirrors :func:`fit_route` axis-for-axis (composability + per-step physical box + process), re-shaped for the
    convergent structure so a DAG is a FIRST-CLASS bench citizen, not a process-axis-only diagnostic (DAG-BENCH-01,
    the named next-step DAG-ADMIT-01 left open).  ``dag_composability``/``dag_process_fit``/``dag_thermo_rollup`` are
    imported LAZILY so ``drafter`` never takes a module-load dependency on ``dag`` (the one-way layering edge; ``dag``
    must not import ``drafter``).

    DAG-THERMO-01: it ALSO computes the four SOURCED per-reaction thermochemical verdicts
    (:func:`~smartchem.experiment.dag.dag_thermo_rollup`, the DAG analogue of the four ``verify_*`` folds
    ``fit_route`` runs) and carries them on the result for :func:`_dag_score` to rank on -- so a DAG ranking is as rich
    as a linear one.  They are RANKING-ONLY: they never enter the ``status`` computation below (a FITS/EXCLUDED/UNKNOWN
    is decided by composability + physical box + process alone, exactly as ``fit_route``'s ``status`` ignores its
    thermo verdicts).  The sourced tables default to their seeds when ``None``, mirroring ``fit_route``."""
    from .dag import SynthesisDAG, dag_composability, dag_process_fit, dag_thermo_rollup
    if type(dag) is not SynthesisDAG:
        raise TypeError("dag must be a SynthesisDAG")
    comp = dag_composability(dag) if stability is None else dag_composability(dag, stability=stability)
    exclusions: list[str] = []
    gaps: list[str] = []
    # E1 composability across the DAG's edges: a degenerate transition is a hard exclude; an UNKNOWN handoff is a gap
    # (never a silent pass) -- the exact split fit_route applies to the linear Composability.
    if comp.is_degenerate:
        exclusions.extend(f"degenerate: {r}" for r in comp.degenerate_reasons)
    gaps.extend(f"composability gap: {g}" for g in comp.gaps)
    # The physical box PER STEP (T/P/reagent/equipment + whole-process extrema) -- order-agnostic, so the DAG's nodes
    # reuse the linear per-step check verbatim.  Disjoint from the process axis below (ProcessBounds carries no T/P).
    for idx, step in enumerate(dag.steps):
        equip = equipment_for_step(step)
        ex, gp = _step_box_check(step, box, equip, idx)
        exclusions.extend(ex)
        gaps.extend(gp)
    # The PROCESS axis, critical-path aware (dag_process_fit): FITS is serial-achievable, so this whole verdict's FITS
    # certificate needs no concurrency -- the joint-single-operator boundary is confined to the UNKNOWN band.
    process_fit = dag_process_fit(dag, box.process)
    exclusions.extend(process_fit.exclusions)
    gaps.extend(process_fit.gaps)

    if exclusions:
        status = RouteFitStatus.EXCLUDED
    elif gaps:
        status = RouteFitStatus.UNKNOWN
    elif box.constrains_anything:
        status = RouteFitStatus.FITS
    else:
        # an empty box constrains nothing, so there is nothing to fit: UNCONSTRAINED, never a silent FITS (section 11).
        status = RouteFitStatus.UNCONSTRAINED
    # DAG-THERMO-01: the four sourced per-reaction thermochemical ranking verdicts (computed AFTER status, and never
    # feeding it -- ranking-only, exactly as fit_route's thermo verdicts never touch its status).  ITEM5-DAG-PHASE-01:
    # ``phases`` reaches ONLY the feasibility fold (equilibrium stays phase-blind, the R37 boundary), so a dual-phase
    # DAG rolls up its feasibility verdict on the DECLARED phase.  It never changes ``status`` above -- a phase can
    # move the feasibility RANKING verdict (and so a DAG ranking's order) but never a FITS/EXCLUDED/UNKNOWN grade.
    rollup = dag_thermo_rollup(dag, selectivity=selectivity, thermo=thermo, kinetics=kinetics, losses=losses,
                               phases=phases)
    return DAGBenchFit(status, tuple(exclusions), tuple(gaps), comp,
                       rollup.selectivity_verdict, rollup.feasibility_verdict,
                       rollup.equilibrium_verdict, rollup.kinetics_verdict)


def _pareto_front_indices(products: "tuple[PhysicsProduct, ...]") -> tuple[int, ...]:
    """The Pareto NON-DOMINATED front (layer) index for each objective -- the M2-FP product order (M2b).

    Complete-objective points (both ``ΔG`` and survival known) are peeled into layers 0, 1, 2, ... by
    non-domination: layer 0 = the non-dominated frontier, layer 1 = non-dominated once layer 0 is removed, and so
    on.  Because a dominator sits in a strictly earlier layer than anything it dominates, this tier is
    domination-MONOTONE -- it never claims a Pareto relation :meth:`PhysicsProduct.dominates` would deny, and two
    INCOMPARABLE complete points share a layer (they do not order each other).

    An INCOMPLETE-objective point (survival ``None`` -- the common case today, since survival needs a sourced
    first-order kinetic record to reach an intermediate) is NEUTRAL: it is assigned layer 0, never penalized
    for the unknown axis (the same "neutral on ignorance" discipline the sourced sign tiers use).  DISCLOSED
    consequence (birdperson design fold): a dominated-but-complete route (layer >= 1) can therefore present
    BELOW an incomplete-objective route (layer 0); this is a data-gated presentation policy, not a dominance
    claim, and it is near-inert today because complete objectives are rare.

    The peel-and-remap itself is the shared :func:`order.non_dominated_layers` primitive (the frontier
    :func:`order.non_dominated_indices`, stratified); this function supplies ONLY the M2-FP product order
    (``a.dominates(b)``) and the completeness eligibility domain (``is_complete`` -- so an incomplete point stays
    at the neutral layer 0, never peeled).  The termination guard and the sub-tuple index REMAP the birdperson
    fold warned about now live, and are tested, in that one primitive instead of hand-rolled here.
    """
    return non_dominated_layers(
        products, lambda a, b: a.dominates(b), eligible=lambda p: p.is_complete
    )


def _score_tuple(
    status: RouteFitStatus, comp_verdict: str, sel_verdict: str, feas_verdict: str, eq_verdict: str,
    kin_verdict: str, n_gaps: int, n_exclusions: int, front_index: int = 0,
    net_delta_g: float | None = None, derived_rank: int = 1,
) -> tuple:
    """The shared 11-tier ranking key (lower = better) for a linear route OR a convergent DAG.

    A linear route (:func:`_route_score`) and its convergent-DAG analogue (:func:`_dag_score`) MUST order by the
    SAME sourced discipline -- the DAG-RANK-01 no-divergence promise.  Historically each carried its OWN verbatim
    copy of the tier dicts + the tuple assembly + the M2b gating, kept in lockstep only by a comment praying they
    stayed in sync (a new tier had to be hand-added to BOTH scorers or the divergence silently reopens -- M2b
    already had to be threaded into both by hand).  This ONE core holds the tiers; the two scorers are now thin
    verdict-EXTRACTORS over it (nested ``fit.selectivity.verdict`` for a route vs flat ``fit.selectivity_verdict``
    for a DAG), so a future tier grows here ONCE and the two rankings CANNOT diverge by omission.  Byte-identical
    to the two prior copies.

    Tiers, worst-last: excluded worst, then composability, then the sourced physics tiers.  Selectivity: a
    sourced-FAVORED route (it makes the major isomer) floats above an unresolved one, above a sourced-DISFAVORED
    one.  Feasibility SIGN: a thermodynamically FAVORABLE route (worst step ΔG < 0) floats above
    borderline/unknown, above UNFAVORABLE (a stuck step still gates -- the worst-node sign is the categorical
    gate, ABOVE the additive refinement below).

    M2b -- the M2-FP objective made LIVE.  Two tiers ride between the feasibility sign and equilibrium:

    * ``front_index`` -- the Pareto non-dominated layer over ``PhysicsProduct(net ΔG, survival)`` (computed
      set-relative by :func:`_pareto_front_indices` in :func:`_physics_ranked_order`; 0 when called standalone).
      It is DATA-GATED (survival is usually ``None`` -> incomplete -> layer 0), so on today's data it rarely
      reorders -- it fires where sourced kinetics reach a multi-step route (the R25 two-axis ``frontier``
      discipline).
    * the ``net ΔG`` MAGNITUDE (the additive Hess functor ``G: Process->(ℝ,+,≤)``) -- the LIVE single-axis
      refinement: a route with a more negative net drive floats.  It is applied ONLY in the FAVORABLE
      feasibility class, where every step is favorable so the net is guaranteed KNOWN and negative -- in every
      other class the slot is a constant 0.0 for all routes, so the tier is inert and falls through to
      equilibrium.  This gating (evil-morty fold) is the fix for a real reward-for-ignorance bug: a route can
      be verdict-UNFAVORABLE (a sourced-endergonic step) yet net-``None`` (another step unsourced), so a raw
      ``None -> 0.0`` sentinel is NOT the neutral middle inside the UNFAVORABLE class -- it is a specific
      magnitude that would float an unsourced route ABOVE a fully-sourced endergonic one.  Confining the
      magnitude to the FAVORABLE class (no known/unknown net can mix there) keeps it honest.

    HONESTY (birdperson fold): the ``net ΔG`` magnitude is a PRESENTATION order, NOT a dominance verdict -- so
    among Pareto-INCOMPARABLE complete routes (same ``front_index``) it presents by net drive then discovery
    order; the honest dominance datum is ``front_index`` itself, and the two Pareto axes are NEVER collapsed
    into one weighted scalar.  Equilibrium / gap+exclusion counts / the rate regime remain the finer legacy
    tiebreakers (the regime rides DEAD LAST, ranking-only, never entering any L2 grade).  All tiers stay
    neutral on ignorance (a sourced positive floats, a sourced negative sinks, UNKNOWN sits in the middle).
    """
    # UNCONSTRAINED shares the top tier with FITS: with no bench box, no route is penalised for the missing
    # constraint and the finer tiebreakers decide.  Because the box is shared across a fit_routes call,
    # UNCONSTRAINED is all-or-nothing and never actually mixes with FITS/UNKNOWN/EXCLUDED in one ranking.
    status_rank = {RouteFitStatus.FITS: 0, RouteFitStatus.UNCONSTRAINED: 0,
                   RouteFitStatus.UNKNOWN: 1, RouteFitStatus.EXCLUDED: 2}
    # COMPOSABLE 0 < NO_TRANSITIONS/SINGLE_STEP 1 < UNKNOWN 2 < DEGENERATE 3.  NO_TRANSITIONS is DAG-only (a
    # linear route's composability verdict is never NO_TRANSITIONS), so it is inert in a route ranking and exact
    # in a DAG ranking -- the one merge that lets a single dict serve both scorers byte-identically.
    comp_rank = {"COMPOSABLE": 0, "NO_TRANSITIONS": 1, "SINGLE_STEP": 1, "UNKNOWN": 2, "DEGENERATE": 3}
    sel_rank = {"FAVORED": 0, "NOT_APPLICABLE": 1, "UNKNOWN": 1, "DISFAVORED": 2}
    feas_rank = {"FAVORABLE": 0, "BORDERLINE": 1, "UNKNOWN": 1, "UNFAVORABLE": 2}
    eq_rank = {"ESSENTIALLY_COMPLETE": 0, "FAVORABLE": 1, "BALANCED": 2, "UNKNOWN": 2,
               "LIMITED": 3, "NEGLIGIBLE": 4}
    regime_rank = {"FAST": 0, "MODERATE": 1, "UNKNOWN": 2, "SLOW": 3, "FROZEN": 4}
    return (
        status_rank[status],
        comp_rank.get(comp_verdict, 4),
        sel_rank.get(sel_verdict, 1),
        feas_rank.get(feas_verdict, 1),
        front_index,                                    # M2b: Pareto non-dominated layer (ΔG × survival)
        # M2b: additive-ΔG magnitude, ONLY in the FAVORABLE class (net then guaranteed known+negative -- no
        # known/unknown net can mix, so no reward-for-ignorance); inert (0.0 for all) elsewhere (evil-morty fold).
        net_delta_g if (net_delta_g is not None and feas_verdict == "FAVORABLE") else 0.0,
        eq_rank.get(eq_verdict, 2),
        n_gaps,
        n_exclusions,
        regime_rank.get(kin_verdict, 2),
        # DEAD-LAST: the DERIVED bond-additivity disconnection tier (DISCONN-SEL-01).  Strictly SUBORDINATE to every
        # sourced tier above -- it only separates routes that tie on all of them (where the sourced thermo is UNKNOWN,
        # e.g. the R45 caffeine over-generation: a sound N-methylation vs a C-C homologation, byte-identical on every
        # sourced tier, previously split only by arbitrary discovery order).  {0 FAVORABLE, 1 BORDERLINE/UNKNOWN,
        # 2 UNFAVORABLE} from the bond-additivity net ΔH sign past a calibrated dead-band -- neutral on ignorance (an
        # untabulated route sits at the BORDERLINE middle, never rewarded or penalised).  RANKING-ONLY: it never enters
        # ``fit.status`` or any L2 grade, exactly like the kinetics regime.  A CALLER-COMPUTED coordinate (like
        # front_index/net_delta_g), threaded through _physics_ranked_order, so BOTH _route_score and _dag_score stay
        # pure extractors and cannot diverge (the R42 no-divergence promise); default 1 (neutral) when unsupplied.
        derived_rank,
    )


def _physics_ranked_order(entries, score_fn) -> list:
    """The shared M2b ranking ORDER for linear routes and convergent DAGs (the DAG-RANK-01 no-divergence promise).

    ``entries`` is a sequence of ``(fit, net, survival[, derived_rank])`` tuples -- one per candidate: ``fit`` is the
    object ``score_fn`` reads; ``net`` / ``survival`` are its M2-FP Pareto coordinates (the additive Hess net ΔG and
    the R23 survival monoid); the optional ``derived_rank`` is the DISCONN-SEL-01 bond-additivity coordinate (neutral 1
    if absent).  Each caller builds the tuple in a SINGLE aligned pass, so a candidate's fit and its coordinates cannot
    drift out of position (birdperson fold: alignment is structural, not a parallel-list caller obligation).  The non-dominated FRONT is SET-RELATIVE, so it is computed here over the WHOLE candidate
    set (:func:`_pareto_front_indices`); the ΔG magnitude is per-candidate.  A STABLE sort over indices keeps
    discovery order for ties -- so Pareto-INCOMPARABLE candidates (same front, no ΔG separation) are presented in
    discovery order, never forced into a fabricated order.  Returns the best-first index permutation.  (This wiring
    was duplicated verbatim in :func:`rank_routes` and :func:`rank_dags`; sharing it makes the "both move together
    or neither does" promise structural, not a comment.)
    """
    fits = [e[0] for e in entries]
    products = tuple(PhysicsProduct(e[1], e[2]) for e in entries)
    # DISCONN-SEL-01: an optional 4th per-candidate coordinate, the DERIVED bond-additivity disconnection rank
    # ({0,1,2}, neutral default 1).  Carried here exactly like net/survival so the dead-last derived tier is fed
    # IDENTICALLY into _route_score and _dag_score -- routes and their DAG twins rank by the same discipline.
    dranks = [e[3] if len(e) > 3 else 1 for e in entries]
    fronts = _pareto_front_indices(products)
    return sorted(range(len(fits)),
                  key=lambda i: score_fn(fits[i], fronts[i], products[i].delta_g_kj, dranks[i]))


def _route_score(fit: RouteFit, front_index: int = 0, net_delta_g: float | None = None,
                 derived_rank: int = 1) -> tuple:
    """The linear-route ranking key: a thin verdict-extractor over the shared :func:`_score_tuple`.

    Pulls a :class:`RouteFit`'s NESTED verdicts (``fit.selectivity.verdict`` etc.) and hands them to the shared
    core.  ``derived_rank`` is a per-candidate coordinate computed by the caller (like ``front_index``/``net_delta_g``),
    so the scorer stays a pure extractor and CANNOT diverge from :func:`_dag_score` by omission.  Default 1 (neutral).
    """
    return _score_tuple(
        fit.status, fit.composability.verdict, fit.selectivity.verdict, fit.feasibility.verdict,
        fit.equilibrium.verdict, fit.kinetics.verdict, len(fit.gaps), len(fit.exclusions),
        front_index, net_delta_g, derived_rank,
    )


def rank_routes(
    routes, box: ConstraintBox | None = None, *,
    stability=None, selectivity: SelectivityTable | None = None, thermo=None,
    kinetics: KineticTable | None = None, losses: tuple = (), phases: "dict[Molecule, str] | None" = None,
) -> tuple[RouteFit, ...]:
    """Rank routes best-first for a bench (or, with ``box=None``, an unconstrained bench).

    The north-star litmus: given several candidate routes to the same target, float the ones that FIT and
    are COMPOSABLE and sourced above those with UNKNOWN gaps above those EXCLUDED or DEGENERATE -- and, among
    otherwise-comparable routes, the one whose steps make the SOURCED major isomer and are thermodynamically
    FAVORABLE above those that make the minor isomer or are endergonic -- surfacing better-evidenced formal
    candidates without asserting procedure readiness.

    ``phases`` (ITEM5-PHASE-RANK-01): the optional ``{Molecule: phase}`` declaration threads through
    :func:`fit_routes`/:func:`fit_route` into :func:`verify_feasibility`, so a route carrying a dual-phase species is
    ranked on the DECLARED phase's feasibility sign AND additive net-ΔG magnitude rather than fail-closed to UNKNOWN.
    This is the item-5 forcing consumer the R37 brick deferred ("no dual-phase ranked route exists -- the
    zero-call-sites trap; unparks when one does"): a route pair whose *ranking order* now flips on the phase
    declaration.  Default ``None`` is byte-identical to the pre-brick behaviour for every existing caller, and the
    returned fits carry the phase-aware verdicts so :meth:`~smartchem.service.RankedRouteSummary.of_fit` projects
    consistently (no rank-vs-dossier divergence -- unlike the DAG path, see :func:`rank_dags`).
    """
    effective_box = box if box is not None else ConstraintBox()
    fits = list(fit_routes(routes, effective_box, stability=stability, selectivity=selectivity, thermo=thermo,
                           kinetics=kinetics, losses=losses, phases=phases))
    # M2b: the M2-FP Pareto product (net additive ΔG × route survival) made LIVE in the ranking.  The net ΔG is
    # the additive Hess functor already computed per route (RouteFeasibility.net_delta_g_kj); survival is the R23
    # monoid functor (Composability.route_surviving_fraction).  The set-relative front + stable score sort is the
    # SHARED _physics_ranked_order (byte-identical wiring to rank_dags -- the DAG-RANK-01 no-divergence promise now
    # structural, not a comment): a route ranks by exactly the discipline a DAG does.
    order = _physics_ranked_order(
        [(f, f.feasibility.net_delta_g_kj, f.composability.route_surviving_fraction,
          disconnection_favorability_rank(f.route)) for f in fits],
        _route_score,
    )
    return tuple(fits[i] for i in order)


def _dag_score(fit: DAGBenchFit, front_index: int = 0, net_delta_g: float | None = None,
               derived_rank: int = 1) -> tuple:
    """Sort key for a convergent DAG, lower = better -- the DAG analogue of :func:`_route_score`'s STRUCTURAL tiers.

    Ranks on exactly what the combined :class:`DAGBenchFit` carries: the section-11 status (a FITS/UNCONSTRAINED DAG
    floats above an UNKNOWN, above an EXCLUDED), then the E1 composability verdict, then fewer gaps, then fewer
    exclusions.  The composability tier is ``COMPOSABLE`` (0) < ``NO_TRANSITIONS``/``SINGLE_STEP`` (1) < ``UNKNOWN``
    handoff (2) < ``DEGENERATE`` (3): a multi-edge convergent route whose handoffs are all affirmatively cleared
    outranks a trivial "nothing to compose" DAG, which outranks one with an unrefuted handoff -- MIRRORING
    :func:`_route_score`'s ``SINGLE_STEP=1`` exactly (a positive composability cleared on sourced data is stronger
    evidence than the vacuous absence of a handoff).  This closes the "DAG mode ranks nothing" gap (DAG-RANK-01, the
    next-step DAG-BENCH-01 left open) so a chemist handed several admissible convergent routes sees the best-evidenced
    one first -- the north-star litmus.

    DAG-THERMO-01: the three SOURCED thermochemical tiers :func:`_route_score` rides between composability and the
    counts (selectivity / feasibility / equilibrium) and its last-resort kinetics tier are aggregated per node
    (:func:`~smartchem.experiment.dag.dag_thermo_rollup`, worst-node-dominated, carried FLAT on ``DAGBenchFit``), so
    this ranks on EXACTLY the same tier order ``_route_score`` does -- a DAG ranking is as rich as a linear one.  Each
    is NEUTRAL on ignorance (a sourced positive floats, a sourced negative sinks, UNKNOWN sits in the middle -- never
    a penalty for missing data) and RANKING-ONLY (it orders otherwise-tied DAGs and NEVER enters ``fit.status``,
    exactly as the linear kinetics tier never enters an L2 grade).

    The tier dicts + the M2b tiers live ONCE in the shared :func:`_score_tuple`; this is a thin verdict-extractor
    over it, pulling the DAG's FLAT rollup verdicts (``fit.selectivity_verdict`` etc.) where :func:`_route_score`
    pulls a RouteFit's NESTED sub-fit verdicts.  Sharing the core makes the DAG-RANK-01 no-divergence promise
    structural: a new tier grows in one place, so the two scorers cannot diverge by a forgotten hand-edit (M2b was
    the last tier that had to be threaded into both copies by hand)."""
    return _score_tuple(
        fit.status, fit.composability.verdict, fit.selectivity_verdict, fit.feasibility_verdict,
        fit.equilibrium_verdict, fit.kinetics_verdict, len(fit.gaps), len(fit.exclusions),
        front_index, net_delta_g, derived_rank,
    )


def rank_dags(
    dags, box: ConstraintBox | None = None, *, phases: "dict[Molecule, str] | None" = None,
) -> tuple:
    """Rank convergent DAGs best-first for a bench (or, with ``box=None``, an unconstrained bench) -- the DAG analogue
    of :func:`rank_routes` (DAG-RANK-01), closing the "DAG mode ranks nothing" gap DAG-BENCH-01 left open.

    Sorts by each DAG's COMBINED section-11 bench fit (:func:`dag_bench_fit`) via :func:`_dag_score`: FITS+COMPOSABLE
    convergent routes float above UNKNOWN-gap ones, above EXCLUDED/DEGENERATE ones.  The sort is STABLE, so DAGs that
    tie on every ranked dimension keep their discovery order -- a deterministic, reproducible ranking.

    It scores each DAG under the DEFAULT sourced tables (stability + the DAG-THERMO-01 selectivity/thermo/kinetics),
    EXACTLY as the caller's :class:`~smartchem.service.RankedDAGSummary.of_dag` projects it -- so the ranked order can
    never disagree with the ``fit_status``/verdicts each dossier carries.  Deliberately takes NO table params (the
    ROUND-15 fold, re-affirmed for DAG-THERMO-01): ``of_dag`` takes none either, so accepting a table here would let a
    caller rank under one table while the dossiers project under the defaults -- a latent divergence with no consumer.
    ``dag_bench_fit`` still accepts the tables for a direct caller who owns BOTH sides; the ranking entry point does not
    expose them until ``of_dag`` can thread them too, so BOTH move together or neither does.

    ITEM5-DAG-PHASE-01 -- the ROUND-15 ``of_dag`` re-projection fold, now DISCHARGED (the DAG twin of the linear
    ITEM5-PHASE-RANK-01).  Historically ``rank_dags`` took NO ``phases`` param, because it returns the DAGs (not the
    scored fits) and :meth:`~smartchem.service.RankedDAGSummary.of_dag` RE-PROJECTS each under the default tables:
    exposing ``phases`` on ``rank_dags`` ALONE would rank under a declared phase while every dossier projected the
    phase-blind (fail-closed-UNKNOWN) verdict -- a rank-vs-dossier divergence with no consumer.  The fold's own stated
    unlock was "a service API that carries a phase declaration into BOTH ``rank_dags`` and ``of_dag``."  That is now
    built: :meth:`~smartchem.service.RankedDAGSummary.of_dag` accepts ``phases`` too, and the seam that co-calls them
    (:func:`~smartchem.service.ranked_dag_dossiers`) passes ONE declaration into both, so rank and dossier read the
    identical phase and CANNOT diverge -- BOTH move together, structurally, exactly as the fold required.  ``phases``
    now threads into ``dag_bench_fit`` -> ``dag_thermo_rollup`` (the per-node feasibility fold) AND into
    ``route_net_delta_g`` (the additive M2b drive), so a dual-phase DAG is ranked on the declared phase's feasibility
    SIGN and additive net-ΔG rather than fail-closed to UNKNOWN.  Default ``None`` is byte-identical to the pre-brick
    behaviour for every existing caller.  Like the linear ranker, the EQUILIBRIUM axis stays phase-blind (the R37
    precedent) and the production recompile path (``_run_recompile``) passes no phases (the request carries no phase
    field yet -- the named follow-up), exactly as the linear ``rank_routes`` production call likewise passes none.  See
    ``docs/research/ITEM5_DAG_PHASE_AWARE_RANKING_SCOPE_v0.1.md``."""
    effective_box = box if box is not None else ConstraintBox()
    scored = [(dag_bench_fit(dag, effective_box, phases=phases), dag) for dag in dags]
    # M2b: the SHARED _physics_ranked_order wires the same M2-FP Pareto product into the DAG ranker, so a DAG and its
    # linear twin rank by the identical discipline (the DAG-RANK-01 no-divergence promise, now structural).  The DAG's
    # additive net ΔG is the Hess sum over its steps (route_net_delta_g accepts the DAG -- intermediates cancel), now
    # phase-fed (ITEM5-DAG-PHASE-01); survival is the DAG survival monoid (Composability.route_surviving_fraction).
    order = _physics_ranked_order(
        [(fit, route_net_delta_g(dag, phases=phases), fit.composability.route_surviving_fraction,
          disconnection_favorability_rank(dag)) for fit, dag in scored],
        _dag_score,
    )
    return tuple(scored[i][1] for i in order)


@dataclass(frozen=True)
class RouteDossier(Digestible):
    """A human-readable route evidence dossier; never, by this type alone, a bench-ready procedure."""

    route: ExperimentRoute
    composability: Composability
    accounting: PhysicalAccounting
    equipment: tuple[tuple[EquipmentItem, ...], ...]   # one tuple per step
    ceiling: RouteCeiling | None
    selectivity: RouteSelectivity  # which isomer each step makes (sourced regiochemistry, or a loud gap)
    feasibility: RouteFeasibility  # thermodynamic ΔG verdict per step (DERIVED, or a loud UNKNOWN)
    equilibrium: RouteEquilibrium  # equilibrium extent K=exp(-ΔG/RT) per step (DERIVED, or a loud UNKNOWN)
    handling: RouteHandling  # E6 bench handling: byproducts, off-gasses, and the care level per step
    #: The typed Sec 3/4/8 obligation ladder for this exact route (``smartchem.experiment.readiness.
    #: RouteReadiness``) -- SOURCE OF TRUTH, computed once by :func:`draft_route_dossier` via the SAME
    #: ``evaluate_route`` the service transport re-derives from on load (v0.8, closing the old
    #: READY-TIER-01 wall: this used to be a hard-coded ``FORMAL_CANDIDATE`` no route could ever earn
    #: or lose). ``readiness_tier`` below is a derived convenience, never the reverse.
    readiness: RouteReadiness

    def __post_init__(self) -> None:
        if type(self.readiness) is not RouteReadiness:
            raise TypeError("readiness must be a RouteReadiness")

    @property
    def readiness_tier(self) -> str:
        """The coarse tier, read straight off the typed ``readiness`` record -- never a second,
        independently-settable claim (there's only one place a caller could construct a lie, and
        ``evaluate_route`` is what fills it)."""
        return self.readiness.tier

    def render(self) -> str:
        tier = self.readiness_tier
        lines = [
            DRAFT_BANNER,
            f"READINESS: {tier} (derived from smartchem.experiment.readiness.evaluate_route)",
        ]
        if tier != PROCESS_SPECIFIED:
            # PROCESS_SPECIFIED is DARK this round (readiness.process_representation_is_complete is
            # always False today) -- so this fires for every dossier this code can currently produce.
            # It stays keyed off the REAL tier, not a static string, so the day PROCESS_SPECIFIED
            # lights up, this disclaimer honestly stops printing instead of lying forever.
            lines.append(f"  -- NOT a bench-ready procedure (tier {tier} < {PROCESS_SPECIFIED})")
        lines.append("SATISFIED OBLIGATIONS (route-level, weakest-link across steps):")
        any_satisfied = False
        for name, status in (
            ("reaction_type recognized", all(
                s.reaction_type is ObligationStatus.SATISFIED for s in self.readiness.per_step
            )),
            ("conditions sourced", all(
                s.conditions is ObligationStatus.SATISFIED for s in self.readiness.per_step
            )),
            ("process fully specified", all(
                s.process is ObligationStatus.SATISFIED for s in self.readiness.per_step
            )),
            ("workup/isolation described", all(
                s.workup_isolation is ObligationStatus.SATISFIED for s in self.readiness.per_step
            )),
        ):
            if status:
                any_satisfied = True
                lines.append(f"  - {name}")
        if not any_satisfied:
            lines.append("  (none)")
        lines.append("OPEN OBLIGATIONS (route-level, union across steps):")
        if self.readiness.route_open_obligations:
            for reason in self.readiness.route_open_obligations:
                lines.append(f"  - {reason}")
        else:
            lines.append("  (none)")
        lines.append("PER-STEP READINESS (why the route tier is what it is above):")
        for idx, step_readiness in enumerate(self.readiness.per_step):
            klass = step_readiness.reaction_class_name or "unrecognized"
            lines.append(
                f"  step {idx + 1}: tier={step_readiness.tier} reaction_type={step_readiness.reaction_type.value}"
                f" ({klass}) conditions={step_readiness.conditions.value}"
                f" process={step_readiness.process.value} workup_isolation={step_readiness.workup_isolation.value}"
            )
        lines.append("MISSING BEFORE BENCH USE (supporting detail; the tier above is the load-bearing claim):")
        lines.extend(f"  - {field}" for field in _MISSING_BENCH_FIELDS)
        lines.append("")
        lines.append(f"TARGET: {self.route.final_target!r}")
        lines.append("")
        for idx, step in enumerate(self.route.steps):
            lines.append(f"STEP {idx + 1}: {step.equation()}")
            lines.append(f"    reactant identities: {' + '.join(_chemist_label(m) for m in step.reactants)}")
            lines.append(f"    product identities: {' + '.join(_chemist_label(m) for m in step.products)}")
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
            # -- E6: what comes off this step, and how much care running it needs --------------------
            sh = self.handling.steps[idx]
            lines.append(f"    handling: {sh.care.value}")
            for b in sh.byproducts:
                gas = " (OFF-GAS)" if b.is_offgas else ""
                haz = f" [{b.hazard_name}]" if b.hazard_name else " [hazard UNASSESSED]"
                lines.append(f"      byproduct: {b.moles_per_target} x {b.molecule!r} -- {b.fate.value}{gas}{haz}")
            for reason in sh.care_reasons:
                lines.append(f"      ! {reason}")
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
        lines.append("")
        lines.append(self.handling.explain())
        if self.ceiling is not None:
            lines.append("")
            lines.append(self.ceiling.explain())
        return "\n".join(lines)


def draft_route_dossier(
    route: ExperimentRoute,
    feed: Mapping[Molecule, "int | Fraction"] | None = None,
    *,
    stability=None,
    selectivity: SelectivityTable | None = None,
    thermo=None,
    losses: tuple = (),
) -> RouteDossier:
    """Compose a formal-candidate route evidence dossier from the available analysis layers.

    The dossier includes E1 composability, E3 accounting, equipment, the optional E2 ceiling,
    the sourced regiochemical selectivity (which isomer each step makes), the DERIVED thermodynamic
    feasibility (ΔG per step), the DERIVED equilibrium diagnostic (M2: K = exp(-ΔG/RT) per step), and
    the DERIVED Sec 3/4/8 readiness obligation ladder (``smartchem.experiment.readiness.evaluate_route``)
    -- an honest, per-route measurement, not a promotion. A route earns whatever tier its own
    recognized reaction types / sourced conditions / process record actually support; today's corpus
    tops out below ``PROCESS_SPECIFIED`` (dark this round), so it is never a complete bench procedure.

    ``feed`` (external reactant amounts in mol) turns on the propagated 100%-efficiency ceiling; omit it to
    skip the outcome bound.  ``stability`` / ``selectivity`` / ``thermo`` optionally extend the sourced data
    for any chemical (``thermo`` feeds both the ΔG feasibility and the equilibrium K).
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    comp = verify_composability(route) if stability is None else verify_composability(route, stability=stability)
    sel = verify_selectivity(route, table=selectivity, losses=losses)  # EVD-KEY-01: a BLOCKER gags the sourced verdict
    feas = verify_feasibility(route, thermo=thermo)
    equi = verify_equilibrium(route, thermo=thermo)
    handling = verify_handling(route) if stability is None else verify_handling(route, stability=stability)
    accounting = account_route(route)
    equipment = tuple(equipment_for_step(s) for s in route.steps)
    ceiling = None
    if feed is not None:
        ceiling = route_ceiling(route, feed)
    # v0.8 Real Route Dossiers: readiness comes from the ONE shared evaluator (smartchem.experiment.
    # readiness.evaluate_route) -- the same one smartchem.service re-derives from on load -- fed the
    # SAME `losses` tuple `verify_selectivity` above already saw (section 5.3's conditions-blocker
    # needs the identical evidence the selectivity gag did; two different loss tuples for the same
    # route would be its own kind of lie).
    readiness = evaluate_route(route, identity_losses=losses)
    return RouteDossier(route, comp, accounting, equipment, ceiling, sel, feas, equi, handling, readiness)


# Compatibility spellings retained for one deprecation cycle.  Canonical code and rendered output use
# route-dossier language; these aliases confer no procedure-readiness claim.
DraftedProcedure = RouteDossier


def draft_procedure(*args, **kwargs) -> RouteDossier:
    """Deprecated compatibility wrapper for :func:`draft_route_dossier`."""
    import warnings
    warnings.warn(
        "draft_procedure is deprecated; use draft_route_dossier (the result is not a bench procedure)",
        DeprecationWarning,
        stacklevel=2,
    )
    return draft_route_dossier(*args, **kwargs)
