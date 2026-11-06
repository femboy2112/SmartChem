"""OPERATION XV Wave B (P1) -- the EquilibriumOperator architecture gate.

The load-bearing pin: the EXISTING, already-verified aqueous equilibrium solver runs as a CONSUMER of the general
EquilibriumOperator interface through a thin adapter, with its numerics PRESERVED (not re-derived), keyed on
conserved-component inventories so it composes with the kernel's E n totals.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation import aqueous_equilibrium
from experiments.sandbox_foundation.claim_tiers import STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_equilibrium import (
    AcetateWaterEquilibriumOperator,
    EquilibriumError,
)


def test_adapter_reproduces_the_verified_solver_through_the_general_interface():
    # THE GATE: the general interface returns EXACTLY the verified solver's speciation (converted mol = conc x V),
    # never a re-derivation. 0.1 mol acetate in 1 L == the curated 0.1 M AcetateWaterSystem.
    op = AcetateWaterEquilibriumOperator(activity_model="ideal")
    V = 1.0
    st = op.speciate({"acetate": 0.1, "sodium": 0.0}, volume_L=V, temperature_K=298.15)
    direct = aqueous_equilibrium.solve(aqueous_equilibrium.AcetateWaterSystem(total_acetic_M=0.1, sodium_M=0.0))
    assert abs(st.species_amounts["H+"] - direct.h_plus_M * V) < 1e-15
    assert abs(st.species_amounts["Ac-"] - direct.ac_minus_M * V) < 1e-15
    assert abs(st.species_amounts["HAc"] - direct.hac_M * V) < 1e-15
    assert abs(st.derived["pH"] - direct.pH) < 1e-15
    assert st.solver_verdict == direct.verdict                       # the wrapped solver's provenance is passed through


def test_fast_equilibrium_conservation_closes():
    op = AcetateWaterEquilibriumOperator()
    st = op.speciate({"acetate": 0.1, "sodium": 0.05}, volume_L=2.0)   # NaAc-like: acetate AND sodium present
    assert st.component_residuals["acetate"] < 1e-9                   # HAc + Ac- + NaAc == total acetate in
    assert st.component_residuals["sodium"] < 1e-9                    # Na+ + NaAc == total sodium in
    assert st.structural_tier == STRUCTURALLY_CONSERVING


def test_operator_is_volume_aware():
    # identical CONCENTRATION (0.1 M) as 0.1 mol/1 L and 1.0 mol/10 L must give equal concentrations; amounts x10.
    op = AcetateWaterEquilibriumOperator()
    s1 = op.speciate({"acetate": 0.1}, volume_L=1.0)
    s10 = op.speciate({"acetate": 1.0}, volume_L=10.0)
    assert abs(s1.species_amounts["H+"] / 1.0 - s10.species_amounts["H+"] / 10.0) < 1e-12
    assert abs(s10.species_amounts["Ac-"] - 10.0 * s1.species_amounts["Ac-"]) < 1e-9


def test_unknown_component_and_bad_volume_are_refused():
    op = AcetateWaterEquilibriumOperator()
    with pytest.raises(EquilibriumError):
        op.speciate({"carbon": 0.1}, volume_L=1.0)                   # carbon not modelled here -> refuse, never ignore
    with pytest.raises(EquilibriumError):
        op.speciate({"acetate": 0.1}, volume_L=0.0)
    with pytest.raises(EquilibriumError):
        op.speciate({"acetate": -0.1}, volume_L=1.0)


def test_operator_declares_its_components_and_species():
    op = AcetateWaterEquilibriumOperator()
    assert op.components == frozenset({"acetate", "sodium"})
    assert set(op.species) == {"HAc", "Ac-", "H+", "OH-", "Na+", "NaAc"}
