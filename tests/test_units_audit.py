"""Nonfinite input and finite-input overflow must never become usable quantities."""
from types import SimpleNamespace

import pytest

from smartchem.experiment.units import (
    grams_to_moles, molar_mass, moles_to_grams, price_per_gram, price_per_mol,
)


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan"), True, 10**1000])
def test_nonfinite_or_nonrepresentable_mass_amount_and_composition_are_unknown(value):
    assert grams_to_moles(value, {"H": 2, "O": 1}) is None
    assert moles_to_grams(value, {"H": 2, "O": 1}) is None
    assert molar_mass({"H": value}) is None


@pytest.mark.parametrize("value", ["inf", "-inf", "NaN", "1e999", True, 10**1000])
def test_nonfinite_price_is_unknown(value):
    observation = SimpleNamespace(amount=value, unit="g", currency="USD")
    assert price_per_gram(observation) is None
    assert price_per_mol(observation, {"H": 2, "O": 1}) is None


def test_finite_inputs_that_overflow_conversion_are_unknown():
    assert molar_mass({"C": 1e308}) is None
    assert moles_to_grams(1e308, {"H": 2, "O": 1}) is None
    assert price_per_gram(SimpleNamespace(amount="1e308", unit="ug", currency="USD")) is None
    assert price_per_mol(
        SimpleNamespace(amount="1e308", unit="g", currency="USD"), {"H": 2, "O": 1}
    ) is None


def test_zero_quantity_and_price_remain_valid():
    assert grams_to_moles(0, {"H": 2, "O": 1}) == 0
    assert moles_to_grams(0, {"H": 2, "O": 1}) == 0
    assert price_per_gram(SimpleNamespace(amount="0", unit="kg", currency="USD")) == (0, "USD")
