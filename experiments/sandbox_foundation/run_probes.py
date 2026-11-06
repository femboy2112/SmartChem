"""Committed harness for the two-cell universe: runs probes A-D and PRINTS the key residuals.

    .venv/bin/python -m experiments.sandbox_foundation.run_probes

NOTE: pytest (experiments/sandbox_foundation/tests) is the AUTHORITATIVE gate; `OVERALL: OK` here is a coarser
residual-threshold check and is NOT a substitute for it.

Every number quoted from this prototype must come from here (SmartChem "experiments are committed").  All results
are finite numerical checks on IDEALIZED / SYNTHETIC systems -- NOT universal proofs.  Deterministic: no RNG.
"""
from __future__ import annotations

import sys

import numpy as np

from . import references as ref
from .analysis import commutator, convergence_ok, estimate_order
from .fixtures import (bimolecular_mechanism, composite_system, isomer_mechanism, single_cell_system,
                       thermal_system, tracer_system)
from .twocell import (Ledger, MissingKineticParameter, ReactionRate, SpeciesBoundary,
                      State, ThermalBoundary, TimestepError, UndeclaredControllerError, apply_controller, audit,
                      reaction_report, reaction_step, run, transport_report, transport_step, Mechanism)

LIMITS = {  # declared acceptance limits (roundoff-level for conservation; method-error-level for analytic)
    "conservation": 1e-12, "energy_abs_J": 1e-8, "analytic_euler_tracer": 5e-3, "analytic_reaction": 1e-8,
    "order_lo": 0.8, "order_hi": 1.3,
}


def _raises(exc, fn) -> bool:
    try:
        fn()
    except exc:
        return True
    return False


def probe_a() -> dict:
    sysm = tracer_system()
    s0 = State(np.array([[4.0], [0.0]]), np.ones(2))
    res = run(sysm, s0, 2.0, 400, ("transport",))
    xa, xb = ref.two_node_relaxation(4.0, 0.0, 1.0, 2.0, sysm.g[0], 2.0)
    b = (SpeciesBoundary("prescribed_flow", (0.3,)), SpeciesBoundary("prescribed_flow", (-0.1,)))
    so = tracer_system(boundaries=b)
    so0 = State(np.array([[1.0], [1.0]]), np.ones(2))
    ro = run(so, so0, 4.0, 200, ("transport",))
    tv = tracer_system(V=(1.0, 1.0), D=1.0)
    return {
        "closed_tracer_conservation_residual_mol": abs(res.state.n.sum() - s0.n.sum()),
        "interface_J_AB_plus_J_BA_max_abs": transport_report(res.ledger)["interface_residual"],
        "open_boundary_inventory_residual_mol": abs(ro.state.n.sum() - so0.n.sum() - (0.3 - 0.1) * 4.0),
        "vs_closed_form_max_abs_err_mol_per_m3": max(abs(res.state.n[0, 0] - xa), abs(res.state.n[1, 0] / 2 - xb)),
        "oversized_dt_refused": _raises(TimestepError, lambda: transport_step(tv, s0, 10.0)),
        "dt_max_s": sysm.transport_dt_max(),
    }


def probe_b() -> dict:
    sysm = thermal_system()
    s0 = State.make(sysm, np.zeros((2, 0)), [400.0, 300.0])
    res = run(sysm, s0, 20.0, 2000, ("thermal",))
    xa, xb = ref.two_node_relaxation(400.0, 300.0, 10.0, 30.0, sysm.G, 20.0)
    T = res.state.temperature(sysm)
    sh = thermal_system(thermal_boundaries=(ThermalBoundary("heater", power_W=5.0), ThermalBoundary()))
    rh = run(sh, s0, 10.0, 1000, ("thermal",))
    sr = thermal_system(thermal_boundaries=(ThermalBoundary(), ThermalBoundary("reservoir", T_res_K=300.0,
                                                                              G_res_W_per_K=1.5)))
    r0 = State.make(sr, np.zeros((2, 0)), [400.0, 350.0])
    rr = run(sr, r0, 300.0, 1200, ("thermal",))
    return {
        "closed_energy_residual_J": abs(audit(sysm, s0, res.state, res.ledger)["energy_residual"]),
        "interface_heat_cancel_max_abs_J": transport_report(res.ledger, "thermal")["interface_residual"],
        "heater_injected_vs_dU_residual_J": abs(rh.state.U.sum() - s0.U.sum() - 50.0),
        "reservoir_supersystem_residual_J": abs(rr.state.U.sum() - r0.U.sum()
                                                + rr.ledger.filter(kind="RESERVOIR_ACCOUNT").total()),
        "vs_closed_form_max_abs_err_K": max(abs(T[0] - xa), abs(T[1] - xb)),
        "undeclared_controller_refused": _raises(UndeclaredControllerError,
                                                 lambda: apply_controller(sysm, s0, None, 0, 350.0)),
        "dt_max_s": sysm.thermal_dt_max(),
    }


def probe_c() -> dict:
    out = {}
    worst = 0.0
    for mech, n0 in ((isomer_mechanism(), [1.0, 0.2]), (bimolecular_mechanism(), [1.0, 0.3, 0.0])):
        sysm = single_cell_system(mech)
        s0 = State(np.array([n0, n0]), np.ones(2))
        led = Ledger()
        s1, _ = reaction_step(sysm, s0, 2.0, ledger=led)
        worst = max(worst, audit(sysm, s0, s1, led)["inventory_residual"],
                    reaction_report(led, mech)["element_charge_residual"])
    out["element_and_charge_residual_mol"] = worst
    s0 = State(np.array([[1.0, 0.2]] * 2), np.ones(2))
    s1, _ = reaction_step(single_cell_system(isomer_mechanism()), s0, 2.0)
    P, _ = ref.isomerization_analytic(1.0, 0.2, 1.5, 0.5, 2.0)
    out["isomerization_vs_closed_form_abs_err_mol"] = abs(s1.n[0, 0] - P)
    sk = State(np.array([[1.0, 0.2]] * 2), np.ones(2))
    s2, _ = reaction_step(single_cell_system(isomer_mechanism(1e4, 1e3)), sk, 1.0)
    P2, _ = ref.isomerization_analytic(1.0, 0.2, 1e4, 1e3, 1.0)
    out["stiff_(k~1e4/s)_vs_closed_form_abs_err_mol"] = abs(s2.n[0, 0] - P2)
    sb = State(np.array([[1.0, 0.3, 0.0]] * 2), np.ones(2))
    _, rb = reaction_step(single_cell_system(bimolecular_mechanism(2.0)), sb, 1.0)
    out["bimolecular_extent_vs_closed_form_abs_err_mol"] = abs(rb.extents["A"][0]
                                                                 - ref.bimolecular_analytic(1.0, 0.3, 2.0, 1.0, 1.0))
    sl, rl = reaction_step(single_cell_system(bimolecular_mechanism(2.0)), sb, 1000.0)
    out["limiting_reactant_extent_overshoot_mol"] = max(0.0, rl.extents["A"][0] - 0.3)
    out["min_amount_after_exhaustion_mol"] = float(sl.n.min())
    out["exhaustion_clamp_flag_raised"] = rl.clamped
    nokin = Mechanism.from_net(("P", "Q"), [[-1.0], [1.0]], ("X",), [[1, 1]], (ReactionRate(k_f=1.0),))
    out["missing_k_r_raises_MissingKineticParameter"] = _raises(
        MissingKineticParameter, lambda: reaction_step(single_cell_system(nokin), s0, 1.0))
    return out


def probe_d() -> dict:
    sysm = composite_system()
    s0 = State(np.array([[1.0, 0.0, 1.0], [0.0, 0.0, 0.0]]), np.ones(2))
    res = run(sysm, s0, 2.0, 40, ("transport", "reaction"))
    T = 1.0
    truth = ref.composite_linear_reference(sysm.volumes_m3, sysm.g, 1.5, 0.5, s0.n, T)
    steps = (8, 16, 32, 64)
    errs = [float(np.max(np.abs(run(sysm, s0, T, k, ("transport", "reaction")).state.n - truth))) for k in steps]
    dts = [T / k for k in steps]
    mobile_T = composite_system(D=(0.0, 0.0, 0.5))
    ms0 = State(np.array([[1.0, 0.2, 1.0], [0.0, 0.0, 0.0]]), np.ones(2))
    return {
        "global_element_charge_tracer_residual_mol": audit(sysm, s0, res.state, res.ledger)["inventory_residual"],
        "transport_report_interface_residual": transport_report(res.ledger)["interface_residual"],
        "reaction_report_element_charge_residual": reaction_report(res.ledger, sysm.mechanism)["element_charge_residual"],
        "commutator_disjoint_(immobile_PQ_vs_mobile_T)": commutator(mobile_T, ms0, "transport", "reaction", 0.4),
        "commutator_coupled_(D_P!=D_Q)": commutator(sysm, s0, "transport", "reaction", 0.4),
        "split_errors_vs_monolithic_expm": errs,
        "dts_s": dts,
        "observed_convergence_order": estimate_order(dts, errs),
        "convergence_in_declared_window": convergence_ok(dts, errs, LIMITS["order_lo"], LIMITS["order_hi"]),
    }


def validate() -> tuple:
    """Run all four probes; return (ok, summary).  ok only if every declared limit holds."""
    A, B, C, D = probe_a(), probe_b(), probe_c(), probe_d()
    L = LIMITS
    checks = {
        "A.tracer_conservation": A["closed_tracer_conservation_residual_mol"] < L["conservation"],
        "A.interface_cancels_exactly": A["interface_J_AB_plus_J_BA_max_abs"] == 0.0,
        "A.open_boundary": A["open_boundary_inventory_residual_mol"] < L["conservation"],
        "A.closed_form": A["vs_closed_form_max_abs_err_mol_per_m3"] < L["analytic_euler_tracer"],
        "A.oversized_dt_refused": A["oversized_dt_refused"],
        "B.energy": B["closed_energy_residual_J"] < L["energy_abs_J"],
        "B.interface_heat_cancels": B["interface_heat_cancel_max_abs_J"] == 0.0,
        "B.heater": B["heater_injected_vs_dU_residual_J"] < L["energy_abs_J"],
        "B.reservoir": B["reservoir_supersystem_residual_J"] < L["energy_abs_J"],
        "B.closed_form": B["vs_closed_form_max_abs_err_K"] < 0.05,
        "B.controller_enforced": B["undeclared_controller_refused"],
        "C.element_charge": C["element_and_charge_residual_mol"] < L["conservation"],
        "C.closed_form": C["isomerization_vs_closed_form_abs_err_mol"] < L["analytic_reaction"],
        "C.stiff_closed_form": C["stiff_(k~1e4/s)_vs_closed_form_abs_err_mol"] < L["analytic_reaction"],
        "C.bimolecular": C["bimolecular_extent_vs_closed_form_abs_err_mol"] < L["analytic_reaction"],
        "C.limiting_reactant": C["limiting_reactant_extent_overshoot_mol"] < 1e-9 and C["min_amount_after_exhaustion_mol"] >= 0,
        "C.missing_rate_raises": C["missing_k_r_raises_MissingKineticParameter"],
        "D.global_conservation": D["global_element_charge_tracer_residual_mol"] < L["conservation"],
        "D.reports_clean": D["transport_report_interface_residual"] == 0.0
        and D["reaction_report_element_charge_residual"] < L["conservation"],
        "D.disjoint_commute": D["commutator_disjoint_(immobile_PQ_vs_mobile_T)"] < 1e-12,
        "D.coupled_do_not_commute": D["commutator_coupled_(D_P!=D_Q)"] > 1e-3,
        "D.convergence": D["convergence_in_declared_window"],
    }
    return all(checks.values()), {"A": A, "B": B, "C": C, "D": D, "checks": checks, "limits": LIMITS}


def main() -> int:
    ok, summ = validate()
    print("SmartChem 2.0 two-cell universe -- SYNTHETIC / IDEALIZED prototype; finite checks are NOT universal proof")
    for name in "ABCD":
        print(f"\n== PROBE {name} ==")
        for k, v in summ[name].items():
            print(f"  {k:55s} {v!r}" if not isinstance(v, float) else f"  {k:55s} {v:.3e}")
    print("\n== CHECKS ==")
    for k, v in summ["checks"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nOVERALL: {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
