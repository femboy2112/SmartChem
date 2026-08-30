"""Sourced qualitative hazard reference: inform-never-neuter, UNKNOWN-is-not-safe.

The tests pin two things that would silently rot: that each record's key is exactly the string a
decompiler Formula reprs to (a key typo would make a real hazard read as UNKNOWN), and that the
safety-critical facts the sourcing established are actually present in the record a chemist reads.
"""

import pytest

from smartchem.contracts import EvidenceStatus
from smartchem.data.hazards import HAZARD_REFS, HazardRef, hazards_for
from smartchem.decompiler import Formula


class TestKeysMatchFormulaRepr:
    def test_every_record_key_is_a_canonical_formula_repr(self):
        # if a key did not equal repr(Formula.parse(key)) the review layer's lookup would miss it
        for ref in HAZARD_REFS:
            assert repr(Formula.parse(ref.formula)) == ref.formula

    def test_lookup_hits_the_litmus_species(self):
        assert hazards_for("C2H2O").name == "ketene"
        assert hazards_for("C6H7NO").name == "4-aminophenol"
        assert hazards_for("C8H9NO2").name == "paracetamol"
        assert hazards_for("C4H6O3").name == "acetic anhydride"


class TestUnknownIsNotSafe:
    def test_a_miss_returns_none_not_an_empty_clearance(self):
        assert hazards_for("H2O") is None      # water: not in the hazard table
        assert hazards_for("C99H1") is None     # nonsense: a loud gap, never "safe"


class TestSafetyCriticalFactsArePresent:
    def test_ketene_is_flagged_fatal_and_reactive(self):
        k = hazards_for("C2H2O")
        assert "H330" in k.ghs_codes                       # fatal if inhaled
        assert any("water" in r for r in k.reactivity)     # violent water reaction
        assert any("explos" in r for r in k.reactivity)    # explosive polymerisation / peroxide
        assert "0.5 ppm" in k.exposure                     # the OSHA PEL a chemist needs

    def test_4_aminophenol_carries_its_regulatory_status(self):
        a = hazards_for("C6H7NO")
        assert "H341" in a.ghs_codes                        # suspected mutagen
        assert "227" in a.regulatory                        # USP <227> control
        assert "nephrotox" in a.regulatory or "nephrotox" in a.summary

    def test_acetic_anhydride_warns_of_the_water_reaction(self):
        aa = hazards_for("C4H6O3")
        assert "VIOLENTLY WITH WATER" in aa.summary.upper()

    def test_every_record_names_its_source(self):
        for ref in HAZARD_REFS:
            assert ref.provenance


class TestRecordGuards:
    def test_a_hazard_record_cannot_be_unsupported(self):
        with pytest.raises(ValueError):
            HazardRef("X", "x", ("H200",), "s", (), "", "", "src", EvidenceStatus.UNSUPPORTED)

    def test_a_hazard_record_must_name_a_source(self):
        with pytest.raises(ValueError):
            HazardRef("X", "x", ("H200",), "s", (), "", "", "")

    def test_no_two_records_share_a_formula(self):
        formulas = [r.formula for r in HAZARD_REFS]
        assert len(formulas) == len(set(formulas))

    def test_digestible(self):
        assert len(hazards_for("C2H2O").digest) == 64
