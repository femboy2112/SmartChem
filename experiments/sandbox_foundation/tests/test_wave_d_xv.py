"""OPERATION XV Wave D -- the distinct-chemistry-consumer gates (ammonia / ammonium, a weak BASE buffer).

The load-bearing pins:
  * a validated ammonia equilibrium solver -- TWO independent routes (transcendental bracket + algebraic cubic Newton)
    agree, mass/charge close -> NUMERICALLY_VERIFIED; the half-neutralized buffer sits at pKa;
  * AmmoniaWaterEquilibriumOperator is a DISTINCT equilibrium consumer of the Wave B interface (base chemistry, not
    acetate) and reproduces the solver;
  * the FULL stiff ammonia-water kinetic network (explicit water, E.N=0 exact) relaxes to the SAME speciation the
    operator computes one-shot -- a kinetic fixed point corroborated by an independent algebraic solve;
  * the MULTIPHASE Wave C consumer: closed NH3(aq)<=>NH3(g) partitioning conserves nitrogen across phases and hits the
    declared Henry partition; open stripping (a fixed-activity sweep) removes ammonia and LEDGERS the lost nitrogen;
  * HONESTY: the stripping dynamics rest on an assumed Henry partition + transfer coefficients, so the dynamic tier is
    capped at ASSUMED_PARAMETER (weakest-premise), never inflated to STRUCTURALLY_CONSERVING.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.ammonia_equilibrium import (
    PKA_NH4,
    AmmoniaWaterSystem,
    solve,
)
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER, STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_ammonia_demo import (
    NH3,
    NH3g,
    NH4,
    Nap,
    ammonia_network_vs_operator_crosscheck,
    build_ammonia_stripping_world,
)
from experiments.sandbox_foundation.general_equilibrium import (
    AmmoniaWaterEquilibriumOperator,
    EquilibriumError,
)


# ---------------------------------------------------------------- the solver
@pytest.mark.parametrize("sys", [
    AmmoniaWaterSystem(0.01),
    AmmoniaWaterSystem(0.1),
    AmmoniaWaterSystem(0.1, strong_base_M=0.05),
    AmmoniaWaterSystem(0.1, strong_acid_M=0.05),
    AmmoniaWaterSystem(0.1, strong_acid_M=0.1),
])
def test_ammonia_solver_two_routes_agree_and_close(sys):
    r = solve(sys)
    assert r.verdict == "SOLVED_IDEAL"
    assert r.tier == "NUMERICALLY_VERIFIED"           # two INDEPENDENT routes agree
    assert r.solver_agreement_residual < 1e-8
    assert r.charge_balance_residual < 1e-9 * max(1.0, sys.total_ammonia_M)
    assert r.mass_balance_residual < 1e-9 * max(1.0, sys.total_ammonia_M)


def test_half_neutralized_buffer_sits_at_pKa():
    # NH4Cl 0.05 + NH3 0.05 (total ammonia 0.1, strong acid 0.05): equal NH3/NH4+ -> pH = pKa
    r = solve(AmmoniaWaterSystem(0.1, strong_acid_M=0.05))
    assert abs(r.pH - PKA_NH4) < 0.01
    assert abs(r.nh3_M - r.nh4_M) < 2e-3


# ---------------------------------------------------------------- the operator (distinct consumer)
def test_ammonia_operator_is_a_distinct_equilibrium_consumer():
    op = AmmoniaWaterEquilibriumOperator()
    assert op.components == frozenset({"ammonia", "strong_base", "strong_acid"})
    assert set(op.species) == {"NH3", "NH4+", "H+", "OH-", "Na+", "Cl-"}
    V = 2.0
    st = op.speciate({"ammonia": 0.1 * V, "strong_acid": 0.05 * V}, volume_L=V)
    direct = solve(AmmoniaWaterSystem(0.1, strong_acid_M=0.05))
    assert abs(st.species_amounts["NH3"] - direct.nh3_M * V) < 1e-12
    assert abs(st.species_amounts["NH4+"] - direct.nh4_M * V) < 1e-12
    assert abs(st.species_amounts["Cl-"] - 0.05 * V) < 1e-15        # strong ion passed through
    assert st.component_residuals["ammonia"] < 1e-9
    assert st.structural_tier == STRUCTURALLY_CONSERVING


def test_ammonia_operator_refuses_unknown_component_and_bad_volume():
    op = AmmoniaWaterEquilibriumOperator()
    with pytest.raises(EquilibriumError):
        op.speciate({"acetate": 0.1}, volume_L=1.0)                 # acetate is not this operator's component
    with pytest.raises(EquilibriumError):
        op.speciate({"ammonia": 0.1}, volume_L=0.0)


# ---------------------------------------------------------------- Wave A kinetics vs Wave D algebra
def test_full_stiff_network_fixed_point_matches_the_operator():
    x = ammonia_network_vs_operator_crosscheck(total_ammonia_M=0.1, strong_acid_M=0.05)
    assert x["max_rel_residual"] < 1e-5                 # kinetic fixed point == independent algebraic solve
    assert x["conservation_drift"] < 1e-12              # E.N=0 exact with explicit water
    assert abs(x["kinetic_pH"] - x["operator_pH"]) < 1e-4


# ---------------------------------------------------------------- multiphase consumer
def test_closed_partitioning_conserves_nitrogen_and_hits_henry():
    world, _c, initial = build_ammonia_stripping_world(purge=False)
    traj = world.integrate(initial, duration=200.0, n_steps=200, scheme="strang",
                           declared_kinetic_tier=ASSUMED_PARAMETER)
    lf, gf = traj.amounts["liq"][-1], traj.amounts["gas"][-1]
    c_aq, c_gas = lf[NH3] / 1.0, gf[NH3g] / 1.0
    assert abs(c_aq / c_gas - 1000.0) / 1000.0 < 1e-4          # the declared Henry partition c_aq/c_gas
    assert traj.max_conserved_drift < 1e-11                    # N conserved across the two phases
    total_N = lf[NH3] + lf[NH4] + gf[NH3g]
    assert abs(total_N - 0.1) < 1e-10


def test_open_stripping_removes_ammonia_ledgers_N_and_preserves_sodium():
    cworld, _c, cinit = build_ammonia_stripping_world(purge=False)
    closed = cworld.integrate(cinit, duration=200.0, n_steps=200, scheme="strang",
                              declared_kinetic_tier=ASSUMED_PARAMETER)
    oworld, _o, oinit = build_ammonia_stripping_world(purge=True)
    opent = oworld.integrate(oinit, duration=200.0, n_steps=200, scheme="strang",
                             declared_kinetic_tier=ASSUMED_PARAMETER)
    # the closed world conserves N exactly; the open (swept) world strips it, and the loss is INDEPENDENTLY LEDGERED
    # (XVIII-3): the stripped nitrogen is no longer dumped into the tautological reservoir_exchange bucket -- it is
    # accumulated as a signed external flux and reconciled against the measured inventory change.
    assert closed.max_conserved_drift < 1e-11
    n0 = oinit["liq"][NH3] + oinit["liq"][NH4]
    nf = opent.amounts["liq"][-1][NH3] + opent.amounts["liq"][-1][NH4]
    assert nf < n0 - 1e-3                                       # meaningful stripping occurred
    assert "N" not in opent.receipt.reservoir_exchange         # XVIII-3: N is a BOUNDARY flux now, not an implicit reservoir
    assert opent.receipt.external_flux["N"] < -1e-3            # nitrogen left via the independently-integrated sweep
    assert opent.receipt.ledger_adjusted_residual["N"] < 1e-5  # and the swept N reconciles with the measured change
    assert opent.receipt.material_balance_closed               # the whole open-world material balance closes
    assert abs(opent.receipt.reservoir_exchange["charge"]) < 1e-9   # charge stays implicit-solvent-coupled (endpoint)
    # sodium is a spectator: not stripped, not reservoir-coupled -> conserved
    assert abs(opent.amounts["liq"][-1][Nap] - oinit["liq"][Nap]) < 1e-9


def test_stripping_dynamic_tier_is_capped_at_assumed_not_inflated():
    world, _c, initial = build_ammonia_stripping_world(purge=True)
    traj = world.integrate(initial, duration=100.0, n_steps=100, scheme="strang",
                           declared_kinetic_tier=ASSUMED_PARAMETER)
    # the Henry partition + transfer coefficients are assumed -> the dynamic prediction must not claim structural rank
    assert traj.tier == ASSUMED_PARAMETER
    assert traj.receipt.structural_tier == STRUCTURALLY_CONSERVING   # the bookkeeping is still exact, reported honestly
