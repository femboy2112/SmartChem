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
    accepted_solver_verdicts = frozenset({"ok"})          # XVII-A1: the ONLY numerical verdict this operator certifies

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
        # XVII-A1: conserving + accepted structural tier, but the NUMERICAL solve was refused (verdict not in the
        # operator's accepted set).  A mass-balanced projection whose solver refused the state is not admissible.
        if self.mode == "refused_solver":
            bad = dict(good, solver_verdict="REFUSED")
            return EquilibriumState(species_amounts={"X": tot}, structural_tier=STRUCTURALLY_CONSERVING, **bad)
        # XVII-A1 metadata forgery: the returned state claims a DIFFERENT problem than the one the world posed.
        if self.mode == "wrong_volume":
            bad = dict(good, volume_L=float(volume_L) + 1.0)
            return EquilibriumState(species_amounts={"X": tot}, structural_tier=STRUCTURALLY_CONSERVING, **bad)
        if self.mode == "wrong_temperature":
            bad = dict(good, temperature_K=float(temperature_K) + 1.0)
            return EquilibriumState(species_amounts={"X": tot}, structural_tier=STRUCTURALLY_CONSERVING, **bad)
        if self.mode == "altered_inputs":
            bad = dict(good, component_inputs={"stuff": tot + 1.0})
            return EquilibriumState(species_amounts={"X": tot}, structural_tier=STRUCTURALLY_CONSERVING, **bad)
        # XVII-A2: a projection creating 1e-7 mol -- tiny ABSOLUTELY, but enormous relative to a ~1e-12 mol trace
        # inventory.  The old 1e-6*max(1.0, totals) floor admitted it; a scale-aware tolerance must refuse it.
        if self.mode == "create_1e7":
            return EquilibriumState(species_amounts={"X": tot + 1e-7}, structural_tier=STRUCTURALLY_CONSERVING, **good)
        return EquilibriumState(species_amounts={"X": tot}, structural_tier=STRUCTURALLY_CONSERVING, **good)


# A complicit component LAW: two species X(R:1), Y(R:2) but a component_totals that counts stuff = X + Y, blind to Y's
# double R.  Re-speciating X->Y "conserves stuff" by the operator's own law while creating one R out of nothing -- a
# forgery that calling the SAME faulty law on input and output can never catch (XVII-A3).
class _UnfaithfulLawOperator(EquilibriumOperator):
    components = frozenset({"stuff"})
    species = ("X", "Y")
    species_signature = {"X": ((("R", 1),), 0), "Y": ((("R", 2),), 0)}   # HONEST per-name composition...
    accepted_solver_verdicts = frozenset({"ok"})

    def component_totals(self, species_amounts):                          # ...but a DISHONEST conservation law
        g = species_amounts.get
        return {"stuff": float(g("X", 0.0)) + float(g("Y", 0.0))}         # ignores that Y carries 2 R, not 1

    def speciate(self, component_amounts, *, volume_L, temperature_K=298.15):
        self._validate(component_amounts, volume_L, temperature_K)
        tot = float(component_amounts.get("stuff", 0.0))
        # move all "stuff" onto Y: stuff_out = 0 + tot == tot (law says conserved), but R_out = 2*tot != R_in = tot
        return EquilibriumState(
            species_amounts={"X": 0.0, "Y": tot}, volume_L=volume_L, temperature_K=temperature_K,
            component_inputs={"stuff": tot}, component_residuals={"stuff": 0.0}, derived={},
            structural_tier=STRUCTURALLY_CONSERVING, solver_verdict="ok")


def _mock_world(mode, *, init=1.0):
    coupling = EquilibriumCoupling(operator=_MockOperator(mode), species_table={"X": X})
    sysm = ChemicalSystem([X], [], volume_L=1.0)
    world = CoupledWorld([Compartment("m", sysm, equilibrium=coupling)])
    return world, {"m": {X: init}}


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


# ---------------------------------------------------------------- XVII-A1: the numerical solver verdict is a gate
def test_projection_refuses_a_solver_refused_state():
    """XVII-A1: a mass-balanced, accepted-tier projection whose WRAPPED SOLVER refused the numerical state (verdict not
    in the operator's accepted set) is NOT scientifically admissible, even though every conservation check passes."""
    world, initial = _mock_world("refused_solver")
    with pytest.raises(CoupledError):
        world.integrate(initial, duration=1.0, n_steps=2, scheme="lie")


def test_operator_without_accepted_verdicts_cannot_be_coupled():
    """Fail-closed: an operator that declares no accepted_solver_verdicts cannot have its numerical verdict judged, so
    it cannot be coupled (the admission of its solver verdict is unprovable)."""
    class _NoVerdicts(EquilibriumOperator):
        components = frozenset({"stuff"})
        species = ("X",)
        species_signature = {"X": ((("R", 1),), 0)}
        # accepted_solver_verdicts left as the empty base default
        def component_totals(self, sa):
            return {"stuff": float(sa.get("X", 0.0))}
        def speciate(self, ca, *, volume_L, temperature_K=298.15):
            return EquilibriumState(species_amounts={"X": 0.0}, volume_L=volume_L, temperature_K=temperature_K,
                                    component_inputs={}, component_residuals={}, derived={},
                                    structural_tier=STRUCTURALLY_CONSERVING, solver_verdict="ok")
    with pytest.raises(CoupledError):
        EquilibriumCoupling(operator=_NoVerdicts(), species_table={"X": X})


@pytest.mark.parametrize("mode", ["wrong_volume", "wrong_temperature", "altered_inputs"])
def test_projection_refuses_forged_metadata(mode):
    """XVII-A1: the returned state's self-reported (volume, temperature, component inputs) must match the problem the
    world actually posed; a state that claims a different problem than the one solved is refused."""
    world, initial = _mock_world(mode)
    with pytest.raises(CoupledError):
        world.integrate(initial, duration=1.0, n_steps=2, scheme="lie")


# ---------------------------------------------------------------- XVII-A2: trace-inventory conservation
def test_trace_inventory_creation_is_refused():
    """XVII-A2: a projection creating 1e-7 mol on a ~1e-12 mol trace inventory must be REFUSED.  Under the old
    1e-6*max(1.0, totals) floor the residual (1e-7) sat below tolerance and was admitted; a scale-aware tolerance
    (absolute + relative to the actual component inventory) catches it."""
    world, initial = _mock_world("create_1e7", init=1e-12)
    with pytest.raises(CoupledError):
        world.integrate(initial, duration=1.0, n_steps=2, scheme="lie")


def test_small_but_real_inventory_still_admitted():
    """Control for A2: the SAME good operator on a small (but not trace) inventory is still admitted -- the tighter
    tolerance refuses fabricated material, it does not refuse an honest small solve."""
    world, initial = _mock_world("good", init=1e-3)
    traj = world.integrate(initial, duration=1.0, n_steps=2, scheme="lie")
    assert traj.receipt.structural_tier == STRUCTURALLY_CONSERVING
    assert abs(traj.amounts["m"][-1][X] - 1e-3) < 1e-9 * 1e-3 + 1e-15


# ---------------------------------------------------------------- XVII-A3: independent elemental closure
def test_complicit_component_law_is_caught_by_independent_elemental_closure():
    """XVII-A3: an operator whose component_totals LAW is itself wrong (counts stuff = X + Y, blind to Y's 2 R) makes
    the input and output component checks AGREE on a false invariant.  The world's INDEPENDENT closure -- the kernel's
    exact element/charge map, which does not consult the operator's law -- catches the fabricated R and refuses."""
    Y = Species.of("Y", {"R": 2}, charge=0, phase=Phase.AQUEOUS)
    coupling = EquilibriumCoupling(operator=_UnfaithfulLawOperator(), species_table={"X": X, "Y": Y})
    sysm = ChemicalSystem([X, Y], [], volume_L=1.0)
    world = CoupledWorld([Compartment("m", sysm, equilibrium=coupling)])
    with pytest.raises(CoupledError):
        world.integrate({"m": {X: 1.0, Y: 0.0}}, duration=1.0, n_steps=2, scheme="lie")


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
