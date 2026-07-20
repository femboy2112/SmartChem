"""
The symmetric monoidal category of chemical configurations.

This is the load-bearing layer. Not a description of the chemistry -- an enforcement of it.

The central design decision
--------------------------
Objects carry **bond topology**, not just atom counts.

That is not decoration. If an object were merely a bag of atoms, then every
mass-conserving reaction would have ``dom == cod`` and be an endomorphism: ``Na + Cl``
and ``NaCl`` would be the *same object*, so the reaction between them could not be a
morphism at all. That is exactly the defect the legacy engine had -- every "product" it
returned was its own reactants (finding F11). Giving objects structure is what makes
``Na + Cl -> NaCl`` a genuine arrow.

The theorem this buys
---------------------
Conservation is checked once, in the ``Reaction`` smart constructor, for **generators
only**. It then holds for every composite for free::

    f : A -> B  conserves  =>  formula(A) == formula(B)
    g : B -> C  conserves  =>  formula(B) == formula(C)
    ------------------------------------------------------
    g . f : A -> C         =>  formula(A) == formula(C)          [transitivity]

    f : A -> B, g : C -> D  conserve
    ------------------------------------------------------
    f (x) g : A(x)C -> B(x)D                                     [additivity]
      formula(A(x)C) = formula(A) + formula(C)
                     = formula(B) + formula(D) = formula(B(x)D)

So a mass-violating reaction is not merely absent from this system, it is
**unconstructible**. ``Fe + O + Cl -> FeO`` (finding F1) raises at construction time
rather than silently dropping the chlorine.

This is also where the speed claim becomes true. The pruning happens *here*, by type,
before any energy oracle is consulted. Candidates that violate conservation, charge
balance or valence never reach the expensive layer at all.

See ``tests/test_laws.py`` for the machine-checked versions of everything above.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import permutations, product
from math import factorial
from typing import Iterable, Iterator, Mapping

# Budget for canonical relabelling, counted in *candidate permutations actually examined*
# -- not in atoms. See `_sorting_permutations` for why those differ by orders of magnitude.
# Above this, canonicalisation is refused rather than silently returning a non-canonical
# form. Full graph canonicalisation (the whole of nauty: automorphism pruning, a search
# tree over target cells) remains out of scope; only its first move, refinement, is here.
#
# Set to hold the ORIGINAL cap's worst-case TIME fixed, rather than to a round number.
# The 8-atom cap permitted 8! = 40_320 candidates at ~5.4 us each, about 0.2 s. That same
# 0.2 s has now been spent twice over to buy reach rather than atoms -- first by
# restricting to symbol classes (#21), then by refining those classes (#23) -- and the
# budget itself has never moved. It matters because `Config.__post_init__` canonicalises
# on every construction, so the worst case is paid per object, not once.
#
# Measured 2026-07-20 on this machine, and the per-candidate cost depends on how many
# bonds there are to sort, so the honest figure comes from a BONDED worst case:
#
#   C7 ring       5_040 candidates    19.4 ms    3.85 us/candidate
#   => 50_000 candidates is ~0.19 s, which is the ceiling this budget actually buys
#   C8 unbonded  40_320 candidates    57.1 ms    1.42 us/candidate  (no edges to sort)
#   C3H8 propane  2_880 candidates    16.2 ms    (241_920 before refinement)
#
# Benzene stays deliberately OUT of budget at 518_400 candidates. Refinement cannot help
# it: its bond graph is vertex-transitive within each element, so no invariant computed
# from local structure can split the carbons. That is a fact about benzene, not a gap in
# the implementation, and it is the honest boundary of this approach.
_MAX_CANONICAL_CANDIDATES = 50_000


def _blocks(keys: tuple) -> list[tuple[int, ...]]:
    """Positions grouped by equal key, the groups themselves in sorted key order."""
    order = sorted(range(len(keys)), key=lambda i: keys[i])
    blocks: list[tuple[int, ...]] = []
    start = 0
    for k in range(1, len(order) + 1):
        if k == len(order) or keys[order[k]] != keys[order[start]]:
            blocks.append(tuple(order[start:k]))
            start = k
    return blocks


def _wl_colours(atoms: tuple[str, ...], bonds: frozenset["Bond"]) -> tuple[int, ...]:
    """
    One-dimensional Weisfeiler-Leman refinement: a colour per atom, invariant under
    relabelling, computed only from what the bond graph says about each atom's
    surroundings.

    Start every atom coloured by its element, then repeatedly recolour it by the pair
    ``(its own colour, the sorted multiset of its neighbours' colours-and-bond-orders)``,
    naming the new colours by sorting those signatures. Stop when a round splits nothing.

    Two properties are load-bearing, and both come from the same fact -- that nothing here
    ever mentions an atom's index:

    - **Equivariance.** Relabelling the molecule permutes the colours with it. That is
      what lets `canonical()` put colours in its sort key at all.
    - **Consistency with symbols.** A colour is ranked by a signature whose first
      component is the previous colour, so refinement never reorders classes, only splits
      them. Sorting by final colour therefore also sorts by element.

    What it cannot do is separate atoms that are genuinely interchangeable. It is a
    one-sided instrument: different colours prove two atoms are distinguishable, equal
    colours prove nothing. So the classes it returns are always a coarsening of the true
    automorphism orbits, which is exactly why the count it produces is a safe upper bound
    on the work and never an underestimate.
    """
    n = len(atoms)
    neighbours: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for b in bonds:
        neighbours[b.i].append((b.j, b.order))
        neighbours[b.j].append((b.i, b.order))
    ranks = {symbol: k for k, symbol in enumerate(sorted(set(atoms)))}
    colour = [ranks[a] for a in atoms]
    for _ in range(n):                      # each round splits or stops; at most n-1 split
        signature = [
            (colour[i], tuple(sorted((order, colour[j]) for j, order in neighbours[i])))
            for i in range(n)
        ]
        ranks = {s: k for k, s in enumerate(sorted(set(signature)))}
        refined = [ranks[s] for s in signature]
        if len(set(refined)) == len(set(colour)):
            break                           # partition stable: no class was split
        colour = refined
    return tuple(colour)


def _refined_blocks(atoms: tuple[str, ...], bonds: frozenset["Bond"]) -> list[tuple[int, ...]]:
    """Atom positions grouped by Weisfeiler-Leman colour, groups in colour order."""
    return _blocks(_wl_colours(atoms, bonds))


def _cost_of(blocks: list[tuple[int, ...]]) -> int:
    """Candidates enumerated when permuting within these classes: prod(m_i!)."""
    total = 1
    for block in blocks:
        total *= factorial(len(block))
    return total


def _canonical_blocks(
    atoms: tuple[str, ...], bonds: frozenset["Bond"]
) -> list[tuple[int, ...]]:
    """
    The classes `canonical()` permutes within: symbol classes, refined ONLY if the plain
    ones would blow the budget.

    Refinement is reach, not speed -- and it was measured to be a tax when spent where
    reach was not needed. Weisfeiler-Leman costs a fixed 5-55 us per call, against 1-4 us
    per candidate; on H2O, CO2, H2 and CH2O it splits nothing at all (2 candidates before,
    2 after) and made construction 3x slower. Those are the species this repository builds
    most, and `Config.__post_init__` canonicalises on every construction.

    So the rule is: try the cheap restriction; refine only when the alternative is
    refusing. Two properties fall out of that, and both are worth more than the speedup
    given up:

    - **The change is purely additive.** Any molecule that could be canonicalised before
      #23 has a symbol cost within budget, so it never reaches the refined branch and its
      canonical form is bit-for-bit what it always was. Only molecules that previously
      RAISED can see the new key.
    - **The two keys never have to agree.** A molecule takes its branch by symbol cost,
      which is fixed by its multiset of elements -- an isomorphism invariant. So every
      relabelling of one molecule takes the same branch, and two molecules in different
      branches differ in composition and were never equal anyway.

    The price, stated rather than hidden: a species whose symbol cost is under budget but
    which refinement would have made much cheaper still pays the old price. A C7 chain
    costs 5,040 candidates (~20 ms) where refinement would have charged 8. That is a
    missed optimisation on a molecule that already worked, not a regression, and it buys
    the additivity above.
    """
    blocks = _blocks(atoms)
    if _cost_of(blocks) <= _MAX_CANONICAL_CANDIDATES:
        return blocks
    return _refined_blocks(atoms, bonds)


def _canonical_cost(atoms: tuple[str, ...], bonds: frozenset["Bond"]) -> int:
    """How many candidate permutations `canonical()` will examine."""
    return _cost_of(_canonical_blocks(atoms, bonds))


def _symbol_cost(atoms: tuple[str, ...]) -> int:
    """
    What canonicalisation costs without refinement: prod over ELEMENTS.

    Kept because the gap between this and `_canonical_cost` is the whole of #23, and a
    claim about a gap is worth more when both sides of it are computed rather than
    remembered. Also the gate itself: refinement happens exactly when this exceeds the
    budget.
    """
    return _cost_of(_blocks(atoms))


def _sorting_permutations(
    atoms: tuple[str, ...], bonds: frozenset["Bond"]
) -> Iterator[tuple[int, ...]]:
    """
    Every permutation that sorts the atom colours -- and, deliberately, no others.

    Why this loses nothing
    ----------------------
    ``canonical()`` minimises the key ``(symbols, colours, edges)`` lexicographically, and
    the restriction falls out of that ordering in two stages:

    1. Over all n! permutations the minimum of ``symbols`` is ``tuple(sorted(atoms))`` --
       a value fixed by the multiset of symbols and reachable by some permutation. A
       permutation that does not sort the symbols is beaten on the primary component
       whatever it does to the rest, so it can never be the argmin.
    2. Among those, the minimum of ``colours`` is ``tuple(sorted(colours))``, by the same
       argument one component down. Colours refine symbols and are ordered consistently
       with them (see `_wl_colours`), so the two stages never fight: sorting by colour
       sorts by symbol for free.

    What survives is the set of permutations that shuffle atoms *within a colour class*,
    of which there are prod(m_i!) over the refined classes rather than over the elements.
    That is where the reach comes from, and it is worth an order of magnitude or three:

        species      symbol classes   refined classes
        C2H5OH                1,440                12
        C3H8 propane        241,920             2,880
        C3H7OH propanol     241,920                24

    This is an exact restriction of the search, not a heuristic prune -- verified against
    brute force over all n! permutations in ``TestCanonicalShortcutIsExact``. The saving
    is composition- *and* topology-dependent, and vanishes entirely where the graph is
    symmetric enough that no local invariant separates anything: C8, and benzene. The
    refusal above ``_MAX_CANONICAL_CANDIDATES`` is what keeps those cases honest.

    Stage 2 is only *reached* when stage 1 alone would exceed the budget; see
    ``_canonical_blocks`` for why refining unconditionally was measured to be a tax.
    """
    return _permute_within(_canonical_blocks(atoms, bonds), len(atoms))


def _permute_within(blocks: list[tuple[int, ...]], n: int) -> Iterator[tuple[int, ...]]:
    """Every permutation that shuffles atoms only within the given classes."""
    targets: list[tuple[int, ...]] = []
    position = 0
    for block in blocks:
        targets.append(tuple(range(position, position + len(block))))
        position += len(block)
    for choice in product(*(permutations(block) for block in blocks)):
        perm = [0] * n
        for olds, news in zip(choice, targets):
            for old, new in zip(olds, news):
                perm[old] = new
        yield tuple(perm)


class ConservationError(ValueError):
    """Raised when a proposed reaction would create or destroy matter or charge."""


class CompositionError(ValueError):
    """Raised when morphisms are composed with mismatched domain and codomain."""


# ======================================================================================
# Bonds and molecules
# ======================================================================================
@dataclass(frozen=True, order=True)
class Bond:
    """An undirected bond between two atom positions within one molecule."""
    i: int
    j: int
    order: int = 1

    def __post_init__(self) -> None:
        if self.i == self.j:
            raise ValueError(f"self-bond at position {self.i}")
        if self.order < 1:
            raise ValueError(f"bond order must be >= 1, got {self.order}")
        if self.i > self.j:
            # keep (i, j) canonical so equality is structural, not orientation-dependent.
            # capture both endpoints before writing either: assigning i first would
            # clobber the value j needs to read.
            lo, hi = self.j, self.i
            object.__setattr__(self, "i", lo)
            object.__setattr__(self, "j", hi)


@dataclass(frozen=True)
class Molecule:
    """
    One connected chemical species, with explicit topology.

    ``atoms`` is positional: ``bonds`` refers to atoms by index. Two molecules are equal
    when they are the same labelled graph after canonical relabelling, so ``H-O-H`` built
    in either atom order compares equal.

    ``state`` is an opaque internal-state label -- an electronic excitation, a mode, an
    operating point. It is part of the object's IDENTITY but not of the conserved
    signature, and that separation is the whole point of the field.

    Without it, the only way to distinguish an excited emitter from a relaxed one is to
    change a symbol, and changing a symbol changes ``formula`` -- so ``Na* -> Na + photon``
    is rejected as mass-violating when it is nothing of the kind. That is a real
    foreclosure rather than a hypothetical: an antenna or any radiating system is exactly
    *the same matter* in a different energy state, and a category that cannot say so
    cannot host one. Photochemistry needs it for the same reason.

    So: composition and charge are conserved; state is free to change. ``Na(state="*") ->
    Na + photon`` is a legal morphism, and the energy difference is the oracle's business,
    not the category's.
    """
    atoms: tuple[str, ...]
    bonds: frozenset[Bond] = frozenset()
    charge: int = 0
    state: str = ""

    def __post_init__(self) -> None:
        n = len(self.atoms)
        for b in self.bonds:
            if not (0 <= b.i < n and 0 <= b.j < n):
                raise ValueError(f"bond {b} refers outside atoms {self.atoms}")

    # -- construction ------------------------------------------------------------
    @classmethod
    def atom(cls, symbol: str, charge: int = 0, state: str = "") -> "Molecule":
        """A lone unbonded atom."""
        return cls((symbol,), frozenset(), charge, state)

    @classmethod
    def quantum(cls, state: str = "") -> "Molecule":
        """
        A carrier of energy and no matter: a photon, a phonon, a radiated quantum.

        Empty ``atoms`` is deliberate and already legal -- it contributes nothing to
        ``formula``, so emission and absorption conserve composition automatically. This
        constructor exists to name the case, not to enable it.
        """
        return cls((), frozenset(), 0, state)

    @classmethod
    def diatomic(cls, a: str, b: str, order: int = 1, charge: int = 0) -> "Molecule":
        return cls((a, b), frozenset({Bond(0, 1, order)}), charge).canonical()

    # -- structure ---------------------------------------------------------------
    @property
    def formula(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.atoms:
            counts[s] = counts.get(s, 0) + 1
        return counts

    def degree(self, index: int) -> int:
        """Total bond order at one atom position -- its used valence."""
        return sum(b.order for b in self.bonds if index in (b.i, b.j))

    def is_connected(self) -> bool:
        """True if the bond graph is connected (a single species, not a mixture)."""
        n = len(self.atoms)
        if n <= 1:
            return True
        adj: dict[int, set[int]] = {i: set() for i in range(n)}
        for b in self.bonds:
            adj[b.i].add(b.j)
            adj[b.j].add(b.i)
        seen = {0}
        stack = [0]
        while stack:
            cur = stack.pop()
            for nxt in adj[cur] - seen:
                seen.add(nxt)
                stack.append(nxt)
        return len(seen) == n

    def canonical(self) -> "Molecule":
        """
        Canonical relabelling, so structurally identical molecules compare equal.

        Minimises the key ``(symbols, edges)`` over the candidate permutations, then
        rebuilds the molecule from the winner. Refuses loudly above
        ``_MAX_CANONICAL_CANDIDATES`` rather than quietly returning something
        non-canonical.

        For molecules the symbol restriction alone cannot afford, the key becomes
        ``(symbols, colours, edges)`` and the candidate set shrinks accordingly -- see
        ``_canonical_blocks``. Those are exactly the molecules that used to raise, so no
        canonical form computed before that change moved.

        Only ``edges`` is compared in the loop below. The other two components are what
        *define* the candidate set -- every candidate realises the same sorted ``symbols``
        and the same sorted ``colours``, so they are constant here and cannot break a tie.
        They are hoisted, not dropped; ``test_every_candidate_realises_the_same_prefix``
        is what holds that claim down.
        """
        n = len(self.atoms)
        if n <= 1:
            return self
        blocks = _canonical_blocks(self.atoms, self.bonds)
        budget = _cost_of(blocks)
        if budget > _MAX_CANONICAL_CANDIDATES:
            raise NotImplementedError(
                f"canonical relabelling of {self!r} needs {budget:,} candidate "
                f"permutations, above the limit of {_MAX_CANONICAL_CANDIDATES:,}; "
                f"full graph canonicalisation is out of scope"
            )
        symbols = tuple(self.atoms[i] for block in blocks for i in block)
        best: tuple | None = None
        for perm in _permute_within(blocks, n):
            # perm[old] = new
            edges = tuple(sorted(
                (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
                for b in self.bonds
            ))
            if best is None or edges < best:
                best = edges
        assert best is not None
        return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in best),
                        self.charge, self.state)

    def __repr__(self) -> str:
        counts = self.formula
        body = "".join(
            f"{s}{counts[s] if counts[s] > 1 else ''}" for s in sorted(counts)
        )
        if self.charge > 0:
            body += f"^{self.charge}+"
        elif self.charge < 0:
            body += f"^{abs(self.charge)}-"
        if self.state:
            body += f"({self.state})"
        return body


# ======================================================================================
# Objects of the category
# ======================================================================================
@dataclass(frozen=True)
class Config:
    """
    An object of the category: a multiset of coexisting molecules.

    This is the contents of the vessel. ``Na + Cl`` (two species) and ``NaCl`` (one
    species) have the same ``formula`` but are different objects -- which is precisely
    what lets a reaction between them be a non-identity morphism.
    """
    species: tuple[Molecule, ...]

    def __post_init__(self) -> None:
        # canonical: each molecule canonicalised, then the multiset sorted deterministically
        # `state` belongs in this key even though it is not conserved. Without it two
        # species differing only in state tie, the sort is stable, and the canonical
        # tuple would then depend on the order they were passed in -- making
        # `Config.of(a, b) != Config.of(b, a)`. Silent, and fatal to every equality above.
        canon = tuple(sorted(
            (m.canonical() for m in self.species),
            key=lambda m: (tuple(sorted(m.formula.items())), m.charge,
                           sorted(m.bonds), m.state),
        ))
        object.__setattr__(self, "species", canon)

    # -- construction ------------------------------------------------------------
    @classmethod
    def of(cls, *molecules: Molecule) -> "Config":
        return cls(tuple(molecules))

    @classmethod
    def atoms(cls, *symbols: str) -> "Config":
        """A configuration of lone unbonded atoms -- the usual reactant side."""
        return cls(tuple(Molecule.atom(s) for s in symbols))

    # -- the conserved quantity --------------------------------------------------
    @property
    def formula(self) -> dict[str, int]:
        """Total atom counts across all species. Invariant under any valid reaction."""
        counts: dict[str, int] = {}
        for m in self.species:
            for s, k in m.formula.items():
                counts[s] = counts.get(s, 0) + k
        return counts

    @property
    def charge(self) -> int:
        """Total charge. Also invariant."""
        return sum(m.charge for m in self.species)

    @property
    def signature(self) -> tuple:
        """The full conserved signature: atoms and charge together."""
        return (tuple(sorted(self.formula.items())), self.charge)

    def atom_count(self) -> int:
        return sum(self.formula.values())

    def __len__(self) -> int:
        return len(self.species)

    def __repr__(self) -> str:
        return " + ".join(repr(m) for m in self.species) if self.species else "I"


#: The monoidal unit: the empty vessel. ``I (x) A == A``.
UNIT = Config(())


def tensor_obj(a: Config, b: Config) -> Config:
    """``A (x) B``: both configurations present in the same vessel."""
    return Config(a.species + b.species)


# ======================================================================================
# Morphisms
# ======================================================================================
@dataclass(frozen=True)
class Reaction:
    """
    A morphism ``dom -> cod``.

    The constructor is where conservation is enforced. There is no way to build a
    ``Reaction`` that creates or destroys matter or charge, so no downstream code has to
    remember to check -- and no composite of valid reactions can violate it either.

    Why ``path`` exists
    -------------------
    A morphism is not determined by its endpoints alone. Two mechanisms can carry the
    same overall species from A to C through different intermediates, and collapsing
    them would throw away exactly the information mechanism search needs.

    So a reaction records the sequence of elementary steps it traverses:

    * an elementary reaction has ``path == ((dom, cod),)`` -- one step
    * an identity has ``path == ()`` -- it traverses nothing
    * composition concatenates paths

    That makes the category laws hold for the right reason rather than by accident:
    associativity is associativity of concatenation, and the identity laws hold because
    the empty tuple is the unit of concatenation.

    ``name`` is a human label and is excluded from equality -- two reactions differing
    only in what they are called are the same morphism.
    """
    dom: Config
    cod: Config
    name: str = field(default="", compare=False)
    path: tuple[tuple[Config, Config], ...] | None = None

    def __post_init__(self) -> None:
        if self.path is None:
            # an elementary generator traverses exactly one step; an identity, none
            step = () if self.dom == self.cod else ((self.dom, self.cod),)
            object.__setattr__(self, "path", step)
        if self.dom.formula != self.cod.formula:
            raise ConservationError(
                f"mass not conserved: {self.dom} -> {self.cod}; "
                f"{self.dom.formula} != {self.cod.formula}"
            )
        if self.dom.charge != self.cod.charge:
            raise ConservationError(
                f"charge not conserved: {self.dom} -> {self.cod}; "
                f"{self.dom.charge:+d} != {self.cod.charge:+d}"
            )

    def then(self, other: "Reaction") -> "Reaction":
        """
        Sequential composition ``other . self``, written left-to-right.

        Defined only when ``self.cod == other.dom``. Conservation of the result is
        automatic: it follows from transitivity, not from a re-check.
        """
        if self.cod != other.dom:
            raise CompositionError(
                f"cannot compose {self.dom} -> {self.cod} with "
                f"{other.dom} -> {other.cod}: codomain != domain"
            )
        label = f"{self.name} ; {other.name}".strip(" ;")
        return Reaction(
            self.dom, other.cod, label,
            path=(self.path or ()) + (other.path or ()),
        )

    def tensor(self, other: "Reaction") -> "Reaction":
        """Parallel composition ``self (x) other``: both reactions in one vessel."""
        label = f"{self.name} (x) {other.name}".strip(" (x)")
        return Reaction(
            tensor_obj(self.dom, other.dom),
            tensor_obj(self.cod, other.cod),
            label,
        )

    @property
    def steps(self) -> int:
        """How many elementary steps this morphism traverses. 0 for an identity."""
        return len(self.path or ())

    def __repr__(self) -> str:
        tag = f" [{self.name}]" if self.name else ""
        return f"{self.dom} -> {self.cod}{tag}"


def identity(obj: Config) -> Reaction:
    """``id_A : A -> A``. Trivially conserving, and traverses no steps."""
    return Reaction(obj, obj, "id", path=())


def braid(a: Config, b: Config) -> Reaction:
    """
    The symmetry ``sigma_{A,B} : A (x) B -> B (x) A``.

    Because ``Config`` canonicalises its species multiset, ``A (x) B`` and ``B (x) A``
    are already the *same object*, so this is an identity. That is the honest outcome:
    the monoidal structure is symmetric on the nose rather than up to a nontrivial
    natural isomorphism. Retained so the SMC interface is complete and so the law is
    stated somewhere a test can find it.
    """
    return Reaction(tensor_obj(a, b), tensor_obj(b, a), "braid")


# ======================================================================================
# Structural properties, decided rather than asserted
# ======================================================================================
def is_catalytic(reaction: Reaction, catalyst: Molecule) -> bool:
    """
    Decide whether ``reaction`` is catalytic in ``catalyst``.

    A catalytic step is a morphism ``C (x) S -> C (x) P``: the catalyst appears in both
    the source and the target with the same multiplicity, so it is regenerated rather
    than consumed. This replaces the legacy implementation, which printed
    "Catalytic Loop Closed" unconditionally and computed nothing (finding F3).

    Note this decides a *structural* property. It says the catalyst survives the step,
    not that the step is kinetically or thermodynamically accessible -- those are the
    oracle's business, and are reported separately.
    """
    c = catalyst.canonical()
    return (
        reaction.dom.species.count(c) > 0
        and reaction.dom.species.count(c) == reaction.cod.species.count(c)
    )


def reaction_residue(reaction: Reaction) -> tuple[Config, Config]:
    """
    Strip the spectators: return ``(dom', cod')`` with the common sub-multiset removed.

    This is the structural half of an *exact* computational shortcut. Because ``E`` is a
    monoidal functor, ``E(S (x) X) = E(S) + E(X)``, so for ``f : S (x) A -> S (x) B`` the
    shared part cancels identically::

        dE(f) = (E(S) + E(B)) - (E(S) + E(A)) = E(B) - E(A)

    ``E(S)`` therefore cannot influence the answer and does not need to be computed. The
    category decides that before any oracle is called -- the same "prune by type, ahead of
    the expensive layer" move the search already makes, applied to the energy itself.

    Two things follow, and the second matters more than the first:

    1. **Cost.** A spectator is never priced. In a catalytic step the catalyst is usually
       the largest species present, so this is the difference between paying for the whole
       vessel and paying for the bond that actually changes.

    2. **Honesty of the error bar.** Uncertainties combine in quadrature, which is valid
       only for *independent* errors. A spectator's energy is not two independent samples
       -- it is one number, appearing twice, minus itself. Summing both sides first and
       subtracting afterwards adds ``2 * u(S)^2`` of variance that physically cancels to
       zero, so the reported interval is too wide by a factor that grows with the
       spectator. Removing the species removes the fiction.

    The cancellation is exact only if the oracle is a deterministic function of the
    species -- true for every oracle here, and worth stating because a stochastic oracle
    (diffusion Monte Carlo, say) would return two different samples and the shared part
    would cancel only to within its own noise.

    An identity morphism has empty residue on both sides, giving ``dE = 0`` exactly.
    """
    left = Counter(reaction.dom.species)
    right = Counter(reaction.cod.species)
    shared = left & right               # multiset intersection: the spectators
    return (
        Config(tuple((left - shared).elements())),
        Config(tuple((right - shared).elements())),
    )


def bond_signature(config: Config) -> Counter:
    """
    The multiset of bond *types* in a configuration: ``{(("H", "Cl"), 1): 2, ...}``.

    A bond type is its two element symbols (sorted, so it is undirected) together with its
    order. This is coarser than the topology -- it forgets which atom is which -- and that
    coarseness is the point: it is the granularity at which method error is roughly
    transferable between molecules.
    """
    sig: Counter = Counter()
    for molecule in config.species:
        for b in molecule.bonds:
            pair = tuple(sorted((molecule.atoms[b.i], molecule.atoms[b.j])))
            sig[(pair, b.order)] += 1
    return sig


def bond_order_profile(config: Config) -> Counter:
    """
    The multiset of bond *orders* in a configuration, forgetting which elements they join:
    ``{1: 2, 3: 1}`` for two single bonds and one triple.

    Coarser than ``bond_signature``, and the coarseness is deliberate. It is the level at
    which "one single bond was broken and one single bond was made" is a statement about
    the morphism, regardless of whether the partners changed.
    """
    profile: Counter = Counter()
    for molecule in config.species:
        for b in molecule.bonds:
            profile[b.order] += 1
    return profile


def is_bond_order_conserving(reaction: Reaction) -> bool:
    """
    Decide whether ``reaction`` preserves the multiset of bond orders -- the same number of
    single bonds, double bonds and so on, though the partners may swap.

    ``HCl + F -> HF + Cl`` satisfies this: one single bond in, one single bond out.
    ``2 H -> H2`` does not: it makes a bond out of nothing.

    Decided from structure alone, with no oracle call, because the objects carry bond
    topology. This is the predicate the measurement below actually tested.

    Why it is worth deciding: a correlated method's error is approximately a property of
    the bonds present, so in a morphism whose bond content is unchanged the errors appear
    on both sides and partly cancel in ``dE`` -- the same shape of argument as the
    arbitrary energy zero, but *approximate* where that one is exact.

    MEASURED, and the pre-registered prediction was wrong. Over 5 bond-creating and 4
    bond-order-conserving diatomic reactions scored against experimental D0:

    ==================  ================  =====================  =====
    tier                bond-creating     bond-order-conserving  ratio
    ==================  ================  =====================  =====
    HF/cc-pVTZ          1.8847 eV         0.7475 eV              2.52
    CCSD(T)/cc-pVTZ     0.1265 eV         0.0592 eV              2.14
    ==================  ================  =====================  =====

    The prediction was a ratio above 3. It is not met at either tier. The effect is real,
    consistent in sign and size across two tiers differing ~15x in absolute error, and
    worth about a factor of two -- not the larger effect claimed in advance.

    So this function DECIDES the property and reports it. It deliberately does not select
    a cheaper tier on its own. Nine diatomic reactions in one basis family do not license
    an automatic accuracy policy, and the last policy proposed here on that kind of
    evidence -- basis augmentation -- lost outright when finally measured at the tier that
    mattered. Candidate generation does not upgrade proof status.

    See ``THE_DIFFERENCE.md`` section 5 and ``tests/test_shortcuts.py``.
    """
    return bond_order_profile(reaction.dom) == bond_order_profile(reaction.cod)


def is_isodesmic(reaction: Reaction) -> bool:
    """
    Decide whether ``reaction`` preserves the multiset of bond *types* -- element pair and
    order both. Strictly stronger than ``is_bond_order_conserving``.

    ``HCl + F -> HF + Cl`` is bond-order conserving but NOT isodesmic, because ``H-Cl``
    became ``H-F``. Chemistry expects the stronger property to cancel error better still,
    since the bonds on each side are then genuinely the same kind of object.

    MEASURED, AND THE MEASUREMENT CANNOT DECIDE. The honest verdict is UNDECIDED, not a
    number, and the reason is worth more than a number would have been.

    Prediction P4, registered before the run: isodesmic < order-conserving < creating in
    mean absolute error against experiment. Over 82 mass-balanced reactions among 14
    species, scored against experimental enthalpies of formation at 0 K:

    ==============  ===  ==========  ==========  ==========
    class             n  absolute    relative    per bond
    ==============  ===  ==========  ==========  ==========
    isodesmic         7  0.1818 eV   0.33        0.0191 eV
    order-conserving 47  0.1101 eV   0.19        0.0111 eV
    creating         28  0.2858 eV   0.57        0.0339 eV
    ==============  ===  ==========  ==========  ==========

    Read naively that refutes P4 on all three statistics at once: isodesmic looks 1.65x
    WORSE than merely order-conserving. It does not refute it, because the comparison is
    confounded, and the confound was introduced by the fix for an earlier problem.

    Over the nine species originally referenced, exactly ONE strictly isodesmic reaction
    exists. Fixing that meant adding species, and over this element set the only species
    that unlock isodesmic reactions carry C=O. So 5 of 7 isodesmic reactions contain a
    carbonyl against 3 of 47 order-conserving ones -- "isodesmic" and "contains C=O" are
    very nearly the same variable in this sample. That matters because HF omits electron
    correlation and correlation energy is largest for multiple bonds, so a C=O species is
    exactly what this tier handles worst. Stratifying:

    ==================  =======================  ==========================
    stratum             isodesmic                order-conserving
    ==================  =======================  ==========================
    no C=O species      0.0701 eV  (n=2)         0.1040 eV  (n=44)
    contains C=O        0.2264 eV  (n=5)         0.2003 eV  (n=3)
    ==================  =======================  ==========================

    The sign flips between strata and the pooled figure agrees with neither -- Simpson's
    paradox, driven by a composition imbalance this project created for itself. n=2 in the
    clean stratum decides nothing, and the largest single isodesmic error and the smallest
    are BOTH carbonyl reactions, so it is not a tidy species effect either.

    One confound was predicted in advance and turned out to be null: reactions containing
    H2 get an experimental zero-point energy rather than a computed one, and H2 appears in
    21 of 47 order-conserving reactions and none of the isodesmic ones. It is worth
    nothing -- 0.1111 eV with H2 against 0.1101 eV overall.

    So this function DECIDES the property and reports it, and quotes no accuracy claim. To
    settle P4 the isodesmic class needs members without carbonyls, which over these
    elements means larger alkanes and alcohols; propane is the smallest and is currently
    beyond ``_MAX_CANONICAL_CANDIDATES``. The blocker is therefore the canonical key, not
    the oracle -- a dependency that is now demonstrated rather than assumed.

    See ``tests/test_shortcuts.py::TestTheIsodesmicMeasurementIsConfounded``.
    """
    return bond_signature(reaction.dom) == bond_signature(reaction.cod)


def catalytic_cycle(steps: Iterable[Reaction], catalyst: Molecule) -> Reaction | None:
    """
    Compose ``steps`` into a single morphism and return it if the composite is catalytic.

    Returns None if the steps do not compose (a real gap in the mechanism) or if the
    catalyst is not regenerated. Returning the composed morphism rather than a bare
    ``True`` is the point: the caller receives the evidence and can re-check it.
    """
    steps = list(steps)
    if not steps:
        return None
    composite = steps[0]
    for nxt in steps[1:]:
        try:
            composite = composite.then(nxt)
        except CompositionError:
            return None
    return composite if is_catalytic(composite, catalyst) else None


def conserves(reaction: Reaction) -> bool:
    """
    Re-verify conservation independently of the constructor.

    Always True for any ``Reaction`` that exists, by construction. Kept as a separate
    predicate so the property tests can assert it over hypothesis-generated composition
    chains without relying on the same code path that enforced it.
    """
    return (
        reaction.dom.formula == reaction.cod.formula
        and reaction.dom.charge == reaction.cod.charge
    )


def formula_of(counts: Mapping[str, int], charge: int = 0) -> tuple:
    """Build the conserved signature directly, for comparison in tests."""
    return (tuple(sorted(counts.items())), charge)
