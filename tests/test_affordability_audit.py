"""Audit regressions for monetary comparability and invalid affordability signals."""
from dataclasses import dataclass

import pytest

from smartchem.data.reagents import COMMODITY_REAGENTS
from smartchem.experiment.affordability import CostVector, basket_cost_vector, dominates, pareto_frontier


@dataclass(frozen=True)
class _Route:
    cost_vector: CostVector


@pytest.mark.parametrize("priced_axis", ["cash", "cash_floor"])
@pytest.mark.parametrize("other_currency", ["EUR", ""])
def test_incommensurable_cash_never_removes_a_route_from_the_frontier(priced_axis, other_currency):
    cheap = _Route(CostVector(cash=5, currency="USD", unit="kg", access_difficulty=0))
    other = _Route(CostVector(**{priced_axis: 10}, currency=other_currency, unit="kg", access_difficulty=1))
    # Even better access cannot buy away the missing FX/currency evidence.
    assert not dominates(cheap.cost_vector, other.cost_vector)
    assert not dominates(other.cost_vector, cheap.cost_vector)
    assert pareto_frontier([cheap, other]) == [cheap, other]
    # Positive control: a compatible currency retains both exact- and interval-cash dominance.
    compatible = CostVector(**{priced_axis: 10}, currency="USD", unit="kg", access_difficulty=1)
    assert dominates(cheap.cost_vector, compatible)


def test_hard_constraints_still_precede_currency_comparability():
    available = CostVector(cash=100, currency="USD", unit="kg")
    unavailable = CostVector(cash=1, currency="EUR", unit="kg", hard_blockers=("required equipment absent",))
    assert dominates(available, unavailable)
    assert not dominates(unavailable, available)


@pytest.mark.parametrize("axis", [
    "cash", "cash_floor", "access_difficulty", "evidence_tier_rank", "new_equipment",
    "material_quantity", "energy", "labor_time", "preprocessing", "analytical", "waste_disposal",
])
@pytest.mark.parametrize("invalid", [-1, float("inf"), float("-inf")])
def test_invalid_costs_cannot_create_spurious_pareto_winners(axis, invalid):
    with pytest.raises(ValueError, match=axis):
        CostVector(**{axis: invalid})


@pytest.mark.parametrize("axis", ["access_difficulty", "evidence_tier_rank"])
def test_ordinal_axes_require_whole_ranks_without_an_invented_upper_limit(axis):
    with pytest.raises(ValueError, match="integral"):
        CostVector(**{axis: 1.5})
    assert getattr(CostVector(**{axis: 5}), axis) == 5
    # Existing numeric payloads can spell integral ranks as floats.
    assert getattr(CostVector(**{axis: 1.0}), axis) == 1


@pytest.mark.parametrize("axis", ["cash", "cash_floor"])
def test_zero_cash_is_distinct_from_an_unknown_cost(axis):
    vector = CostVector(**{axis: 0})
    assert vector.has_cost_signal()
    assert getattr(vector, axis) == 0
    assert not CostVector().has_cost_signal()


@pytest.mark.parametrize("label", ["currency", "unit", "region"])
def test_cost_labels_are_strings(label):
    with pytest.raises(TypeError, match=label):
        CostVector(**{label: None})


def test_whitespace_is_not_a_hard_constraint_reason():
    with pytest.raises(TypeError, match="reason"):
        CostVector(hard_blockers=("  ",))


@pytest.mark.parametrize("moles", [float("inf"), float("-inf"), float("nan"), 10 ** 400])
def test_nonfinite_weighted_quantities_keep_the_documented_per_unit_fallback(moles):
    salt = next(c.molecule for c in COMMODITY_REAGENTS if c.name == "sodium chloride")
    assert basket_cost_vector([salt], weighted_cash_leaves=[(salt, moles)]) == basket_cost_vector([salt])


def test_unrepresentable_integer_cash_cannot_escape_as_an_overflow():
    with pytest.raises(ValueError, match="finite"):
        CostVector(cash=10 ** 400)
