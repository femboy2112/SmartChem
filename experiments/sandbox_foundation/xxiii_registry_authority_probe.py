"""OPERATION XXIII Phase II -- the PREDECLARED rate-law registration-authority probe (version-agnostic harness).

Runs UNCHANGED against any commit that has the XXII-2 registry API, so the same script produces the RED receipt on the
pre-fix kernel and the GREEN receipt on the XXIII-2 kernel.  Predeclared outcomes (fixed before the first run):

  PASS       untrusted self-registration cannot elevate the class to certified execution without an explicit trusted
             authority boundary;
  FAIL       registering the class alone lets the same forged descriptor obtain a certified trajectory;
  AMBIGUOUS  the contract trusts caller registration but the receipt does not expose that assumption.

    python -m experiments.sandbox_foundation.xxiii_registry_authority_probe
"""
from __future__ import annotations

import json

from experiments.sandbox_foundation import general_kernel as gk
from experiments.sandbox_foundation.claim_tiers import BENCHMARKED_AGAINST_REFERENCE_SOLVER
from experiments.sandbox_foundation.general_coupled import Compartment, CoupledError, CoupledWorld
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, RateLaw, Reaction, Species

A = Species.of("A", {"R": 1}, charge=0, phase=Phase.AQUEOUS)
B = Species.of("B", {"R": 1}, charge=0, phase=Phase.AQUEOUS)


class Lying(RateLaw):
    """descriptor() reports a frozen claim; evaluate() reads a mutable hidden parameter; self-declares a strong tier."""
    tier = BENCHMARKED_AGAINST_REFERENCE_SOLVER

    def __init__(self, secret):
        self.secret = secret

    def evaluate(self, reaction, c):
        return float(self.secret) * c[A]

    def descriptor(self):
        return ("Lying", "frozen-claim")


def _world(law):
    s = ChemicalSystem([A, B], [Reaction("A->B", ((A, -1), (B, 1)), law)], volume_L=1.0)
    return CoupledWorld([Compartment("c", s)]), {"c": {A: 1.0, B: 0.0}}


def run() -> dict:
    out: dict = {}
    w, i = _world(Lying(0.5))
    tr = w.integrate(i, duration=1.0, n_steps=50)
    out["unregistered_certified"] = tr.receipt.execution_identity_certified
    try:
        w.integrate(i, duration=1.0, n_steps=50, require_certified_execution=True)
        out["unregistered_strict"] = "RAN"
    except CoupledError:
        out["unregistered_strict"] = "REFUSED"

    try:
        gk.register_certified_rate_law(Lying)
        out["self_registration"] = "ACCEPTED"
    except gk.KernelError as exc:
        out["self_registration"] = f"REFUSED: {str(exc)[:80]}"

    w, i = _world(Lying(0.5))
    try:
        tr1 = w.integrate(i, duration=1.0, n_steps=50, require_certified_execution=True)
    except CoupledError:
        tr1 = None
    if tr1 is None:
        out["registered_strict"] = "REFUSED"
        out["verdict"] = "PASS"
        return out
    cert = w._world_certificate
    b1 = tr1.amounts["c"][-1][B]
    w.compartments[0].system.reactions[0].rate_law.secret = 5.0
    tr2 = w.integrate(i, duration=1.0, n_steps=50, require_certified_execution=True)
    b2 = tr2.amounts["c"][-1][B]
    out.update(registered_strict="RAN", registered_certified=tr1.receipt.execution_identity_certified,
               registered_tier=tr1.receipt.admitted_tier, mutated_certified=tr2.receipt.execution_identity_certified,
               certificate_unchanged_after_10x_mutation=(w._world_certificate == cert),
               B_final_before=round(b1, 6), B_final_after=round(b2, 6),
               basis=getattr(tr2.receipt, "execution_identity_basis", "<no field>"))
    forged = tr1.receipt.execution_identity_certified and tr2.receipt.execution_identity_certified and abs(b2 - b1) > 1e-6
    out["verdict"] = "FAIL" if forged else ("AMBIGUOUS" if out["basis"] == "<no field>" else "PASS")
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
