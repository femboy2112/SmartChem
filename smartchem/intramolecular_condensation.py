"""Intramolecular condensation with a conserved coproduct -- the type-3 event's FIRST real producer (OPERATION XII P2).

THE GAP THIS CLOSES.  ``smartchem.experiment.event_search`` defines three typed event classes; the third,
``INTRAMOLECULAR_COPRODUCT`` -- a single connected principal precursor LARGER than the target, expelling a conserved
coproduct (lactonization, Dieckmann) -- was DEFINED but had ZERO producers: ``CappedScission`` structurally requires
>=2 disconnected product components (#125 arity wall) and no lateral family expels a coproduct, so nothing in the repo
emitted one.  This module is the first generator that does, for the LACTONIZATION subfamily (a cyclic ester formed from
a hydroxy acid, expelling water).

WHY A SHAPE RECOGNIZER CANNOT CERTIFY THIS, AND WHY THE GENERATOR CAN (the P1 hard constraint).
``classify_event`` certifies only the SHAPE of a type-3 step (one connected larger precursor + a coproduct); it CANNOT
tell an intramolecular condensation from an INTERmolecular 1->many fragmentation (a retro-Diels-Alder has the identical
shape) because a constitution-only ``Molecule`` carries no atom-map between precursor and products.  THIS generator does
not have that problem: it BUILDS the step from the precursor's own structure, forming the ring-closing bond between two
atoms that are ALREADY in one connected molecule (the single ``Molecule`` precursor), so the event is intramolecular BY
CONSTRUCTION -- a nonlocal property proven by the model that has the atom-map, never proxied by a shape check.  A
retro-Diels-Alder fragmentation can never be emitted here: the forward op forms exactly ONE new intramolecular bond and
expels only the small water coproduct; it never splits a skeleton into two substantial fragments.

DIRECTION / THE TRANSFORM CONVENTION (``ExperimentStep.from_transform``).  A transform is a DECOMPOSITION
``reactant + reagents -> products`` whose reverse assembles ``reactant``.  For lactonization the synthesis is
``hydroxy_acid -> lactone + water``, so in the decomposition view ``reactant`` is the lactone (the assembled target),
``reagents`` is ``(water,)`` (consumed by the hydrolysis that opens it), and ``products`` is ``(hydroxy_acid,)`` (the
synthesis precursor).  ``from_transform`` then builds the synthesis step ``hydroxy_acid -> lactone + water``, which
``classify_event`` classifies ``INTRAMOLECULAR_COPRODUCT``.

THE CERTIFICATES (conservation alone proves NOTHING -- every condensation balances mass; the re-derivation is the
load-bearing one, the lateral_rewrite lesson).  Built at edge construction:
  1. CONSERVATION via a real :class:`~smartchem.category.Reaction` (shared-nothing with this module).
  2. RE-DERIVATION, independent of how the precursor was generated: the precursor is re-scanned for its OWN carboxylic
     acid + hydroxyl, the forward esterification is applied as a graph op, and the result is compared to the target by
     CANONICAL molecular identity (:meth:`Molecule.canonical`, a trusted separate subsystem).  A fabricated precursor
     that merely balances mass does NOT lactonize to the target and is refused.
  3. INTRAMOLECULARITY: the precursor is ONE connected ``Molecule`` (enforced by construction) and the forward op forms
     a bond WITHIN it -- intramolecular by construction, the property ``classify_event`` cannot see.

SCOPE (Problem A, structural type-validity only).  A found edge means "this is a structurally valid intramolecular
lactonization", NEVER that it is feasible, favourable, or kinetically accessible.  OPT-IN / STANDALONE: like the lateral
rewrites, this is a standalone enumeration -- it is NOT wired into ``search_routes`` or ``search_event_routes`` (that
wiring, with the ``(coproduct_events, atoms, lateral_hops)`` termination proof for the rank-INCREASING retro step, is
the deferred follow-on).  Everything fails CLOSED: a site whose certificates do not pass is DROPPED.
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Bond, Config, ConservationError, Molecule, Reaction
from .contracts import Digestible

#: Edge schema id (its own, not a scission/lateral schema).
INTRAMOLECULAR_CONDENSATION_SCHEMA = "smartchem.intramolecular-condensation/lactonization-v1"
LACTONIZATION_CLASS = "intramolecular-lactonization (hydroxy acid -> lactone + water)"

#: The conserved coproduct of an esterification condensation: water, H2O.
_WATER = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))


class IntramolecularCondensationError(ValueError):
    """A proposed intramolecular-condensation edge failed a certificate (fail-closed)."""


def _adjacency(molecule: Molecule) -> dict[int, list[tuple[int, int]]]:
    """``{atom_index: [(neighbour_index, bond_order), ...]}`` (the repo's standard undirected adjacency idiom)."""
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(molecule.atoms))}
    for b in molecule.bonds:
        adj[b.i].append((b.j, b.order))
        adj[b.j].append((b.i, b.order))
    return adj


def _is_carbonyl(c: int, atoms, adj) -> bool:
    return atoms[c] == "C" and any(order == 2 and atoms[n] == "O" for n, order in adj[c])


def _acyl_is_lactone_like(c: int, o_link: int, atoms, adj) -> bool:
    """Is carbon ``c`` a genuine ESTER/LACTONE acyl carbon through the single-bonded oxygen ``o_link``?  The acyl
    carbon must bear EXACTLY ONE heteroatom besides its carbonyl ``=O`` -- that one being ``o_link`` -- so every other
    substituent is C or H.  This is the guard that keeps the family to true lactones and rejects the look-alikes an
    unguarded 'carbonyl C single-bonded to O in a ring' would admit (evil-morty P2 review):

      * a CARBONATE carbon bears a SECOND single-bonded O  -> rejected (a non-``o_link`` O neighbour);
      * a CARBAMATE carbon bears an N                      -> rejected (a non-C/H neighbour);
      * an ANHYDRIDE bridge's far atom is a 2nd carbonyl C  -> rejected (``o_link``'s alkoxy neighbour is a carbonyl).

    So the precursor the retro yields is a genuine hydroxy-ACID (not a diacid / carbonic-acid half-ester / carbamic
    acid), which is exactly what ``reaction_class = 'intramolecular-lactonization (hydroxy acid -> lactone + water)'``
    claims."""
    for n, order in adj[c]:
        if order == 2 and atoms[n] == "O":
            continue                                   # the carbonyl =O
        if n == o_link:
            continue                                   # the ester linkage O itself
        if atoms[n] not in ("C", "H"):
            return False                               # a SECOND heteroatom on the acyl C (carbonate O / carbamate N)
    alkoxy = [x for x, _o in adj[o_link] if x != c and atoms[x] != "H"]
    return len(alkoxy) == 1 and atoms[alkoxy[0]] == "C" and not _is_carbonyl(alkoxy[0], atoms, adj)


def _bond_order(bonds: frozenset[Bond], i: int, j: int) -> int | None:
    for b in bonds:
        if {b.i, b.j} == {i, j}:
            return b.order
    return None


def _connected_over(n: int, bonds: frozenset[Bond]) -> bool:
    """Is the bond graph over ``n`` atoms connected?  A free function on a raw bond set (NOT via ``Molecule``, which
    REFUSES a disconnected graph at construction) -- so it can answer the RING test "is this bond on a cycle?" by
    checking connectivity of the graph with that bond removed, where a disconnection is the expected, legal answer."""
    if n <= 1:
        return True
    adj: dict[int, set[int]] = {i: set() for i in range(n)}
    for b in bonds:
        adj[b.i].add(b.j)
        adj[b.j].add(b.i)
    seen, stack = {0}, [0]
    while stack:
        for nxt in adj[stack.pop()] - seen:
            seen.add(nxt)
            stack.append(nxt)
    return len(seen) == n


def _drop_atoms(atoms: tuple[str, ...], bonds: frozenset[Bond], drop: set[int],
                add_bonds: frozenset[Bond] = frozenset()) -> Molecule:
    """Rebuild a Molecule with ``drop`` atom indices removed and ``add_bonds`` (in OLD indices) added, re-indexing
    the survivors.  Any bond touching a dropped atom is discarded; survivors' bonds are relabelled to the new compact
    index space.  Raises via ``Molecule`` if the result is disconnected (a certificate, not a silent pass)."""
    keep = [i for i in range(len(atoms)) if i not in drop]
    remap = {old: new for new, old in enumerate(keep)}
    new_atoms = tuple(atoms[i] for i in keep)
    kept_bonds = set()
    for b in bonds | add_bonds:
        if b.i in drop or b.j in drop:
            continue
        kept_bonds.add(Bond(remap[b.i], remap[b.j], b.order))
    return Molecule(new_atoms, frozenset(kept_bonds))


# --------------------------------------------------------------------------------------------------------------------
# The RETRO generator: given a lactone target, open each in-ring ester linkage into its hydroxy-acid precursor.
# --------------------------------------------------------------------------------------------------------------------

def _ring_ester_sites(target: Molecule) -> list[tuple[int, int, int]]:
    """Every in-ring ester linkage of ``target`` as ``(c_acyl, o_ester, o_carbonyl)``: a carbonyl carbon ``c_acyl``
    single-bonded to an ester oxygen ``o_ester`` (which bridges to a second heavy atom, i.e. an ester -O-, not a free
    acid -OH), where the ``c_acyl -- o_ester`` bond lies on a RING (its removal leaves the molecule connected).  The
    ring condition is the structural heart: a forward esterification that CLOSES this bond is intramolecular exactly
    when the two atoms are already connected by another path."""
    atoms, bonds = target.atoms, target.bonds
    adj = _adjacency(target)
    sites: list[tuple[int, int, int]] = []
    for c in range(len(atoms)):
        if not _is_carbonyl(c, atoms, adj):
            continue
        o_carbonyls = [n for n, order in adj[c] if order == 2 and atoms[n] == "O"]
        if len(o_carbonyls) != 1:
            continue                                   # a clean single C=O acyl carbon
        for o_ester, order in adj[c]:
            if order != 1 or atoms[o_ester] != "O":
                continue
            # ester -O- : the bridging oxygen has a heavy neighbour OTHER than c_acyl (the alkoxy carbon). A free
            # acid -OH (heavy neighbour only c_acyl) is NOT an ester linkage and is skipped.
            heavy = [x for x, _o in adj[o_ester] if x != c and atoms[x] != "H"]
            if len(heavy) != 1 or atoms[heavy[0]] != "C":
                continue
            # TRUE LACTONE only: the acyl carbon bears exactly one heteroatom (this o_ester), so a carbonate /
            # carbamate / anhydride ring is NOT opened and mislabeled a lactonization (evil-morty P2 review).
            if not _acyl_is_lactone_like(c, o_ester, atoms, adj):
                continue
            # RING condition: removing c_acyl--o_ester must leave the molecule connected (the bond is on a cycle).
            # Use the raw connectivity test -- a disconnection here is the LEGAL "acyclic ester" answer, which the
            # Molecule constructor would instead raise on.
            if _connected_over(len(atoms), frozenset(b for b in bonds if {b.i, b.j} != {c, o_ester})):
                sites.append((c, o_ester, o_carbonyls[0]))
    return sites


def _open_lactone(target: Molecule, c_acyl: int, o_ester: int) -> Molecule:
    """Open the ring ester at ``(c_acyl, o_ester)`` by adding the elements of water: break ``c_acyl--o_ester``, give
    ``c_acyl`` a new ``-O-H`` (reforming the carboxylic acid) and ``o_ester`` a new ``-H`` (reforming the alcohol).
    The result is the hydroxy-acid precursor, ONE connected molecule (the rest of the ring still links the two ends)."""
    atoms = target.atoms
    n = len(atoms)
    o_new, h_acid, h_alk = n, n + 1, n + 2            # the three water atoms appended
    new_atoms = atoms + ("O", "H", "H")
    bonds = frozenset(b for b in target.bonds if {b.i, b.j} != {c_acyl, o_ester})
    bonds = bonds | {Bond(c_acyl, o_new, 1), Bond(o_new, h_acid, 1), Bond(o_ester, h_alk, 1)}
    return Molecule(new_atoms, bonds).canonical()


# --------------------------------------------------------------------------------------------------------------------
# The FORWARD re-derivation certificate (independent of the retro: re-scans the precursor's own groups).
# --------------------------------------------------------------------------------------------------------------------

def _carboxyl_sites(mol: Molecule, adj, atoms) -> list[tuple[int, int, int]]:
    """Every free carboxylic-acid group as ``(c_acyl, o_acid, h_acid)``: a carbonyl carbon whose single-bonded O has
    NO heavy neighbour but that carbon and bears exactly one H (the acid -O-H)."""
    out: list[tuple[int, int, int]] = []
    for c in range(len(atoms)):
        if not _is_carbonyl(c, atoms, adj):
            continue
        for o_acid, order in adj[c]:
            if order != 1 or atoms[o_acid] != "O":
                continue
            heavy = [x for x, _o in adj[o_acid] if x != c and atoms[x] != "H"]
            hs = [x for x, _o in adj[o_acid] if atoms[x] == "H"]
            if not heavy and len(hs) == 1 and len(adj[o_acid]) == 2:
                # genuine CARBOXYLIC acid: the acyl carbon bears no OTHER heteroatom besides this -OH and its =O,
                # so a carbonate / carbamate carbon (a 2nd single-bonded O / an N) is NOT read as an acid.
                if all(atoms[n] in ("C", "H") for n, o in adj[c]
                       if n != o_acid and not (o == 2 and atoms[n] == "O")):
                    out.append((c, o_acid, hs[0]))
    return out


def _hydroxyl_sites(mol: Molecule, adj, atoms) -> list[tuple[int, int]]:
    """Every ALCOHOL hydroxyl as ``(o_alk, h_alk)``: an O with exactly one heavy neighbour (a carbon) and exactly one
    H, whose carbon is NOT a carbonyl.  The carbonyl exclusion is load-bearing and now actually enforced (it was
    promised in prose but absent -- evil-morty P2 review): without it a carboxyl -OH satisfies every other condition,
    so a DIACID's second acid would be read as an 'alcohol' and lactonize into an anhydride under this label."""
    out: list[tuple[int, int]] = []
    for o in range(len(atoms)):
        if atoms[o] != "O":
            continue
        heavy = [x for x, _o in adj[o] if atoms[x] != "H"]
        hs = [x for x, _o in adj[o] if atoms[x] == "H"]
        if (len(heavy) == 1 and atoms[heavy[0]] == "C" and len(hs) == 1 and len(adj[o]) == 2
                and not _is_carbonyl(heavy[0], atoms, adj)):
            out.append((o, hs[0]))
    return out


def _forward_lactonizations(precursor: Molecule) -> list[Molecule]:
    """Every lactone ``precursor`` reaches by ONE intramolecular esterification (carboxyl + hydroxyl -> ring ester +
    water), re-derived from the precursor's OWN structure.  For each (carboxyl c_acyl/o_acid/h_acid, hydroxyl
    o_alk/h_alk) with o_alk distinct from the acid's oxygen and its carbon not that same acyl carbon: form the new
    ``c_acyl--o_alk`` bond and expel water (drop o_acid, h_acid, h_alk).  Returns the distinct connected products."""
    from .smiles import resonance_identity
    atoms = precursor.atoms
    adj = _adjacency(precursor)
    out: list[Molecule] = []
    seen: set[str] = set()
    for c_acyl, o_acid, h_acid in _carboxyl_sites(precursor, adj, atoms):
        for o_alk, h_alk in _hydroxyl_sites(precursor, adj, atoms):
            if o_alk in (o_acid,):
                continue
            if _bond_order(precursor.bonds, c_acyl, o_alk) is not None:
                continue                               # already bonded -- not a new ester linkage
            c_alk = [x for x, _o in adj[o_alk] if atoms[x] != "H"][0]
            if c_alk == c_acyl:
                continue                               # the alcohol is on the acyl carbon itself (no ring to close)
            try:
                lactone = _drop_atoms(atoms, precursor.bonds, {o_acid, h_acid, h_alk},
                                      add_bonds=frozenset({Bond(c_acyl, o_alk, 1)})).canonical()
            except (ValueError, TypeError):
                continue                               # a disconnecting / invalid op is dropped (fail-closed)
            # dedup by STRUCTURAL identity, never repr(): Molecule.__repr__ is the FORMULA string, so repr-keyed
            # dedup collapses distinct same-formula isomers and can DISCARD the genuine target lactone (a polyol
            # precursor reaches several C_nH_mO_k lactones) -- a false-negative bug the resonance key fixes.
            key = resonance_identity(lactone)
            if key not in seen:
                seen.add(key)
                out.append(lactone)
    return out


def _lactonizes_to(precursor: Molecule, target: Molecule) -> bool:
    """Load-bearing certificate: does ``precursor`` intramolecularly esterify to EXACTLY ``target`` (+ water)?  Re-scans
    the precursor's own carboxyl/hydroxyl groups and compares by canonical identity -- independent of the retro that
    built ``precursor``, so a fabricated precursor that only balances mass is refused."""
    want = target.canonical()
    return any(lactone == want for lactone in _forward_lactonizations(precursor))


@dataclass(frozen=True)
class IntramolecularCondensationEdge(Digestible):
    """An intramolecular lactonization stored in the DECOMPOSITION convention (so ``ExperimentStep.from_transform``
    builds the synthesis ``precursor -> target + water``):

    * ``reactant`` -- the lactone TARGET (the assembled species);
    * ``products`` -- ``(hydroxy_acid,)``, the single connected synthesis precursor (LARGER than the target);
    * ``reagents`` -- ``(water,)``, the conserved coproduct liberated by the synthesis.

    Three certificates run at construction (see the module docstring): conservation (independent ``Reaction``),
    the load-bearing forward re-derivation (:func:`_lactonizes_to`), and intramolecularity (the precursor is one
    connected ``Molecule`` and the re-derivation forms a bond within it).  Structural type-validity ONLY."""

    schema_version: str
    reactant: Molecule
    products: tuple[Molecule, ...]
    reagents: tuple[Molecule, ...]
    reaction_class: str

    def __post_init__(self) -> None:
        if self.schema_version != INTRAMOLECULAR_CONDENSATION_SCHEMA:
            raise IntramolecularCondensationError(
                f"schema_version must be exactly {INTRAMOLECULAR_CONDENSATION_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise IntramolecularCondensationError("reactant (the lactone target) must be a Molecule")
        if (type(self.products) is not tuple or len(self.products) != 1
                or type(self.products[0]) is not Molecule):
            raise IntramolecularCondensationError("products must be exactly one precursor Molecule (the hydroxy acid)")
        if self.reagents != (_WATER,):
            raise IntramolecularCondensationError("the lactonization coproduct is exactly one water molecule")
        if self.reaction_class != LACTONIZATION_CLASS:
            raise IntramolecularCondensationError(f"reaction_class must be {LACTONIZATION_CLASS!r}")
        precursor = self.products[0]
        # (1) CONSERVATION: lactone + water -> hydroxy_acid balances (re-checked the repo's shared-nothing way).
        try:
            Reaction(Config.of(self.reactant, *self.reagents), Config.of(*self.products), name="lactonization")
        except ConservationError as clash:
            raise IntramolecularCondensationError(
                f"intramolecular condensation does not conserve mass/charge: {clash}") from clash
        # (3) INTRAMOLECULARITY precondition: the precursor is ONE connected species (Molecule enforces this for
        # >1 atom; assert it explicitly so the invariant is a stated certificate, not an inherited accident).
        if len(precursor.atoms) > 1 and not precursor.is_connected():
            raise IntramolecularCondensationError("the precursor must be one connected molecule (intramolecular)")
        # (2) RE-DERIVATION (load-bearing): the precursor genuinely lactonizes to exactly this target + water.
        if not _lactonizes_to(precursor, self.reactant):
            raise IntramolecularCondensationError(
                "not an intramolecular lactonization of this precursor (a fabricated condensation edge is refused)")

    def equation(self) -> str:
        return f"{self.products[0]!r} -> {self.reactant!r} + {self.reagents[0]!r}"

    def reaction_center(self):
        """No coordinate-free centre is minted for this family (the oracle re-derives recognition from the molecules,
        never a carried centre -- ISSUE-126); returning None keeps the step's advisory centre empty."""
        return None

    def __repr__(self) -> str:
        return f"IntramolecularCondensationEdge({self.equation()})"


@dataclass(frozen=True)
class LactonizationEnumeration:
    """The result of a bounded lactonization enumeration, reporting whether it was EXHAUSTIVE.

    INTERFACE DEBT (OPERATION XIII, section 9).  ``retro_lactonization_edges`` returns only a tuple and its ``budget``
    can TRUNCATE the scan of candidate ring-ester sites silently, so a caller cannot tell a complete enumeration from
    a cut-off one.  Before this generator can feed a search that claims a COMPLETE receipt, the enumeration must say
    whether it saw every candidate.  ``exhaustive`` is True iff every ring-ester site was examined
    (``sites_total <= budget``); when False the scan stopped at the budget and the edge set is a LOWER BOUND, which
    MUST NOT contribute to a COMPLETE search receipt.

    (``exhaustive`` is about candidate COVERAGE, not acceptance: a site whose certificates fail is still
    EXAMINED -- and correctly dropped -- so dropping it does not make the enumeration non-exhaustive.)"""
    edges: tuple
    exhaustive: bool
    sites_total: int          # candidate ring-ester sites the target has
    sites_examined: int       # how many were actually scanned (min(sites_total, budget))
    budget: int

    def __post_init__(self) -> None:
        # the invariant the caller relies on: exhaustive <=> every candidate site was examined.
        if self.exhaustive != (self.sites_examined >= self.sites_total):
            raise IntramolecularCondensationError(
                "LactonizationEnumeration.exhaustive disagrees with sites_examined/sites_total")


def retro_lactonization_enumeration(target: Molecule, *, budget: int = 10_000) -> LactonizationEnumeration:
    """Bounded enumeration of lactonization edges that REPORTS its exhaustiveness (section 9 interface debt).  Opens
    each in-ring ester linkage into its hydroxy-acid precursor and keeps only those whose forward re-derivation
    reproduces ``target`` exactly; fail-closed (a neutral, uncharged lactone only; a failing site is dropped).  The
    returned record states whether the ``budget`` truncated the candidate-site scan -- read ``exhaustive`` before
    treating the edge set as complete."""
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    if not (isinstance(budget, int) and budget >= 1):
        raise IntramolecularCondensationError("budget must be an int >= 1")
    if target.charge != 0 or target.state:
        # a charged/stateful target is out of this generator's scope: there is nothing to enumerate, so the empty
        # result is vacuously exhaustive (zero candidate sites, all examined).
        return LactonizationEnumeration((), True, 0, 0, budget)
    from .smiles import resonance_identity
    sites = list(_ring_ester_sites(target))
    sites_total = len(sites)
    sites_examined = min(sites_total, budget)
    edges: list[IntramolecularCondensationEdge] = []
    seen: set[str] = set()
    for c_acyl, o_ester, _o_carbonyl in sites[:budget]:
        try:
            precursor = _open_lactone(target, c_acyl, o_ester)
        except (ValueError, TypeError):
            continue
        try:
            edge = IntramolecularCondensationEdge(
                INTRAMOLECULAR_CONDENSATION_SCHEMA, target, (precursor,), (_WATER,), LACTONIZATION_CLASS)
        except IntramolecularCondensationError:
            continue                                   # a site whose certificates fail is dropped (fail-closed)
        key = resonance_identity(precursor)            # structural identity, not repr() (the formula string)
        if key not in seen:
            seen.add(key)
            edges.append(edge)
    return LactonizationEnumeration(tuple(edges), sites_examined >= sites_total, sites_total, sites_examined, budget)


def retro_lactonization_edges(target: Molecule, *, budget: int = 10_000) -> tuple[IntramolecularCondensationEdge, ...]:
    """Every :class:`IntramolecularCondensationEdge` whose synthesis assembles ``target`` (a lactone) from a hydroxy
    acid expelling water (the edge TUPLE only; backward-compatible).  Standalone enumeration (NOT a ``search_routes``
    provider).  For an enumeration that reports whether ``budget`` truncated the scan -- which a COMPLETE search
    receipt requires -- use :func:`retro_lactonization_enumeration` and read ``.exhaustive``."""
    return retro_lactonization_enumeration(target, budget=budget).edges
