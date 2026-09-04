"""THERMO-UNC-01 (remainder): σ(ΔG) / σ(log10 K) propagation through feasibility + equilibrium.

Pins: (1) the crux fix -- the group-additivity uncertainty band, previously DROPPED by resolve_thermo, now rides the
ThermoRef; (2) σ(ΔG) propagated in quadrature to the EXACT hand value from the seed's sourced ±; (3) the honest mixed
sourced/derived edge -- one species with no sourced σ makes σ(ΔG) UNKNOWN (never a partial sum that understates it),
even though ΔG itself is known; (4) the LOWER-BOUND flag when ≥2 group-derived species make the independent-quadrature
assumption unsound; (5) the same σ carried to σ(log10 K).
"""
from __future__ import annotations

import math

from smartchem.data.thermo_groups import estimate_thermo
from smartchem.experiment.equilibrium import GAS_CONSTANT_J_PER_MOL_K, equilibrium_of_step
from smartchem.experiment.feasibility import feasibility_of_step, resolve_thermo
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

H2 = parse_smiles("[H][H]")
O2 = parse_smiles("O=O")
H2O = parse_smiles("O")
ETHANOL = parse_smiles("CCO")      # off-seed (C2H6O) -> group-additivity DERIVED
ETHYLENE = parse_smiles("C=C")     # off-seed -> group-additivity DERIVED


def water_synthesis():   # 2 H2 + O2 -> 2 H2O(l): every species is sourced WITH a CODATA ±
    return ExperimentStep.assembling(H2O, (H2, H2, O2), (H2O, H2O))


def haber():             # N2 + 3 H2 -> 2 NH3: N2's S° and NH3 have NO sourced ±
    N2, NH3 = parse_smiles("N#N"), parse_smiles("N")
    return ExperimentStep.assembling(NH3, (N2, H2, H2, H2), (NH3, NH3))


def test_the_group_additivity_sigma_is_now_threaded_not_dropped():
    """The crux: resolve_thermo used to destructure 5 of GroupThermoEstimate's fields and drop the uncertainty band.
    Now a DERIVED record carries the SAME band estimate_thermo computed -- distinguishable from a sourced value that
    honestly has no ±."""
    est = estimate_thermo(ETHANOL)
    assert est is not None and est.dhf_uncertainty_kj > 0 and est.s_uncertainty_j_per_k > 0  # a real band exists
    ref = resolve_thermo(ETHANOL, condensed=False)  # gas estimate, no phase correction
    assert ref is not None and ref.grade in ("DERIVED", "PREDICTED")
    assert ref.uncertainty_dhf_kj == est.dhf_uncertainty_kj   # threaded, not None
    assert ref.uncertainty_s_j_per_mol_k == est.s_uncertainty_j_per_k


def test_sigma_delta_g_is_the_exact_quadrature_of_the_sourced_uncertainties():
    """All-sourced reaction: σ(ΔG) is computable and equals the hand quadrature of the seed's ± -- σ(ΔH)²=Σ(ν σ_ΔfH)²,
    σ(ΔS)²=Σ(ν σ_S)², σ(ΔG)²=σ(ΔH)²+(T σ(ΔS)/1000)². Independent CODATA inputs, so NOT a lower bound."""
    f = feasibility_of_step(water_synthesis())
    assert f.delta_g_kj is not None and f.sigma_delta_g_kj is not None
    t = f.temperature_k
    # net ν (reactant +, product -): H2=+2 (σ_ΔfH 0.0, σ_S 0.003), O2=+1 (0.0, 0.005), H2O=-2 (0.040, 0.03)
    sdh = math.sqrt((2 * 0.0) ** 2 + (1 * 0.0) ** 2 + (2 * 0.040) ** 2)
    sds = math.sqrt((2 * 0.003) ** 2 + (1 * 0.005) ** 2 + (2 * 0.03) ** 2)
    expected = math.sqrt(sdh ** 2 + (t * sds / 1000.0) ** 2)
    assert abs(f.sigma_delta_g_kj - expected) < 1e-9
    assert f.sigma_delta_g_is_lower_bound is False


def test_a_species_with_no_sourced_sigma_makes_sigma_delta_g_unknown():
    """The honest mixed edge: Haber uses N2 (S° has no sourced ±) and NH3 (no ± at all), so σ(ΔG) is UNKNOWN -- a
    partial sum over only the σ-bearing species would understate it. ΔG itself is still known (the value is not
    gated on the uncertainty)."""
    f = feasibility_of_step(haber())
    assert f.delta_g_kj is not None       # ΔG computed
    assert f.sigma_delta_g_kj is None     # but σ(ΔG) honestly UNKNOWN, not a fabricated/partial number
    assert f.sigma_delta_g_is_lower_bound is False


def test_two_derived_species_flag_sigma_as_a_lower_bound():
    """≥2 group-additivity DERIVED species share Benson-group anchors (correlated errors), so the independent
    quadrature UNDERSTATES σ(ΔG) -- it is reported as a LOWER BOUND, not a tight value."""
    step = ExperimentStep.assembling(ETHYLENE, (ETHANOL,), (ETHYLENE, H2O))  # ethanol + ethylene both DERIVED
    f = feasibility_of_step(step)
    assert f.delta_g_kj is not None
    assert f.sigma_delta_g_kj is not None            # every species has a σ (derived bands + water's ±)
    assert f.sigma_delta_g_is_lower_bound is True     # correlated derived inputs -> lower bound
    assert "LOWER BOUND" in f.reason


def test_sigma_log10_k_propagates_linearly_from_sigma_delta_g():
    """log10 K is linear in ΔG, so σ(log10 K) = σ(ΔG)·1000/(R·T·ln10); UNKNOWN when σ(ΔG) is; the lower-bound flag
    rides forward."""
    e = equilibrium_of_step(water_synthesis())
    f = feasibility_of_step(water_synthesis())
    assert e.sigma_log10_k is not None and f.sigma_delta_g_kj is not None
    expected = f.sigma_delta_g_kj * 1000.0 / (GAS_CONSTANT_J_PER_MOL_K * f.temperature_k * math.log(10.0))
    assert abs(e.sigma_log10_k - expected) < 1e-12
    assert e.sigma_log10_k_is_lower_bound is False

    haber_eq = equilibrium_of_step(haber())
    assert haber_eq.sigma_log10_k is None  # σ(ΔG) UNKNOWN -> σ(log10 K) UNKNOWN
