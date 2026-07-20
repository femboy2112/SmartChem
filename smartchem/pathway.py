"""
Multi-step mechanism search: the monad, actually used.

The legacy ``Reaction`` monad had a ``bind`` with zero call sites. Its "collapse of the
superposition of states" was an ordinary ``min``-tracking for-loop at engine.py:144, and
``bind`` silently dropped the ``metadata`` that was supposed to be the certificate
(finding F4). Here ``bind`` is the only mechanism by which pathways compose, and the
certificate is a monoid so it cannot be dropped.

The monad
---------
``Pathway a`` is ``WriterT (Tally) []``:

* the **list** part branches over competing mechanisms -- a genuine superposition of
  candidate routes, explored in parallel;
* the **writer** part accumulates a ``Tally`` (energy plus provenance) along each branch.

``Tally`` is a monoid, which is what makes the writer legal and what makes the certificate
survive composition. Both halves matter: without the monoid, ``bind`` has nothing lawful
to combine and the temptation is to drop one -- which is exactly what the legacy code did.

Why this is not just a list of tuples
-------------------------------------
Because the laws hold, a pathway can be built compositionally and refactored without
changing its meaning: ``a.bind(f).bind(g) == a.bind(lambda x: f(x).bind(g))`` means the
search strategy can be restructured freely. ``tests/test_pathway.py`` checks that against
hypothesis-generated chains rather than examples.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generic, Iterable, Sequence, TypeVar

from .category import Config, Molecule, Reaction, is_catalytic

A = TypeVar("A")
B = TypeVar("B")

__all__ = [
    "Tally", "Pathway", "Step", "Mechanism",
    "search", "catalytic_cycles", "best_route",
]


# ======================================================================================
# The accumulated value -- a monoid
# ======================================================================================
@dataclass(frozen=True)
class Tally:
    """
    What accumulates along a pathway: energy, and the provenance of how it was obtained.

    A monoid under ``+`` with ``Tally.empty()`` as identity. That is not decoration --
    it is the precondition for a lawful Writer, and it is what stops ``bind`` from
    dropping the certificate the way the legacy implementation did.

    ``uncertainty_ev`` adds in quadrature, treating step estimates as independent. That
    is an assumption, stated here rather than buried: correlated errors (the same oracle
    making the same systematic mistake at every step) would add closer to linearly, so
    this is a lower bound on the true uncertainty of a long route.
    """
    energy_ev: float = 0.0
    uncertainty_ev: float = 0.0
    steps: tuple[str, ...] = ()
    methods: frozenset[str] = frozenset()

    @staticmethod
    def empty() -> "Tally":
        """The monoid identity."""
        return Tally()

    def __add__(self, other: "Tally") -> "Tally":
        return Tally(
            energy_ev=self.energy_ev + other.energy_ev,
            uncertainty_ev=(self.uncertainty_ev ** 2 + other.uncertainty_ev ** 2) ** 0.5,
            steps=self.steps + other.steps,
            methods=self.methods | other.methods,
        )

    @property
    def certificate(self) -> str:
        """Human-readable provenance. Survives arbitrary composition, by construction."""
        route = " -> ".join(self.steps) if self.steps else "(no steps)"
        methods = ", ".join(sorted(self.methods)) if self.methods else "none"
        return (f"{route}  |  dG = {self.energy_ev:+.3f} +/- {self.uncertainty_ev:.3f} eV"
                f"  |  oracles: {methods}")

    def __repr__(self) -> str:
        return f"Tally({self.energy_ev:+.3f} eV, {len(self.steps)} steps)"


# ======================================================================================
# The monad
# ======================================================================================
@dataclass(frozen=True)
class Pathway(Generic[A]):
    """
    ``WriterT Tally []`` -- branching mechanism search accumulating energy and provenance.

    Each branch is ``(value, tally)``. ``bind`` explores every continuation of every
    branch and combines the tallies with the monoid.
    """
    branches: tuple[tuple[A, Tally], ...] = ()

    # -- monad operations --------------------------------------------------------
    @staticmethod
    def pure(value: A) -> "Pathway[A]":
        """``eta``: one branch, nothing accumulated yet."""
        return Pathway(((value, Tally.empty()),))

    @staticmethod
    def none() -> "Pathway[A]":
        """The empty pathway -- no viable route. The zero of the list part."""
        return Pathway(())

    def bind(self, f: "Callable[[A], Pathway[B]]") -> "Pathway[B]":
        """
        ``>>=``: extend every branch, accumulating tallies.

        The certificate is combined here rather than discarded. That single line is the
        fix for finding F4.
        """
        out: list[tuple[B, Tally]] = []
        for value, tally in self.branches:
            for next_value, next_tally in f(value).branches:
                out.append((next_value, tally + next_tally))
        return Pathway(tuple(out))

    def map(self, g: Callable[[A], B]) -> "Pathway[B]":
        return Pathway(tuple((g(v), t) for v, t in self.branches))

    def filter(self, predicate: Callable[[A, Tally], bool]) -> "Pathway[A]":
        """Prune branches. Used to cut endothermic or over-long routes during search."""
        return Pathway(tuple((v, t) for v, t in self.branches if predicate(v, t)))

    # -- inspection --------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.branches)

    def __bool__(self) -> bool:
        return bool(self.branches)

    def best(self) -> "tuple[A, Tally] | None":
        """The lowest-energy branch, or None if there are none."""
        if not self.branches:
            return None
        return min(self.branches, key=lambda b: b[1].energy_ev)

    def spontaneous(self) -> "Pathway[A]":
        """Only the downhill branches."""
        return self.filter(lambda _v, t: t.energy_ev < 0.0)

    def __repr__(self) -> str:
        return f"Pathway({len(self.branches)} branch(es))"


# ======================================================================================
# Chemistry on top of the monad
# ======================================================================================
@dataclass(frozen=True)
class Step:
    """One elementary reaction with its energetics, as a monadic action."""
    reaction: Reaction
    energy_ev: float
    uncertainty_ev: float = 0.0
    method: str = ""

    def as_action(self) -> Callable[[Config], Pathway[Config]]:
        """
        Turn this step into something ``bind`` can consume.

        Returns the empty pathway when the step does not apply to the current state --
        which is how impossible continuations prune themselves rather than needing a
        special case.
        """
        def action(state: Config) -> Pathway[Config]:
            if state != self.reaction.dom:
                return Pathway.none()
            label = self.reaction.name or f"{self.reaction.dom} -> {self.reaction.cod}"
            return Pathway((
                (self.reaction.cod,
                 Tally(self.energy_ev, self.uncertainty_ev, (label,),
                       frozenset({self.method}) if self.method else frozenset())),
            ))
        return action


@dataclass
class Mechanism:
    """A route found by search: the composed morphism plus its accumulated tally."""
    route: Reaction
    tally: Tally
    intermediates: tuple[Config, ...] = field(default_factory=tuple)

    @property
    def energy_ev(self) -> float:
        return self.tally.energy_ev

    @property
    def certificate(self) -> str:
        return self.tally.certificate

    def __repr__(self) -> str:
        return (f"Mechanism({self.route.dom} -> {self.route.cod}, "
                f"{len(self.tally.steps)} steps, {self.energy_ev:+.3f} eV)")


def search(
    start: Config,
    steps: Sequence[Step],
    target: Config | None = None,
    max_depth: int = 4,
    spontaneous_only: bool = False,
) -> list[Mechanism]:
    """
    Explore multi-step routes from ``start`` using ``bind``.

    Every reachable state at every depth is returned (optionally filtered to ``target``),
    each carrying the accumulated energy and full provenance. Because composition happens
    through the monad, the energy bookkeeping cannot drift out of step with the route.

    ``max_depth`` is a real bound and is enforced, not advisory -- the reachable set grows
    combinatorially and an unbounded search would not terminate on a rich step set.
    """
    actions = [s.as_action() for s in steps]
    found: list[Mechanism] = []
    seen: set[tuple[Config, tuple[str, ...]]] = set()

    frontier: Pathway[Config] = Pathway.pure(start)
    for _depth in range(max_depth):
        extended = Pathway.none()
        for action in actions:
            branch = frontier.bind(action)
            extended = Pathway(extended.branches + branch.branches)
        if spontaneous_only:
            extended = extended.spontaneous()
        if not extended:
            break

        for state, tally in extended.branches:
            key = (state, tally.steps)
            if key in seen:
                continue
            seen.add(key)
            if target is None or state == target:
                found.append(Mechanism(
                    route=Reaction(start, state, " ; ".join(tally.steps)),
                    tally=tally,
                ))
        frontier = extended

    found.sort(key=lambda m: m.energy_ev)
    return found


def catalytic_cycles(
    start: Config,
    steps: Sequence[Step],
    catalyst: Molecule,
    max_depth: int = 4,
) -> list[Mechanism]:
    """
    Find routes that regenerate ``catalyst``, returning the evidence.

    Replaces ``network.py``'s ``find_catalytic_cycles``, which printed "Catalytic Loop
    Closed mathematically" unconditionally and computed nothing (finding F3). Here the
    property is *decided* by ``category.is_catalytic`` on the composed morphism, and the
    morphism itself is handed back so the caller can re-check it rather than trust a bool.

    A cycle must also do work: a route of zero steps trivially regenerates everything, so
    those are excluded.
    """
    return [
        m for m in search(start, steps, target=None, max_depth=max_depth)
        if m.tally.steps and is_catalytic(m.route, catalyst)
    ]


def best_route(mechanisms: Iterable[Mechanism]) -> Mechanism | None:
    """Lowest-energy mechanism, or None if the sequence is empty."""
    mechanisms = list(mechanisms)
    return min(mechanisms, key=lambda m: m.energy_ev) if mechanisms else None
