"""OPERATION XIV Track B -- the general chemical-system carrier (plan sections 2/3/4/5/10).

The load-bearing pins:
  * THE ARCHITECTURAL GATE: two UNRELATED chemistries -- a synthetic A<->B, B+C->D network and a weak-acid
    dissociation -- run through the SAME ChemicalSystem.integrate with NO solver edit (the kernel imports no
    species-specific constant);
  * CONSERVATION as algebra: E N = 0 is proven EXACTLY at construction; an unbalanced reaction is refused; a closed
    trajectory conserves E n (elements + charge) to machine zero;
  * MISSING DATA is fail-closed: a RATE_UNKNOWN reaction is REFUSED (never a silent k = 0);
  * a reversible reaction REGISTERS its own equilibrium constant (kf/kr) and relaxes to it, matching the analytic
    weak-acid equilibrium;
  * typed species identity: an aqueous ion is NOT its metal / gas counterpart even at equal composition + charge;
  * an external source/sink q changes the conserved totals by EXACTLY its integral, never spuriously.
"""
from __future__ import annotations

import json
import math

import pytest

from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    ConservationError,
    KernelError,
    MassActionIrreversible,
    MassActionReversible,
    MissingKineticsError,
    Phase,
    RATE_UNKNOWN,
    Reaction,
    Species,
)


# -- Consumer B: a purely synthetic network (no acetate, CO2, sodium anywhere) -------------------------------------
def _synthetic_system():
    A = Species.of("A", {"X": 1})        # A, B are isomers -> A<->B conserves X
    B = Species.of("B", {"X": 1})
    C = Species.of("C", {"Y": 1})
    D = Species.of("D", {"X": 1, "Y": 1})  # B + C -> D conserves X and Y
    r1 = Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=2.0, kr=1.0))
    r2 = Reaction("B+C->D", ((B, -1), (C, -1), (D, 1)), MassActionIrreversible(k=5.0))
    return ChemicalSystem([A, B, C, D], [r1, r2]), (A, B, C, D)


def test_synthetic_network_conserves_components_and_holds_positivity():
    sysB, (A, B, C, D) = _synthetic_system()
    assert sysB.component_labels == ("X", "Y", "charge")
    traj = sysB.integrate({A: 1.0, C: 0.5}, duration=20.0, n_samples=30, method="BDF")
    end = traj.amounts[-1]
    assert abs((end[A] + end[B] + end[D]) - 1.0) < 1e-9          # total X conserved
    assert abs((end[C] + end[D]) - 0.5) < 1e-9                   # total Y conserved
    assert traj.max_component_drift < 1e-9                       # E n invariant to machine zero (closed system)
    assert traj.min_amount >= -1e-12                             # positivity held
    assert traj.solver_success


def test_synthetic_network_limiting_reagent():
    sysB, (A, B, C, D) = _synthetic_system()
    # C (0.5) limits B+C->D; even with all A eventually funnelling through B, D cannot exceed the Y budget 0.5.
    end = sysB.integrate({A: 1.0, C: 0.5}, duration=200.0, n_samples=5, method="BDF").amounts[-1]
    assert end[D] <= 0.5 + 1e-9
    assert end[D] > 0.3                                          # the reaction genuinely ran


def test_reversible_reaction_relaxes_to_its_declared_equilibrium_constant():
    # an isolated A<->B (kf/kr = 2) relaxes to [B]/[A] = 2 at the fixed point (detailed balance).
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    sys = ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=2.0, kr=1.0))])
    end = sys.integrate({A: 1.0}, duration=50.0, n_samples=5, method="BDF").amounts[-1]
    assert abs(end[B] / end[A] - 2.0) < 1e-4


# -- Consumer C: a weak-acid dissociation through the SAME kernel (a different aqueous chemistry) -------------------
def _weak_acid_system(Ka: float):
    HA = Species.of("HA", {"H": 1, "Z": 1}, 0, Phase.AQUEOUS)
    Hp = Species.of("H+", {"H": 1}, +1, Phase.AQUEOUS)
    Am = Species.of("A-", {"Z": 1}, -1, Phase.AQUEOUS)
    kr = 1e6
    diss = Reaction("HA<->H+ + A-", ((HA, -1), (Hp, 1), (Am, 1)), MassActionReversible(kf=Ka * kr, kr=kr))
    return ChemicalSystem([HA, Hp, Am], [diss]), (HA, Hp, Am)


def test_weak_acid_matches_the_analytic_equilibrium_on_the_same_kernel():
    Ka, C0 = 1.75e-5, 0.1
    sysC, (HA, Hp, Am) = _weak_acid_system(Ka)
    traj = sysC.integrate({HA: C0}, duration=1.0, n_samples=20, method="BDF", rtol=1e-11, atol=1e-18)
    end = traj.amounts[-1]
    analytic = (-Ka + math.sqrt(Ka * Ka + 4 * Ka * C0)) / 2.0    # exact weak-acid [H+] quadratic root
    assert abs(end[Hp] - analytic) / analytic < 1e-3
    assert abs(end[Hp] - end[Am]) < 1e-12                        # charge balance [H+] = [A-] from stoichiometry
    assert traj.max_component_drift < 1e-12                      # elements + charge conserved to machine zero


def test_the_architectural_gate_both_consumers_use_the_same_integrate_method():
    # the gate: the SAME bound method ChemicalSystem.integrate evolves BOTH systems; neither needed a solver edit.
    sysB, (A, B, C, D) = _synthetic_system()
    sysC, (HA, Hp, Am) = _weak_acid_system(1e-5)
    assert type(sysB).integrate is type(sysC).integrate         # literally the same function object
    assert sysB.integrate({A: 1.0, C: 0.5}, duration=5.0, n_samples=3).solver_success
    assert sysC.integrate({HA: 0.1}, duration=1.0, n_samples=3).solver_success


# -- conservation algebra + fail-closed missing data --------------------------------------------------------------
def test_unbalanced_reaction_is_refused_at_construction():
    A = Species.of("A", {"X": 1})
    C = Species.of("C", {"Y": 1})
    with pytest.raises(ConservationError):
        ChemicalSystem([A, C], [Reaction("A->C?", ((A, -1), (C, 1)), MassActionIrreversible(1.0))])  # X->Y: not balanced


def test_charge_imbalance_is_refused_at_construction():
    # same elements but charge not conserved: HA(0) -> H+(+1) + A(0 charge) leaves +1 unbalanced.
    HA = Species.of("HA", {"H": 1, "Z": 1}, 0)
    Hp = Species.of("H+", {"H": 1}, +1)
    A0 = Species.of("A0", {"Z": 1}, 0)                           # neutral, so charge does NOT balance
    with pytest.raises(ConservationError):
        ChemicalSystem([HA, Hp, A0], [Reaction("bad", ((HA, -1), (Hp, 1), (A0, 1)), MassActionIrreversible(1.0))])


def test_rate_unknown_reaction_refuses_to_integrate_never_silent_zero():
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    sys = ChemicalSystem([A, B], [Reaction("A<->B?", ((A, -1), (B, 1)), RATE_UNKNOWN)])
    with pytest.raises(MissingKineticsError):
        sys.integrate({A: 1.0}, duration=1.0)


# -- typed species identity (plan section 2A): phase/charge distinguish, never formula alone -----------------------
def test_species_identity_distinguishes_phase_and_charge():
    na_aq = Species.of("Na+(aq)", {"Na": 1}, +1, Phase.AQUEOUS)
    na_metal = Species.of("Na(s)", {"Na": 1}, 0, Phase.SOLID)
    na_gas = Species.of("Na(g)", {"Na": 1}, 0, Phase.GAS)
    assert na_aq != na_metal and na_metal != na_gas and na_aq != na_gas
    # a system treats them as three distinct conserved entities (a charge row separates the ion).
    sys = ChemicalSystem([na_aq, na_metal, na_gas], [])
    assert "charge" in sys.component_labels
    assert sys.component_amounts({na_aq: 1.0})["charge"] == 1.0
    assert sys.component_amounts({na_metal: 1.0})["charge"] == 0.0


def test_missing_thermo_data_is_a_first_class_status_never_faked():
    sp = Species.of("mystery", {"Q": 1}, 0, Phase.AQUEOUS, data_status="NONE")
    assert sp.data_status == "NONE"                              # UNKNOWN stays UNKNOWN; no fabricated constant
    with pytest.raises(KernelError):
        Species.of("bad", {"Q": 1}, 0, Phase.AQUEOUS, data_status="TOTALLY_SOURCED_TRUST_ME")


# -- external source/sink q: conserved totals change by EXACTLY its integral, not spuriously -----------------------
def test_external_source_changes_components_by_exactly_its_integral():
    # feed species A into an inert system at a constant rate q; total X rises by q * duration, exactly.
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    sys = ChemicalSystem([A, B], [Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=1.0, kr=1.0))])
    dur, qdot = 10.0, 0.3
    traj = sys.integrate({A: 0.0, B: 0.0}, duration=dur, n_samples=5, source={A: qdot}, method="BDF")
    end = traj.amounts[-1]
    assert abs((end[A] + end[B]) - qdot * dur) < 1e-6           # total X == integral of the feed, nothing invented


# -- the headless demo (plan section F: reproducible frames, strict JSON, CSV) -------------------------------------
def test_demo_report_is_strict_json_and_conserves():
    from experiments.sandbox_foundation import general_chemistry_demo as demo
    report = demo.run_pack()
    text = json.dumps(report, allow_nan=False)                  # raises if any NaN/Infinity leaked in
    for tok in ("NaN", "Infinity"):
        assert tok not in text
    for sc in report["scenarios"]:
        assert sc["trust"]["conservation"] == "CERTIFIED"
        assert sc["trust"]["kinetic_data"] == "ASSUMED"         # the rates are synthetic/declared, never measured
        assert sc["trust"]["external_measured_validation"] == "UNAVAILABLE"
        assert sc["numerics"]["positivity_held"] is True


def test_demo_weak_acid_cross_check_agrees_and_digest_is_deterministic():
    from experiments.sandbox_foundation import general_chemistry_demo as demo
    sc = demo.run_scenario("weak_acid")
    a = sc["analytic_cross_check"]
    assert abs(a["kinetic_fixed_point"] - a["analytic_weak_acid_root"]) / a["analytic_weak_acid_root"] < 1e-3
    assert demo.model_source_digest()["sha256"] == demo.model_source_digest()["sha256"]
    assert len(demo.model_source_digest()["sha256"]) == 64


def test_demo_main_single_scenario_writes_json_and_csv(tmp_path):
    from experiments.sandbox_foundation import general_chemistry_demo as demo
    jf, cf = tmp_path / "r.json", tmp_path / "r.csv"
    assert demo.main(["--scenario", "synthetic", "--json", str(jf), "--csv", str(cf)]) == 0
    obj = json.loads(jf.read_text())
    assert [s["scenario"] for s in obj["scenarios"]] == ["synthetic"]
    rows = cf.read_text().splitlines()
    assert rows[0] == "scenario,time_s,species,amount_mol" and len(rows) > 10
