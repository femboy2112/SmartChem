"""V1.1-COVERAGE-EXPANSION-111-115: the committed before/after reproducer for the #111 and #115 recognition pivot.

The forensic record is docs/research/V1_1_COVERAGE_EXPANSION_111_115.md. This probe emits the RAW Part-B facts:
the recognizer count and ``recognize_reaction_type`` for each family's vetted positive exemplar (lifted verbatim
from tests/test_sulfonate_ester_transfer_111.py and tests/test_claisen_condensation_115.py). It is checkout-
agnostic -- the SAME file runs under the v1.0.0 tree (expect 17 recognizers, both ``None``) and the 1.1 tree
(expect 20, both recognized), because ``ExperimentStep.assembling`` exists at v1.0.0:

    SP=.venv/lib/python3.12/site-packages
    git worktree add --detach /tmp/wt-v1.0.0 v1.0.0
    ( cd /tmp/wt-v1.0.0 && PYTHONPATH="/tmp/wt-v1.0.0:$PWD/$SP" .venv/bin/python -S experiments/v1_1_coverage_expansion_111_115_probe.py )
    .venv/bin/python experiments/v1_1_coverage_expansion_111_115_probe.py   # the current (1.1) tree

No verdict is emitted here; the reader compares the two trees. The committed 1.1-side assertions live in the two
regression files above (the v1.0.0 side is a historical fact about the ``v1.0.0`` tag).
"""
from __future__ import annotations

import json

from smartchem.experiment.reaction_type_oracle import _RECOGNIZERS, recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles


def _step(reactant_smis: tuple[str, ...], product_smis: tuple[str, ...]) -> ExperimentStep:
    """A conserving step built the checkout-agnostic way (primary product, reactants, products)."""
    return ExperimentStep.assembling(
        parse_smiles(product_smis[0]),
        tuple(parse_smiles(s) for s in reactant_smis),
        tuple(parse_smiles(s) for s in product_smis),
    )


# vetted positive exemplars, verbatim from the #111 / #115 regression files
STEP_111 = _step(("CO", "Cc1ccc(cc1)S(=O)(=O)Cl"), ("Cc1ccc(cc1)S(=O)(=O)OC", "Cl"))  # MeOH + TsCl -> MeOTs + HCl
STEP_115 = _step(("CC(=O)OCC", "CC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CCO"))              # 2 EtOAc -> EAA + EtOH


def snapshot() -> dict:
    """Raw recognition facts for the current tree."""
    return {
        "recognizer_count": len(_RECOGNIZERS),
        "recognize_111_sulfonate": recognize_reaction_type(STEP_111),
        "recognize_115_claisen": recognize_reaction_type(STEP_115),
    }


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2, sort_keys=True))
