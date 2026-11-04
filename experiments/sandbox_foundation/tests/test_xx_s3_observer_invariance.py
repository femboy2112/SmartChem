"""OPERATION XX section 3 -- OBSERVER-INVARIANT numerical verification.

The numerical verdict (positivity, conservation drift, the independent-ledger residual) is computed over EVERY accepted
macro-step, NOT over the sampled subset ``ys``.  It therefore depends on the integration and not on how densely the
observer chose to sample it.

  3C  a CLEAN run's verdict is identical across sampling cadences (rendering cadence != certification cadence).
  3A  a transient negative at a NON-sampled step is caught identically at every cadence -- a sparse observer can no
      longer be fooled.  (RED, archived in the measure-first probe xx_s3_measure.py: before this fix min_amount and
      positivity were taken over the SAMPLED subset, so this exact injection flipped the verdict True/False with
      n_samples.)
  3B  a mid-trajectory create-then-remove that CLOSES at the endpoint is still caught by the per-step ledger, though an
      endpoint-only check passes.

Substrate: the pure-kinetic two-cell reaction-diffusion world (no fast-equilibrium projection; closed, so every
component is conserved), which isolates the INTEGRATOR's verification behaviour from any particular chemistry.
``_observer_perturb`` is the integrator's test-only controlled-perturbation hook (unused -> no-op in production).
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_coupled_demo import A, build_reaction_diffusion_world

_DUR, _NSTEPS = 4.0, 60
_DT = _DUR / _NSTEPS


def _R_row(world):
    return list(world.component_labels).index("R")


# ----------------------------------------------------------------- 3C: clean run, verdict invariant to sampling
def test_3C_clean_run_verdict_is_invariant_to_sampling_cadence():
    world, initial = build_reaction_diffusion_world()
    verdicts, counts = set(), {}
    for ns in (None, 10, 5, 1):
        t = world.integrate(initial, duration=_DUR, n_steps=_NSTEPS, scheme="strang", n_samples=ns)
        verdicts.add((t.receipt.positivity_held, t.receipt.material_balance_closed,
                      round(t.min_amount, 12), round(t.max_conserved_drift, 18)))
        counts[ns] = len(t.times)
    assert len(verdicts) == 1                              # NOT ONE certification quantity moved with n_samples
    pos, closed, _, _ = next(iter(verdicts))
    assert pos is True and closed is True
    assert counts[None] > counts[5] > counts[1]            # the cadences really are different (frame counts differ)


# ----------------------------------------------------------------- 3A: transient negative at a non-sampled step
def _transient_negative(slot, inj_step, mag=1e-3):
    saved = {}

    def perturb(step, y):
        if step == inj_step:
            y = y.copy()
            saved["v"] = float(y[slot])
            y[slot] = -mag
            return y
        if step == inj_step + 1:
            y = y.copy()
            y[slot] = saved["v"]
            return y
        return y
    return perturb


def test_3A_transient_negative_caught_identically_at_every_cadence():
    world, initial = build_reaction_diffusion_world()
    slot = world._slot[("cell0", A)]
    inj = 37                     # NOT sampled at n_samples=5 ({0,12,24,36,48,60}) nor 3 ({0,20,40,60})
    verdicts = set()
    for ns in (None, 5, 3, 1):
        t = world.integrate(initial, duration=_DUR, n_steps=_NSTEPS, scheme="strang", n_samples=ns,
                            _observer_perturb=_transient_negative(slot, inj))
        rc = t.receipt
        verdicts.add((rc.positivity_held, rc.first_violation[1], round(rc.first_violation[0], 10),
                      round(t.min_amount, 10)))
    assert len(verdicts) == 1                              # IDENTICAL verdict at every sampling cadence
    pos, kind, t_viol, mn = next(iter(verdicts))
    assert pos is False                                    # the transient negative IS caught (not missed)
    assert kind == "positivity"
    assert t_viol == pytest.approx(inj * _DT)
    assert mn == pytest.approx(-1e-3, abs=1e-9)            # the per-step min captured exactly the injected dip


def test_3A_the_dip_is_invisible_to_a_sparse_observers_samples():
    world, initial = build_reaction_diffusion_world()
    slot = world._slot[("cell0", A)]
    t = world.integrate(initial, duration=_DUR, n_steps=_NSTEPS, scheme="strang", n_samples=5,
                        _observer_perturb=_transient_negative(slot, 37))
    sampled_min = min(float(v) for cn in t.compartments for frame in t.amounts[cn] for v in frame.values())
    assert sampled_min >= -1e-12                           # every SAMPLED frame is clean -> a sampled-only verdict is fooled
    assert t.receipt.positivity_held is False              # but the per-step verdict still catches the step-37 dip


# ----------------------------------------------------------------- 3B: create-then-remove, endpoint closes
def test_3B_midtrajectory_create_then_remove_caught_though_endpoint_closes():
    world, initial = build_reaction_diffusion_world()
    slot = world._slot[("cell0", A)]
    D, k = 1e-2, 30                                        # 30 is not sampled at n_samples=3 ({0,20,40,60})
    coeff = abs(float(world._Eg[_R_row(world), slot]))     # R carried per molecule of A

    def perturb(step, y):
        if step == k:
            y = y.copy()
            y[slot] += D
            return y
        if step == k + 1:
            y = y.copy()
            y[slot] -= D
            return y
        return y

    verdicts = set()
    for ns in (None, 3):
        t = world.integrate(initial, duration=_DUR, n_steps=_NSTEPS, scheme="strang", n_samples=ns,
                            _observer_perturb=perturb)
        rc = t.receipt
        # the ENDPOINT per-component ledger CLOSES (the created R was removed one step later): endpoint-only PASSES
        assert max(rc.ledger_adjusted_residual.values()) <= rc.tolerance
        verdicts.add((rc.material_balance_closed, rc.first_violation[1], round(rc.first_violation[0], 10),
                      round(rc.max_step_material_residual, 8)))
    assert len(verdicts) == 1                              # per-step verdict identical at every cadence
    closed, kind, t_viol, mx = next(iter(verdicts))
    assert closed is False                                 # CAUGHT by the per-step ledger ...
    assert kind == "material_ledger"
    assert t_viol == pytest.approx(k * _DT)
    assert mx == pytest.approx(D * coeff, rel=1e-3)        # ... residual == the injected R, to roundoff
