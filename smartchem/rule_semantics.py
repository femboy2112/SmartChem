"""Small exact semantics for rule-calculus research, not bench authorization.

Relations keep compatibility witnesses; intervals keep uncertainty; separate
capability axes keep ignorance out of the success lane. These are finite model
checks, not empirical validation or a universal reaction classifier.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Hashable, Iterable, Mapping


@dataclass(frozen=True)
class FiniteRelation:
    domain: frozenset[Hashable]
    codomain: frozenset[Hashable]
    pairs: frozenset[tuple[Hashable, Hashable]]

    def __post_init__(self) -> None:
        if any(type(x) is not frozenset for x in (self.domain, self.codomain, self.pairs)):
            raise ValueError("finite relation carriers and pairs must be frozen sets")
        if any(type(p) is not tuple or len(p) != 2 or p[0] not in self.domain
               or p[1] not in self.codomain for p in self.pairs):
            raise ValueError("relation pair outside declared carriers")

    @classmethod
    def identity(cls, states: frozenset[Hashable]) -> FiniteRelation:
        return cls(states, states, frozenset((x, x) for x in states))

    def then(self, other: FiniteRelation) -> FiniteRelation:
        if self.codomain != other.domain:
            raise ValueError("context carriers disagree; an explicit transport is needed")
        return FiniteRelation(self.domain, other.codomain, frozenset(
            (a, c) for a, b in self.pairs for bb, c in other.pairs if b == bb
        ))

    def tensor(self, other: FiniteRelation) -> FiniteRelation:
        return FiniteRelation(
            frozenset((a, b) for a in self.domain for b in other.domain),
            frozenset((a, b) for a in self.codomain for b in other.codomain),
            frozenset(((a, c), (b, d)) for a, b in self.pairs for c, d in other.pairs),
        )

    def image(self, inputs: frozenset[Hashable]) -> frozenset[Hashable]:
        if not inputs <= self.domain:
            raise ValueError("input set outside domain")
        return frozenset(b for a, b in self.pairs if a in inputs)

    def may_preimage(self, outputs: frozenset[Hashable]) -> frozenset[Hashable]:
        if not outputs <= self.codomain:
            raise ValueError("output set outside codomain")
        return frozenset(a for a, b in self.pairs if b in outputs)

    def must_preimage(self, outputs: frozenset[Hashable]) -> frozenset[Hashable]:
        """Right adjoint to image; empty successor sets satisfy this VACUOUSLY.

        This is a safety-style universal preimage, not an existence witness.
        Conjoin with may_preimage(codomain) when nonblocking execution is needed.
        """
        if not outputs <= self.codomain:
            raise ValueError("output set outside codomain")
        return self.domain - frozenset(a for a, b in self.pairs if b not in outputs)


@dataclass(frozen=True)
class FibreCollision:
    observation: Hashable
    left_case: Hashable
    right_case: Hashable
    left_verdict: Hashable
    right_verdict: Hashable


def fibre_collisions(rows: Iterable[tuple[Hashable, Hashable, Hashable]]) -> tuple[FibreCollision, ...]:
    """Given (case, observation, verdict), find finite factorization obstructions.

    No collisions certifies factorization ONLY on the supplied labelled cases.
    It does not certify an external label's truth or an untested population.
    """
    seen: dict[Hashable, tuple[Hashable, Hashable]] = {}
    collisions = []
    for case, observation, verdict in rows:
        if observation in seen:
            prior_case, prior_verdict = seen[observation]
            if verdict != prior_verdict:
                collisions.append(FibreCollision(observation, prior_case, case, prior_verdict, verdict))
        else:
            seen[observation] = case, verdict
    return tuple(collisions)


@dataclass(frozen=True)
class QuantityInterval:
    unit: str
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if type(self.unit) is not str or not self.unit:
            raise ValueError("explicit nonempty unit required")
        if any(type(x) not in (int, Fraction) for x in (self.lower, self.upper)):
            raise ValueError("use exact integers or Fractions, not floats or booleans")
        object.__setattr__(self, "lower", Fraction(self.lower))
        object.__setattr__(self, "upper", Fraction(self.upper))
        if self.lower > self.upper:
            raise ValueError("reversed interval")

    def __add__(self, other: QuantityInterval) -> QuantityInterval:
        if self.unit != other.unit:
            raise ValueError("unit/context mismatch")
        return QuantityInterval(self.unit, self.lower + other.lower, self.upper + other.upper)


def sum_known(values: Iterable[QuantityInterval | None], *, unit: str) -> QuantityInterval | None:
    """Add exact enclosures; unknown is absorbing, not a zero-price bargain."""
    total = QuantityInterval(unit, 0, 0)
    missing = False
    for value in values:
        if value is None:
            missing = True
        else:
            total = total + value
    return None if missing else total


def robustly_dominates(a: tuple[QuantityInterval | None, ...],
                      b: tuple[QuantityInterval | None, ...]) -> bool:
    """Sufficient strict Pareto dominance for every realization in the boxes.

    All objectives minimize; any unknown coordinate prevents this certificate.
    Correlation-aware dominance may be stronger; we do not invent independence.
    """
    if len(a) != len(b):
        raise ValueError("objective dimensions differ")
    if any(x is None for x in a + b):
        return False
    pairs = tuple(zip(a, b))
    if any(x.unit != y.unit for x, y in pairs):
        raise ValueError("objective units differ")
    return all(x.upper <= y.lower for x, y in pairs) and any(x.upper < y.lower for x, y in pairs)


class AxisVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


CAPABILITY_AXES = (
    "substrates", "conditions", "kinetics_selectivity", "equipment_containment",
    "separation", "identity_purity", "waste_handling",
)


def capability_verdict(axes: Mapping[str, AxisVerdict]) -> str:
    """Aggregate DECLARED evidence; no structural certificate fills missing axes.

    SUPPORTED is caller-supplied, not authenticated laboratory evidence. The
    resulting FITS_DECLARED_MODEL is neither safe-to-run nor experimentally valid.
    """
    if set(axes) - set(CAPABILITY_AXES):
        raise ValueError("unrecognized capability axis (possible typo)")
    if any(type(v) is not AxisVerdict for v in axes.values()):
        raise ValueError("typed AxisVerdict values required")
    values = tuple(axes.get(k, AxisVerdict.UNKNOWN) for k in CAPABILITY_AXES)
    if AxisVerdict.BLOCKED in values:
        return "BLOCKED"
    if AxisVerdict.UNKNOWN in values:
        return "UNKNOWN"
    return "FITS_DECLARED_MODEL"


@dataclass(frozen=True, order=True)
class PotentialKey:
    """A symbolic state-potential coordinate; identities must be explicit.

    environment_id must bind temperature, standard state, activity convention,
    reservoirs and other model context. An empty/missing phase is NOT a wildcard.
    No key is inferred from a molecular formula or an informal chemical name.
    """
    species_id: str
    phase: str
    environment_id: str
    model_id: str

    def __post_init__(self) -> None:
        if any(type(x) is not str or not x for x in (
            self.species_id, self.phase, self.environment_id, self.model_id
        )):
            raise ValueError("every potential identity coordinate must be explicit")


@dataclass(frozen=True)
class PotentialBalance:
    """A finite signed stoichiometric ledger of SHARED potential variables.

    Normalize algebraically BEFORE partial numerical evaluation. Unknown
    internal variables may cancel from a net boundary without making a single
    unknown step feasible. This is an auxiliary symbolic model, not a change to
    the production thermodynamic/feasibility ranker.
    """
    terms: tuple[tuple[PotentialKey, Fraction], ...] = ()

    def __post_init__(self) -> None:
        if type(self.terms) is not tuple:
            raise ValueError("terms must be a tuple")
        acc: dict[PotentialKey, Fraction] = {}
        for term in self.terms:
            if type(term) is not tuple or len(term) != 2:
                raise ValueError("each term must be a (PotentialKey, coefficient) pair")
            key, coefficient = term
            if type(key) is not PotentialKey or type(coefficient) not in (int, Fraction):
                raise ValueError("typed state identities and exact coefficients required")
            acc[key] = acc.get(key, Fraction(0)) + coefficient
        object.__setattr__(self, "terms", tuple(sorted((k, Fraction(c)) for k, c in acc.items() if c)))

    def __add__(self, other: PotentialBalance) -> PotentialBalance:
        return PotentialBalance(self.terms + other.terms)

    def evaluate(self, values: Mapping[PotentialKey, QuantityInterval | None], *, unit: str) -> QuantityInterval | None:
        pieces = []
        for key, coefficient in self.terms:
            interval = values.get(key)
            if interval is None:
                pieces.append(None)
            else:
                ends = (coefficient * interval.lower, coefficient * interval.upper)
                pieces.append(QuantityInterval(interval.unit, min(ends), max(ends)))
        return sum_known(pieces, unit=unit)
