"""OPERATION XV Wave A -- the five P0 kernel-certification repairs, each with a HOSTILE, counterexample-resistant test.

The plan's exit gate: every P0 defect is reproduced-and-repaired or decisively refuted by an executable test.  Here
each repair is pinned by a test that FAILS on the pre-XV kernel and passes on the repaired one:

  1A  exact (unbounded-integer) conservation       -- an int64 matrix product overflows and FALSELY certifies 2^62 A
                                                       -> 2^62 B (true imbalance 2^64 wraps to 0); the exact proof refuses it.
  1B  canonical / unique composition               -- a duplicate element is refused; a float count is rejected, never
                                                       silently truncated to a smaller integer.
  1C  volume + concentration-basis kinetics        -- the SAME concentrations in a 1 L and a 10 L reactor give identical
                                                       concentration trajectories; mole inventories scale with volume.
  1D  external-ledger conservation for open systems -- E(n_final-n0) == integral(E q dt) is verified independently;
                                                       dropping/reversing a source is detectable; a dropped source is NOT 0-drift.
  1E  derived, non-self-certifying evidence + digest -- a caller cannot inflate the admitted tier; the model/run digest
                                                       changes when a rate constant, coefficient, volume or initial amount changes.
"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

from experiments.sandbox_foundation.claim_tiers import (
    ASSUMED_PARAMETER,
    InvalidClaimTierError,
    PREDICTIVE_WITHIN_VALIDATED_DOMAIN,
    STRUCTURALLY_CONSERVING,
)
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    ConservationError,
    KernelError,
    MassActionIrreversible,
    MassActionReversible,
    Phase,
    Reaction,
    Species,
)


# =========================================================================== 1A: exact integer conservation
def test_int64_overflow_cannot_forge_a_false_conservation_certificate():
    # A has 4 X, B has 8 X. The reaction 2^62 A -> 2^62 B has a TRUE X imbalance of 4*2^62 = 2^64, which WRAPS to 0
    # in two's-complement int64. The exact (unbounded Python integer) proof must REFUSE it.
    A = Species.of("A", {"X": 4})
    B = Species.of("B", {"X": 8})
    c = 2 ** 62

    # first demonstrate the defect is REAL: the int64 product the old kernel used would say "balanced" (0).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        E64 = np.array([[4, 8]], dtype=np.int64)
        N64 = np.array([[-c], [c]], dtype=np.int64)
        assert int((E64 @ N64)[0, 0]) == 0                       # the FALSE certificate the exact proof defends against

    with pytest.raises(ConservationError):
        ChemicalSystem([A, B], [Reaction("2^62 A -> 2^62 B", ((A, -c), (B, c)), MassActionIrreversible(1.0))])


def test_large_but_genuinely_balanced_coefficients_are_still_accepted():
    # the fix must not OVER-refuse: a truly balanced large-coefficient reaction still constructs.
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    c = 2 ** 62
    sysX = ChemicalSystem([A, B], [Reaction("big A<->B", ((A, -c), (B, c)), MassActionReversible(kf=1.0, kr=1.0))])
    assert sysX.component_labels == ("X", "charge")


def test_large_element_counts_balance_exactly():
    # a huge per-species element count (not just coefficient) must also be checked exactly.
    big = 10 ** 30
    A = Species.of("A", {"X": big})
    B = Species.of("B", {"X": big})
    C = Species.of("C", {"X": big + 1})
    ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=1.0, kr=1.0))])  # balanced
    with pytest.raises(ConservationError):
        ChemicalSystem([A, C], [Reaction("A->C?", ((A, -1), (C, 1)), MassActionIrreversible(1.0))])        # off by one X


# =========================================================================== 1B: canonical / unique composition
def test_duplicate_element_in_composition_is_refused():
    # (("H",1),("H",1)) is sorted but NOT unique; count("H") would under-report (1) the real multiplicity (2),
    # which could let an unbalanced transform acquire a false certificate. Refuse it at construction.
    with pytest.raises(KernelError):
        Species(name="bad", composition=(("H", 1), ("H", 1)), charge=0, phase=Phase.AQUEOUS)


def test_species_of_rejects_float_counts_never_silently_truncates():
    with pytest.raises(KernelError):
        Species.of("bad", {"H": 1.9})                            # must REJECT, never become "1"
    with pytest.raises(KernelError):
        Species.of("bad", {"H": 0})                              # strictly positive
    with pytest.raises(KernelError):
        Species.of("bad", {"H": -2})
    with pytest.raises(KernelError):
        Species.of("bad", {"H": True})                           # a bool is not a count
    sp = Species.of("ok", {"H": 2.0})                            # an integer-valued float is coerced EXACTLY
    assert sp.count("H") == 2


# =========================================================================== 1C: volume + concentration basis
def _second_order_system(volume_L):
    A = Species.of("A", {"P": 1})
    B = Species.of("B", {"Q": 1})
    C = Species.of("C", {"P": 1, "Q": 1})
    sysX = ChemicalSystem([A, B, C],
                          [Reaction("A+B->C", ((A, -1), (B, -1), (C, 1)), MassActionIrreversible(k=0.5))],
                          volume_L=volume_L)
    return sysX, (A, B, C)


def test_second_order_concentration_trajectories_agree_across_volumes():
    # identical CONCENTRATIONS (1 M each) in a 1 L and a 10 L reactor must give identical concentration trajectories.
    s1, (A1, B1, C1) = _second_order_system(1.0)
    s10, (A10, B10, C10) = _second_order_system(10.0)
    t1 = s1.integrate({A1: 1.0, B1: 1.0}, duration=2.0, n_samples=11, method="BDF")
    t10 = s10.integrate({A10: 10.0, B10: 10.0}, duration=2.0, n_samples=11, method="BDF")
    for f1, f10 in zip(t1.amounts, t10.amounts):
        assert abs(f1[C1] / 1.0 - f10[C10] / 10.0) < 1e-6        # concentration trajectories agree
    # the EXTENSIVE mole inventory scales with volume (10x), the INTENSIVE concentration does not.
    assert abs(t10.amounts[-1][C10] - 10.0 * t1.amounts[-1][C1]) < 1e-5
    assert t10.volume_L == 10.0 and t1.volume_L == 1.0


def test_weak_acid_equilibrium_is_volume_independent():
    # [H+] at equilibrium depends on CONCENTRATION, not amount: 0.1 mol/1 L and 1.0 mol/10 L (both 0.1 M) must agree.
    def build(volume_L, n_HA):
        HA = Species.of("HA", {"H": 1, "Z": 1}, 0)
        Hp = Species.of("H+", {"H": 1}, +1)
        Am = Species.of("A-", {"Z": 1}, -1)
        kr = 1e6
        sysX = ChemicalSystem([HA, Hp, Am],
                              [Reaction("HA<->H+ + A-", ((HA, -1), (Hp, 1), (Am, 1)),
                                        MassActionReversible(kf=1.75e-5 * kr, kr=kr))], volume_L=volume_L)
        return sysX, HA, Hp, n_HA
    s1, HA1, Hp1, n1 = build(1.0, 0.1)
    s10, HA10, Hp10, n10 = build(10.0, 1.0)
    e1 = s1.integrate({HA1: n1}, duration=1.0, n_samples=5, rtol=1e-11, atol=1e-18).amounts[-1]
    e10 = s10.integrate({HA10: n10}, duration=1.0, n_samples=5, rtol=1e-11, atol=1e-18).amounts[-1]
    assert abs((e1[Hp1] / 1.0) - (e10[Hp10] / 10.0)) / (e1[Hp1] / 1.0) < 1e-3


def test_volume_must_be_positive_and_finite():
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    rxn = [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=1.0, kr=1.0))]
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        with pytest.raises(KernelError):
            ChemicalSystem([A, B], rxn, volume_L=bad)


# =========================================================================== 1D: external-ledger conservation
def _feed_system():
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    sysX = ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=1.0, kr=1.0))])
    return sysX, A, B


def test_open_ledger_closes_and_raw_drift_is_not_falsely_zero():
    sysX, A, B = _feed_system()
    dur, qdot = 10.0, 0.3
    traj = sysX.integrate({A: 0.0, B: 0.0}, duration=dur, n_samples=5, source={A: qdot}, method="BDF")
    assert traj.receipt.external_ledger_closed                   # the independent ledger closes
    assert traj.external_ledger_residual < 1e-6
    # the pre-XV bug reported max_component_drift = 0 for an open system; now the fed material is VISIBLE.
    assert traj.max_component_drift > 2.0
    assert abs((traj.amounts[-1][A] + traj.amounts[-1][B]) - qdot * dur) < 1e-6


def test_competing_source_and_sink_ledger_closes():
    sysX, A, B = _feed_system()
    dur = 10.0
    traj = sysX.integrate({A: 5.0, B: 5.0}, duration=dur, n_samples=5, source={A: 0.5, B: -0.2})
    assert traj.receipt.external_ledger_closed
    total_x = traj.amounts[-1][A] + traj.amounts[-1][B]
    assert abs(total_x - (10.0 + (0.5 - 0.2) * dur)) < 1e-5       # started 10 X, net +3.0 fed


def test_reversing_a_source_sign_reverses_the_net_flux():
    sysX, A, B = _feed_system()
    dur = 5.0
    inflow = sysX.integrate({A: 10.0, B: 10.0}, duration=dur, n_samples=3, source={A: +0.4})
    outflow = sysX.integrate({A: 10.0, B: 10.0}, duration=dur, n_samples=3, source={A: -0.4})
    tin = inflow.amounts[-1][A] + inflow.amounts[-1][B]
    tout = outflow.amounts[-1][A] + outflow.amounts[-1][B]
    assert tin > 20.0 > tout                                     # inflow adds X, outflow removes it
    assert inflow.receipt.external_ledger_closed and outflow.receipt.external_ledger_closed


def test_unknown_initial_or_nonfinite_source_is_refused_not_ignored():
    sysX, A, B = _feed_system()
    Z = Species.of("Z", {"W": 1})
    with pytest.raises(KernelError):
        sysX.integrate({A: 1.0, Z: 0.5}, duration=1.0)           # Z not in the system -> refuse, never silently drop
    with pytest.raises(KernelError):
        sysX.integrate({A: 1.0}, duration=1.0, source={B: float("inf")})


# =========================================================================== 1E: derived evidence + digest identity
def _simple_system():
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    return ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=2.0, kr=1.0))]), A, B


def test_caller_cannot_inflate_the_admitted_tier():
    sysX, A, _B = _simple_system()
    # a caller DECLARES the strongest tier; the kernel earns only STRUCTURALLY_CONSERVING, so weakest-premise caps it.
    traj = sysX.integrate({A: 1.0}, duration=10.0, declared_kinetic_tier=PREDICTIVE_WITHIN_VALIDATED_DOMAIN)
    assert traj.receipt.structural_tier == STRUCTURALLY_CONSERVING
    assert traj.receipt.admitted_tier == STRUCTURALLY_CONSERVING     # NOT predictive -- the lie is capped
    assert traj.tier == STRUCTURALLY_CONSERVING


def test_declared_assumed_kinetics_lower_the_admitted_tier():
    sysX, A, _B = _simple_system()
    traj = sysX.integrate({A: 1.0}, duration=10.0, declared_kinetic_tier=ASSUMED_PARAMETER)
    assert traj.receipt.admitted_tier == ASSUMED_PARAMETER           # weakest(STRUCTURAL, ASSUMED) = ASSUMED
    assert traj.receipt.structural_tier == STRUCTURALLY_CONSERVING   # the structure is still certified separately


def test_invalid_declared_tier_fails_loudly():
    sysX, A, _B = _simple_system()
    with pytest.raises(InvalidClaimTierError):
        sysX.integrate({A: 1.0}, duration=1.0, declared_kinetic_tier="TOTALLY_LEGIT_TRUST_ME")


def test_model_digest_changes_when_the_governing_science_changes():
    from experiments.sandbox_foundation import general_chemistry_demo as demo
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    base = ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=2.0, kr=1.0))])
    kf_changed = ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=3.0, kr=1.0))])
    vol_changed = ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=2.0, kr=1.0))],
                                 volume_L=2.0)
    d_base = demo.model_identity_digest(base)
    assert d_base != demo.model_identity_digest(kf_changed)          # a rate constant changed
    assert d_base != demo.model_identity_digest(vol_changed)         # the volume changed
    assert d_base == demo.model_identity_digest(base)                # but it is deterministic


def test_run_digest_separates_initial_conditions_from_the_model():
    from experiments.sandbox_foundation import general_chemistry_demo as demo
    sysX, A, _B = _simple_system()
    d1 = demo.run_identity_digest(sysX, {A: 1.0}, 10.0)
    d2 = demo.run_identity_digest(sysX, {A: 2.0}, 10.0)              # only an initial amount changed
    assert d1 != d2                                                  # the RUN digest moves
    assert demo.model_identity_digest(sysX) == demo.model_identity_digest(sysX)   # the MODEL digest does not
