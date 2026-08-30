"""M-4 v2: the W3 boundary, made EXECUTABLE.

Part 13 classifies several capabilities as BOUNDARY -- things W3 forbids the engine to *claim*,
because they are physical predictions, not the graph/conservation facts this package certifies. A
boundary is not an unfinished feature; it is a line the engine must refuse to cross. This module
turns that refusal from a paragraph into code, so a test can prove the line holds:

* **Which cleavage actually happens** is not answered *by the formal engine itself*. The structure engine
  enumerates *every* valence-valid rewrite; ordering them by an INVENTED, ungrounded reactivity heuristic
  would be fabrication. :func:`evidence_ranking` orders by graded evidence -- SOURCED facts present
  (declared conditions, documented hazards), loudly ``UNRANKED`` when there is no basis. Ordering by a
  value from an ESTABLISHED, validated model (a computed feasibility/energy, each labelled with its grade)
  is admissible and lives in the experiment-compiler layer (roadmap M1+), not here; the formal engine stays
  enumerative and attaches graded evidence, it does not invent a ranking.
* **Stereochemistry** is not represented (bond graphs are constitutional) and not claimed.
  :func:`stereo_status` *detects* where stereochemistry exists -- tetrahedral stereocentres, potential
  E/Z double bonds -- and reports it as ``CONSTITUTIONAL_ONLY``, so the silence is explicit and
  auditable rather than a quiet omission. Detection is a sound LOWER bound (it uses 1-WL colours,
  which cannot separate every orbit), which is the safe direction: it never under-warns by claiming a
  centre is absent when WL merely could not resolve it.
* **Tautomer / resonance preference** is not claimed. :func:`tautomerizable` detects the classic
  keto-enol motif (a carbonyl with an alpha C-H); the drawn form is one of several and which
  dominates is physical.

Nothing here computes chemistry. It detects graph motifs and refuses to say more than the graph does.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .category import Molecule, _wl_colours
from .contracts import Digestible

__all__ = [
    "BOUNDARY_SCHEMA",
    "StereoRepresentation",
    "StereoStatus",
    "RankingBasis",
    "EvidenceRanking",
    "SpeciesClass",
    "stereocenters",
    "cis_trans_candidates",
    "stereo_status",
    "tautomerizable",
    "evidence_ranking",
    "species_class",
    "stability_caveat",
]

BOUNDARY_SCHEMA = "smartchem.decompiler_boundary/w3-v1"


def _neighbours(molecule: Molecule) -> list[list[tuple[int, int]]]:
    """Per-atom adjacency as ``(neighbour_index, bond_order)`` lists."""
    adj: list[list[tuple[int, int]]] = [[] for _ in molecule.atoms]
    for b in molecule.bonds:
        adj[b.i].append((b.j, b.order))
        adj[b.j].append((b.i, b.order))
    return adj


def stereocenters(molecule: Molecule) -> tuple[int, ...]:
    """Atom indices that are DEFINITE tetrahedral stereocentres.

    A stereocentre here is an atom with exactly four single-bond neighbours whose substituents are all
    distinct -- decided by the four neighbours carrying four *distinct 1-WL colours*, which proves the
    substituent subtrees genuinely differ. Because 1-WL is a coarsening of the true orbits, this is a
    SOUND LOWER bound: every atom returned really is a stereocentre, but a centre whose distinct
    substituents WL failed to separate is conservatively omitted rather than falsely denied. That
    incompleteness is the safe direction for a boundary that exists to avoid over-claiming.
    """
    colours = _wl_colours(molecule.atoms, molecule.bonds)
    adj = _neighbours(molecule)
    out: list[int] = []
    for i in range(len(molecule.atoms)):
        singles = [(j, order) for j, order in adj[i] if order == 1]
        if len(singles) != 4 or len(adj[i]) != 4:
            continue  # not a saturated four-coordinate centre
        neighbour_colours = [colours[j] for j, _ in singles]
        if len(set(neighbour_colours)) == 4:
            out.append(i)
    return tuple(out)


def _is_bridge(molecule: Molecule, bond) -> bool:
    """Whether removing ``bond`` disconnects its two endpoints (i.e. the bond is not in a ring)."""
    adj: dict[int, set[int]] = {i: set() for i in range(len(molecule.atoms))}
    for b in molecule.bonds:
        if b == bond:
            continue
        adj[b.i].add(b.j)
        adj[b.j].add(b.i)
    seen = {bond.i}
    stack = [bond.i]
    while stack:
        cur = stack.pop()
        for nxt in adj[cur] - seen:
            seen.add(nxt)
            stack.append(nxt)
    return bond.j not in seen


def cis_trans_candidates(molecule: Molecule) -> tuple[tuple[int, int], ...]:
    """Double bonds ``(i, j)`` that could carry E/Z geometry.

    Each end of the double bond must bear two substituents with distinct 1-WL colours (so the two
    faces are distinguishable), AND the bond must be a BRIDGE -- a ring double bond has no E/Z (and an
    aromatic ring drawn in one Kekule form must not be mistaken for a stereo element, which is the
    aromaticity boundary, a different concern). Same soundness note as :func:`stereocenters` -- a
    LOWER bound; a large-ring double bond that could be E/Z is a documented incompleteness.
    """
    colours = _wl_colours(molecule.atoms, molecule.bonds)
    adj = _neighbours(molecule)
    out: list[tuple[int, int]] = []
    for b in molecule.bonds:
        if b.order != 2 or not _is_bridge(molecule, b):
            continue
        ok = True
        for centre, other in ((b.i, b.j), (b.j, b.i)):
            side = [colours[j] for j, _ in adj[centre] if j != other]
            if len(side) != 2 or side[0] == side[1]:
                ok = False
                break
        if ok:
            out.append((b.i, b.j))
    return tuple(out)


class StereoRepresentation(str, Enum):
    CONSTITUTIONAL_ONLY = "CONSTITUTIONAL_ONLY"  # bonds and atoms, no 3D configuration


@dataclass(frozen=True)
class StereoStatus(Digestible):
    """What stereochemistry a structure HAS, and the explicit statement that none of it is claimed."""

    representation: StereoRepresentation
    tetrahedral_stereocenters: tuple[int, ...]
    cis_trans_bonds: tuple[tuple[int, int], ...]
    note: str

    @property
    def is_stereogenic(self) -> bool:
        return bool(self.tetrahedral_stereocenters or self.cis_trans_bonds)


def stereo_status(molecule: Molecule) -> StereoStatus:
    """Report a structure's stereochemistry as detected, and REFUSE to claim any configuration.

    The representation is always ``CONSTITUTIONAL_ONLY``: this package carries connectivity, never a
    3D configuration, so it never claims R/S or E/Z. Where stereochemistry EXISTS it is named (a lower
    bound), so the boundary is auditable -- a chemist sees exactly where a real, unrepresented degree
    of freedom lives, rather than a silent gap.
    """
    centres = stereocenters(molecule)
    ez = cis_trans_candidates(molecule)
    if centres or ez:
        note = (
            f"constitutional graph only: {len(centres)} tetrahedral stereocentre(s) and {len(ez)} "
            f"potential E/Z bond(s) exist here and are NOT represented or claimed (configuration is a "
            f"physical fact this engine does not carry). Detection is a 1-WL lower bound."
        )
    else:
        note = "no stereogenic element detected (1-WL lower bound); representation is constitutional."
    return StereoStatus(StereoRepresentation.CONSTITUTIONAL_ONLY, centres, ez, note)


def tautomerizable(molecule: Molecule) -> tuple[int, ...]:
    """Carbonyl carbons bearing an alpha C-H -- the classic keto-enol tautomer motif.

    Returns the carbonyl carbon indices where an adjacent carbon carries at least one hydrogen, so the
    keto form drawn here has an enol partner. This is DETECTION only: which tautomer dominates is a
    physical claim the engine does not make (the drawn graph is one of several real forms).
    """
    adj = _neighbours(molecule)
    hydrogens = {i for i, s in enumerate(molecule.atoms) if s == "H"}
    out: list[int] = []
    for i, symbol in enumerate(molecule.atoms):
        if symbol != "C":
            continue
        has_carbonyl = any(molecule.atoms[j] == "O" and order == 2 for j, order in adj[i])
        if not has_carbonyl:
            continue
        alpha_carbons = [j for j, _ in adj[i] if molecule.atoms[j] == "C"]
        if any(any(k in hydrogens for k, _ in adj[a]) for a in alpha_carbons):
            out.append(i)
    return tuple(out)


class SpeciesClass(str, Enum):
    """What KIND of species a decomposition intermediate is -- so a reactive one is never presented
    as a stable, bottle-able compound (the honesty half of BUILD #4)."""

    CLOSED = "CLOSED"            # a valence-complete neutral molecule -- a real, isolable compound
    RADICAL = "RADICAL"         # unpaired valence(s): a reactive fragment, not isolable as drawn
    ION = "ION"                 # net charge: exists with a counter-ion, not neutral in isolation
    RADICAL_ION = "RADICAL_ION"  # both


def species_class(species: object) -> SpeciesClass:
    """Classify a decomposition species as CLOSED / RADICAL / ION / RADICAL_ION.

    Accepts a :class:`~smartchem.category.Molecule` (uses its charge) or a
    :class:`~smartchem.structure_descent.Fragment` (uses its ``open_valence_total`` and its molecule's
    charge). A scission fragment carries open valences -> RADICAL; a heterolytic product carries a
    charge -> ION. The point is to keep the review honest: neither is a stable compound, and this is
    what lets a caller say so rather than list a radical beside a real molecule as if they were peers.
    """
    open_valences = int(getattr(species, "open_valence_total", 0) or 0)
    charge = getattr(species, "charge", None)
    if charge is None:
        inner = getattr(species, "molecule", None)
        charge = getattr(inner, "charge", 0) if inner is not None else 0
    radical = open_valences > 0
    ion = charge != 0
    if radical and ion:
        return SpeciesClass.RADICAL_ION
    if radical:
        return SpeciesClass.RADICAL
    if ion:
        return SpeciesClass.ION
    return SpeciesClass.CLOSED


def stability_caveat(species: object) -> str:
    """A one-line honesty caveat for a non-closed species, or ``""`` for a closed molecule.

    A review that surfaces a decomposition intermediate uses this so a reactive fragment is never
    displayed as if it were an isolable compound.
    """
    cls = species_class(species)
    return {
        SpeciesClass.CLOSED: "",
        SpeciesClass.RADICAL: "RADICAL -- an open-valence fragment, reactive and not isolable as drawn",
        SpeciesClass.ION: "ION -- carries a net charge; exists with a counter-ion, not neutral alone",
        SpeciesClass.RADICAL_ION: "RADICAL ION -- open-valence AND charged; highly reactive, not isolable",
    }[cls]


class RankingBasis(str, Enum):
    EVIDENCE_ORDERED = "EVIDENCE_ORDERED"  # ordered by sourced evidence present
    UNRANKED = "UNRANKED"                  # no evidence basis -- the engine refuses to invent an order


@dataclass(frozen=True)
class EvidenceRanking(Digestible):
    """An ordering of reviews by SOURCED evidence, with an explicit basis and a no-prediction note.

    ``order`` is the reviews' indices, most-evidence first. ``basis`` is ``EVIDENCE_ORDERED`` when at
    least one review carries sourced conditions, else ``UNRANKED`` -- and an ``UNRANKED`` result keeps
    the input order untouched, because inventing a reactivity order from nothing is the exact W3
    crossing this refuses. The order is NEVER by computed-energy magnitude or predicted rate.
    """

    basis: RankingBasis
    order: tuple[int, ...]
    note: str


def _evidence_weight(review) -> tuple[int, int]:
    """(has-sourced-conditions, has-documented-hazard) -- presence flags, never a magnitude."""
    conditions = getattr(review, "conditions", None)
    has_conditions = 1 if (conditions is not None and getattr(conditions, "is_declared", False)) else 0
    hazard = getattr(review, "hazard", None)
    flags = getattr(hazard, "flags", ()) if hazard is not None else ()
    has_hazard = 1 if any(getattr(f, "value", f) == "DOCUMENTED_HAZARD" for f in flags) else 0
    return (has_conditions, has_hazard)


def evidence_ranking(reviews) -> EvidenceRanking:
    """Order ``reviews`` by SOURCED evidence PRESENT -- the formal engine's ranking (it attaches graded
    evidence; it never invents an order).

    Reviews with declared conditions rank above those without; documented hazards break ties. This orders by
    the PRESENCE of sourced facts, never by an unsourced reactivity guess. (Ordering by a value from an
    ESTABLISHED model -- a computed feasibility/energy, each graded -- is admissible too, but lives in the
    experiment-compiler layer, e.g. `feasibility` ranking; it is not this formal function's job.) If NO
    review carries sourced conditions there is no evidential basis, and the result is ``UNRANKED`` with the
    input order preserved -- the engine will not manufacture an order.
    """
    reviews = tuple(reviews)
    weights = [_evidence_weight(r) for r in reviews]
    if not any(w[0] for w in weights):
        return EvidenceRanking(
            RankingBasis.UNRANKED,
            tuple(range(len(reviews))),
            "no sourced conditions on any edge: there is no evidence basis to rank these rewrites, and "
            "the engine refuses to invent one. This is not a reactivity prediction.",
        )
    order = tuple(sorted(range(len(reviews)), key=lambda k: weights[k], reverse=True))
    return EvidenceRanking(
        RankingBasis.EVIDENCE_ORDERED,
        order,
        "ordered by SOURCED evidence present (declared conditions, then documented hazards); this "
        "surfaces what is known and is NOT a reactivity, kinetic, or thermodynamic-favourability claim.",
    )
