"""COST-VEC-01 (2b): the section-10.4 vector-affordability core -- CostVector, Pareto dominance, basket aggregation.

Pins the two honest section-10.4 rules (a hard blocker dominates cost; an UNKNOWN axis is incomparable so the
frontier never over-ranks on absent data) and proves the basket aggregation over REAL 2a commodity prices is
non-vacuous and fails to UNKNOWN rather than fabricating a cheaper total.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from smartchem.data.reagents import COMMODITY_REAGENTS
from smartchem.experiment.affordability import (
    CostVector,
    basket_cost_vector,
    dominates,
    pareto_frontier,
)

_BY_NAME = {c.name: c for c in COMMODITY_REAGENTS}


@dataclass(frozen=True)
class _Item:
    name: str
    cost_vector: CostVector


# ---- CostVector validation ----

def test_costvector_refuses_a_fabricated_or_nonnumeric_axis():
    with pytest.raises(TypeError):
        CostVector(cash=float("nan"))
    with pytest.raises(TypeError):
        CostVector(cash="cheap")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        CostVector(hard_blockers=("",))  # a blocker needs a real reason


# ---- dominance: the ordinary Pareto cases ----

def test_strictly_cheaper_same_access_dominates():
    a = CostVector(cash=52.95, access_difficulty=0)
    b = CostVector(cash=169.35, access_difficulty=0)
    assert dominates(a, b)
    assert not dominates(b, a)


def test_a_tie_is_not_domination():
    a = CostVector(cash=10.0, access_difficulty=1)
    b = CostVector(cash=10.0, access_difficulty=1)
    assert not dominates(a, b) and not dominates(b, a)


def test_a_tradeoff_is_incomparable_not_dominated():
    cheap_but_hard = CostVector(cash=10.0, access_difficulty=3)
    dear_but_easy = CostVector(cash=99.0, access_difficulty=0)
    assert not dominates(cheap_but_hard, dear_but_easy)
    assert not dominates(dear_but_easy, cheap_but_hard)


# ---- dominance: UNKNOWN is incomparable, never over-ranked ----

def test_unknown_axis_blocks_domination_both_ways():
    known = CostVector(cash=1.0)             # knows only cash
    other_axis = CostVector(access_difficulty=0)  # knows only access
    # no axis one knows that the other also knows -> neither dominates (fully incomparable)
    assert not dominates(known, other_axis) and not dominates(other_axis, known)


def test_cannot_dominate_when_unknown_on_an_axis_the_other_knows():
    cheaper_unknown_access = CostVector(cash=1.0)                 # access UNKNOWN
    dearer_known_access = CostVector(cash=2.0, access_difficulty=5)
    # the cheaper one is UNKNOWN on access, which the other KNOWS -> it cannot claim no-worse -> no domination
    assert not dominates(cheaper_unknown_access, dearer_known_access)
    # the dearer one is worse on cash (the only axis the cheaper one knows) -> also no domination
    assert not dominates(dearer_known_access, cheaper_unknown_access)


def test_knowing_more_still_dominates_on_the_others_known_axis():
    richer = CostVector(cash=1.0, access_difficulty=0)  # knows cash + access
    poorer = CostVector(cash=2.0)                        # knows only cash
    # richer is <= on every axis poorer knows (cash), strictly better on cash -> dominates; the extra known axis
    # cannot be BEATEN by poorer's unknown, so it does not block.
    assert dominates(richer, poorer)
    assert not dominates(poorer, richer)  # poorer is UNKNOWN on access which richer knows


def test_all_unknown_is_dominated_by_nothing():
    nothing_known = CostVector()
    priced = CostVector(cash=1.0, access_difficulty=0)
    assert not dominates(priced, nothing_known)  # nothing to be strictly better ON
    assert not dominates(nothing_known, priced)


# ---- dominance: a hard blocker dominates cost (section 10.4 / G6) ----

def test_a_hard_blocker_dominates_cost():
    blocked_cheap = CostVector(cash=1.0, hard_blockers=("flammable: open-flame step",))
    clean_dear = CostVector(cash=10_000.0)
    assert dominates(clean_dear, blocked_cheap)       # clean beats blocked at ANY price
    assert not dominates(blocked_cheap, clean_dear)   # a blocked option never dominates a clean one


def test_both_blocked_falls_back_to_the_numeric_axes():
    a = CostVector(cash=1.0, hard_blockers=("legal",))
    b = CostVector(cash=2.0, hard_blockers=("legal",))
    assert dominates(a, b) and not dominates(b, a)  # equally blocked -> cheaper wins


# ---- the frontier ----

def test_pareto_frontier_drops_the_dominated_and_keeps_the_tradeoffs():
    items = [
        _Item("cheap-easy", CostVector(cash=10.0, access_difficulty=0)),   # dominates dear-easy
        _Item("dear-easy", CostVector(cash=99.0, access_difficulty=0)),    # dominated
        _Item("cheaper-hard", CostVector(cash=5.0, access_difficulty=3)),  # tradeoff -> stays
        _Item("blocked", CostVector(cash=1.0, hard_blockers=("unsafe",))),  # dominated by any clean
    ]
    names = {it.name for it in pareto_frontier(items)}
    assert names == {"cheap-easy", "cheaper-hard"}


def test_frontier_requires_a_cost_vector():
    with pytest.raises(TypeError):
        pareto_frontier([object()])


def test_dominance_is_a_sound_strict_partial_order():
    """The frontier is only well-defined (order-independent) if `dominates` is irreflexive, asymmetric, and
    transitive. A seeded brute-force over random vectors (mixed UNKNOWN axes + hard blockers) pins all three, so a
    future edit that (say) makes UNKNOWN over-rank or breaks transitivity is caught here, not silently."""
    import random

    rng = random.Random(1234)
    axes = ["cash", "access_difficulty", "evidence_tier_rank", "new_equipment", "material_quantity"]

    def rand_vec() -> CostVector:
        kw: dict = {a: float(rng.randint(0, 3)) for a in axes if rng.random() < 0.5}
        if rng.random() < 0.3:
            kw["hard_blockers"] = ("blk",)
        return CostVector(**kw)

    vs = [rand_vec() for _ in range(200)]
    assert not any(dominates(v, v) for v in vs)  # irreflexive
    for _ in range(8000):
        a, b, c = rng.choice(vs), rng.choice(vs), rng.choice(vs)
        assert not (dominates(a, b) and dominates(b, a))  # asymmetric: no mutual domination
        if dominates(a, b) and dominates(b, c):
            assert dominates(a, c)  # transitive


# ---- basket aggregation over REAL 2a commodity prices ----

def _mol(name: str):
    return _BY_NAME[name].molecule


def test_basket_sums_real_prices_and_takes_the_worst_access():
    salt, soda = _mol("sodium chloride"), _mol("sodium carbonate")
    v = basket_cost_vector([salt, soda])
    assert v.cash == pytest.approx(52.95 + 169.35)  # sum of the two 2a prices
    assert v.unit == "metric ton" and v.currency == "USD"
    assert v.access_difficulty == 0  # both grocery -> worst is still grocery(0)


def test_one_unpriced_leaf_drops_basket_cash_to_unknown():
    salt, ethanol = _mol("sodium chloride"), _mol("ethanol")  # ethanol is a commodity but unpriced (2a)
    v = basket_cost_vector([salt, ethanol])
    assert v.cash is None                    # fail-SAFE: not the salt price alone, not a fabricated total
    assert v.access_difficulty == 0          # both are known grocery commodities -> access still known


def test_a_non_commodity_leaf_drops_access_to_unknown():
    from smartchem.smiles import parse_smiles
    salt = _mol("sodium chloride")
    v = basket_cost_vector([salt, parse_smiles("CCCCCCCCO")])  # octan-1-ol: not a commodity
    assert v.access_difficulty is None       # cannot assume an unknown material is easy to obtain
    assert v.cash is None                    # the octanol leaf is unpriced -> basket cash UNKNOWN


def test_empty_basket_is_unknown_not_free():
    v = basket_cost_vector([])
    assert v.cash is None and v.access_difficulty is None  # a route buying nothing is not "free"


def test_a_cheaper_real_basket_dominates_a_pricier_one_on_the_frontier():
    salt, soda = _mol("sodium chloride"), _mol("sodium carbonate")
    baskets = [
        _Item("just-salt", basket_cost_vector([salt])),          # 52.95, grocery
        _Item("salt+soda", basket_cost_vector([salt, soda])),    # 222.30, grocery -> dominated on cash
    ]
    names = {it.name for it in pareto_frontier(baskets)}
    assert names == {"just-salt"}


def test_access_ordinal_covers_every_availability():
    """Fail-fast (the red-team's F1): every Availability member must map to an access ordinal, else a basket could
    silently drop an unmapped (possibly hardest) leaf and report a fabricated 'easy'. If a future member is added
    unmapped, this reddens; the runtime also fails-SAFE (access -> UNKNOWN) as defense-in-depth."""
    from smartchem.data.reagents import Availability
    from smartchem.experiment.affordability import _ACCESS_ORDINAL

    missing = [a.value for a in Availability if a.value not in _ACCESS_ORDINAL]
    assert not missing, f"_ACCESS_ORDINAL must map every Availability member; missing {missing}"


def test_incommensurable_units_drop_basket_cash_to_unknown(monkeypatch):
    """Backs the docstring claim (the red-team's F2): two leaves in different currency/unit cannot be summed
    honestly, so basket cash goes UNKNOWN (never apples+oranges). Unreachable with today's all-USD/metric-ton data,
    so injected via the pricing seam."""
    from smartchem.experiment import commodity_pricing
    from smartchem.experiment.stock import CostObservation

    salt, soda = _mol("sodium chloride"), _mol("sodium carbonate")
    usd_ton = CostObservation.of("10", "USD", "metric ton", "2024", "src A")
    eur_kg = CostObservation.of("10", "EUR", "kg", "2024", "src B")
    monkeypatch.setattr(commodity_pricing, "cost_observation_for",
                        lambda mol: usd_ton if mol is salt else eur_kg)
    v = basket_cost_vector([salt, soda])
    assert v.cash is None and v.currency == "" and v.unit == ""  # incommensurable -> UNKNOWN, labels blanked


def test_hard_blocker_rule_precedes_the_unknown_rule():
    """Pins the residual precedence (the red-team's nag): a CLEAN vector dominates a hard-blocked one even with NO
    known cost axes -- an unmet hard constraint is never traded for cost (section 10.4). The 'all-unknown b is
    dominated by nothing' clause holds only among vectors of EQUAL blocked-status."""
    clean_all_unknown = CostVector()
    blocked = CostVector(cash=1.0, hard_blockers=("unsafe",))
    assert dominates(clean_all_unknown, blocked)
    assert not dominates(blocked, clean_all_unknown)
    assert not dominates(CostVector(), CostVector())  # equal blocked-status all-unknowns: mutually non-dominating
