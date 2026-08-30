"""Decompiler-support thermochemistry: tiered, convention-safe, and honest about its gaps.

These tests are the anti-drift pins the reference module's history demands: the exact sourced numbers
are asserted (so a later edit cannot silently move a value the way the ethanol near-miss did), and the
convention filter is shown to BITE -- paracetamol's 298 K value is stored for display but is excluded
from every 0 K balance, so it can never silently corrupt one.
"""

import pytest

from smartchem.contracts import EvidenceStatus
from smartchem.data.decompiler_thermo import (
    DECOMPILER_THERMO,
    THERMO_GAPS,
    ThermoRef,
    records_for,
    zero_k_records,
)
from smartchem.decompiler import Formula


class TestUsableValues:
    def test_ketene_and_acetic_acid_are_usable_at_0k(self):
        ket = zero_k_records("C2H2O")
        aa = zero_k_records("C2H4O2")
        assert len(ket) == 1 and ket[0].dfh_kj == -44.51 and ket[0].status is EvidenceStatus.ESTABLISHED
        assert len(aa) == 1 and aa[0].dfh_kj == -418.10 and aa[0].status is EvidenceStatus.ESTABLISHED

    def test_established_values_name_their_second_source(self):
        for r in DECOMPILER_THERMO:
            if r.status is EvidenceStatus.ESTABLISHED:
                assert r.second_source


class TestConventionFilterBites:
    def test_paracetamol_is_stored_for_display_but_excluded_from_the_0k_balance(self):
        # present at 298 K...
        display = records_for("C8H9NO2")
        assert len(display) == 1 and display[0].temperature_k == 298 and display[0].dfh_kj == -280.5
        # ...but NOT usable in a 0 K balance -- so its edges stay ENERGETICS_UNKNOWN, honestly
        assert zero_k_records("C8H9NO2") == ()


class TestDocumentedGaps:
    def test_4_aminophenol_and_acetic_anhydride_are_documented_not_stored(self):
        # no usable value...
        assert zero_k_records("C6H7NO") == ()
        assert zero_k_records("C4H6O3") == ()
        assert records_for("C6H7NO") == ()
        # ...but the reason is recorded, so the UNKNOWN is loud, not an empty absence
        assert "DISAGREE" in THERMO_GAPS["C6H7NO"]
        assert "liquid" in THERMO_GAPS["C4H6O3"]


class TestKeysAndGuards:
    def test_keys_are_canonical_formula_reprs(self):
        for r in DECOMPILER_THERMO:
            assert repr(Formula.parse(r.formula)) == r.formula
        for key in THERMO_GAPS:
            assert repr(Formula.parse(key)) == key

    def test_established_without_a_second_source_is_rejected(self):
        with pytest.raises(ValueError):
            ThermoRef("X2", "x", -1.0, 0, EvidenceStatus.ESTABLISHED, "src", second_source="")

    def test_unsupported_status_is_rejected(self):
        with pytest.raises(ValueError):
            ThermoRef("X2", "x", -1.0, 0, EvidenceStatus.UNSUPPORTED, "src")

    def test_a_value_must_name_its_source(self):
        with pytest.raises(ValueError):
            ThermoRef("X2", "x", -1.0, 0, EvidenceStatus.EXPERIMENTAL, "")

    def test_an_unrecognised_temperature_convention_is_rejected(self):
        with pytest.raises(ValueError):
            ThermoRef("X2", "x", -1.0, 500, EvidenceStatus.EXPERIMENTAL, "src")

    def test_digestible(self):
        assert len(zero_k_records("C2H2O")[0].digest) == 64
