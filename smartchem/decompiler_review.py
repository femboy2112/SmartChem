"""M-4b review layer: make a decomposition graph usable to a working chemist — safely.

Two jobs, both aimed at the litmus ("could a chemist with only bare elements use this
coherently?"), and both explicitly honest about what they do and do not establish.

1. **Structural coherence ranking (data-free).** v1 returns dozens of conservation-valid
   edges, most of them element *shrapnel* (`-> C + CO + ... + 2 H`). :func:`coherence_score`
   scores an edge by the fraction of its product content that is a *declared compound* rather
   than an element bucket, so :func:`review_graph` floats the chemically meaningful
   decompositions (e.g. `paracetamol -> p-aminophenol + ketene`, score 1.0) above the
   shrapnel. This is a **presentation heuristic**, not a feasibility or thermodynamic claim.

2. **Source-backed safety screen — inform, never neuter.** This is a professional tool: it
   does **not** hide or refuse a hazardous decomposition. It *attaches* what is known so the
   chemist owns the safety call. The energetics are real — reaction enthalpy at 0 K computed
   from NIST/CCCBDB formation enthalpies (`smartchem.data.reference`), cross-checked against
   that module's own `atomization_energy_ev`. Because assembly is the reverse of decomposition,
   forming a molecule from its bare atoms is strongly **exothermic**, and that is flagged with
   the actual number and source. Two rules keep the safety honest:

   * **UNKNOWN is not safe.** Where any species lacks reference data the energetics are
     `ENERGETICS_UNKNOWN` — a loud caution, never an absent flag read as a clearance.
   * **Formula-level ambiguity is surfaced.** A formula can name several isomers with different
     enthalpies (C2H6O = ethanol or dimethyl ether); the assessment carries the resulting
     enthalpy *interval* and an `ISOMER_AMBIGUOUS` flag rather than a false single number.

   The screen is decoration on the CERTIFIED conservation skeleton and never upgrades it; the
   number is a standard formation-enthalpy balance (0 K, ideal, from gas-phase atoms), a
   *screening estimate*, not the enthalpy under a chemist's real reagents, solvent, or
   conditions. C2 (mediated reactions) and real condition/kinetic hazards remain future rungs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import Digestible
from .data import reference
from .decompiler import DecompositionEdge, DecompositionGraph, Formula, admissible_edges
from .decompiler_mediated import MediatedEdge, mediated_edges

#: Either kind of decomposition edge the review layer knows how to score and screen. Both expose
#: ``reactant`` / ``reactant_multiplicity`` / ``products``; a MediatedEdge additionally exposes
#: ``reagents`` (drawn from solution), which the energy balance adds to the reactant side.
AnyEdge = DecompositionEdge | MediatedEdge

__all__ = [
    "SAFETY_BANNER",
    "HazardFlag",
    "EnergyAssessment",
    "HazardProfile",
    "EdgeReview",
    "AnyEdge",
    "coherence_score",
    "assess_edge_energy",
    "screen_edge",
    "review_edges",
    "review_graph",
    "decompile_and_review",
]

SAFETY_BANNER = (
    "SAFETY: hazards shown are INFORMATIONAL and never a filter — no decomposition is hidden or "
    "refused for being dangerous. Energetics are a 0 K standard formation-enthalpy balance from "
    "gas-phase atoms (NIST/CCCBDB), a SCREENING estimate, not the enthalpy under your real "
    "reagents, solvent, or conditions. ENERGETICS_UNKNOWN means unassessed, NOT safe. You own the "
    "decision about whether a real experiment is within your safety profile."
)

# The default exothermicity threshold: assembling any molecule from bare atoms releases many eV,
# so this is deliberately low — the point is to flag the "bare-element assembly is a large heat
# release" reality the litmus is about, with the actual number, not to gate on it.
_DEFAULT_EXOTHERM_THRESHOLD_EV = 1.0

_ENERGY_SOURCE = "NIST/CCCBDB R22 formation enthalpies at 0 K (smartchem.data.reference)"


class HazardFlag(str, Enum):
    """Informational hazard tags. Extensible; energetics-driven ones are populated today."""

    EXOTHERMIC_ASSEMBLY = "EXOTHERMIC_ASSEMBLY"   # forming this species releases significant heat
    ENERGETICS_UNKNOWN = "ENERGETICS_UNKNOWN"     # not assessable from reference data -- NOT "safe"
    ISOMER_AMBIGUOUS = "ISOMER_AMBIGUOUS"         # formula-level: enthalpy depends on the isomer


def _dfh_range_kj(formula: Formula) -> tuple[float, float] | None:
    """Formation enthalpy at 0 K (kJ/mol) as a ``(min, max)`` interval over matching references.

    An element bucket ``{E: k}`` resolves exactly to ``k * dfH(atom E)``; a molecule resolves to
    the min/max over every tabulated isomer of its composition (formula-level ambiguity made
    explicit). ``None`` if any needed reference is absent.
    """
    if formula.is_element:
        (symbol, count), = formula.counts
        base = reference.ATOM_FORMATION_KJ.get(symbol)
        return None if base is None else (count * base, count * base)
    comp = formula.as_dict
    matches = [r.dfh_0k_kj for r in reference.POLYATOMIC_REFS if dict(r.composition) == comp]
    return (min(matches), max(matches)) if matches else None


@dataclass(frozen=True)
class EnergyAssessment(Digestible):
    """The assembly (formation-from-buckets) reaction enthalpy interval in eV, or a coverage gap.

    ``assembly_lo_ev``/``assembly_hi_ev`` are ``None`` iff some species lacks reference data
    (then ``uncovered_species`` names the gaps). Assembly is the reverse of the decomposition
    edge, so a negative enthalpy means forming the reactant *releases* heat.
    """

    assembly_lo_ev: float | None
    assembly_hi_ev: float | None
    uncovered_species: tuple[str, ...]
    source: str = _ENERGY_SOURCE

    def __post_init__(self) -> None:
        both_none = self.assembly_lo_ev is None and self.assembly_hi_ev is None
        both_set = self.assembly_lo_ev is not None and self.assembly_hi_ev is not None
        if not (both_none or both_set):
            raise ValueError("assembly interval bounds must both be set or both None")
        if both_set and self.assembly_lo_ev > self.assembly_hi_ev:
            raise ValueError("assembly_lo_ev must be <= assembly_hi_ev")
        if both_none and not self.uncovered_species:
            raise ValueError("an uncovered assessment must name the species it could not resolve")

    @property
    def covered(self) -> bool:
        return self.assembly_lo_ev is not None

    @property
    def is_exothermic_assembly(self) -> bool | None:
        """True iff the whole interval is negative (isomer-robust). ``None`` if uncovered."""
        if not self.covered:
            return None
        return self.assembly_hi_ev < 0.0

    @property
    def sign_ambiguous(self) -> bool:
        return self.covered and self.assembly_lo_ev < 0.0 <= self.assembly_hi_ev


def assess_edge_energy(edge: AnyEdge) -> EnergyAssessment:
    """Compute the assembly enthalpy interval for an edge from reference formation enthalpies.

    Handles both a plain :class:`~smartchem.decompiler.DecompositionEdge` and a mediated
    :class:`~smartchem.decompiler_mediated.MediatedEdge`: the reactant-side (LHS) interval is
    ``n * reactant`` plus every reagent drawn from solution, so a hydrolysis is scored with its
    water on the balance, not silently dropped.
    """
    if type(edge.reactant) is not Formula:  # duck-typed over both edge kinds
        raise TypeError("edge must expose a Formula reactant, int multiplicity, and products")
    uncovered: list[str] = []
    # reactant-side species: n * reactant, then any reagents (empty for a plain edge)
    lhs_lo = lhs_hi = 0.0
    lhs_species = [(edge.reactant, edge.reactant_multiplicity)] + list(getattr(edge, "reagents", ()))
    for species, mult in lhs_species:
        rng = _dfh_range_kj(species)
        if rng is None:
            uncovered.append(repr(species))
        else:
            lhs_lo += mult * rng[0]
            lhs_hi += mult * rng[1]
    prod_lo = prod_hi = 0.0
    for product, mult in edge.products:
        rng = _dfh_range_kj(product)
        if rng is None:
            uncovered.append(repr(product))
        else:
            prod_lo += mult * rng[0]
            prod_hi += mult * rng[1]
    if uncovered:
        return EnergyAssessment(None, None, tuple(sorted(set(uncovered))))

    # decomposition ΔH interval (kJ): products - LHS; assembly is its reverse (negate and swap)
    assembly_lo = -(prod_hi - lhs_lo) / reference.KJ_PER_EV
    assembly_hi = -(prod_lo - lhs_hi) / reference.KJ_PER_EV
    return EnergyAssessment(assembly_lo, assembly_hi, ())


@dataclass(frozen=True)
class HazardProfile(Digestible):
    """Informational hazard tags for an edge, plus its energy assessment. Never a filter."""

    energy: EnergyAssessment
    flags: tuple[HazardFlag, ...]
    notes: str = ""

    def __post_init__(self) -> None:
        if type(self.energy) is not EnergyAssessment:
            raise TypeError("energy must be an EnergyAssessment")
        if type(self.flags) is not tuple or any(type(f) is not HazardFlag for f in self.flags):
            raise TypeError("flags must be a tuple of HazardFlag")
        object.__setattr__(self, "flags", tuple(sorted(set(self.flags), key=lambda f: f.value)))
        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")

    @property
    def assessed(self) -> bool:
        """True iff the energetics were resolvable; False means UNKNOWN (and UNKNOWN is not safe)."""
        return self.energy.covered


def screen_edge(
    edge: AnyEdge, *, exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV
) -> HazardProfile:
    """Screen one edge for hazards. Always returns a profile -- it never hides or refuses an edge."""
    energy = assess_edge_energy(edge)
    flags: list[HazardFlag] = []
    if not energy.covered:
        flags.append(HazardFlag.ENERGETICS_UNKNOWN)
        note = (
            f"energetics unassessed — no reference formation enthalpy for "
            f"{', '.join(energy.uncovered_species)}; UNKNOWN is not safe."
        )
    else:
        if energy.sign_ambiguous:
            flags.append(HazardFlag.ISOMER_AMBIGUOUS)
        # exothermic if the interval is (robustly) negative beyond the threshold, or if it could
        # be strongly exothermic on one isomer -- either way the chemist should see it.
        if energy.assembly_lo_ev is not None and energy.assembly_lo_ev < -exotherm_threshold_ev:
            flags.append(HazardFlag.EXOTHERMIC_ASSEMBLY)
        lo, hi = energy.assembly_lo_ev, energy.assembly_hi_ev
        span = f"{lo:.2f} eV" if lo == hi else f"[{lo:.2f}, {hi:.2f}] eV"
        note = f"assembly enthalpy {span} (0 K formation balance; negative = releases heat)."
    return HazardProfile(energy, tuple(flags), note)


def coherence_score(edge: AnyEdge) -> float:
    """Fraction of product content that is a declared compound rather than an element bucket.

    1.0 = every product is a molecule (a chemically meaningful split); 0.0 = pure element
    shrapnel (the elemental floor). A STRUCTURAL presentation heuristic, not a feasibility or
    thermodynamic claim. Reagents are not scored -- coherence is about what the target became.
    """
    molecular = sum(m for p, m in edge.products if not p.is_element)
    total = sum(m for _p, m in edge.products)
    return molecular / total if total else 0.0


@dataclass(frozen=True)
class EdgeReview(Digestible):
    """One reviewed edge (plain or mediated): the edge, its coherence, and its safety profile."""

    edge: AnyEdge
    coherence: float
    hazard: HazardProfile

    def __post_init__(self) -> None:
        if type(self.edge) not in (DecompositionEdge, MediatedEdge):
            raise TypeError("edge must be a DecompositionEdge or MediatedEdge")
        if type(self.hazard) is not HazardProfile:
            raise TypeError("hazard must be a HazardProfile")

    @property
    def mediated(self) -> bool:
        return type(self.edge) is MediatedEdge


def _review_key(review: "EdgeReview") -> tuple:
    # most chemically coherent first; break ties by the edge's own canonical order
    return (-review.coherence, review.edge.digest)


def review_edges(
    edges, *, exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV
) -> tuple[str, tuple[EdgeReview, ...]]:
    """Rank any mix of plain and mediated edges by coherence and attach a safety profile to each.

    Returns ``(banner, reviews)``, most chemically coherent first. No edge is ever dropped — the
    review *informs*, it does not censor.
    """
    reviews = tuple(
        sorted(
            (
                EdgeReview(e, coherence_score(e), screen_edge(e, exotherm_threshold_ev=exotherm_threshold_ev))
                for e in edges
            ),
            key=_review_key,
        )
    )
    return SAFETY_BANNER, reviews


def review_graph(
    graph: DecompositionGraph,
    *,
    reactant: Formula | None = None,
    exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV,
) -> tuple[str, tuple[EdgeReview, ...]]:
    """Rank a graph's edges by structural coherence and attach a safety profile to each.

    Returns ``(banner, reviews)``. No edge is ever dropped. Restrict to one reactant's direct
    decompositions with ``reactant``.
    """
    if type(graph) is not DecompositionGraph:
        raise TypeError("graph must be a DecompositionGraph")
    edges = graph.edges_from(reactant) if reactant is not None else graph.edges
    return review_edges(edges, exotherm_threshold_ev=exotherm_threshold_ev)


def decompile_and_review(
    target: "str | dict[str, int] | Formula",
    inventory: "tuple[Formula, ...] | tuple[str, ...]" = (),
    medium: "tuple[Formula, ...] | tuple[str, ...]" = (),
    *,
    exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV,
    max_reagent_instances: int = 1,
    budget: int = 200_000,
) -> tuple[str, tuple[EdgeReview, ...]]:
    """The unified chemist-facing view of one target's direct decompositions.

    Generates both the plain (own-atoms) edges and the mediated (solution-assisted) edges over the
    declared ``inventory`` + ``medium``, then reviews them together — so the real runnable reaction
    (a hydrolysis, say) surfaces ranked and safety-screened alongside the anhydrous backbone. No
    edge is dropped; ``ENERGETICS_UNKNOWN`` is loud where reference data is absent.
    """
    tf = target if isinstance(target, Formula) else (
        Formula.parse(target) if isinstance(target, str) else Formula.of(target)
    )
    inv = tuple(
        s if isinstance(s, Formula) else (Formula.parse(s) if isinstance(s, str) else Formula.of(s))
        for s in inventory
    )
    plain, _pc = admissible_edges(tf, inv, budget=budget)
    mediated, _mc = mediated_edges(
        tf, inv, medium, max_reagent_instances=max_reagent_instances, budget=budget
    )
    return review_edges(plain + mediated, exotherm_threshold_ev=exotherm_threshold_ev)
