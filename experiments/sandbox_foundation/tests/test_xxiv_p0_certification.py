"""OPERATION XXIV Phase I/II -- regression tests for the five P0 certification-gap repairs.

The predeclared probes (``xxiv_p0_probes.py``) FAIL on 7314e2a (receipt ``benchmarks/p0_xxiv/RED_receipt_7314e2a.json``)
and PASS here.  These tests pin each repair with positive, negative, null and mutation controls.
"""
from __future__ import annotations

import numpy as np
import pytest

from experiments.sandbox_foundation import admissibility as adm
from experiments.sandbox_foundation import general_equilibrium as ge
from experiments.sandbox_foundation import general_kernel as gk
from experiments.sandbox_foundation import xxiv_p0_probes as probes
from experiments.sandbox_foundation.aqueous_equilibrium import SourcedConstant
from experiments.sandbox_foundation.claim_tiers import REFUSED, STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_coupled import (Compartment, CoupledError, CoupledSourceDomainError,
                                                            CoupledWorld, EquilibriumCoupling, ExternalBoundary)
from experiments.sandbox_foundation.general_equilibrium import AcetateWaterEquilibriumOperator
from experiments.sandbox_foundation.general_kernel import (ChemicalSystem, MassActionIrreversible, Phase, Reaction,
                                                           SourceDomainError, Species, StaleCertificateError)

AQ = Phase.AQUEOUS


# ============================================================================================ the predeclared probes
@pytest.mark.parametrize("name", ["probe_f2", "probe_p6b", "probe_charge", "probe_temperature"])
def test_predeclared_probe_passes(name):
    assert getattr(probes, name)()["verdict"] == "PASS"


def test_predeclared_closure_probe_passes_and_its_control_demotes():
    r = probes.probe_closure()
    assert r["verdict"] == "PASS"
    assert r["control_demoted"] is True
    assert r["baseline"]["audit_status"] == "SEALED" and r["baseline"]["certificates_equal"] is False
    assert "audit-closure sha256" in r["helper_edit"]["audit_status"]


# ============================================================================================ 1A operator authority
class _Attested(probes.TwoIsomerOperator):
    """A plugin operator whose descriptor DOES bind frac (attested by its author)."""

    def descriptor(self) -> list:
        return self._class_descriptor() + [["frac", repr(self.frac)]]

    def speciate(self, component_amounts, *, volume_L, temperature_K=298.15):
        return probes.TwoIsomerOperator.speciate(self, component_amounts, volume_L=volume_L,
                                                 temperature_K=temperature_K)


ge.register_attested_equilibrium_operator(_Attested, attested_by="xxiv-test-lab")


def _iso_world(op):
    return CoupledWorld([probes._iso_compartment("c", op)])


class TestOperatorAuthority:
    def test_in_tree_operators_are_sealed_against_the_closed_table(self):
        assert set(ge.operator_audit_status().values()) == {"SEALED"}
        assert ge.equilibrium_operator_authority(AcetateWaterEquilibriumOperator()) == gk.AUDITED_BUILTIN

    def test_operator_pins_are_a_regression_anchor(self):
        for (mod, qual), pin in ge._AUDITED_OPERATOR_PINS.items():
            cls = getattr(ge, qual)
            assert gk._audit_closure(cls)[0] == pin, f"{qual} or a dependency changed: re-audit and re-pin"

    def test_the_operator_closure_covers_the_wrapped_solver(self):
        hashed = {(m.rsplit(".", 1)[-1], n) for m, n, _ in gk.audit_closure_inventory(AcetateWaterEquilibriumOperator)["hashed"]}
        assert ("aqueous_equilibrium", "solve") in hashed
        assert ("general_equilibrium", "EquilibriumOperator") in hashed      # the base's _class_descriptor/_validate

    def test_unaudited_operator_with_its_own_descriptor_is_unverifiable(self):
        op = probes.TwoIsomerOperator(0.3)
        assert ge.equilibrium_operator_authority(op) == gk.UNVERIFIABLE_AUTHORITY
        tr = _iso_world(op).integrate({"c": {probes.X1: 1.0}}, duration=1.0, n_steps=4)
        assert tr.receipt.execution_identity_certified is False
        assert tr.receipt.execution_identity_basis == "UNVERIFIED"
        assert tr.receipt.uncertified_equilibrium_operators == (("c", "TwoIsomerOperator"),)

    def test_attested_operator_is_bound_but_never_certified(self):
        w = _iso_world(_Attested(0.3))
        with pytest.raises(CoupledError, match="CALLER-ATTESTED"):
            w.integrate({"c": {probes.X1: 1.0}}, duration=1.0, n_steps=4, require_certified_execution=True)
        tr = w.integrate({"c": {probes.X1: 1.0}}, duration=1.0, n_steps=4, require_certified_execution=True,
                         accept_attested_extensions=True)
        assert tr.receipt.execution_identity_certified is False
        assert tr.receipt.execution_identity_basis == "CALLER_ATTESTED"
        assert tr.receipt.attested_equilibrium_operators == (("c", "_Attested", "xxiv-test-lab"),)

    def test_attested_operator_bound_parameter_mutation_is_detected(self):
        op = _Attested(0.3)
        w = _iso_world(op)
        op.frac = 0.7
        with pytest.raises(StaleCertificateError):
            w.integrate({"c": {probes.X1: 1.0}}, duration=1.0, n_steps=4)

    def test_subclass_and_instance_override_gain_no_authority(self):
        class Sub(AcetateWaterEquilibriumOperator):
            pass
        assert ge.equilibrium_operator_authority(Sub()) == gk.UNVERIFIABLE_AUTHORITY
        op = AcetateWaterEquilibriumOperator()
        op.speciate = lambda *a, **k: None
        assert ge.equilibrium_operator_authority(op) == gk.UNVERIFIABLE_AUTHORITY

    def test_audited_operator_cannot_be_downgraded_by_attestation(self):
        with pytest.raises(gk.KernelError, match="closed operator audit table"):
            ge.register_attested_equilibrium_operator(AcetateWaterEquilibriumOperator, attested_by="x")

    def test_control_real_acetate_operator_keeps_its_certified_identity(self):
        sig =AcetateWaterEquilibriumOperator.species_signature
        sp = {nm: Species.of(nm, dict(sig[nm][0]), sig[nm][1], AQ) for nm in sig}
        ec = EquilibriumCoupling(AcetateWaterEquilibriumOperator(), dict(sp),
                                 reservoir_components=frozenset({"H", "O", "charge"}))
        w = CoupledWorld([Compartment("c", ChemicalSystem(list(sp.values()), [], volume_L=1.0), equilibrium=ec)])
        tr = w.integrate({"c": {sp["HAc"]: 0.2, sp["Na+"]: 0.1}}, duration=1.0, n_steps=3,
                         require_certified_execution=True)
        assert tr.receipt.execution_identity_certified is True
        assert tr.receipt.charge_validity.bulk_electroneutrality == adm.CHARGE_NEUTRALITY_IMPOSED


# ============================================================================================ 1B positivity (p6b)
A = Species.of("A", {"Q": 1}, 0, AQ)
B = Species.of("B", {"Q": 1}, 0, AQ)


def _drain(initial, rate, duration, atol):
    w = CoupledWorld([Compartment("c", ChemicalSystem([A, B], [], volume_L=1.0))],
                     boundaries=[ExternalBoundary("drain", "c", A, "feed", rate=rate)])
    return w.integrate({"c": {A: initial}}, duration=duration, n_steps=20, atol=atol).receipt


class TestPositivity:
    @pytest.mark.parametrize("atol", [1e-14, 1e-6, 1e-2, 1.0])
    def test_macroscopic_negative_is_never_admitted_at_any_tolerance(self, atol):
        r = _drain(2.0, -1.0, 2.5, atol)
        assert r.positivity_held is False and r.structural_tier == REFUSED
        assert r.positivity_verdict in (adm.POSITIVITY_VIOLATED, adm.POSITIVITY_UNRESOLVED)
        assert r.negative_minima["c/A"] == pytest.approx(-0.5)                 # raw value preserved, not clipped

    def test_unresolved_is_distinguished_from_violated(self):
        assert _drain(2.0, -1.0, 2.5, 1e-14).positivity_verdict == adm.POSITIVITY_VIOLATED
        assert _drain(2.0, -1.0, 2.5, 1e-2).positivity_verdict == adm.POSITIVITY_UNRESOLVED

    @pytest.mark.parametrize("atol", [1e-14, 1e-2])
    def test_positive_control_and_exact_exhaustion(self, atol):
        r = _drain(2.0, -1.0, 2.0, atol)                                       # drains exactly to zero
        assert r.positivity_held is True and r.structural_tier == STRUCTURALLY_CONSERVING

    def test_zero_inventory_species_never_touched_is_held(self):
        r = _drain(1.0, -0.1, 1.0, 1e-14)
        assert r.positivity_verdict == adm.POSITIVITY_HELD

    def test_large_inventory_relative_floor(self):
        held = _drain(1e6, -1e6, 1.0, 1e-14)                                    # exhaustion of a 1e6 mol species
        assert held.positivity_held is True
        neg = _drain(1e6, -1.001e6, 1.0, 1e-14)                                 # -1000 mol of a 1e6 mol species
        assert neg.positivity_held is False and neg.positivity_verdict == adm.POSITIVITY_VIOLATED

    def test_tiny_inventory_dip_beyond_its_scale_is_not_admitted_silently(self):
        r = _drain(1e-13, -1e-13, 2.0, 1e-14)                                   # -1e-13 mol of a 1e-13 mol trace
        assert r.positivity_verdict == adm.POSITIVITY_WITHIN_FLOOR             # below the absolute floor ...
        assert r.positivity_resolution_limited is True                          # ... so flagged unresolvable

    def test_stiff_kinetics_kernel_exhaustion_is_held(self):
        s = ChemicalSystem([A, B], [Reaction("A->B", ((A, -1), (B, 1)), MassActionIrreversible(1e6))], volume_L=1.0)
        r = s.integrate({A: 1.0}, duration=10.0, atol=1e-15, rtol=1e-9).receipt
        assert r.positivity_held is True and r.structural_tier == STRUCTURALLY_CONSERVING

    def test_kernel_path_shares_the_contract(self):
        s = ChemicalSystem([A, B], [], volume_L=1.0)
        r = s.integrate({A: 2.0}, duration=2.5, source={A: -1.0}, atol=1.0).receipt
        assert r.positivity_held is False and r.structural_tier == REFUSED
        assert r.negative_minima["A"] == pytest.approx(-0.5)

    def test_audit_function_classification(self):
        a = adm.positivity_audit([-0.5, 0.0, -1e-11], [2.0, 1.0, 1.0], abs_floor=1e-10, solver_atol=1e-14,
                                 solver_rtol=1e-10, atol_factor=100.0)
        assert a.verdict == adm.POSITIVITY_VIOLATED and a.worst_slot == 0 and set(a.negative_minima) == {0, 2}


# ============================================================================================ 1C charge contract
NA = Species.of("Na+", {"Na": 1}, 1, AQ)
CL = Species.of("Cl-", {"Cl": 1}, -1, AQ)


class TestChargeContract:
    def test_declared_non_neutral_input_is_reported_not_floored(self):
        tr = ChemicalSystem([NA, CL], [], volume_L=1.0).integrate({NA: 0.1}, duration=1.0)
        cv = tr.receipt.charge_validity
        assert cv.bulk_electroneutrality == adm.CHARGE_DECLARED_NON_NEUTRAL and cv.physically_supported is False
        assert tr.receipt.admitted_tier != REFUSED

    def test_neutral_system_without_charges(self):
        cv = ChemicalSystem([A, B], [], volume_L=1.0).integrate({A: 1.0}, duration=1.0).receipt.charge_validity
        assert cv.bulk_electroneutrality == adm.CHARGE_NOT_APPLICABLE and cv.physically_supported is True

    def test_three_claims_are_separate_for_an_unbalanced_feed(self):
        for r in (probes.probe_charge()[k] for k in ("kernel_unbalanced_feed", "coupled1_unbalanced_feed")):
            cv = r["charge_validity"]
            assert cv["reaction_charge_conservation"] == adm.REACTION_CHARGE_EXACT      # (a) holds
            assert cv["external_charge_accounted"] is True                               # (b) holds
            assert cv["bulk_electroneutrality"] == adm.CHARGE_UNSUPPORTED_EXTERNAL        # (c) fails
            assert cv["external_charge_supplied_mol"] == pytest.approx(0.01)
            assert r["structural_tier"] == STRUCTURALLY_CONSERVING and r["admitted_tier"] == REFUSED


# ============================================================================================ 2A temperature transport
class TestSourceDomainTemperature:
    def test_off_domain_refused_on_both_paths(self):
        with pytest.raises(CoupledSourceDomainError):
            CoupledWorld([Compartment("c", probes._p5_system())], temperature_K=310.0).integrate(
                {"c": {probes.S_: 1e-2}}, duration=1.0, n_steps=2)
        with pytest.raises(SourceDomainError):
            probes._p5_system().integrate({probes.S_: 1e-2}, duration=1.0, temperature_K=310.0)

    def test_within_match_tolerance_runs(self):
        tr = probes._p5_system().integrate({probes.S_: 1e-2}, duration=1.0, temperature_K=298.155)
        assert tr.receipt.source_domain.startswith("SUPPORTED")

    def test_laws_without_sourced_constants_are_labeled_not_refused(self):
        s = ChemicalSystem([A, B], [Reaction("A->B", ((A, -1), (B, 1)), MassActionIrreversible(1.0))], volume_L=1.0)
        tr = s.integrate({A: 1.0}, duration=1.0, temperature_K=350.0)
        assert tr.receipt.source_domain == adm.SOURCE_DOMAIN_NONE

    def test_the_law_source_temperature_inventory(self):
        law = probes._p5_system().reactions[0].rate_law
        assert adm.law_source_temperatures(law) == (("ksp", 298.15),)
        c = SourcedConstant("K", 1.0, 0.1, "-", 310.0, "x", "SOURCED")
        assert adm.temperature_domain_violations([("o", Reaction("diss", probes.ST_, type(law)(1e-3, c, probes.ST_)))],
                                                 298.15) == [("o", "diss", "ksp", 310.0)]


def test_no_admissibility_helper_reads_caller_atol_into_the_physical_floor():
    """The physical floor must not move with atol (the p6b invariant, stated directly)."""
    lo = adm.positivity_audit([-1e-3], [1.0], abs_floor=1e-10, solver_atol=1e-14, solver_rtol=0.0, atol_factor=100.0)
    hi = adm.positivity_audit([-1e-3], [1.0], abs_floor=1e-10, solver_atol=1.0, solver_rtol=0.0, atol_factor=100.0)
    assert lo.floors == hi.floors and not lo.held and not hi.held
    assert np.isclose(lo.floors[0], 1e-10 + adm.POS_REL_FLOOR * 1.0)
