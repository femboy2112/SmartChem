"""
Multi-step mechanism search with list branching and a structured accumulator.

The legacy ``Reaction`` monad had a ``bind`` with zero call sites. Its "collapse of the
superposition of states" was an ordinary ``min``-tracking for-loop at engine.py:144, and
``bind`` silently dropped the ``metadata`` that was supposed to be the certificate
(finding F4). Here ``bind`` is the mechanism by which pathways compose, and it appends route
transitions together with a caller-supplied ``Tally`` instead of discarding provenance.

Writer/List-style representation
--------------------------------
``Pathway a`` follows the engineering shape of a Writer accumulator over list branching:

* the **list** part enumerates competing candidate routes in ordinary Python; it is neither
  a quantum superposition nor concurrent execution;
* the **writer** part accumulates a ``Tally`` (energy plus provenance) along each branch.

The tuple and set components of ``Tally`` have associative combination and an identity.
The numerical energy and quadrature fields are IEEE-754 floats, so their associativity is
only approximate and depends on evaluation order. Accordingly this is a useful Writer-style
engineering pattern, not an exact monad in the mathematical category of Python values.

Why this is not just a list of tuples
-------------------------------------
With exact associative tallies, the corresponding abstract Writer/List construction has the
usual laws. This concrete Python type is only an approximation to that model: tests check
representative generated values, but floating-point totals can differ after reassociation.
Code that requires reproducible high-dynamic-range sums should use a defined summation order
or a higher-precision/exact numeric representation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real
from typing import Callable, Generic, Iterable, Sequence, TypeVar

from .category import Config, Molecule, Reaction, is_regenerated

A = TypeVar("A")
B = TypeVar("B")

__all__ = [
    "Tally", "Pathway", "Step", "Mechanism",
    "search", "catalytic_cycles", "best_route",
]


# ======================================================================================
# The accumulated value -- approximately monoidal over floats
# ======================================================================================
@dataclass(frozen=True)
class Tally:
    """
    What accumulates along a pathway: energy, and the provenance of how it was obtained.

    Intended as an additive Writer accumulator with ``Tally.empty()`` as identity. Tuple
    concatenation and method-set union are exact; floating-point addition and quadrature are
    not exactly associative.

    ``uncertainty_ev`` adds in quadrature, treating step estimates as independent. Without
    covariance information this can understate uncertainty for positive correlation or
    overstate it for negative correlation. It is not a calibrated confidence interval or a
    general lower bound. Unlike ``Estimate``, ``Tally`` also does not track named systematic
    sources; callers should not infer cancellation from this scalar field.
    """
    energy_ev: float = 0.0
    uncertainty_ev: float = 0.0
    steps: tuple[str, ...] = ()
    methods: frozenset[str] = frozenset()
    transitions: tuple[tuple[Config, Config], ...] = ()
    generator_word: tuple[tuple[Config, Config, str], ...] = ()

    def __post_init__(self) -> None:
        for name in ("energy_ev", "uncertainty_ev"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
            object.__setattr__(self, name, float(value))
        if self.uncertainty_ev < 0:
            raise ValueError("uncertainty_ev must be non-negative")
        if not isinstance(self.steps, tuple):
            raise TypeError("steps must be a tuple of display labels")
        if not isinstance(self.methods, frozenset):
            raise TypeError("methods must be a frozenset of provenance labels")
        if not isinstance(self.transitions, tuple) or not isinstance(self.generator_word, tuple):
            raise TypeError("transitions and generator_word must be tuples")
        if any(not isinstance(step, str) or not step for step in self.steps):
            raise ValueError("steps must contain non-empty display labels")
        if any(not isinstance(method, str) or not method for method in self.methods):
            raise ValueError("methods must contain non-empty provenance labels")
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not all(isinstance(config, Config) for config in item)
            for item in self.transitions
        ):
            raise TypeError("transitions must contain (Config, Config) pairs")
        if any(
            not isinstance(item, tuple)
            or len(item) != 3
            or not isinstance(item[0], Config)
            or not isinstance(item[1], Config)
            or not isinstance(item[2], str)
            for item in self.generator_word
        ):
            raise TypeError("generator_word must contain typed (Config, Config, id) keys")
        if any(not item[2] for item in self.generator_word):
            raise ValueError("generator IDs must be non-empty strings")
        if len(self.transitions) != len(self.generator_word):
            raise ValueError("transitions and generator_word must have equal lengths")

    @staticmethod
    def empty() -> "Tally":
        """The intended accumulator identity."""
        return Tally()

    def __add__(self, other: "Tally") -> "Tally":
        return Tally(
            energy_ev=self.energy_ev + other.energy_ev,
            uncertainty_ev=math.hypot(self.uncertainty_ev, other.uncertainty_ev),
            steps=self.steps + other.steps,
            methods=self.methods | other.methods,
            transitions=self.transitions + other.transitions,
            generator_word=self.generator_word + other.generator_word,
        )

    @property
    def certificate(self) -> str:
        """Human-readable provenance. Survives arbitrary composition, by construction."""
        route = " -> ".join(self.steps) if self.steps else "(no steps)"
        methods = ", ".join(sorted(self.methods)) if self.methods else "none"
        return (f"{route}  |  dE = {self.energy_ev:+.3f} +/- {self.uncertainty_ev:.3f} eV"
                f"  |  oracles: {methods}")

    def __repr__(self) -> str:
        return f"Tally({self.energy_ev:+.3f} eV, {len(self.steps)} steps)"


# ======================================================================================
# The branching accumulator
# ======================================================================================
@dataclass(frozen=True)
class Pathway(Generic[A]):
    """
    Writer/List-style branching search accumulating energy and provenance.

    Each branch is ``(value, tally)``. ``bind`` explores every continuation of every
    branch and combines the tallies with the intended accumulator operation. Floating-point
    non-associativity means this is not claimed as an exact lawful monad of Python values.
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
        """The branch with the lowest caller-supplied energy tally, if any."""
        if not self.branches:
            return None
        return min(self.branches, key=lambda b: b[1].energy_ev)

    def downhill(self) -> "Pathway[A]":
        """Only branches whose supplied energy tally is negative."""
        return self.filter(lambda _v, t: t.energy_ev < 0.0)

    def spontaneous(self) -> "Pathway[A]":
        """Compatibility alias for :meth:`downhill`; it does not establish spontaneity."""
        return self.downhill()

    def __repr__(self) -> str:
        return f"Pathway({len(self.branches)} branch(es))"


# ======================================================================================
# Chemistry on top of the monad
# ======================================================================================
@dataclass(frozen=True)
class Step:
    """One elementary reaction with caller-supplied energetics, as a search action."""
    reaction: Reaction
    energy_ev: float
    uncertainty_ev: float = 0.0
    method: str = ""

    def __post_init__(self) -> None:
        if self.reaction.steps != 1:
            raise ValueError(
                "Step requires one elementary Reaction; compose multi-step mechanisms "
                "through search or Reaction.then"
            )
        for name in ("energy_ev", "uncertainty_ev"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.uncertainty_ev < 0:
            raise ValueError("uncertainty_ev must be non-negative")
        if not isinstance(self.method, str):
            raise TypeError("method must be a provenance string")

    def as_action(
        self, *, fallback_generator_id: str | None = None
    ) -> Callable[[Config], Pathway[Config]]:
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
            word = tuple(
                (source, target, stable_id or fallback_generator_id or "")
                for source, target, stable_id in (self.reaction.generator_word or ())
            )
            return Pathway((
                (self.reaction.cod,
                 Tally(self.energy_ev, self.uncertainty_ev, (label,),
                       frozenset({self.method}) if self.method else frozenset(),
                       tuple(self.reaction.path or ()),
                       word)),
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

    Every positive-depth reachable state up to the bound is returned (optionally filtered
    to ``target``); the zero-step identity is not emitted as a mechanism,
    each carrying the accumulated supplied energy and provenance labels. Each action appends
    its transition and tally in the same operation, keeping route order aligned with those
    labels. The type does not verify that an energy came from the named method, that step
    energies are thermodynamically consistent, or that their uncertainties are calibrated.

    ``max_depth`` is a real bound and is enforced, not advisory -- the reachable set grows
    combinatorially and an unbounded search would not terminate on a rich step set.

    ``spontaneous_only`` is a compatibility name for filtering *returned completed routes*
    to negative supplied endpoint tallies. Uphill prefixes remain in the frontier because a
    later step can make the overall route downhill. The flag does not establish Gibbs
    spontaneity, kinetics, or transition-state accessibility.
    """
    if isinstance(max_depth, bool) or not isinstance(max_depth, int):
        raise TypeError("max_depth must be a non-negative integer")
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    if type(spontaneous_only) is not bool:
        raise TypeError("spontaneous_only must be a boolean")
    actions = [
        # NUL is reserved from public generator_id values by Reaction validation, keeping
        # anonymous call-local identities disjoint from the user ID namespace.
        step.as_action(fallback_generator_id=f"\x00smartchem-local-step:{index}")
        for index, step in enumerate(steps)
    ]
    found: list[Mechanism] = []
    # A display label is not mechanism identity. Preserve different estimates/provenance
    # for the same generator word; choosing the most negative estimate would select model
    # error, not a better mechanism. Anonymous inputs receive call-local step IDs so two
    # legacy same-endpoint channels do not alias merely because IDs were omitted.
    found_by_key: dict[tuple, Mechanism] = {}

    frontier: Pathway[Config] = Pathway.pure(start)
    for _depth in range(max_depth):
        extended = Pathway.none()
        for action in actions:
            branch = frontier.bind(action)
            extended = Pathway(extended.branches + branch.branches)
        if not extended:
            break

        for state, tally in extended.branches:
            if (target is None or state == target) and (
                not spontaneous_only or tally.energy_ev < 0.0
            ):
                mechanism = Mechanism(
                    route=Reaction(start, state, " ; ".join(tally.steps),
                                   path=tally.transitions,
                                   generator_word=tally.generator_word),
                    tally=tally,
                    intermediates=tuple(
                        target for _source, target in tally.transitions[:-1]
                    ),
                )
                # Display labels are intentionally absent: renaming an otherwise identical
                # generator does not create a second mechanism. Distinct estimates remain
                # visible but are not silently ranked against one another below.
                key = (
                    state,
                    tally.transitions,
                    tally.generator_word,
                    tally.energy_ev,
                    tally.uncertainty_ev,
                    tally.methods,
                )
                found_by_key.setdefault(key, mechanism)
        frontier = extended

    found.extend(found_by_key.values())
    return found


def catalytic_cycles(
    start: Config,
    steps: Sequence[Step],
    catalyst: Molecule,
    max_depth: int = 4,
) -> list[Mechanism]:
    """
    Compatibility name: find routes that stoichiometrically regenerate ``catalyst``.

    Replaces ``network.py``'s ``find_catalytic_cycles``, which printed "Catalytic Loop
    Closed mathematically" unconditionally and computed nothing (finding F3). Here the
    structural property is checked by ``category.is_regenerated`` on the composed history,
    and the history itself is returned so the caller can re-check it. Regeneration alone
    does not establish rate enhancement, participation in an elementary step, or a catalytic
    mechanism; an unchanged spectator also satisfies it.

    Zero-step identities are excluded. Despite the historical function name, the remaining
    route need not be a cycle in full configuration space; only the named species count is
    required to return.
    """
    return [
        m for m in search(start, steps, target=None, max_depth=max_depth)
        if m.tally.steps and is_regenerated(m.route, catalyst)
    ]


def best_route(mechanisms: Iterable[Mechanism]) -> Mechanism | None:
    """Lowest supplied tally only when the candidate estimates are comparable.

    Alternative estimates of the same structural route, or candidates evaluated by
    different method sets, require an explicit model/estimator policy. Picking the most
    negative number in either case would select model disagreement as though it were a
    physically better mechanism. Even a valid comparison is only the caller's supplied
    energy objective; it is not a kinetic fastest-route decision.
    """
    mechanisms = list(mechanisms)
    if not mechanisms:
        return None
    method_sets = {mechanism.tally.methods for mechanism in mechanisms}
    if len(method_sets) != 1:
        raise ValueError("best_route requires one common estimator/method policy")
    by_route: dict[tuple, tuple[float, float, frozenset[str]]] = {}
    for mechanism in mechanisms:
        identity = mechanism.route.generator_word or ()
        estimate = (
            mechanism.tally.energy_ev,
            mechanism.tally.uncertainty_ev,
            mechanism.tally.methods,
        )
        previous = by_route.setdefault(identity, estimate)
        if previous != estimate:
            raise ValueError(
                "one structural route has alternative estimates; select an estimator "
                "before calling best_route"
            )
    return min(mechanisms, key=lambda mechanism: mechanism.energy_ev)
