"""THERMO-UNC-01 organic widen: the frozen Burcat/ATcT seed -- the committed record that the both-sigma organic
thermo gate is CONFIRMED CLOSED, and the achievable ENTHALPY-sigma half (ATcT dfH ±) with a self-validating,
reproducible NASA-7-DERIVED entropy.  The seed's consumer is this validation test (like the CODATA seed's).
"""

import pytest

from experiments.burcat_atct_seed import (
    ACCESS_DATE,
    BURCAT_ATCT_REFS,
    FROZEN_HASH,
    GATE_STATUS,
    SOURCE,
    BurcatAtctRef,
    content_hash,
    nasa7_s298,
    report,
    validate,
)


class TestSeedIsSourcedAndFrozen:
    def test_the_frozen_set_validates(self):
        validate()  # raises if any record is hollow / non-reproducible / off its cross-check

    def test_the_content_hash_is_frozen_and_matches(self):
        assert content_hash() == FROZEN_HASH
        assert len(FROZEN_HASH) == 64  # sha256 hex

    def test_it_names_a_dated_fetchable_source(self):
        assert "Burcat" in SOURCE and "2026-09-04" in SOURCE
        assert ACCESS_DATE == "2026-09-04"

    def test_the_transcribed_atct_enthalpies_match(self):
        # the load-bearing sourced values, quoted verbatim from the ATcT comment in each Burcat record (fetched myself)
        by_key = {(r.formula, r.phase): r for r in BURCAT_ATCT_REFS}
        assert by_key[("CH4O", "gas")].dfh_kj == -200.70 and by_key[("CH4O", "gas")].dfh_unc_kj == 0.17
        assert by_key[("C2H6O", "gas")].dfh_kj == -234.56 and by_key[("C2H6O", "gas")].dfh_unc_kj == 0.2
        assert by_key[("C2H4O2", "gas")].dfh_kj == -432.216 and by_key[("C2H4O2", "gas")].dfh_unc_kj == 1.5
        assert by_key[("CH4O", "gas")].atct_ref == "ATcT C"

    def test_keys_are_distinct(self):
        keys = [r.key() for r in BURCAT_ATCT_REFS]
        assert len(keys) == len(set(keys))


class TestTheConfirmedClosedGate:
    def test_no_organic_carries_a_stated_entropy_uncertainty(self):
        # THE gate, recorded as data: a fetchable BOTH-sigma organic source does not exist, so NOT ONE organic here
        # has a sourced S uncertainty -- the entropy half stays UNKNOWN and is NOT faked (section 10.4).
        assert report()["with_stated_s_uncertainty"] == 0
        assert GATE_STATUS == "BOTH_SIGMA_ORGANIC_GATE_CONFIRMED_CLOSED"

    def test_the_record_cannot_even_hold_an_entropy_uncertainty(self):
        # the STRUCTURAL gate (red-team fold: the report count alone was a near-vacuous literal) -- BurcatAtctRef has
        # NO s-uncertainty field at all, the strongest possible enforcement that a derived S ships no fabricated ±.
        assert not hasattr(BURCAT_ATCT_REFS[0], "s_unc_j_per_k")
        assert not hasattr(BURCAT_ATCT_REFS[0], "uncertainty_s_j_per_mol_k")

    def test_the_enthalpy_half_is_real_and_sourced(self):
        # what IS achievable: every organic carries a REAL ATcT dfH uncertainty (> 0), the sourced enthalpy half.
        assert report()["with_real_dfh_uncertainty"] == len(BURCAT_ATCT_REFS)
        assert all(r.dfh_unc_kj > 0 for r in BURCAT_ATCT_REFS)


class TestTheEntropyIsDerivedAndReproducible:
    def test_stored_entropy_reproduces_from_the_committed_nasa7_polynomial(self):
        # the S is DERIVED (no both-sigma source): it must be recomputable from the record's OWN NASA-7 coefficients,
        # so the seed cannot ship a hand number -- the derivation is auditable from the seed itself.
        for r in BURCAT_ATCT_REFS:
            assert r.derived_s298() == pytest.approx(r.s_j_per_k, abs=0.02)

    def test_the_derived_entropy_crosschecks_against_nist_within_one_percent(self):
        # the two-blind-paths sanity gate: the NASA-7-derived S agrees with the independently-known NIST value to <1%,
        # so a coefficient transcription error that produced a plausible-but-wrong S would be caught.
        for r in BURCAT_ATCT_REFS:
            assert abs(r.derived_s298() - r.s_crosscheck_nist) / r.s_crosscheck_nist < 0.01

    def test_methanol_entropy_is_about_240(self):
        # a concrete pin: methanol S°(gas, 298.15) ~ 240 J/mol/K (NASA-7 -> 240.65, NIST ~239.9)
        methanol = next(r for r in BURCAT_ATCT_REFS if r.name == "methanol")
        assert methanol.derived_s298() == pytest.approx(240.65, abs=0.05)


class TestValidateIsNonVacuous:
    def _valid_coeffs(self):
        # methanol's real low-T NASA-7 coefficients (S298 -> 240.654)
        return (5.65851051e+00, -1.62983419e-02, 6.91938156e-05, -7.58372926e-08, 2.80427550e-11,
                -2.56119736e+04, -8.97330508e-01)

    def test_a_hollow_dfh_uncertainty_is_refused(self):
        # a sourced (non-reference) dfH claiming a zero uncertainty is REFUSED -- the guard fires on the record.
        s = nasa7_s298(self._valid_coeffs())
        hollow = BurcatAtctRef("fake", "XY", "gas", "", -10.0, 0.0, "ATcT A", s, self._valid_coeffs(), s)
        with pytest.raises(ValueError, match="uncertainty"):
            validate((hollow,))

    def test_a_stored_entropy_that_does_not_match_its_polynomial_is_refused(self):
        # THE derivation non-vacuity: an S that is NOT reproducible from its own NASA-7 coefficients is refused, so a
        # smuggled hand entropy cannot pass as "derived".
        bad = BurcatAtctRef("fake", "XY", "gas", "", -10.0, 0.5, "ATcT A", 999.0, self._valid_coeffs(), 999.0)
        with pytest.raises(ValueError, match="reproducible"):
            validate((bad,))

    def test_a_derivation_that_misses_the_nist_crosscheck_is_refused(self):
        # a self-consistent-but-GROSSLY-wrong S (matches its poly, but poly+crosscheck disagree by >1%) is refused: the
        # cross-check catches a coefficient set that produced a number for the WRONG species / a gross slip.  (A SUBTLE
        # single-digit coefficient slip made self-consistent can still pass this coarse gate -- documented honestly in
        # validate()'s docstring; the real transcription guarantee is the commit-time audit + FROZEN_HASH.)
        s = nasa7_s298(self._valid_coeffs())
        bad = BurcatAtctRef("fake", "XY", "gas", "", -10.0, 0.5, "ATcT A", s, self._valid_coeffs(), s * 1.5)
        with pytest.raises(ValueError, match="cross-check|>1%"):
            validate((bad,))
