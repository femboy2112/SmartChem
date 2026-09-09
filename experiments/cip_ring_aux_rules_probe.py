"""ROUND 35: written ring order, revised Rule 1b, and bounded auxiliary Rules 4a/5.

The committed battery is RDKit-free and freezes exact expected labels.  ``_rdkit_cross_check`` is the independent
development-oracle bearing (RDKit 2026.3.6); it also randomizes equivalent SMILES for fresh spelling-order probes.
The admitted auxiliary slice is deliberately small: one established R/S descriptor for Rule 4a, or exactly one
opposed R/S pair for revised Rule 5.  Recursive Rule 4b/4c cases remain explicit deferrals.
"""
from __future__ import annotations

import hashlib
import json

from smartchem import smiles
from smartchem.smiles import cip_labels, configuration_key

FROZEN_HASH = "1c3ceb6bc8623d9d302bcc6d7dc90868280b1e93fe752a43cdafe6aa1081ccc0"

OPENSMILES_EQUIVALENTS = (
    ("FC1C[C@](Br)(Cl)CCC1", "[C@]1(Br)(Cl)CCCC(F)C1", ("S",)),
    ("FC1C[C@@](Br)(Cl)CCC1", "[C@@]1(Br)(Cl)CCCC(F)C1", ("R",)),
)

# smiles, baked RDKit labels, expected ours, category, note
BATTERY = (
    ("C[C@H]1CCCCC1O", ("S",), ("S",), "ring-centre", "written-order constitutional ring centre"),
    ("O[C@H]1CCCC[C@@H]1O", ("S", "S"), ("S", "S"), "ring-centre", "two ring centres"),
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O", ("R", "R", "S"), ("R", "R", "S"), "ring-centre", "menthol"),
    ("[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl", ("R",), ("R",), "rule1b-rule2", "ring tie then isotope"),
    ("O[C@H](C12CCC(CC1)CC2)C(CCC1CC1)(CCC2CC2)CCC3CC3", ("S",), ("S",), "rule1b", "IUPAC P-9 Rule 1b example"),
    ("O[C@@H](C12CCC(CC1)CC2)C(CCC1CC1)(CCC2CC2)CCC3CC3", ("R",), ("R",), "rule1b", "IUPAC witness mirror"),
    ("[C@](C[C@H](F)Cl)(CC(F)Cl)(Br)I", ("R", "R"), ("R", "R"), "rule4a", "descriptor beats none"),
    ("[C@@](C[C@H](F)Cl)(CC(F)Cl)(Br)I", ("R", "S"), ("R", "S"), "rule4a", "centre mirror"),
    ("[C@](C[C@H](F)Cl)(C[C@@H](F)Cl)(Br)I", ("R", "S", "r"), ("R", "S", "r"), "rule5", "enantiomorphic ligands"),
    (r"C\C=C/[C@@H](\C=C\O)[C@H](C)[C@H](\C=C/C)\C=C\O", ("R", "S", "r"), ("R", "S", "r"), "rule5", "RDKit para example"),
    ("O[C@H]1CC[C@@H](C)CC1", ("s", "s"), (), "defer-rule4bc", "mutually dependent pseudo ring pair"),
    ("O[C@H](c1ccccn1)C1=NC=CC=C1", (), (), "agreed-defer", "true unresolved identical ligands"),
)


def _rule1b_isolation() -> dict:
    """Show the official example ties under Rule 1a and is decided by Rule 1b."""
    text = BATTERY[4][0]
    atoms, bonds, directions, written_tokens = smiles._parse_skeleton_stereo(text)
    work = [list(b) for b in bonds]
    smiles._kekulize_in_place(atoms, work, sum(a.charge for a in atoms))
    elems, filled = smiles._fill_hydrogens(atoms, work)
    adj = {i: [] for i in range(len(elems))}
    for bond in filled:
        adj[bond.i].append((bond.j, bond.order))
        adj[bond.j].append((bond.i, bond.order))
    mass = [smiles._cip_mass(elems[i], atoms[i].isotope if i < len(atoms) else 0)
            for i in range(len(elems))]
    aromatic, mancude = smiles._cip_mancude(atoms, work, adj)
    centre = next(i for i, atom in enumerate(atoms) if atom.chirality)
    hydrogens = iter(j for j, _ in adj[centre] if j >= len(atoms) and elems[j] == "H")
    written = [next(hydrogens) if token is None else token for token in written_tokens[centre]]
    roots = [smiles._cip_digraph(w, centre, (centre, w), adj, elems, mass, aromatic,
                                 [smiles._CIP_NODE_BUDGET], mancude, {}) for w in written]
    ctx = {"cmp": {}, "sc": {}, "budget": [smiles._CIP_COMPARE_BUDGET]}
    return {
        "written": written,
        "rule1a": smiles._cip_compare(roots[2], roots[3], ctx),
        "rule1b": smiles._cip_compare_rule1b(roots[2], roots[3], ctx),
    }


def content_hash() -> str:
    payload = {
        "battery": [[s, list(rd), list(exp), category] for s, rd, exp, category, _ in BATTERY],
        "live": [list(cip_labels(s)) for s, *_ in BATTERY],
        "opensmiles": [[a, b, list(cip_labels(a)), list(cip_labels(b))]
                       for a, b, _ in OPENSMILES_EQUIVALENTS],
        "rule1b": _rule1b_isolation(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> None:
    for a, b, expected in OPENSMILES_EQUIVALENTS:
        assert cip_labels(a) == cip_labels(b) == expected
        assert configuration_key(a) == configuration_key(b)
    for text, oracle, expected, category, note in BATTERY:
        got = cip_labels(text)
        assert got == expected, f"{text}: {got} != {expected} [{category}: {note}]"
        if category not in ("defer-rule4bc", "agreed-defer"):
            assert got == oracle, f"{text}: {got} != baked RDKit {oracle} [{note}]"
    isolation = _rule1b_isolation()
    assert isolation["rule1a"] == 0 and isolation["rule1b"] == 1


def _rdkit_cross_check() -> dict:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    def oracle(text):
        mol = Chem.MolFromSmiles(text)
        assert mol is not None, text
        rdCIPLabeler.AssignCIPLabels(mol)
        return tuple(sorted(atom.GetProp("_CIPCode") for atom in mol.GetAtoms() if atom.HasProp("_CIPCode"))), mol

    for text, baked, _expected, _category, note in BATTERY:
        live, _ = oracle(text)
        assert live == baked, f"stale oracle for {text}: {live} != {baked} [{note}]"

    # Fresh representation rotation: deterministic random equivalent SMILES for the fully admitted constitutional
    # ring centres.  This probes parser order separately from the fixed authored spellings.
    checked = mismatches = 0
    for text, baked, _expected, category, _note in BATTERY:
        if category in ("defer-rule4bc", "agreed-defer"):
            continue
        _, mol = oracle(text)
        for variant in Chem.MolToRandomSmilesVect(mol, 32, randomSeed=0x35):
            rd, _ = oracle(variant)
            got = cip_labels(variant)
            checked += 1
            mismatches += got != rd
    assert mismatches == 0
    return {"battery": len(BATTERY), "random_equivalents": checked, "mismatches": mismatches}


def report() -> dict:
    digest = content_hash()
    return {"battery": len(BATTERY), "rule1b_isolation": _rule1b_isolation(), "content_hash": digest,
            "frozen_hash": FROZEN_HASH, "hash_matches": digest == FROZEN_HASH}


if __name__ == "__main__":
    validate()
    try:
        print("rdkit:", _rdkit_cross_check())
    except ImportError:
        print("rdkit: SKIPPED (not installed)")
    print(json.dumps(report(), indent=2, sort_keys=True))
