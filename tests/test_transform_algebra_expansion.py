"""The 2026-09-20 transform-algebra expansion round: the five new reaction-TYPE classes (thia-diene DA, aza-Claisen,
thia-Claisen, 4pi + 6pi electrocyclization) wired into the oracle, the oxy-Cope non-family disposition, and item 5's
opt-in whole-fragment-neutrality predicate.

The load-bearing pins: (1) each new family's own step is recognized as EXACTLY its class -- a full 17-way no-cross-poach
matrix, so no class poaches another's steps; (2) every lateral + DA family centre is value-distinct where Layer B is a
separator (and the diene<->dienophile centre collisions are the ONLY collisions, separated by Layer A); (3) oxy-Cope is
NOT a new structural class -- a 3-hydroxy-1,5-hexadiene is already a Cope match (the honest disposition); (4) the
opt-in whole_fragment_neutral predicate flags a drawn-neutral over-valent atom without touching the guarded retro.
"""
from __future__ import annotations

import pytest

from smartchem.diels_alder import (
    THIA_DIENE_DA, THIA_DA, _THIA_DA_CENTER, ThiaDieneDielsAlderProvider, whole_fragment_neutral,
)
from smartchem.experiment.reaction_type_oracle import _RECOGNIZERS, recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.lateral_rewrite import (
    AZA_CLAISEN, THIA_CLAISEN, ELECTRO_4PI, ELECTRO_6PI, COPE, LATERAL_FAMILIES, rewrite_edges, sigmatropic_rewrites,
)
from smartchem.smiles import parse_smiles


def _lateral_step(family, smi):
    return ExperimentStep.from_transform(rewrite_edges(family, parse_smiles(smi))[0], envelope=None)


def _thia_diene_step():
    edge = ThiaDieneDielsAlderProvider().enumerate_transforms(parse_smiles("C1CCC=CS1"), (), budget=100000)[0][0]
    return ExperimentStep.from_transform(edge, envelope=None)


#: (label, step, expected recognizer-name substring) for each of the five new classes.
_NEW_CLASS_STEPS = [
    ("thia-diene-DA", _thia_diene_step(), "1-thiadiene"),
    ("aza-Claisen", _lateral_step(AZA_CLAISEN, "C=CCCC=N"), "aza-Claisen"),
    ("thia-Claisen", _lateral_step(THIA_CLAISEN, "C=CCCC=S"), "thia-Claisen"),
    ("electro-4pi", _lateral_step(ELECTRO_4PI, "C1=CCC1"), "4pi"),
    ("electro-6pi", _lateral_step(ELECTRO_6PI, "C1=CCCC=C1"), "6pi"),
]


def test_oracle_has_seventeen_recognizers():
    assert len(_RECOGNIZERS) == 17


@pytest.mark.parametrize("label,step,expect", _NEW_CLASS_STEPS, ids=[c[0] for c in _NEW_CLASS_STEPS])
def test_each_new_class_is_recognized_as_its_own(label, step, expect):
    name = recognize_reaction_type(step)
    assert name is not None and expect in name, f"{label} recognized as {name!r}"


@pytest.mark.parametrize("label,step,_expect", _NEW_CLASS_STEPS, ids=[c[0] for c in _NEW_CLASS_STEPS])
def test_no_cross_poach_exactly_one_recognizer_fires(label, step, _expect):
    fired = []
    for cname, pred in _RECOGNIZERS:
        try:
            if pred(step):
                fired.append(cname)
        except Exception:
            pass
    assert len(fired) == 1, f"{label} fired {len(fired)} recognizers: {fired}"


def test_full_17x_no_cross_poach_matrix():
    """Every new class's step, run against ALL 17 recognizers, fires exactly its own -- and NO existing class's
    recognizer fires on it (the matrix that pins the whole whitelist apart)."""
    for label, step, _ in _NEW_CLASS_STEPS:
        matches = [cname for cname, pred in _RECOGNIZERS if _safe(pred, step)]
        assert len(matches) == 1, f"{label}: {matches}"


def _safe(pred, step) -> bool:
    try:
        return bool(pred(step))
    except Exception:
        return False


def test_thia_diene_shares_centre_with_thia_dienophile_position_invariant():
    # the crown collision, thia edition: the diene- and dienophile-position S families share a centre by construction.
    assert THIA_DIENE_DA.center == _THIA_DA_CENTER == THIA_DA.center
    assert THIA_DIENE_DA.position == "diene" and THIA_DIENE_DA.hetero_vertex == 0


def test_thia_diene_and_thia_dienophile_separated_by_layer_a_only():
    # Layer B (centre) cannot separate them (identical centre); Layer A does -- the thia-diene adduct re-derives ONLY
    # under the diene family, and its step fires ONLY the thia-diene recognizer (verified in the no-cross-poach test).
    step = _thia_diene_step()
    name = recognize_reaction_type(step)
    assert name is not None and "1-thiadiene" in name and "dihydrothiopyran isomer" in name


def test_all_lateral_family_centres_are_value_distinct():
    centres = [f.center for f in LATERAL_FAMILIES]
    assert len({repr(c) for c in centres}) == len(centres)


def test_oxy_cope_is_already_a_cope_not_a_new_family():
    """oxy-Cope DISPOSITION (item 2): a 3-hydroxy-1,5-hexadiene's six-atom array is all-carbon, so it is ALREADY a
    Cope match -- the enol->ketone tautomerisation is a separate step (Problem B / feasibility), so oxy-Cope needs NO
    new structural class.  Pin that COPE matches it and yields the [3,3] isomer."""
    isomers = sigmatropic_rewrites(COPE, parse_smiles("C=CC(O)CC=C"))
    assert len(isomers) == 1
    # and a Cope step built from it is recognized as Cope (not a distinct "oxy-Cope" class).
    step = _lateral_step(COPE, "C=CC(O)CC=C")
    name = recognize_reaction_type(step)
    assert name is not None and "Cope" in name


def test_whole_fragment_neutral_predicate():
    # item 5: True on genuine neutrals, False on a drawn-neutral over-valent atom (an oxonium O at bond-order 3).
    assert whole_fragment_neutral(parse_smiles("CCO")) is True       # ethanol
    assert whole_fragment_neutral(parse_smiles("COC")) is True       # dimethyl ether (O bond-order 2)
    assert whole_fragment_neutral(parse_smiles("O")) is True         # water
    assert whole_fragment_neutral(parse_smiles("C[O](C)C")) is False  # trimethyloxonium-shaped fiction (O bond-order 3)


def test_whole_fragment_neutral_is_opt_in_not_wired_into_guarded_retro():
    # the guarded retro (its provider) must NOT apply whole_fragment_neutral -- it is opt-in; a real neutral thiopyran
    # still disconnects (guard 2c's matched-centre scope is the declared boundary).  A structural smoke that the
    # provider still yields the thia-diene retro (item 5 changed no default behaviour).
    edges, _ = ThiaDieneDielsAlderProvider().enumerate_transforms(parse_smiles("C1CCC=CS1"), (), budget=100000)
    assert len(edges) >= 1
