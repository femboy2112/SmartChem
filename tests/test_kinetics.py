"""L1 kinetics: the Arrhenius rate dimension -- calibrated, orthogonal, and loud on a gap.

The rung reproduces a KNOWN rate where (Ea, A) are sourced and refuses (loud UNKNOWN) where they are not; it
is a dimension REPORTED alongside the L2 grade, never one that changes it.  These tests pin all three: the
instrument reads true on the sourced calibration reaction, a missing rate is UNKNOWN not fabricated, and a
reaction's rate never lifts or lowers its epistemic grade.
"""
from __future__ import annotations

import math

import pytest

from smartchem.data.kinetics import (
    DEFAULT_KINETICS,
    KINETIC_GAPS,
    SEED_KINETIC_REFS,
    KineticRef,
    KineticTable,
)
from smartchem.experiment.bucket import Bucket
from smartchem.experiment.classify import Grade, classify_step
from smartchem.experiment.kinetics import (
    RateGrade,
    RateRegime,
    RouteKinetics,
    StepKinetics,
    _resolve_record,
    kinetics_of_step,
    reaction_key_of,
    verify_kinetics,
    worst_regime,
)
from smartchem.experiment.selectivity import DEFAULT_SELECTIVITY
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles


def _n2o5_decomposition() -> ExperimentStep:
    """2 N2O5 -> 4 NO2 + O2 -- the sourced first-order calibration reaction."""
    n2o5 = parse_smiles("O=[N+]([O-])O[N+](=O)[O-]")
    no2 = parse_smiles("[N+](=O)[O-]")
    o2 = parse_smiles("O=O")
    return ExperimentStep.assembling(o2, (n2o5, n2o5), (no2, no2, no2, no2, o2))


def _paracetamol_acetylation() -> ExperimentStep:
    """4-aminophenol + acetic anhydride -> paracetamol + acetic acid (KNOWN via sourced selectivity)."""
    aminophenol = parse_smiles("Nc1ccc(O)cc1")
    anhydride = parse_smiles("CC(=O)OC(=O)C")
    paracetamol = parse_smiles("CC(=O)Nc1ccc(O)cc1")
    acetic = parse_smiles("CC(=O)O")
    return ExperimentStep.assembling(paracetamol, (aminophenol, anhydride), (paracetamol, acetic))


class TestSeedIntegrity:
    def test_the_seed_holds_the_n2o5_calibration_record(self) -> None:
        names = {r.name for r in SEED_KINETIC_REFS}
        assert "N2O5 decomposition" in names

    def test_a_kinetic_ref_requires_a_provenance(self) -> None:
        with pytest.raises(ValueError):
            KineticRef(
                reactant_smiles=(("O=O", 1),), product_smiles=(("O=O", 1),), name="x",
                ea_kj_per_mol=103.5, log10_a=13.69, a_units="s^-1", temperature_range_k=(298.0, 338.0),
                provenance="",
            )

    def test_a_kinetic_ref_rejects_a_malformed_species_spec(self) -> None:
        # a non-positive coefficient / empty smiles is refused (the source form must be well-formed)
        with pytest.raises(ValueError):
            KineticRef(
                reactant_smiles=(("O=O", 0),), product_smiles=(("O=O", 1),), name="x",
                ea_kj_per_mol=103.5, log10_a=13.69, a_units="s^-1", temperature_range_k=(298.0, 338.0),
                provenance="p",
            )

    def test_a_kinetic_ref_rejects_a_negative_activation_energy(self) -> None:
        with pytest.raises(ValueError):
            KineticRef(
                reactant_smiles=(("O=O", 1),), product_smiles=(("O=O", 1),), name="x",
                ea_kj_per_mol=-1.0, log10_a=13.69, a_units="s^-1", temperature_range_k=(298.0, 338.0),
                provenance="p",
            )

    def test_gaps_document_the_hi_and_litmus_rate_absences(self) -> None:
        assert "2 HI -> H2 + I2" in KINETIC_GAPS
        assert any("paracetamol" in k for k in KINETIC_GAPS)


class TestCalibration:
    """The instrument reads true: engine k reproduces the FETCHED measured rate before novel outputs count."""

    @pytest.mark.parametrize("temperature_k, measured_k", [(298.15, 3.38e-5), (338.0, 4.82e-3)])
    def test_engine_k_reproduces_the_measured_rate_within_15_percent(self, temperature_k, measured_k) -> None:
        step = _n2o5_decomposition()
        sk = kinetics_of_step(step, temperature_k=temperature_k)
        engine_k = 10.0 ** sk.log10_k
        assert math.isclose(engine_k, measured_k, rel_tol=0.15), (engine_k, measured_k)

    def test_inside_the_fit_window_the_rate_is_derived(self) -> None:
        sk = kinetics_of_step(_n2o5_decomposition(), temperature_k=310.0)
        assert sk.grade is RateGrade.DERIVED
        assert sk.regime is not RateRegime.UNKNOWN

    def test_outside_the_fit_window_the_rate_is_flagged_predicted(self) -> None:
        sk = kinetics_of_step(_n2o5_decomposition(), temperature_k=200.0)  # below 298-338 K
        assert sk.grade is RateGrade.PREDICTED
        assert "PREDICTED" in sk.reason and "outside" in sk.reason

    def test_a_sourced_rate_is_a_known_sourced_quantity_with_provenance(self) -> None:
        sk = kinetics_of_step(_n2o5_decomposition(), temperature_k=310.0)
        assert sk.k_finding.bucket is Bucket.KNOWN_SOURCED
        assert sk.k_finding.provenance  # non-empty


class TestLoudUnknownOnAGap:
    def test_a_reaction_with_no_sourced_ea_a_is_a_loud_unknown(self) -> None:
        sk = kinetics_of_step(_paracetamol_acetylation())  # not in the seed
        assert sk.regime is RateRegime.UNKNOWN
        assert sk.grade is RateGrade.UNKNOWN
        assert sk.k_finding.bucket is Bucket.UNKNOWN
        assert sk.k_finding.value is None  # never a fabricated k
        assert "bond energies" in sk.reason  # states it will not guess a barrier

    def test_the_reverse_direction_is_a_different_reaction_and_stays_unknown(self) -> None:
        # the sourced rate is for the forward decomposition; the reverse assembly is a distinct, unsourced key
        n2o5 = parse_smiles("O=[N+]([O-])O[N+](=O)[O-]")
        no2 = parse_smiles("[N+](=O)[O-]")
        o2 = parse_smiles("O=O")
        reverse = ExperimentStep.assembling(n2o5, (no2, no2, no2, no2, o2), (n2o5, n2o5))
        assert kinetics_of_step(reverse).regime is RateRegime.UNKNOWN


class TestReactionKey:
    def test_the_key_is_canonical_and_order_independent(self) -> None:
        # same reaction, product tuple written in a different order -> identical structural key
        key = reaction_key_of(_n2o5_decomposition())
        r, p = key
        assert list(r) == sorted(r) and list(p) == sorted(p)  # canonical (sorted) form
        assert _resolve_record(DEFAULT_KINETICS, _n2o5_decomposition()) is not None  # the seed matches it

    def test_uniform_equation_scaling_preserves_the_reaction_key_and_rate_lookup(self) -> None:
        base = _n2o5_decomposition()
        scaled = ExperimentStep.assembling(base.target, base.reactants * 3, base.products * 3)
        assert reaction_key_of(scaled) == reaction_key_of(base)
        assert _resolve_record(DEFAULT_KINETICS, scaled) is not None
        assert kinetics_of_step(scaled, temperature_k=310.0).log10_k == pytest.approx(
            kinetics_of_step(base, temperature_k=310.0).log10_k
        )

    def test_a_same_formula_isomer_does_NOT_inherit_the_rate(self) -> None:
        # a peroxide isomer of N2O5 (same formula N2O5, different structure) must NOT borrow N2O5's rate
        peroxy = parse_smiles("O=[N+]([O-])OO[N]=O")
        no2 = parse_smiles("[N+](=O)[O-]")
        o2 = parse_smiles("O=O")
        step = ExperimentStep.assembling(o2, (peroxy, peroxy), (no2, no2, no2, no2, o2))
        sk = kinetics_of_step(step, temperature_k=298.15)
        assert sk.regime is RateRegime.UNKNOWN  # a loud UNKNOWN, never the wrong compound's KNOWN_SOURCED rate
        assert sk.k_finding.bucket is Bucket.UNKNOWN

    def test_forward_and_reverse_are_distinct_reactions(self) -> None:
        # an injected record for a forward direction must NOT answer the reverse
        eth = parse_smiles("CCO")
        dme = parse_smiles("COC")
        fwd = ExperimentStep.assembling(dme, (eth,), (dme,))   # ethanol -> dimethyl ether
        rev = ExperimentStep.assembling(eth, (dme,), (eth,))   # dimethyl ether -> ethanol
        tbl = KineticTable((KineticRef(
            reactant_smiles=(("CCO", 1),), product_smiles=(("COC", 1),), name="fwd only",
            ea_kj_per_mol=200.0, log10_a=13.0, a_units="s^-1", temperature_range_k=(300.0, 800.0),
            provenance="TEST forward ethanol->dimethyl ether only"),))
        assert kinetics_of_step(fwd, kinetics=tbl, temperature_k=600.0).regime is not RateRegime.UNKNOWN
        assert kinetics_of_step(rev, kinetics=tbl, temperature_k=600.0).regime is RateRegime.UNKNOWN


class TestUnphysicalTemperature:
    def test_a_nonpositive_temperature_is_refused_not_a_fabricated_rate(self) -> None:
        step = _n2o5_decomposition()
        with pytest.raises(ValueError):
            kinetics_of_step(step, temperature_k=0.0)
        with pytest.raises(ValueError):
            kinetics_of_step(step, temperature_k=-100.0)


class TestOrthogonality:
    """The rate NEVER enters the epistemic grade -- L2's whole point for this dimension."""

    def test_a_sourced_rate_does_not_lift_a_hypothesized_grade(self) -> None:
        # N2O5 has a sourced RATE but no sourced thermo/attestation -> grade stays the HYPOTHESIZED floor
        step = _n2o5_decomposition()
        verdict = classify_step(step)
        assert verdict.grade is Grade.HYPOTHESIZED
        assert verdict.kinetics is not None
        assert verdict.kinetics.regime is not RateRegime.UNKNOWN  # it DOES carry a rate, it just isn't graded

    def test_a_missing_rate_does_not_lower_a_known_grade(self) -> None:
        # the litmus acetylation is KNOWN (sourced selectivity) but its rate is UNKNOWN -> known-but-unknown-rate
        step = _paracetamol_acetylation()
        verdict = classify_step(step, selectivity=DEFAULT_SELECTIVITY)
        assert verdict.grade is Grade.KNOWN
        assert verdict.kinetics is not None
        assert verdict.kinetics.regime is RateRegime.UNKNOWN

    def test_the_grade_is_identical_with_and_without_a_kinetic_table(self) -> None:
        step = _n2o5_decomposition()
        with_rate = classify_step(step, kinetics=DEFAULT_KINETICS).grade
        without_rate = classify_step(step, kinetics=KineticTable(())).grade
        assert with_rate is without_rate


class TestRouteAggregation:
    def test_worst_regime_is_slowest_dominated(self) -> None:
        assert worst_regime([RateRegime.FAST, RateRegime.FROZEN]) is RateRegime.FROZEN
        assert worst_regime([RateRegime.FAST, RateRegime.SLOW]) is RateRegime.SLOW
        assert worst_regime([RateRegime.FAST, RateRegime.UNKNOWN]) is RateRegime.UNKNOWN
        assert worst_regime([RateRegime.FAST, RateRegime.MODERATE]) is RateRegime.MODERATE
        assert worst_regime([RateRegime.FAST]) is RateRegime.FAST
        assert worst_regime([]) is RateRegime.UNKNOWN

    def test_verify_kinetics_reports_a_route_rate(self) -> None:
        route = ExperimentRoute.of(_n2o5_decomposition())
        rk = verify_kinetics(route)
        assert type(rk) is RouteKinetics
        assert len(rk.per_step) == 1
        assert all(type(s) is StepKinetics for s in rk.per_step)
        assert rk.verdict == rk.per_step[0].regime.value


class TestKineticBreadth:
    """A second sourced Arrhenius family: cyclopropane -> propene, calibration-verified against its anchor."""

    def _cyclopropane(self) -> ExperimentStep:
        return ExperimentStep.assembling(
            parse_smiles("CC=C"), (parse_smiles("C1CC1"),), (parse_smiles("CC=C"),)
        )

    def test_cyclopropane_is_in_the_default_seed(self) -> None:
        assert "cyclopropane isomerization" in {r.name for r in SEED_KINETIC_REFS}

    def test_the_engine_reproduces_the_sourced_anchor_k_at_773K(self) -> None:
        # Atkins Table 22.1 anchor: k = 6.71e-4 s^-1 at 773 K (500 C). The instrument must recover it.
        sk = kinetics_of_step(self._cyclopropane(), temperature_k=773.0)
        assert math.isclose(10.0 ** sk.log10_k, 6.71e-4, rel_tol=0.05)  # within 5% (actually ~1.5%)
        assert sk.grade is RateGrade.DERIVED  # 773 K inside the 700-800 K window

    def test_cyclopropane_is_frozen_at_room_temperature(self) -> None:
        # Correct chemistry: cyclopropane does not isomerize at RT; a FROZEN, flagged-extrapolated read.
        sk = kinetics_of_step(self._cyclopropane(), temperature_k=298.0)
        assert sk.regime is RateRegime.FROZEN
        assert sk.grade is RateGrade.PREDICTED  # 298 K far outside the 700-800 K fit window

    def test_the_c3h6_isomer_pair_is_kept_distinct_by_the_structural_key(self) -> None:
        # cyclopropane and propene are both C3H6; the reverse must NOT inherit the forward rate.
        rev = ExperimentStep.assembling(
            parse_smiles("C1CC1"), (parse_smiles("CC=C"),), (parse_smiles("C1CC1"),)
        )
        assert kinetics_of_step(rev).regime is RateRegime.UNKNOWN

    def test_the_saponification_arrhenius_units_gap_is_documented(self) -> None:
        assert any("saponification" in k for k in KINETIC_GAPS)
