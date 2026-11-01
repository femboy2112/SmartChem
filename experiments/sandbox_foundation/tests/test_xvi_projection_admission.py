"""OPERATION XVI P0.2 -- make the fast-equilibrium projection a CERTIFIED operation.

CoupledWorld._project installed an operator's returned species vector WITHOUT checking its structural tier, its
solver verdict, its component closure, or even that the required species were present and finite.  An equilibrium
operator could therefore LAUNDER an invalid, misidentified or numerically-refused state into an admitted, certified
world.  The repair (XVI-P0.2): a fail-closed admission gate that the WORLD evaluates itself -- it does not trust the
operator's self-reported residuals; it recomputes the conserved-component closure from the RETURNED species -- plus
EquilibriumCoupling hardening that refuses a non-injective or chemically-unfaithful species_table.

RED on the pre-XVI code (which installs whatever the operator returns); GREEN after the gate.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.claim_tiers import REFUSED, STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    EquilibriumCoupling,
)
from experiments.sandbox_foundation.general_coupled_demo import (
    _ACETATE_TABLE,
    build_acetate_buffer_world,
)
from experiments.sandbox_foundation.general_equilibrium import (
    AcetateWaterEquilibriumOperator,
    EquilibriumOperator,
    EquilibriumState,
)
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Species

X = Species.of("X", {"R": 1}, charge=0, phase=Phase.AQUEOUS)


# ---------------------------------------------------------------- a controlled operator that returns a chosen bad state
class _MockOperator(EquilibriumOperator):
    components = frozenset({"stuff"})
    species = ("X",)
    species_signature = {"X": ((("R", 1),), 0)}

    def __init__(self, mode):
        self.mode = mode

    def component_totals(self, species_amounts):
        return {"stuff": float(species_amounts.get("X", 0.0))}

    def speciate(self, component_amounts, *, volume_L, temperature_K=298.15):
        self._validate(component_amounts, volume_L, temperature_K)
        tot = float(component_amounts.get("stuff", 0.0))
        good = dict(volume_L=volume_L, temperature_K=temperature_K, component_inputs={"stuff": tot},
                    component_residuals={"stuff": 0.0}, derived={}, solver_verdict="ok")
        if self.mode == "refused":          # finite, plausible values, but the solve is REFUSED
            return EquilibriumState(species_amounts={"X": tot}, structural_tier=REFUSED, **good)
        if self.mode == "nonconserving":     # LIES: self-reports residual 0 but actually creates 1 mol of material
            return EquilibriumState(species_amounts={"X": tot + 1.0}, structural_tier=STRUCTURALLY_CONSERVING, **good)
        if self.mode == "missing":           # mismatched species map: required species absent
            return EquilibriumState(species_amounts={}, structural_tier=STRUCTURALLY_CONSERVING, **good)
        if self.mode == "negative":
            return EquilibriumState(species_amounts={"X": -5.0}, structural_tier=STRUCTURALLY_CONSERVING, **good)
        if self.mode == "nonfinite":
            return EquilibriumState(species_amounts={"X": float("nan")}, structural_tier=STRUCTURALLY_CONSERVING, **good)
        return EquilibriumState(species_amounts={"X": tot}, structural_tier=STRUCTURALLY_CONSERVING, **good)


def _mock_world(mode):
    coupling = EquilibriumCoupling(operator=_MockOperator(mode), species_table={"X": X})
    sysm = ChemicalSystem([X], [], volume_L=1.0)
    world = CoupledWorld([Compartment("m", sysm, equilibrium=coupling)])
    return world, {"m": {X: 1.0}}


@pytest.mark.parametrize("mode", ["refused", "nonconserving", "missing", "negative", "nonfinite"])
def test_projection_refuses_a_bad_operator_result(mode):
    """A controlled operator returning a refused / non-conserving / incomplete / non-finite / negative vector must be
    REFUSED by the world -- it cannot launder that state into an admitted trajectory."""
    world, initial = _mock_world(mode)
    with pytest.raises(CoupledError):
        world.integrate(initial, duration=1.0, n_steps=2, scheme="lie")


def test_projection_admits_a_good_operator_result():
    """The control: a well-behaved mock operator (conserving, complete, finite, accepted tier) IS admitted."""
    world, initial = _mock_world("good")
    traj = world.integrate(initial, duration=1.0, n_steps=2, scheme="lie")
    assert traj.receipt.structural_tier == STRUCTURALLY_CONSERVING
    assert abs(traj.amounts["m"][-1][X] - 1.0) < 1e-9       # the single component is conserved through the projection


# ---------------------------------------------------------------- species_table hardening (at coupling construction)
def test_noninjective_species_table_is_refused():
    """Two operator species mapped to ONE kernel Species would merge distinct chemistry -- refused."""
    bad = dict(_ACETATE_TABLE)
    bad["Ac-"] = bad["HAc"]                                  # alias Ac- onto HAc
    with pytest.raises(CoupledError):
        EquilibriumCoupling(operator=AcetateWaterEquilibriumOperator(), species_table=bad,
                            reservoir_components=frozenset({"H", "O", "charge"}))


def test_unfaithful_species_table_is_refused():
    """A name mapped to a chemically incompatible Species (H+ -> a Na+ species) is refused by the signature check."""
    bad = dict(_ACETATE_TABLE)
    bad["H+"] = Species.of("not-a-proton", {"Na": 1}, charge=1, phase=Phase.AQUEOUS)
    with pytest.raises(CoupledError):
        EquilibriumCoupling(operator=AcetateWaterEquilibriumOperator(), species_table=bad,
                            reservoir_components=frozenset({"H", "O", "charge"}))


def test_operator_without_signature_cannot_be_coupled():
    """Fail-closed: an operator that declares no species_signature cannot have its table verified faithful -> refused."""
    class _NoSig(EquilibriumOperator):
        components = frozenset({"stuff"})
        species = ("X",)
        # species_signature left as the empty base default
        def component_totals(self, sa):
            return {"stuff": float(sa.get("X", 0.0))}
        def speciate(self, ca, *, volume_L, temperature_K=298.15):
            return EquilibriumState(species_amounts={"X": 0.0}, volume_L=volume_L, temperature_K=temperature_K,
                                    component_inputs={}, component_residuals={}, derived={},
                                    structural_tier=STRUCTURALLY_CONSERVING, solver_verdict="ok")
    with pytest.raises(CoupledError):
        EquilibriumCoupling(operator=_NoSig(), species_table={"X": X})


# ---------------------------------------------------------------- positive controls: the real projection still works
def test_real_acetate_projection_still_runs_and_is_idempotent():
    """The verified acetate projection is admitted, and P(P(n)) == P(n) (an admitted projection is idempotent)."""
    world, _sys, _coupling, initial = build_acetate_buffer_world()
    traj = world.integrate(initial, duration=50.0, n_steps=100, scheme="strang")
    assert traj.receipt.structural_tier == STRUCTURALLY_CONSERVING
    y = world._pack(initial)
    y1 = world._project(y)
    y2 = world._project(y1)
    import numpy as np
    assert float(np.max(np.abs(y2 - y1))) < 1e-9            # idempotent on the admitted domain
