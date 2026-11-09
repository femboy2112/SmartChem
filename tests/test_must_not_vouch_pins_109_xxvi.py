"""Issue #109 regression guard: the reaction-TYPE oracle must NOT vouch generated-but-demoted fictions.

The compiler's capped-scission search conserves molecular FORMULA, not chemical feasibility, so it
OVER-GENERATES formula-balanced steps that are *no real reaction at all* -- the "generated-but-demoted"
over-generation class #109 is about.  The production whitelist recognizer
(:func:`~smartchem.experiment.reaction_type_oracle.recognize_reaction_type_outcome`) is the demoter that
sinks them: a step VOUCHES (``.is_match is True``) only when it POSITIVELY matches a known reaction class;
otherwise it is fail-closed demoted as "unrecognized reaction type" (``.is_match is False``) -- honest
non-recognition, NOT a claim of "proven fake".

These pins are the no-false-VOUCH cardinal, adversarial side.  Each fiction LOCALLY resembles a registered
class (a fake esterification / etherification / amidation / N-alkylation whose superficial shape -- two
reactants, water expelled -- matches a real condensation) but is really an alkyl GLUING that mints a new C-C
bond and calls the departing atoms "water", the canonical #109 non-reaction
``isopropanol + ethyl acetate -> isopentyl acetate + water`` among them.  Every fiction is formula-balanced
(the :class:`~smartchem.experiment.step.ExperimentStep` constructor refuses a non-conserving step, so a fiction
that did not balance would never reach the recognizer at all) and VERIFIED to demote on this revision.

GREEN today.  A future recognizer that starts VOUCHING any pinned fiction is a soundness regression (a
false-VOUCH on a generated non-reaction, exactly #109) -- the pin flips RED and names the escape.  The
positive controls below are the anti-vacuity half: without a genuine reaction the oracle DOES vouch, this
whole file would still pass if the oracle were broken-closed (always-``False``), and the must-not-vouch pins
would mean nothing.  Keep both halves.
"""
from __future__ import annotations

import pytest

from smartchem.experiment.reaction_type_oracle import recognize_reaction_type_outcome
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles


def _step(target_smi: str, reactant_smis: tuple[str, ...], product_smis: tuple[str, ...]) -> ExperimentStep:
    """Build a conserving step from SMILES, mirroring the existing recognizer tests exactly.

    The constructor re-derives conservation by an independent path (it builds a real ``Reaction``), so a
    SMILES typo that unbalanced the equation would raise here rather than silently pin a different step --
    the certificate is the scalpel's own sterility check.
    """
    target = parse_smiles(target_smi)
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    products = tuple(parse_smiles(s) for s in product_smis)
    return ExperimentStep.assembling(target, reactants, products, reagents=())


# ======================================================================================================
# MUST-NOT-VOUCH -- near-neighbour fictions: formula-balanced alkyl C-C gluing masquerading as a
# condensation.  Each VERIFIED to return ``.is_match is False`` on this revision before being pinned.
# ======================================================================================================
_MUST_NOT_VOUCH = [
    # The canonical #109 non-reaction (named in the oracle module docstring): the ethyl of ethyl acetate is
    # extended by an isopropyl via a NEW C-C bond, the isopropanol's -OH leaving as "water".  Superficially a
    # transesterification/esterification; chemically a C-C glue no acyl recognizer can re-derive.
    ("#109 canonical: isopropanol + ethyl acetate -> isopentyl acetate + water",
     "CC(=O)OCCC(C)C", ("CC(C)O", "CC(=O)OCC"), ("CC(=O)OCCC(C)C", "O")),
    # Fake dehydrative etherification: two alcohols, water out -- but a C-C bond forms (propanol), not the
    # dialkyl C-O-C ether the etherification census demands.
    ("fake etherification: methanol + ethanol -> 1-propanol + water (C-C glue, no C-O-C)",
     "CCCO", ("CO", "CCO"), ("CCCO", "O")),
    # Fake Fischer esterification: a free acid + an alcohol, water out -- but the carbonyl carbon is glued to
    # the alcohol's carbon by a C-C bond, yielding a hydroxy-ketone, not the new ester carbonyl the acyl
    # census requires.
    ("fake esterification: propanoic acid + ethanol -> 4-hydroxypentan-3-one + water (C-C glue, no ester)",
     "CCC(=O)CCO", ("CCC(=O)O", "CCO"), ("CCC(=O)CCO", "O")),
    # Second fake esterification twin: acetic acid + ethanol glued C-C to 4-hydroxybutan-2-one instead of the
    # genuine ethyl acetate the positive control below makes from the SAME two reactants.
    ("fake esterification 2: acetic acid + ethanol -> 4-hydroxybutan-2-one + water (C-C glue, no ester)",
     "CC(=O)CCO", ("CC(=O)O", "CCO"), ("CC(=O)CCO", "O")),
    # Fake dehydrative N-alkylation: an amine + an alcohol, water out -- but the chain extends by a C-C bond
    # (propylamine), so no sp3 C-N bond net-forms; the N-alkylation census demotes it.
    ("fake N-alkylation: methylamine + ethanol -> propylamine + water (C-C glue, no C-N)",
     "CCCN", ("CN", "CCO"), ("CCCN", "O")),
    # Fake amidation: a free acid + an amine, water out -- but the acid carbon glues C-C to the amine's carbon
    # (an amino-ketone), minting no amide carbonyl, so the acyl census refuses it.
    ("fake amidation: propanoic acid + methylamine -> 1-aminobutan-2-one + water (C-C glue, no amide)",
     "CCC(=O)CN", ("CCC(=O)O", "CN"), ("CCC(=O)CN", "O")),
]


@pytest.mark.parametrize("label,tgt,rs,ps", _MUST_NOT_VOUCH, ids=[c[0] for c in _MUST_NOT_VOUCH])
def test_generated_fiction_must_not_vouch(label, tgt, rs, ps):
    """A formula-balanced #109 fiction must be DEMOTED (``.is_match is False``), never vouched."""
    out = recognize_reaction_type_outcome(_step(tgt, rs, ps))
    # The exact soundness claim: not a MATCH.  (An ABSTAIN and an INTERNAL_RECOGNIZER_ERROR both demote;
    # #109 is only ever violated by a spurious True here, so that is what the pin guards.)
    assert out.is_match is False, f"FALSE-VOUCHED a generated fiction (issue #109 regression): {label}"


# ======================================================================================================
# POSITIVE CONTROLS -- genuine reactions of REGISTERED classes.  Anti-vacuity: these are what prove the
# oracle still vouches real chemistry, so the must-not-vouch pins above mean "demotes a fiction", not
# "demotes everything (broken-closed)".
# ======================================================================================================
_POSITIVE_CONTROLS = [
    # A genuine free-acid dehydrative esterification -- the acyl-condensation class.  Note it shares its two
    # reactants with "fake esterification 2" above and is decided OPPOSITELY: same inputs, real ester vs C-C glue.
    ("acyl condensation: acetic acid + ethanol -> ethyl acetate + water",
     "CC(=O)OCC", ("CC(=O)O", "CCO"), ("CC(=O)OCC", "O")),
    # A genuine dehydrative etherification -- the etherification class.
    ("etherification: ethanol + ethanol -> diethyl ether + water",
     "CCOCC", ("CCO", "CCO"), ("CCOCC", "O")),
]


@pytest.mark.parametrize("label,tgt,rs,ps", _POSITIVE_CONTROLS, ids=[c[0] for c in _POSITIVE_CONTROLS])
def test_genuine_reaction_still_vouches(label, tgt, rs, ps):
    """Anti-vacuity: a real reaction of a registered class VOUCHES (``.is_match is True``)."""
    out = recognize_reaction_type_outcome(_step(tgt, rs, ps))
    assert out.is_match is True, f"a genuine registered-class reaction failed to vouch (oracle broken-closed?): {label}"
