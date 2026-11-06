"""Wave B4 (Round VII): the local identifiability finding is pinned.

pH ALONE is rank-1 in theta = (logK_NaAc, Davies A) -- a single scalar cannot separate two parameters.  The full
observable set {pH, free-acetate fraction, ion-pair fraction, ionic strength} is rank-2 and well-conditioned, and a
speciation observable added to pH already reaches rank 2.  (Local Jacobian at one operating point, not a global
claim -- see identifiability.py.)"""
import numpy as np

from experiments.sandbox_foundation.identifiability import OBSERVABLE_NAMES, sensitivity


def test_full_observable_set_is_locally_identifiable_rank2_well_conditioned():
    s = sensitivity(C_T=0.45, Na=0.45)
    assert s["rank_full"] == 2
    assert s["cond_full"] < 10.0                          # well conditioned (~1.7), not a near-degenerate pair
    assert set(s["observables"]) == set(OBSERVABLE_NAMES)


def test_pH_alone_is_rank_one_cannot_separate_the_two_parameters():
    s = sensitivity(C_T=0.45, Na=0.45)
    assert s["rank_pH_only"] == 1                         # one scalar, two params -> at most rank one
    assert np.all(np.abs(s["jacobian"][0, :]) > 0.0)      # pH IS sensitive to both, but spans only a 1-D subspace


def test_a_speciation_observable_on_top_of_pH_lifts_the_rank_to_two():
    s = sensitivity(C_T=0.45, Na=0.45)
    two = s["jacobian"][:2, :]                            # {pH, free-acetate fraction}
    assert int(np.sum(np.linalg.svd(two, compute_uv=False) > 1e-9)) == 2
