"""TERM-MAT-01: the molar-mass + price-unit-conversion layer -- KNOWN-physics conversions that fail to UNKNOWN
(never a fabricated factor) whenever the denominator is not a mass unit or the composition has no molar mass."""

import pytest

from smartchem.experiment.stock import CostObservation
from smartchem.experiment.units import (
    MASS_UNIT_GRAMS,
    grams_per_unit,
    grams_to_moles,
    molar_mass,
    moles_to_grams,
    price_per_gram,
    price_per_mol,
)


class TestMolarMass:
    def test_water_from_sourced_atomic_weights(self):
        # 2*1.0080 + 15.999 = 18.015 (IUPAC/CIAAW abridged, via smartchem.data.periodic_table)
        assert molar_mass({"H": 2, "O": 1}) == pytest.approx(18.015, abs=1e-3)

    def test_sodium_chloride(self):
        # 22.990 + 35.45 = 58.44
        assert molar_mass({"Na": 1, "Cl": 1}) == pytest.approx(58.44, abs=1e-2)

    def test_accepts_pairs_or_mapping_identically(self):
        assert molar_mass([("C", 2), ("H", 6), ("O", 1)]) == molar_mass({"C": 2, "H": 6, "O": 1})

    def test_none_for_a_mass_number_only_element(self):
        # Tc (technetium) has NO standard atomic weight -- only a most-stable-isotope mass number -- so a composition
        # containing it has no honest molar mass (UNKNOWN), never the mass number masquerading as a molar mass.
        assert molar_mass({"Tc": 1}) is None
        assert molar_mass({"C": 1, "Tc": 1}) is None  # one tainted element taints the whole composition

    def test_none_for_unknown_symbol_or_empty_or_bad_count(self):
        assert molar_mass({"Xx": 1}) is None       # not an element
        assert molar_mass({}) is None              # no atoms
        assert molar_mass({"C": 0}) is None        # non-positive count is not an honest composition
        assert molar_mass({"C": -1}) is None


class TestMassUnitConversion:
    def test_definitional_factors(self):
        assert grams_per_unit("metric ton") == 1_000_000.0
        assert grams_per_unit("kg") == 1_000.0
        assert grams_per_unit("g") == 1.0
        assert grams_per_unit("lb") == 453.59237          # 1959 international pound, exact
        assert grams_per_unit("oz") == pytest.approx(453.59237 / 16)

    def test_case_and_whitespace_insensitive(self):
        assert grams_per_unit("  Metric Ton ") == 1_000_000.0
        assert grams_per_unit("KG") == 1_000.0

    def test_non_mass_units_are_unknown_not_guessed(self):
        for u in ("L", "mL", "each", "unit", "piece", "gallon", ""):
            assert grams_per_unit(u) is None, u

    def test_ambiguous_mt_is_deliberately_absent(self):
        # "mt" is ambiguous (metric ton vs megatonne) -> UNKNOWN rather than a coin-flip factor.
        assert grams_per_unit("mt") is None
        assert "mt" not in MASS_UNIT_GRAMS

    def test_non_string_is_unknown(self):
        assert grams_per_unit(None) is None
        assert grams_per_unit(1000) is None


def _obs(amount, unit, currency="USD"):
    return CostObservation.of(str(amount), currency, unit, "2024", "test source")


class TestPriceConversion:
    def test_price_per_gram_from_a_per_ton_price(self):
        pg = price_per_gram(_obs(52.95, "metric ton"))
        assert pg is not None
        value, currency = pg
        assert value == pytest.approx(52.95 / 1_000_000.0)
        assert currency == "USD"

    def test_price_per_gram_unknown_for_a_non_mass_denominator(self):
        assert price_per_gram(_obs(3.0, "L")) is None
        assert price_per_gram(_obs(3.0, "each")) is None

    def test_price_per_gram_unknown_for_a_bad_amount(self):
        # a CostObservation validates its amount numeric, so forge a duck-typed observation with a junk amount
        class _Junk:
            amount, unit, currency = "not-a-number", "kg", "USD"
        assert price_per_gram(_Junk()) is None

    def test_price_per_mol_multiplies_by_molar_mass(self):
        # 52.95 $/t of NaCl -> per gram -> per mol (× 58.44 g/mol)
        pm = price_per_mol(_obs(52.95, "metric ton"), {"Na": 1, "Cl": 1})
        assert pm is not None
        value, currency = pm
        assert value == pytest.approx(52.95 / 1_000_000.0 * 58.44, rel=1e-3)
        assert currency == "USD"

    def test_price_per_mol_unknown_if_either_half_unknown(self):
        assert price_per_mol(_obs(52.95, "L"), {"Na": 1, "Cl": 1}) is None       # denominator not mass
        assert price_per_mol(_obs(52.95, "metric ton"), {"Tc": 1}) is None        # no molar mass


class TestGramMoleBridge:
    def test_round_trip(self):
        water = {"H": 2, "O": 1}
        moles = grams_to_moles(36.03, water)          # ~2 mol of water (2 × 18.015)
        assert moles == pytest.approx(2.0, rel=1e-3)
        assert moles_to_grams(moles, water) == pytest.approx(36.03, rel=1e-3)

    def test_unknown_molar_mass_blocks_the_bridge(self):
        assert grams_to_moles(10.0, {"Tc": 1}) is None
        assert moles_to_grams(10.0, {"Tc": 1}) is None

    def test_negative_or_nan_input_is_unknown(self):
        assert grams_to_moles(-1.0, {"H": 2, "O": 1}) is None
        assert moles_to_grams(float("nan"), {"H": 2, "O": 1}) is None
