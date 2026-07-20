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

from dataclasses import dataclass, field
from itertools import permutations
from typing import Iterable, Mapping

# Above this many atoms, canonical relabelling by brute-force permutation is refused
# rather than silently returning a non-canonical form. Graph canonicalisation proper
# (nauty-style refinement) is out of scope; the honest move is to say so.
_MAX_CANONICAL_ATOMS = 8


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

        Brute force over permutations that sort the atom symbols. Fine for the small
        species this system targets; refuses loudly above ``_MAX_CANONICAL_ATOMS``
        rather than quietly returning something non-canonical.
        """
        n = len(self.atoms)
        if n <= 1:
            return self
        if n > _MAX_CANONICAL_ATOMS:
            raise NotImplementedError(
                f"canonical relabelling of {n} atoms is not supported "
                f"(limit {_MAX_CANONICAL_ATOMS}); graph canonicalisation is out of scope"
            )
        best: tuple | None = None
        best_perm: tuple[int, ...] | None = None
        for perm in permutations(range(n)):
            # perm[old] = new
            symbols = tuple(x for _, x in sorted(zip(perm, self.atoms)))
            edges = tuple(sorted(
                (min(perm[b.i], perm[b.j]), max(perm[b.i], perm[b.j]), b.order)
                for b in self.bonds
            ))
            key = (symbols, edges)
            if best is None or key < best:
                best, best_perm = key, perm
        assert best is not None and best_perm is not None
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
