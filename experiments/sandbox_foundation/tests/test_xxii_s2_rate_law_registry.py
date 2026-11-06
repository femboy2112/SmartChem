"""OPERATION XXII section 2 -- a descriptor() is NOT proof that a rate law is certified.

XXI-2 distinguished descriptor-equipped laws from opaque ones, but descriptor() was SELF-ATTESTED: a custom law can
return a frozen descriptor while evaluate() reads a mutable hidden parameter.  Under XXI-2 such a "lying" law was
treated as CERTIFIABLE -- strict mode accepted it and a 10x mutation of the hidden parameter ran different physics
under an unchanged certificate.  XXII-2 anchors certification in an AUDITED REGISTRY: a law earns a CERTIFIABLE
execution identity only if its EXACT type is registered (a maintainer having verified its descriptor faithfully binds
every operative parameter).  An unregistered law -- even one supplying a descriptor() -- runs EXECUTABLE-UNVERIFIED.

Acceptance (directive §2): a lying descriptor cannot obtain a certified trajectory; a valid built-in mass-action law
can; a valid custom law is promoted only through the explicit verification route (registration); unverifiable laws
remain available with a truthful, conspicuous limitation.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation import general_kernel as gk
from experiments.sandbox_foundation.claim_tiers import BENCHMARKED_AGAINST_REFERENCE_SOLVER, rank
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    _rate_law_descriptor,
)
from experiments.sandbox_foundation.general_coupled_demo import build_reaction_diffusion_world
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    MassActionIrreversible,
    Phase,
    RateLaw,
    Reaction,
    Species,
    StaleCertificateError,
    is_certified_rate_law_type,
    register_certified_rate_law,
)

_A = Species.of("A", {"R": 1}, charge=0, phase=Phase.AQUEOUS)
_B = Species.of("B", {"R": 1}, charge=0, phase=Phase.AQUEOUS)


class _LyingLaw(RateLaw):
    """r = secret * c[A]; mutable hidden parameter; descriptor() returns a CONSTANT that never reflects secret."""
    tier = BENCHMARKED_AGAINST_REFERENCE_SOLVER            # a self-declared STRONG tier, too

    def __init__(self, secret):
        self.secret = secret

    def evaluate(self, reaction, concentrations):
        r = float(self.secret)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                r *= concentrations[sp] ** (-coeff)
        return r

    def descriptor(self):
        return ("_LyingLaw", "frozen-claim")


class _FaithfulCustomLaw(RateLaw):
    """A custom law whose descriptor() FAITHFULLY binds its (mutable) parameter.  Honest -- but its honesty is not
    verifiable from outside; only registration (audit) licenses certification."""
    tier = BENCHMARKED_AGAINST_REFERENCE_SOLVER

    def __init__(self, k):
        self.k = k

    def evaluate(self, reaction, concentrations):
        r = float(self.k)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                r *= concentrations[sp] ** (-coeff)
        return r

    def descriptor(self):
        return ("_FaithfulCustomLaw", repr(float(self.k)))


def _world(law):
    sysA = ChemicalSystem([_A, _B], [Reaction("A->B", ((_A, -1), (_B, 1)), law)], volume_L=1.0)
    return CoupledWorld([Compartment("c", sysA)]), {"c": {_A: 1.0, _B: 0.0}}


# ============================================================ the lying descriptor cannot forge certification
def test_lying_descriptor_is_not_certified():
    world, init = _world(_LyingLaw(0.5))
    tr = world.integrate(init, duration=1.0, n_steps=50)
    assert tr.receipt.execution_identity_certified is False
    assert tr.receipt.uncertified_rate_laws == (("c", "A->B", "_LyingLaw"),)
    assert rank(tr.receipt.admitted_tier) <= 1                      # floored despite its self-declared strong tier
    assert _rate_law_descriptor(_LyingLaw(0.5))[0] == "UNVERIFIABLE_RATE_LAW"


def test_lying_descriptor_strict_mode_refuses():
    world, init = _world(_LyingLaw(0.5))
    with pytest.raises(CoupledError) as ei:
        world.integrate(init, duration=1.0, n_steps=50, require_certified_execution=True)
    assert "no certified execution identity" in str(ei.value).lower()


def test_lying_mutation_runs_different_physics_but_receipt_stays_honest():
    world, init = _world(_LyingLaw(0.5))
    law = world.compartments[0].system.reactions[0].rate_law
    b1 = world.integrate(init, duration=1.0, n_steps=50).amounts["c"][-1][_B]
    law.secret = 5.0                                               # mutate the hidden parameter 10x
    tr2 = world.integrate(init, duration=1.0, n_steps=50)          # no rebuild -> does not raise (unverifiable by design)
    assert abs(tr2.amounts["c"][-1][_B] - b1) > 1e-6               # physics really changed ...
    assert tr2.receipt.execution_identity_certified is False        # ... and the receipt never claimed a certified identity


# ============================================================ built-in mass-action IS certified
def test_builtin_mass_action_is_certified_and_strict_runs():
    world, init = build_reaction_diffusion_world()                 # MassActionIrreversible -> registered
    tr = world.integrate(init, duration=1.0, n_steps=50, require_certified_execution=True)
    assert tr.receipt.execution_identity_certified is True
    assert tr.receipt.uncertified_rate_laws == ()


def test_builtin_types_are_registered():
    assert is_certified_rate_law_type(MassActionIrreversible)
    assert is_certified_rate_law_type(gk.MassActionReversible)
    # BicarbonateDissolutionRate registers on import of its module
    from experiments.sandbox_foundation.unified_chemical_world import BicarbonateDissolutionRate
    assert is_certified_rate_law_type(BicarbonateDissolutionRate)


# ============================================================ the explicit promotion route: registration
def test_custom_law_is_uncertified_until_registered_then_certifiable():
    # UNREGISTERED: even a FAITHFUL descriptor does not certify (its faithfulness is unverifiable from outside)
    assert not is_certified_rate_law_type(_FaithfulCustomLaw)
    assert _rate_law_descriptor(_FaithfulCustomLaw(0.5))[0] == "UNVERIFIABLE_RATE_LAW"
    world, init = _world(_FaithfulCustomLaw(0.5))
    assert world.integrate(init, duration=1.0, n_steps=20).receipt.execution_identity_certified is False
    # PROMOTE via the explicit verification route (registration), then it certifies
    try:
        register_certified_rate_law(_FaithfulCustomLaw)
        assert is_certified_rate_law_type(_FaithfulCustomLaw)
        world2, init2 = _world(_FaithfulCustomLaw(0.5))
        tr = world2.integrate(init2, duration=1.0, n_steps=20, require_certified_execution=True)
        assert tr.receipt.execution_identity_certified is True
    finally:
        gk._CERTIFIED_RATE_LAW_TYPES.discard(_FaithfulCustomLaw)   # keep the global registry clean for other tests


def test_registered_law_mutation_is_caught_by_the_cert_backstop():
    """A registered law's descriptor is audited-faithful, so the XIX-1D cert-recompute catches a post-construction
    mutation of its bound parameter -- the backstop the lying law defeats precisely because its descriptor lies."""
    try:
        register_certified_rate_law(_FaithfulCustomLaw)
        world, init = _world(_FaithfulCustomLaw(0.5))
        world.integrate(init, duration=1.0, n_steps=10)            # snapshot the cert at first integrate
        world.compartments[0].system.reactions[0].rate_law.k = 5.0 # mutate the FAITHFULLY-bound parameter
        with pytest.raises(StaleCertificateError):
            world.integrate(init, duration=1.0, n_steps=10)
    finally:
        gk._CERTIFIED_RATE_LAW_TYPES.discard(_FaithfulCustomLaw)


# ============================================================ registry is fail-closed
def test_registering_a_non_ratelaw_is_refused():
    with pytest.raises(gk.KernelError):
        register_certified_rate_law(int)

    class _NotALaw:
        pass
    with pytest.raises(gk.KernelError):
        register_certified_rate_law(_NotALaw)


def test_registering_a_descriptorless_law_is_refused():
    class _NoDescriptor(RateLaw):
        def evaluate(self, reaction, concentrations):
            return 1.0
    with pytest.raises(gk.KernelError) as ei:
        register_certified_rate_law(_NoDescriptor)
    assert "descriptor" in str(ei.value)
    assert not is_certified_rate_law_type(_NoDescriptor)


def test_unverifiable_law_remains_available_with_a_conspicuous_limitation():
    world, init = _world(_LyingLaw(0.5))
    tr = world.integrate(init, duration=1.0, n_steps=20)           # it RUNS (research mode) ...
    assert tr.amounts["c"][-1][_B] > 0.0
    assert any("certified execution identity" in cav.lower() for cav in tr.caveats)   # ... with the limitation stated
