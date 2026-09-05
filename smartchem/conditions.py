"""M-4b C0 — condition contexts and the Env comonad (the conditions-aware decompiler's spine).

M-4 v1 (`smartchem.decompiler`) is the *structural skeleton*: the space of conservation-valid
decompositions, context-free. A real chemist needs the other half — *under what conditions is a
step possible?* — and that half is **comonadic**, not a field bolted onto an edge.

Why a comonad, precisely
------------------------
The repo's `pathway.Pathway` is a monad: it *produces* a reaction network and accumulates effects.
Conditions are the dual: a step is a value *embedded in a condition context*, and the operations
you want are a comonad's. This module implements the **Env (coreader) comonad** ``Env C a = (C, a)``
— a value paired with the :class:`ConditionEnvelope` it lives in:

* ``extract : (C, a) -> a`` — the value *as realized in this context*. (In later rungs, a product
  whose ``extract`` "fails" — survives only transiently under the very conditions that formed it —
  is the milliseconds-stability case; C0 only establishes the algebra.)
* ``extend : (Env C a -> b) -> Env C a -> Env C b`` — re-evaluate a context-dependent function at
  this context, keeping the context. This is what lets a *whole chain* be judged co-valid under one
  shared envelope rather than as a product of independent per-edge checks.
* ``duplicate : Env C a -> Env C (Env C a)`` — expose the context around the value.

The three comonad laws (``extend extract = id``; ``extract . extend f = f``;
``extend f . extend g = extend (f . extend g)``) hold by construction here and are property-tested
in ``tests/test_conditions.py``.

The boundary that keeps this honest (formal ≠ physical, one layer up)
--------------------------------------------------------------------
A :class:`ConditionEnvelope` is a **declared context, never a prediction**. It carries an
:class:`~smartchem.contracts.EvidenceStatus`, provenance, and an optional typed source citation, and:

* the only ``UNSUPPORTED`` envelope is the empty :meth:`ConditionEnvelope.unknown` — the honest
  default for the overwhelming majority of formal edges, which have no sourced conditions;
* any *declared* condition (a temperature, a medium, a catalyst, …) **requires a non-empty
  provenance**, but free text remains ``DECLARED`` and is not laundered into sourced evidence;
* the status is **capped at ``EXPERIMENTAL``** — a decorator layer never raises a condition to a
  certified-lane status (`VALIDATED_WITHIN_REGIME`/`ESTABLISHED`), because that vocabulary carries
  governance the conditions layer's machinery does not run (the label-borrowing constraint the
  evidence bridge already established).

Nothing here computes chemistry. It is the exact context algebra onto which C1 (sourced
annotation), C2 (mediated/solution edges), C3 (stability), and C4 (the Store-comonad cost frontier)
will hang, each as a separately-tiered `EvidenceIR`-shaped layer over the certified conservation
skeleton.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .contracts import Digestible, EvidenceStatus
from .provenance import SourceCitation
from .process_constraints import ProcessRequirements

__all__ = [
    "Interval",
    "ConditionEnvelope",
    "Conditioned",
    "condition",
    "unconditioned",
    "extract",
    "extend",
    "duplicate",
]

A = TypeVar("A")
B = TypeVar("B")

#: A declared-condition envelope never claims a certified-lane status; the cap is EXPERIMENTAL.
_ALLOWED_STATUS = (
    EvidenceStatus.UNSUPPORTED,
    EvidenceStatus.STRUCTURAL_TOY,
    EvidenceStatus.EXPERIMENTAL,
)


@dataclass(frozen=True)
class Interval(Digestible):
    """A closed ``[lo, hi]`` range in a named unit -- a condition bound (T, P, time, …)."""

    lo: float
    hi: float
    unit: str

    def __post_init__(self) -> None:
        for name in ("lo", "hi"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"interval {name} must be a real number")
            if not math.isfinite(v):
                raise ValueError(f"interval {name} must be finite")
            object.__setattr__(self, name, float(v))  # normalise int/float so digests are stable
        if self.lo > self.hi:
            raise ValueError(f"interval lo ({self.lo}) must be <= hi ({self.hi})")
        if not isinstance(self.unit, str) or not self.unit:
            raise ValueError("interval unit must be a non-empty string")


@dataclass(frozen=True)
class ConditionEnvelope(Digestible):
    """The comonadic context: the declared conditions under which a step is claimed possible.

    Every field is optional; the empty envelope (:meth:`unknown`) is the honest "no declared
    conditions" default. A non-empty envelope is a *declaration* and is refused unless it carries
    provenance and a below-certified status. Only an accepted :class:`SourceCitation` earns a sourced label.
    """

    temperature: Interval | None = None
    pressure: Interval | None = None
    duration: Interval | None = None
    medium: str = ""
    catalysts: tuple[str, ...] = ()
    applied_field: str = ""
    status: EvidenceStatus = EvidenceStatus.UNSUPPORTED
    provenance: str = ""
    source: SourceCitation | None = None
    process: ProcessRequirements | None = None

    def __post_init__(self) -> None:
        if self.process is not None and type(self.process) is not ProcessRequirements:
            raise TypeError("process must be a ProcessRequirements or None")
        for name in ("temperature", "pressure", "duration"):
            v = getattr(self, name)
            if v is not None and type(v) is not Interval:
                raise TypeError(f"{name} must be an Interval or None")
        # Every downstream consumer compares these raw magnitudes against K / atm thresholds.  Accepting an
        # arbitrary unit here would make a perfectly valid-looking envelope catastrophically ambiguous (for
        # example 20--100 C was previously read as 20--100 K and triggered an ice-bath recommendation).
        # Convert before construction or refuse; silent unit reinterpretation is never a convenience.
        if self.temperature is not None and self.temperature.unit != "K":
            raise ValueError(
                f"temperature intervals must use unit 'K', got {self.temperature.unit!r}; convert explicitly"
            )
        if self.pressure is not None and self.pressure.unit != "atm":
            raise ValueError(
                f"pressure intervals must use unit 'atm', got {self.pressure.unit!r}; convert explicitly"
            )
        for name in ("temperature", "pressure"):
            value = getattr(self, name)
            if value is not None and value.lo <= 0:
                raise ValueError(f"{name} must be positive")
        if self.duration is not None and self.duration.lo < 0:
            raise ValueError("duration must be nonnegative")
        for name in ("medium", "applied_field", "provenance"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be a string")
        if type(self.catalysts) is not tuple or any(
            not isinstance(c, str) or not c for c in self.catalysts
        ):
            raise TypeError("catalysts must be a tuple of non-empty strings")
        object.__setattr__(self, "catalysts", tuple(sorted(set(self.catalysts))))
        if not isinstance(self.status, EvidenceStatus):
            raise TypeError("status must be an EvidenceStatus")
        if self.source is not None and type(self.source) is not SourceCitation:
            raise TypeError("source must be a SourceCitation or None")
        if self.status not in _ALLOWED_STATUS:
            raise ValueError(
                f"a declared-condition envelope never claims a certified-lane status; "
                f"the cap is EXPERIMENTAL, got {self.status.value}"
            )
        declared = any((
            self.temperature is not None,
            self.pressure is not None,
            self.duration is not None,
            self.medium,
            self.catalysts,
            self.applied_field,
        ))
        if self.status is EvidenceStatus.UNSUPPORTED:
            if declared:
                raise ValueError(
                    "UNSUPPORTED is the unknown/unconditioned envelope and may declare no "
                    "conditions; state a source and raise the status, or leave it empty"
                )
        else:
            if not declared:
                raise ValueError(
                    "a declared envelope (status above UNSUPPORTED) must state at least one condition"
                )
            if not self.provenance.strip():
                raise ValueError(
                    "a declared envelope must carry a non-empty provenance; conditions are never "
                    "anonymous (state whether the provenance is a declaration or source citation)"
                )
        if self.source is not None and self.status is not EvidenceStatus.EXPERIMENTAL:
            raise ValueError("a cited condition must carry EXPERIMENTAL evidence status")

    @classmethod
    def unknown(cls) -> "ConditionEnvelope":
        """The honest default: no declared conditions (status ``UNSUPPORTED``)."""
        return cls()

    @property
    def is_declared(self) -> bool:
        return self.status is not EvidenceStatus.UNSUPPORTED

    @property
    def is_sourced(self) -> bool:
        """True only for a declared envelope whose typed source was explicitly accepted by review."""
        return self.is_declared and self.source is not None and self.source.accepted


@dataclass(frozen=True)
class Conditioned(Digestible, Generic[A]):
    """The Env comonad ``Env C a``: a value together with the condition context it lives in.

    ``value`` is any semantic value -- a :class:`~smartchem.decompiler.DecompositionEdge`, a product,
    or (during ``duplicate``) another :class:`Conditioned`. The comonad operations keep the envelope
    fixed and move only the value; that fixed context is exactly what a whole chain is judged inside.
    """

    envelope: ConditionEnvelope
    value: A

    def __post_init__(self) -> None:
        if type(self.envelope) is not ConditionEnvelope:
            raise TypeError("envelope must be a ConditionEnvelope")

    def extract(self) -> A:
        """The value as realized in this context (``counit``)."""
        return self.value

    def extend(self, f: "Callable[[Conditioned[A]], B]") -> "Conditioned[B]":
        """Re-evaluate a context-dependent function here, keeping the context (``cobind``)."""
        return Conditioned(self.envelope, f(self))

    def duplicate(self) -> "Conditioned[Conditioned[A]]":
        """Expose the context around the value (``comultiplication``)."""
        return Conditioned(self.envelope, self)

    def map(self, g: "Callable[[A], B]") -> "Conditioned[B]":
        """Functorial map over the value alone."""
        return Conditioned(self.envelope, g(self.value))


# -- point-free aliases, the form the comonad laws are stated in --------------------------
def extract(w: "Conditioned[A]") -> A:
    return w.extract()


def extend(f: "Callable[[Conditioned[A]], B]", w: "Conditioned[A]") -> "Conditioned[B]":
    return w.extend(f)


def duplicate(w: "Conditioned[A]") -> "Conditioned[Conditioned[A]]":
    return w.duplicate()


def condition(value: A, envelope: ConditionEnvelope | None = None) -> "Conditioned[A]":
    """Place a value in a condition context (the unknown/unconditioned envelope by default)."""
    return Conditioned(envelope if envelope is not None else ConditionEnvelope.unknown(), value)


def unconditioned(value: A) -> "Conditioned[A]":
    """Place a value in the honest no-declared-conditions context."""
    return Conditioned(ConditionEnvelope.unknown(), value)
