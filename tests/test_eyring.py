"""L1 Eyring / transition-state rate provider -- the SECOND, independent rate provider.

Pins the properties the whole design turns on: the engine reproduces an INDEPENDENTLY measured rate from
sourced (ΔH‡, ΔS‡) (the instrument rule, and non-circular vs the Arrhenius provider); a same-formula isomer
never inherits another reaction's barrier; the rate is ORTHOGONAL to the L2 grade; the Arrhenius/Eyring
cross-check corroborates or flags two independent k's; a missing barrier is a LOUD UNKNOWN; an unphysical
temperature is refused.
"""
import math

import pytest

from smartchem.data.eyring import DEFAULT_EYRING, EYRING_GAPS, EyringRef, EyringTable, SEED_EYRING_REFS
from smartchem.data.kinetics import DEFAULT_KINETICS, KineticRef, KineticTable
from smartchem.experiment.eyring import (
    BOLTZMANN_J_PER_K,
    PLANCK_J_S,
    eyring_of_step,
    rate_agreement,
    verify_eyring,
)
from smartchem.experiment.kinetics import RateGrade, RateRegime, _resolve_record, kinetics_of_step
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles


def _saponification() -> ExperimentStep:
    """CH3COOC2H5 + OH- -> CH3COO- + C2H5OH -- the sourced Eyring calibration reaction."""
    ea = parse_smiles("CCOC(C)=O")
    oh = parse_smiles("[OH-]")
    ac = parse_smiles("CC(=O)[O-]")
    et = parse_smiles("CCO")
    return ExperimentStep.assembling(et, (ea, oh), (ac, et))


def _n2o5_decomposition() -> ExperimentStep:
    a = parse_smiles("O=[N+]([O-])O[N+](=O)[O-]")
    n = parse_smiles("[N+](=O)[O-]")
    o = parse_smiles("O=O")
    return ExperimentStep.assembling(o, (a, a), (n, n, n, n, o))


class TestSeedIntegrity:
    def test_the_seed_is_the_saponification_calibration_reaction(self):
        assert len(SEED_EYRING_REFS) == 1
        r = SEED_EYRING_REFS[0]
        assert r.dh_dagger_kj_per_mol == 38.6
        assert r.ds_dagger_j_per_mol_k == -131.0
        assert r.a_units == "M^-1 s^-1"
        assert "Petek" in r.provenance and "Tsujikawa" in r.provenance  # params source AND independent calib

    def test_the_constants_are_the_si_2019_exact_values(self):
        assert BOLTZMANN_J_PER_K == 1.380649e-23
        assert PLANCK_J_S == 6.62607015e-34

    def test_a_negative_activation_enthalpy_is_refused_but_negative_entropy_is_allowed(self):
        with pytest.raises(ValueError):
            EyringRef((("CCO", 1),), (("CCO", 1),), "bad", -1.0, 0.0, "s^-1", (298.0, 300.0), "x")
        # a large NEGATIVE ΔS‡ is physically correct (associative TS) and must be allowed:
        EyringRef((("CCO", 1),), (("CCO", 1),), "ok", 50.0, -150.0, "s^-1", (298.0, 300.0), "x")


class TestCalibration:
    def test_engine_reproduces_the_independent_measured_k(self):
        # ΔH‡/ΔS‡ (Petek 2012) must reproduce the INDEPENDENT measured k (Tsujikawa 1966, 0.112 M^-1 s^-1) --
        # the instrument rule, and a cross-validation across two independent studies 46 years apart.
        sk = eyring_of_step(_saponification(), temperature_k=298.15)
        engine_k = 10.0 ** sk.log10_k
        assert math.isclose(engine_k, 0.112, rel_tol=0.5)  # within ~a factor of 1.5 (actually ~1.4)
        assert sk.grade is RateGrade.DERIVED  # 298 K inside the 298-323 K window
        assert sk.regime is RateRegime.MODERATE

    def test_gibbs_is_self_consistent(self):
        sk = eyring_of_step(_saponification(), temperature_k=298.15)
        assert math.isclose(sk.dg_dagger_kj_per_mol, 38.6 - 298.15 * (-131.0) / 1000.0, rel_tol=1e-9)


class TestNonCircularity:
    def test_the_eyring_seed_is_not_an_arrhenius_relabel(self):
        # The saponification reaction is NOT in the Arrhenius seed (its Arrhenius A is a documented gap), so the
        # sourced Eyring params cannot be a back-calc of a seeded Arrhenius record -- they are independent.
        assert _resolve_record(DEFAULT_KINETICS, _saponification()) is None


class TestLoudUnknownAndSafety:
    def test_a_missing_barrier_is_a_loud_unknown_never_a_fabricated_k(self):
        sk = eyring_of_step(_n2o5_decomposition())  # not in DEFAULT_EYRING
        assert sk.regime is RateRegime.UNKNOWN and sk.grade is RateGrade.UNKNOWN
        assert not sk.is_known
        assert sk.log10_k is None

    def test_direction_specific_the_reverse_does_not_inherit_the_barrier(self):
        rev = ExperimentStep.assembling(
            parse_smiles("CCOC(C)=O"),
            (parse_smiles("CC(=O)[O-]"), parse_smiles("CCO")),
            (parse_smiles("CCOC(C)=O"), parse_smiles("[OH-]")),
        )
        assert eyring_of_step(rev).regime is RateRegime.UNKNOWN

    def test_a_same_formula_isomer_does_not_inherit_the_barrier(self):
        # Inject a barrier for a DIFFERENT reactant that shares a formula; the real reaction must not match it.
        iso = EyringTable((
            EyringRef((("C1CC1", 1),), (("CC=C", 1),), "cyclopropane iso", 50.0, -10.0, "s^-1",
                      (298.0, 400.0), "synthetic"),
        ))
        # a propene->cyclopropane step (same formulas C3H6) must not borrow the cyclopropane->propene barrier
        step = ExperimentStep.assembling(parse_smiles("C1CC1"), (parse_smiles("CC=C"),), (parse_smiles("C1CC1"),))
        assert eyring_of_step(step, barriers=iso).regime is RateRegime.UNKNOWN

    def test_unphysical_temperature_is_refused(self):
        with pytest.raises(ValueError):
            eyring_of_step(_saponification(), temperature_k=0.0)
        with pytest.raises(ValueError):
            eyring_of_step(_saponification(), temperature_k=-5.0)


class TestCrossCheck:
    def test_agreement_note_when_both_providers_fire(self):
        # Seed the SAME reaction in a (synthetic) Arrhenius table chosen to reproduce ~the Eyring k, and confirm
        # the cross-check reports AGREEMENT -- the two-blind-paths corroboration on one observable.
        eyr = eyring_of_step(_saponification(), temperature_k=298.15)
        # pick a synthetic Arrhenius (Ea, A) giving log10 k close to the Eyring value at 298 K
        target = eyr.log10_k
        ea = 41.4
        # log10 k = log10_a - Ea*1000/(R*T*ln10) => log10_a = target + Ea*1000/(R*T*ln10)
        log10_a = target + ea * 1000.0 / (8.314462618 * 298.15 * math.log(10.0))
        arr = KineticTable((
            KineticRef((("CCOC(C)=O", 1), ("[OH-]", 1)), (("CC(=O)[O-]", 1), ("CCO", 1)),
                       "sap-arrhenius-synthetic", ea, log10_a, "M^-1 s^-1", (298.0, 323.0), "SYNTHETIC test ref"),
        ))
        kin = kinetics_of_step(_saponification(), kinetics=arr, temperature_k=298.15)
        note = rate_agreement(kin, eyr)
        assert note is not None and "AGREE" in note

    def test_no_note_when_only_one_provider_fires(self):
        eyr = eyring_of_step(_saponification(), temperature_k=298.15)
        kin = kinetics_of_step(_saponification(), temperature_k=298.15)  # Arrhenius UNKNOWN (a documented gap)
        assert not kin.is_known
        assert rate_agreement(kin, eyr) is None  # nothing to cross-check

    def test_disagreement_is_flagged_not_hidden(self):
        eyr = eyring_of_step(_saponification(), temperature_k=298.15)
        # a synthetic Arrhenius ref wildly off from the Eyring k
        arr = KineticTable((
            KineticRef((("CCOC(C)=O", 1), ("[OH-]", 1)), (("CC(=O)[O-]", 1), ("CCO", 1)),
                       "sap-off", 10.0, 20.0, "M^-1 s^-1", (298.0, 323.0), "SYNTHETIC off ref"),
        ))
        kin = kinetics_of_step(_saponification(), kinetics=arr, temperature_k=298.15)
        note = rate_agreement(kin, eyr)
        assert note is not None and "DISAGREE" in note


class TestRouteAggregation:
    def test_route_verdict_is_bottleneck_dominated(self):
        route = ExperimentRoute.of(_saponification())
        reyr = verify_eyring(route)
        assert reyr.verdict == "MODERATE"  # the single sourced step's regime at 298 K


class TestEyringGaps:
    def test_the_rejected_retro_diels_alder_is_documented_not_seeded(self):
        # the physically-anomalous open-access candidate was rejected, and that refusal is documented.
        assert any("retro-Diels-Alder" in v for v in EYRING_GAPS.values())
        # and it is NOT silently seeded:
        assert all("retro" not in r.name.lower() for r in DEFAULT_EYRING.records)


class TestEyringInClassify:
    def test_classify_surfaces_eyring_but_it_never_touches_the_grade(self):
        # Go through the CLASSIFY DISPATCHER (not classify_step directly), so this also guards that the
        # dispatcher threads `barriers` to the step branch -- a bug the acceptance gate once caught.
        from smartchem.experiment.classify import classify

        step = _saponification()
        base = classify(step)  # DEFAULT_EYRING carries this reaction (MODERATE at 298 K)
        assert base.eyring is not None and base.eyring.regime is RateRegime.MODERATE
        # inject a FROZEN barrier for the same reaction -> the grade must be IDENTICAL (orthogonality)
        frozen = EyringTable((
            EyringRef((("CCOC(C)=O", 1), ("[OH-]", 1)), (("CC(=O)[O-]", 1), ("CCO", 1)),
                      "sap-frozen", 200.0, -131.0, "M^-1 s^-1", (298.0, 323.0), "SYNTHETIC frozen"),
        ))
        with_frozen = classify(step, barriers=frozen)
        assert with_frozen.grade == base.grade  # rate NEVER enters the grade
        assert with_frozen.eyring.regime is RateRegime.FROZEN
        # the sourced Eyring rate is surfaced as a bucketed finding
        assert any("eyring" in f.label for f in with_frozen.findings)
