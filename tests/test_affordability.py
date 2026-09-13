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
    Disposition,
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


# ---- DISPOSITION-01: the distinct disposition channel un-flattens the two blocker KINDS ----

def test_the_disposition_tier_is_the_worst_over_the_two_channels():
    assert CostVector().disposition is Disposition.CLEAN
    assert CostVector(hard_blockers=("Pd",)).disposition is Disposition.REAL_BUT_HARD
    assert CostVector(fiction_blockers=("fake",)).disposition is Disposition.NOT_A_REACTION
    # a route that is BOTH real-but-hard AND a fiction is a fiction (one non-reaction step voids the whole route).
    assert CostVector(hard_blockers=("Pd",), fiction_blockers=("fake",)).disposition is Disposition.NOT_A_REACTION


def test_real_but_hard_strictly_outranks_not_a_reaction_at_any_price():
    # THE win: a genuine reaction merely needing an unobtainable catalyst (REAL_BUT_HARD) beats a formula-balanced
    # non-reaction (NOT_A_REACTION) even when the fiction is CHEAPER -- the partial order the shared tuple flattened.
    real_but_hard = CostVector(cash=1000.0, hard_blockers=("catalyst not kitchen-obtainable: Pd [industrial]",))
    not_a_reaction = CostVector(cash=1.0, fiction_blockers=("unrecognized reaction type: no attested class",))
    assert dominates(real_but_hard, not_a_reaction)          # real-but-hard wins DESPITE being 1000x dearer
    assert not dominates(not_a_reaction, real_but_hard)      # the cheap fiction never dominates a real option
    # and a clean route still beats BOTH tiers at any price (the original G6 rule, preserved)
    clean_dear = CostVector(cash=1e6)
    assert dominates(clean_dear, real_but_hard) and dominates(clean_dear, not_a_reaction)
    assert not dominates(real_but_hard, clean_dear) and not dominates(not_a_reaction, clean_dear)


def test_the_frontier_drops_a_fiction_when_a_real_but_hard_route_exists():
    # a Pareto frontier with all three tiers keeps only the best-disposed among comparable routes: the cheap fiction
    # is dominated OFF by the dearer real-but-hard route (and both by the clean one) -- observable frontier movement.
    items = [
        _Item("clean", CostVector(cash=50.0)),
        _Item("real-but-hard", CostVector(cash=5.0, hard_blockers=("needs a fume hood",))),
        _Item("fiction-cheap", CostVector(cash=0.01, fiction_blockers=("unrecognized reaction type",))),
    ]
    assert {it.name for it in pareto_frontier(items)} == {"clean"}
    # remove the clean route: the real-but-hard survives, the cheaper fiction is still dropped (tier beats price).
    assert {it.name for it in pareto_frontier(items[1:])} == {"real-but-hard"}


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
    axes = ["access_difficulty", "evidence_tier_rank", "new_equipment", "material_quantity"]

    def rand_vec() -> CostVector:
        kw: dict = {a: float(rng.randint(0, 3)) for a in axes if rng.random() < 0.5}
        # the cash axis is INTERVAL-valued (COST-VEC-01-coupled): exercise all three states -- a known cash, an honest
        # floor [F, +inf), and entirely UNKNOWN -- so the necessary-dominance interval logic is under the proof too.
        r = rng.random()
        if r < 0.4:
            kw["cash"] = float(rng.randint(0, 3))
        elif r < 0.7:
            kw["cash_floor"] = float(rng.randint(0, 3))
        # exercise ALL THREE disposition tiers (DISPOSITION-01) -- clean, real-but-hard, not-a-reaction, and the
        # both-blocked case -- so the 3-valued disposition rule is under the strict-partial-order proof too, not just
        # the old 2-valued clean/blocked split.
        if rng.random() < 0.3:
            kw["hard_blockers"] = ("blk",)
        if rng.random() < 0.3:
            kw["fiction_blockers"] = ("fic",)
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


def test_a_partially_priced_basket_reports_an_honest_cash_floor_not_bare_unknown():
    # COST-VEC-01-coupled: the exact total is UNKNOWN (ethanol unpriced) but the priced leaf proves a LOWER BOUND --
    # you need at least the salt, so the basket costs AT LEAST its price.  Report that honest floor, never a fabricated
    # total and never a blind UNKNOWN that throws the real signal away.
    salt, ethanol = _mol("sodium chloride"), _mol("ethanol")  # ethanol is a commodity but unpriced (2a)
    v = basket_cost_vector([salt, ethanol])
    assert v.cash is None                    # exact total still UNKNOWN -- never a fabricated full basket cost
    assert v.cash_floor == pytest.approx(52.95)   # the honest lower bound: at least the priced salt
    assert v.currency == "USD" and v.unit == "metric ton"  # the floor is labelled in its currency
    assert v.access_difficulty == 0          # both are known grocery commodities -> access still known


def test_a_non_commodity_leaf_drops_access_to_unknown_but_keeps_the_priced_floor():
    from smartchem.smiles import parse_smiles
    salt = _mol("sodium chloride")
    v = basket_cost_vector([salt, parse_smiles("CCCCCCCCO")])  # octan-1-ol: not a commodity
    assert v.access_difficulty is None       # cannot assume an unknown material is easy to obtain
    assert v.cash is None                    # the octanol leaf is unpriced -> exact basket cash UNKNOWN
    assert v.cash_floor == pytest.approx(52.95)   # but the priced salt still floors the basket cost honestly


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
    # incommensurable -> neither an exact cash NOR a floor (you cannot sum across currencies honestly), labels blanked
    assert v.cash is None and v.cash_floor is None and v.currency == "" and v.unit == ""


def test_hard_blocker_rule_precedes_the_unknown_rule():
    """Pins the residual precedence (the red-team's nag): a CLEAN vector dominates a hard-blocked one even with NO
    known cost axes -- an unmet hard constraint is never traded for cost (section 10.4). The 'all-unknown b is
    dominated by nothing' clause holds only among vectors of EQUAL blocked-status."""
    clean_all_unknown = CostVector()
    blocked = CostVector(cash=1.0, hard_blockers=("unsafe",))
    assert dominates(clean_all_unknown, blocked)
    assert not dominates(blocked, clean_all_unknown)
    assert not dominates(CostVector(), CostVector())  # equal blocked-status all-unknowns: mutually non-dominating


# ---- COST-VEC-01-coupled: the honest cash floor (interval-valued cash axis) ----

def test_cash_floor_and_cash_are_mutually_exclusive():
    # a KNOWN cash carries no separate floor -- the two together is a contradiction, refused.
    with pytest.raises(ValueError, match="mutually exclusive"):
        CostVector(cash=10.0, cash_floor=5.0)


def test_cash_floor_rejects_a_negative_lower_bound():
    # a floor is a lower bound on a sum of non-negative prices; a negative "floor" is meaningless, refused.
    with pytest.raises(ValueError, match="cannot be negative"):
        CostVector(cash_floor=-1.0)


def test_a_known_cash_below_a_floor_dominates_the_floored_vector():
    # necessary dominance on the cash interval: known 5 vs floor [10, +inf) -> 5 < 10 <= true, so the known-cheap
    # vector is necessarily cheaper and dominates.  This is the whole point of the floor entering dominance.
    known_cheap = CostVector(cash=5.0, access_difficulty=0)
    floored_dear = CostVector(cash_floor=10.0, access_difficulty=0)
    assert dominates(known_cheap, floored_dear)
    assert not dominates(floored_dear, known_cheap)


def test_a_floor_cannot_dominate_a_known_cost_or_another_floor():
    # a floor's interval is [F, +inf): its MAX possible cost is unbounded, so it can never be "necessarily no worse"
    # -- a floor never dominates on cash (only ever gets dominated by a known cost below it).
    floor_low = CostVector(cash_floor=1.0, access_difficulty=0)
    known_high = CostVector(cash=100.0, access_difficulty=0)
    assert not dominates(floor_low, known_high)   # true cost could exceed 100 -> cannot claim no-worse
    floor_high = CostVector(cash_floor=50.0, access_difficulty=0)
    assert not dominates(floor_low, floor_high)   # two floors: both upper-unbounded -> incomparable on cash
    assert not dominates(floor_high, floor_low)


def test_a_floor_only_vector_carries_frontier_signal():
    # a route whose cash is only bounded BELOW still carries real affordability signal -- it must NOT be gated off as
    # a blank vector (the service signal-gate uses has_cost_signal, which counts a floor).
    floor_only = CostVector(cash_floor=25.0)
    assert floor_only.has_cost_signal()
    assert not floor_only.known_axes()            # a floor is not a "known" point axis...
    assert floor_only.cash_floor == 25.0          # ...but it is real signal
    assert not CostVector().has_cost_signal()     # a truly blank vector carries none


# ---- COST-VEC-01 quantity/stoich axis: material_quantity (mol external per mol product) ----

def test_basket_cost_vector_accepts_an_optional_material_quantity():
    # additive keyword: existing positional callers are unchanged (material_quantity defaults None); when supplied it
    # populates the material_quantity axis (the route's total external-leaf moles per mol product).
    v = basket_cost_vector([_mol("sodium chloride")], material_quantity=2.5)
    assert v.material_quantity == 2.5
    assert basket_cost_vector([_mol("sodium chloride")]).material_quantity is None  # default: UNKNOWN


def test_material_quantity_enters_dominance_as_a_minimized_axis():
    # the quantity axis is a real §10.4 minimized axis: a route needing LESS external material (same everything else)
    # dominates a heavier one -- the discrimination the per-unit cash axis is blind to.
    lean = CostVector(access_difficulty=2, material_quantity=2.0)
    heavy = CostVector(access_difficulty=2, material_quantity=3.0)
    assert dominates(lean, heavy)
    assert not dominates(heavy, lean)
    # UNKNOWN material_quantity stays incomparable on that axis (never over-ranked)
    unknown = CostVector(access_difficulty=2)
    assert not dominates(lean, unknown) and not dominates(unknown, lean)  # tie on access, material incomparable


# ---- TERM-MAT: quantity-weighted cash floor (per-leaf moles x price_per_mol) ----

def test_weighted_cash_leaves_gives_a_quantity_weighted_cash_floor():
    # the payoff of the molar-mass + price-unit layer: 2 mol of NaCl at the USGS 52.95 $/t price, weighted by the
    # sourced molar mass 58.44 g/mol -> a real per-mol-product material cash, where the per-unit axis only knew
    # "one metric ton = $52.95".  It is ALWAYS a floor (100%-yield x UNKNOWN-assay), labelled per mol of product.
    salt = _mol("sodium chloride")
    v = basket_cost_vector([salt], weighted_cash_leaves=[(salt, 2.0)])
    expected = 2.0 * (52.95 / 1_000_000.0) * 58.44   # moles x price_per_gram x molar_mass
    assert v.cash is None                              # a weighted floor is never an exact total
    assert v.cash_floor == pytest.approx(expected, rel=1e-3)
    assert v.unit == "mol product" and v.currency == "USD"


def test_weighted_cash_default_is_byte_identical_to_the_per_unit_path():
    # the gate: without weighted_cash_leaves the per-unit behaviour is UNCHANGED (exact cash from the package price) --
    # zero churn for every existing caller.
    salt = _mol("sodium chloride")
    assert basket_cost_vector([salt]).cash == pytest.approx(52.95)
    assert basket_cost_vector([salt]).unit == "metric ton"


def test_weighted_cash_is_a_partial_floor_when_a_leaf_is_unpriced():
    # a route needing an unpriced leaf (ethanol) alongside a priced one contributes only the priced leaf's weighted
    # cost -- a PARTIAL floor (you need at least that much), never a fabricated total for the unpriced remainder.
    salt, ethanol = _mol("sodium chloride"), _mol("ethanol")  # ethanol: a commodity, but unpriced (no 2a price)
    v = basket_cost_vector([salt, ethanol], weighted_cash_leaves=[(salt, 1.0), (ethanol, 5.0)])
    expected = 1.0 * (52.95 / 1_000_000.0) * 58.44
    assert v.cash is None
    assert v.cash_floor == pytest.approx(expected, rel=1e-3)  # only the salt's weighted cost enters the floor
    assert v.unit == "mol product"


def test_weighted_cash_falls_back_to_per_unit_when_no_leaf_is_convertible():
    # if NO supplied leaf is priced-and-mass-convertible, the weighted floor is UNKNOWN and the per-unit path STANDS
    # (never silently blanks the real per-unit signal).  Here the weighted leaves are all unpriced -> fall back to the
    # exact per-unit cash of the priced commodity_molecules.
    salt, ethanol = _mol("sodium chloride"), _mol("ethanol")
    v = basket_cost_vector([salt], weighted_cash_leaves=[(ethanol, 3.0)])
    assert v.cash == pytest.approx(52.95)   # per-unit path preserved
    assert v.cash_floor is None
    assert v.unit == "metric ton"


def test_cash_is_incomparable_across_denominations():
    # red-team fold (Finding 1): a per-unit package cash ("metric ton") and a quantity-weighted floor ("mol product")
    # are DIFFERENT denominations; dominance must NOT compare them numerically (it used to let $5/ton "dominate"
    # $10/mol).  The `unit` field is load-bearing on the cash axis: a different denomination is incomparable.
    per_ton = CostVector(cash=5.0, unit="metric ton")
    per_mol = CostVector(cash_floor=10.0, unit="mol product")
    assert not dominates(per_ton, per_mol) and not dominates(per_mol, per_ton)  # incomparable, both ways
    # NON-VACUITY: the guard does NOT over-block -- SAME-denomination cash still compares (a cheaper ton dominates a
    # dearer ton), so the fix isolates the denomination mismatch and nothing else.
    cheap_ton = CostVector(cash=5.0, unit="metric ton")
    dear_ton = CostVector(cash=9.0, unit="metric ton")
    assert dominates(cheap_ton, dear_ton) and not dominates(dear_ton, cheap_ton)


def test_weighted_cash_negative_moles_is_skipped_not_a_crash():
    # red-team fold (Finding 4): a negative/NaN moles is not an honest requirement (never happens on the wire -- dag
    # requirements are net>0) but must not crash the vector build (a negative floor is rejected by CostVector); it is
    # skipped, so an all-negative weighted set falls back to the per-unit path rather than raising.
    salt = _mol("sodium chloride")
    v = basket_cost_vector([salt], weighted_cash_leaves=[(salt, -5.0)])
    assert v.cash == pytest.approx(52.95) and v.cash_floor is None  # negative leaf skipped -> per-unit fallback
