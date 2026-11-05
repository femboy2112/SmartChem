"""OPERATION XXI section 6 -- Na-carbonate ION-PAIR ablation with PHREEQC as the instrument.

Ooh yeah, can do!  One question: how much of a high-Na carbonate pH gap is the two minteq.v4 Na-carbonate ion pairs?
One instrument: PHREEQC itself, run TWICE -- WITH the pairs (minteq.v4.dat verbatim) and with EXACTLY those two
SOLUTION_SPECIES reactions deleted (minteq.v4.nopairs.dat) -- same program, same input, same everything else.
delta_pH = pH(with) - pH(no) IS the pair contribution, in database-sourced constants.  NO custom solver, NO tuning:
every log_k / delta_h is the database's own, and SmartChem's carbonate_equilibrium.py is only IMPORTED (read-only).

This harness writes RAW numbers.  It does not write a verdict (the claim ledger is the orchestrator's).

Run from the repo root in a venv that has phreeqpython + numpy/scipy:
    PYTHONPATH=. python -m experiments.sandbox_foundation.benchmarks.carbonate_na_pair_s6.run_na_pair_ablation_s6
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_DIR = HERE / "db"
DB_WITH = "minteq.v4.dat"
DB_NO = "minteq.v4.nopairs.dat"
GRID = HERE.parent / "carbonate_phreeqc" / "grid.json"
S1_TABLE = HERE.parent / "carbonate_phreeqc" / "comparison_table.json"   # phreeqc.dat context column (read-only)

ORIGINAL_SHA256 = "4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3"
# The two reactions ablated -- header (equation) lines, VERBATIM from minteq.v4.dat:
PAIR_REACTIONS = ("Na+ + CO3-2 = NaCO3-", "Na+ + H+ + CO3-2 = NaHCO3")
PAIR_CONSTANTS = {   # for the record; asserted against the removed text by the test (never edited)
    "Na+ + CO3-2 = NaCO3-": {"log_k": 1.27, "delta_h_kJ": -20.35},
    "Na+ + H+ + CO3-2 = NaHCO3": {"log_k": 10.079, "delta_h_kJ": -28.3301},
}

# NIST SRM 191d (certificate Table 1 / Table A1; same numbers as run_unit_convention_s5.CERT)
NIST_TABLE1, NIST_TABLE1_U = 10.014, 0.010
NIST_TABLEA1, NIST_TABLEA1_UR = 10.0137, 0.0029
NIST_EACH_MOLALITY = 0.025

# PREREGISTERED holdout (PREREGISTRATION.md section 5, item 3)
HOLDOUT_CT = 0.05
HOLDOUT_NA_OVER_C = (0.5, 1.0, 1.5)
OOD_I_MAX, OOD_PH_MAX = 0.5, 12.0


def sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def split_reaction_blocks(lines):
    """Return [(start_idx, end_idx_exclusive)] for each PAIR_REACTIONS block.  A block = its un-indented equation line
    plus every following indented/comment line, up to the next un-indented line."""
    spans = []
    for i, ln in enumerate(lines):
        if ln.rstrip("\n") in PAIR_REACTIONS:
            j = i + 1
            while j < len(lines) and lines[j][:1] in (" ", "\t"):
                j += 1
            spans.append((i, j))
    return spans


def build_nopairs_text(original_text: str):
    lines = original_text.splitlines(keepends=True)
    spans = split_reaction_blocks(lines)
    if len(spans) != len(PAIR_REACTIONS):
        raise RuntimeError(f"expected exactly {len(PAIR_REACTIONS)} pair reaction blocks, found {len(spans)}")
    drop = {k for a, b in spans for k in range(a, b)}
    removed = "".join(lines[k] for k in sorted(drop))
    kept = "".join(ln for k, ln in enumerate(lines) if k not in drop)
    return kept, removed, spans


def ensure_databases():
    """Verify the original DB's sha256, (re)build the no-pairs DB deterministically, return both shas + removed text."""
    orig = DB_DIR / DB_WITH
    sha_o = sha256_file(orig)
    if sha_o != ORIGINAL_SHA256:
        raise RuntimeError(f"{orig} sha256 {sha_o} != pinned {ORIGINAL_SHA256}")
    kept, removed, spans = build_nopairs_text(orig.read_bytes().decode("utf-8"))
    (DB_DIR / DB_NO).write_bytes(kept.encode("utf-8"))
    return {"original_sha256": sha_o, "nopairs_sha256": sha256_file(DB_DIR / DB_NO),
            "removed_text": removed, "removed_line_spans_1based": [[a + 1, b] for a, b in spans]}


# ---------------------------------------------------------------- PHREEQC drivers
_SEL_WITH = """
SELECTED_OUTPUT 1
    -reset false
    -pH true
    -ionic_strength true
    -totals C(4) Na
    -molalities CO2 HCO3- CO3-2 Na+ NaCO3- NaHCO3
"""
_SEL_NO = """
SELECTED_OUTPUT 1
    -reset false
    -pH true
    -ionic_strength true
    -totals C(4) Na
    -molalities CO2 HCO3- CO3-2 Na+
"""


def _run(pp, inp, with_pairs):
    pp.ip.run_string((_SEL_WITH if with_pairs else _SEL_NO) + inp)
    out = pp.ip.get_selected_output_array()
    # an EQUILIBRIUM_PHASES step writes the initial solution first and the equilibrated state LAST -> take LAST row
    return dict(zip(out[0], out[-1]))


def _open_input(p_co2_atm):
    return f"""
SOLUTION 1
    temp 25
EQUILIBRIUM_PHASES 1
    CO2(g) {math.log10(p_co2_atm)} 10.0
END"""


def _closed_input(total_carbon, sodium):
    return f"""
SOLUTION 1
    temp 25
    units mol/kgw
    Na {sodium}
    C(4) {total_carbon}
    pH 7 charge
END"""


def _case_input(c):
    if c["mode"] == "open":
        assert c["sodium"] == 0.0
        return _open_input(c["p_co2_atm"])
    return _closed_input(c["total_carbon"], c["sodium"])


def _g(r, key):
    return float(r.get(key, 0.0))


def _speciation(r, with_pairs):
    na_t = _g(r, "Na(mol/kgw)")
    d = {"Na_total_molal": na_t, "m_Na_free": _g(r, "m_Na+(mol/kgw)"),
         "m_CO2": _g(r, "m_CO2(mol/kgw)"), "m_HCO3": _g(r, "m_HCO3-(mol/kgw)"), "m_CO3": _g(r, "m_CO3-2(mol/kgw)")}
    if with_pairs:
        d["m_NaCO3-"] = _g(r, "m_NaCO3-(mol/kgw)")
        d["m_NaHCO3"] = _g(r, "m_NaHCO3(mol/kgw)")
        d["Na_bound_fraction"] = ((d["m_NaCO3-"] + d["m_NaHCO3"]) / na_t) if na_t > 0 else 0.0
    return d


def run_pair(pp_with, pp_no, inp):
    rw, rn = _run(pp_with, inp, True), _run(pp_no, inp, False)
    ph_w, ph_n = float(rw["pH"]), float(rn["pH"])
    i_w, i_n = float(rw["mu"]), float(rn["mu"])
    return {
        "pH_with": ph_w, "pH_no": ph_n, "delta_pH": ph_w - ph_n,
        "I_with": i_w, "I_no": i_n, "delta_I": i_w - i_n,
        "speciation_with": _speciation(rw, True), "speciation_no": _speciation(rn, False),
        "finite": bool(all(map(math.isfinite, (ph_w, ph_n, i_w, i_n)))),
    }


# ---------------------------------------------------------------- SmartChem (read-only import of the unchanged model)
def _smartchem_closed(total_carbon, sodium):
    from experiments.sandbox_foundation.carbonate_equilibrium import CarbonateWaterSystem, solve
    from experiments.sandbox_foundation.aqueous_equilibrium import NumericalVerificationError, OutOfSourceDomainError
    try:
        r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=total_carbon, sodium_M=sodium,
                                       activity_model="davies"))
    except (NumericalVerificationError, OutOfSourceDomainError) as e:
        return {"refused": type(e).__name__, "reason": str(e)[:160]}
    return {"pH_activity": float(r.pH_activity), "I": float(r.ionic_strength_M), "verdict": r.verdict}


def _smartchem_from_committed(cid):
    """SmartChem pH for the existing grid, read from the committed code_results.json (produced by run_code.py)."""
    code = json.loads((HERE.parent / "carbonate_phreeqc" / "code_results.json").read_text())
    dav = code["cases"][cid]["davies"]
    if "refused" in dav:
        return {"refused": dav["refused"], "reason": dav["reason"]}
    return {"pH_activity": float(dav["pH_activity"]), "I": float(dav["I"]), "verdict": dav["verdict"]}


def _signed(a, b):
    return None if (a is None or b is None) else a - b


def evaluate() -> dict:
    from phreeqpython import PhreeqPython

    dbinfo = ensure_databases()
    pp_with = PhreeqPython(database=DB_WITH, database_directory=DB_DIR)
    pp_no = PhreeqPython(database=DB_NO, database_directory=DB_DIR)
    s1_phreeqc_dat = json.loads(S1_TABLE.read_text())

    # ---- 1. existing carbonate grid ----
    grid = json.loads(GRID.read_text())
    cases = {}
    for c in grid["cases"]:
        res = run_pair(pp_with, pp_no, _case_input(c))
        sc = _smartchem_from_committed(c["id"])
        res.update({"mode": c["mode"], "desc": c["desc"], "sodium": c["sodium"],
                    "smartchem_no_pairs_davies": sc,
                    "phreeqc_dat_context_pH": s1_phreeqc_dat["rows"].get(c["id"], {}).get("ph_phreeqc")})
        spc = sc.get("pH_activity")
        res["three_way"] = {
            "smartchem": spc, "phreeqc_no_pairs": res["pH_no"], "phreeqc_with_pairs": res["pH_with"],
            "smartchem_minus_phreeqc_no": _signed(spc, res["pH_no"]),
            "smartchem_minus_phreeqc_with": _signed(spc, res["pH_with"]),
            "phreeqc_with_minus_no": res["delta_pH"],
        }
        cases[c["id"]] = res

    # ---- 2. NIST SRM 191d composition ----
    na, ct = 3 * NIST_EACH_MOLALITY, 2 * NIST_EACH_MOLALITY
    nist = run_pair(pp_with, pp_no, _closed_input(ct, na))
    from experiments.sandbox_foundation.benchmarks.measured_carbonate_srm191d import run_unit_convention_s5 as S5
    sc_molal = S5._solve_davies(S5.MOLALITY_EACH)
    sc_molar = {t: S5._solve_davies(S5.molarity_each(r)) for t, r in
                (("lo", S5.DENSITY_INTERVAL_G_PER_ML[0]), ("mid", S5.DENSITY_MID_G_PER_ML),
                 ("hi", S5.DENSITY_INTERVAL_G_PER_ML[1]))}
    nist.update({
        "composition": {"Na_molal": na, "C4_molal": ct, "each_salt_molality": NIST_EACH_MOLALITY},
        "certified": {"table1_pH_S": NIST_TABLE1, "table1_U": NIST_TABLE1_U,
                      "tableA1_pH_S": NIST_TABLEA1, "tableA1_U_R": NIST_TABLEA1_UR},
        "residual_with_vs_table1": nist["pH_with"] - NIST_TABLE1,
        "residual_no_vs_table1": nist["pH_no"] - NIST_TABLE1,
        "residual_with_vs_tableA1": nist["pH_with"] - NIST_TABLEA1,
        "residual_no_vs_tableA1": nist["pH_no"] - NIST_TABLEA1,
        "abs_residual_with_vs_table1": abs(nist["pH_with"] - NIST_TABLE1),
        "abs_residual_no_vs_table1": abs(nist["pH_no"] - NIST_TABLE1),
        "abs_residual_with_vs_tableA1": abs(nist["pH_with"] - NIST_TABLEA1),
        "abs_residual_no_vs_tableA1": abs(nist["pH_no"] - NIST_TABLEA1),
        "pairs_move_pH_toward_table1": bool(abs(nist["pH_with"] - NIST_TABLE1) < abs(nist["pH_no"] - NIST_TABLE1)),
        "pairs_move_pH_toward_tableA1": bool(abs(nist["pH_with"] - NIST_TABLEA1) < abs(nist["pH_no"] - NIST_TABLEA1)),
        "within_table1_U": {"with": bool(abs(nist["pH_with"] - NIST_TABLE1) <= NIST_TABLE1_U),
                            "no": bool(abs(nist["pH_no"] - NIST_TABLE1) <= NIST_TABLE1_U)},
        "within_tableA1_U_R": {"with": bool(abs(nist["pH_with"] - NIST_TABLEA1) <= NIST_TABLEA1_UR),
                               "no": bool(abs(nist["pH_no"] - NIST_TABLEA1) <= NIST_TABLEA1_UR)},
        "smartchem_unchanged_davies": {"molality_fed_XIX_pH": sc_molal, "molarity_fed_density_interval_pH": sc_molar},
    })

    # ---- 3. FRESH preregistered Na-sweep holdout ----
    holdout = {}
    for ratio in HOLDOUT_NA_OVER_C:
        na_h = round(ratio * HOLDOUT_CT, 12)
        key = f"NaC_{ratio:g}"
        res = run_pair(pp_with, pp_no, _closed_input(HOLDOUT_CT, na_h))
        sc = _smartchem_closed(HOLDOUT_CT, na_h)
        ood = []
        if max(res["I_with"], res["I_no"]) > OOD_I_MAX:
            ood.append("ionic_strength>0.5")
        if max(res["pH_with"], res["pH_no"]) > OOD_PH_MAX:
            ood.append("pH>12")
        res.update({"Na_over_C": ratio, "total_carbon": HOLDOUT_CT, "sodium": na_h,
                    "out_of_domain": ood, "in_domain": not ood, "smartchem_no_pairs_davies": sc,
                    "three_way": {"smartchem": sc.get("pH_activity"), "phreeqc_no_pairs": res["pH_no"],
                                  "phreeqc_with_pairs": res["pH_with"],
                                  "smartchem_minus_phreeqc_no": _signed(sc.get("pH_activity"), res["pH_no"]),
                                  "smartchem_minus_phreeqc_with": _signed(sc.get("pH_activity"), res["pH_with"]),
                                  "phreeqc_with_minus_no": res["delta_pH"]}})
        holdout[key] = res

    out = {
        "section": "OPERATION XXI section 6 -- Na-carbonate ion-pair ablation (raw numbers; NO verdict here)",
        "temperature_K": 298.15, "pressure_atm": 1.0,
        "instrument": "PHREEQC via phreeqpython; same program/input, database differs by deletion of 2 reactions",
        "databases": {
            "with_pairs": {"file": f"db/{DB_WITH}", "sha256": dbinfo["original_sha256"]},
            "no_pairs": {"file": f"db/{DB_NO}", "sha256": dbinfo["nopairs_sha256"]},
            "removed_reactions": list(PAIR_REACTIONS), "removed_constants": PAIR_CONSTANTS,
            "removed_line_spans_1based_in_original": dbinfo["removed_line_spans_1based"],
            "removed_text": dbinfo["removed_text"],
        },
        "no_tuning": True,
        "carbonate_grid": cases, "nist_srm191d": nist, "holdout_na_sweep": holdout,
        "verdict": "(left to orchestrator)",
    }
    return out


def main():
    out = evaluate()
    dbinfo = out["databases"]
    cases, nist, holdout = out["carbonate_grid"], out["nist_srm191d"], out["holdout_na_sweep"]
    with open(HERE / "result_s6_na_pair_ablation.json", "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    print("wrote result_s6_na_pair_ablation.json")
    print(f"  with sha256 {dbinfo['with_pairs']['sha256']}\n  no   sha256 {dbinfo['no_pairs']['sha256']}")
    for cid, r in cases.items():
        print(f"  {cid:3s} Na={r['sodium']:<5} smart={r['three_way']['smartchem']} no={r['pH_no']:.4f} "
              f"with={r['pH_with']:.4f} d={r['delta_pH']:+.5f}")
    print(f"  NIST with={nist['pH_with']:.4f} no={nist['pH_no']:.4f} d={nist['delta_pH']:+.5f}")
    for k, r in holdout.items():
        print(f"  {k} no={r['pH_no']:.4f} with={r['pH_with']:.4f} d={r['delta_pH']:+.5f} I={r['I_with']:.4f} "
              f"ood={r['out_of_domain']}")


if __name__ == "__main__":
    main()
