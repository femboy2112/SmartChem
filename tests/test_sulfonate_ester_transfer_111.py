"""Regression lock for SULFONATE-ESTER-TRANSFER-111 (OPERATION Wave C, issue #111 sub-family).

A sulfonyl halide sulfonylating an alcohol O (R-OH + R'SO2X -> R-O-SO2R' + HX) is a recognized class. The cardinal
no-false-vouch holds: cross-poach controls stay their own class, out-of-scope nucleophiles and fictions abstain, and
recognition is content-deterministic (a forged reaction centre buys nothing).
"""
from __future__ import annotations

import dataclasses

import pytest

import experiments.sulfonate_ester_transfer_111 as bench
from smartchem.diels_alder import _DA_CENTER
from smartchem.experiment.reaction_type_oracle import (
    _RECOGNIZERS,
    _sulfonate_ester_bond_count,
    recognize_reaction_type,
)
from smartchem.smiles import parse_smiles


def test_recognizer_matrix_and_no_false_vouch():
    m = bench.recognizer_matrix()
    assert m["passed"] == m["total"], f"matrix regressed: {[r for r in m['rows'] if not r[3]]}"
    assert m["recognized_sulfonate"] == 4, "a sulfonate-ester positive stopped being recognized"
    assert m["false_vouch_as_sulfonate"] == 0, "a non-sulfonate case was vouched AS sulfonate (CARDINAL)"


def test_oracle_now_has_twenty_recognizers():
    assert len(_RECOGNIZERS) == 20  # #110 (18th) + #111 sulfonate-ester transfer (19th) + #115 Claisen cond. (20th)


def test_does_not_poach_acyl_transfer_or_etherification():
    rows = {name: klass for name, _expect, klass, _ok in bench.recognizer_matrix()["rows"]}
    assert "activated acyl transfer" in str(
        rows["acyl transfer (AcCl + methanol) -> activated acyl (not sulfonate)"])
    assert "etherification" in str(rows["dehydrative ether (2 methanol) -> etherification (not sulfonate)"])
    # and the sulfonate recognizer never fires on either (checked explicitly below)


def test_exactly_one_recognizer_fires_on_a_sulfonate_step():
    step = bench._hand(("CO", "Cc1ccc(cc1)S(=O)(=O)Cl"), ("Cc1ccc(cc1)S(=O)(=O)OC", "Cl"))
    fired = [name for name, pred in _RECOGNIZERS if _safe(pred, step)]
    assert fired == ["sulfonate-ester transfer (sulfonyl halide + R-OH -> sulfonate ester + HX)"], fired


def test_content_deterministic_forged_centre_buys_nothing():
    # a genuine sulfonate step wearing a BORROWED Diels-Alder centre still vouches (centre is never read) ...
    genuine = bench._hand(("CO", "Cc1ccc(cc1)S(=O)(=O)Cl"), ("Cc1ccc(cc1)S(=O)(=O)OC", "Cl"))
    forged_genuine = dataclasses.replace(genuine, reaction_center=_DA_CENTER)
    assert "sulfonate-ester transfer" in str(recognize_reaction_type(forged_genuine))
    # ... and a NON-sulfonate step wearing any centre stays unrecognized (no forged annotation mints a vouch).
    fiction = bench._hand(("CC(=O)Cl", "CO"), ("COC(C)=O", "Cl"))  # an acyl transfer, not sulfonate
    forged_fiction = dataclasses.replace(fiction, reaction_center=_DA_CENTER)
    assert "sulfonate-ester transfer" not in str(recognize_reaction_type(forged_fiction))


#: evil-morty Wave-C kills (reactants, products) that MUST abstain -- retained as permanent regression controls.
#: Each was a VERIFIED false-vouch before the alkyl-carbinol + sulfonate-S census hardening in
#: ``_sulfonate_ester_bond_count``; the cardinal no-false-vouch requires every one to recognize as NOT sulfonate.
_MUST_NOT_VOUCH = [
    ("mixed_anhydride_acetic_acid_F1", ("CS(=O)(=O)Cl", "CC(=O)O"), ("CC(=O)OS(=O)(=O)C", "Cl")),
    ("mixed_anhydride_tosyl_acetic_F1", ("Cc1ccc(cc1)S(=O)(=O)Cl", "CC(=O)O"),
     ("Cc1ccc(cc1)S(=O)(=O)OC(C)=O", "Cl")),
    ("mixed_anhydride_formic_F1", ("CS(=O)(=O)Cl", "OC=O"), ("O=COS(=O)(=O)C", "Cl")),
    ("gem_diol_masked_carbonyl_F2a", ("CS(=O)(=O)Cl", "OCO"), ("OCOS(=O)(=O)C", "Cl")),
    ("hemiacetal_masked_carbonyl_F2a", ("CS(=O)(=O)Cl", "COCO"), ("COCOS(=O)(=O)C", "Cl")),
    ("enol_masked_carbonyl_F2b", ("CS(=O)(=O)Cl", "C=CO"), ("C=COS(=O)(=O)C", "Cl")),
    ("phenol_aryl_O_coverage_loss", ("Oc1ccccc1", "CS(=O)(=O)Cl"), ("O(c1ccccc1)S(=O)(=O)C", "Cl")),
]


@pytest.mark.parametrize("name,rs,ps", _MUST_NOT_VOUCH, ids=[c[0] for c in _MUST_NOT_VOUCH])
def test_wave_c_kills_do_not_false_vouch_as_sulfonate(name, rs, ps):
    # the CARDINAL gate: a mixed anhydride (acyl-O), a masked carbonyl (gem-diol / hemiacetal / enol) and an aryl
    # phenol-O are NOT alkyl sulfonate esters -- each must recognize as NOT a sulfonate-ester transfer.
    klass = recognize_reaction_type(bench._hand(rs, ps))
    assert klass is None or "sulfonate-ester transfer" not in str(klass), f"{name} FALSE-VOUCHED as {klass!r}"


def test_benzyl_is_a_genuine_alkyl_positive():
    # the new 4th positive replacing phenol: benzyl's carbinol carbon is sp3 (aryl only at the BETA position).
    klass = recognize_reaction_type(bench._hand(("OCc1ccccc1", "CS(=O)(=O)Cl"), ("C(c1ccccc1)OS(=O)(=O)C", "Cl")))
    assert klass is not None and "sulfonate-ester transfer" in str(klass)


def test_bond_count_rejects_sulfate_and_anhydride_but_counts_genuine_alkyl_ester():
    # the census is the load-bearing soundness surface: it counts GENUINE alkyl sulfonate-ester linkages only.
    assert _sulfonate_ester_bond_count(parse_smiles("COS(=O)(=O)C")) == 1          # methyl mesylate: one genuine
    assert _sulfonate_ester_bond_count(parse_smiles("CCOS(=O)(=O)C")) == 1         # ethyl mesylate: one genuine
    assert _sulfonate_ester_bond_count(parse_smiles("COS(=O)(=O)OC")) == 0         # dimethyl SULFATE: no S-C (F3)
    assert _sulfonate_ester_bond_count(parse_smiles("COS(=O)(=O)Cl")) == 0         # methyl chlorosulfate: no S-C (F3)
    assert _sulfonate_ester_bond_count(parse_smiles("CC(=O)OS(=O)(=O)C")) == 0     # mixed anhydride: acyl-O, not ester
    assert _sulfonate_ester_bond_count(parse_smiles("OCOS(=O)(=O)C")) == 0         # gem-diol masked carbonyl
    assert _sulfonate_ester_bond_count(parse_smiles("O(c1ccccc1)S(=O)(=O)C")) == 0  # phenyl: aryl carbinol, not sp3


def _safe(pred, step) -> bool:
    try:
        return bool(pred(step))
    except Exception:
        return False


def test_validate_is_green():
    assert bench.validate() is True
