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
order 1 -> 2).  It is a POSITIVE SAFE-SET: a site is admitted only when EVERY condition below holds; anything else
abstains (the standing rule that a hand-enumerated decline list over an unbounded hazard space leaks).
  1. the leaving O is a terminal hydroxyl: exactly one heavy neighbour (C_alpha) and exactly one H, all single bonds;
  2. C_alpha is an sp3 carbon (four single bonds -- so not a carbonyl, enol or aryl carbon) carrying no heteroatom
     other than the leaving O (a gem-diol / hemiacetal / hemiaminal / halohydrin carbinol is a masked carbonyl or a
     different class);
  3. C_beta is an sp3 carbon with at least one H and only C/H neighbours, so the new C=C carbons carry only C/H
     substituents (no enol, enol ether or enamine is minted);
  (a) C_alpha and C_beta are each acyclic or lie in a MONOCYCLIC ring system (the ring bonds connected to the atom
      form exactly one cycle).  This excludes every bridgehead, fusion and spiro atom -- so every anti-Bredt product
      (1-norbornanol, 1-adamantanol, bicyclo[1.1.1]pentan-1-ol, cubanol, bicyclo[3.3.1]nonan-1-ol) -- and, as an
      ACCEPTED coverage loss, every dehydration inside a fused or bridged system: decalols -> octalins, indanols,
      tetralols, 2-norbornanol (the textbook Wagner-Meerwein substrate);
  (b) that ring, where present, has at least five members (no cyclopropene / cyclobutene / methylenecyclopropane);
  (c) no carbon neighbour of C_alpha or C_beta (other than each other) lies on a ring of size <= 4 -- the
      cyclopropyl- / cyclobutyl-carbinyl rearrangement;
  (d) no carbon neighbour of C_alpha is quaternary (no H, four heavy neighbours) -- the Wagner-Meerwein / neopentyl
      shift;
  (e) no carbon neighbour of C_alpha bears a hydroxyl -- vicinal diols (pinacol / semipinacol) are out;
  (e') the NEIGHBOURHOOD is whitelisted, not the hazards: every heavy atom within two bonds of C_alpha or C_beta (the
      leaving O excepted) is CARBON, with one allowance -- a carbonyl / carboxyl / ester / nitrile carbon bonded to
      C_beta, whose own O / N atoms are then allowed (the beta-hydroxy-carbonyl E1cB scope).  A halogen, N, O, S, Si,
      B, P or any other element within radius two abstains (beta-halo / beta-amino / beta-alkoxy alcohols, Peterson
      and deboronation substrates, 1,3-diols, heteroaryl or ring-heteroatom neighbours: accepted coverage loss);
  (f') after the edit, no ring containing C_alpha or C_beta (this covers a C=C exocyclic to that ring) has all of its
      atoms but AT MOST ONE pi-capable (pi-capable = carrying a multiple bond, or any non-carbon heavy atom) --
      whatever that one atom carries.  That excludes aromatising closures (cyclohexa-2,4-dien-1-ol -> benzene),
      aromatic tautomers and their conjugate acids (isotoluenes, semibenzenes, dienone-phenol substrates, the
      4-picoline anhydrobase, fulvenes, 2H-pyrans incl. 2,2-dimethyl) and, as accepted coverage loss, cyclopentadiene
      / cycloheptatriene formation.  Only the ring the edit touches is read, so an arene beside an exocyclic C=C
      (1-phenylethanol -> styrene) is unaffected;
  (g) both species closed-shell, neutral, stateless and isotopically UNLABELLED (no ``D`` / ``T`` / mass-number atom
      symbol) -- isotopic identity is outside 1.x (#130).
COST (h).  The retro producer builds each precursor POSITIONALLY (target indices kept, O/H/H appended) and certifies
only the site it built; every certificate first tries the positional fast path (a safe-set site whose product IS the
target graph) before the global canonical re-derivation, so a producer edge is certified without canonicalising.
Because C_alpha and C_beta are sp3 in the precursor, neither carries another multiple bond in the product, so no
cumulene (allene) can be formed.  A beta-hydroxy carbonyl (aldol -> enone, often E1cB) is DELIBERATELY inside the
safe set: its new C=C carries only C/H substituents and none of (a)-(g) applies ((e') excuses exactly the O/N of
that beta acyl carbon, reached through it).  The result is compared to the
target by resonance-canonical identity (:func:`~smartchem.smiles.resonance_identity`), so a Kekule spelling of an
arene substituent cannot mask a match.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass

from .category import Bond, Molecule
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


def _connected_without(adj, a: int, b: int, *, skip_edge: tuple[int, int] | None = None,
                       skip_atom: int | None = None) -> int | None:
    """BFS distance from ``a`` to ``b`` avoiding the edge ``skip_edge`` and/or the atom ``skip_atom``; None if cut."""
    dist = {a: 0}
    queue = deque([a])
    while queue:
        cur = queue.popleft()
        for nxt, _order in adj[cur]:
            if nxt == skip_atom or nxt in dist:
                continue
            if skip_edge is not None and {cur, nxt} == set(skip_edge):
                continue
            dist[nxt] = dist[cur] + 1
            if nxt == b:
                return dist[nxt]
            queue.append(nxt)
    return None


class _Rings:
    """Ring facts of one molecule, by edge-deletion connectivity (a bond is a ring bond iff its endpoints stay
    connected without it)."""

    def __init__(self, atoms, adj) -> None:
        self.adj = adj
        self.ring_nbrs: dict[int, list[int]] = {i: [] for i in adj}
        for i in adj:
            if atoms[i] == "H":
                continue
            for j, _order in adj[i]:
                if j > i and atoms[j] != "H" and _connected_without(adj, i, j, skip_edge=(i, j)) is not None:
                    self.ring_nbrs[i].append(j)
                    self.ring_nbrs[j].append(i)

    def system(self, x: int) -> tuple[set[int], int]:
        """``(atoms, ring_bond_count)`` of the ring system reached from ``x`` through ring bonds."""
        seen = {x}
        stack = [x]
        while stack:
            for nxt in self.ring_nbrs[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        edges = sum(len(self.ring_nbrs[v]) for v in seen) // 2
        return seen, edges

    def monocycle(self, x: int) -> "set[int] | None":
        """The atoms of ``x``'s ring when its ring system is ONE cycle; ``set()`` when acyclic; None when polycyclic."""
        if not self.ring_nbrs[x]:
            return set()
        members, edges = self.system(x)
        return members if edges == len(members) else None

    def smallest_ring_through(self, n: int) -> int | None:
        """Size of the smallest ring through atom ``n`` (min over pairs of its ring neighbours of the path length
        around ``n`` + 2), or None when ``n`` is on no ring."""
        nbrs = self.ring_nbrs[n]
        best = None
        for k, u in enumerate(nbrs):
            for v in nbrs[k + 1:]:
                d = _connected_without(self.adj, u, v, skip_atom=n)
                if d is not None and (best is None or d + 2 < best):
                    best = d + 2
        return best


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
# The FORWARD certificate: every alkene a precursor reaches by ONE safe-set 1,2-dehydration.
# --------------------------------------------------------------------------------------------------------------------

def _bears_hydroxyl(c: int, atoms, adj) -> bool:
    return any(atoms[o] == "O" and any(atoms[h] == "H" for h, _o2 in adj[o]) for o, _o in adj[c])


def _is_quaternary_carbon(c: int, atoms, adj) -> bool:
    return atoms[c] == "C" and len(adj[c]) == 4 and all(atoms[x] != "H" for x, _o in adj[c])


#: (g) isotope labels the model can carry only as an atom symbol.  Isotopic identity is outside 1.x (#130).
_ISOTOPE_SYMBOLS = frozenset({"D", "T"})


def _unlabelled_closed_shell(mol) -> bool:
    """(g) A neutral, stateless, closed-shell species whose every atom is a plain element symbol (no ``D`` / ``T`` /
    mass-number label).  Anything else is outside the class and refused."""
    if type(mol) is not Molecule or mol.charge != 0 or mol.state:
        return False
    if any(not (sym.isalpha() and sym[0].isupper()) or sym in _ISOTOPE_SYMBOLS for sym in mol.atoms):
        return False
    from .diels_alder import is_closed_shell_neutral
    return is_closed_shell_neutral(mol)


def _acyl_heteroatoms(x: int, atoms, adj) -> "frozenset[int] | None":
    """If ``x`` is a carbonyl / carboxyl / ester / nitrile carbon, the O/N atoms bonded to it; else None.  Exactly one
    of: one ``=O`` plus at most one single-bonded O and otherwise only C/H (aldehyde, ketone, acid, ester); or one
    ``#N`` and otherwise only C/H (nitrile).  An amide, acyl halide, carbonate, imine ... is not on the list."""
    if atoms[x] != "C":
        return None
    dbl_o = [n for n, o in adj[x] if o == 2 and atoms[n] == "O"]
    tri_n = [n for n, o in adj[x] if o == 3 and atoms[n] == "N"]
    single_o = [n for n, o in adj[x] if o == 1 and atoms[n] == "O"]
    others = [n for n, o in adj[x] if atoms[n] not in ("C", "H") and n not in dbl_o + tri_n + single_o]
    if others:
        return None
    if len(dbl_o) == 1 and not tri_n and len(single_o) <= 1:
        return frozenset(dbl_o + single_o)
    if len(tri_n) == 1 and not dbl_o and not single_o:
        return frozenset(tri_n)
    return None


def _neighbourhood_is_carbon(o: int, ca: int, cb: int, atoms, adj) -> bool:
    """(e') Every heavy atom within two bonds of C_alpha or C_beta -- the leaving O excepted -- is carbon, save the
    O/N atoms of a carbonyl / carboxyl / ester / nitrile carbon bonded to C_beta (the beta-hydroxy-carbonyl scope).

    Checked PER BOND, not per atom: a heteroatom is excused only when reached THROUGH that acyl carbon.  The same atom
    reached through any other first-shell atom (an ester / lactone O two bonds from C_alpha via a ring CH2) is not
    excused, so the allowance cannot leak to a beta-alkoxy pattern on the far side of the new C=C.  (The per-atom form
    this replaces was latent, not exploitable: every such path closes a 4- or 5-ring that (a)-(b) / (f') already
    refuse -- but the definition no longer leans on that masking.)"""
    core = {ca, cb, o}
    for v in (ca, cb):
        for n, _o in adj[v]:
            if n in core or atoms[n] == "H":
                continue
            if atoms[n] != "C":
                return False                           # a heteroatom bonded to C_alpha / C_beta
            excused = _acyl_heteroatoms(n, atoms, adj) if v == cb else None
            for m, _o2 in adj[n]:
                if m in core or atoms[m] in ("C", "H"):
                    continue
                if excused is None or m not in excused:
                    return False                       # a heteroatom two bonds out, not via a beta acyl carbon
    return True


def _dehydration_sites(precursor: Molecule) -> list[tuple[int, int, int, int, tuple[int, ...]]]:
    """Every safe-set site as ``(o, h_o, c_alpha, c_beta, h_betas)`` -- conditions 1-3 and (a)-(e') of the module
    docstring ((f') needs the product graph and is applied per product)."""
    atoms = precursor.atoms
    adj = _adjacency(precursor)
    rings: _Rings | None = None
    out: list[tuple[int, int, int, int, tuple[int, ...]]] = []
    for o in range(len(atoms)):
        if atoms[o] != "O" or len(adj[o]) != 2 or any(order != 1 for _n, order in adj[o]):
            continue
        heavy = [x for x, _o in adj[o] if atoms[x] != "H"]
        hs = [x for x, _o in adj[o] if atoms[x] == "H"]
        if len(heavy) != 1 or len(hs) != 1:
            continue                                   # (1) a terminal hydroxyl, not an ether / water / peroxide
        ca = heavy[0]
        if rings is None:
            rings = _Rings(atoms, adj)
        for cb, _o in adj[ca]:
            site = _site_is_safe(o, hs[0], ca, cb, atoms, adj, rings)
            if site is not None:
                out.append(site)
    return out


def _site_is_safe(o: int, h_o: int, ca: int, cb: int, atoms, adj, rings: "_Rings"):
    """Conditions 2-3 and (a)-(e') for ONE site; the site tuple when every one holds, else None."""
    if not _is_sp3_carbon(ca, atoms, adj):
        return None                                    # (2) sp3 carbinol carbon (no carbonyl / enol / phenol)
    if any(atoms[x] not in ("C", "H") for x, _o in adj[ca] if x != o):
        return None                                    # (2) no second heteroatom (masked-carbonyl guard)
    alpha_carbons = [x for x, _o in adj[ca] if atoms[x] == "C"]
    if any(_is_quaternary_carbon(x, atoms, adj) for x in alpha_carbons):
        return None                                    # (d) no quaternary neighbour of C_alpha
    if any(_bears_hydroxyl(x, atoms, adj) for x in alpha_carbons):
        return None                                    # (e) no vicinal hydroxyl (also implied by (e'))
    if cb not in alpha_carbons or not _is_sp3_carbon(cb, atoms, adj):
        return None                                    # (3) sp3 C_beta (also excludes the cumulene route)
    if any(atoms[x] not in ("C", "H") for x, _o in adj[cb]):
        return None                                    # (3) the new C=C carries only C/H substituents
    h_betas = tuple(sorted(x for x, _o in adj[cb] if atoms[x] == "H"))
    if not h_betas:
        return None                                    # (3) a hydrogen to eliminate
    if not _ring_context_is_safe(ca, cb, atoms, adj, rings):
        return None                                    # (a)-(c)
    if not _neighbourhood_is_carbon(o, ca, cb, atoms, adj):
        return None                                    # (e') a heteroatom within two bonds
    return (o, h_o, ca, cb, h_betas)


def _ring_context_is_safe(ca: int, cb: int, atoms, adj, rings: "_Rings") -> bool:
    for x in (ca, cb):
        ring = rings.monocycle(x)
        if ring is None:
            return False                               # (a) bridgehead / fusion / spiro / polycyclic system
        if ring and len(ring) < 5:
            return False                               # (b) a ring of three or four members
    for x, partner in ((ca, cb), (cb, ca)):
        for n, _o in adj[x]:
            if n == partner or atoms[n] != "C":
                continue
            size = rings.smallest_ring_through(n)
            if size is not None and size <= 4:
                return False                           # (c) a cyclopropyl / cyclobutyl neighbour
    return True


def _aromatisable_ring(ring: set[int], atoms, adj) -> bool:
    """(f') on the PRODUCT graph: are all atoms of ``ring`` but at most ONE pi-capable (whatever that one carries)?"""
    return sum(1 for x in ring if not _pi_capable(x, atoms, adj)) <= 1


def _site_product(precursor: Molecule, site, h_beta: int, rings: "_Rings") -> "Molecule | None":
    """The alkene from one safe-set site with ``h_beta`` removed, or None when (f') refuses it.  Positional: atom
    indices are those of ``precursor`` with the three removed atoms dropped (no canonicalisation)."""
    o, h_o, ca, cb, _h_betas = site
    atoms = precursor.atoms
    try:
        alkene = _rebuild(atoms, precursor.bonds, {o, h_o, h_beta}, (ca, cb))
    except (ValueError, TypeError):
        return None
    keep = [i for i in range(len(atoms)) if i not in {o, h_o, h_beta}]
    remap = {old: new for new, old in enumerate(keep)}
    p_adj = _adjacency(alkene)
    for x in (ca, cb):
        ring = rings.monocycle(x)
        if ring and _aromatisable_ring({remap[v] for v in ring}, alkene.atoms, p_adj):
            return None                                # (f') aromatising / aromatic-tautomer ring
    return alkene


def _forward_dehydrations(precursor: Molecule) -> list[Molecule]:
    """Every alkene ``precursor`` reaches by ONE safe-set 1,2-dehydration (``-> alkene + H2O``), re-derived from the
    precursor's own hydroxyls.  Distinct by resonance-canonical identity; empty outside (g)."""
    from .smiles import resonance_identity
    if not _unlabelled_closed_shell(precursor):
        return []
    sites = _dehydration_sites(precursor)
    if not sites:
        return []
    rings = _Rings(precursor.atoms, _adjacency(precursor))
    out: list[Molecule] = []
    seen: set[str] = set()
    for site in sites:
        alkene = _site_product(precursor, site, site[4][0], rings)
        if alkene is None:
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
    """Load-bearing certificate: does ``precursor`` reach EXACTLY ``target`` (+ one water) by one safe-set
    1,2-dehydration?  Re-derived from the precursor's own groups, never from how it was produced.

    Two exact routes, the cheap one first: (i) POSITIONAL -- some safe-set site, with some choice of its beta H, yields
    a graph literally equal to ``target`` (same atoms, same bonds): identical graphs are isomorphic, so this proves the
    match without canonicalising; (ii) otherwise the GLOBAL re-derivation, comparing every safe-set product to the
    target by resonance-canonical identity.  (i) is a sufficient condition for (ii), so the verdict is the same; only
    the cost differs (a producer-built precursor is a positional extension of its target)."""
    from .smiles import resonance_identity
    if not (_unlabelled_closed_shell(precursor) and _unlabelled_closed_shell(target)):
        return False                                   # (g)
    sites = _dehydration_sites(precursor)
    if not sites:
        return False
    rings = _Rings(precursor.atoms, _adjacency(precursor))
    for site in sites:
        for h_beta in site[4]:
            alkene = _site_product(precursor, site, h_beta, rings)
            if alkene is None:
                break                                  # (f') does not depend on which beta H leaves
            if alkene == target:
                return True
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
    -H.  POSITIONAL: the target's atoms keep their indices and O, H(O), H(C) are appended as ``n, n+1, n+2`` -- so the
    precursor's own dehydration at that site rebuilds the target graph exactly (the certificate's fast path)."""
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
    return Molecule(atoms + ("O", "H", "H"), frozenset(bonds))


def _wl_key(mol: Molecule) -> tuple:
    """A RESONANCE-invariant colour-refinement key over CONNECTIVITY ONLY (element + neighbour colours; bond orders are
    deliberately ignored).  A Kekule / resonance change moves only bond orders, so two spellings of one compound always
    get equal keys, and unequal keys prove two candidates are not resonance-identical.  Used only to skip the
    resonance-identity comparison between candidates that cannot be duplicates; the dedup verdict itself is always
    :func:`resonance_identity`.  (A bond-order-aware key split meta-divinylbenzene's two Kekule spellings of ONE
    precursor into two "independent" edges -- one supply counted twice.)  In-process only: ``hash`` is salted."""
    adj = _adjacency(mol)
    colour = {i: hash((a, len(adj[i]))) for i, a in enumerate(mol.atoms)}
    for _round in range(len(mol.atoms)):
        new = {i: hash((colour[i], tuple(sorted(colour[n] for n, _o in adj[i])))) for i in adj}
        if len(set(new.values())) == len(set(colour.values())):
            colour = new
            break
        colour = new
    return tuple(sorted(colour.values()))


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
        if not (_unlabelled_closed_shell(precursor) and _unlabelled_closed_shell(self.reactant)):
            raise EliminationError("(g) both species must be closed-shell, neutral and isotopically unlabelled")
        # Conservation by element and charge arithmetic (precursor = alkene + H2O).  The search's ExperimentStep
        # re-checks it through a real Reaction; doing it here through Config would canonicalise both species.
        want = Counter({k: v for k, v in self.reactant.formula.items() if v}) + Counter({"H": 2, "O": 1})
        have = Counter({k: v for k, v in precursor.formula.items() if v})
        if want != have or precursor.charge != self.reactant.charge:
            raise EliminationError("dehydration does not conserve mass/charge (precursor != alkene + H2O)")
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
    if not _unlabelled_closed_shell(target):
        return DehydrationEnumeration((), True, 0, 0, budget)        # (g): nothing in scope to enumerate
    from .smiles import resonance_identity
    sites = _alkene_sites(target)
    sites_total = len(sites)
    sites_examined = min(sites_total, budget)
    n = len(target.atoms)
    edges: list[DehydrationEdge] = []
    kept: list[tuple[tuple, Molecule]] = []                         # (wl_key, precursor) of every emitted edge
    rings: _Rings | None = None
    for a, b in sites[:budget]:
        for c_oh, c_h in ((a, b), (b, a)):           # BOTH regiochemistries; no selectivity is claimed
            try:
                precursor = _hydrate(target, c_oh, c_h)
            except (ValueError, TypeError):
                continue
            # (h) certify ONLY the site this candidate was built from (O = n, H(O) = n+1, H(C) = n+2); the
            # edge constructor then re-derives it independently (its positional fast path hits this same site).
            p_atoms, p_adj = precursor.atoms, _adjacency(precursor)
            if rings is None:
                rings = _Rings(p_atoms, p_adj)        # ring bonds are identical for every hydrated candidate
            site = _site_is_safe(n, n + 1, c_oh, c_h, p_atoms, p_adj, rings)
            if site is None or _site_product(precursor, site, n + 2, rings) != target:
                continue
            key = _wl_key(precursor)
            dup = False
            for other_key, other in kept:
                if other_key == key:
                    try:
                        dup = resonance_identity(other) == resonance_identity(precursor)
                    except (ValueError, TypeError, NotImplementedError):
                        dup = False
                    if dup:
                        break
            if dup:
                continue
            try:
                edge = DehydrationEdge(DEHYDRATION_SCHEMA, target, (precursor,), (_WATER,), DEHYDRATION_CLASS)
            except EliminationError:
                continue                               # a candidate whose certificate fails is dropped
            kept.append((key, precursor))
            edges.append(edge)
    return DehydrationEnumeration(tuple(edges), sites_examined >= sites_total, sites_total, sites_examined, budget)


def retro_dehydration_edges(target: Molecule, *, budget: int = 10_000) -> tuple[DehydrationEdge, ...]:
    """The edge tuple of :func:`retro_dehydration_enumeration` (use the enumeration to read ``exhaustive``)."""
    return retro_dehydration_enumeration(target, budget=budget).edges
