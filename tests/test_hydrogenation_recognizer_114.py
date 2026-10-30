"""#114 -- the hydrogenation (partial bond-order edit) reaction-TYPE recognizer.

The ``BondOrderEditProvider`` GENERATOR and the opt-in ``bond-order-edit-v1`` profile shipped in 1.1
(tests/test_bond_order_edit_profile_114.py); this is the RECOGNITION side. ``_hydrogenation`` re-derives a
step ``precursor + H2 -> saturated`` via the family's OWN generator (``bond_order_edits``) and vouches ONLY a
genuine single bond-order edit -- sound by construction (the ``BondOrderEdit`` constructor is a conservation +
W1-descent certificate), content-deterministic (NEVER reads ``step.reaction_center``), fail-closed otherwise.

Proof obligations pinned here: positive, negative, null, mutation, no-false-VOUCH corpus, cross-poach,
conjugated-ring deferral, conservation, and fresh holdouts.
"""
from __future__ import annotations

import pytest

from smartchem.experiment.reaction_type_oracle import (
    _RECOGNIZERS,
    _hydrogenation,
    recognize_reaction_type,
    recognize_reaction_type_outcome,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

H2 = parse_smiles("[H][H]")


def _step(target_smi: str, *reactant_smis: str) -> ExperimentStep:
    target = parse_smiles(target_smi)
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    return ExperimentStep.assembling(target, reactants, (target,), reagents=())


def _hydro_step(target_smi: str, precursor_smi: str) -> ExperimentStep:
    return _step(target_smi, precursor_smi, "[H][H]")


# -- positives: genuine single bond-order reductions (one unsaturation + H2 -> saturated) -------------------
_POSITIVES = [
    ("C=C -> ethane",            "CC",        "C=C"),
    ("propene -> propane",       "CCC",       "CC=C"),
    ("2-butene -> butane",       "CCCC",      "CC=CC"),
    ("acetaldehyde(C=O)->EtOH",  "CCO",       "CC=O"),
    ("cyclohexene->cyclohexane", "C1CCCCC1",  "C1=CCCCC1"),   # isolated RING double: kept
]


@pytest.mark.parametrize("label,target,precursor", _POSITIVES, ids=[c[0] for c in _POSITIVES])
def test_genuine_hydrogenation_is_recognized(label, target, precursor):
    name = recognize_reaction_type(_hydro_step(target, precursor))
    assert name is not None and "hydrogenation" in name, f"{label}: recognized as {name!r}"


# -- conjugated-ring DEFERRAL: aromatic / polyene-ring reductions abstain (honest coverage loss) -----------
_DEFERRED = [
    ("benzene -> 1,3-cyclohexadiene", "C1=CC=CCC1", "c1ccccc1"),
    ("1,3-chd -> cyclohexene",        "C1=CCCCC1",  "C1=CC=CCC1"),
]


@pytest.mark.parametrize("label,target,precursor", _DEFERRED, ids=[c[0] for c in _DEFERRED])
def test_conjugated_ring_reduction_is_deferred(label, target, precursor):
    out = recognize_reaction_type_outcome(_hydro_step(target, precursor))
    assert not out.is_match, f"{label}: must DEFER an aromatic-ring reduction, got {out.reaction_class!r}"
    assert not out.is_internal_error, f"{label}: clean abstain, not an instrument error ({out.faults})"


# -- no-false-VOUCH: a conserved H2-addition that is NOT a bond-order edit must abstain --------------------
def test_ring_opening_hydrogenolysis_is_not_this_family():
    # cyclopropane + H2 -> propane conserves (C3H6 + H2 = C3H8) but is a RING-OPENING hydrogenolysis, not a
    # bond-order reduction: bond_order_edits(propane) emits propene, never cyclopropane, so the recognizer abstains.
    out = recognize_reaction_type_outcome(_hydro_step("CCC", "C1CC1"))
    assert not out.is_match, f"ring-opening must NOT vouch as hydrogenation (got {out.reaction_class!r})"
    assert not out.is_internal_error


# resonance_identity INJECTIVITY (dalembert's reinforcement): the no-skeletal-rearrangement guarantee
# rests entirely on resonance_identity never merging two distinct constitutions. Each decoy below conserves
# with H2 to the target but is a DIFFERENT constitution (a carbocycle / an epoxide), so it is NOT a single
# bond-order reduction and MUST abstain, while the genuine carrier vouches -- pinning the one load-bearing
# assumption the recognizer silently trusts.
_SAME_FORMULA_DECOYS = [
    ("propane: propene(genuine) vs cyclopropane(decoy)", "CCC",  "CC=C",  "C1CC1"),
    ("butane: 1-butene(genuine) vs cyclobutane(decoy)",  "CCCC", "C=CCC", "C1CCC1"),
    ("ethanol: acetaldehyde(genuine) vs oxirane(decoy)", "CCO",  "CC=O",  "C1CO1"),
]


@pytest.mark.parametrize("label,target,genuine,decoy", _SAME_FORMULA_DECOYS, ids=[c[0] for c in _SAME_FORMULA_DECOYS])
def test_same_formula_decoy_does_not_collide_with_a_genuine_carrier(label, target, genuine, decoy):
    assert "hydrogenation" in (recognize_reaction_type(_hydro_step(target, genuine)) or ""), f"{label}: genuine must vouch"
    out = recognize_reaction_type_outcome(_hydro_step(target, decoy))
    assert not out.is_match, f"{label}: same-formula decoy must NOT vouch (resonance_identity injectivity)"
    assert not out.is_internal_error


def test_a_step_without_dihydrogen_is_not_a_hydrogenation():
    # an esterification (AcOH + EtOH -> ethyl acetate + water) is 2->2 with water, no H2 reactant.
    step = ExperimentStep.assembling(
        parse_smiles("CCOC(C)=O"),
        (parse_smiles("CC(=O)O"), parse_smiles("CCO")),
        (parse_smiles("CCOC(C)=O"), parse_smiles("O")),
        reagents=(),
    )
    assert _hydrogenation(step) is False


# -- cross-poach: exactly one recognizer fires on a hydrogenation; hydrogenation fires on nothing else -----
def test_exactly_one_recognizer_fires_on_a_hydrogenation_step():
    step = _hydro_step("CC", "C=C")
    fired = []
    for name, pred in _RECOGNIZERS:
        try:
            if pred(step):
                fired.append(name)
        except Exception:
            pass
    assert len(fired) == 1 and "hydrogenation" in fired[0], f"fired: {fired}"


def test_hydrogenation_does_not_fire_on_other_families():
    # a genuine Diels-Alder step (butadiene + ethene -> cyclohexene) and an esterification: neither is 2->1 with H2.
    da = ExperimentStep.assembling(
        parse_smiles("C1=CCCCC1"),
        (parse_smiles("C=CC=C"), parse_smiles("C=C")),
        (parse_smiles("C1=CCCCC1"),),
        reagents=(),
    )
    ester = ExperimentStep.assembling(
        parse_smiles("CCOC(C)=O"),
        (parse_smiles("CC(=O)O"), parse_smiles("CCO")),
        (parse_smiles("CCOC(C)=O"), parse_smiles("O")),
        reagents=(),
    )
    assert _hydrogenation(da) is False
    assert _hydrogenation(ester) is False


# -- content-determinism: the recognizer is a pure function of the molecules, NEVER the stored centre -------
def test_recognizer_never_reads_the_reaction_centre():
    # ISSUE-126/132 discipline, enforced by TEST not just convention: a future edit that read step.reaction_center
    # for a vouch would reopen the forged-centre hole. co_names holds the attribute/global names the BYTECODE
    # references (prose in the docstring is NOT there), so this bites on a real access, never on a mention.
    names = set(_hydrogenation.__code__.co_names)
    assert "reaction_center" not in names, f"the hydrogenation recognizer must not read step.reaction_center ({names})"


def test_null_control_centreless_step_is_recognized():
    # a step built with NO reaction_center is recognized purely from its molecules.
    step = _hydro_step("CC", "C=C")
    assert getattr(step, "reaction_center", None) is None
    assert "hydrogenation" in (recognize_reaction_type(step) or "")


# -- conservation: a vouched step balances atom-for-atom (ExperimentStep enforces it; pinned here too) ------
def test_a_recognized_step_is_mass_conserved():
    from collections import Counter

    step = _hydro_step("CCO", "CC=O")  # acetaldehyde + H2 -> ethanol
    assert "hydrogenation" in (recognize_reaction_type(step) or "")
    lhs = Counter(a for m in step.reactants for a in m.atoms)
    rhs = Counter(a for m in step.products for a in m.atoms)
    assert lhs == rhs


# -- fresh holdouts not used to design the rule -----------------------------------------------------------
def test_holdout_acyclic_positive():
    assert "hydrogenation" in (recognize_reaction_type(_hydro_step("CCCCC", "CCCC=C")) or "")   # 1-pentene -> pentane


def test_holdout_carbonyl_positive():
    assert "hydrogenation" in (recognize_reaction_type(_hydro_step("CCC=O", "C=CC=O")) or "")   # acrolein -> propanal (C=C)


def test_holdout_arene_pendant_is_deferred():
    # styrene -> ethylbenzene reduces the vinyl, but styrene is cyclic with >=2 multiple bonds (aromatic ring +
    # vinyl), so the conservative conjugated-ring proxy DEFERS it (honest coverage loss, safe-direction).
    out = recognize_reaction_type_outcome(_hydro_step("CCc1ccccc1", "C=Cc1ccccc1"))
    assert not out.is_match and not out.is_internal_error
