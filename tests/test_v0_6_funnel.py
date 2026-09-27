"""FUNNEL-01 -- pin the v0.6 release funnel aggregate, and prove the grammar on a FRESH holdout.

Two jobs:

* a regression anchor on the committed design-corpus funnel (the meter must not silently drift);
* a fresh HOLDOUT of formula spellings/families that were NOT used to design any parser branch (larger
  hydrate multipliers, different elements, higher charges), each asserted to the exact composition/layer,
  so a grammar that merely fit its own examples is caught.
"""
from __future__ import annotations

import pytest

from experiments.v0_6_front_door_funnel import run_funnel
from smartchem.identity_parse import InputKind, resolve_identity


def test_design_funnel_aggregate_is_stable():
    _, agg = run_funnel()
    # v0.6 hostile-review round added four repaired refusals (P0-B/C/D) -> total 36, typed_refusal 11; the
    # resolved/eligible denominators are unchanged (the new cases are all correct refusals, not new structures).
    assert agg == {
        "total": 36,
        "syntax_represented": 25,
        "composition_resolved": 25,
        "ambiguity_classified": 25,
        "structure_represented": 6,
        "structural_planning_eligible": 6,
        "typed_refusal": 11,
    }


def test_only_names_and_smiles_reach_structural_eligibility():
    rows, _ = run_funnel()
    eligible = {r.case_id for r in rows if r.structural_planning_eligible}
    # exactly the three registered NAMEs and three SMILES -- never a bare formula.
    assert eligible == {
        "n-paracetamol", "n-water", "n-acetic-anhydride",
        "s-paracetamol", "s-methyl-acetate", "s-methanol-CO",
    }


# -- fresh holdout: (input, kind, expected composition dict, expected charge, expected layer, eligible) -------
# None composition => expect a typed refusal (never reaches composition).
_HOLDOUT = [
    ("MgSO4·7H2O", InputKind.AUTO, {"Mg": 1, "S": 1, "O": 11, "H": 14}, 0, "FORMULA", False),
    ("Na2CO3·10H2O", InputKind.AUTO, {"Na": 2, "C": 1, "O": 13, "H": 20}, 0, "FORMULA", False),
    ("KAl(SO4)2·12H2O", InputKind.AUTO, {"K": 1, "Al": 1, "S": 2, "O": 20, "H": 24}, 0, "FORMULA", False),
    ("Fe2O3", InputKind.AUTO, {"Fe": 2, "O": 3}, 0, "FORMULA", False),
    ("Ca3(PO4)2", InputKind.AUTO, {"Ca": 3, "P": 2, "O": 8}, 0, "FORMULA", False),
    ("C6H12O6", InputKind.AUTO, {"C": 6, "H": 12, "O": 6}, 0, "FORMULA", False),
    ("PO4^3-", InputKind.FORMULA, {"P": 1, "O": 4}, -3, "FORMULA", False),
    ("Cr2O7^2-", InputKind.FORMULA, {"Cr": 2, "O": 7}, -2, "FORMULA", False),
    ("Mg²⁺", InputKind.FORMULA, {"Mg": 1}, 2, "FORMULA", False),
    ("(SiO2)n", InputKind.AUTO, None, 0, "NONE", False),          # parametric -> refused
    ("Zz9", InputKind.FORMULA, None, 0, "NONE", False),           # unknown element -> refused
]


@pytest.mark.parametrize("text,kind,comp,charge,layer,eligible", _HOLDOUT)
def test_fresh_holdout(text, kind, comp, charge, layer, eligible):
    if comp is None:
        from smartchem.identity_parse import IdentityParseError

        with pytest.raises(IdentityParseError):
            resolve_identity(text, kind)
        return
    r = resolve_identity(text, kind)
    assert dict(r.formula.counts) == comp, f"{text!r} composition"
    assert getattr(r.formula, "charge", 0) == charge, f"{text!r} charge"
    assert r.receipt.identity_layer == layer, f"{text!r} layer"
    assert r.constitution_established is eligible, f"{text!r} eligibility"
    # a bare formula must never be promoted to a selected structure
    if layer == "FORMULA":
        assert r.molecule is None
