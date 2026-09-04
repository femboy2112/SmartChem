"""THERMO-UNC-01: the committed CODATA Key Values seed -- a dated, cited, frozen reference dataset with REAL
uncertainties, and the non-vacuous uncertainty discipline that lifts the old BLOCKED wall honestly.
"""

import pytest

from experiments.thermo_codata_seed import (
    ACCESS_DATE,
    CODATA_KEY_VALUES,
    FROZEN_HASH,
    SOURCE,
    CodataRef,
    content_hash,
    report,
    validate,
)


class TestCodataSeedIsSourcedAndFrozen:
    def test_the_frozen_set_validates(self):
        validate()  # raises if any record is hollow / non-finite / duplicate-keyed

    def test_the_content_hash_is_frozen_and_matches(self):
        # tamper-evident: the committed FROZEN_HASH must equal the live content hash of the values.
        assert content_hash() == FROZEN_HASH
        assert len(FROZEN_HASH) == 64  # sha256 hex

    def test_it_names_a_dated_source(self):
        assert "1989" in SOURCE and "CODATA" in SOURCE
        assert ACCESS_DATE == "2026-09-04"

    def test_the_transcribed_values_match_textbook_codata(self):
        # a transcription check pinning the load-bearing numbers (values a chemist knows by heart).
        by_key = {(r.formula, r.phase): r for r in CODATA_KEY_VALUES}
        assert by_key[("H2O", "liquid")].dfh_kj == -285.830 and by_key[("H2O", "liquid")].dfh_unc_kj == 0.040
        assert by_key[("CO2", "gas")].dfh_kj == -393.51 and by_key[("CO2", "gas")].dfh_unc_kj == 0.13
        assert by_key[("CO", "gas")].dfh_kj == -110.53
        assert by_key[("NH3", "gas")].dfh_kj == -45.94

    def test_keys_are_distinct(self):
        keys = [r.key() for r in CODATA_KEY_VALUES]
        assert len(keys) == len(set(keys))  # single-valued per (formula, phase)


class TestNonVacuousUncertaintyDiscipline:
    def test_a_reference_state_zero_is_legitimate_not_hollow(self):
        # O2/H2/N2/graphite: dfH = 0 EXACTLY by convention (unc 0), but S still carries a REAL +/- -- accepted.
        refs = [r for r in CODATA_KEY_VALUES if r.is_reference_state]
        assert refs, "the seed must contain reference-state elements"
        for r in refs:
            assert r.dfh_kj == 0.0 and r.dfh_unc_kj == 0.0 and r.s_unc_j_per_k > 0
        validate(tuple(refs))  # a set of pure reference states still validates (their zeros are convention, not hollow)

    def test_a_hollow_uncertainty_on_a_non_reference_value_is_refused(self):
        # THE non-vacuity: a sourced (non-reference) dfH claiming precision it does not have -- a zero uncertainty --
        # is REFUSED. The guard fires on the hollow RECORD, not merely on an empty set.
        hollow = CodataRef("fake", "XY", "gas", "", -10.0, 0.0, 100.0, 1.0, False)
        with pytest.raises(ValueError, match="real uncertainty|hollow"):
            validate((hollow,))

    def test_a_zero_entropy_uncertainty_is_refused_even_for_a_reference_state(self):
        # every species (elements included) has a REAL entropy uncertainty; a hollow S +/- is refused.
        bad = CodataRef("fake", "XY", "gas", "", 0.0, 0.0, 100.0, 0.0, True)
        with pytest.raises(ValueError, match="entropy|positive|real"):
            validate((bad,))

    def test_ch4_is_honestly_absent_not_invented(self):
        # CH4 is NOT a CODATA key species; it must NOT be silently fabricated into the seed.
        assert "CH4" not in {r.formula for r in CODATA_KEY_VALUES}


def test_report_is_self_consistent():
    r = report()
    assert r["hash_matches"] is True
    assert r["reference_states"] == 4  # O2, H2, N2, C-graphite
    assert r["with_real_dfh_uncertainty"] >= 3  # H2O(l), H2O(g), CO, CO2, NH3 all carry a real +/-
