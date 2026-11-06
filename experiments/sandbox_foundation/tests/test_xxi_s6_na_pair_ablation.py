"""OPERATION XXI section 6 -- pins the Na-carbonate ION-PAIR ablation (PHREEQC with vs without the two minteq.v4 pairs).

Ooh yeah, can do!  Skips cleanly where phreeqpython is absent (the committed baseline stays runnable without it).
Asserts: (1) the no-pairs DB differs from minteq.v4 by EXACTLY the two Na-carbonate reactions and both sha256 are
pinned; (2) every case produced a finite pH both ways and a finite delta; (3) the ablation actually does something --
high-Na delta_pH is non-trivial, zero-Na delta_pH is ~0, and the preregistered Na-sweep is monotone in Na; (4) no
model constant was touched (git diff vs e18e134 empty).  It asserts NO scientific verdict.
"""
from __future__ import annotations

import difflib
import math
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("phreeqpython")

from experiments.sandbox_foundation.benchmarks.carbonate_na_pair_s6 import run_na_pair_ablation_s6 as H  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
BASE = "e18e134"        # the §11 commit immediately BEFORE the §6 ablation work
XXI_TIP = "07afeff"     # the XXI final tip (Wave F).  The no-tune claim is scoped to the §6..XXI range BASE..XXI_TIP
# so it certifies what §6 ACTUALLY did and stays TRUE as later operations (XXII+) legitimately evolve these files; an
# open-ended `git diff BASE` to HEAD could not distinguish §6 tuning from an unrelated later change to the same file.
ORIGINAL_SHA = "4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3"
NOPAIRS_SHA = "6ada9d3f17bd1a101b446ed5eb67cb520bd923e842f3b0547a5261f3493a3082"


@pytest.fixture(scope="module")
def res():
    return H.evaluate()


def test_database_shas_are_pinned():
    assert H.sha256_file(H.DB_DIR / H.DB_WITH) == ORIGINAL_SHA
    H.ensure_databases()                                            # deterministic rebuild
    assert H.sha256_file(H.DB_DIR / H.DB_NO) == NOPAIRS_SHA


def test_nopairs_db_differs_by_exactly_the_two_na_carbonate_reactions():
    a = (H.DB_DIR / H.DB_WITH).read_text().splitlines()
    b = (H.DB_DIR / H.DB_NO).read_text().splitlines()
    removed, added = [], []
    for ln in difflib.unified_diff(a, b, lineterm="", n=0):
        if ln.startswith(("---", "+++", "@@")):
            continue
        (removed if ln.startswith("-") else added).append(ln[1:])
    assert added == []                                               # deletion only: nothing added or edited
    assert len(removed) == 16                                        # 2 blocks x (equation + log_k + delta_h + -gamma + 4 comments)
    headers = [ln for ln in removed if ln and not ln[0].isspace()]
    assert headers == ["Na+ + CO3-2 = NaCO3-", "Na+ + H+ + CO3-2 = NaHCO3"]
    txt = "\n".join(removed)
    assert "log_k 1.27" in txt and "delta_h -20.35 kJ" in txt
    assert "log_k 10.079" in txt and "delta_h -28.3301 kJ" in txt
    # the no-pairs DB defines neither pair species any more; the original defines both
    assert "= NaCO3-" not in "\n".join(b) and "= NaHCO3" not in "\n".join(b)
    assert "= NaCO3-" in "\n".join(a) and "= NaHCO3" in "\n".join(a)


def test_result_records_both_shas_and_removed_reactions(res):
    d = res["databases"]
    assert d["with_pairs"]["sha256"] == ORIGINAL_SHA and d["no_pairs"]["sha256"] == NOPAIRS_SHA
    assert d["removed_reactions"] == ["Na+ + CO3-2 = NaCO3-", "Na+ + H+ + CO3-2 = NaHCO3"]
    assert res["no_tuning"] is True and res["verdict"] == "(left to orchestrator)"


def test_every_case_finite_both_ways(res):
    rows = list(res["carbonate_grid"].values()) + [res["nist_srm191d"]] + list(res["holdout_na_sweep"].values())
    assert len(res["carbonate_grid"]) == 11 and len(res["holdout_na_sweep"]) == 3
    for r in rows:
        assert r["finite"] is True
        assert all(math.isfinite(r[k]) for k in ("pH_with", "pH_no", "delta_pH", "I_with", "I_no", "delta_I"))
        assert r["delta_pH"] == pytest.approx(r["pH_with"] - r["pH_no"])


def test_zero_sodium_cases_have_zero_delta_and_high_sodium_cases_do_not(res):
    g = res["carbonate_grid"]
    for cid in ("O1", "O2", "O3", "O4", "O5", "O6", "C5"):            # no Na => the ablated species never form
        assert g[cid]["sodium"] == 0.0
        assert abs(g[cid]["delta_pH"]) < 1e-6
    for cid in ("C2", "C4"):                                         # high-Na closed carbonate => non-trivial
        assert abs(g[cid]["delta_pH"]) > 0.05
    assert abs(res["nist_srm191d"]["delta_pH"]) > 0.05
    # the pairs really form there (Na speciation is not trivially all-free)
    assert g["C4"]["speciation_with"]["Na_bound_fraction"] > 0.1
    assert g["C4"]["speciation_no"].get("m_NaCO3-") is None          # no pair species in the ablated run


def test_preregistered_na_sweep_is_in_domain_and_monotone_in_na(res):
    h = res["holdout_na_sweep"]
    assert [h[k]["Na_over_C"] for k in h] == [0.5, 1.0, 1.5]
    assert all(h[k]["in_domain"] for k in h)
    mags = [abs(h[k]["delta_pH"]) for k in h]
    assert mags[0] < mags[1] < mags[2]                               # pair contribution grows with Na/C_T
    fr = [h[k]["speciation_with"]["Na_bound_fraction"] for k in h]
    assert fr[0] < fr[1] < fr[2]


def test_nist_block_carries_both_certified_values_and_both_runs(res):
    n = res["nist_srm191d"]
    assert n["certified"]["table1_pH_S"] == 10.014 and n["certified"]["tableA1_pH_S"] == 10.0137
    assert n["composition"]["Na_molal"] == pytest.approx(0.075) and n["composition"]["C4_molal"] == pytest.approx(0.05)
    assert n["residual_with_vs_table1"] == pytest.approx(n["pH_with"] - 10.014)
    assert n["residual_no_vs_tableA1"] == pytest.approx(n["pH_no"] - 10.0137)
    # the NIST composition is the holdout Na/C = 1.5 cell (same system): the two must coincide
    assert n["pH_with"] == pytest.approx(res["holdout_na_sweep"]["NaC_1.5"]["pH_with"], abs=1e-9)


def test_three_way_table_present_for_the_grid(res):
    for cid, r in res["carbonate_grid"].items():
        t = r["three_way"]
        assert t["phreeqc_no_pairs"] == r["pH_no"] and t["phreeqc_with_pairs"] == r["pH_with"]
        assert t["smartchem"] is not None and math.isfinite(t["smartchem"]), cid


def test_no_model_constant_was_touched():
    out = subprocess.run(
        ["git", "diff", BASE, XXI_TIP, "--",
         "experiments/sandbox_foundation/carbonate_equilibrium.py",
         "experiments/sandbox_foundation/general_coupled.py",
         "experiments/sandbox_foundation/open_diagram_bridge.py",
         "experiments/sandbox_foundation/benchmarks/carbonate_phreeqc",
         "smartchem"],
        cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git unavailable or base/tip SHA absent")
    assert out.stdout == ""                                          # XXI-6 ablates inside PHREEQC; tunes nothing
