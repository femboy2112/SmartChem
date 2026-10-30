"""Regression lock for CLAISEN-CONDENSATION-115 (Round IV Wave E2, issue #115).

The 1,3-dicarbonyl / beta-ketoester Claisen condensation (ester/ketone + ester/carbonate -> 1,3-dicarbonyl +
alcohol) is a recognized class -- the 20th.  NOT the Claisen [3,3] sigmatropic rearrangement.

The cardinal no-false-vouch holds, PROVEN against the exact fictions #115 was filed to exclude: the
butanone = acetic acid + ethane fiction (and its ethane-coproduct / EtOH-cap variants), the orientation fakes
(aldehyde + alpha-alkoxy-ester reconstructs the beta-ketoester by a FLIPPED cap), the free-acid donor, the
no-alpha-H substrate, the amide/aldehyde flank, and the mono-ketone target.  Each negative is a mutation control:
it abstains ONLY because a specific guard fires, so re-introducing that defect (dropping the guard) flips it to a
false-vouch and fails this file.  Recognition is content-deterministic (a forged reaction centre buys nothing).

Scope is Problem A type-validity only; the stoichiometric base is Problem B / #107 (same honesty as #110).
"""
from __future__ import annotations

import dataclasses

import pytest

from smartchem.diels_alder import _DA_CENTER
from smartchem.experiment.reaction_type_oracle import _RECOGNIZERS, _claisen_condensation, recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

CLAISEN = "Claisen condensation (ester/ketone + ester/carbonate -> 1,3-dicarbonyl + alcohol)"


def _step(rs, ps):
    return ExperimentStep.assembling(parse_smiles(ps[0]), tuple(parse_smiles(x) for x in rs),
                                     tuple(parse_smiles(x) for x in ps))


def _safe(pred, step):
    try:
        return bool(pred(step))
    except Exception:
        return False


#: genuine Claisen condensations -- each MUST recognize as the Claisen class.
_POSITIVES = [
    ("2_EtOAc_to_EAA", ("CC(=O)OCC", "CC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CCO")),
    ("2_MeOAc_to_methyl_acetoacetate", ("CC(=O)OC", "CC(=O)OC"), ("CC(=O)CC(=O)OC", "CO")),
    ("acetone_EtOAc_to_acetylacetone", ("CC(C)=O", "CC(=O)OCC"), ("CC(=O)CC(C)=O", "CCO")),
    ("acetophenone_EtOAc_to_benzoylacetone", ("CC(=O)c1ccccc1", "CC(=O)OCC"), ("CC(=O)CC(=O)c1ccccc1", "CCO")),
    ("acetone_diethyl_carbonate_to_EAA", ("CC(C)=O", "CCOC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CCO")),
    ("EtOAc_diethyl_oxalate", ("CC(=O)OCC", "CCOC(=O)C(=O)OCC"), ("CCOC(=O)CC(=O)C(=O)OCC", "CCO")),
    ("EtOAc_ethyl_formate", ("CC(=O)OCC", "O=COCC"), ("O=CCC(=O)OCC", "CCO")),
    ("2_ethyl_propanoate", ("CCC(=O)OCC", "CCC(=O)OCC"), ("CCC(=O)C(C)C(=O)OCC", "CCO")),
    ("diethyl_carbonate_EtOAc_to_diethyl_malonate", ("CCOC(=O)OCC", "CC(=O)OCC"), ("CCOC(=O)CC(=O)OCC", "CCO")),
    ("crossed_MeOAc_EtOAc", ("CC(=O)OC", "CC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CO")),
]

#: fictions -- each MUST NOT recognize as Claisen.  The trailing tag names the guard whose removal would flip it.
_MUST_NOT_VOUCH = [
    ("butanone_AcOH_plus_ethane", ("CC(=O)O", "CC"), ("CCC(C)=O", "O"), "water-guard / 1,3-dicarbonyl-lock"),
    ("butanone_acetone_plus_propane", ("CC(C)=O", "CCC"), ("CCC(C)=O", "CC"), "alcohol-coproduct-gate"),
    ("butanone_EtOAc_plus_ethane_EtOH_cap", ("CC(=O)OCC", "CC"), ("CCC(C)=O", "CCO"), "1,3-dicarbonyl-lock"),
    ("free_acid_AcOH_plus_EtOAc", ("CC(=O)O", "CC(=O)OCC"), ("CC(=O)CC(=O)OCC", "O"), "water-guard"),
    ("orientation_fake_MeCHO_methoxyacetate", ("CC=O", "COCC(=O)OC"), ("CC(=O)CC(=O)OC", "CO"), "orientation-witness"),
    ("orientation_fake_MeCHO_ethoxyacetate", ("CC=O", "CCOCC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CCO"), "orientation-witness"),
    ("no_alpha_H_isobutyrate", ("CC(C)C(=O)OCC", "CC(C)C(=O)OCC"), ("CC(C)C(=O)C(C)(C)C(=O)OCC", "CCO"), "alpha-H-guard"),
    ("mono_ketone_2_pentanone", ("CC(=O)OCC", "CCC"), ("CCCC(C)=O", "CCO"), "1,3-dicarbonyl-lock"),
    ("ketone_plus_ketone_methane_coproduct", ("CC(C)=O", "CC(C)=O"), ("CC(=O)CC(C)=O", "C"), "alcohol-coproduct-gate"),
    ("beta_keto_acid_ethyl_H_carbonate", ("CC(C)=O", "CCOC(=O)O"), ("CC(=O)CC(=O)OCC", "O"), "water-guard"),
    ("amide_flank_N_methylacetamide", ("CC(=O)OCC", "CC(=O)NC"), ("CC(=O)CC(=O)NC", "CCO"), "flank-type-whitelist"),
]


def test_oracle_now_has_twentyone_recognizers():
    assert len(_RECOGNIZERS) == 22  # + #112 SN2 (21st) + #119 imine condensation (22nd)


@pytest.mark.parametrize("name,rs,ps", _POSITIVES, ids=[c[0] for c in _POSITIVES])
def test_genuine_claisen_is_recognized(name, rs, ps):
    assert _claisen_condensation(_step(rs, ps)) is True
    assert recognize_reaction_type(_step(rs, ps)) == CLAISEN


@pytest.mark.parametrize("name,rs,ps,guard", _MUST_NOT_VOUCH, ids=[c[0] for c in _MUST_NOT_VOUCH])
def test_fiction_does_not_false_vouch_as_claisen(name, rs, ps, guard):
    step = _step(rs, ps)
    assert _claisen_condensation(step) is False, f"{name} FALSE-VOUCHED (guard {guard})"
    klass = recognize_reaction_type(step)
    assert klass is None or CLAISEN not in str(klass), f"{name} recognized as {klass!r}"


def test_exactly_one_recognizer_fires_on_a_claisen_step():
    step = _step(("CC(=O)OCC", "CC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CCO"))
    fired = [name for name, pred in _RECOGNIZERS if _safe(pred, step)]
    assert fired == [CLAISEN], fired


def test_claisen_does_not_poach_neighbouring_classes():
    # esterification (water coproduct), activated acyl transfer (acid coproduct), Diels-Alder (2->1 shape):
    # none is a Claisen condensation and the recognizer must abstain on each.
    esterification = _step(("CCO", "CC(=O)O"), ("CC(=O)OCC", "O"))
    activated_acyl = _step(("CC(=O)OC(C)=O", "CO"), ("CC(=O)OC", "CC(=O)O"))   # Ac2O + MeOH -> MeOAc + AcOH
    diels_alder = _step(("C=CC=C", "C=C"), ("C1CCC=CC1",))                       # butadiene + ethene -> cyclohexene
    for lab, step in (("esterification", esterification), ("activated acyl", activated_acyl),
                      ("diels-alder", diels_alder)):
        assert _claisen_condensation(step) is False, f"Claisen poached {lab}"


def test_content_deterministic_forged_centre_buys_nothing():
    # a genuine Claisen wearing a BORROWED Diels-Alder centre still vouches (the centre is never read) ...
    genuine = dataclasses.replace(_step(("CC(=O)OCC", "CC(=O)OCC"), ("CC(=O)CC(=O)OCC", "CCO")),
                                  reaction_center=_DA_CENTER)
    assert recognize_reaction_type(genuine) == CLAISEN
    # ... and a butanone fiction wearing any centre stays unrecognized (no forged annotation mints a vouch).
    fiction = dataclasses.replace(_step(("CC(=O)O", "CC"), ("CCC(C)=O", "O")), reaction_center=_DA_CENTER)
    assert CLAISEN not in str(recognize_reaction_type(fiction))
