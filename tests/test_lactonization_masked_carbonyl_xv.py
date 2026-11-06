"""OPERATION XV P8 -- regression for the masked-carbonyl false-VOUCH d'Alembert proved against head 98a31f6.

THE KILL (now closed): the 25th-class lactonization recognizer vouched a MASKED-CARBONYL carbinol -- a hemiacetal /
hemiketal / gem-diol -OH -- as a genuine ``hydroxy acid -> lactone + water``.  The shared witness ``_hydroxyl_sites``
excluded only a LITERAL carbonyl carbon, never a carbinol carbon bearing a SECOND heteroatom (the masked carbonyl).
That is a Problem-A false-VOUCH (the cardinal coverage-loss-never-false-VOUCH rule, violated), reachable from BOTH the
generator and the recognizer through their common ``_lactonizes_to`` witness.  The fix adds the alkyl-carbinol
discipline to the one shared helper, mirroring ``feasibility._alkyl_carbinol_alcohol_count`` on the N-alkylation side,
so a single guard closes emission AND vouch.  These cases must now ABSTAIN; a genuine hydroxy acid must still vouch
(honest coverage loss, not a regression).
"""
from __future__ import annotations

import pytest

from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.intramolecular_condensation import LACTONIZATION_CLASS
from smartchem.smiles import parse_smiles


def _handbuilt_lactonization(lactone_smiles, precursor_smiles):
    lactone = parse_smiles(lactone_smiles)
    precursor = parse_smiles(precursor_smiles)
    return ExperimentStep.assembling(lactone, (precursor,), (lactone, parse_smiles("O")), reagents=())


@pytest.mark.parametrize("lactone,precursor,kind", [
    # Case B (dalembert): 5-methoxyoxolan-2-one <- 4-hydroxy-4-methoxybutanoic acid.  C5H10O4 -> C5H8O3 + H2O.
    # The carbinol carbon bears -OH AND -OCH3: a HEMIACETAL, the masked form of an aldehyde-acid, not a hydroxy acid.
    ("COC1CCC(=O)O1", "COC(O)CCC(=O)O", "hemiacetal"),
    # Case A (dalembert): 5-hydroxyoxolan-2-one <- 4,4-dihydroxybutanoic acid.  C4H8O4 -> C4H6O3 + H2O.
    # The carbinol carbon bears two -OH: a GEM-DIOL, the hydrate of the same aldehyde-acid.
    ("OC1CCC(=O)O1", "OC(O)CCC(=O)O", "gem-diol"),
])
def test_masked_carbonyl_carbinol_is_not_vouched_as_lactonization(lactone, precursor, kind):
    step = _handbuilt_lactonization(lactone, precursor)
    # the step is mass-conserving (ExperimentStep.assembling enforces it) -- it only FAILS the chemistry, which is
    # exactly what must now be caught: a masked carbonyl is not a hydroxy-acid alcohol.
    assert recognize_reaction_type(step) != LACTONIZATION_CLASS


def test_genuine_hydroxy_acid_still_vouches_after_the_guard():
    # the positive control: a real alcohol carbinol (no second heteroatom) is unaffected -- honest coverage loss only.
    step = _handbuilt_lactonization("O=C1CCCO1", "OCCCC(=O)O")   # gamma-butyrolactone <- 4-hydroxybutanoic acid
    assert recognize_reaction_type(step) == LACTONIZATION_CLASS


def test_a_benzylic_carbinol_is_not_collateral_damage():
    # the guard excludes a SECOND heteroatom on the carbinol carbon, NOT a carbinol whose other neighbours are
    # aromatic/unsaturated carbons.  A benzylic -CH2OH (carbinol carbon: ring-C + O + 2H, no second heteroatom) must
    # still vouch: 2-(hydroxymethyl)benzoic acid -> phthalide (isobenzofuran-1(3H)-one) + water, a classic lactonisation.
    step = _handbuilt_lactonization("O=C1OCc2ccccc21", "OCc1ccccc1C(=O)O")
    assert recognize_reaction_type(step) == LACTONIZATION_CLASS
