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
        assert hazards_for("C3H8") is None      # propane: not in the hazard table -> a loud gap
        assert hazards_for("C99H1") is None     # nonsense: a loud gap, never "safe"


class TestCommonSpeciesAreNowCovered:
    """The widening: common decomposition products / inventory carry sourced records, so those
    edges read DOCUMENTED rather than the loud HAZARDS_UNASSESSED. Keys are canonical Formula reprs
    (ammonia is 'H3N', not 'NH3' -- alphabetical element order)."""

    def test_the_common_species_have_records(self):
        expected = {
            "CO": "carbon monoxide", "CO2": "carbon dioxide", "CH4": "methane",
            "H3N": "ammonia", "H2O2": "hydrogen peroxide", "CH4O": "methanol",
            "CH2O": "formaldehyde", "CH2O2": "formic acid", "H2O": "water",
        }
        for formula, name in expected.items():
            rec = hazards_for(formula)
            assert rec is not None and rec.name == name

    def test_carbon_monoxide_warns_toxic_and_flammable(self):
        co = hazards_for("CO")
        assert "H220" in co.ghs_codes and "H331" in co.ghs_codes   # flammable + toxic-by-inhalation
        assert "INHALED" in co.summary.upper()

    def test_formaldehyde_is_flagged_carcinogen(self):
        f = hazards_for("CH2O")
        assert "H350" in f.ghs_codes                                # ECHA Carc. 1B
        assert "IARC" in f.regulatory or "carcinogen" in f.regulatory.lower()

    def test_water_is_assessed_benign_not_unassessed(self):
        # water carries a POSITIVE record with no GHS codes -- assessed and benign, which is a
        # different thing from an absent record (the loud UNKNOWN a chemist must not read as "safe").
        w = hazards_for("H2O")
        assert w is not None and w.ghs_codes == ()
        assert "benign" in w.summary.lower()


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

    def test_records_are_keyed_by_unique_name_isomers_may_share_a_formula(self):
        # isomer-keying: a formula MAY carry several records (ethanol and dimethyl ether both under
        # C2H6O), but every record's NAME is unique -- that is what makes structure -> name -> record
        # unambiguous. hazards_for on a multi-isomer formula returns None (ambiguous), by design.
        names = [r.name for r in HAZARD_REFS]
        assert len(names) == len(set(names))
        assert hazards_for("C2H6O") is None                       # ambiguous formula -> no single answer
        assert {r.name for r in HAZARD_REFS if r.formula == "C2H6O"} == {"ethanol", "dimethyl ether"}

    def test_digestible(self):
        assert len(hazards_for("C2H2O").digest) == 64
