"""Optional finite mancude review panel; RDKit is not a SmartChem runtime dependency.

The reviewer chose this donor/fused-heterocycle and unsupported-boundary panel separately
from the builder's fixtures and the 17-ligand external panel. The implementation was visible
during review: this is a fresh-case external implementation bearing, not a blind proof.
The CIP specification and RDKit parser/labeler remain shared sources of assumptions.

Run with RDKit on PYTHONPATH::

    python -m experiments.cip_mancude_adversarial_probe --output /tmp/cip-review.json

Every emitted label must match the accurate rdCIPLabeler. Deferrals and parser refusals
remain counted; this instrument does not certify completeness or general CIP soundness.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import time
from unittest.mock import patch

import smartchem.smiles as implementation


LIGANDS = (
    "c1ncc[nH]1", "c1nc[nH]c1", "c1nn[nH]c1", "c1n[nH]nc1",
    "c1nocc1", "c1ncoc1", "c1nccs1", "c1ncsc1", "c1nnco1", "c1nocn1",
    "c1nc2ccccc2o1", "c1nc2ccccc2s1", "c1nc2ccccc2[nH]1",
    "c1ccc2[nH]ccc2c1", "c1ccc2occc2c1", "c1ccc2sccc2c1",
    "c1ccc2[nH]cnc2c1", "c1cc[n+]([O-])cc1", "C1=CC(=O)C=CC1=O",
    "C1=CC=CC=CC=C1", "C1=NC=NC=N1", "C1=CC=CN1C",
    "c1cc(Cl)cnc1", "c1cc(O)cnc1", "c1cc(N)cnc1", "C(=N)N", "C#N",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(*, max_seconds: float = 120.0) -> dict:
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("max_seconds must be finite and positive")
    try:
        from rdkit import Chem, rdBase
        from rdkit.Chem import rdCIPLabeler
    except ImportError as exc:
        raise SystemExit("This optional probe requires RDKit; no comparison was run.") from exc

    source_path = Path(implementation.__file__).resolve()
    source_sha256 = _sha256(source_path)
    start = time.monotonic()

    def reference(mol):
        if mol is None:
            raise ValueError("RDKit refused an oracle fixture")
        mol = Chem.Mol(mol)
        for atom in mol.GetAtoms():
            if atom.HasProp("_CIPCode"):
                atom.ClearProp("_CIPCode")
        rdCIPLabeler.AssignCIPLabels(mol, maxRecursiveIterations=100000)
        return tuple(sorted(atom.GetProp("_CIPCode") for atom in mol.GetAtoms()
                            if atom.HasProp("_CIPCode")))

    anchors = {"N[C@@H](C)C(=O)O": ("S",), "[C@H](F)(Cl)Br": ("S",),
               "O[C@H](c1ncc[nH]1)c1ncc[nH]1": ()}
    for smiles, expected in anchors.items():
        if reference(Chem.MolFromSmiles(smiles)) != expected:
            raise RuntimeError(f"Oracle calibration failed: {smiles}")

    rows = []
    for a, b in itertools.combinations_with_replacement(LIGANDS, 2):
        original = f"O[C@H]({a}){b}"
        mol = Chem.MolFromSmiles(original)
        expected = reference(mol)
        # These 27 rooted ligands are constitutionally distinct. Detect accidental stereo
        # stripping as well as an unexpected extra centre before trusting an empty oracle label.
        if len(expected) != (0 if a == b else 1):
            raise RuntimeError(f"Fixture escaped the declared zero/one-centre scope: {original}")
        canonical = Chem.MolToSmiles(mol)
        variants = {
            "written": original,
            "kekule": Chem.MolToSmiles(mol, kekuleSmiles=True),
            "reverse": Chem.MolToSmiles(
                Chem.RenumberAtoms(mol, list(reversed(range(mol.GetNumAtoms())))), canonical=False),
        }
        for representation, smiles in variants.items():
            transformed = Chem.MolFromSmiles(smiles)
            if (transformed is None or Chem.MolToSmiles(transformed) != canonical
                    or reference(transformed) != expected):
                raise RuntimeError(f"Transform changed the reference stereoisomer: {smiles}")
            try:
                got, error = implementation.cip_labels(smiles), None
            except implementation.SmilesError as exc:
                got, error = (), str(exc)
            status = ("parser_refusal" if error else "mismatch" if got and got != expected else
                      "named_match" if got else "deferred" if expected else "true_tie")
            rows.append({"smiles": smiles, "expected": expected, "actual": got, "status": status,
                         "representation": representation, "error": error})
        if time.monotonic() - start > max_seconds:
            raise TimeoutError("Finite probe exceeded max_seconds; no complete report was produced")

    required = "O[C@H](c1ccccn1)c1nccnc1"
    early = "F[C@H](Cl)c1ccccn1"
    required_label, early_label = reference(Chem.MolFromSmiles(required)), reference(Chem.MolFromSmiles(early))
    if (not required_label or implementation.cip_labels(required) != required_label
            or not early_label or implementation.cip_labels(early) != early_label):
        raise RuntimeError("Cap controls require non-vacuous, correct labels before lowering limits")
    cap_controls = []
    for cap in ("_CIP_MANCUDE_MAX_ATOMS", "_CIP_MANCUDE_MAX_MATCHINGS", "_CIP_MANCUDE_WORK_BUDGET"):
        with patch.object(implementation, cap, 0):
            required_result, early_result = implementation.cip_labels(required), implementation.cip_labels(early)
        if required_result or early_result != early_label:
            raise RuntimeError(f"Resource cap did not defer only the dependent comparison: {cap}")
        cap_controls.append({"cap": cap, "value": 0, "dependent_result": required_result,
                             "early_decision_result": early_result})

    if _sha256(source_path) != source_sha256:
        raise RuntimeError("SmartChem source changed during the probe; rerun against a stable file")
    counts = Counter(row["status"] for row in rows)
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "smartchem.cip-mancude-adversarial-probe/v1", "rdkit_version": rdBase.rdkitVersion,
        "oracle": "rdCIPLabeler.AssignCIPLabels(maxRecursiveIterations=100000)",
        "boundary": "finite reviewer case panel; shared CIP specification; deferrals and refusals counted",
        "source_file": "smartchem/smiles.py", "source_sha256": source_sha256,
        "probe_file": "experiments/cip_mancude_adversarial_probe.py", "probe_sha256": _sha256(Path(__file__)),
        "anchors": len(anchors), "ligands": len(LIGANDS), "base_cases": len(rows) // 3,
        "representations_per_base": 3, "rows_count": len(rows), "complete": True,
        "counts": {status: counts[status] for status in
                   ("named_match", "true_tie", "deferred", "parser_refusal", "mismatch")},
        "cap_controls": cap_controls,
        "rows_sha256": hashlib.sha256(encoded).hexdigest(), "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    args = parser.parse_args()
    report = probe(max_seconds=args.max_seconds)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    summary = {key: value for key, value in report.items() if key != "rows"}
    if args.summary_output:
        args.summary_output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return int(report["counts"]["mismatch"] > 0 or report["counts"]["named_match"] == 0)


if __name__ == "__main__":
    raise SystemExit(main())
