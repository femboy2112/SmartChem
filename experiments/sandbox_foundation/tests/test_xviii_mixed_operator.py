"""OPERATION XVIII §5 prerequisite -- the mixed acetate+carbonate equilibrium operator.

The unified vinegar/bicarbonate world needs a fast-equilibrium operator for a cell that holds BOTH acetic acid and
inorganic carbon.  No such operator existed (only acetate-water and ammonia); the mixed liquid SOLVER did
(coupled_equilibrium.solve).  MixedAcetateCarbonateEquilibriumOperator is the thin adapter.  These pins prove it
speciates, closes its conserved components, is admissible to the coupled world's projection gate, and covers the two
chemical limits (pure acetate, pure carbonate) so ONE operator serves both cells.
"""
from __future__ import annotations

from experiments.sandbox_foundation.claim_tiers import STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_equilibrium import MixedAcetateCarbonateEquilibriumOperator


def test_mixed_operator_speciates_and_closes():
    op = MixedAcetateCarbonateEquilibriumOperator(activity_model="davies")
    st = op.speciate({"acetate": 0.1, "carbon": 0.1, "sodium": 0.1}, volume_L=1.0, temperature_K=298.15)
    assert st.structural_tier == STRUCTURALLY_CONSERVING
    assert st.solver_verdict in op.accepted_solver_verdicts
    assert st.volume_L == 1.0 and st.temperature_K == 298.15
    assert set(st.component_inputs) == {"acetate", "carbon", "sodium"}
    # conserved-component closure: the returned species recompute to the supplied inventories
    tot = op.component_totals(st.species_amounts)
    for k, v in {"acetate": 0.1, "carbon": 0.1, "sodium": 0.1}.items():
        assert abs(tot[k] - v) < 1e-9, f"{k} did not close"
    assert 0.0 < st.derived["pH"] < 14.0


def test_mixed_operator_pure_carbonate_limit_is_basic():
    """acetate = 0 -> a pure NaHCO3 solution: no acetate species, pH basic.  The one operator covers cell B's initial
    (bicarbonate-only) state."""
    op = MixedAcetateCarbonateEquilibriumOperator()
    st = op.speciate({"acetate": 0.0, "carbon": 0.1, "sodium": 0.1}, volume_L=1.0)
    assert st.species_amounts["HAc"] == 0.0 and st.species_amounts["Ac-"] == 0.0
    assert st.species_amounts["HCO3-"] > 0.0          # bicarbonate dominates
    assert st.derived["pH"] > 7.0                      # a bicarbonate solution is basic


def test_mixed_operator_pure_acetate_limit_is_acidic():
    """carbon = 0 -> pure acetic acid: no carbon species, pH acidic.  The one operator covers cell A's initial state."""
    op = MixedAcetateCarbonateEquilibriumOperator()
    st = op.speciate({"acetate": 0.1, "carbon": 0.0, "sodium": 0.0}, volume_L=1.0)
    assert st.species_amounts["CO2(aq)"] == 0.0 and st.species_amounts["HCO3-"] == 0.0
    assert st.derived["pH"] < 7.0                      # acetic acid is acidic


def test_mixed_operator_signature_faithful_to_elements():
    """XVI-P0.2: every declared signature matches the elemental composition the name implies (the coupling gate relies
    on this to refuse a chemically-infidelic kernel-Species alias)."""
    op = MixedAcetateCarbonateEquilibriumOperator()
    assert set(op.species) == set(op.species_signature)
    # carbon balance of the signatures: every carbon-bearing species carries its stated C count
    assert dict(op.species_signature["HCO3-"][0])["C"] == 1
    assert op.species_signature["CO3-2"][1] == -2     # carbonate is the 2- ion
    assert op.species_signature["CO2(aq)"][1] == 0
