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
# form. Full graph canonicalisation (nauty-style refinement) remains out of scope.
#
# Set to hold the old cap's WORST-CASE COST fixed, rather than to a round number. The
# 8-atom cap already permitted 8! = 40_320 candidates, measured here at 5.4 us each
# (~0.2 s). Keeping that same time budget and spending it through the symbol-class
# restriction buys reach instead of atoms: C2H5OH costs 1_440 (20 ms), and this matters
# because `Config.__post_init__` canonicalises on every construction, so the worst case
# is paid per object, not once.
#
# Benzene is deliberately OUT of budget: 518_400 candidates, measured at 4.1 s. That is
# not a cost this system can pay inside a constructor, so it refuses and says why.
_MAX_CANONICAL_CANDIDATES = 50_000


def _symbol_blocks(atoms: tuple[str, ...]) -> list[tuple[int, ...]]:
    """Atom positions grouped by symbol, the groups themselves in sorted symbol order."""
    order = sorted(range(len(atoms)), key=lambda i: atoms[i])
    blocks: list[tuple[int, ...]] = []
    start = 0
    for k in range(1, len(order) + 1):
        if k == len(order) or atoms[order[k]] != atoms[order[start]]:
            blocks.append(tuple(order[start:k]))
            start = k
    return blocks


def _canonical_cost(atoms: tuple[str, ...]) -> int:
    """How many candidate permutations `canonical()` will examine: prod(m_i!)."""
    total = 1
    for block in _symbol_blocks(atoms):
        total *= factorial(len(block))
    return total


def _sorting_permutations(atoms: tuple[str, ...]) -> Iterator[tuple[int, ...]]:
    """
    Every permutation that sorts the atom symbols -- and, deliberately, no others.

    Why this loses nothing
    ----------------------
    ``canonical()`` minimises the key ``(symbols, edges)``, ordered lexicographically
    with ``symbols`` first. Over all n! permutations the minimum of that first component
    is ``tuple(sorted(atoms))``, a value fixed by the multiset of symbols and reachable
    by some permutation. So a permutation that does not sort the symbols is strictly
    beaten on the primary component by one that does, whatever it does to ``edges``, and
    can never be the argmin.

    The candidate set is therefore exactly the symbol-sorting permutations -- the ones
    that shuffle atoms *within* a symbol class -- of which there are prod(m_i!), not n!.
    For C2H5OH that is 1,440 instead of 362,880. For benzene, 518,400 instead of
    479,001,600.

    This is an exact restriction of the search, not a heuristic prune: same argmin, same
    canonical form, verified against the old brute force in
    ``TestCanonicalShortcutIsExact``. The saving is real but composition-dependent, and
    vanishes entirely in the homonuclear worst case -- for C8 every permutation sorts the
    symbols, prod(m_i!) = n!, and nothing is saved. The refusal above
    ``_MAX_CANONICAL_CANDIDATES`` is what keeps that case honest.
    """
    n = len(atoms)
    blocks = _symbol_blocks(atoms)
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
    """
    atoms: tuple[str, ...]
    bonds: frozenset[Bond] = frozenset()
    charge: int = 0

    def __post_init__(self) -> None:
        n = len(self.atoms)
        for b in self.bonds:
            if not (0 <= b.i < n and 0 <= b.j < n):
                raise ValueError(f"bond {b} refers outside atoms {self.atoms}")

    # -- construction ------------------------------------------------------------
    @classmethod
    def atom(cls, symbol: str, charge: int = 0) -> "Molecule":
        """A lone unbonded atom."""
        return cls((symbol,), frozenset(), charge)

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
        """
        n = len(self.atoms)
        if n <= 1:
            return self
        budget = _canonical_cost(self.atoms)
        if budget > _MAX_CANONICAL_CANDIDATES:
            raise NotImplementedError(
                f"canonical relabelling of {self!r} needs {budget:,} candidate "
                f"permutations, above the limit of {_MAX_CANONICAL_CANDIDATES:,}; "
                f"full graph canonicalisation is out of scope"
            )
        best: tuple | None = None
        for perm in _sorting_permutations(self.atoms):
            # perm[old] = new
            symbols = tuple(x for _, x in sorted(zip(perm, self.atoms)))
            edges = tuple(sorted(
                (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
                for b in self.bonds
            ))
            key = (symbols, edges)
            if best is None or key < best:
                best = key
        assert best is not None
        symbols, edges = best
        return Molecule(symbols, frozenset(Bond(i, j, o) for i, j, o in edges), self.charge)

    def __repr__(self) -> str:
        counts = self.formula
        body = "".join(
            f"{s}{counts[s] if counts[s] > 1 else ''}" for s in sorted(counts)
        )
        if self.charge > 0:
            body += f"^{self.charge}+"
        elif self.charge < 0:
            body += f"^{abs(self.charge)}-"
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
        canon = tuple(sorted(
            (m.canonical() for m in self.species),
            key=lambda m: (tuple(sorted(m.formula.items())), m.charge, sorted(m.bonds)),
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

    UNMEASURED here, and labelled as such on purpose. The measurement that exists tested
    the weaker predicate, and the two must not be conflated -- the whole reason the number
    in ``is_bond_order_conserving`` is trustworthy is that it is attached to the property
    that was actually varied.
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
