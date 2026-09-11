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


def haber():             # N2 + 3 H2 -> 2 NH3: now FULLY sourced -- N2's S° ± and NH3's ± are CODATA-wired (widen)
    N2, NH3 = parse_smiles("N#N"), parse_smiles("N")
    return ExperimentStep.assembling(NH3, (N2, H2, H2, H2), (NH3, NH3))


def methane_combustion():   # CH4 + 2 O2 -> CO2 + 2 H2O: CH4's ΔfH° has a (Gurvich/JANAF) ± but its S° has NO stated ±
    CH4, CO2 = parse_smiles("C"), parse_smiles("O=C=O")
    return ExperimentStep.assembling(CO2, (CH4, O2, O2), (CO2, H2O, H2O))


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
    """The honest mixed edge: methane combustion uses CH4, whose S° has NO single stated ± (the statistical vs
    calorimetric sources disagree), so even though its ΔfH° ± IS sourced (Gurvich/JANAF), σ(ΔS) is UNKNOWN and thus
    σ(ΔG) is UNKNOWN -- a partial sum over only the σ-bearing axes would understate it. ΔG itself is still known.
    (After the THERMO-UNC-01 widen this is CH4's job -- Haber is now fully sourced; see the test below.)"""
    f = feasibility_of_step(methane_combustion())
    assert f.delta_g_kj is not None       # ΔG computed
    assert f.sigma_delta_g_kj is None     # but σ(ΔG) honestly UNKNOWN, not a fabricated/partial number
    assert f.sigma_delta_g_is_lower_bound is False


def test_the_widen_makes_hcl_synthesis_sigma_delta_g_informative():
    """ROUND-7 widen: wiring HCl and Cl2 (both CODATA, both σ) turns H2 + Cl2 -> 2 HCl into an INFORMATIVE σ(ΔG) case.
    Every species now carries both a ΔfH° ± and an S° ±, so σ(ΔG) is the exact hand quadrature; HCl's ΔfH° ±0.10
    (×2) dominates.  All independent CODATA/reference inputs, so NOT a lower bound."""
    H2, Cl2, HCl = parse_smiles("[H][H]"), parse_smiles("ClCl"), parse_smiles("Cl")
    f = feasibility_of_step(ExperimentStep.assembling(HCl, (H2, Cl2), (HCl, HCl)))
    assert f.delta_g_kj is not None and f.sigma_delta_g_kj is not None
    t = f.temperature_k
    # net ν: H2=+1 (0.0, 0.003), Cl2=+1 (0.0, 0.010), HCl=-2 (0.10, 0.005)
    sdh = math.sqrt((2 * 0.10) ** 2)
    sds = math.sqrt((1 * 0.003) ** 2 + (1 * 0.010) ** 2 + (2 * 0.005) ** 2)
    expected = math.sqrt(sdh ** 2 + (t * sds / 1000.0) ** 2)
    assert abs(f.sigma_delta_g_kj - expected) < 1e-9
    assert f.sigma_delta_g_is_lower_bound is False


def test_the_widened_seed_makes_haber_sigma_delta_g_informative():
    """THERMO-UNC-01-widen: wiring N2's S° ± and NH3's ΔfH°+S° ± from the frozen CODATA seed turns Haber from the old
    σ(ΔG)=UNKNOWN case into an INFORMATIVE one. σ(ΔG) is the exact hand quadrature; NH3's ΔfH° ±0.35 (×2) dominates.
    All inputs are independent CODATA/reference values, so it is NOT a lower bound. ΔG itself is unchanged (the values
    were untouched -- only the ± were added, compare=False)."""
    f = feasibility_of_step(haber())
    assert f.delta_g_kj is not None and f.sigma_delta_g_kj is not None
    t = f.temperature_k
    # net ν: N2=+1 (σ_ΔfH 0.0, σ_S 0.004), H2=+3 (0.0, 0.003), NH3=-2 (0.35, 0.05)
    sdh = math.sqrt((1 * 0.0) ** 2 + (3 * 0.0) ** 2 + (2 * 0.35) ** 2)
    sds = math.sqrt((1 * 0.004) ** 2 + (3 * 0.003) ** 2 + (2 * 0.05) ** 2)
    expected = math.sqrt(sdh ** 2 + (t * sds / 1000.0) ** 2)
    assert abs(f.sigma_delta_g_kj - expected) < 1e-9
    assert f.sigma_delta_g_is_lower_bound is False


def test_two_derived_species_flag_sigma_as_a_lower_bound():
    """≥2 group-additivity DERIVED species share the SAME Benson group DATABASE + the additivity assumption -- a
    common-mode systematic model error the independent quadrature cannot see -- so σ(ΔG) is a LOWER BOUND. This holds
    even though ethanol and ethylene share NO specific group (the correlation is through the shared MODEL, not a
    shared anchor -- the red-team-corrected rationale)."""
    step = ExperimentStep.assembling(ETHYLENE, (ETHANOL,), (ETHYLENE, H2O))  # ethanol + ethylene both DERIVED
    f = feasibility_of_step(step)
    assert f.delta_g_kj is not None
    assert f.sigma_delta_g_kj is not None            # every species has a σ (derived bands + water's ±)
    assert f.sigma_delta_g_is_lower_bound is True     # common-mode group-model error -> lower bound
    assert "LOWER BOUND" in f.reason


def test_a_lone_phase_corrected_derived_species_still_flags_lower_bound():
    """The red-team's HIGH: a group-DERIVED species phase-corrected (gas->liquid) keeps its gas band but the Δvap
    correction carries no sourced σ, so its ± is a LOWER BOUND. Esterification isolates it: ethanol is the SOLE
    derived species (acetic acid + ethyl acetate injected as SOURCED liquid, water is sourced liquid), all partners
    are liquid, so neither the ≥2-derived nor the phase-mixed trigger fires -- ONLY ethanol's per-record
    ``sigma_is_lower_bound`` marker can. Without the fold the flag would read False (tight) over an understated σ."""
    from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef

    tbl = DEFAULT_THERMO.with_records(
        ThermoRef("C2H4O2", "acetic acid", -484.3, 159.8, "liquid", "test-injected sourced liquid",
                  uncertainty_dhf_kj=0.5, uncertainty_s_j_per_mol_k=0.4),
        ThermoRef("C4H8O2", "ethyl acetate", -479.0, 259.4, "liquid", "test-injected sourced liquid",
                  uncertainty_dhf_kj=0.6, uncertainty_s_j_per_mol_k=0.5),
    )
    ref = resolve_thermo(ETHANOL, tbl, condensed=True)  # ethanol has a vaporization record -> corrected to liquid
    assert ref.grade == "PREDICTED" and ref.sigma_is_lower_bound is True
    # ester HYDROLYSIS (ethyl acetate + water -> ethanol + acetic acid), NOT the forward esterification: the forward
    # direction is a P1.3 domain-guarded class (aqueous free-acid dehydrative acylation -> UNKNOWN), so it would never
    # reach the σ machinery.  Hydrolysis isolates the SAME lone phase-corrected derived species (ethanol) and the σ
    # propagation is direction-symmetric, so this still exercises exactly the lower-bound flag under test.
    step = ExperimentStep.assembling(
        ETHANOL, (parse_smiles("CCOC(C)=O"), H2O), (ETHANOL, parse_smiles("CC(=O)O")),
    )
    f = feasibility_of_step(step, thermo=tbl)
    assert f.sigma_delta_g_kj is not None
    assert f.sigma_delta_g_is_lower_bound is True
    assert "LOWER BOUND" in f.reason


def test_phase_change_enthalpy_sigma_narrows_the_condensed_enthalpy_leg():
    """PHASE-CHANGE-SIGMA: ethanol's vaporization ref carries a SOURCED ΔvapH ± (0.4), so resolve_thermo makes the
    condensed ΔfH° ± the quadrature of the gas band and that ± -- strictly larger than the bare gas band, no longer
    understating the enthalpy leg. Its ΔvapS ± is None, so the S° leg keeps the gas band and the record stays flagged
    lower-bound overall (honest: one leg is still understated)."""
    gas = resolve_thermo(ETHANOL, condensed=False)
    cond = resolve_thermo(ETHANOL, condensed=True)  # ethanol has a vaporization ref carrying ΔvapH ± 0.4
    assert cond.uncertainty_dhf_kj == math.sqrt(gas.uncertainty_dhf_kj ** 2 + 0.4 ** 2)  # enthalpy leg quadratured
    assert cond.uncertainty_dhf_kj > gas.uncertainty_dhf_kj                              # strictly larger -> ± is sourced
    # honest: the effect is SMALL -- the ±0.4 is ~25x below the dominating group-additivity band (~9.8), so the
    # narrowing is ~0.008 kJ/mol.  The mechanism is correct and ready; the payoff scales with tighter gas-band data.
    assert cond.uncertainty_dhf_kj - gas.uncertainty_dhf_kj < 0.05
    assert cond.uncertainty_s_j_per_mol_k == gas.uncertainty_s_j_per_mol_k              # S° leg unchanged (ΔvapS ± None)
    assert cond.sigma_is_lower_bound is True                                            # entropy leg still understated


def test_a_fully_sourced_phase_change_sigma_lifts_the_lower_bound():
    """The lift mechanism: when a phase-change ref carries BOTH a sourced ΔH ± and a sourced ΔS ±, the condensed σ is a
    proper quadrature on both legs and the lower-bound caveat LIFTS. Demonstrated with an injected both-± ethanol
    vaporization ref -- the default seed's ΔvapS ± is None (the named THERMO-PHASE-ENTROPY-SIGMA follow-on, ΔS ± being
    not cleanly reported by free sources), so the caveat correctly stands on the default data."""
    from smartchem.data.phase_change import DEFAULT_PHASE_CHANGE, PhaseChangeRef, PhaseTransition
    gas = resolve_thermo(ETHANOL, condensed=False)
    tbl = DEFAULT_PHASE_CHANGE.with_records(
        PhaseChangeRef("C2H6O", "ethanol", PhaseTransition.VAPORIZATION, 42.3, 120.70,
                       "injected both-± vaporization", uncertainty_dh_kj_per_mol=0.4, uncertainty_ds_j_per_mol_k=1.0),
    )
    cond = resolve_thermo(ETHANOL, condensed=True, phase_change=tbl)
    assert cond.sigma_is_lower_bound is False  # BOTH legs sourced -> the caveat lifts
    assert cond.uncertainty_dhf_kj == math.sqrt(gas.uncertainty_dhf_kj ** 2 + 0.4 ** 2)
    assert cond.uncertainty_s_j_per_mol_k == math.sqrt(gas.uncertainty_s_j_per_mol_k ** 2 + 1.0 ** 2)


def test_nonphysical_negative_temperature_yields_unknown_not_negative_sigma():
    """The red-team's F3: σ(log10 K) is linear in 1/T, so a nonphysical T < 0 would flip it NEGATIVE -- a nonsense
    uncertainty. Guarded to UNKNOWN instead."""
    e = equilibrium_of_step(water_synthesis(), temperature_k=-50.0)
    assert e.sigma_log10_k is None


def test_sigma_log10_k_propagates_linearly_from_sigma_delta_g():
    """log10 K is linear in ΔG, so σ(log10 K) = σ(ΔG)·1000/(R·T·ln10); UNKNOWN when σ(ΔG) is; the lower-bound flag
    rides forward."""
    e = equilibrium_of_step(water_synthesis())
    f = feasibility_of_step(water_synthesis())
    assert e.sigma_log10_k is not None and f.sigma_delta_g_kj is not None
    expected = f.sigma_delta_g_kj * 1000.0 / (GAS_CONSTANT_J_PER_MOL_K * f.temperature_k * math.log(10.0))
    assert abs(e.sigma_log10_k - expected) < 1e-12
    assert e.sigma_log10_k_is_lower_bound is False

    methane_eq = equilibrium_of_step(methane_combustion())  # CH4's S° has no ± -> σ(ΔG) UNKNOWN
    assert methane_eq.sigma_log10_k is None  # σ(ΔG) UNKNOWN -> σ(log10 K) UNKNOWN
