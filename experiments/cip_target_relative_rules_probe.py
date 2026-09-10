"""CIP-TARGET-RELATIVE-4B4C-01: the VERIFIED DEFER of CIP target-relative Rules 4b/4c (item 1).

A sound target-relative Rules 4b/4c is a from-scratch build of the hardest, most bug-prone stratum of CIP; it is
NOT a bounded extension of the ROUND-35 auxiliary pass, and NO in-scope consumer forces it.  This probe is the
committed EVIDENCE that a defer is the correct outcome this round (the R32 Rule-1b precedent:
``an-oracle-driven-existence-check-can-prove-a-defer``).  It proves three things:

1.  BOUNDARY.  The forcing class -- symmetric even-ring MUTUALLY-pseudoasymmetric centres -- is deferred SOUNDLY:
    the repo returns no label (``cip_labels`` ``()``), RDKit ``rdCIPLabeler`` names them lowercase ``s,s`` (a
    pseudoasymmetric assignment) via its root-relative distance-batched ``labelAux`` recursion.  The repo declines
    rather than guess; it never mislabels.

2.  STRUCTURE.  The defer is PRECISELY the mutual-pseudo case, not a blanket ring failure.  When the ring symmetry
    is broken (5- or 7-membered homolog) the two centres are resolved by Rules 1a-3 and the repo NAMES them,
    matching RDKit.  And when the auxiliary pool is NON-empty (a ring pseudoasymmetric centre flanked by two
    already-resolved R/S centres) the bounded ROUND-35 Rule-4a/5 pass DOES name the ``r`` -- so the wall is
    exactly the case where BOTH mutually-dependent centres are unresolved by Rules 1a-3, leaving the pool empty
    with nothing to seed the bounded pass (a build cannot widen a threshold to reach it -- it needs the recursion).

3.  NO CONSUMER.  The north-star litmus targets are STEREOCENTER-FREE (paracetamol, aspirin), and a battery of
    real chiral drugs (menthol, tartaric, ...) is fully named by the shipped rules -- none needs 4b/4c.  The
    forcing class is synthetic, authored to probe the boundary.

Why a bounded hack would be UNSOUND: the repo has NO genuine Rule 4b (its ``_cip_compare_rules45`` is a faithful
port of RDKit's Rule5New two-fixed-reference trick; Rule 4b's reference is a per-branch nearest-sphere MAJORITY
vote, absent here), so a special-case naming the target ``s,s`` without real majority-vote 4b would silently
diverge from RDKit wherever the majority-vote reference matters -- a mislabel, not mere incompleteness.  The
phased build plan lives in ``docs/research/CIP_TARGET_RELATIVE_RULES_SCOPE_v0.1.md``.

``validate()``, ``content_hash()`` and the non-vacuity proof are RDKit-free (committed baseline).
``_rdkit_cross_check()`` is a gated development-oracle probe (dev venv only); the frozen RDKit references below
were BLESSED against RDKit 2026.03.6 at authoring time.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.smiles import _parse_skeleton_stereo, cip_labels, cip_labels_by_atom

FROZEN_HASH = "7e1ee9731814002c7a8cf1c66fe22834d0c51c8ef33af1834d35ceffa1d2a9b9"

#: (SMILES, blessed repo per-atom map, blessed RDKit per-atom map, category, note).
#: category: "forcing" (repo DEFERS, RDKit names -> the 4b/4c wall) | "named" (repo NAMES, structure control) |
#: "existence" (no consumer: north-star achiral targets + fully-named real chiral drugs).
BATTERY = (
    # --- the forcing class: symmetric even-ring MUTUALLY-pseudoasymmetric centres.  Aux pool empty (BOTH centres
    #     unresolved by Rules 1a-3), so the bounded 4a/5 pass is never admitted; RDKit names s,s by recursion.
    ("O[C@H]1CC[C@@H](C)CC1", {}, {1: "s", 4: "s"}, "forcing",
     "4-methylcyclohexan-1-ol: mutual pseudo, repo DEFERS / RDKit s,s"),
    ("C[C@H]1CC[C@@H](C)CC1", {}, {1: "s", 4: "s"}, "forcing",
     "trans/cis-1,4-dimethylcyclohexane: mutual pseudo, repo DEFERS / RDKit s,s"),
    # --- NAMED controls: symmetry-broken homologs (odd ring / different size) -> Rules 1a-3 resolve, repo NAMES.
    #     Proof the defer is PRECISELY the mutual-pseudo case, not a blanket ring failure.
    ("O[C@H]1CC[C@@H](C)CCC1", {1: "R", 4: "S"}, {1: "R", 4: "S"}, "named",
     "7-ring homolog: symmetry broken -> NAMED (R,S)"),
    ("O[C@H]1C[C@@H](C)CC1", {1: "R", 3: "S"}, {1: "R", 3: "S"}, "named",
     "5-ring homolog: symmetry broken -> NAMED (R,S)"),
    # --- the bounded Rule-4a/5 pass DOES resolve a pseudoasymmetric centre when the auxiliary pool is NON-empty:
    #     the flanking R and S centres seed it, so the 'r' at index 2 is named.  Contrast the empty-pool forcing class.
    ("O[C@H]1[C@H](O)[C@@H](O)CCC1", {1: "R", 4: "S", 2: "r"}, {1: "R", 4: "S", 2: "r"}, "named",
     "ring pseudo, NON-empty aux pool -> bounded 4a/5 names the r"),
    # --- EXISTENCE: no in-scope consumer.  North-star targets are stereocenter-free; real chiral drugs fully named.
    ("CC(=O)Nc1ccc(O)cc1", {}, {}, "existence", "paracetamol (north star): achiral, no centres"),
    ("CC(=O)Oc1ccccc1C(=O)O", {}, {}, "existence", "aspirin (north star): achiral"),
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O", {3: "S", 6: "R", 9: "R"}, {3: "S", 6: "R", 9: "R"}, "existence",
     "menthol: fully named by the shipped rules"),
    ("OC(=O)[C@@H](O)[C@H](O)C(=O)O", {3: "S", 5: "S"}, {3: "S", 5: "S"}, "existence",
     "(2S,3S)-tartaric: fully named"),
)


def _payload() -> dict:
    """The namer's ACTUAL per-atom output over the battery -- RDKit-free, deterministic, hashed for drift."""
    return {smi: sorted(cip_labels_by_atom(smi).items()) for smi, *_ in BATTERY}


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True).encode()).hexdigest()


def _assert_structure_theorem() -> None:
    """The defer is PRECISELY the empty-aux-pool mutual-pseudo case (RDKit-free, from repo output alone).

    * the forcing class defers ALL its centres (both marked, none named -> the pool the bounded pass would read
      is empty);
    * a symmetry-broken homolog of the SAME motif NAMES both centres (so it is not a blanket ring failure);
    * a ring pseudoasymmetric centre with a NON-empty pool IS named by the bounded 4a/5 pass (so the pass works
      when seeded -- the wall is the empty pool, exactly what the recursion is needed for).
    """
    target = "O[C@H]1CC[C@@H](C)CC1"
    marked = [i for i, a in enumerate(_parse_skeleton_stereo(target)[0]) if a.chirality]
    assert len(marked) == 2, f"the forcing target must carry two marked centres, got {marked}"
    assert cip_labels_by_atom(target) == {}, "the forcing class must defer ALL centres (empty aux pool)"
    assert cip_labels_by_atom("O[C@H]1CC[C@@H](C)CCC1") == {1: "R", 4: "S"}, "symmetry-broken homolog must NAME"
    assert cip_labels_by_atom("O[C@H]1[C@H](O)[C@@H](O)CCC1") == {1: "R", 4: "S", 2: "r"}, (
        "the bounded 4a/5 pass must name a pseudo centre when the aux pool is non-empty"
    )


def validate() -> None:
    """RDKit-free: the namer still produces the blessed per-atom maps; the forcing class defers, controls name."""
    for smi, expected, _rd, category, note in BATTERY:
        got = cip_labels_by_atom(smi)
        assert got == expected, f"per-atom drift on {smi}: {got} != {expected} [{note}]"
        assert cip_labels(smi) == tuple(sorted(expected.values())), f"cip_labels disagrees on {smi} [{note}]"
        if category == "forcing":
            assert got == {}, f"a forcing-class centre must DEFER, not name: {smi} -> {got}"
    _assert_structure_theorem()


def _rdkit_cross_check() -> dict:
    """Gated development oracle: confirm the forcing class is nameable-but-declined and controls match RDKit."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    compared = skipped = mismatches = forcing_confirmed = 0
    details: list[tuple] = []
    for smi, expected, rd_expected, category, note in BATTERY:
        mol = Chem.MolFromSmiles(smi)
        assert mol is not None, f"RDKit could not parse {smi}"
        rdCIPLabeler.AssignCIPLabels(mol)
        rd = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
        assert rd == rd_expected, f"RDKit reference drift on {smi}: {rd} != {rd_expected} [{note}]"
        assert cip_labels_by_atom(smi) == expected, f"namer drift vs blessed on {smi} [{note}]"
        elems = [a.element for a in _parse_skeleton_stereo(smi)[0]]
        if category == "forcing":
            # the repo declines EXACTLY the centres RDKit names (nameable-but-declined, never mislabelled)
            assert cip_labels_by_atom(smi) == {} and rd, f"forcing class must be declined-yet-RDKit-named: {smi}"
            forcing_confirmed += 1
            continue
        for idx, lbl in cip_labels_by_atom(smi).items():
            if idx >= len(elems) or elems[idx] != mol.GetAtomWithIdx(idx).GetSymbol():
                skipped += 1
                continue
            compared += 1
            if rd.get(idx) != lbl:
                mismatches += 1
                details.append((smi, idx, lbl, rd.get(idx), note))
    return {
        "compared": compared,
        "skipped": skipped,
        "mismatches": mismatches,
        "forcing_confirmed": forcing_confirmed,
        "details": details,
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


def report() -> dict:
    validate()
    return {
        "forcing_class": sum(1 for *_r, c, _n in BATTERY if c == "forcing"),
        "named_controls": sum(1 for *_r, c, _n in BATTERY if c == "named"),
        "existence_no_consumer": sum(1 for *_r, c, _n in BATTERY if c == "existence"),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    print("validate(): OK (forcing-class defers, controls name, structure theorem holds)")
    try:
        r = _rdkit_cross_check()
        print(f"_rdkit_cross_check(): compared={r['compared']} skipped={r['skipped']} "
              f"mismatches={r['mismatches']} forcing_confirmed={r['forcing_confirmed']}")
        for d in r["details"]:
            print("  MISMATCH:", d)
    except ImportError:
        print("_rdkit_cross_check(): SKIPPED (rdkit absent -- run in the dev oracle venv)")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
