"""Run the carbonate benchmark grid through PHREEQC (the INDEPENDENT instrument).

Run ONLY in an isolated scratch venv that has `phreeqpython` -- NEVER the SmartChem .venv (the committed baseline
stays free of it, exactly like the acetate benchmark).  phreeqc.dat is PHREEQC's default database; the carbonate
system is native to it.  Writes `phreeqc_results.json` (NOT committed -- the committed reference is the pH column
inside `comparison_table.json`, see compare.py).  Deterministic; pin the database sha256 in README.md.

Usage (from an isolated venv):  python run_phreeqc.py
"""
import hashlib
import json
import os

from phreeqpython import PhreeqPython

HERE = os.path.dirname(os.path.abspath(__file__))
_SEL = """
SELECTED_OUTPUT 1
    -reset false
    -pH true
    -ionic_strength true
    -totals C(4)
    -molalities CO2 HCO3- CO3-2
"""


def _run(pp, inp):
    pp.ip.run_string(_SEL + inp)
    out = pp.ip.get_selected_output_array()
    # out = [headers, row1, row2, ...]; an EQUILIBRIUM_PHASES step writes the INITIAL solution first and the
    # equilibrated state LAST, so take the LAST data row (for a plain SOLUTION there is only one data row).
    return dict(zip(out[0], out[-1]))


def _open_input(p_co2_atm, sodium):
    # fixed CO2 partial pressure = infinite reservoir: equilibrate pure water with CO2(g) at the fixed log P (10 mol
    # available ~ infinite vs the ~1e-5 mol that dissolves).  No 'pH charge' -- PHREEQC sets the proton balance as the
    # carbonic acid dissolves; forcing 'pH charge' on Na=0 water suppressed the equilibration.  All open cases are
    # pure water (sodium == 0); a nonzero Na would need a counter-ion treatment not used in this grid.
    import math
    assert sodium == 0.0, "the open grid is pure-water only"
    return f"""
SOLUTION 1
    temp 25
EQUILIBRIUM_PHASES 1
    CO2(g) {math.log10(p_co2_atm)} 10.0
END"""


def _closed_input(total_carbon, sodium):
    # defined composition, pH found by charge balance (no gas phase): the closed, fixed-dissolved-carbon case.
    return f"""
SOLUTION 1
    temp 25
    units mol/kgw
    Na {sodium}
    C(4) {total_carbon}
    pH 7 charge
END"""


def main():
    grid = json.load(open(os.path.join(HERE, "grid.json")))
    pp = PhreeqPython(database="phreeqc.dat")
    db = os.path.join(os.path.dirname(__import__("phreeqpython").__file__), "database", "phreeqc.dat")
    db_sha = hashlib.sha256(open(db, "rb").read()).hexdigest()
    results = {"database": "phreeqc.dat", "database_sha256": db_sha, "cases": {}}
    for c in grid["cases"]:
        if c["mode"] == "open":
            r = _run(pp, _open_input(c["p_co2_atm"], c["sodium"]))
        else:
            r = _run(pp, _closed_input(c["total_carbon"], c["sodium"]))
        results["cases"][c["id"]] = {
            "mode": c["mode"], "desc": c["desc"],
            "pH": r["pH"], "I": r["mu"], "C4_total_molal": r["C(4)(mol/kgw)"],
            "m_CO2": r["m_CO2(mol/kgw)"], "m_HCO3": r["m_HCO3-(mol/kgw)"], "m_CO3": r["m_CO3-2(mol/kgw)"],
        }
    with open(os.path.join(HERE, "phreeqc_results.json"), "w") as f:
        json.dump(results, f, indent=2, allow_nan=False)
    print(f"wrote phreeqc_results.json ({len(results['cases'])} cases); phreeqc.dat sha256 {db_sha}")


if __name__ == "__main__":
    main()
