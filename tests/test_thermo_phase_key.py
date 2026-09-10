"""Item 5 (Lane B·C): the phase-carrying thermo key -- a gas and a liquid record of one species coexist, a
phase-blind lookup of a dual-phase species fails CLOSED, and the frozen CODATA liquid value is mirrored exactly.
Pins the ROUND-26 M2b carried debt (a) as closed, and the FROZEN_HASH of the collider-kinetics probe as unmoved.
"""
from __future__ import annotations

from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef, ThermoTable
from smartchem.experiment.feasibility import resolve_thermo
from smartchem.smiles import parse_smiles

from experiments import thermo_phase_key_probe as probe


def test_probe_validate_holds():
    probe.validate()  # the committed demonstration: every load-bearing property of the key


def test_both_br2_phases_are_live_with_exact_values():
    g = DEFAULT_THERMO.for_formula("Br2", phase="gas")
    liq = DEFAULT_THERMO.for_formula("Br2", phase="liquid")
    assert (g.dhf_kj_per_mol, g.s_j_per_mol_k) == (30.91, 245.468)
    assert (liq.dhf_kj_per_mol, liq.s_j_per_mol_k) == (0.0, 152.21)  # bromine's reference state, ΔfH°=0


def test_phase_blind_dual_phase_fails_closed():
    # the debt: a phase-blind caller must NOT be silently handed the gas ΔfH° for what could be liquid Br₂
    assert DEFAULT_THERMO.for_formula("Br2") is None
    assert DEFAULT_THERMO.for_named("Br2", "bromine") is None


def test_resolve_thermo_br2_is_unknown_not_a_gas_borrow():
    # the closed debt, as negative space: resolve_thermo(Br₂) is a loud UNKNOWN, never +30.91 kJ/mol silently
    assert resolve_thermo(parse_smiles("BrBr")) is None


def test_with_records_no_silent_overwrite_across_phases():
    # under the OLD (formula, name) dedup key this add SILENTLY deleted the gas record; the (formula, name, phase)
    # key keeps both -- a write-time hazard sharper than the read-time miss
    base = ThermoTable((ThermoRef("X2", "sample", 10.0, 100.0, "gas", "test"),))
    ext = base.with_records(ThermoRef("X2", "sample", 0.0, 80.0, "liquid", "test"))
    assert ext.for_formula("X2", phase="gas").dhf_kj_per_mol == 10.0
    assert ext.for_formula("X2", phase="liquid").dhf_kj_per_mol == 0.0
    assert ext.for_formula("X2") is None  # phase-blind on a now-dual-phase species -> fail closed


def test_single_phase_species_unchanged_under_phase_blind_lookup():
    # a strict superset: everything that is single-phase resolves identically without a phase argument
    for f in ("H2O", "CO2", "CO", "N2", "O2", "H2", "ClH", "Cl2", "CH4", "Br"):
        assert DEFAULT_THERMO.for_formula(f) is not None


def test_derive_gate_fails_closed_on_benson_coverable_dual_phase():
    # red-team Finding 1: the phase-ambiguity fail-closed must hold at the DERIVE gate, not just the sourced
    # lookup.  Br₂ escapes the Benson estimate only by being Benson-uncoverable; a Benson-COVERABLE dual-phase
    # species (ethanol, injected gas+liquid) must STILL fail closed phase-blind -- never a silent gas estimate.
    two_phase = DEFAULT_THERMO.with_records(
        ThermoRef("C2H6O", "ethanol", -234.8, 281.6, "gas", "test gas"),
        ThermoRef("C2H6O", "ethanol", -277.6, 160.7, "liquid", "test liquid"),
    )
    et = parse_smiles("CCO")
    assert resolve_thermo(et, two_phase, phase="gas").phase == "gas"
    assert resolve_thermo(et, two_phase, phase="liquid").phase == "liquid"
    assert resolve_thermo(et, two_phase) is None            # phase-blind -> fail closed, NOT a Benson gas estimate
    assert two_phase.is_multiphase("C2H6O") is True
    assert DEFAULT_THERMO.is_multiphase("Br2") is True       # the live dual-phase species
    assert DEFAULT_THERMO.is_multiphase("H2O") is False      # single-phase (liquid only) -> derive still allowed


def test_phase_threads_to_the_step_consumer():
    # the fix Evil Morty forced: feasibility_of_step / route_net_delta_g forward `phases`, so a DECLARED gas
    # dissociation stays computable (R26 preserved) while a phase-blind Br₂ step is a loud UNKNOWN (debt closed)
    from smartchem.experiment.feasibility import feasibility_of_step
    from smartchem.experiment.step import ExperimentStep
    assert resolve_thermo(parse_smiles("BrBr"), phase="gas").dhf_kj_per_mol == 30.91
    assert resolve_thermo(parse_smiles("BrBr"), phase="liquid").dhf_kj_per_mol == 0.0
    br2, br = parse_smiles("BrBr"), parse_smiles("[Br]")
    step = ExperimentStep.assembling(br, (br2,), (br, br))
    assert abs(feasibility_of_step(step, phases={br2: "gas"}).delta_g_kj - 161.65) < 0.1
    assert feasibility_of_step(step).delta_g_kj is None  # phase-blind Br₂ step -> UNKNOWN, not a gas verdict


def test_collider_kinetics_frozen_hash_unmoved():
    # the mandatory same-commit migration (Br₂ call -> phase="gas") keeps the gas values, so ΔG₂₉₈ and the
    # probe's content hash are byte-identical -- no golden regenerated
    from experiments import dow_bromine_kinetics_probe as k
    assert k.content_hash() == k.FROZEN_HASH
    k.validate()
