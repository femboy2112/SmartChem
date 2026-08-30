"""M-4b C2 — mediated (solution / byproduct) decomposition edges.

v1 (`smartchem.decompiler`) splits a target using only the target's own atoms, so it cannot
represent the reaction a chemist actually runs: paracetamol degrades by **hydrolysis**,
consuming water from solution — `paracetamol + H2O -> 4-aminophenol + acetic acid` — and the
`4-aminophenol + acetic acid` pair does not balance against paracetamol without that water. The
litmus's #1 gap.

A :class:`MediatedEdge` closes it: `n . reactant (+ reagents drawn from a declared medium) ->
products`, where the **whole system conserves**, every product is a strictly-lower-rank fragment
of the target (so the descent — and termination — is unchanged from v1), and the reagents are
small helpers pulled from a declared closed `medium` inventory. Reagents are consumed *into* the
products (no species is both a reagent and a product in one edge — a pure pass-through would be a
plain decomposition with a spectator, and catalytic reagent=product regeneration is a later C2b
refinement).

Termination is preserved exactly: products are strictly lower rank than the reactant, and reagents
are strictly lower rank too, so no edge grows a species and the recursion still descends in the
multiset order. The medium is a **closed declared inventory** (the registry pattern), not open.

This is still formal, not physical: a mediated edge certifies that the *augmented* system conserves
mass, and establishes nothing about whether the reaction occurs, its conditions, or its rate — the
same boundary as the rest of M-4, now with a solution ledger. Conditions/safety ride on top via the
C0/review layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from math import gcd

from .contracts import Digestible
from .decompiler import Formula

__all__ = [
    "MEDIATED_SCHEMA",
    "MediatedEdge",
    "mediated_edges",
]

MEDIATED_SCHEMA = "smartchem.decompiler/mediated-edge-v1"


def _multi_gcd(values: tuple[int, ...]) -> int:
    return reduce(gcd, values, 0)


def _sort_key(formula: Formula) -> tuple:
    return (formula.counts, formula.charge)


def _coerce(value: "str | dict[str, int] | Formula") -> Formula:
    if isinstance(value, Formula):
        return value
    if isinstance(value, str):
        return Formula.parse(value)
    if isinstance(value, dict):
        return Formula.of(value)
    raise TypeError(f"cannot coerce {type(value).__name__} to a Formula")


@dataclass(frozen=True)
class MediatedEdge(Digestible):
    """One reagent-assisted decomposition ``n . reactant + reagents -> products``.

    Every invariant is enforced at construction, as in v1:

    * **conservation of the augmented system** — ``n.reactant + sum(reagents) == sum(products)``
      element by element (and charge, zero in v1);
    * **descent (termination)** — every product *and* every reagent is strictly lower rank than the
      reactant, so no species grows and the recursion terminates;
    * **genuine mediation** — at least one reagent, and no species is both a reagent and a product
      (a pass-through would be a plain decomposition with a spectator);
    * **a real split** — at least two product instances;
    * canonical unit-bucket spelling for single-element reagents/products, and primitivity over all
      coefficients.
    """

    reactant: Formula
    reactant_multiplicity: int
    reagents: tuple[tuple[Formula, int], ...]
    products: tuple[tuple[Formula, int], ...]

    def __post_init__(self) -> None:
        if type(self.reactant) is not Formula:
            raise TypeError("reactant must be a Formula")
        if type(self.reactant_multiplicity) is not int or self.reactant_multiplicity < 1:
            raise ValueError("reactant_multiplicity must be an int >= 1")
        if self.reactant.charge != 0:
            raise ValueError("v1 mediates neutral species only; reactant is charged")
        for role, pairs, need in (("reagents", self.reagents, 1), ("products", self.products, 2)):
            if type(pairs) is not tuple or len(pairs) < 1:
                raise TypeError(f"{role} must be a non-empty tuple of (Formula, multiplicity)")
        r_rank = self.reactant.rank

        def _check(pairs, role):
            instances = 0
            for pair in pairs:
                if type(pair) is not tuple or len(pair) != 2:
                    raise TypeError(f"each {role} entry must be a (Formula, multiplicity) pair")
                species, mult = pair
                if type(species) is not Formula:
                    raise TypeError(f"each {role} must be a Formula")
                if type(mult) is not int or mult < 1:
                    raise ValueError(f"each {role} multiplicity must be an int >= 1")
                if species.charge != 0:
                    raise ValueError(f"v1 {role} are neutral; one is charged")
                if species.rank >= r_rank:
                    raise ValueError(
                        f"non-descending {role} {species!r} (rank {species.rank}) for reactant "
                        f"{self.reactant!r} (rank {r_rank}); reagents and products must be strictly "
                        f"lower rank so the descent terminates"
                    )
                if species.is_element and species.counts[0][1] != 1:
                    raise ValueError(f"element-bucket {role} {species!r} must be the unit bucket")
                instances += mult
            keys = [(_sort_key(s), m) for s, m in pairs]
            if keys != sorted(keys):
                raise ValueError(f"{role} must be sorted canonically")
            if len({s for s, _ in pairs}) != len(pairs):
                raise ValueError(f"a {role} species appears twice; merge its multiplicities")
            return instances

        _check(self.reagents, "reagent")
        product_instances = _check(self.products, "product")
        if product_instances < 2:
            raise ValueError("a mediated decomposition must have at least two product instances")

        reagent_species = {s for s, _ in self.reagents}
        if reagent_species & {s for s, _ in self.products}:
            raise ValueError(
                "a species is both a reagent and a product (a pass-through/spectator); C2 requires "
                "reagents consumed into products (catalytic regeneration is a later refinement)"
            )

        # conservation of the augmented system: n.reactant + reagents == products
        want: dict[str, int] = {s: self.reactant_multiplicity * k for s, k in self.reactant.counts}
        for reagent, mult in self.reagents:
            for s, k in reagent.counts:
                want[s] = want.get(s, 0) + mult * k
        got: dict[str, int] = {}
        for product, mult in self.products:
            for s, k in product.counts:
                got[s] = got.get(s, 0) + mult * k
        if got != want:
            raise ValueError(
                f"mass not conserved: {self.reactant_multiplicity} . {self.reactant!r} + reagents "
                f"carries {want} but products carry {got}"
            )

        coeffs = (
            (self.reactant_multiplicity,)
            + tuple(m for _, m in self.reagents)
            + tuple(m for _, m in self.products)
        )
        if _multi_gcd(coeffs) != 1:
            raise ValueError("edge is not primitive; divide all coefficients by their common factor")

    def equation(self) -> str:
        def term(mult: int, formula: Formula) -> str:
            return f"{mult} {formula!r}" if mult > 1 else repr(formula)
        lhs = " + ".join(
            [term(self.reactant_multiplicity, self.reactant)]
            + [term(m, r) for r, m in self.reagents]
        )
        rhs = " + ".join(term(m, p) for p, m in self.products)
        return f"{lhs} -> {rhs}"

    def __repr__(self) -> str:
        return f"MediatedEdge({self.equation()})"


def _reagent_multisets(candidates: list[Formula], max_instances: int) -> list[dict[Formula, int]]:
    """Every non-empty reagent multiset of total size 1..max_instances (combinations w/ repetition)."""
    out: list[dict[Formula, int]] = []

    def rec(start: int, chosen: dict[Formula, int], count: int) -> None:
        if count >= 1:
            out.append(dict(chosen))
        if count >= max_instances:
            return
        for i in range(start, len(candidates)):
            c = candidates[i]
            chosen[c] = chosen.get(c, 0) + 1
            rec(i, chosen, count + 1)
            chosen[c] -= 1
            if chosen[c] == 0:
                del chosen[c]

    rec(0, {}, 0)
    return out


def mediated_edges(
    reactant: "str | dict[str, int] | Formula",
    inventory: "tuple[Formula, ...] | tuple[str, ...]" = (),
    medium: "tuple[Formula, ...] | tuple[str, ...]" = (),
    *,
    max_reagent_instances: int = 2,
    max_multiplicity: int = 1,
    budget: int = 200_000,
) -> tuple[tuple[MediatedEdge, ...], bool]:
    """Every primitive mediated decomposition of ``reactant`` over closed ``inventory`` + ``medium``.

    For each reagent multiset drawn from ``medium`` (size 1..``max_reagent_instances``, each reagent
    lower-rank than the reactant) and each reactant multiplicity ``n``, the products enumerate every
    bucket-forced multiset summing to ``n.reactant + reagents`` over the lower-rank ``inventory``
    compounds and element buckets. Returns ``(edges, complete)``; ``complete`` is ``False`` iff the
    search hit ``budget`` (a partial result, never silently a full one).
    """
    reactant_f = _coerce(reactant)
    if reactant_f.charge != 0:
        raise ValueError("v1 mediates neutral targets only")
    r_rank = reactant_f.rank
    inv = [f for f in (_coerce(s) for s in inventory)
           if f.charge == 0 and 0 < f.rank < r_rank and not f.is_element]
    med = [f for f in (_coerce(s) for s in medium) if f.charge == 0 and 0 < f.rank < r_rank]
    med = sorted(set(med), key=_sort_key)

    edges: dict[str, MediatedEdge] = {}
    work = [0]
    complete = True

    def enumerate_products(target: dict[str, int], molecular: list[Formula], reagents_key):
        nonlocal complete

        def register(t: dict[str, int], chosen: list[tuple[Formula, int]]) -> None:
            merged: dict[Formula, int] = {}
            for formula, m in chosen:
                merged[formula] = merged.get(formula, 0) + m
            for symbol, left in t.items():
                if left:
                    b = Formula.bucket(symbol)
                    merged[b] = merged.get(b, 0) + left
            if sum(merged.values()) < 2:
                return
            products = tuple(sorted(merged.items(), key=lambda pm: (_sort_key(pm[0]), pm[1])))
            n, reagents = reagents_key
            coeffs = (n,) + tuple(m for _, m in reagents) + tuple(m for _, m in products)
            scale = _multi_gcd(coeffs)
            try:
                edge = MediatedEdge(
                    reactant_f,
                    n // scale,
                    tuple((r, m // scale) for r, m in reagents),
                    tuple((p, m // scale) for p, m in products),
                )
            except ValueError:
                return  # non-descending / pass-through / non-conserving combination is dropped
            edges[edge.digest] = edge

        def solve(t: dict[str, int], start: int, chosen: list[tuple[Formula, int]]) -> bool:
            work[0] += 1
            if work[0] > budget:
                return False
            register(t, chosen)
            for idx in range(start, len(molecular)):
                cand = molecular[idx]
                cap = min(t.get(s, 0) // k for s, k in cand.counts)
                if cap <= 0:
                    continue
                for m in range(cap, 0, -1):
                    nt = dict(t)
                    for s, k in cand.counts:
                        nt[s] -= m * k
                    chosen.append((cand, m))
                    if not solve(nt, idx + 1, chosen):
                        chosen.pop()
                        return False
                    chosen.pop()
            return True

        if not solve(target, 0, []):
            complete = False

    for n in range(1, max_multiplicity + 1):
        for reagent_map in _reagent_multisets(med, max_reagent_instances):
            reagents = tuple(sorted(reagent_map.items(), key=lambda pm: (_sort_key(pm[0]), pm[1])))
            target = {s: n * k for s, k in reactant_f.counts}
            for reagent, mult in reagents:
                for s, k in reagent.counts:
                    target[s] = target.get(s, 0) + mult * k
            elements = frozenset(target)
            molecular = [f for f in inv if f.elements <= elements]
            molecular = sorted(set(molecular), key=lambda f: (-f.rank, _sort_key(f)))
            enumerate_products(target, molecular, (n, reagents))
            if not complete:
                return tuple(sorted(edges.values(), key=_edge_key)), False

    return tuple(sorted(edges.values(), key=_edge_key)), complete


def _edge_key(edge: MediatedEdge) -> tuple:
    return (
        _sort_key(edge.reactant),
        edge.reactant_multiplicity,
        tuple((_sort_key(r), m) for r, m in edge.reagents),
        tuple((_sort_key(p), m) for p, m in edge.products),
    )
