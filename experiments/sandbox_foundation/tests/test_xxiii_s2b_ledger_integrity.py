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

from experiments.sandbox_foundation.claim_tiers import STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
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


