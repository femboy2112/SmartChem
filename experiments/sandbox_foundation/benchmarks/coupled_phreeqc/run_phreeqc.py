"""Run the MIXED vinegar/bicarbonate decks through PHREEQC -- the INDEPENDENT instrument.

Toxic Rick rewrite (OPERATION XVIII Track D). The prior version was triple-broken, and every
break would have shipped a wrong or absent number:
  (1) it passed NO database_directory, so phreeqpython never found the fetched DB;
  (2) it hashed phreeqpython's OWN bundled copy of the DB, not the file we actually fetched --
      a provenance lie waiting to happen;
  (3) it skipped the PREREGISTRATION.md:39-41 molar-match entirely (`units mol/l` is not a true
      molar input), so code-molar vs PHREEQC-molal would have been compared off-basis.
All three are fixed. The acetate benchmark's `run_any` fixed point is generalized from ONE
total to THREE (acetate, carbonate carbon, Na) because the mixed grid carries all three.

Species names are read off the LIVE solver, never guessed: minteq.v4 names aqueous CO2
"H2CO3", llnl names it "CO2", and BOTH carry Na-carbonate / Na-acetate ion pairs that a guessed
table would have silently dropped from the mass-balance totals. A species above threshold that
is NOT in the table raises -- Toxic Rick fails closed rather than fudge a formula weight.

Run with the dev venv that actually has phreeqpython (absent from the committed baseline, by
design -- that is WHY the committed PHREEQC column was null until this run signed it):
    python -I run_phreeqc.py
Reads the gitignored db_dl/*.dat (fetch via reproduce.sh). Writes phreeqc_results.json (NOT
committed). Deterministic. Tool-computed numbers only; nothing is hand-tuned.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# `python -I` (isolated mode, implies -P on 3.11+) does NOT prepend the script's own directory to
# sys.path, so a bare `from cases import ...` dies with ModuleNotFoundError. Toxic Morty face-planted
# on exactly that on the first run and handed it back straight instead of guessing -- credit the
# roach where it's due. Put our OWN trusted dir on the path explicitly, so the -I posture (ignore
# env / user-site, which matters because db_dl holds fetched files) still resolves the sibling.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import CASES, DATABASES   # noqa: E402 (must follow the sys.path insert above)

HERE = Path(__file__).resolve().parent
DB_DIR = HERE / "db_dl"

# name -> (charge, nNa, nAcetate, nCarbonateC, gram_formula_weight). Keyed by the names PHREEQC
# ACTUALLY emits for each DB (confirmed live, both DBs, see module docstring). Carbonate carbon
# only counts the C(4) system (CO2/HCO3-/CO3-2 + Na pairs); acetate's own carbons are NOT C(4).
SP = {
    "H+":            ( 1, 0, 0, 0,   1.008),
    "OH-":           (-1, 0, 0, 0,  17.007),
    "Na+":           ( 1, 1, 0, 0,  22.990),
    "Acetate-":      (-1, 0, 1, 0,  59.044),
    "H(Acetate)":    ( 0, 0, 1, 0,  60.052),   # minteq.v4 undissociated acetic acid
    "HAcetate":      ( 0, 0, 1, 0,  60.052),   # llnl undissociated acetic acid
    "Na(Acetate)":   ( 0, 1, 1, 0,  82.034),   # minteq.v4 Na-acetate ion pair
    "NaAcetate":     ( 0, 1, 1, 0,  82.034),   # llnl Na-acetate ion pair
    "Na(Acetate)2-": (-1, 1, 2, 0, 141.078),   # llnl 1:2 Na-acetate pair
    "CO2":           ( 0, 0, 0, 1,  44.009),   # llnl aqueous CO2
    "H2CO3":         ( 0, 0, 0, 1,  62.024),   # minteq.v4 aqueous CO2 (named H2CO3)
    "HCO3-":         (-1, 0, 0, 1,  61.016),
    "CO3-2":         (-2, 0, 0, 1,  60.008),
    "NaHCO3":        ( 0, 1, 0, 1,  84.006),   # Na-bicarbonate ion pair (both DBs)
    "NaCO3-":        (-1, 1, 0, 1,  82.998),   # Na-carbonate ion pair (both DBs)
    "NaOH":          ( 0, 1, 0, 0,  39.997),   # llnl Na-hydroxide pair
}
IGNORE = {"H2O", "H2", "O2"}   # solvent + ~1e-30 redox artefacts; never a chemistry carrier here


def run(database, c_ac, c_c, na, units):
    from phreeqpython import PhreeqPython
    # DB_DIR is a pathlib.Path on purpose: phreeqpython 1.6.2 does `database_directory / database`
    # and a str blows up with "unsupported operand type(s) for /". That was defect (1)+(2).
    pp = PhreeqPython(database=database, database_directory=DB_DIR)
    lines = ["SOLUTION 1", f"  units {units}", "  temp 25", "  pH 7 charge"]
    if na > 0:
        lines.append(f"  Na {na!r}")
    if c_ac > 0:
        lines.append(f"  Acetate {c_ac!r}")
    if c_c > 0:
        lines.append(f"  C(4) {c_c!r}")
    lines.append("END")
    pp.ip.run_string("\n".join(lines))
    s = pp.get_solution(1)
    mol = dict(s.species_molalities)

    unk = [k for k, v in mol.items() if k not in SP and k not in IGNORE and v > 1e-12]
    if unk:   # fail closed: an unmodelled carrier silently corrupts the totals. Do NOT widen IGNORE.
        raise RuntimeError(f"unmodelled species > 1e-12 mol/kgw in {database}: "
                           + ", ".join(f"{k}={mol[k]:.3e}" for k in unk))

    keys = [k for k in SP if k in mol]
    # molality -> molarity via PHREEQC's own density (its water-only volume is NOT solution volume).
    solute_g_per_kgw = sum(mol[k] * SP[k][4] for k in keys)
    kgw_per_L = s.density / (1.0 + solute_g_per_kgw / 1000.0)   # kg water per L solution
    molar = {k: mol[k] * kgw_per_L for k in keys}
    return {
        "db": database, "units": units, "c_ac": c_ac, "c_c": c_c, "na": na,
        "pH": s.pH, "I_molal": s.I, "density": s.density, "mass_kgw": s.mass,
        "kgw_per_L_solution": kgw_per_L,
        "acetate_total_molarity": sum(molar[k] * SP[k][2] for k in keys),
        "carbon_total_molarity":  sum(molar[k] * SP[k][3] for k in keys),
        "na_total_molarity":      sum(molar[k] * SP[k][1] for k in keys),
        "charge_residual_molal":  sum(mol[k] * SP[k][0] for k in keys),
        "molality": {k: mol[k] for k in keys},
        "molarity": {k: molar[k] for k in keys},
    }


def run_any(database, c_ac, c_c, na, units):
    """Molar-match (PREREGISTRATION.md:39-41). Feed mol/kgw and fixed-point the kgw/L factor
    until the sum-of-species MOLARITIES reproduce the requested mol/L totals. One scalar factor
    serves all three totals -- it is a solution-wide density effect, not a per-species fudge."""
    if units == "mol/kgw":
        return run(database, c_ac, c_c, na, "mol/kgw")
    f = 0.9970
    for _ in range(80):
        o = run(database, c_ac / f, c_c / f, na / f, "mol/kgw")
        fn = o["kgw_per_L_solution"]
        if abs(fn - f) < 1e-13:
            break
        f = fn
    o["units"] = "molar-matched"
    o["requested"] = {"c_ac": c_ac, "c_c": c_c, "na": na}
    o["fixed_point_f"] = f
    o["match_residual"] = {   # the honest PROOF the match matched -- not a claim, a number
        "acetate": o["acetate_total_molarity"] - c_ac,
        "carbon":  o["carbon_total_molarity"] - c_c,
        "na":      o["na_total_molarity"] - na,
    }
    return o


def main():
    results = {"databases": {}, "cases": []}
    for database in DATABASES:
        db_file = DB_DIR / database
        sha = hashlib.sha256(db_file.read_bytes()).hexdigest()   # the FETCHED file, defect (2) fixed
        results["databases"][database] = {"database_sha256": sha, "path": str(db_file)}
        print(f"{database}: sha256 {sha}")
    worst = 0.0
    for case_id, desc, c_ac, c_c, na, _exp in CASES:
        for database in DATABASES:
            for units in ("mol/kgw", "molar-matched"):
                rec = {"case": case_id, "desc": desc}
                rec.update(run_any(database, c_ac, c_c, na, units))
                results["cases"].append(rec)
                if units == "molar-matched":
                    r = rec["match_residual"]
                    worst = max(worst, abs(r["acetate"]), abs(r["carbon"]), abs(r["na"]))
                    print(f"  {case_id:4s} {database:14s} molar-matched pH={rec['pH']:.4f} I={rec['I_molal']:.4f} "
                          f"resid(ac,c,na)=({r['acetate']:.1e},{r['carbon']:.1e},{r['na']:.1e})")
    (HERE / "phreeqc_results.json").write_text(json.dumps(results, indent=2, allow_nan=False))
    print(f"wrote phreeqc_results.json; worst molar-match residual = {worst:.2e} (gate: < 1e-9)")
    if worst >= 1e-9:   # dead-man on the molar match: a non-converged match is a FAILURE, not a pass
        raise SystemExit(f"MOLAR-MATCH FAILED: worst residual {worst:.2e} >= 1e-9")


if __name__ == "__main__":
    main()
