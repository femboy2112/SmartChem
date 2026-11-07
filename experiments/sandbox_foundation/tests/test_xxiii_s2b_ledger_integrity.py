"""OPERATION XXIII section 2b -- ledger integrity: five false certifications, excised one at a time.

Each section is a RED test distilled from a red-team repro (it failed on 8783f19, assertion text recorded in the commit
that fixes it) plus a NEGATIVE control proving the legitimate case still certifies -- a guard that refuses everything
is not a fix, it is an amputation.

  F1  a rebound ``ChemicalSystem.reactions`` ran different kinetics under an unchanged kernel + world certificate.
  F2  an equilibrium operator's solve parameters (``include_ion_pair``) sat outside the world certificate.
  F3  a selective single-ion transfer left compartments at +/-0.49 mol net charge, receipted "CONSERVED".
  F4  the ledger baseline was taken AFTER the t=0 projection, so a projection that deleted a trace component was
      absorbed into the baseline and then "verified" against itself.
  F5  a NEUTRAL multivalent inventory's charge verdict depended on float roundoff of its net (scale = |sum z n|).
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.claim_tiers import REFUSED, STRUCTURALLY_CONSERVING, UNVERIFIED, rank
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    ElectroneutralBulkExchange,
    EquilibriumCoupling,
    InterfaceTransfer,
)
from experiments.sandbox_foundation.general_equilibrium import (
    AcetateWaterEquilibriumOperator,
    EquilibriumOperator,
    EquilibriumState,
    MixedAcetateCarbonateEquilibriumOperator,
)
from experiments.sandbox_foundation.general_kernel import (
    MassActionIrreversible,
    Phase,
    Reaction,
    Species,
    StaleCertificateError,
    ChemicalSystem,
)

# ===================================================================================================== F1 rebind
_A = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS)
_B = Species.of("B", {"X": 1}, 0, Phase.AQUEOUS)
_LAW = MassActionIrreversible(k=1.0)


def _f1_build():
    s = ChemicalSystem([_A, _B], [Reaction("A->B", ((_A, -1), (_B, 1)), _LAW)], volume_L=1.0)
    return s, CoupledWorld([Compartment("c", s)])


def _f1_hostile_rebind(s):
    # same name, same sealed audited law -- but the stoichiometry now says 2A -> 2B (a second-order rate)
    s.reactions = (Reaction("A->B", ((_A, -2), (_B, 2)), _LAW),)


class TestF1ReactionRebind:
    def test_rebind_moves_the_kernel_certificate(self):
        s, _ = _f1_build()
        cert = s._model_certificate
        _f1_hostile_rebind(s)
        assert s._compute_certificate() != cert

    def test_rebind_is_refused_on_the_kernel_path(self):
        s, _ = _f1_build()
        _f1_hostile_rebind(s)
        with pytest.raises(StaleCertificateError):
            s.integrate({_A: 0.1}, duration=1.0)

    def test_rebind_is_refused_on_the_coupled_path(self):
        s, w = _f1_build()
        _f1_hostile_rebind(s)
        with pytest.raises(StaleCertificateError):
            w.integrate({"c": {_A: 0.1}}, duration=1.0, n_steps=4, require_certified_execution=True)

    def test_rate_law_swap_with_identical_stoichiometry_is_refused_on_the_kernel_path(self):
        s, _ = _f1_build()
        s.reactions = (Reaction("A->B", ((_A, -1), (_B, 1)), MassActionIrreversible(k=10.0)),)
        with pytest.raises(StaleCertificateError):
            s.integrate({_A: 0.1}, duration=1.0)

    def test_resealing_the_certificate_does_not_relicense_a_stale_stoichiometric_matrix(self):
        # an attacker who rebinds reactions AND recomputes the hash still cannot run: the stored N (the matrix the
        # integer conservation proof was made over) no longer matches the N the CURRENT reactions re-derive to.
        s, w = _f1_build()
        _f1_hostile_rebind(s)
        s._model_certificate = s._compute_certificate()
        with pytest.raises(StaleCertificateError):
            s.integrate({_A: 0.1}, duration=1.0)
        with pytest.raises(StaleCertificateError):
            w.integrate({"c": {_A: 0.1}}, duration=1.0, n_steps=4)

    def test_control_an_untouched_system_integrates_certified_on_both_paths(self):
        s, w = _f1_build()
        k = s.integrate({_A: 0.1}, duration=1.0)
        assert k.receipt.structural_tier == STRUCTURALLY_CONSERVING
        assert k.amounts[-1][_A] == pytest.approx(0.1 * 2.718281828459045 ** -1, rel=1e-6)
        tr = w.integrate({"c": {_A: 0.1}}, duration=1.0, n_steps=20, require_certified_execution=True)
        assert tr.receipt.execution_identity_certified is True
        assert tr.receipt.structural_tier == STRUCTURALLY_CONSERVING


# ===================================================================================================== F2 operator
_SIG = AcetateWaterEquilibriumOperator.species_signature
_SP = {nm: Species.of(nm, dict(_SIG[nm][0]), _SIG[nm][1], Phase.AQUEOUS) for nm in _SIG}
_F2_INIT = {"c": {_SP["HAc"]: 0.2, _SP["Na+"]: 0.1}}


def _f2_world(op):
    ec = EquilibriumCoupling(op, dict(_SP), reservoir_components=frozenset({"H", "O", "charge"}))
    return CoupledWorld([Compartment("c", ChemicalSystem(list(_SP.values()), [], volume_L=1.0), equilibrium=ec)])


class _AcetateSubclassNoOwnDescriptor(AcetateWaterEquilibriumOperator):
    """Inherits descriptor() but overrides the solve -- the inherited descriptor does not describe THIS physics."""

    def speciate(self, component_amounts, *, volume_L, temperature_K=298.15):
        return super().speciate(component_amounts, volume_L=volume_L, temperature_K=temperature_K)


class _BareOperator(EquilibriumOperator):
    """A minimal conserving operator with NO descriptor(): its solve parameters are unbindable."""
    components = frozenset({"x"})
    species = ("X",)
    species_signature = {"X": ((("Q", 1),), 0)}
    accepted_solver_verdicts = frozenset({"ok"})

    def speciate(self, component_amounts, *, volume_L, temperature_K=298.15):
        tot = float(component_amounts.get("x", 0.0))
        return EquilibriumState(species_amounts={"X": tot}, volume_L=volume_L, temperature_K=temperature_K,
                                component_inputs=dict(component_amounts), component_residuals={}, derived={},
                                structural_tier=STRUCTURALLY_CONSERVING, solver_verdict="ok")

    def component_totals(self, species_amounts):
        return {"x": species_amounts.get("X", 0.0)}


class TestF2EquilibriumOperatorDescriptor:
    def test_two_physically_distinct_worlds_no_longer_share_a_certificate(self):
        w_off = _f2_world(AcetateWaterEquilibriumOperator(activity_model="davies", include_ion_pair=False))
        w_on = _f2_world(AcetateWaterEquilibriumOperator(activity_model="davies", include_ion_pair=True))
        assert w_off._world_certificate != w_on._world_certificate

    def test_post_construction_ion_pair_toggle_is_refused(self):
        op = AcetateWaterEquilibriumOperator(activity_model="davies", include_ion_pair=False)
        w = _f2_world(op)
        op.include_ion_pair = True
        with pytest.raises(StaleCertificateError):
            w.integrate(_F2_INIT, duration=1.0, n_steps=2, require_certified_execution=True)

    def test_post_construction_activity_model_toggle_on_the_mixed_operator_is_refused(self):
        op = MixedAcetateCarbonateEquilibriumOperator(activity_model="davies")
        tab = {nm: Species.of(nm, dict(sig[0]), sig[1], Phase.AQUEOUS)
               for nm, sig in MixedAcetateCarbonateEquilibriumOperator.species_signature.items()}
        ec = EquilibriumCoupling(op, tab, reservoir_components=frozenset({"H", "O", "charge"}))
        w = CoupledWorld([Compartment("c", ChemicalSystem(list(tab.values()), [], 1.0), equilibrium=ec)])
        op.activity_model = "ideal"
        with pytest.raises(StaleCertificateError):
            w.integrate({"c": {tab["HAc"]: 0.1}}, duration=1.0, n_steps=1)

    @pytest.mark.parametrize("op_factory", [_BareOperator, _AcetateSubclassNoOwnDescriptor])
    def test_an_operator_without_its_own_descriptor_voids_the_execution_identity(self, op_factory):
        op = op_factory()
        if isinstance(op, _BareOperator):
            X = Species.of("X", {"Q": 1}, 0, Phase.AQUEOUS)
            ec = EquilibriumCoupling(op, {"X": X})
            w = CoupledWorld([Compartment("c", ChemicalSystem([X], [], 1.0), equilibrium=ec)])
            init = {"c": {X: 1.0}}
        else:
            w, init = _f2_world(op), _F2_INIT
        tr = w.integrate(init, duration=1.0, n_steps=1)
        assert tr.receipt.execution_identity_certified is False
        assert tr.receipt.execution_identity_basis == "UNVERIFIED"
        assert rank(tr.receipt.admitted_tier) == rank(UNVERIFIED)          # floored (weakest() canonicalises the synonym)
        assert any("equilibrium operator" in c for c in tr.caveats)
        with pytest.raises(CoupledError):
            w.integrate(init, duration=1.0, n_steps=1, require_certified_execution=True)

    def test_control_an_untouched_in_tree_operator_integrates_certified(self):
        w = _f2_world(AcetateWaterEquilibriumOperator(activity_model="davies", include_ion_pair=True))
        tr = w.integrate(_F2_INIT, duration=1.0, n_steps=2, require_certified_execution=True)
        assert tr.receipt.execution_identity_certified is True
        assert tr.receipt.execution_identity_basis == "AUDITED_BUILTIN"
        assert tr.receipt.structural_tier == STRUCTURALLY_CONSERVING
        assert tr.amounts["c"][-1][_SP["NaAc"]] > 0.0                    # the ion pair actually ran


# ===================================================================================================== F3 local charge
_Na = Species.of("Na+", {"Na": 1}, 1, Phase.AQUEOUS)
_Cl = Species.of("Cl-", {"Cl": 1}, -1, Phase.AQUEOUS)


def _f3_cells():
    return [Compartment(n, ChemicalSystem([_Na, _Cl], [], volume_L=1.0)) for n in ("A", "B")]


class TestF3LocalElectroneutrality:
    def test_selective_single_ion_interface_is_not_receipted_conserved(self):
        w = CoupledWorld(_f3_cells(), interfaces=[InterfaceTransfer("na_only", "A", "B", _Na, _Na, k_transfer=1.0)])
        tr = w.integrate({"A": {_Na: 1.0, _Cl: 1.0}, "B": {}}, duration=2.0, n_steps=8)
        r = tr.receipt
        assert r.local_electroneutrality_held is False
        assert r.compartment_max_net_charge["A"] > 0.4 and r.compartment_max_net_charge["B"] > 0.4
        assert r.compartment_max_charge_separation["A"] > 0.4 and r.compartment_max_charge_separation["B"] > 0.4
        assert r.charge_balance_claim.startswith("GLOBAL_ONLY_LOCAL_VIOLATED")
        assert not r.charge_balance_claim.startswith("CONSERVED")
        assert rank(r.admitted_tier) == rank(REFUSED) and r.structural_tier == REFUSED
        assert r.material_balance_closed is True                         # GLOBAL charge still closes -- separate facet
        assert any("'A'" in c and "electroneutral" in c for c in tr.caveats)
        assert any("na_only" in c and "charged species" in c for c in tr.caveats)

    def test_bulk_exchange_fed_from_a_non_neutral_compartment_is_refused(self):
        w = CoupledWorld(_f3_cells(),
                         bulk_exchanges=[ElectroneutralBulkExchange("bx", "A", "B", ((_Na, _Na), (_Cl, _Cl)), 1.0)])
        tr = w.integrate({"A": {_Na: 1.0}, "B": {_Na: 0.5, _Cl: 0.5}}, duration=2.0, n_steps=8)
        r = tr.receipt
        assert r.local_electroneutrality_held is False
        assert r.charge_balance_claim.startswith("GLOBAL_ONLY_LOCAL_VIOLATED")
        assert rank(r.admitted_tier) == rank(REFUSED)

    def test_control_neutral_complete_bulk_exchange_stays_certified(self):
        w = CoupledWorld(_f3_cells(),
                         bulk_exchanges=[ElectroneutralBulkExchange("bx", "A", "B", ((_Na, _Na), (_Cl, _Cl)), 1.0)])
        tr = w.integrate({"A": {_Na: 1.0, _Cl: 1.0}, "B": {_Na: 0.1, _Cl: 0.1}}, duration=2.0, n_steps=8)
        r = tr.receipt
        assert r.local_electroneutrality_held is True
        assert r.charge_balance_claim.startswith("CONSERVED")
        assert r.structural_tier == STRUCTURALLY_CONSERVING
        assert set(r.compartment_max_net_charge) == {"A", "B"}
        assert max(r.compartment_max_net_charge.values()) < 1e-12
        assert not any("charged species" in c for c in tr.caveats)

    def test_a_declared_non_neutral_input_is_reported_but_is_not_a_separation(self):
        # the judged quantity is SEPARATION (charge the dynamics moved), not the input's own imbalance: one beaker seeded
        # with a bare anion (the categorical bridge emits no spectator) is caveated and its absolute charge reported, but
        # its charge-conserving kinetics are not refused (E N = 0 cannot separate charge within one compartment).
        Ac = Species.of("Ac-", {"C": 2, "H": 3, "O": 2}, -1, Phase.AQUEOUS)
        HAc = Species.of("HAc", {"C": 2, "H": 4, "O": 2}, 0, Phase.AQUEOUS)
        Hp = Species.of("H+", {"H": 1}, 1, Phase.AQUEOUS)
        rx = Reaction("diss", ((HAc, -1), (Ac, 1), (Hp, 1)), MassActionIrreversible(k=0.1))
        w = CoupledWorld([Compartment("c", ChemicalSystem([HAc, Ac, Hp], [rx], 1.0))])
        tr = w.integrate({"c": {HAc: 1.0, Ac: 1.0}}, duration=1.0, n_steps=4)
        r = tr.receipt
        assert r.local_electroneutrality_held is True
        assert r.structural_tier == STRUCTURALLY_CONSERVING
        assert r.compartment_max_net_charge["c"] == pytest.approx(1.0)
        assert r.compartment_max_charge_separation["c"] < 1e-12
        assert any("START non-electroneutral" in c and "'c'" in c for c in tr.caveats)

    @pytest.mark.parametrize("mode", ("closed", "membrane", "bulk"))
    def test_control_the_reactor_modes_stay_locally_neutral_and_certified(self, mode):
        from experiments.sandbox_foundation.general_reactor_demo import run_reactor
        tr, _sp, _p = run_reactor(mode, duration=30.0, n_steps=30)
        r = tr.receipt
        assert r.local_electroneutrality_held is True
        assert r.structural_tier == STRUCTURALLY_CONSERVING
        assert not r.charge_balance_claim.startswith("GLOBAL_ONLY_LOCAL_VIOLATED")


# ===================================================================================================== F4 t=0 baseline
_BULK = Species.of("BULK", {"Q": 1}, 0, Phase.AQUEOUS)
_TRACE = Species.of("TRACE", {"Z": 1}, 0, Phase.AQUEOUS)


class _LossyOp(EquilibriumOperator):
    """Deletes the trace component -- within the compartment-max admission tol, so the projection is admitted."""
    components = frozenset({"bulk", "trace"})
    species = ("BULK", "TRACE")
    species_signature = {"BULK": ((("Q", 1),), 0), "TRACE": ((("Z", 1),), 0)}
    accepted_solver_verdicts = frozenset({"SOLVED"})
    activity_model = "ideal"

    def speciate(self, ca, *, volume_L, temperature_K=298.15):
        return EquilibriumState(species_amounts={"BULK": ca["bulk"], "TRACE": 0.0}, volume_L=volume_L,
                                temperature_K=temperature_K, component_inputs=dict(ca), component_residuals={},
                                derived={}, structural_tier=STRUCTURALLY_CONSERVING, solver_verdict="SOLVED")

    def component_totals(self, sa):
        return {"bulk": sa.get("BULK", 0.0), "trace": sa.get("TRACE", 0.0)}


class TestF4DeclaredBaseline:
    def test_a_t0_projection_that_deletes_a_trace_component_is_violated_not_absorbed(self):
        w = CoupledWorld([Compartment("c", ChemicalSystem([_BULK, _TRACE], [], volume_L=1.0),
                                      equilibrium=EquilibriumCoupling(_LossyOp(), {"BULK": _BULK, "TRACE": _TRACE}))])
        tr = w.integrate({"c": {_BULK: 1.0, _TRACE: 5e-10}}, duration=1.0, n_steps=5)
        r = tr.receipt
        assert r.component_resolution["Z"] == "VIOLATED"
        assert r.material_balance_closed is False
        assert r.structural_tier == REFUSED
        assert r.component_max_residual["Z"] == pytest.approx(5e-10, rel=1e-9)
        assert r.first_violation[:2] == (0.0, "material_ledger") and r.first_violation[3] == "Z"
        assert r.raw_material_change["Z"] == pytest.approx(-5e-10, rel=1e-9)   # measured vs the DECLARED state

    @pytest.mark.parametrize("trace", (1e-9, 1e-11, 1e-13))
    def test_control_the_real_mixed_operator_keeps_a_trace_carbon_certified(self, trace):
        from experiments.sandbox_foundation.unified_chemical_world import _build_species, _liquid_species_table
        sp = _build_species()
        tab = _liquid_species_table(sp)
        w = CoupledWorld([Compartment("c", ChemicalSystem(list(tab.values()), [], 1.0), EquilibriumCoupling(
            MixedAcetateCarbonateEquilibriumOperator(), tab, frozenset({"H", "O", "charge"})))])
        tr = w.integrate({"c": {sp.HAc: 0.2, sp.Nap: 0.1, sp.HCO3: trace}}, duration=1.0, n_steps=2)
        assert tr.receipt.component_resolution["C"] == "VERIFIED_WITHIN_RESOLUTION"
        assert tr.receipt.material_balance_closed is True
        assert tr.receipt.structural_tier == STRUCTURALLY_CONSERVING


