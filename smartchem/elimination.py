"""Alcohol DEHYDRATION -- the 1,2-elimination slice of #116 (``alcohol -> alkene + H2O``), a type-3 coproduct producer.

THE CLASS.  An alcohol loses the elements of water across two ADJACENT sp3 carbons -- the hydroxyl from C_alpha and a
hydrogen from C_beta -- and the C_alpha--C_beta single bond becomes a C=C.  In the decomposition convention of
``ExperimentStep.from_transform`` the edge's ``reactant`` is the ALKENE (the assembled target), ``reagents`` is
``(water,)`` (consumed by the formal hydration that opens it) and ``products`` is ``(alcohol,)`` (the synthesis
precursor), so ``from_transform`` builds the synthesis step ``alcohol -> alkene + water``, which
:func:`~smartchem.experiment.event_search.classify_event` classifies ``INTRAMOLECULAR_COPRODUCT`` (one connected
precursor, three atoms LARGER than the target, one water coproduct).

WHY THIS IS NOT A TRANSFORM PROVIDER.  The step is rank-INCREASING (precursor = target + H2O), so it can never satisfy
W1 (``len(precursor.atoms) < len(target.atoms)``) and must never enter the decompiler / ``forget()`` path.  Exactly
like :mod:`smartchem.intramolecular_condensation` (lactonization) it is a standalone bounded enumeration consumed only
by the type-3 lane of :func:`~smartchem.experiment.event_search.search_event_routes`, under that search's
``(coproduct_events_left, atom_count, hops_left)`` termination measure, and only when the caller opts in.

SCOPE AND WHAT IS DELIBERATELY NOT CLAIMED.
  * BOTH regiochemistries are enumerated for every qualifying C=C (the hydroxyl on either alkene carbon).  No
    Zaitsev / Hofmann / Markovnikov selectivity is modelled or claimed anywhere: 2-butanol reaches 1-butene AND
    2-butene, each as a structurally valid dehydration, neither ranked over the other.
  * NO skeletal rearrangement.  The forward certificate forms the C=C between the carbinol carbon and one of its OWN
    neighbours, so a 1,2-shift product (neopentyl alcohol -> 2-methyl-2-butene) or a remote alkene (1-butanol ->
    2-butene) is never derived.
  * The HX slice of elimination (``R-X -> alkene + HX``) is out of scope; the coproduct is exactly water.
  * Structural type-validity only (Problem A): an edge never means feasible, favourable or selective.  The acid
    catalyst the class needs is the activator ledger's concern, not this module's.

THE FORWARD CERTIFICATE (:func:`_forward_dehydrations`, shared by the edge and the oracle recognizer).  It re-scans
the precursor's OWN hydroxyls and applies the graph operation (remove O, its H and one H on C_beta; C_alpha--C_beta
order 1 -> 2), admitting a site only when every guard holds:
  1. the leaving O is a terminal hydroxyl: exactly one heavy neighbour (C_alpha) and exactly one H, all single bonds;
  2. C_alpha is an sp3 carbon (four single bonds -- so not a carbonyl, enol or aryl carbon) carrying no heteroatom
     other than the leaving O (a gem-diol / hemiacetal / hemiaminal / halohydrin carbinol is a masked carbonyl or a
     different class);
  3. C_beta is an sp3 carbon with at least one H and only C/H neighbours, so the new C=C carbons carry only C/H
     substituents (no enol, enol ether or enamine is minted);
  4. the new C=C is not in a three-membered ring;
  5. the new C=C does not complete a ring all of whose atoms are pi-capable (a multiply-bonded atom or any non-carbon
     heavy atom) -- an aromatising closure (cyclohexa-2,4-dien-1-ol -> benzene) is deferred.  The check is LOCAL to
     the new bond (a ring path between C_alpha and C_beta), so an exocyclic vinyl next to an arene (1-phenylethanol ->
     styrene) is unaffected.
Because C_alpha and C_beta are sp3 in the precursor, neither carries another multiple bond in the product, so no
cumulene (allene) can be formed.  The result is compared to the target by resonance-canonical identity
(:func:`~smartchem.smiles.resonance_identity`), so a Kekule spelling of an arene substituent cannot mask a match.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .category import Bond, Config, ConservationError, Molecule, Reaction
from .contracts import Digestible

#: Edge schema id (its own, not a scission / lateral / lactonization schema).
DEHYDRATION_SCHEMA = "smartchem.elimination/dehydration-v1"
#: The oracle display name (the 26th class).  The recognizer, the generator's edge stamp and the activator ledger key
#: all import this one constant, so the three cannot drift apart.
DEHYDRATION_CLASS = "dehydration (1,2-elimination, alcohol -> alkene + water)"

#: The conserved coproduct: water, H2O.
_WATER = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))


class EliminationError(ValueError):
    """A proposed dehydration edge failed a certificate (fail-closed)."""


def _adjacency(molecule: Molecule) -> dict[int, list[tuple[int, int]]]:
    """``{atom_index: [(neighbour_index, bond_order), ...]}``."""
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(molecule.atoms))}
    for b in molecule.bonds:
        adj[b.i].append((b.j, b.order))
        adj[b.j].append((b.i, b.order))
    return adj


def _is_sp3_carbon(c: int, atoms, adj) -> bool:
    """A carbon with exactly four SINGLE bonds in the explicit-H graph.  This excludes carbonyl, enol, aryl, alkene
    and alkyne carbons, and an implicit-H carbon (degree < 4), in one test."""
    return atoms[c] == "C" and len(adj[c]) == 4 and all(order == 1 for _n, order in adj[c])


def _pi_capable(x: int, atoms, adj) -> bool:
    """Can atom ``x`` take part in a fully conjugated ring?  True for an atom carrying a multiple bond and, fail-closed,
    for any non-carbon heavy atom (a lone-pair donor such as a pyrrole N or furan O)."""
    if atoms[x] == "H":
        return False
    if atoms[x] != "C":
        return True
    return any(order >= 2 for _n, order in adj[x])


def _closes_pi_ring(a: int, b: int, atoms, adj) -> bool:
    """In the PRODUCT adjacency, is there a path ``a -> ... -> b`` that avoids the direct ``a--b`` bond and whose every
    intermediate atom is pi-capable?  If so the new ``a=b`` completes a fully conjugated ring (aromatisation)."""
    seen = {a}
    queue = deque([a])
    while queue:
        cur = queue.popleft()
        for nxt, _order in adj[cur]:
            if cur == a and nxt == b:
                continue                               # the new double bond itself is not a ring path
            if nxt == b:
                return True
            if nxt in seen or not _pi_capable(nxt, atoms, adj):
                continue
            seen.add(nxt)
            queue.append(nxt)
    return False


def _rebuild(atoms: tuple[str, ...], bonds: frozenset[Bond], drop: set[int], raise_bond: tuple[int, int]) -> Molecule:
    """Rebuild a Molecule with ``drop`` removed and the bond ``raise_bond`` (old indices) raised one order."""
    keep = [i for i in range(len(atoms)) if i not in drop]
    remap = {old: new for new, old in enumerate(keep)}
    key = frozenset(raise_bond)
    new_bonds = set()
    for bd in bonds:
        if bd.i in drop or bd.j in drop:
            continue
        order = bd.order + 1 if frozenset((bd.i, bd.j)) == key else bd.order
        new_bonds.add(Bond(remap[bd.i], remap[bd.j], order))
    return Molecule(tuple(atoms[i] for i in keep), frozenset(new_bonds))


# --------------------------------------------------------------------------------------------------------------------
# The FORWARD certificate: every alkene a precursor reaches by ONE guarded 1,2-dehydration.
# --------------------------------------------------------------------------------------------------------------------

def _dehydration_sites(precursor: Molecule) -> list[tuple[int, int, int, int, int]]:
    """Every guarded site as ``(o, h_o, c_alpha, c_beta, h_beta)`` (guards 1-3 of the module docstring)."""
    atoms = precursor.atoms
    adj = _adjacency(precursor)
    out: list[tuple[int, int, int, int, int]] = []
    for o in range(len(atoms)):
        if atoms[o] != "O" or len(adj[o]) != 2 or any(order != 1 for _n, order in adj[o]):
            continue
        heavy = [x for x, _o in adj[o] if atoms[x] != "H"]
        hs = [x for x, _o in adj[o] if atoms[x] == "H"]
        if len(heavy) != 1 or len(hs) != 1:
            continue                                   # (1) a terminal hydroxyl, not an ether / water / peroxide
        ca = heavy[0]
        if not _is_sp3_carbon(ca, atoms, adj):
            continue                                   # (2) sp3 carbinol carbon (no carbonyl / enol / phenol)
        if any(atoms[x] not in ("C", "H") for x, _o in adj[ca] if x != o):
            continue                                   # (2) no second heteroatom (masked-carbonyl guard)
        for cb, _o in adj[ca]:
            if not _is_sp3_carbon(cb, atoms, adj):
                continue                               # (3) sp3 C_beta (also excludes the cumulene route)
            if any(atoms[x] not in ("C", "H") for x, _o2 in adj[cb]):
                continue                               # (3) the new C=C carries only C/H substituents
            h_beta = [x for x, _o2 in adj[cb] if atoms[x] == "H"]
            if not h_beta:
                continue                               # (3) a hydrogen to eliminate
            out.append((o, hs[0], ca, cb, min(h_beta)))
    return out


def _forward_dehydrations(precursor: Molecule) -> list[Molecule]:
    """Every alkene ``precursor`` reaches by ONE guarded 1,2-dehydration (``-> alkene + H2O``), re-derived from the
    precursor's own hydroxyls.  Distinct by resonance-canonical identity; empty for a charged / stateful species."""
    from .smiles import resonance_identity
    if type(precursor) is not Molecule or precursor.charge != 0 or precursor.state:
        return []
    atoms = precursor.atoms
    adj = _adjacency(precursor)
    out: list[Molecule] = []
    seen: set[str] = set()
    for o, h_o, ca, cb, h_beta in _dehydration_sites(precursor):
        neighbours_a = {x for x, _o in adj[ca]}
        if any(x in neighbours_a for x, _o in adj[cb]):
            continue                                   # (4) C_alpha and C_beta share a neighbour: a 3-membered ring
        try:
            alkene = _rebuild(atoms, precursor.bonds, {o, h_o, h_beta}, (ca, cb))
        except (ValueError, TypeError):
            continue                                   # an invalid rebuild is dropped (fail-closed)
        # (5) the aromatisation guard, read on the PRODUCT graph around the new bond only.
        keep = [i for i in range(len(atoms)) if i not in {o, h_o, h_beta}]
        remap = {old: new for new, old in enumerate(keep)}
        if _closes_pi_ring(remap[ca], remap[cb], alkene.atoms, _adjacency(alkene)):
            continue
        try:
            alkene = alkene.canonical()
            key = resonance_identity(alkene)
        except (ValueError, TypeError, NotImplementedError):
            continue
        if key not in seen:
            seen.add(key)
            out.append(alkene)
    return out


def _dehydrates_to(precursor: Molecule, target: Molecule) -> bool:
    """Load-bearing certificate: does ``precursor`` reach EXACTLY ``target`` (+ one water) by one guarded
    1,2-dehydration?  Re-derived from the precursor's own groups and compared by resonance-canonical identity, so a
    fabricated precursor that merely balances mass is refused."""
    from .smiles import resonance_identity
    if type(target) is not Molecule or target.charge != 0 or target.state:
        return False
    try:
        want = resonance_identity(target)
    except (ValueError, TypeError, NotImplementedError):
        return False
    return any(resonance_identity(alkene) == want for alkene in _forward_dehydrations(precursor))


# --------------------------------------------------------------------------------------------------------------------
# The RETRO generator: add H-OH across each C=C of the target, in both orientations.
# --------------------------------------------------------------------------------------------------------------------

def _alkene_sites(target: Molecule) -> list[tuple[int, int]]:
    """Every carbon-carbon double bond of ``target`` as an ordered pair ``(a, b)`` with ``a < b`` -- the candidate
    sites.  The chemistry guards are NOT applied here; the forward certificate applies them to each built precursor,
    so a candidate that fails is still EXAMINED (and dropped), which keeps ``exhaustive`` a coverage fact."""
    atoms = target.atoms
    return sorted((min(b.i, b.j), max(b.i, b.j)) for b in target.bonds
                  if b.order == 2 and atoms[b.i] == "C" and atoms[b.j] == "C")


def _hydrate(target: Molecule, c_oh: int, c_h: int) -> Molecule:
    """Add H-OH across the ``c_oh = c_h`` double bond: the bond drops to order 1, ``c_oh`` gains -O-H, ``c_h`` gains
    -H.  Returns the candidate alcohol precursor (canonical)."""
    atoms = target.atoms
    n = len(atoms)
    o_new, h_o, h_c = n, n + 1, n + 2
    key = frozenset((c_oh, c_h))
    bonds = set()
    for bd in target.bonds:
        if frozenset((bd.i, bd.j)) == key:
            bonds.add(Bond(bd.i, bd.j, bd.order - 1))
        else:
            bonds.add(bd)
    bonds |= {Bond(c_oh, o_new, 1), Bond(o_new, h_o, 1), Bond(c_h, h_c, 1)}
    return Molecule(atoms + ("O", "H", "H"), frozenset(bonds)).canonical()


@dataclass(frozen=True)
class DehydrationEdge(Digestible):
    """An alcohol dehydration stored in the DECOMPOSITION convention (so ``ExperimentStep.from_transform`` builds the
    synthesis ``alcohol -> alkene + water``):

    * ``reactant`` -- the alkene TARGET;
    * ``products`` -- ``(alcohol,)``, the single connected synthesis precursor (three atoms LARGER than the target);
    * ``reagents`` -- ``(water,)``, the coproduct liberated by the synthesis.

    Certificates at construction: conservation (an independent ``Reaction``), a connected single precursor, and the
    load-bearing forward re-derivation :func:`_dehydrates_to`.  Structural type-validity ONLY."""

    schema_version: str
    reactant: Molecule
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    reaction_class: str

    def __post_init__(self) -> None:
        if self.schema_version != DEHYDRATION_SCHEMA:
            raise EliminationError(f"schema_version must be exactly {DEHYDRATION_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise EliminationError("reactant (the alkene target) must be a Molecule")
        if (type(self.products) is not tuple or len(self.products) != 1
                or type(self.products[0]) is not Molecule):
            raise EliminationError("products must be exactly one precursor Molecule (the alcohol)")
        if self.reagents != (_WATER,):
            raise EliminationError("the dehydration coproduct is exactly one water molecule")
        if self.reaction_class != DEHYDRATION_CLASS:
            raise EliminationError(f"reaction_class must be {DEHYDRATION_CLASS!r}")
        precursor = self.products[0]
        try:
            Reaction(Config.of(self.reactant, *self.reagents), Config.of(*self.products), name="dehydration")
        except ConservationError as clash:
            raise EliminationError(f"dehydration does not conserve mass/charge: {clash}") from clash
        if len(precursor.atoms) > 1 and not precursor.is_connected():
            raise EliminationError("the precursor must be one connected molecule")
        if not _dehydrates_to(precursor, self.reactant):
            raise EliminationError(
                "not a guarded 1,2-dehydration of this precursor (a fabricated elimination edge is refused)")

    def equation(self) -> str:
        return f"{self.products[0]!r} -> {self.reactant!r} + {self.reagents[0]!r}"

    def reaction_center(self):
        """No centre is minted: the oracle re-derives recognition from the molecules (ISSUE-126)."""
        return None

    def __repr__(self) -> str:
        return f"DehydrationEdge({self.equation()})"


@dataclass(frozen=True)
class DehydrationEnumeration:
    """A bounded dehydration enumeration that REPORTS whether it was exhaustive (the type-3 producer contract shared
    with :class:`~smartchem.intramolecular_condensation.LactonizationEnumeration`).  ``exhaustive`` is True iff every
    C=C candidate site was examined (``sites_examined >= sites_total``); when False the edge set is a LOWER BOUND and
    must not feed a COMPLETE search receipt.  A site whose certificate fails is still examined."""
    edges: tuple
    exhaustive: bool
    sites_total: int          # candidate C=C sites the target has
    sites_examined: int       # min(sites_total, budget)
    budget: int

    def __post_init__(self) -> None:
        if self.exhaustive != (self.sites_examined >= self.sites_total):
            raise EliminationError("DehydrationEnumeration.exhaustive disagrees with sites_examined/sites_total")


def retro_dehydration_enumeration(target: Molecule, *, budget: int = 10_000) -> DehydrationEnumeration:
    """Bounded enumeration of dehydration edges assembling ``target`` (an alkene) from an alcohol + expelled water.
    For each C=C site (up to ``budget`` sites) both orientations of H-OH addition are built, and each candidate
    precursor is kept only if the forward certificate re-derives ``target`` exactly.  Fail-closed: a charged / stateful
    target has nothing to enumerate (vacuously exhaustive).  Read ``exhaustive`` before treating the set as complete."""
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    if not (isinstance(budget, int) and not isinstance(budget, bool) and budget >= 1):
        raise EliminationError("budget must be an int >= 1")
    if target.charge != 0 or target.state:
        return DehydrationEnumeration((), True, 0, 0, budget)
    from .smiles import resonance_identity
    sites = _alkene_sites(target)
    sites_total = len(sites)
    sites_examined = min(sites_total, budget)
    edges: list[DehydrationEdge] = []
    seen: set[str] = set()
    for a, b in sites[:budget]:
        for c_oh, c_h in ((a, b), (b, a)):           # BOTH regiochemistries; no selectivity is claimed
            try:
                precursor = _hydrate(target, c_oh, c_h)
                key = resonance_identity(precursor)
            except (ValueError, TypeError, NotImplementedError):
                continue
            if key in seen:
                continue
            try:
                edge = DehydrationEdge(DEHYDRATION_SCHEMA, target, (precursor,), (_WATER,), DEHYDRATION_CLASS)
            except EliminationError:
                continue                               # a candidate whose certificate fails is dropped
            seen.add(key)
            edges.append(edge)
    return DehydrationEnumeration(tuple(edges), sites_examined >= sites_total, sites_total, sites_examined, budget)


def retro_dehydration_edges(target: Molecule, *, budget: int = 10_000) -> tuple[DehydrationEdge, ...]:
    """The edge tuple of :func:`retro_dehydration_enumeration` (use the enumeration to read ``exhaustive``)."""
    return retro_dehydration_enumeration(target, budget=budget).edges
