"""Reproducible Rule-1a mancude controls; no network or optional toolkit required.

Source absolutes: Hanson et al. (2018), Fig. 3, validation-suite VS032/033, both 2S.
https://github.com/cipvalidationsuite/ValidationSuite/blob/master/compounds.smi
Duplicate-number source: IUPAC Blue Book P-92.1.4.4.
https://iupac.qmul.ac.uk/BlueBook/P9.html#P-92.1.4.4

The family labels below follow the existing anchored SMILES geometry convention and the elementary
priority O > aryl carbon > methyl > H. They check spelling/reflection and are not external absolutes.
The separate external-oracle probe supplies independent implementation evidence, when installed.
"""
from __future__ import annotations

import json

from smartchem.smiles import cip_labels


SOURCE_ANCHORS = (
    ("VS032", r"O[C@H](/C=N\C)C1=NC=CC=C1", ("S",)),
    ("VS033", r"O[C@H](/C=N\C)C=1N=CC=CC1", ("S",)),
)

# Each pair describes the same ligand attachment, one aromatic and one explicit Kekule spelling.
LIGANDS = (
    ("phenyl", "c1ccccc1", "C1=CC=CC=C1"),
    ("2-pyridyl", "c1ccccn1", "C1=CC=CC=N1"),
    ("3-pyridyl", "c1cccnc1", "C1=CC=CN=C1"),
    ("4-pyridyl", "c1ccncc1", "C1=CC=NC=C1"),
    ("pyrimidinyl", "c1ncccn1", "C1=NC=CC=N1"),
    ("2-furyl", "c1ccco1", "C1=CC=CO1"),
    ("2-thienyl", "c1cccs1", "C1=CC=CS1"),
    ("2-pyrrolyl", "c1ccc[nH]1", "C1=CC=C[NH]1"),
    ("imidazolyl", "c1ncc[nH]1", "C1=NC=C[NH]1"),
    ("naphthyl", "c1ccc2ccccc2c1", "C1=CC=C2C=CC=CC2=C1"),
    ("quinolyl", "c1ccc2ncccc2c1", "C1=CC=C2N=CC=CC2=C1"),
    ("indolyl", "c1ccc2[nH]ccc2c1", "C1=CC=C2[NH]C=CC2=C1"),
)


def report() -> dict:
    anchors = []
    for source_id, smi, expected in SOURCE_ANCHORS:
        labels = cip_labels(smi)
        assert labels == expected, (source_id, smi, labels, expected)
        anchors.append({"id": source_id, "smiles": smi, "expected": expected, "labels": labels})
    families = []
    for name, aromatic, kekule in LIGANDS:
        named = [cip_labels(f"C[C@H](O){ligand}") for ligand in (aromatic, kekule)]
        mirrors = [cip_labels(f"C[C@@H](O){ligand}") for ligand in (aromatic, kekule)]
        ties = [cip_labels(f"O[C@H]({left}){right}")
                for left, right in ((aromatic, aromatic), (aromatic, kekule), (kekule, aromatic), (kekule, kekule))]
        assert named == [("S",), ("S",)], (name, named)
        assert mirrors == [("R",), ("R",)], (name, mirrors)
        assert ties == [(), (), (), ()], (name, ties)
        families.append({"name": name, "aromatic": aromatic, "kekule": kekule,
                         "labels": named, "mirrors": mirrors, "identical_ligand_labels": ties})
    return {"source_anchors": anchors, "families": families, "family_count": len(families),
            "family_comparisons": len(families) * 8,
            "scope": "bounded neutral mancude Rule 1a; source absolutes plus relational family controls"}


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
