"""
The Store comonad, and what it is actually for.

THE_ORBITAL.md section II claimed a store comonad. The shipped code was a Coreader (also
called Env or Product) comonad -- ``(a, e)``, a value paired with a context. That is a
perfectly good comonad, and its laws held, but it is not the Store comonad and it cannot
do the thing Store is for.

    Coreader  W a = (a, e)          "a value, and the environment it sits in"
    Store     W a = (e -> a, e)     "a way to compute the value at ANY environment,
                                     plus the one we are currently looking at"

The difference is the whole point. With Coreader, ``extend`` can only ever see the single
environment it was handed, so it computes one answer. With Store, ``extend`` re-focuses
the computation at every position, so one local definition yields the **entire response
surface** -- a phase diagram, a solvent series, a pressure sweep -- for free.

That is what makes the comonad load-bearing rather than decorative. In the legacy engine
``extend`` had zero call sites; here it is the only way ``survey`` and ``response_surface``
are implemented.

It also gives a structural fix for finding F2. The legacy engine returned an identical
energy for NaCl in vacuum and in water because ``min(ionic, covalent)`` selected a branch
with no solvation term. A response surface makes that visible immediately -- a flat
surface over a 100-fold change in dielectric is a defect you can see and test for, rather
than one hiding behind a single number. See ``is_responsive`` and the property test in
tests/test_store.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Sequence, TypeVar

S = TypeVar("S")   # position type (an environment)
A = TypeVar("A")   # value type (a computed property)
B = TypeVar("B")

__all__ = [
    "Store", "survey", "response_surface", "is_responsive",
    "Conditions", "grid", "argmin_position", "argmax_position",
]


# ======================================================================================
# The comonad
# ======================================================================================
@dataclass(frozen=True)
class Store(Generic[S, A]):
    """
    ``Store s a = (s -> a, s)``.

    ``peek`` computes the value at any position; ``focus`` is the position currently
    under consideration. Two Stores are equal only if they are the same object graph --
    function equality is undecidable, so the comonad laws are tested *extensionally*
    (agreement at sample positions), which is the honest way to check them.
    """
    peek: Callable[[S], A]
    focus: S

    # -- comonad operations ------------------------------------------------------
    def extract(self) -> A:
        """``epsilon : W a -> a``. The value here."""
        return self.peek(self.focus)

    def extend(self, f: "Callable[[Store[S, A]], B]") -> "Store[S, B]":
        """
        ``extend : (W a -> b) -> W a -> W b``.

        Given a computation that needs the whole context to produce one answer, produce
        that answer *at every position*. This is the operation the legacy code declared
        and never called, and it is what turns a single prediction into a surface.
        """
        return Store(lambda s: f(Store(self.peek, s)), self.focus)

    def duplicate(self) -> "Store[S, Store[S, A]]":
        """``delta : W a -> W (W a)``. Equivalent to ``extend(identity)``."""
        return self.extend(lambda w: w)

    def map(self, g: Callable[[A], B]) -> "Store[S, B]":
        """Functor action: post-compose ``g`` onto the observation."""
        return Store(lambda s: g(self.peek(s)), self.focus)

    # -- navigation --------------------------------------------------------------
    def seek(self, position: S) -> "Store[S, A]":
        """Move the focus to an absolute position."""
        return Store(self.peek, position)

    def experiment(self, move: Callable[[S], S]) -> A:
        """Look at what the value would be somewhere else, without moving."""
        return self.peek(move(self.focus))

    def __repr__(self) -> str:
        return f"Store(focus={self.focus!r}, here={self.extract()!r})"


# ======================================================================================
# Response surfaces -- the payoff
# ======================================================================================
def survey(store: Store[S, A], positions: Iterable[S]) -> dict[S, A]:
    """
    Evaluate the stored computation across many positions.

    Implemented through ``extend``, not by looping over ``peek`` directly, so the comonad
    is genuinely carrying the work rather than being narrated around it.
    """
    surface = store.extend(lambda w: w.extract())
    return {p: surface.peek(p) for p in positions}


def response_surface(
    compute: Callable[[S], A],
    positions: Sequence[S],
    focus: S | None = None,
) -> dict[S, A]:
    """Convenience: build a Store from a local computation and survey it."""
    if not positions:
        return {}
    return survey(Store(compute, focus if focus is not None else positions[0]), positions)


def is_responsive(
    store: Store[S, float],
    positions: Sequence[S],
    tolerance: float = 1e-9,
) -> bool:
    """
    Does the computed property actually vary across these positions?

    A flat response is nearly always a bug rather than a physical result: it means some
    branch of the calculation is ignoring the variable being swept. This is the direct
    check for finding F2, where NaCl returned byte-identical energies across a dielectric
    range of 1.0 to 109.0.
    """
    values = [store.peek(p) for p in positions]
    if not values:
        return False
    return (max(values) - min(values)) > tolerance


def argmin_position(store: Store[S, float], positions: Iterable[S]) -> S | None:
    """The position minimising the stored property -- e.g. the most stabilising solvent."""
    best, best_val = None, float("inf")
    for p in positions:
        v = store.peek(p)
        if v < best_val:
            best, best_val = p, v
    return best


def argmax_position(store: Store[S, float], positions: Iterable[S]) -> S | None:
    best, best_val = None, float("-inf")
    for p in positions:
        v = store.peek(p)
        if v > best_val:
            best, best_val = p, v
    return best


# ======================================================================================
# Chemical conditions as Store positions
# ======================================================================================
@dataclass(frozen=True, order=True)
class Conditions:
    """
    A point in environment space -- the position type for chemical Stores.

    Frozen and ordered so it can key a surface dictionary and sort into a grid. Distinct
    from the legacy ``Env`` in that it carries no behaviour: all the computation lives in
    the Store's ``peek``, which is what lets one definition be evaluated everywhere.
    """
    temperature_k: float = 298.15
    pressure_atm: float = 1.0
    dielectric: float = 1.0
    photon_ev: float = 0.0

    def with_(self, **changes) -> "Conditions":
        """A copy with some coordinates replaced. Handy as an ``experiment`` move."""
        return Conditions(
            temperature_k=changes.get("temperature_k", self.temperature_k),
            pressure_atm=changes.get("pressure_atm", self.pressure_atm),
            dielectric=changes.get("dielectric", self.dielectric),
            photon_ev=changes.get("photon_ev", self.photon_ev),
        )

    def __repr__(self) -> str:
        return (f"({self.temperature_k:g}K, {self.pressure_atm:g}atm, "
                f"eps={self.dielectric:g}"
                + (f", {self.photon_ev:g}eV" if self.photon_ev else "") + ")")


#: Common solvents, as dielectric constants. Source: CRC Handbook, 104th ed., section 6.
SOLVENTS: dict[str, float] = {
    "vacuum": 1.0,
    "hexane": 1.88,
    "diethyl ether": 4.27,
    "chloroform": 4.81,
    "acetone": 20.7,
    "ethanol": 24.5,
    "methanol": 32.7,
    "acetonitrile": 37.5,
    "DMSO": 46.7,
    "water": 80.1,
    "formamide": 109.0,
}


def grid(
    temperatures: Sequence[float] = (298.15,),
    pressures: Sequence[float] = (1.0,),
    dielectrics: Sequence[float] = (1.0,),
    photons: Sequence[float] = (0.0,),
) -> list[Conditions]:
    """
    The Cartesian product of the requested axes.

    Note the cost is multiplicative in the axes -- a 20x20x20 sweep is 8000 oracle calls.
    With an expensive oracle that matters, which is exactly why the categorical layer
    prunes structurally invalid candidates before any of this runs.
    """
    return [
        Conditions(t, p, d, e)
        for t in temperatures
        for p in pressures
        for d in dielectrics
        for e in photons
    ]
