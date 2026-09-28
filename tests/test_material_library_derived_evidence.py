"""Round-IV data-validation: the DERIVED_WITH_ERROR intervals must EQUAL their own stated derivation.

Before this seam, "derived" was a string in the provenance and nothing checked the arithmetic. These
tests validate the CALCULATION -- each evidence record reconstructs its interval from its raw inputs -- and
pin the two arithmetic bugs the Round-IV numeric audit found: the g-per-100g-water figure used directly as
a mass-fraction-of-solution (NaCl, isoamyl dilute), and a decorative +-0.5% band relabelled honestly as
ASSUMED (NaHCO3). The old NaCl ``[0.23, 0.27]`` must FAIL the reconstruction; the fix must PASS.
"""
from fractions import Fraction

import pytest

from smartchem.data import material_library as ml
from smartchem.data.derived_evidence import (
    DerivationMethod,
    DerivedIntervalEvidence,
    IntervalUnit,
    complement_band,
    solution_fraction_from_solubility,
)
from smartchem.experiment.stock import Phase


class TestEvidenceReconstructsItsInterval:
    def test_every_published_record_verifies(self):
        # the load-bearing invariant: value_interval == derivation_fn(*derivation_inputs), exactly.
        assert ml.DERIVED_INTERVAL_EVIDENCE  # non-empty
        for derivation_id, ev in ml.DERIVED_INTERVAL_EVIDENCE.items():
            assert ev.verify(), derivation_id
            assert ev.recompute() == ev.value_interval, derivation_id

    def test_nacl_active_is_the_converted_brine_not_the_bug(self):
        ev = ml.DERIVED_INTERVAL_EVIDENCE["nacl-saturated-brine-active-massfrac"]
        # solubility 35.7-36.0 g/100 g water -> mass fraction of SOLUTION via s/(s+100).
        assert ev.unit is IntervalUnit.MASS_FRACTION_OF_SOLUTION
        assert ev.derivation_method is DerivationMethod.UNIT_CONVERTED
        assert ev.value_interval == (Fraction(357, 1357), Fraction(9, 34))
        lo, hi = ev.as_floats()
        assert 0.263 <= lo <= 0.264 and 0.264 <= hi <= 0.265
        # NOT the raw g/100g figure (0.357), NOT the mis-stated-premise value (0.208), NOT the old band.
        assert not (0.23 <= lo <= 0.27 and lo < 0.263)

    def test_isoamyl_dilute_active_is_converted(self):
        ev = ml.DERIVED_INTERVAL_EVIDENCE["isoamyl-dilute-aqueous-active-massfrac"]
        assert ev.value_interval == (Fraction(1, 51), Fraction(3, 103))  # 2/102, 3/103
        lo, hi = ev.as_floats()
        assert abs(lo - 0.019608) < 1e-6 and abs(hi - 0.029126) < 1e-6

    def test_nahco3_width_is_assumed_not_derived(self):
        ev = ml.DERIVED_INTERVAL_EVIDENCE["nahco3-5pct-wash-active-massfrac"]
        # the nominal 5% is sourced; the +-0.5% WIDTH is ASSUMED, not a measured/propagated error bar.
        assert ev.derivation_method is DerivationMethod.ASSUMED
        assert ev.value_interval == (Fraction(9, 200), Fraction(11, 200))  # 0.045, 0.055

    def test_water_complements_are_one_minus_active(self):
        for active_id, water_id in (
            ("nacl-saturated-brine-active-massfrac", "nacl-saturated-brine-water-balance"),
            ("nahco3-5pct-wash-active-massfrac", "nahco3-5pct-wash-water-balance"),
            ("isoamyl-dilute-aqueous-active-massfrac", "isoamyl-dilute-aqueous-water-balance"),
        ):
            active = ml.DERIVED_INTERVAL_EVIDENCE[active_id]
            water = ml.DERIVED_INTERVAL_EVIDENCE[water_id]
            a_lo, a_hi = active.value_interval
            assert water.value_interval == (1 - a_hi, 1 - a_lo)
            assert water.derivation_method is DerivationMethod.COMPLEMENT


class TestOldIntervalFailsTheCheck:
    def test_old_nacl_band_cannot_be_built_over_its_stated_derivation(self):
        # This is the regression guard: the OLD [0.23, 0.27] paired with the real conversion kernel must
        # NOT construct -- derivation_fn(35.7, 36.0) reconstructs [0.263, 0.265], not [0.23, 0.27].
        with pytest.raises(ValueError, match="derivation mismatch"):
            DerivedIntervalEvidence(
                derivation_id="nacl-OLD-buggy-band",
                value_interval=(Fraction(23, 100), Fraction(27, 100)),  # the retired [0.23, 0.27]
                unit=IntervalUnit.MASS_FRACTION_OF_SOLUTION,
                source_locator="(regression fixture)",
                derivation_method=DerivationMethod.UNIT_CONVERTED,
                derivation_inputs=(Fraction(357, 10), Fraction(36)),
                derivation_fn=solution_fraction_from_solubility,
                domain_of_validity="(regression fixture)",
            )

    def test_g_per_100g_used_as_fraction_is_the_bug_the_type_forbids(self):
        # The structural point: a solubility (g/100 g water) is NOT a mass fraction. Feeding 26.3 g/100 g
        # water as though the band were [0.263, 0.263] (the g/100g figure /100) does not equal the honest
        # conversion 26.3/(26.3+100) = 0.2082 -- so a record claiming the former over the real kernel fails.
        honest = solution_fraction_from_solubility(Fraction(263, 10), Fraction(263, 10))
        assert honest == (Fraction(263, 1263), Fraction(263, 1263))
        assert abs(float(honest[0]) - 0.2082) < 1e-3
        with pytest.raises(ValueError, match="derivation mismatch"):
            DerivedIntervalEvidence(
                derivation_id="nacl-g-per-100g-as-fraction",
                value_interval=(Fraction(263, 1000), Fraction(263, 1000)),  # 0.263 as if g/100g WERE the fraction
                unit=IntervalUnit.MASS_FRACTION_OF_SOLUTION,
                source_locator="(regression fixture)",
                derivation_method=DerivationMethod.UNIT_CONVERTED,
                derivation_inputs=(Fraction(263, 10), Fraction(263, 10)),
                derivation_fn=solution_fraction_from_solubility,
                domain_of_validity="(regression fixture)",
            )


class TestStockMaterialsCarryTheCorrectedNumbers:
    def test_nacl_wash_components_match_the_evidence(self):
        mat = ml.sodium_chloride_saturated_wash()
        by_role = {c.role: c for c in mat.components}
        a_lo, a_hi = ml.DERIVED_INTERVAL_EVIDENCE["nacl-saturated-brine-active-massfrac"].as_floats()
        w_lo, w_hi = ml.DERIVED_INTERVAL_EVIDENCE["nacl-saturated-brine-water-balance"].as_floats()
        assert (by_role["active"].min_fraction, by_role["active"].max_fraction) == (a_lo, a_hi)
        assert (by_role["solvent"].min_fraction, by_role["solvent"].max_fraction) == (w_lo, w_hi)
        assert mat.phase is Phase.AQUEOUS_SOLUTION

    def test_nahco3_wash_components_match_the_evidence(self):
        mat = ml.sodium_bicarbonate_wash_5pct()
        by_role = {c.role: c for c in mat.components}
        a_lo, a_hi = ml.DERIVED_INTERVAL_EVIDENCE["nahco3-5pct-wash-active-massfrac"].as_floats()
        assert (by_role["active"].min_fraction, by_role["active"].max_fraction) == (a_lo, a_hi)

    def test_isoamyl_dilute_components_match_the_evidence(self):
        mat = ml.isoamyl_alcohol_dilute_aqueous()
        by_role = {c.role: c for c in mat.components}
        a_lo, a_hi = ml.DERIVED_INTERVAL_EVIDENCE["isoamyl-dilute-aqueous-active-massfrac"].as_floats()
        assert (by_role["active"].min_fraction, by_role["active"].max_fraction) == (a_lo, a_hi)


class TestKernels:
    def test_solution_fraction_matches_hand_arithmetic(self):
        assert solution_fraction_from_solubility(Fraction(2), Fraction(3)) == (Fraction(1, 51), Fraction(3, 103))

    def test_complement_is_one_minus(self):
        assert complement_band(Fraction(1, 4), Fraction(1, 3)) == (Fraction(2, 3), Fraction(3, 4))
