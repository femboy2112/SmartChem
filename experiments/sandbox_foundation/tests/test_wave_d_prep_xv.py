"""OPERATION XV Wave D PREP -- gates for the ammonia stiff-network first consumer.

The load-bearing pins: a DISTINCT base-buffer chemistry (NH3/NH4+) runs through the SAME Wave A kernel; its stiff
kinetic fixed point satisfies DETAILED BALANCE against the declared 1/Ka (not a fitted curve); conservation is exact;
and the tier stays ASSUMED_PARAMETER (kf is assumed, only kf/kr is pinned to chemistry -- no inflated claim)."""
from __future__ import annotations

from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER
from experiments.sandbox_foundation.general_ammonia_demo import (
    KA_NH4,
    build_ammonia_protonation_system,
    run_ammonia_buffer,
)


def test_ammonia_fixed_point_satisfies_detailed_balance():
    _traj, info = run_ammonia_buffer()
    # at r_vol = 0 the mass-action law forces [NH4+]/([NH3][H+]) = kf/kr = 1/Ka, exactly -- an analytic cross-check
    assert info["detailed_balance_rel_residual"] < 1e-6
    assert abs(info["measured_ratio"] - 1.0 / KA_NH4) / (1.0 / KA_NH4) < 1e-6


def test_ammonia_network_conserves_to_machine_zero():
    traj, _info = run_ammonia_buffer()
    assert traj.max_component_drift < 1e-12
    assert traj.min_amount >= -1e-12


def test_ammonia_is_a_distinct_chemistry_through_the_same_kernel():
    sys = build_ammonia_protonation_system()
    # a base buffer over {N, H} + charge -- disjoint from the acetate work's {C, H, Na, O}; same integrate() path
    assert set(sys.component_labels) == {"N", "H", "charge"}
    traj = run_ammonia_buffer()[0]
    assert traj.solver_success


def test_ammonia_tier_is_assumed_not_inflated():
    _traj, info = run_ammonia_buffer()
    # kf is a representative (assumed) value; pinning only the ratio to Ka does not earn a stronger claim
    assert info["tier"] == ASSUMED_PARAMETER
