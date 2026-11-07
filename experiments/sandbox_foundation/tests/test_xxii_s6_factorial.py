"""OPERATION XXII section 6C/6D -- pins the 2^3 Na ion-pairing FACTORIAL (PHREEQC, eight deletion-only minteq.v4 variants).

Ooh yeah, can do!  Skips cleanly where phreeqpython is absent.  Asserts: (1) each of the 8 DB variants is the ORIGINAL with
EXACTLY the selected factor blocks deleted (reconstruction + difflib: only 'equal'/'delete' opcodes, deleted text == the
selected blocks), 'ABC' is byte-identical to the original, every sha256 matches the JSON; (2) the result JSON has all 8
cells for every system and the Yates effects are present and finite; (3) the acetate factor A is inactive (|E_A| < 1e-3)
on the acetate-free pure-carbonate grid and NIST, and the Yates identity closes; (4) continuity with the XXI result;
(5) re-running gives an identical result serialization.  It asserts NO scientific verdict.
"""
from __future__ import annotations

import difflib
import hashlib
import itertools
import json
import math
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("phreeqpython")

from experiments.sandbox_foundation.benchmarks.carbonate_na_pair_s6 import run_na_pair_factorial_s6b as H  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
ORIGINAL_SHA = "4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3"
XXI_NOPAIRS_SHA = "6ada9d3f17bd1a101b446ed5eb67cb520bd923e842f3b0547a5261f3493a3082"
BASE = "9d04894"      # worktree base; the XXI section 6 files must be unchanged relative to it
XXI_FILES = [
    "experiments/sandbox_foundation/benchmarks/carbonate_na_pair_s6/run_na_pair_ablation_s6.py",
    "experiments/sandbox_foundation/benchmarks/carbonate_na_pair_s6/PREREGISTRATION.md",
    "experiments/sandbox_foundation/benchmarks/carbonate_na_pair_s6/S6_NA_PAIR_ABLATION_NOTES.md",
    "experiments/sandbox_foundation/benchmarks/carbonate_na_pair_s6/result_s6_na_pair_ablation.json",
    "experiments/sandbox_foundation/benchmarks/carbonate_na_pair_s6/db/minteq.v4.dat",
    "experiments/sandbox_foundation/benchmarks/carbonate_na_pair_s6/db/minteq.v4.nopairs.dat",
]
ALL_FLAGS = ["".join(f if on else "-" for f, on in zip("ABC", bits))
             for bits in itertools.product((True, False), repeat=3)]
# block header + constant lines, VERBATIM as they must appear in the removed text
EXPECT_TEXT = {
    "A": ("Na+ + Acetate- = Na(Acetate)", "log_k -0.18", "delta_h 12 kJ"),
    "B": ("Na+ + H+ + CO3-2 = NaHCO3", "log_k 10.079", "delta_h -28.3301 kJ"),
    "C": ("Na+ + CO3-2 = NaCO3-", "log_k 1.27", "delta_h -20.35 kJ"),
}


@pytest.fixture(scope="module")
def res():
    return H.evaluate()


@pytest.fixture(scope="module")
def orig_text():
    p = H.DB_DIR / H.DB_ORIGINAL
    assert H.sha256_file(p) == ORIGINAL_SHA
    return p.read_bytes().decode("utf-8")


def test_all_eight_variants_enumerated():
    assert sorted(H.CELL_ORDER) == sorted(ALL_FLAGS) and len(set(H.CELL_ORDER)) == 8


def test_abc_variant_is_byte_identical_to_original(res):
    sha_abc = H.sha256_file(H.DB_DIR / H.variant_name("ABC"))
    assert sha_abc == ORIGINAL_SHA == H.sha256_file(H.DB_DIR / H.DB_ORIGINAL)
    assert (H.DB_DIR / H.variant_name("ABC")).read_bytes() == (H.DB_DIR / H.DB_ORIGINAL).read_bytes()
    assert res["databases"]["ABC_equals_original"] is True
    assert res["databases"]["original"]["sha256"] == ORIGINAL_SHA


def test_xxi_nopairs_db_equals_A_present_B_C_removed(res):
    # content-equality of the new 'A--' variant with the XXI no-pairs DB (B and C are exactly the XXI pair)
    assert res["databases"]["variants"]["A--"]["sha256"] == XXI_NOPAIRS_SHA


@pytest.mark.parametrize("flags", ALL_FLAGS)
def test_variant_is_deletion_only_of_exactly_the_selected_blocks(flags, res, orig_text):
    removed = [f for f, ch in zip("ABC", flags) if ch == "-"]
    var_text = (H.DB_DIR / H.variant_name(flags)).read_bytes().decode("utf-8")
    olines, vlines = H.split_lines(orig_text), H.split_lines(var_text)

    # (i) independent reconstruction: original minus the blocks located by header text + indented continuation
    drop, located = set(), []
    for fac in removed:
        eq = EXPECT_TEXT[fac][0]
        hits = [i for i, ln in enumerate(olines) if ln.rstrip("\n") == eq]
        assert len(hits) == 1, f"{eq!r} must occur exactly once in the original"
        i = hits[0]
        j = i + 1
        while j < len(olines) and olines[j][:1] in (" ", "\t"):
            j += 1
        drop.update(range(i, j))
        located.append((i, "".join(olines[i:j])))
    removed_chunks = [ch for _, ch in sorted(located)]          # FILE order (difflib emits deletions in file order)
    assert "".join(ln for k, ln in enumerate(olines) if k not in drop) == var_text

    split_all = lambda chunks: [ln for ch in chunks for ln in H.split_lines(ch)]     # noqa: E731
    # (ii) difflib: only 'equal' and 'delete' opcodes (nothing inserted, nothing replaced), deleted text == the blocks
    deleted = []
    for tag, a1, a2, b1, b2 in difflib.SequenceMatcher(None, olines, vlines, autojunk=False).get_opcodes():
        assert tag in ("equal", "delete"), f"non-deletion edit {tag} in variant {flags}"
        if tag == "delete":
            deleted.append("".join(olines[a1:a2]))
    # difflib may slide a deletion window past byte-identical neighbouring lines (the trailing '#T and ionic strength'
    # comment repeats in every block), so compare the deleted LINES as a multiset; exact positions are pinned by (i).
    assert sorted(split_all(deleted)) == sorted(split_all(removed_chunks))

    # (iii) the removed text carries the database's own constants verbatim; and no OTHER factor's block is touched
    for fac in "ABC":
        header, logk, dh = EXPECT_TEXT[fac]
        in_removed = any(header + "\n" in ch for ch in removed_chunks)
        assert in_removed == (fac in removed)
        if fac in removed:
            chunk = next(ch for ch in removed_chunks if header + "\n" in ch)
            assert logk in chunk and dh in chunk
        else:
            assert header + "\n" in var_text
    assert len(vlines) == len(olines) - sum(len(H.split_lines(c)) for c in removed_chunks)

    # (iv) JSON bookkeeping matches the files on disk
    meta = res["databases"]["variants"][flags]
    assert meta["sha256"] == H.sha256_file(H.DB_DIR / H.variant_name(flags))
    assert meta["removed_factors"] == removed
    if removed:
        assert meta["sha256"] != ORIGINAL_SHA


def test_removed_block_text_recorded_per_factor(res):
    for fac, (header, logk, dh) in EXPECT_TEXT.items():
        blk = res["factors"][fac]
        assert blk["removed_text"].splitlines()[0] == header
        assert logk in blk["removed_text"] and dh in blk["removed_text"]
        assert blk["constants"]["log_k"] == float(logk.split()[1])


def test_variant_shas_are_distinct():
    shas = {H.sha256_file(H.DB_DIR / H.variant_name(f)) for f in ALL_FLAGS}
    assert len(shas) == 8


def _systems(res):
    yield from ((f"grid:{cid}", b) for cid, b in res["carbonate_grid"].items())
    yield "nist", res["nist_srm191d"]
    yield from ((f"holdout:{r}", b) for r, b in res["mixed_holdout"].items())


def test_all_eight_cells_for_every_system_and_finite(res):
    assert len(res["carbonate_grid"]) == 11
    assert set(res["mixed_holdout"]) == {"dilute", "concentrated"}
    for name, b in _systems(res):
        assert sorted(b["cells"]) == sorted(ALL_FLAGS), name
        assert b["finite"] is True, name
        for c in ALL_FLAGS:
            assert math.isfinite(b["cells"][c]["pH"]) and math.isfinite(b["cells"][c]["I"]), (name, c)


def test_factorial_effects_present_and_finite(res):
    for name, b in _systems(res):
        fx = b["pH_factorial"]
        assert set(fx["effects"]) == set(H.EFFECT_ORDER), name
        assert set(fx["effect_classes"]) == set(H.EFFECT_ORDER), name
        assert all(math.isfinite(v) for v in fx["effects"].values()), name
        assert all(math.isfinite(v) for v in fx["contrasts"].values()), name
        assert math.isfinite(fx["mean"]), name
    for r in ("dilute", "concentrated"):
        assert set(res["mixed_holdout"][r]["I_factorial"]["effects"]) == set(H.EFFECT_ORDER)


def test_yates_identity_closes_and_matches_hand_contrast(res):
    for name, b in _systems(res):
        assert b["pH_factorial"]["reconstruction_max_abs_err"] <= 1e-9, name
    # independent hand contrast for a main effect and an interaction on a holdout regime
    b = res["mixed_holdout"]["concentrated"]
    y = b["pH_by_cell"]
    pres = lambda f, c: c["ABC".index(f)] != "-"        # noqa: E731
    e_c = (sum(y[c] for c in y if pres("C", c)) - sum(y[c] for c in y if not pres("C", c))) / 4.0
    assert e_c == pytest.approx(b["pH_factorial"]["effects"]["C"], abs=1e-12)
    e_ab = sum((1 if pres("A", c) == pres("B", c) else -1) * y[c] for c in y) / 4.0
    assert e_ab == pytest.approx(b["pH_factorial"]["effects"]["AB"], abs=1e-12)


def test_unit_yates_on_known_additive_response():
    # y = 7 + 2*xA - 3*xC (no interactions) -> E_A = 4, E_C = -6, everything else exactly 0
    y = {c: 7 + 2 * (1 if c[0] != "-" else -1) - 3 * (1 if c[2] != "-" else -1) for c in H.CELL_ORDER}
    fx = H.yates_effects(y)
    assert fx["effects"]["A"] == pytest.approx(4.0) and fx["effects"]["C"] == pytest.approx(-6.0)
    for e in ("B", "AB", "AC", "BC", "ABC"):
        assert fx["effects"][e] == pytest.approx(0.0, abs=1e-12)
    assert fx["reconstruction_max_abs_err"] <= 1e-12


def test_A_is_inactive_on_acetate_free_systems(res):
    # no acetate anywhere in the grid or NIST -> the Na(Acetate) block cannot matter
    for cid, b in res["carbonate_grid"].items():
        assert abs(b["pH_factorial"]["effects"]["A"]) < 1e-3, cid
        assert b["A_toggle_max_abs_pH_diff"] <= 1e-9, cid
    assert abs(res["nist_srm191d"]["pH_factorial"]["effects"]["A"]) < 1e-3
    assert res["nist_srm191d"]["A_toggle_max_abs_pH_diff"] <= 1e-9
    assert res["derived"]["A_null_max_abs_cell_diff"] <= 1e-9


def test_continuity_with_xxi_result(res):
    # ABC reproduces the XXI 'with pairs' pH and A-- reproduces the XXI 'no pairs' pH (A inactive there)
    assert res["derived"]["O2_continuity_max_abs_diff_vs_XXI"] <= 1e-9
    xxi = json.loads(H.XXI_RESULT.read_text())
    assert res["nist_srm191d"]["pH_by_cell"]["ABC"] == pytest.approx(xxi["nist_srm191d"]["pH_with"], abs=1e-9)
    assert res["nist_srm191d"]["pH_by_cell"]["A--"] == pytest.approx(xxi["nist_srm191d"]["pH_no"], abs=1e-9)


def test_holdout_preregistered_compositions_and_acetate_present(res):
    d, c = res["mixed_holdout"]["dilute"], res["mixed_holdout"]["concentrated"]
    assert d["composition"] == {"Na_molal": 0.025, "Acetate_molal": 0.01, "C4_molal": 0.01}
    assert c["composition"] == {"Na_molal": 0.25, "Acetate_molal": 0.1, "C4_molal": 0.1}
    assert "Acetate 0.01" in d["phreeqc_input"] and "Na 0.025" in d["phreeqc_input"] and "pH 7 charge" in d["phreeqc_input"]
    assert "Acetate 0.1" in c["phreeqc_input"] and "Na 0.25" in c["phreeqc_input"]
    # the A factor is actually exercised (Na(Acetate) forms) in the cells where block A is present
    assert d["cells"]["ABC"]["speciation"]["m_Na(Acetate)"] > 0 and c["cells"]["ABC"]["speciation"]["m_Na(Acetate)"] > 0
    assert d["in_domain"] is True and c["in_domain"] is True


def test_nist_variant_table_and_toward_away_records(res):
    n = res["nist_srm191d"]
    assert sorted(n["per_variant"]) == sorted(ALL_FLAGS)
    for fac in "ABC":
        assert len(n["adding_factor_effect_on_abs_residual_table1"][fac]) == 4
    assert res["nist_srm191d"]["certified"]["table1_pH_S"] == 10.014


def test_xxi_section6_files_untouched():
    out = subprocess.run(["git", "diff", "--name-only", BASE, "--", *XXI_FILES],
                         cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git/base commit unavailable")
    assert out.stdout.strip() == ""


def test_rerun_gives_identical_result_serialization(res):
    a = json.dumps(res, indent=2, allow_nan=False)
    b = json.dumps(H.evaluate(), indent=2, allow_nan=False)
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()
    on_disk = H.HERE / H.RESULT_NAME
    if on_disk.exists():
        assert on_disk.read_text() == a
