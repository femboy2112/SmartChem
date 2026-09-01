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

from .category import Molecule
from .conditions import ConditionEnvelope
from .contracts import Digestible
from .data import decompiler_thermo, reference
from .data.hazards import HazardRef, hazards_for, hazards_for_named
from .decompiler import DecompositionEdge, DecompositionGraph, Formula, admissible_edges
from .decompiler_conditions import reaction_conditions
from .decompiler_mediated import MediatedEdge, mediated_edges
from .structure import resolve_names, resolve_structure

#: The loud no-declared-conditions default shared by every un-annotated review.
_UNKNOWN_CONDITIONS = ConditionEnvelope.unknown()

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
    "molecule_name",
    "molecule_hazards",
    "molecule_dfh_0k_kj",
    "molecule_dfh_0k_range_kj",
    "structures_of",
    "review_capped_scission",
]

SAFETY_BANNER = (
    "SAFETY: hazards shown are INFORMATIONAL and never a filter — no decomposition is hidden or "
    "refused for being dangerous. Energetics are a 0 K standard formation-enthalpy balance from "
    "gas-phase atoms (NIST/CCCBDB), a SCREENING estimate, not the enthalpy under your real "
    "reagents, solvent, or conditions. Sourced qualitative hazards (GHS/CAMEO/RTK) are ATTACHED "
    "where known — their absence is UNASSESSED, not a clearance. ENERGETICS_UNKNOWN means "
    "unassessed, NOT safe. You own the decision about whether a real experiment is within your "
    "safety profile."
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
    DOCUMENTED_HAZARD = "DOCUMENTED_HAZARD"       # a species carries a sourced qualitative hazard record
    HAZARDS_UNASSESSED = "HAZARDS_UNASSESSED"     # a species has NO sourced hazard record -- NOT "safe"
    ISOMER_ASSUMED = "ISOMER_ASSUMED"             # a specific isomer's name/hazards attached at formula level


def molecule_name(molecule: Molecule) -> str | None:
    """The specific isomer name of a structure, or ``None`` if unregistered/unresolvable."""
    st = resolve_structure(molecule)
    return st.name if st is not None else None


def molecule_hazards(molecule: Molecule) -> HazardRef | None:
    """The ISOMER-resolved hazard record for a structure (via its resolved name), or ``None``.

    This is what closes the formula-keying gap for hazards: given the actual structure, the hazards
    of *that* isomer (ethanol's, not the C2H6O interval) attach unambiguously.
    """
    name = molecule_name(molecule)
    return hazards_for_named(name) if name is not None else None


def molecule_dfh_0k_kj(molecule: Molecule) -> float | None:
    """The ISOMER-resolved 0 K formation enthalpy (kJ/mol) for a structure, or ``None``."""
    name = molecule_name(molecule)
    if name is None:
        return None
    recs = [r.dfh_kj for r in decompiler_thermo.records_for_named(name) if r.usable_at_0k]
    return recs[0] if recs else None


def molecule_dfh_0k_range_kj(molecule: Molecule) -> tuple[float, float] | None:
    """The 0 K formation-enthalpy interval (kJ/mol) for a *molecule*, isomer-resolved where known.

    The molecule-level entry point to :func:`_dfh_range_kj`, the same resolver the energy screen uses, so
    a caller gets the COMPLETE coverage (both the reference ``POLYATOMIC_REFS`` and the decompiler's own 0 K
    tiered values), unlike :func:`molecule_dfh_0k_kj`, which reads only the tiered set.  Returns an EXACT
    (degenerate) interval when the structure resolves to a tabulated isomer, the min/max over a
    composition's isomers when only the formula is known (ambiguity made explicit, not hidden), and
    ``None`` when no reference covers it.
    """
    return _dfh_range_kj(Formula.of(molecule.formula, molecule.charge), molecule)


def _dfh_range_kj(formula: Formula, molecule: Molecule | None = None) -> tuple[float, float] | None:
    """Formation enthalpy at 0 K (kJ/mol) as a ``(min, max)`` interval over matching references.

    An element bucket ``{E: k}`` resolves exactly to ``k * dfH(atom E)``. When a ``molecule`` is
    supplied and resolves to a registered isomer with a named 0 K value, the result is that ISOMER's
    exact value (a degenerate interval) -- so ethanol gets -217.1 rather than the C2H6O interval over
    both isomers. Otherwise a formula resolves to the min/max over every tabulated isomer of its
    composition (formula-level ambiguity made explicit). ``None`` if no reference is available.
    """
    if formula.is_element:
        (symbol, count), = formula.counts
        base = reference.ATOM_FORMATION_KJ.get(symbol)
        return None if base is None else (count * base, count * base)
    # structure-resolved: the exact per-isomer value where the structure is actually known
    if molecule is not None:
        exact = molecule_dfh_0k_kj(molecule)
        if exact is not None:
            return (exact, exact)
    comp = formula.as_dict
    # the benchmark verified set, plus the decompiler's own tiered 0 K values (ketene, acetic acid,
    # ...). Only 0 K-convention thermo entries are folded in -- a 298 K value (paracetamol) is
    # excluded upstream by zero_k_records, so it never contaminates this 0 K balance.
    matches = [r.dfh_0k_kj for r in reference.POLYATOMIC_REFS if dict(r.composition) == comp]
    matches += [r.dfh_kj for r in decompiler_thermo.zero_k_records(repr(formula))]
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


def assess_edge_energy(
    edge: AnyEdge, *, structures: "dict[Formula, Molecule] | None" = None
) -> EnergyAssessment:
    """Compute the assembly enthalpy interval for an edge from reference formation enthalpies.

    Handles both a plain :class:`~smartchem.decompiler.DecompositionEdge` and a mediated
    :class:`~smartchem.decompiler_mediated.MediatedEdge`: the reactant-side (LHS) interval is
    ``n * reactant`` plus every reagent drawn from solution, so a hydrolysis is scored with its
    water on the balance, not silently dropped.

    ``structures`` optionally maps a species ``Formula`` to its actual :class:`Molecule`; where a
    species is structure-resolved, its EXACT per-isomer 0 K value is used instead of the formula-level
    interval over all isomers -- so a structure-derived edge is scored without the isomer ambiguity.
    """
    if type(edge.reactant) is not Formula:  # duck-typed over both edge kinds
        raise TypeError("edge must expose a Formula reactant, int multiplicity, and products")
    structures = structures or {}
    uncovered: list[str] = []
    # reactant-side species: n * reactant, then any reagents (empty for a plain edge)
    lhs_lo = lhs_hi = 0.0
    lhs_species = [(edge.reactant, edge.reactant_multiplicity)] + list(getattr(edge, "reagents", ()))
    for species, mult in lhs_species:
        rng = _dfh_range_kj(species, structures.get(species))
        if rng is None:
            uncovered.append(repr(species))
        else:
            lhs_lo += mult * rng[0]
            lhs_hi += mult * rng[1]
    prod_lo = prod_hi = 0.0
    for product, mult in edge.products:
        rng = _dfh_range_kj(product, structures.get(product))
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
    """Informational hazard tags for an edge, its energy assessment, and any sourced species hazards.

    ``species_hazards`` are the qualitative :class:`~smartchem.data.hazards.HazardRef` records for the
    species this edge touches (reactant, reagents, products) -- attached, never used to filter. They
    are what tells a chemist that ketene is fatal if inhaled or that 4-aminophenol is a regulated
    degradant, beyond the bare heat-of-formation number.
    """

    energy: EnergyAssessment
    flags: tuple[HazardFlag, ...]
    notes: str = ""
    species_hazards: tuple[HazardRef, ...] = ()

    def __post_init__(self) -> None:
        if type(self.energy) is not EnergyAssessment:
            raise TypeError("energy must be an EnergyAssessment")
        if type(self.flags) is not tuple or any(type(f) is not HazardFlag for f in self.flags):
            raise TypeError("flags must be a tuple of HazardFlag")
        object.__setattr__(self, "flags", tuple(sorted(set(self.flags), key=lambda f: f.value)))
        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")
        if type(self.species_hazards) is not tuple or any(
            type(h) is not HazardRef for h in self.species_hazards
        ):
            raise TypeError("species_hazards must be a tuple of HazardRef")

    @property
    def assessed(self) -> bool:
        """True iff the energetics were resolvable; False means UNKNOWN (and UNKNOWN is not safe)."""
        return self.energy.covered


def _edge_species(edge: AnyEdge) -> tuple[Formula, ...]:
    """Every distinct species an edge touches: reactant, any reagents (mediated), and products."""
    seen: dict[Formula, None] = {edge.reactant: None}
    for species, _ in getattr(edge, "reagents", ()):
        seen.setdefault(species, None)
    for species, _ in edge.products:
        seen.setdefault(species, None)
    return tuple(seen)


def _collect_species_hazards(
    edge: AnyEdge, structures: "dict[Formula, Molecule] | None" = None
) -> tuple[tuple[HazardRef, ...], tuple[str, ...]]:
    """``(found_records, unassessed_species)`` for the edge's species.

    A species with a sourced record contributes to ``found_records``; one WITHOUT contributes its
    repr to ``unassessed_species`` -- so a coverage gap is data the caller must surface, symmetric
    with the energetics channel, never a silent drop (the clearance-by-omission this layer forbids).

    ``structures`` optionally maps a species ``Formula`` to its actual :class:`Molecule`; a
    structure-resolved species gets its ISOMER-specific record (``molecule_hazards``), so a formula
    that is ambiguous at formula level (``hazards_for`` returns ``None``) still attaches the right
    isomer's hazards when its structure is known.
    """
    structures = structures or {}
    found: list[HazardRef] = []
    unassessed: list[str] = []
    for species in _edge_species(edge):
        mol = structures.get(species)
        record = molecule_hazards(mol) if mol is not None else hazards_for(repr(species))
        if record is not None:
            if record not in found:
                found.append(record)
        else:
            unassessed.append(repr(species))
    return tuple(found), tuple(unassessed)


def screen_edge(
    edge: AnyEdge,
    *,
    exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV,
    structures: "dict[Formula, Molecule] | None" = None,
) -> HazardProfile:
    """Screen one edge for hazards. Always returns a profile -- it never hides or refuses an edge.

    ``structures`` optionally maps a species ``Formula`` to its actual :class:`Molecule`. Where a
    species is structure-resolved, its ISOMER-specific hazards and exact energetics are used, and it
    no longer triggers ``ISOMER_ASSUMED`` -- the isomer is *known*, not assumed. Species left at
    formula level behave exactly as before (loud ambiguity).
    """
    structures = structures or {}
    energy = assess_edge_energy(edge, structures=structures)
    flags: list[HazardFlag] = []
    if not energy.covered:
        flags.append(HazardFlag.ENERGETICS_UNKNOWN)
        note = (
            f"energetics unassessed — no reference formation enthalpy for "
            f"{', '.join(energy.uncovered_species)}; UNKNOWN is not safe."
        )
    else:
        # the enthalpy depends on which isomer of a formula-level species this is whenever the
        # tabulated interval is non-degenerate -- fire on any real spread, not only a sign flip.
        if energy.assembly_lo_ev != energy.assembly_hi_ev:
            flags.append(HazardFlag.ISOMER_AMBIGUOUS)
        # exothermic if the interval is (robustly) negative beyond the threshold, or if it could
        # be strongly exothermic on one isomer -- either way the chemist should see it.
        if energy.assembly_lo_ev is not None and energy.assembly_lo_ev < -exotherm_threshold_ev:
            flags.append(HazardFlag.EXOTHERMIC_ASSEMBLY)
        lo, hi = energy.assembly_lo_ev, energy.assembly_hi_ev
        span = f"{lo:.2f} eV" if lo == hi else f"[{lo:.2f}, {hi:.2f}] eV"
        note = f"assembly enthalpy {span} (0 K formation balance; negative = releases heat)."
    # attach sourced qualitative hazards -- inform, never neuter -- AND surface the coverage gaps
    hazards, unassessed = _collect_species_hazards(edge, structures)
    if hazards:
        flags.append(HazardFlag.DOCUMENTED_HAZARD)
        note = note + " DOCUMENTED HAZARDS -- " + "; ".join(
            f"{h.name}: {h.summary}" for h in hazards
        ) + "."
    if unassessed:
        flags.append(HazardFlag.HAZARDS_UNASSESSED)
        note = note + " HAZARDS UNASSESSED for " + ", ".join(unassessed) + (
            " -- no sourced hazard record; UNKNOWN is not safe."
        )
    # isomer honesty: a specific-isomer name/hazard attached to a species whose STRUCTURE is not
    # known is an ASSUMPTION (a formula-level node does not pin structure). A structure-RESOLVED
    # species is known, not assumed, so it does not raise the flag -- which is exactly the point of
    # isomer-keying: the flag retires as structures become available.
    assumed = False
    for species in _edge_species(edge):
        if not resolve_names(species):
            continue  # this composition names no registered isomer -> nothing to assume
        mol = structures.get(species)
        if mol is None or resolve_structure(mol) is None:
            assumed = True  # a name would be attached at formula level -> an assumption
            break
    if assumed:
        flags.append(HazardFlag.ISOMER_ASSUMED)
    return HazardProfile(energy, tuple(flags), note, hazards)


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
    """One reviewed edge (plain or mediated): edge, coherence, safety profile, and conditions.

    ``conditions`` is a C0 :class:`~smartchem.conditions.ConditionEnvelope` — sourced where a
    reference documents the reaction, the loud ``unknown()`` otherwise (the usual case).
    """

    edge: AnyEdge
    coherence: float
    hazard: HazardProfile
    conditions: ConditionEnvelope = _UNKNOWN_CONDITIONS
    #: ``(formula_repr, definitive_isomer_name)`` pairs for species whose STRUCTURE is known -- set by
    #: the structure-resolved review path so naming is definitive rather than a formula-level guess.
    structure_names: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if type(self.edge) not in (DecompositionEdge, MediatedEdge):
            raise TypeError("edge must be a DecompositionEdge or MediatedEdge")
        if type(self.hazard) is not HazardProfile:
            raise TypeError("hazard must be a HazardProfile")
        if type(self.conditions) is not ConditionEnvelope:
            raise TypeError("conditions must be a ConditionEnvelope")
        if type(self.structure_names) is not tuple or any(
            type(p) is not tuple or len(p) != 2 for p in self.structure_names
        ):
            raise TypeError("structure_names must be a tuple of (formula_repr, name) pairs")

    @property
    def mediated(self) -> bool:
        return type(self.edge) is MediatedEdge

    @property
    def compound_names(self) -> tuple[tuple[str, str], ...]:
        """``(formula_repr, display_name)`` for each species this edge touches that resolves to a name.

        A species whose STRUCTURE is known (present in :attr:`structure_names`) is named definitively.
        Otherwise the name is formula-level: a composition with one registered isomer names it, and a
        composition with SEVERAL isomers is shown ambiguously (``"paracetamol or 4-aminophenyl
        acetate"``) rather than silently picking one -- the honest form now that a formula can name
        more than one compound. An unresolved formula is simply absent here, never renamed by guess.
        """
        resolved = dict(self.structure_names)
        pairs: list[tuple[str, str]] = []
        seen: set[str] = set()
        for species in _edge_species(self.edge):
            key = repr(species)
            if key in seen:
                continue
            seen.add(key)
            if key in resolved:
                pairs.append((key, resolved[key]))       # structure-resolved: definitive
                continue
            names = resolve_names(species)
            if names:
                display = names[0] if len(names) == 1 else " or ".join(sorted(names))
                pairs.append((key, display))
        return tuple(pairs)

    def named_equation(self) -> str:
        """The edge equation with each recognised formula annotated by its assumed compound name.

        The annotation is the registry's known isomer of a *formula-level* node, not a structural
        identity claim: a bare ``C2H4O2`` node is equally methyl formate, so the name is an
        assumption the co-located ``ISOMER_ASSUMED`` hazard flag marks. Whole-token replacement only,
        so ``H2O`` is never matched inside ``H2O2``.
        """
        names = dict(self.compound_names)
        tokens = self.edge.equation().split(" ")
        return " ".join(f"{t} ({names[t]})" if t in names else t for t in tokens)


def _review_key(review: "EdgeReview") -> tuple:
    # most chemically coherent first; break ties by the edge's own canonical order
    return (-review.coherence, review.edge.digest)


def review_edges(
    edges,
    *,
    exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV,
    conditions_source=reaction_conditions,
) -> tuple[str, tuple[EdgeReview, ...]]:
    """Rank any mix of plain and mediated edges by coherence; attach safety and conditions to each.

    Returns ``(banner, reviews)``, most chemically coherent first. No edge is ever dropped — the
    review *informs*, it does not censor. ``conditions_source(edge) -> ConditionEnvelope`` supplies
    sourced conditions where known (the loud ``unknown()`` otherwise).
    """
    reviews = tuple(
        sorted(
            (
                EdgeReview(
                    e,
                    coherence_score(e),
                    screen_edge(e, exotherm_threshold_ev=exotherm_threshold_ev),
                    conditions_source(e),
                )
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
    conditions_source=reaction_conditions,
) -> tuple[str, tuple[EdgeReview, ...]]:
    """Rank a graph's edges by structural coherence and attach a safety profile to each.

    Returns ``(banner, reviews)``. No edge is ever dropped. Restrict to one reactant's direct
    decompositions with ``reactant``.
    """
    if type(graph) is not DecompositionGraph:
        raise TypeError("graph must be a DecompositionGraph")
    edges = graph.edges_from(reactant) if reactant is not None else graph.edges
    return review_edges(
        edges, exotherm_threshold_ev=exotherm_threshold_ev, conditions_source=conditions_source
    )


def decompile_and_review(
    target: "str | dict[str, int] | Formula",
    inventory: "tuple[Formula, ...] | tuple[str, ...]" = (),
    medium: "tuple[Formula, ...] | tuple[str, ...]" = (),
    *,
    exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV,
    max_reagent_instances: int = 1,
    budget: int = 200_000,
    conditions_source=reaction_conditions,
) -> tuple[str, tuple[EdgeReview, ...]]:
    """The unified chemist-facing view of one target's direct decompositions.

    Generates both the plain (own-atoms) edges and the mediated (solution-assisted) edges over the
    declared ``inventory`` + ``medium``, then reviews them together — so a mediated formal candidate
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
    plain, plain_complete = admissible_edges(tf, inv, budget=budget)
    mediated, mediated_complete = mediated_edges(
        tf, inv, medium, max_reagent_instances=max_reagent_instances, budget=budget
    )
    banner, reviews = review_edges(
        plain + mediated,
        exotherm_threshold_ev=exotherm_threshold_ev,
        conditions_source=conditions_source,
    )
    if plain_complete and mediated_complete:
        search_line = (
            "SEARCH STATUS: COMPLETE_WITHIN_DECLARED_DIRECT-EDGE BOUNDS (formula/mediated grammar only; "
            "not all chemistry)."
        )
    else:
        incomplete = ", ".join(
            name for name, complete in (("plain", plain_complete), ("mediated", mediated_complete))
            if not complete
        )
        search_line = (
            f"SEARCH STATUS: INCOMPLETE_BUDGET ({incomplete}); returned reviews are a partial sample and "
            "absence is not evidence that an edge does not exist."
        )
    return f"{banner}\n{search_line}", reviews


def structures_of(capped) -> "dict[Formula, Molecule]":
    """The structure context for a :class:`~smartchem.structure_descent.CappedScission`.

    Maps each species' composition ``Formula`` to its actual :class:`Molecule` (reactant, reagents,
    products), the mapping :func:`screen_edge`/:func:`assess_edge_energy` consume to resolve isomers.
    (A degenerate edge carrying two distinct isomers of one formula on the same side would collide
    here; structure-resolved review of such an edge is a documented future refinement.)
    """
    out: "dict[Formula, Molecule]" = {}
    for molecule in (capped.reactant, *capped.reagents, *capped.products):
        out[Formula.of(molecule.formula, molecule.charge)] = molecule
    return out


def review_capped_scission(
    capped,
    *,
    exotherm_threshold_ev: float = _DEFAULT_EXOTHERM_THRESHOLD_EV,
    conditions_source=reaction_conditions,
) -> EdgeReview:
    """Review a structure-derived ``CappedScission`` with ISOMER-RESOLVED evidence.

    Its :meth:`~smartchem.structure_descent.CappedScission.forget` ``MediatedEdge`` is screened with
    the actual reactant/product STRUCTURES, so hazards and energetics attach per isomer (paracetamol's
    own, not the ambiguous ``C8H9NO2`` interval), naming is definitive, and ``ISOMER_ASSUMED`` /
    ``ISOMER_AMBIGUOUS`` retire wherever the structure is known. This is the payoff of isomer-keying:
    a structure-derived reaction is reviewed at structure resolution, not formula resolution.
    """
    edge = capped.forget()
    structures = structures_of(capped)
    resolved_names: list[tuple[str, str]] = []
    for formula, molecule in structures.items():
        structure = resolve_structure(molecule)
        if structure is not None:
            resolved_names.append((repr(formula), structure.name))
    return EdgeReview(
        edge,
        coherence_score(edge),
        screen_edge(edge, exotherm_threshold_ev=exotherm_threshold_ev, structures=structures),
        conditions_source(edge),
        tuple(resolved_names),
    )
