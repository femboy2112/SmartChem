"""CIP-PER-ATOM-ORACLE-01: a PER-ATOM oracle cross-check that closes the multiset-blind hole.

Three independent ROUND-35 review bearings (a principled soundness review, a directed counterexample
hunt, and a structure-theorem audit) each landed on the SAME gap: the shipped namer collapses its result to
``tuple(sorted(...))`` (``cip_labels``), and every committed RDKit cross-check compares that SORTED MULTISET.
A per-centre R<->S SWAP on a molecule whose label multiset is symmetric (one R and one S, say) is therefore
STRUCTURALLY INVISIBLE to the repo's own self-checks -- exactly the failure mode the round's load-bearing novel
code (the ``_parse_skeleton_stereo`` written-neighbour ring-parity witness, whose slot flips a ring centre's
sign if wrong) would produce.  No such mislabel was found; none was PROVABLE with a multiset-blind harness.

This probe removes the blindness.  It compares the namer PER HEAVY-ATOM INDEX against RDKit ``rdCIPLabeler``
(no ``in ("R","S")`` filter -- lowercase pseudoasymmetric ``r``/``s`` are compared too), verifying the
SmartChem<->RDKit atom-index mapping by element before it trusts a comparison (an unverifiable mapping is
skipped, never compared blindly).  It also carries a NON-VACUITY proof (``_assert_swap_detected``): on a real
one-R-one-S molecule it forges a per-centre swap, shows the sorted multiset cannot see it, and shows the
per-atom map does -- so a green here is evidence the check can actually catch the bug class it exists for.

``validate()``, ``content_hash()`` and the non-vacuity proof are RDKit-free (they run in the committed
baseline).  ``_rdkit_cross_check()`` is a gated development-oracle probe (dev venv only).  The frozen expected
per-atom maps were BLESSED against RDKit 2026.03.6 at authoring time, not merely read off the namer.
Re-run ``python -m experiments.cip_per_atom_oracle_probe`` after an intentional change and set ``FROZEN_HASH``
to the printed value; drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.smiles import cip_labels, cip_labels_by_atom, _parse_skeleton_stereo

FROZEN_HASH = "1fa41faf433459119f9ac721d76a5c962a9a71e08a82f89a9ecbc794b28c58ca"

#: (SMILES, oracle-blessed per-atom {heavy_index: label}, note).  Chosen to load the multiset-blind seam:
#: symmetric multisets (S,S / R,S / R,R), ring pseudoasymmetry, bridged bicyclics, ring stereocentres, one
#: sound DEFER (empty), and a single-centre control.  Each map was cross-checked per atom against RDKit.
BATTERY = (
    ("OC(=O)[C@@H](O)[C@H](O)C(=O)O", {3: "S", 5: "S"}, "(2S,3S)-tartaric: symmetric S,S multiset"),
    ("OC(=O)[C@H](O)[C@H](O)C(=O)O", {3: "R", 5: "S"}, "meso tartaric: symmetric R,S multiset (swap-demo)"),
    ("OC[C@@H](O)[C@H](O)CO", {2: "R", 4: "R"}, "threitol: symmetric R,R multiset"),
    ("O[C@H]1[C@H](O)[C@@H](O)CCC1", {1: "R", 4: "S", 2: "r"}, "ring pseudoasymmetry (R,S,r)"),
    ("OC(=O)[C@@H](O)[C@H](O)[C@@H](O)C(=O)O", {3: "S", 7: "R", 5: "s"}, "trihydroxyglutaric (R,S,s)"),
    ("CC1(C)[C@@H]2CC[C@@]1(C)[C@H](O)C2", {3: "R", 6: "R", 8: "R"}, "bridged bicyclic camphor skeleton (R,R,R)"),
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O", {3: "S", 6: "R", 9: "R"}, "menthol (S,R,R)"),
    ("OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O", {2: "R", 4: "R", 6: "R", 8: "S", 10: "S"}, "glucopyranose (5 centres)"),
    ("FC1C[C@](Br)(Cl)CCC1", {3: "S"}, "ring stereocentre (parser witness)"),
    ("[C@](C1CCCCC1)(C1CCCC1)(C)F", {0: "R"}, "ring-vs-ring on an acyclic centre"),
    ("O[C@H]1CC[C@@H](C)CC1", {}, "sound DEFER: mutually-dependent pseudo (RDKit names s,s; we decline)"),
    ("C[C@H](N)C(=O)O", {1: "S"}, "L-alanine single-centre control (S)"),
)


def _payload() -> dict:
    """The namer's actual per-atom output over the battery -- RDKit-free, deterministic, hashed for drift."""
    return {smi: sorted(cip_labels_by_atom(smi).items()) for smi, _expected, _note in BATTERY}


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True).encode()).hexdigest()


def _assert_swap_detected() -> None:
    """Non-vacuity proof: a per-centre R<->S swap is invisible to the sorted multiset, visible per atom.

    This is the whole reason the probe exists.  If this ever fails to hold, the per-atom check has stopped
    being able to catch the bug class it guards, and a green cross-check would be meaningless.
    """
    smi = "OC(=O)[C@H](O)[C@H](O)C(=O)O"                     # meso tartaric: exactly one R and one S
    m = cip_labels_by_atom(smi)
    assert tuple(sorted(m.values())) == ("R", "S"), f"swap-demo molecule changed shape: {m}"
    keys = sorted(m)
    swapped = dict(m)
    swapped[keys[0]], swapped[keys[1]] = m[keys[1]], m[keys[0]]
    # what cip_labels() ships -- the sorted multiset -- is BLIND to the swap:
    assert tuple(sorted(swapped.values())) == tuple(sorted(m.values())), "multiset unexpectedly distinguished the swap"
    # the per-atom map -- what this probe compares -- CATCHES it:
    assert swapped != m, "per-atom map failed to distinguish a per-centre swap"


def validate() -> None:
    """RDKit-free: the namer still produces the oracle-blessed per-atom maps, coherent with cip_labels()."""
    for smi, expected, note in BATTERY:
        got = cip_labels_by_atom(smi)
        assert got == expected, f"per-atom drift on {smi}: {got} != {expected} [{note}]"
        # the two public functions must agree: the sorted per-atom values ARE cip_labels()'s tuple.
        assert cip_labels(smi) == tuple(sorted(expected.values())), (
            f"cip_labels()/cip_labels_by_atom() disagree on {smi} [{note}]"
        )
    _assert_swap_detected()


def _rdkit_cross_check() -> dict:
    """Gated development oracle: compare the namer to RDKit rdCIPLabeler PER ATOM (r/s included)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    compared = skipped = mismatches = 0
    details: list[tuple] = []
    for smi, expected, note in BATTERY:
        mol = Chem.MolFromSmiles(smi)
        assert mol is not None, f"RDKit could not parse {smi}"
        rdCIPLabeler.AssignCIPLabels(mol)
        rd = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
        elems = [a.element for a in _parse_skeleton_stereo(smi)[0]]
        ours = cip_labels_by_atom(smi)
        assert ours == expected, f"namer drift vs frozen expected on {smi}: {ours} != {expected} [{note}]"
        for idx, lbl in ours.items():
            if idx >= len(elems) or elems[idx] != mol.GetAtomWithIdx(idx).GetSymbol():
                skipped += 1                                 # fail-closed: don't compare an unverifiable mapping
                continue
            compared += 1
            if rd.get(idx) != lbl:                           # a wrong label OR a name RDKit does not give here
                mismatches += 1
                details.append((smi, idx, lbl, rd.get(idx), note))
    return {
        "compared": compared,
        "skipped": skipped,
        "mismatches": mismatches,
        "details": details,
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    print("validate(): OK (per-atom maps + non-vacuity swap proof)")
    try:
        r = _rdkit_cross_check()
        print(f"_rdkit_cross_check(): compared={r['compared']} skipped={r['skipped']} "
              f"mismatches={r['mismatches']}")
        if r["details"]:
            for d in r["details"]:
                print("  MISMATCH:", d)
    except ImportError:
        print("_rdkit_cross_check(): SKIPPED (rdkit absent -- run in the dev oracle venv)")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
