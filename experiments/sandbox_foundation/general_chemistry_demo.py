"""OPERATION XIV Track B / XV Wave A -- the general-kernel headless demo.

Runs TWO unrelated chemistries through the SAME general kernel (experiments.sandbox_foundation.general_kernel),
proving the architectural gate with a runnable command rather than a prose claim:

    python -m experiments.sandbox_foundation.general_chemistry_demo [--json OUT.json] [--csv OUT.csv]
                                                                    [--scenario synthetic|weak_acid]

  * ``synthetic``  -- an abstract A<->B, B+C->D network (no acetate, CO2 or sodium anywhere);
  * ``weak_acid``  -- a weak-acid dissociation HA <-> H+ + A- whose kinetic fixed point matches the ANALYTIC
                      weak-acid equilibrium (a different aqueous chemistry, same integrator).

Output is a strict-JSON report (no NaN/Infinity), an optional CSV time series, a terminal dashboard, and a
deterministic MODEL/RUN digest (XV-1E: the digest binds every numerically operative input -- stoichiometry, rate
constants, volume, initial amounts, solver config -- not just names).  Conserved totals (elements + charge) and
positivity are reported as VERIFIED numerical facts carried by the trajectory's DERIVED receipt; a quantity the model
does not supply is null, never a fabricated 0.  Nothing here is a measured validation -- the rates are
synthetic/declared (the weak acid's kf/kr ratio encodes a sourced Ka), so the admitted tier is ASSUMED_PARAMETER;
the weak-acid scenario additionally earns NUMERICALLY_VERIFIED via an INDEPENDENT analytic cross-check.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys

from experiments.sandbox_foundation.claim_tiers import NUMERICALLY_VERIFIED, REFUSED
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    MassActionIrreversible,
    MassActionReversible,
    Phase,
    Reaction,
    Species,
)

#: a weak acid's acid-dissociation constant (acetic-acid-like pKa 4.756); its kf/kr ratio encodes it.
_KA_WEAK_ACID = 1.75e-5

_SOLVER = {"method": "BDF", "rtol": 1e-11, "atol": 1e-18, "n_samples": 20}


def _synthetic_system():
    A = Species.of("A", {"X": 1})
    B = Species.of("B", {"X": 1})
    C = Species.of("C", {"Y": 1})
    D = Species.of("D", {"X": 1, "Y": 1})
    rxns = [
        Reaction("A<->B", ((A, -1), (B, 1)), MassActionReversible(kf=2.0, kr=1.0)),
        Reaction("B+C->D", ((B, -1), (C, -1), (D, 1)), MassActionIrreversible(k=5.0)),
    ]
    return ChemicalSystem([A, B, C, D], rxns), {A: 1.0, C: 0.5}, 20.0


def _weak_acid_system():
    HA = Species.of("HA", {"H": 1, "Z": 1}, 0, Phase.AQUEOUS)
    Hp = Species.of("H+", {"H": 1}, +1, Phase.AQUEOUS)
    Am = Species.of("A-", {"Z": 1}, -1, Phase.AQUEOUS)
    kr = 1e6
    rxns = [Reaction("HA<->H+ + A-", ((HA, -1), (Hp, 1), (Am, 1)),
                     MassActionReversible(kf=_KA_WEAK_ACID * kr, kr=kr))]
    return ChemicalSystem([HA, Hp, Am], rxns), {HA: 0.1}, 1.0


_SCENARIOS = {"synthetic": _synthetic_system, "weak_acid": _weak_acid_system}


def _finite_or_none(x):
    return float(x) if (isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)) else None


# ------------------------------------------------------------------ deterministic MODEL / RUN identity (XV-1E)
def _ratelaw_payload(rl):
    if rl is None:
        return ["RATE_UNKNOWN"]
    if isinstance(rl, MassActionReversible):
        return ["MassActionReversible", float(rl.kf), float(rl.kr)]
    if isinstance(rl, MassActionIrreversible):
        return ["MassActionIrreversible", float(rl.k)]
    return [type(rl).__name__]


def _species_payload(sp):
    return [sp.name, [list(p) for p in sp.composition], sp.charge, sp.phase.value, sp.data_status]


def model_identity(system) -> dict:
    """Every numerically operative MODEL input -- species (composition/charge/phase), reactions (signed stoichiometry
    + rate-law parameters), reactor volume.  Changing kf, kr, a coefficient, or the volume changes this (XV-1E)."""
    return {
        "species": [_species_payload(sp) for sp in system.species],
        "reactions": [[r.name, [[sp.name, coeff] for sp, coeff in r.stoich], _ratelaw_payload(r.rate_law),
                       bool(r.elementary)] for r in system.reactions],
        "volume_L": round(float(system.volume_L), 12),
    }


def model_identity_digest(system) -> str:
    return hashlib.sha256(json.dumps(model_identity(system), sort_keys=True).encode()).hexdigest()


def run_identity(system, n0: dict, duration: float, source: dict | None = None) -> dict:
    """The MODEL plus the initial-value problem: initial amounts, external source, duration and solver config.
    Changing any initial amount changes the RUN digest while the MODEL digest stays fixed (XV-1E)."""
    return {
        "model": model_identity(system),
        "initial_amounts": sorted([sp.name, round(float(v), 12)] for sp, v in n0.items()),
        "source": sorted([sp.name, round(float(v), 12)] for sp, v in (source or {}).items()),
        "duration_s": round(float(duration), 12),
        "solver": dict(_SOLVER),
    }


def run_identity_digest(system, n0: dict, duration: float, source: dict | None = None) -> str:
    return hashlib.sha256(json.dumps(run_identity(system, n0, duration, source), sort_keys=True).encode()).hexdigest()


def model_source_digest() -> dict:
    """A deterministic digest of the demo's declared systems, binding the FULL model identity of each scenario (not
    just names), so a frame is reproducibly tied to its governing science (XV-1E)."""
    payload = []
    for name in sorted(_SCENARIOS):
        system, _n0, _dur = _SCENARIOS[name]()
        payload.append([name, model_identity(system)])
    blob = json.dumps(payload, sort_keys=True).encode()
    return {"sha256": hashlib.sha256(blob).hexdigest(), "scenarios": sorted(_SCENARIOS)}


def run_scenario(name: str) -> dict:
    """Run one declared scenario through the general kernel and return a strict-JSON-able frame record."""
    if name not in _SCENARIOS:
        raise ValueError(f"unknown scenario {name!r}; choose from {sorted(_SCENARIOS)}")
    system, n0, duration = _SCENARIOS[name]()
    traj = system.integrate(n0, duration=duration, n_samples=_SOLVER["n_samples"], method=_SOLVER["method"],
                            rtol=_SOLVER["rtol"], atol=_SOLVER["atol"])
    rc = traj.receipt
    end = traj.amounts[-1]
    comp0 = system.component_amounts(n0)
    comp_end = system.component_amounts(end)

    analytic = None
    scenario_tier = rc.admitted_tier
    if name == "weak_acid":
        Ka, C0 = _KA_WEAK_ACID, n0[system.species[0]]
        hp = [sp for sp in system.species if sp.name == "H+"][0]
        root = (-Ka + math.sqrt(Ka * Ka + 4 * Ka * C0)) / 2.0
        kin = _finite_or_none(end[hp])
        agrees = kin is not None and abs(kin - root) / root < 1e-3
        analytic = {
            "quantity": "equilibrium [H+] (mol/L, V=1)",
            "kinetic_fixed_point": kin,
            "analytic_weak_acid_root": _finite_or_none(root),
            "agrees_within_1e-3": bool(agrees),
        }
        # the EQUILIBRIUM [H+] is set by Ka = kf/kr (the sourced ratio), not the assumed absolute rates, and an
        # INDEPENDENT analytic route (the exact weak-acid quadratic root) agrees to <1e-3 -> that equilibrium quantity
        # earns NUMERICALLY_VERIFIED, which SUPERSEDES the structural tier.  (The transient trajectory remains
        # ASSUMED_PARAMETER -- admitted_tier -- because it depends on the assumed absolute kf, kr.)
        if agrees and rc.structural_tier != REFUSED:
            scenario_tier = NUMERICALLY_VERIFIED

    return {
        "scenario": name,
        "species": [sp.name for sp in system.species],
        "reactions": [r.name for r in system.reactions],
        "volume_L": _finite_or_none(system.volume_L),
        "components_conserved": {
            lbl: {"initial": _finite_or_none(comp0[lbl]), "final": _finite_or_none(comp_end[lbl]),
                  "drift": _finite_or_none(abs(comp_end[lbl] - comp0[lbl]))}
            for lbl in system.component_labels},
        "final_amounts": {sp.name: _finite_or_none(end[sp]) for sp in system.species},
        "time_series": [
            {"time_s": _finite_or_none(t), **{sp.name: _finite_or_none(fr[sp]) for sp in system.species}}
            for t, fr in zip(traj.times, traj.amounts)],
        "numerics": {
            "integrator": traj.integrator,
            "solver_success": traj.solver_success,
            "max_component_drift": _finite_or_none(traj.max_component_drift),
            "external_ledger_residual": _finite_or_none(traj.external_ledger_residual),
            "min_inventory": _finite_or_none(traj.min_amount),
            "positivity_held": bool(rc.positivity_held),
        },
        "analytic_cross_check": analytic,       # null for scenarios without a closed-form check
        "receipt": {                            # DERIVED, non-self-certifying (XV-1E)
            "structural_tier": rc.structural_tier,
            "declared_kinetic_tier": rc.declared_kinetic_tier,
            "admitted_tier": rc.admitted_tier,
            "scenario_tier": scenario_tier,     # admitted, plus any independent cross-check this scenario earned
            "external_ledger_closed": bool(rc.external_ledger_closed),
            "tolerance": _finite_or_none(rc.tolerance),
        },
        "trust": {                              # kept for backward compatibility; the receipt is the authority
            "conservation": "CERTIFIED" if rc.external_ledger_closed else "VIOLATED",
            "numerical_solver": "VERIFIED" if traj.solver_success else "FAILED",
            "kinetic_data": "ASSUMED",           # the rates are synthetic/declared, never measured
            "external_measured_validation": "UNAVAILABLE",
        },
        "run_digest": run_identity_digest(system, n0, duration),
        "caveats": list(traj.caveats),
    }


def run_pack() -> dict:
    return {"scenarios": [run_scenario(n) for n in sorted(_SCENARIOS)],
            "model_source_digest": model_source_digest()}


def _dashboard(report: dict) -> str:
    out = io.StringIO()
    out.write("=== SmartChem general-kernel demo (OPERATION XIV Track B / XV Wave A) ===\n")
    for sc in report["scenarios"]:
        out.write(f"\n[{sc['scenario']}]  species={sc['species']}  reactions={sc['reactions']}  "
                  f"V={sc['volume_L']} L\n")
        out.write(f"  integrator={sc['numerics']['integrator']}  "
                  f"conservation={sc['trust']['conservation']}  "
                  f"max_drift={sc['numerics']['max_component_drift']:.2e}  "
                  f"ledger_residual={sc['numerics']['external_ledger_residual']:.2e}  "
                  f"positivity={'ok' if sc['numerics']['positivity_held'] else 'VIOLATED'}\n")
        out.write(f"  tier: structural={sc['receipt']['structural_tier']}  "
                  f"admitted={sc['receipt']['admitted_tier']}  scenario={sc['receipt']['scenario_tier']}\n")
        out.write("  final: " + ", ".join(f"{k}={v:.4g}" for k, v in sc["final_amounts"].items()
                                           if v is not None) + "\n")
        if sc["analytic_cross_check"]:
            a = sc["analytic_cross_check"]
            out.write(f"  cross-check: kinetic={a['kinetic_fixed_point']:.4e} vs "
                      f"analytic={a['analytic_weak_acid_root']:.4e}  "
                      f"agrees={a['agrees_within_1e-3']}\n")
    out.write(f"\nmodel digest: {report['model_source_digest']['sha256'][:16]}...\n")
    return out.getvalue()


def _write_csv(report: dict, path: str) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "time_s", "species", "amount_mol"])
        for sc in report["scenarios"]:
            for row in sc["time_series"]:
                for sp in sc["species"]:
                    w.writerow([sc["scenario"], row["time_s"], sp, row[sp]])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SmartChem general-kernel headless demo (OPERATION XIV Track B / XV)")
    ap.add_argument("--json", metavar="OUT.json", help="write the strict-JSON report here")
    ap.add_argument("--csv", metavar="OUT.csv", help="write the CSV time series here")
    ap.add_argument("--scenario", choices=sorted(_SCENARIOS), help="run a single scenario (default: the pack)")
    args = ap.parse_args(argv)

    report = ({"scenarios": [run_scenario(args.scenario)], "model_source_digest": model_source_digest()}
              if args.scenario else run_pack())
    text = json.dumps(report, allow_nan=False, indent=2)
    if args.json:
        with open(args.json, "w") as fh:
            fh.write(text)
    if args.csv:
        _write_csv(report, args.csv)
    sys.stdout.write(_dashboard(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
