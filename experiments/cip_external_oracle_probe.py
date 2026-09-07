"""Optional external CIP cross-check; RDKit is deliberately NOT a runtime dependency.

Run from the repository root with RDKit on PYTHONPATH::

    python -m experiments.cip_external_oracle_probe --output /tmp/cip-external.json

Uses rdCIPLabeler (the accurate Hanson/Mayfield implementation, not legacy CIP).
The external parser, graph construction and labeler provide an implementation
bearing; the underlying CIP specification is shared with SmartChem. This finite
probe is not a proof of Rule-1a completeness or correctness on arbitrary graphs.
Only an emitted wrong label fails: unresolved priorities may defer. Per-case
results preserve deferrals, so empty output cannot masquerade as agreement.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

from smartchem.smiles import SmilesError, cip_labels


# Chosen independently of the mancude builder's fixtures: carbon/pyridine isomers,
# heteroatom donors, fused and linked rings, and nonaromatic competing ligands.
LIGANDS = (
    "C", "CC", "C(C)C", "C=C", "C(=O)O", "Cc1ccccc1",
    "c1ccccc1", "c1ccccn1", "c1cccnc1", "c1ccncc1",
    "c1nccnc1", "c1ccco1", "c1cccs1", "c1ccc[nH]1",
    "c1ccc2ccccc2c1", "c1ccc2ncccc2c1", "c1ccc(-c2ccccc2)cc1",
)


def probe() -> dict:
    try:
        from rdkit import Chem, rdBase
        from rdkit.Chem import rdCIPLabeler
    except ImportError as exc:
        raise SystemExit("This optional probe requires RDKit; no comparison was run.") from exc

    def reference(mol):
        mol = Chem.Mol(mol)
        for atom in mol.GetAtoms():
            if atom.HasProp("_CIPCode"):
                atom.ClearProp("_CIPCode")
        rdCIPLabeler.AssignCIPLabels(mol, maxRecursiveIterations=100000)
        return tuple(sorted(a.GetProp("_CIPCode") for a in mol.GetAtoms()
                            if a.HasProp("_CIPCode")))

    # Absolute instrument calibration and false-centre negative control.
    anchors = {
        "N[C@@H](C)C(=O)O": ("S",),
        "C([C@@H](C(=O)O)N)S": ("R",),
        "[C@H](F)(Cl)Br": ("S",),
        "O[C@H](c1ccccn1)c1ccccn1": (),
    }
    for smiles, expected in anchors.items():
        if reference(Chem.MolFromSmiles(smiles)) != expected:
            raise AssertionError(f"External oracle calibration failed: {smiles}: {expected}")

    rows = []
    for a, b in itertools.combinations_with_replacement(LIGANDS, 2):
        for sense in ("@", "@@"):
            original = f"O[C{sense}H]({a}){b}"
            mol = Chem.MolFromSmiles(original)
            if mol is None:
                raise AssertionError(f"Invalid external probe fixture: {original}")
            expected = reference(mol)
            if len(expected) != int(a != b):
                raise AssertionError(f"Unexpected number of reference centres: {original}: {expected}")
            identity = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
            reverse = Chem.RenumberAtoms(mol, list(reversed(range(mol.GetNumAtoms()))))
            variants = {
                "written": original,
                "canonical_aromatic": Chem.MolToSmiles(mol, canonical=True),
                "canonical_kekule": Chem.MolToSmiles(mol, canonical=True, kekuleSmiles=True),
                "reverse_atom_order": Chem.MolToSmiles(reverse, canonical=False),
            }
            for representation, smiles in variants.items():
                # The lawful transform must preserve the reference stereoisomer.
                transformed = Chem.MolFromSmiles(smiles)
                if (transformed is None or reference(transformed) != expected or
                        Chem.MolToSmiles(transformed, canonical=True, isomericSmiles=True) != identity):
                    raise AssertionError(f"Representation changed the reference molecule: {original}: {smiles}")
                try:
                    got = cip_labels(smiles)
                    status = "mismatch" if got and got != expected else (
                        "named_match" if got else "deferred" if expected else "true_tie")
                    error = None
                except SmilesError as exc:
                    got, status, error = (), "parser_refusal", str(exc)
                rows.append({"ligands": [a, b], "sense": sense,
                             "representation": representation, "smiles": smiles,
                             "expected": expected, "actual": got,
                             "status": status, "error": error})

    counts = {status: sum(r["status"] == status for r in rows) for status in
              ("named_match", "true_tie", "deferred", "parser_refusal", "mismatch")}
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"schema": "smartchem.cip-external-probe/v1", "rdkit_version": rdBase.rdkitVersion,
            "oracle": "rdCIPLabeler.AssignCIPLabels(maxRecursiveIterations=100000)",
            "boundary": "finite external implementation comparison; shared CIP specification; deferrals counted",
            "anchors": len(anchors), "base_cases": len(rows) // 4,
            "representations_per_base": 4, "counts": counts,
            "rows_sha256": hashlib.sha256(encoded).hexdigest(), "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = probe()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    return int(report["counts"]["mismatch"] > 0 or report["counts"]["named_match"] == 0)


if __name__ == "__main__":
    raise SystemExit(main())
