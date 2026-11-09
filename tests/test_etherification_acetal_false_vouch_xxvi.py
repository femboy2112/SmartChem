"""Regression: the etherification recognizer must NOT false-VOUCH acetalization (issue #109 family).

OPERATION XXVI, WAVE 3. A directed chemical adversary (d'Alembert) broke the reaction-type oracle's "0
false-VOUCH" cardinal: `reaction_type_oracle.recognize_reaction_type_outcome` VOUCHED
``hemiacetal + alcohol -> acetal + water`` as an *etherification*.

Why that was a false-VOUCH. Dimethoxymethane ``CH2(OMe)2`` is formaldehyde's dimethyl ACETAL: its central carbon
bears TWO C-O bonds -- it sits at the carbonyl (aldehyde) oxidation level, a MASKED CARBONYL. The reaction
``hemiacetal + alcohol -> acetal + water`` is textbook acetalization (an oxocarbenium mechanism), NOT the
dehydrative Williamson coupling of two independent alcohols ``R-OH + R'-OH -> R-O-R'`` the recognizer claims. The
root cause: the ether census `_ether_oxygen_counts` counted an acetal O (whose carbon bears a second O) as a
"dialkyl ether", and the `("O",)` single-cut re-derivation cannot see the masked carbonyl because exactly one C-O
bond forms. The N-alkylation recognizer had already closed the analogous donor-side hole
(`_alkyl_carbinol_alcohol_count`); the ether census never got the medicine. The fix transports the same
masked-carbonyl discipline to the ether oxygen (`_carbon_bears_other_heteroatom`): an O whose carbon bears a
second heteroatom is an acetal/orthoester O, not a dialkyl ether, so it no longer counts.

These pins are RED before the fix (they FALSE-VOUCHED) and GREEN after. The positive controls guarantee the fix
removed the acetal false-VOUCH WITHOUT a coverage regression: genuine etherifications still VOUCH.
"""
from __future__ import annotations

import pytest

from smartchem.experiment.reaction_type_oracle import recognize_reaction_type_outcome
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles


def _step(target_smi, reactant_smis, product_smis):
    return ExperimentStep.assembling(
        parse_smiles(target_smi),
        tuple(parse_smiles(s) for s in reactant_smis),
        tuple(parse_smiles(s) for s in product_smis),
        reagents=(),
    )


# Masked-carbonyl condensations the etherification recognizer FALSE-VOUCHED before the fix. Each is formula-balanced
# (the ExperimentStep constructor re-derives conservation and would raise otherwise) and VERIFIED to demote after.
_MUST_NOT_VOUCH_AS_ETHER = [
    # The d'Alembert kill: formaldehyde hemiacetal + methanol -> formaldehyde dimethyl ACETAL + water.
    ("acetalization: methoxymethanol + methanol -> dimethoxymethane + water",
     "COCOC", ("COCO", "CO"), ("COCOC", "O")),
    # Second independent instance: acetaldehyde hemiacetal -> dimethyl acetal.
    ("acetalization: 1-methoxyethanol + methanol -> 1,1-dimethoxyethane + water",
     "CC(OC)OC", ("CC(O)OC", "CO"), ("CC(OC)OC", "O")),
    # Orthoester: the carbon bears THREE C-O bonds -- an even more masked carbonyl.
    ("orthoesterification: dimethoxymethanol + methanol -> trimethyl orthoformate + water",
     "COC(OC)OC", ("COC(O)OC", "CO"), ("COC(OC)OC", "O")),
]


@pytest.mark.parametrize("label,tgt,rs,ps", _MUST_NOT_VOUCH_AS_ETHER, ids=[c[0] for c in _MUST_NOT_VOUCH_AS_ETHER])
def test_acetalization_must_not_vouch_as_etherification(label, tgt, rs, ps):
    """A masked-carbonyl acetal/orthoester condensation must be DEMOTED, never vouched as an etherification."""
    out = recognize_reaction_type_outcome(_step(tgt, rs, ps))
    assert out.is_match is False, f"FALSE-VOUCHED acetalization as etherification (issue #109 regression): {label}"


# Anti-regression: genuine dehydrative etherifications must STILL vouch -- the fix excludes acetals, not real ethers.
_GENUINE_ETHERIFICATIONS = [
    ("diethyl ether: ethanol + ethanol -> diethyl ether + water",
     "CCOCC", ("CCO", "CCO"), ("CCOCC", "O")),
    ("mixed ether: methanol + ethanol -> methoxyethane + water",
     "COCC", ("CO", "CCO"), ("COCC", "O")),
    # The non-locality case the span-local recognizer is meant to keep: a reactant CONTAINS an unrelated ether.
    ("ether with an unrelated ether in a reactant: methanol + 2-methoxyethanol -> 1,2-dimethoxyethane + water",
     "COCCOC", ("CO", "COCCO"), ("COCCOC", "O")),
]


@pytest.mark.parametrize("label,tgt,rs,ps", _GENUINE_ETHERIFICATIONS, ids=[c[0] for c in _GENUINE_ETHERIFICATIONS])
def test_genuine_etherification_still_vouches(label, tgt, rs, ps):
    """Anti-regression: a real dialkyl etherification VOUCHES; the masked-carbonyl guard is specific to acetals."""
    out = recognize_reaction_type_outcome(_step(tgt, rs, ps))
    assert out.is_match is True, f"a genuine etherification failed to vouch after the acetal-guard fix: {label}"
