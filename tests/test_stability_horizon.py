"""DURATION-STABILITY-01 (queue item 3): a duration-aware survival verdict over SOURCED decomposition kinetics.

E1's shipped composability check is instantaneous (onset-vs-exposure); ROUND 15 shipped only the diagnostic
hold-minutes.  This battery pins the duration-aware MACHINERY on KNOWN physics: the N2O5 instrument
calibration (k reproduces the measured value), the first-order survival exp(-k t) reproduced to hand value,
the NON-vacuous verdict spread, the DERIVED/PREDICTED grade, and -- the load-bearing discipline -- fail-closed
UNKNOWN plus the structure-keyed (never formula) direction-specific rate bridge, so no isomer or product
borrows a rate.  Boundary pinned too: it is a standalone primitive, not yet wired into the core E1 verdict.
"""
from __future__ import annotations

import math

import pytest

from experiments.stability_horizon_probe import FROZEN_HASH, content_hash
from experiments.stability_horizon_probe import validate as validate_probe
from smartchem.experiment.kinetics import GAS_CONSTANT_J_PER_MOL_K as ENGINE_R
from smartchem.experiment.stability_horizon import (
    GAS_CONSTANT_J_PER_MOL_K,
    STABILITY_HORIZON_SCHEMA,
    StabilityHorizon,
    SurvivalVerdict,
    decomposition_rate_for,
    stability_horizon,
    surviving_fraction,
)
from smartchem.smiles import parse_smiles

_N2O5 = "O=[N+]([O-])O[N+](=O)[O-]"


def _n2o5():
    return parse_smiles(_N2O5)


# --- the instrument calibration: recover the measured rate before trusting a survival reading -------

def test_n2o5_rate_reproduces_the_measured_k_and_R_does_not_drift():
    assert GAS_CONSTANT_J_PER_MOL_K == ENGINE_R          # no drift from the L1 rate engine
    rec = decomposition_rate_for(_n2o5())
    assert rec is not None and rec.name == "N2O5 decomposition"
    log10_k = rec.log10_a - (rec.ea_kj_per_mol * 1000.0) / (GAS_CONSTANT_J_PER_MOL_K * 298.0 * math.log(10.0))
    assert abs(10.0 ** log10_k - 3.38e-5) / 3.38e-5 < 0.10   # measured k(298 K) to ~7%


def test_survival_is_first_order_decay_reproduced_to_hand_value():
    rec = decomposition_rate_for(_n2o5())
    for T, t in ((298.0, 60.0), (298.0, 3600.0), (338.0, 600.0)):
        hand = math.exp(-(10.0 ** (rec.log10_a - (rec.ea_kj_per_mol * 1000.0)
                       / (GAS_CONSTANT_J_PER_MOL_K * T * math.log(10.0)))) * t)
        assert abs(surviving_fraction(rec, T, t) - hand) < 1e-12
        assert abs(stability_horizon(_n2o5(), T, t).fraction_remaining - hand) < 1e-12


# --- the verdict is non-vacuous, and duration actually moves it --------------------------------------

def test_the_duration_aware_verdict_spreads_non_vacuously_with_hold_and_temperature():
    mol = _n2o5()
    assert stability_horizon(mol, 298.0, 60.0).verdict is SurvivalVerdict.SURVIVES       # 60 s: essentially intact
    assert stability_horizon(mol, 298.0, 3600.0).verdict is SurvivalVerdict.MARGINAL     # 1 h: a disclosed concern
    assert stability_horizon(mol, 298.0, 21600.0).verdict is SurvivalVerdict.DEGRADES    # 6 h: majority destroyed
    # and hotter degrades faster: 338 K reaches DEGRADES in 10 min where 298 K needs hours.
    assert stability_horizon(mol, 338.0, 600.0).verdict is SurvivalVerdict.DEGRADES
    # the whole point: the SAME compound flips verdict on the HOLD alone -- a time axis the onset check lacks.
    assert (stability_horizon(mol, 298.0, 60.0).verdict
            is not stability_horizon(mol, 298.0, 21600.0).verdict)


def test_grade_is_derived_in_window_and_flagged_predicted_outside():
    mol = _n2o5()
    assert stability_horizon(mol, 298.0, 60.0).grade == "DERIVED"        # inside 298-338 K
    assert stability_horizon(mol, 373.0, 60.0).grade == "PREDICTED"      # extrapolated, flagged


# --- fail-closed + anti-fabrication: no rate, wrong direction, or same-formula isomer -> UNKNOWN -----

def test_a_compound_with_no_sourced_rate_is_unknown_never_fabricated():
    h = stability_horizon(parse_smiles("O"), 298.0, 60.0)               # water: no sourced decomposition rate
    assert h.verdict is SurvivalVerdict.UNKNOWN
    assert h.fraction_remaining is None
    assert h.is_sourced is False


def test_a_product_species_gets_no_decomposition_rate_direction_matters():
    # NO2 is a PRODUCT of the N2O5 record; its decomposition rate is a different (unsourced) reaction.
    assert decomposition_rate_for(parse_smiles("[N+](=O)[O-]")) is None


def test_a_same_formula_isomer_does_not_borrow_the_rate_structure_keyed():
    # cyclopropane and propene are both C3H6; only cyclopropane (the sourced reactant) reads a rate.
    assert decomposition_rate_for(parse_smiles("C1CC1")) is not None    # cyclopropane: sourced
    assert decomposition_rate_for(parse_smiles("CC=C")) is None         # propene: same formula, NOT borrowed


# --- the reading is coherent and its provenance flag is computed, not stored ------------------------

def test_the_horizon_is_coherent_and_is_sourced_is_computed():
    sourced = stability_horizon(_n2o5(), 298.0, 60.0)
    assert sourced.is_sourced is True and sourced.fraction_remaining is not None
    # fail-closed coherence: fraction_remaining is None IFF the verdict is UNKNOWN.
    with pytest.raises(ValueError, match="fail-closed coherence"):
        StabilityHorizon(STABILITY_HORIZON_SCHEMA, "d", 298.0, 60.0, None, SurvivalVerdict.SURVIVES, "DERIVED")
    with pytest.raises(ValueError, match="fail-closed coherence"):
        StabilityHorizon(STABILITY_HORIZON_SCHEMA, "d", 298.0, 60.0, 0.9, SurvivalVerdict.UNKNOWN, "UNKNOWN")


def test_non_positive_temperature_or_hold_is_refused():
    for T, t in ((0.0, 60.0), (-1.0, 60.0), (298.0, 0.0), (298.0, -5.0)):
        with pytest.raises(ValueError):
            stability_horizon(_n2o5(), T, t)


def test_a_non_finite_injected_rate_fails_closed_never_a_nan_fraction():
    # evil-morty LOW-2: the data layer accepts a non-finite (Ea, A); surviving_fraction must NOT return a
    # silent NaN over it.  Fail-closed at the primitive, not only at the [0,1] coherence guard downstream.
    from smartchem.data.kinetics import KineticRef
    bad = KineticRef((("O=[N+]([O-])O[N+](=O)[O-]", 2),), (("[N+](=O)[O-]", 4), ("O=O", 1)),
                     "nan record", float("nan"), 13.69, "s^-1", (298.0, 338.0), "fabricated non-finite Ea")
    with pytest.raises(ValueError, match="finite"):
        surviving_fraction(bad, 298.0, 60.0)


# --- the committed harness --------------------------------------------------------------------------

def test_the_committed_harness_validates_and_its_hash_is_frozen():
    validate_probe()
    assert content_hash() == FROZEN_HASH
