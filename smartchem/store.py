"""
The Store comonad and finite sampling utilities.

THE_ORBITAL.md section II claimed a store comonad. The shipped code was a Coreader (also
called Env or Product) comonad -- ``(a, e)``, a value paired with a context. That is a
perfectly good comonad, and its laws held, but it is not the Store comonad and it cannot
do the thing Store is for.

    Coreader  W a = (a, e)          "a value, and the environment it sits in"
    Store     W a = (e -> a, e)     "a way to compute the value at ANY environment,
                                     plus the one we are currently looking at"

Store represents a query function together with a current focus. ``extend`` can build a new
query whose value at a position depends on a re-focused view of the original Store. It is a
lawful and sometimes useful context abstraction, but it supplies no interpolation, caching
or computation for free: sampling ``n`` positions evaluates the supplied function ``n``
times unless that function has its own cache.

In particular, ``survey`` uses ``extend(extract)``, which is extensionally the original
Store by a comonad law. The call demonstrates the law but does not perform additional work;
the dictionary comprehension is the finite sweep. Nor do the bundled energy oracles consume
``Conditions`` automatically. A caller must provide a computation whose physical model
actually depends on the swept variables.

The utilities can expose finding F2: if dependence on dielectric is expected from the
chosen model, a flat sweep is evidence that the variable may have been ignored. Flatness is
not intrinsically a defect; some observables and models are genuinely invariant over a
specified range.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType
from typing import Callable, Generic, Iterable, Mapping, Sequence, TypeVar

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

        Given a computation that inspects a focused Store, return a new lazy query that
        re-focuses the original Store before applying that computation. Values are only
        produced when ``peek`` or ``extract`` evaluates the query.
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
# Finite response-surface sampling
# ======================================================================================
def survey(store: Store[S, A], positions: Iterable[S]) -> dict[S, A]:
    """
    Evaluate the stored computation across many positions.

    This costs one ``peek`` evaluation per listed position (absent caching inside ``peek``).
    The intermediate ``extend(extract)`` is extensionally equal to ``store``; it is retained
    as an explicit use of the Store law, not as an optimisation.
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

    Flatness is a useful diagnostic only when the selected physical model predicts
    dependence on the swept variable. Otherwise a flat result may be correct. This check
    exposed finding F2, where a model intended to include dielectric response returned
    byte-identical NaCl energies from dielectric 1.0 to 109.0.
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
    the Store's ``peek``. A supplied definition can be evaluated at any requested point,
    with one evaluation per point unless it implements caching.
    """
    temperature_k: float = 298.15
    pressure_atm: float = 1.0
    dielectric: float = 1.0
    photon_ev: float = 0.0

    def __post_init__(self) -> None:
        for name in ("temperature_k", "pressure_atm", "dielectric", "photon_ev"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.temperature_k < 0:
            raise ValueError("temperature_k must be non-negative")
        if self.pressure_atm < 0:
            raise ValueError("pressure_atm must be non-negative")
        if self.dielectric <= 0:
            raise ValueError("dielectric must be positive")
        if self.photon_ev < 0:
            raise ValueError("photon_ev must be non-negative")

    def with_(self, **changes) -> "Conditions":
        """A copy with some coordinates replaced. Handy as an ``experiment`` move."""
        allowed = {"temperature_k", "pressure_atm", "dielectric", "photon_ev"}
        unknown = set(changes) - allowed
        if unknown:
            raise TypeError(f"unknown condition field(s): {', '.join(sorted(unknown))}")
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


#: Illustrative approximate *static* relative permittivities near room temperature, adapted
#: from CRC Handbook, 104th ed., section 6. These legacy scalars omit record-level
#: temperature, frequency, phase and uncertainty (water 80.1 is roughly a 20 C value), so
#: they are sweep conveniences rather than reproducible constitutive-law records. A solver
#: must not silently combine them with an unrelated ``Conditions.temperature_k``.
SOLVENTS: Mapping[str, float] = MappingProxyType({
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
})


def grid(
    temperatures: Sequence[float] = (298.15,),
    pressures: Sequence[float] = (1.0,),
    dielectrics: Sequence[float] = (1.0,),
    photons: Sequence[float] = (0.0,),
) -> list[Conditions]:
    """
    The Cartesian product of the requested axes.

    Note the cost is multiplicative in the axes -- a 20x20x20 sweep is 8000 oracle calls.
    With an expensive oracle that matters. Closed reactions that fail atom or net-charge
    conservation can be rejected before such a sweep, but the Store itself performs no
    physical pruning.
    """
    return [
        Conditions(t, p, d, e)
        for t in temperatures
        for p in pressures
        for d in dielectrics
        for e in photons
    ]
