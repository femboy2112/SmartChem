"""OPERATION XXI section 2 -- an opaque rate law cannot obtain FALSE execution certification.

XX-2 bound the OPERATIVE parameters of a rate law that exposes ``descriptor()`` into the world certificate, so a
post-construction mutation of a CERTIFIABLE law is caught at integrate().  XXI-2 closes the FALLBACK: a user-defined
law that exposes no bindable descriptor is marked UNVERIFIABLE in the certificate -- but that marker is only the class
name, so mutating the law's hidden parameters is invisible to the certificate BY CONSTRUCTION.  The repair is not to
pretend the certificate can witness an unbindable law (it cannot); it is to make the three states EXPLICIT and the
unverified state IMPOSSIBLE TO HIDE:

  * CERTIFIABLE           -- bindable descriptor; mutation detected (XX-2, regressed here via the positive case).
  * EXECUTABLE-UNVERIFIED -- no bindable descriptor; runs, but execution_identity_certified is False, the law is named,
                             the kinetic tier is floored to UNVERIFIED regardless of the law's self-declared tier, and
                             a caveat says so -- the limitation cannot be hidden behind an otherwise-clean receipt.
  * REFUSED               -- require_certified_execution=True raises rather than run an unidentifiable world.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.claim_tiers import (
    BENCHMARKED_AGAINST_REFERENCE_SOLVER,
    STRUCTURALLY_CONSERVING,
    rank,
)
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
)
from experiments.sandbox_foundation.general_coupled_demo import build_reaction_diffusion_world
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    Phase,
    RateLaw,
    Reaction,
    Species,
)

_A = Species.of("A", {"R": 1}, charge=0, phase=Phase.AQUEOUS)
_B = Species.of("B", {"R": 1}, charge=0, phase=Phase.AQUEOUS)


class _SecretLaw(RateLaw):
    """A user law r = secret * c[reactant] with a mutable, hidden, load-bearing parameter and NO descriptor()."""
    def __init__(self, secret, tier=None):
        self.secret = secret
        if tier is not None:
            self.tier = tier                 # a SELF-DECLARED tier -- a caller-supplied label, not a binding

    def evaluate(self, reaction, concentrations):
        r = float(self.secret)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                r *= concentrations[sp] ** (-coeff)
        return r


def _opaque_world(secret=0.5, tier=None):
    law = _SecretLaw(secret, tier=tier)
    sysA = ChemicalSystem([_A, _B], [Reaction("A->B", ((_A, -1), (_B, 1)), law)], volume_L=1.0)
    world = CoupledWorld([Compartment("c", sysA)])
    return world, {"c": {_A: 1.0, _B: 0.0}}, law


# -------------------------------------------------------- EXECUTABLE-UNVERIFIED: runs, but flagged + named + floored
def test_opaque_law_runs_only_as_explicitly_uncertified():
    world, initial, _law = _opaque_world()
    tr = world.integrate(initial, duration=1.0, n_steps=50)
    r = tr.receipt
    assert r.execution_identity_certified is False
    assert r.uncertified_rate_laws == (("c", "A->B", "_SecretLaw"),)
    assert rank(r.admitted_tier) <= 1                                   # floored to the no-certification rank
    assert any("certified execution identity" in cav.lower() for cav in tr.caveats)


def test_a_self_declared_high_tier_is_floored_anyway():
    """A label is not a binding: an opaque law that DECLARES a strong tier must not ride at it.  Without the floor the
    clean closed run would admit at STRUCTURALLY_CONSERVING (rank 2); the descriptor-driven floor drops it to rank 1."""
    world, initial, _law = _opaque_world(tier=BENCHMARKED_AGAINST_REFERENCE_SOLVER)
    tr = world.integrate(initial, duration=1.0, n_steps=50)
    assert tr.receipt.execution_identity_certified is False
    assert rank(tr.receipt.admitted_tier) == 1                          # NOT rank 2 (STRUCTURALLY_CONSERVING), NOT rank 4
    assert rank(STRUCTURALLY_CONSERVING) == 2                           # (guards the premise of the assertion above)


# -------------------------------------------------------- REFUSED: a strict caller gets a refusal, never a false cert
def test_strict_mode_refuses_an_uncertified_world():
    world, initial, _law = _opaque_world()
    with pytest.raises(CoupledError) as ei:
        world.integrate(initial, duration=1.0, n_steps=50, require_certified_execution=True)
    assert "no certified execution identity" in str(ei.value).lower()
    assert "A->B" in str(ei.value)


# -------------------------------------------------------- the honest contract: mutation is invisible, receipt is not
def test_mutating_the_hidden_secret_is_invisible_to_the_cert_but_the_receipt_stays_honest():
    world, initial, law = _opaque_world(secret=0.5)
    tr1 = world.integrate(initial, duration=1.0, n_steps=50)
    b1 = tr1.amounts["c"][-1][_B]
    law.secret = 5.0                                                   # mutate the hidden, unbindable parameter 10x
    tr2 = world.integrate(initial, duration=1.0, n_steps=50)           # no rebuild -- does NOT raise (by construction)
    b2 = tr2.amounts["c"][-1][_B]
    assert abs(b2 - b1) > 1e-6                                         # the physics really changed ...
    assert tr2.receipt.execution_identity_certified is False           # ... and the receipt never claimed otherwise


# -------------------------------------------------------- CERTIFIABLE: the positive case is cleanly distinguished
def test_a_certifiable_world_is_certified_and_runs_under_strict_mode():
    world, initial = build_reaction_diffusion_world()                  # MassActionIrreversible -> bindable descriptor
    tr = world.integrate(initial, duration=1.0, n_steps=50)
    assert tr.receipt.execution_identity_certified is True
    assert tr.receipt.uncertified_rate_laws == ()
    assert not any("certified execution identity" in cav.lower() for cav in tr.caveats)
    # strict mode is a no-op for a fully certifiable world (it runs, same result)
    tr_strict = world.integrate(initial, duration=1.0, n_steps=50, require_certified_execution=True)
    assert tr_strict.receipt.execution_identity_certified is True


def test_strict_mode_distinguishes_the_two_worlds():
    """The boolean flag -- not the tier -- is the real discriminator: both worlds admit at rank 1, yet only the opaque
    one has no execution identity, and only it is refused under strict mode."""
    certifiable, cinit = build_reaction_diffusion_world()
    opaque, oinit, _ = _opaque_world()
    assert rank(certifiable.integrate(cinit, duration=1.0, n_steps=20).receipt.admitted_tier) == 1
    assert rank(opaque.integrate(oinit, duration=1.0, n_steps=20).receipt.admitted_tier) == 1
    # certifiable: strict is a no-op and runs
    certifiable.integrate(cinit, duration=1.0, n_steps=20, require_certified_execution=True)
    # opaque: strict refuses -- the discrimination the equal tiers alone cannot provide
    with pytest.raises(CoupledError):
        opaque.integrate(oinit, duration=1.0, n_steps=20, require_certified_execution=True)
