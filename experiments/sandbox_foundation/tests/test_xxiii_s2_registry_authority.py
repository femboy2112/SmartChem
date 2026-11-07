"""OPERATION XXIII Phase II -- rate-law registration AUTHORITY (the predeclared priority probe).

PREDECLARED (before running): PASS = untrusted self-registration cannot elevate a class to certified execution without
an explicit trusted authority boundary; FAIL = registering the class alone lets the same forged descriptor obtain a
certified trajectory; AMBIGUOUS = the contract intentionally trusts caller registration but does not expose it.

RED (observed on main 6a2686e, receipt in docs/research/OPERATION_XXIII_TRUST_BOUNDARY.md): FAIL.  One public call,
``register_certified_rate_law(Lying)``, made a lying law run under ``require_certified_execution=True`` with
``execution_identity_certified=True``; a 10x hidden-parameter mutation then moved B_final 0.393469 -> 0.993262 under a
byte-identical world certificate, and the admitted tier ROSE (ASSUMED_PARAMETER -> STRUCTURALLY_CONSERVING).

GREEN (XXIII-2): a CLOSED, source-pinned audit table is the only route to AUDITED_BUILTIN; plugins go through
``register_attested_rate_law`` and stay labeled CALLER_ATTESTED (bound, mutation-checked, never certified, tier-floored,
refused by strict mode unless explicitly accepted).  This is an in-process trusted-code authority, NOT cryptographic
validation -- the boundary tests below say exactly what it does and does not stop.
"""
from __future__ import annotations

import hashlib

import pytest

from experiments.sandbox_foundation import general_kernel as gk
from experiments.sandbox_foundation.claim_tiers import BENCHMARKED_AGAINST_REFERENCE_SOLVER, rank
from experiments.sandbox_foundation.general_coupled import Compartment, CoupledError, CoupledWorld
from experiments.sandbox_foundation.general_coupled_demo import build_reaction_diffusion_world
from experiments.sandbox_foundation.general_kernel import (
    AUDITED_BUILTIN,
    CALLER_ATTESTED_EXTENSION,
    UNVERIFIABLE_AUTHORITY,
    ChemicalSystem,
    KernelError,
    MassActionIrreversible,
    Phase,
    RateLaw,
    Reaction,
    Species,
    StaleCertificateError,
    audit_status,
    is_certified_rate_law_type,
    rate_law_authority,
    register_attested_rate_law,
    register_certified_rate_law,
)

_A = Species.of("A", {"R": 1}, charge=0, phase=Phase.AQUEOUS)
_B = Species.of("B", {"R": 1}, charge=0, phase=Phase.AQUEOUS)


def _first_order(k, reaction, c):
    r = float(k)
    for sp, coeff in reaction.stoich:
        if coeff < 0:
            r *= c[sp] ** (-coeff)
    return r


class _Lying(RateLaw):
    """Descriptor reports a frozen claim; evaluate reads a mutable hidden ``secret``; self-declares a strong tier."""
    tier = BENCHMARKED_AGAINST_REFERENCE_SOLVER

    def __init__(self, secret):
        self.secret = secret

    def evaluate(self, reaction, concentrations):
        return _first_order(self.secret, reaction, concentrations)

    def descriptor(self):
        return ("_Lying", "frozen-claim")


class _Faithful(RateLaw):
    tier = BENCHMARKED_AGAINST_REFERENCE_SOLVER

    def __init__(self, k):
        self.k = k

    def evaluate(self, reaction, concentrations):
        return _first_order(self.k, reaction, concentrations)

    def descriptor(self):
        return ("_Faithful", repr(float(self.k)))


@pytest.fixture(autouse=True)
def _clean_attestations():
    before = dict(gk._ATTESTED_EXTENSIONS)
    yield
    gk._ATTESTED_EXTENSIONS.clear()
    gk._ATTESTED_EXTENSIONS.update(before)


def _world(law):
    sysA = ChemicalSystem([_A, _B], [Reaction("A->B", ((_A, -1), (_B, 1)), law)], volume_L=1.0)
    return CoupledWorld([Compartment("c", sysA)]), {"c": {_A: 1.0, _B: 0.0}}


# ======================================================================= the RED replay: self-registration is gone
def test_red_replay_self_registration_cannot_certify():
    with pytest.raises(KernelError, match="removed"):
        register_certified_rate_law(_Lying)
    assert rate_law_authority(_Lying(0.5)) == UNVERIFIABLE_AUTHORITY
    assert not is_certified_rate_law_type(_Lying)


def test_unregistered_lying_law_is_demoted_and_strict_refuses():
    world, init = _world(_Lying(0.5))
    tr = world.integrate(init, duration=1.0, n_steps=50)
    assert tr.receipt.execution_identity_certified is False
    assert tr.receipt.execution_identity_basis == "UNVERIFIED"
    assert rank(tr.receipt.admitted_tier) <= 1
    with pytest.raises(CoupledError):
        world.integrate(init, duration=1.0, n_steps=50, require_certified_execution=True)


# ======================================================================= the attested-extension route (plugins)
def test_attested_lying_law_strict_refuses_without_explicit_acceptance():
    register_attested_rate_law(_Lying, attested_by="a hostile plugin author")
    assert rate_law_authority(_Lying(0.5)) == CALLER_ATTESTED_EXTENSION
    assert not is_certified_rate_law_type(_Lying)
    world, init = _world(_Lying(0.5))
    with pytest.raises(CoupledError, match="CALLER-ATTESTED"):
        world.integrate(init, duration=1.0, n_steps=50, require_certified_execution=True)


def test_attested_lying_law_accepted_explicitly_is_never_certified_and_mutation_stays_honest():
    register_attested_rate_law(_Lying, attested_by="a hostile plugin author")
    world, init = _world(_Lying(0.5))
    tr1 = world.integrate(init, duration=1.0, n_steps=50, require_certified_execution=True,
                          accept_attested_extensions=True)
    rc = tr1.receipt
    assert rc.execution_identity_certified is False
    assert rc.execution_identity_basis == "CALLER_ATTESTED"
    assert rc.attested_extension_laws == (("c", "A->B", "_Lying", "a hostile plugin author"),)
    assert rank(rc.admitted_tier) <= 1                     # floored: an attestation is a claim, not evidence
    assert any("CALLER ATTESTATION" in cav for cav in tr1.caveats)
    cert = world._world_certificate
    world.compartments[0].system.reactions[0].rate_law.secret = 5.0     # the lie: hidden 10x mutation
    tr2 = world.integrate(init, duration=1.0, n_steps=50, require_certified_execution=True,
                          accept_attested_extensions=True)
    assert world._world_certificate == cert                # the lying descriptor hides it (cannot be prevented) ...
    assert abs(tr2.amounts["c"][-1][_B] - tr1.amounts["c"][-1][_B]) > 1e-3
    assert tr2.receipt.execution_identity_certified is False   # ... but no receipt ever claimed an AUDITED identity
    assert tr2.receipt.execution_identity_basis == "CALLER_ATTESTED"


def test_attested_faithful_law_keeps_the_mutation_backstop():
    register_attested_rate_law(_Faithful, attested_by="lab-x")
    world, init = _world(_Faithful(0.5))
    world.integrate(init, duration=1.0, n_steps=10)
    world.compartments[0].system.reactions[0].rate_law.k = 5.0
    with pytest.raises(StaleCertificateError):
        world.integrate(init, duration=1.0, n_steps=10)


def test_attestation_requires_a_named_attester_and_a_real_law():
    with pytest.raises(KernelError, match="attested_by"):
        register_attested_rate_law(_Faithful, attested_by="  ")
    with pytest.raises(KernelError):
        register_attested_rate_law(int, attested_by="x")

    class _NoDescriptor(RateLaw):
        def evaluate(self, reaction, concentrations):
            return 1.0
    with pytest.raises(KernelError, match="descriptor"):
        register_attested_rate_law(_NoDescriptor, attested_by="x")


def test_an_audited_name_cannot_be_downgraded_or_spoofed_by_attestation():
    with pytest.raises(KernelError, match="closed audit table"):
        register_attested_rate_law(MassActionIrreversible, attested_by="x")
    spoof = type("MassActionIrreversible", (RateLaw,), {
        "__module__": "experiments.sandbox_foundation.general_kernel",
        "evaluate": lambda self, r, c: 99.0, "descriptor": lambda self: ("MassActionIrreversible", "0.1")})
    with pytest.raises(KernelError, match="closed audit table"):
        register_attested_rate_law(spoof, attested_by="x")
    gk._seal_audited_builtin(spoof)                         # canonical module attribute is NOT the spoof -> refused
    assert rate_law_authority(spoof()) == UNVERIFIABLE_AUTHORITY
    assert is_certified_rate_law_type(MassActionIrreversible)  # and the real class was not displaced


# ======================================================================= the closed audited table
def test_every_pinned_builtin_is_sealed_and_strict_certifies():
    from experiments.sandbox_foundation import unified_chemical_world  # noqa: F401  (seals BicarbonateDissolutionRate)
    from experiments.sandbox_foundation import solid_equilibrium  # noqa: F401  (XXIII-S4: seals the two activity laws)
    assert set(audit_status().values()) == {"SEALED"}, audit_status()
    world, init = build_reaction_diffusion_world()
    tr = world.integrate(init, duration=1.0, n_steps=50, require_certified_execution=True)
    assert tr.receipt.execution_identity_certified is True
    assert tr.receipt.execution_identity_basis == AUDITED_BUILTIN
    assert tr.receipt.attested_extension_laws == ()


def test_audit_pins_are_a_regression_anchor():
    """Editing an audited class without re-auditing it must fail HERE (and demote it at runtime)."""
    from experiments.sandbox_foundation import unified_chemical_world as ucw
    classes = {("experiments.sandbox_foundation.general_kernel", "MassActionIrreversible"): gk.MassActionIrreversible,
               ("experiments.sandbox_foundation.general_kernel", "MassActionReversible"): gk.MassActionReversible,
               ("experiments.sandbox_foundation.unified_chemical_world", "BicarbonateDissolutionRate"):
                   ucw.BicarbonateDissolutionRate}
    # XXIII-S4 audit event: the two activity-based solid/speciation laws joined the closed table.
    from experiments.sandbox_foundation import solid_equilibrium as se
    classes[("experiments.sandbox_foundation.solid_equilibrium", "ActivitySolubilityRate")] = se.ActivitySolubilityRate
    classes[("experiments.sandbox_foundation.solid_equilibrium", "ActivityReversibleRate")] = se.ActivityReversibleRate
    assert set(classes) == set(gk._AUDITED_BUILTIN_PINS)
    for key, cls in classes.items():
        digest = hashlib.sha256(gk._class_source(cls)[0].encode("utf-8")).hexdigest()
        assert digest == gk._AUDITED_BUILTIN_PINS[key], f"{key} changed: re-audit it and update its pin"


def test_stale_pin_demotes_fail_closed_with_a_named_reason():
    key = ("experiments.sandbox_foundation.general_kernel", "MassActionReversible")
    good = gk._AUDITED_BUILTIN_PINS[key]
    try:
        gk._AUDITED_BUILTIN_PINS[key] = "0" * 64
        gk._seal_audited_builtin(gk.MassActionReversible)
        assert not is_certified_rate_law_type(gk.MassActionReversible)
        assert "re-audit" in audit_status()[key]
    finally:
        gk._AUDITED_BUILTIN_PINS[key] = good
        gk._seal_audited_builtin(gk.MassActionReversible)
    assert is_certified_rate_law_type(gk.MassActionReversible)


# ======================================================================= demotion of every override route
def test_subclass_of_an_audited_builtin_inherits_nothing():
    class _Evil(MassActionIrreversible):
        def evaluate(self, reaction, concentrations):
            return 123.0
    assert rate_law_authority(_Evil(k=0.1)) == UNVERIFIABLE_AUTHORITY


def test_instance_level_method_override_demotes():
    from experiments.sandbox_foundation.unified_chemical_world import BicarbonateDissolutionRate
    from experiments.sandbox_foundation.general_kernel import Phase as P
    s = Species.of("NaHCO3(s)", {"Na": 1, "H": 1, "C": 1, "O": 3}, charge=0, phase=P.SOLID)
    na = Species.of("Na+", {"Na": 1}, charge=1, phase=P.AQUEOUS)
    h = Species.of("HCO3-", {"H": 1, "C": 1, "O": 3}, charge=-1, phase=P.AQUEOUS)
    law = BicarbonateDissolutionRate(k_diss=1e-3, Qsp=1.5, solid=s, na=na, hco3=h)
    assert rate_law_authority(law) == AUDITED_BUILTIN
    law.evaluate = lambda reaction, concentrations: 42.0
    assert rate_law_authority(law) == UNVERIFIABLE_AUTHORITY


def test_post_seal_method_swap_demotes_then_restores():
    original = MassActionIrreversible.__dict__["evaluate"]
    try:
        MassActionIrreversible.evaluate = lambda self, reaction, concentrations: 0.0
        assert rate_law_authority(MassActionIrreversible(k=0.1)) == UNVERIFIABLE_AUTHORITY
        assert not is_certified_rate_law_type(MassActionIrreversible)
    finally:
        MassActionIrreversible.evaluate = original
    assert rate_law_authority(MassActionIrreversible(k=0.1)) == AUDITED_BUILTIN


def test_boundary_in_process_rebinding_of_the_table_is_inside_the_trust_boundary():
    """HONEST BOUNDARY (not a guarantee): code that writes the private tables directly can forge the audited tier.
    This test pins that the authority is a trusted-code assumption, so nobody reads it as cryptographic."""
    try:
        gk._AUDITED_BUILTINS[_Lying] = gk._SealRecord(AUDITED_BUILTIN, gk._method_snapshot(_Lying), "forged")
        assert rate_law_authority(_Lying(0.5)) == AUDITED_BUILTIN
    finally:
        gk._AUDITED_BUILTINS.pop(_Lying, None)
    assert rate_law_authority(_Lying(0.5)) == UNVERIFIABLE_AUTHORITY
