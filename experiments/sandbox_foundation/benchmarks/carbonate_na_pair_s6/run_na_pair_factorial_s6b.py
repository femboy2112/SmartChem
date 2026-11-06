"""OPERATION XXII section 6C/6D -- 2^3 FACTORIAL over three Na ion-pairing reactions, PHREEQC as the instrument.

Ooh yeah, can do!  XXI section 6 ablated two Na-carbonate pairs as ONE factor.  Here there are THREE independently
toggleable factors, each one whole SOLUTION_SPECIES block of minteq.v4.dat:
    A  Na+ + Acetate- = Na(Acetate)      (log_k -0.18)
    B  Na+ + H+ + CO3-2 = NaHCO3         (log_k 10.079)
    C  Na+ + CO3-2 = NaCO3-              (log_k 1.27)
Eight databases = the original with each subset of {A,B,C} DELETED (nothing added, nothing edited; "ABC" is the verbatim
original).  Same PHREEQC input in all 8; the 2^3 Yates effects on pH are computed from the 8 cells.  NO custom solver,
NO tuning: every log_k / delta_h is the database's own.  This harness writes RAW numbers; it does not write a verdict
(the section 6E claim ledger is the orchestrator's).  See PREREGISTRATION_FACTORIAL.md (written before any run).

Run from the repo root in a venv that has phreeqpython + numpy/scipy:
    PYTHONPATH=. python -m experiments.sandbox_foundation.benchmarks.carbonate_na_pair_s6.run_na_pair_factorial_s6b
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_DIR = HERE / "db"
DB_ORIGINAL = "minteq.v4.dat"
GRID = HERE.parent / "carbonate_phreeqc" / "grid.json"
XXI_RESULT = HERE / "result_s6_na_pair_ablation.json"      # read-only continuity reference
RESULT_NAME = "result_s6b_factorial.json"

ORIGINAL_SHA256 = "4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3"

# ---- the three factors: equation line VERBATIM from minteq.v4.dat; constants for the record (asserted by the test)
FACTORS = ("A", "B", "C")
FACTOR_REACTION = {
    "A": "Na+ + Acetate- = Na(Acetate)",
    "B": "Na+ + H+ + CO3-2 = NaHCO3",
    "C": "Na+ + CO3-2 = NaCO3-",
}
FACTOR_NAME = {"A": "Na-acetate", "B": "Na-bicarbonate", "C": "Na-carbonate"}
FACTOR_CONSTANTS = {
    "A": {"log_k": -0.18, "delta_h_kJ": 12.0, "gamma": "0 0"},
    "B": {"log_k": 10.079, "delta_h_kJ": -28.3301, "gamma": "0 0"},
    "C": {"log_k": 1.27, "delta_h_kJ": -20.35, "gamma": "5.4 0"},
}
FACTOR_PAIR_SPECIES = {"A": "Na(Acetate)", "B": "NaHCO3", "C": "NaCO3-"}

# Yates standard order, A fastest; each cell is a 3-char flag string (letter = present, '-' = removed)
CELL_ORDER = tuple("".join(f if on else "-" for f, on in zip(FACTORS, bits))
                   for bits in ((a, b, c) for c in (False, True) for b in (False, True) for a in (False, True)))
EFFECT_ORDER = ("A", "B", "C", "AB", "AC", "BC", "ABC")

# NIST SRM 191d (same numbers as the XXI harness)
NIST_TABLE1, NIST_TABLE1_U = 10.014, 0.010
NIST_TABLEA1, NIST_TABLEA1_UR = 10.0137, 0.0029
NIST_EACH_MOLALITY = 0.025

# PREREGISTERED mixed holdout (PREREGISTRATION_FACTORIAL.md section 5c): Na = 2.5 x, Acetate = x, C(4) = x
HOLDOUT_REGIMES = {"dilute": 0.01, "concentrated": 0.1}
OOD_I_MAX, OOD_PH_MAX = 0.5, 12.0

# effect classes (PREREGISTRATION_FACTORIAL.md section 7)
NULL_BELOW, MATERIAL_AT = 1e-4, 1e-3
CONTINUITY_TOL = 1e-9


def sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def variant_name(flags: str) -> str:
    return f"minteq.v4.fac_{flags}.dat"


def removed_factors(flags: str):
    """Factors REMOVED in a flag string (the '-' positions)."""
    assert len(flags) == 3
    return tuple(f for f, ch in zip(FACTORS, flags) if ch == "-")


# ---------------------------------------------------------------- deletion-only database construction
def split_lines(text: str):
    """Split on '\\n' ONLY (so no stray unicode line separators), keeping the terminators."""
    return re.findall(r"[^\n]*\n|[^\n]+", text)


def factor_spans(lines):
    """{factor: (start, end_exclusive)} -- a block = its un-indented equation line plus every following
    indented/comment line up to the next un-indented line.  Each equation must occur EXACTLY once."""
    spans = {}
    for fac, eq in FACTOR_REACTION.items():
        hits = [i for i, ln in enumerate(lines) if ln.rstrip("\n") == eq]
        if len(hits) != 1:
            raise RuntimeError(f"expected exactly one block for {eq!r}, found {len(hits)}")
        i = hits[0]
        j = i + 1
        while j < len(lines) and lines[j][:1] in (" ", "\t"):
            j += 1
        spans[fac] = (i, j)
    return spans


def build_variant_text(original_text: str, flags: str):
    """Return (variant_text, {factor: removed_text}) -- the original minus EXACTLY the blocks of the removed factors."""
    lines = split_lines(original_text)
    assert "".join(lines) == original_text
    spans = factor_spans(lines)
    drop = set()
    for fac in removed_factors(flags):
        a, b = spans[fac]
        drop.update(range(a, b))
    kept = "".join(ln for k, ln in enumerate(lines) if k not in drop)
    removed = {fac: "".join(lines[a:b]) for fac, (a, b) in spans.items() if fac in removed_factors(flags)}
    return kept, removed


def ensure_databases():
    """Verify the original's sha256, (re)build all 8 variants deterministically from the ORIGINAL, return their info."""
    orig = DB_DIR / DB_ORIGINAL
    sha_o = sha256_file(orig)
    if sha_o != ORIGINAL_SHA256:
        raise RuntimeError(f"{orig} sha256 {sha_o} != pinned {ORIGINAL_SHA256}")
    text = orig.read_bytes().decode("utf-8")
    lines = split_lines(text)
    spans = factor_spans(lines)
    block_text = {fac: "".join(lines[a:b]) for fac, (a, b) in spans.items()}
    info = {"original_sha256": sha_o, "variants": {}, "factor_blocks": {}}
    for fac, (a, b) in spans.items():
        info["factor_blocks"][fac] = {
            "name": FACTOR_NAME[fac], "reaction": FACTOR_REACTION[fac], "constants": FACTOR_CONSTANTS[fac],
            "original_lines_1based": [a + 1, b], "removed_text": block_text[fac]}
    for flags in CELL_ORDER:
        kept, removed = build_variant_text(text, flags)
        path = DB_DIR / variant_name(flags)
        path.write_bytes(kept.encode("utf-8"))
        info["variants"][flags] = {"file": f"db/{variant_name(flags)}", "sha256": sha256_file(path),
                                   "removed_factors": list(removed_factors(flags)),
                                   "n_lines": len(split_lines(kept)),
                                   "n_removed_lines": sum(len(split_lines(t)) for t in removed.values())}
    return info


# ---------------------------------------------------------------- PHREEQC driver (single instrument)
def _sel(flags: str) -> str:
    """Selected output; pair species keys listed only if that block is PRESENT in this variant's database."""
    pairs = " ".join(FACTOR_PAIR_SPECIES[f] for f in FACTORS if f not in removed_factors(flags))
    return f"""
SELECTED_OUTPUT 1
    -reset false
    -pH true
    -ionic_strength true
    -totals C(4) Na Acetate
    -molalities CO2 HCO3- CO3-2 Na+ Acetate- H(Acetate) {pairs}
"""


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


def _mixed_input(x):
    """PREREGISTRATION_FACTORIAL.md 5c:  Na = 2.5 x, Acetate = x, C(4) = x, charge-balanced pH."""
    return f"""
SOLUTION 1
    temp 25
    units mol/kgw
    Na {round(2.5 * x, 12)}
    Acetate {x}
    C(4) {x}
    pH 7 charge
END"""


def _case_input(c):
    if c["mode"] == "open":
        assert c["sodium"] == 0.0
        return _open_input(c["p_co2_atm"])
    return _closed_input(c["total_carbon"], c["sodium"])


def _run(pp, flags, inp):
    pp.ip.run_string(_sel(flags) + inp)
    out = pp.ip.get_selected_output_array()
    # an EQUILIBRIUM_PHASES step writes the initial solution first and the equilibrated state LAST -> take LAST row
    return dict(zip(out[0], out[-1]))


def _g(r, key):
    return float(r.get(key, 0.0))


def _cell(r, flags):
    """pH, I and the molal speciation of one PHREEQC run (pair species only where present in this variant's DB)."""
    na_t = _g(r, "Na(mol/kgw)")
    sp = {"Na_total_molal": na_t, "Acetate_total_molal": _g(r, "Acetate(mol/kgw)"),
          "C4_total_molal": _g(r, "C(4)(mol/kgw)"), "m_Na_free": _g(r, "m_Na+(mol/kgw)"),
          "m_CO2": _g(r, "m_CO2(mol/kgw)"), "m_HCO3": _g(r, "m_HCO3-(mol/kgw)"), "m_CO3": _g(r, "m_CO3-2(mol/kgw)"),
          "m_Acetate": _g(r, "m_Acetate-(mol/kgw)"), "m_HAcetate": _g(r, "m_H(Acetate)(mol/kgw)")}
    bound = 0.0
    for fac in FACTORS:
        if fac in removed_factors(flags):
            continue
        sp["m_" + FACTOR_PAIR_SPECIES[fac]] = _g(r, f"m_{FACTOR_PAIR_SPECIES[fac]}(mol/kgw)")
        bound += sp["m_" + FACTOR_PAIR_SPECIES[fac]]
    sp["Na_bound_in_pairs_fraction"] = (bound / na_t) if na_t > 0 else 0.0
    return {"pH": float(r["pH"]), "I": float(r["mu"]), "speciation": sp}


def run_system(pps, inp):
    """Run ONE input on all 8 variants -> {flags: cell}."""
    return {flags: _cell(_run(pps[flags], flags, inp), flags) for flags in CELL_ORDER}


# ---------------------------------------------------------------- 2^3 Yates decomposition
def _sign(flags: str, effect: str) -> int:
    s = 1
    for f in effect:
        s *= 1 if flags[FACTORS.index(f)] != "-" else -1
    return s


def yates_effects(y: dict) -> dict:
    """y = {flags: response}.  E_S = (1/4) sum_cells prod_{i in S} x_i * y ; x_i = +1 present / -1 removed."""
    assert set(y) == set(CELL_ORDER)
    eff = {e: sum(_sign(c, e) * y[c] for c in CELL_ORDER) / 4.0 for e in EFFECT_ORDER}
    contrasts = {e: sum(_sign(c, e) * y[c] for c in CELL_ORDER) for e in EFFECT_ORDER}
    mean = sum(y.values()) / 8.0
    recon = {c: mean + sum(eff[e] / 2.0 * _sign(c, e) for e in EFFECT_ORDER) for c in CELL_ORDER}
    return {"mean": mean, "effects": eff, "contrasts": contrasts,
            "reconstruction_max_abs_err": max(abs(recon[c] - y[c]) for c in CELL_ORDER)}


def effect_class(e: float) -> str:
    a = abs(e)
    return "NULL" if a < NULL_BELOW else ("AMBIGUOUS" if a < MATERIAL_AT else "MATERIAL")


def _decompose(cells: dict, key: str) -> dict:
    d = yates_effects({c: cells[c][key] for c in CELL_ORDER})
    d["effect_classes"] = {e: effect_class(v) for e, v in d["effects"].items()}
    return d


def _system_block(cells: dict, with_I: bool) -> dict:
    out = {"cells": cells, "pH_by_cell": {c: cells[c]["pH"] for c in CELL_ORDER},
           "pH_factorial": _decompose(cells, "pH"),
           "finite": bool(all(math.isfinite(cells[c]["pH"]) and math.isfinite(cells[c]["I"]) for c in CELL_ORDER))}
    if with_I:
        out["I_factorial"] = _decompose(cells, "I")
    out["A_toggle_max_abs_pH_diff"] = max(abs(cells[c]["pH"] - cells[_toggle(c, "A")]["pH"]) for c in CELL_ORDER)
    return out


def _toggle(flags: str, fac: str) -> str:
    i = FACTORS.index(fac)
    return flags[:i] + ("-" if flags[i] != "-" else fac) + flags[i + 1:]


# ---------------------------------------------------------------- evaluate
def evaluate() -> dict:
    from phreeqpython import PhreeqPython

    dbinfo = ensure_databases()
    pps = {flags: PhreeqPython(database=variant_name(flags), database_directory=DB_DIR) for flags in CELL_ORDER}
    xxi = json.loads(XXI_RESULT.read_text())

    # ---- (a) existing carbonate grid ----
    grid = json.loads(GRID.read_text())
    grid_out = {}
    for c in grid["cases"]:
        blk = _system_block(run_system(pps, _case_input(c)), with_I=False)
        ref = xxi["carbonate_grid"][c["id"]]
        blk.update({"mode": c["mode"], "desc": c["desc"], "sodium": c["sodium"],
                    "continuity_vs_XXI": {
                        "ABC_minus_XXI_pH_with": blk["pH_by_cell"]["ABC"] - ref["pH_with"],
                        "A--_minus_XXI_pH_no": blk["pH_by_cell"]["A--"] - ref["pH_no"]}})
        grid_out[c["id"]] = blk

    # ---- (b) NIST SRM 191d ----
    na, ct = 3 * NIST_EACH_MOLALITY, 2 * NIST_EACH_MOLALITY
    nist = _system_block(run_system(pps, _closed_input(ct, na)), with_I=True)
    refn = xxi["nist_srm191d"]
    nist["continuity_vs_XXI"] = {"ABC_minus_XXI_pH_with": nist["pH_by_cell"]["ABC"] - refn["pH_with"],
                                 "A--_minus_XXI_pH_no": nist["pH_by_cell"]["A--"] - refn["pH_no"]}
    nist["composition"] = {"Na_molal": na, "C4_molal": ct, "each_salt_molality": NIST_EACH_MOLALITY}
    nist["certified"] = {"table1_pH_S": NIST_TABLE1, "table1_U": NIST_TABLE1_U,
                         "tableA1_pH_S": NIST_TABLEA1, "tableA1_U_R": NIST_TABLEA1_UR}
    nist["per_variant"] = {c: {
        "pH": nist["pH_by_cell"][c],
        "residual_vs_table1": nist["pH_by_cell"][c] - NIST_TABLE1,
        "abs_residual_vs_table1": abs(nist["pH_by_cell"][c] - NIST_TABLE1),
        "residual_vs_tableA1": nist["pH_by_cell"][c] - NIST_TABLEA1,
        "abs_residual_vs_tableA1": abs(nist["pH_by_cell"][c] - NIST_TABLEA1),
        "within_table1_U": bool(abs(nist["pH_by_cell"][c] - NIST_TABLE1) <= NIST_TABLE1_U),
        "within_tableA1_U_R": bool(abs(nist["pH_by_cell"][c] - NIST_TABLEA1) <= NIST_TABLEA1_UR),
    } for c in CELL_ORDER}
    # adding factor f (present minus absent) in each context of the OTHER two factors; d|residual| < 0 = toward
    nist["adding_factor_effect_on_abs_residual_table1"] = {}
    for fac in FACTORS:
        ctxs = {}
        for c in CELL_ORDER:
            if c[FACTORS.index(fac)] == "-":
                present = _toggle(c, fac)
                d_abs = abs(nist["pH_by_cell"][present] - NIST_TABLE1) - abs(nist["pH_by_cell"][c] - NIST_TABLE1)
                d_ph = nist["pH_by_cell"][present] - nist["pH_by_cell"][c]
                ctxs[f"{c}->{present}"] = {"delta_pH": d_ph, "delta_abs_residual": d_abs,
                                           "moves_nothing": bool(abs(d_ph) < CONTINUITY_TOL),
                                           "toward_table1": bool(d_abs < -CONTINUITY_TOL),
                                           "away_from_table1": bool(d_abs > CONTINUITY_TOL)}
        nist["adding_factor_effect_on_abs_residual_table1"][fac] = ctxs

    # ---- (c) NEW preregistered mixed holdout, two regimes ----
    holdout = {}
    for regime, x in HOLDOUT_REGIMES.items():
        inp = _mixed_input(x)
        blk = _system_block(run_system(pps, inp), with_I=True)
        ood = {c: [r for r, bad in (("ionic_strength>0.5", blk["cells"][c]["I"] > OOD_I_MAX),
                                    ("pH>12", blk["cells"][c]["pH"] > OOD_PH_MAX)) if bad] for c in CELL_ORDER}
        blk.update({"regime": regime, "scale_x_molal": x,
                    "composition": {"Na_molal": round(2.5 * x, 12), "Acetate_molal": x, "C4_molal": x},
                    "phreeqc_input": inp.strip("\n"),
                    "out_of_domain_by_cell": ood, "in_domain": bool(not any(ood.values()))})
        holdout[regime] = blk

    out = {
        "section": "OPERATION XXII section 6C/6D -- 2^3 factorial over three Na ion-pairing reactions "
                   "(raw numbers; NO verdict here)",
        "temperature_K": 298.15, "pressure_atm": 1.0,
        "instrument": "PHREEQC via phreeqpython; same program/input; database differs by whole-block deletion only",
        "no_tuning": True,
        "factors": dbinfo["factor_blocks"],
        "cell_order_yates": list(CELL_ORDER),
        "coding": "x_i=+1 factor PRESENT, -1 REMOVED; E_S=(1/4)*sum_cells prod_{i in S}x_i*y (Yates); "
                  "main effect = mean(present)-mean(removed)",
        "databases": {"original": {"file": f"db/{DB_ORIGINAL}", "sha256": dbinfo["original_sha256"]},
                      "variants": dbinfo["variants"],
                      "ABC_equals_original": bool(dbinfo["variants"]["ABC"]["sha256"] == dbinfo["original_sha256"])},
        "carbonate_grid": grid_out, "nist_srm191d": nist, "mixed_holdout": holdout,
        "derived": _derived(grid_out, nist, holdout),
        "verdict": "(left to orchestrator)",
    }
    return out


def _derived(grid_out, nist, holdout) -> dict:
    """Mechanical application of the PREREGISTRATION_FACTORIAL.md section 8 rules to the raw numbers (no verdict)."""
    d = {"note": "mechanical rule application only; VERDICT: (left to orchestrator)"}
    # O2 continuity
    cont = [abs(v) for b in list(grid_out.values()) + [nist] for v in b["continuity_vs_XXI"].values()]
    d["O2_continuity_max_abs_diff_vs_XXI"] = max(cont)
    d["O2"] = "PASS" if max(cont) <= CONTINUITY_TOL else "FAIL"
    # O3 A inactive on acetate-free systems
    a_eff = {cid: b["pH_factorial"]["effects"]["A"] for cid, b in grid_out.items()}
    a_eff["NIST"] = nist["pH_factorial"]["effects"]["A"]
    d["A_main_effect_pH_acetate_free"] = a_eff
    d["A_null_max_abs_cell_diff"] = max(b["A_toggle_max_abs_pH_diff"] for b in list(grid_out.values()) + [nist])
    d["O3_strict_cell_identity"] = bool(d["A_null_max_abs_cell_diff"] <= CONTINUITY_TOL)
    d["O3"] = "PASS" if max(abs(v) for v in a_eff.values()) < MATERIAL_AT else "FAIL"
    # O4-O7 on the holdout
    eh = {r: holdout[r]["pH_factorial"]["effects"] for r in HOLDOUT_REGIMES}
    d["holdout_pH_effects"] = eh
    d["holdout_effect_classes"] = {r: holdout[r]["pH_factorial"]["effect_classes"] for r in HOLDOUT_REGIMES}
    neg = all(eh[r][f] < 0 for r in eh for f in ("B", "C"))
    pos_material = any(eh[r][f] >= MATERIAL_AT for r in eh for f in ("B", "C"))
    d["O4"] = ("PASS" if neg and all(abs(eh[r]["C"]) >= MATERIAL_AT for r in eh)
               else "FAIL" if pos_material else "AMBIGUOUS")
    gb, gc = abs(eh["concentrated"]["B"]) > abs(eh["dilute"]["B"]), abs(eh["concentrated"]["C"]) > abs(eh["dilute"]["C"])
    d["O5"] = "PASS" if (gb and gc) else ("FAIL" if not (gb or gc) else "AMBIGUOUS")
    a_conc, a_dil = abs(eh["concentrated"]["A"]), abs(eh["dilute"]["A"])
    d["O6"] = ("PASS" if (a_conc >= MATERIAL_AT and a_dil < MATERIAL_AT)
               else "FAIL" if a_conc < NULL_BELOW else "AMBIGUOUS")
    inter = max(abs(eh["concentrated"][e]) for e in ("AB", "AC", "BC", "ABC"))
    d["O7_max_abs_interaction_concentrated"] = inter
    d["O7"] = "PASS" if inter >= MATERIAL_AT else ("FAIL" if inter < NULL_BELOW else "AMBIGUOUS")
    # O8 NIST direction
    mov = nist["adding_factor_effect_on_abs_residual_table1"]
    away = {f: all(v["away_from_table1"] for v in mov[f].values()) for f in ("B", "C")}
    toward = {f: all(v["toward_table1"] for v in mov[f].values()) for f in ("B", "C")}
    a_none = all(v["moves_nothing"] for v in mov["A"].values())
    d["O8"] = ("PASS" if (all(away.values()) and a_none) else "FAIL" if any(toward.values()) else "AMBIGUOUS")
    # O9 closure (determinism is checked across two runs by the test / orchestrator)
    d["O9_reconstruction_max_abs_err"] = max(
        [b["pH_factorial"]["reconstruction_max_abs_err"] for b in list(grid_out.values()) + [nist]]
        + [b["pH_factorial"]["reconstruction_max_abs_err"] for b in holdout.values()])
    d["O9_closure"] = "PASS" if d["O9_reconstruction_max_abs_err"] <= CONTINUITY_TOL else "FAIL"
    return d


def main():
    out = evaluate()
    path = HERE / RESULT_NAME
    with open(path, "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    print(f"wrote {RESULT_NAME}  sha256 {sha256_file(path)}")
    for flags, v in out["databases"]["variants"].items():
        print(f"  DB {flags} {v['sha256']}")
    print("  ABC == original:", out["databases"]["ABC_equals_original"])
    nist = out["nist_srm191d"]
    for c in CELL_ORDER:
        print(f"  NIST {c} pH={nist['pH_by_cell'][c]:.5f}")
    for r, blk in out["mixed_holdout"].items():
        print(f"  holdout {r} in_domain={blk['in_domain']}  " + "  ".join(
            f"E_{e}={blk['pH_factorial']['effects'][e]:+.6f}" for e in EFFECT_ORDER))
    print("  derived:", {k: v for k, v in out["derived"].items() if k.startswith("O") and k[1:2].isdigit()
                         and not isinstance(v, (dict, float))})


if __name__ == "__main__":
    main()
