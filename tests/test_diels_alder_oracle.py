"""DIELS-ALDER-ORACLE-01: promote the DA family into the production reaction-type oracle (4th active class).

Acceptance pins for the ``_diels_alder`` recognizer: a genuine DA synthesis step is now VOUCHED (so a DA route
stops being demoted as "unrecognized" -- the promotion payoff), while the soundness invariant holds -- Layer A
(the family's own re-derivation) refuses a mass-balancing non-DA EVEN WITH a spoofed centre, Layer C blocks a
centre-less step, and the recognizer does not poach the dehydrative classes.  The adversarial gate
(evil-morty/dalembert) runs SEPARATELY per the meta-lesson.  Design: docs/research/RULE_CALCULUS_DIELS_ALDER_FAMILY_v0.1.md.
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem.diels_alder import (
    _ALKYNE_DA_CENTER, _DA_CENTER, _FORWARD, AZA_DA, OXA_DA, AlkyneDielsAlderProvider, AzaDielsAlderProvider,
    DielsAlderProvider, OxaDielsAlderProvider, _synthesis_center,
)
from smartchem.experiment.reaction_type_oracle import (
    _alkyne_diels_alder, _aza_diels_alder, _diels_alder, _oxa_diels_alder, recognize_reaction_type,
    route_reaction_type_blockers,
)
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import CappedScissionProvider, TransformProviderRegistry

_DA_LABEL = "Diels-Alder [4+2] cycloaddition (all-carbon diene + alkene dienophile -> cyclohexene adduct)"
_ALKYNE_DA_LABEL = "Diels-Alder [4+2] cycloaddition (all-carbon diene + alkyne dienophile -> 1,4-cyclohexadiene)"


def _alkyne_da_synthesis_step() -> ExperimentStep:
    edge = AlkyneDielsAlderProvider().enumerate_transforms(parse_smiles("C1=CCC=CC1"), (), budget=100000)[0][0]
    return ExperimentStep.from_transform(edge, envelope=None)


def _da_synthesis_step() -> ExperimentStep:
    edge = DielsAlderProvider().enumerate_transforms(parse_smiles("C1CC=CCC1"), (), budget=100000)[0][0]
    return ExperimentStep.from_transform(edge, envelope=None)


# --- the edge/step now surfaces the family reaction centre ---

def test_da_step_carries_the_family_reaction_center():
    assert _da_synthesis_step().reaction_center == _DA_CENTER


# --- a genuine DA synthesis step is now VOUCHED (the promotion payoff) ---

def test_da_synthesis_step_is_vouched_as_diels_alder():
    step = _da_synthesis_step()
    assert _diels_alder(step) is True
    assert recognize_reaction_type(step) == _DA_LABEL


def test_a_da_route_is_no_longer_fiction_blocked():
    chx, buta, eth = parse_smiles("C1CC=CCC1"), parse_smiles("C=CC=C"), parse_smiles("C=C")
    reg = TransformProviderRegistry((CappedScissionProvider(), DielsAlderProvider()))
    res = search_routes(chx, reagents=(), available=(buta, eth), registry=reg, max_depth=2)
    assert len(res.routes) == 1
    # before the recognizer the DA step was demoted as "unrecognized reaction type"; now the route is clean.
    assert route_reaction_type_blockers(res.routes[0]) == ()


# --- soundness: Layer A (family re-derivation) is the gate, not the self-reported centre ---

def test_layer_a_refuses_a_mass_balancing_non_da_even_with_a_spoofed_center():
    # ethylene + butadiene -> 1,5-hexadiene BALANCES mass (C2H4 + C4H6 = C6H10) but is NOT a [4+2] (the product is
    # acyclic).  Handed the DA centre adversarially, Layer A's independent re-derivation still refuses it.
    spoofed = SimpleNamespace(
        reactants=(parse_smiles("C=C"), parse_smiles("C=CC=C")),
        products=(parse_smiles("C=CCCC=C"),),   # 1,5-hexadiene, not the cyclohexene adduct
        reaction_center=_DA_CENTER,
    )
    assert _diels_alder(spoofed) is False


def test_layer_c_blocks_a_genuine_da_shape_with_no_readable_center():
    # genuine DA molecules but the centre is absent (a nulled replay / non-scission transform) -> fail-closed.
    centreless = SimpleNamespace(
        reactants=(parse_smiles("C=C"), parse_smiles("C=CC=C")),
        products=(parse_smiles("C1CC=CCC1"),),   # cyclohexene: a genuine [4+2] adduct
        reaction_center=None,
    )
    assert _diels_alder(centreless) is False


# --- the DA recognizer does not poach the dehydrative classes ---

def test_a_dehydrative_condensation_shape_is_not_vouched_as_da():
    # esterification is 2 -> 2 (ester + water); the DA structural gate (2 -> 1) rejects it before any re-derivation.
    dehydrative = SimpleNamespace(
        reactants=(parse_smiles("CC(=O)O"), parse_smiles("CO")),
        products=(parse_smiles("CC(=O)OC"), parse_smiles("O")),
        reaction_center=_DA_CENTER,
    )
    assert _diels_alder(dehydrative) is False


# --- the reaction centre is derived from the rule (true by construction), and the scope is honest ---

def test_da_center_is_derived_from_the_forward_rule():
    # dalembert's reinforcement: the centre TRACKS the rule, it is not a hand-typed constant.
    assert _DA_CENTER == _synthesis_center(_FORWARD)
    assert _DA_CENTER.formed == (("C", "C", 1),) * 5 + (("C", "C", 2),)
    assert _DA_CENTER.broken == (("C", "C", 1),) + (("C", "C", 2),) * 3
    assert _DA_CENTER.n_components == 1


def test_alkyne_dienophile_da_is_honest_coverage_loss():
    # dalembert/evil-morty: butadiene + acetylene -> 1,3-cyclohexadiene IS a genuine all-carbon [4+2], but the
    # family rule fixes an ALKENE dienophile, so the recognizer abstains (false-UNRECOGNIZED, safe) -- never a
    # false-vouch.  Pinned so the label's honest scope (alkene dienophile only) cannot silently broaden.
    alkyne_da = SimpleNamespace(
        reactants=(parse_smiles("C=CC=C"), parse_smiles("C#C")),
        products=(parse_smiles("C1=CC=CCC1"),),   # 1,3-cyclohexadiene (two ring C=C)
        reaction_center=_DA_CENTER,
    )
    assert _diels_alder(alkyne_da) is False


# --- the alkyne-dienophile sibling family: its own genuine synthesis step is now vouched too ---

def test_alkyne_da_synthesis_step_is_vouched_as_alkyne_diels_alder():
    step = _alkyne_da_synthesis_step()
    assert _alkyne_diels_alder(step) is True
    assert recognize_reaction_type(step) == _ALKYNE_DA_LABEL
    assert step.reaction_center == _ALKYNE_DA_CENTER


def test_a_alkyne_da_route_is_no_longer_fiction_blocked():
    chd, buta, ac = parse_smiles("C1=CCC=CC1"), parse_smiles("C=CC=C"), parse_smiles("C#C")
    reg = TransformProviderRegistry((CappedScissionProvider(), AlkyneDielsAlderProvider()))
    res = search_routes(chd, reagents=(), available=(buta, ac), registry=reg, max_depth=2)
    assert len(res.routes) == 1
    assert route_reaction_type_blockers(res.routes[0]) == ()


# --- the two DA classes are locked apart: neither recognizer poaches the other's genuine step ---

def test_the_alkene_recognizer_does_not_poach_a_genuine_alkyne_da_step():
    step = _alkyne_da_synthesis_step()
    assert _diels_alder(step) is False


def test_the_alkyne_recognizer_does_not_poach_a_genuine_alkene_da_step():
    step = _da_synthesis_step()
    assert _alkyne_diels_alder(step) is False


# --- the HETEROATOM families (aza + oxa): the first non-all-carbon pericyclic recognizers ---

_AZA_LABEL = "aza-Diels-Alder [4+2] cycloaddition (diene + imine dienophile -> tetrahydropyridine)"
_OXA_LABEL = "oxa-Diels-Alder [4+2] cycloaddition (diene + carbonyl dienophile -> dihydropyran)"


def _aza_synthesis_step() -> ExperimentStep:
    edge = AzaDielsAlderProvider().enumerate_transforms(parse_smiles("C1C=CCCN1"), (), budget=100000)[0][0]
    return ExperimentStep.from_transform(edge, envelope=None)


def _oxa_synthesis_step() -> ExperimentStep:
    edge = OxaDielsAlderProvider().enumerate_transforms(parse_smiles("C1C=CCCO1"), (), budget=100000)[0][0]
    return ExperimentStep.from_transform(edge, envelope=None)


def test_aza_synthesis_step_is_vouched_as_aza_diels_alder():
    step = _aza_synthesis_step()
    assert _aza_diels_alder(step) is True
    assert recognize_reaction_type(step) == _AZA_LABEL
    assert step.reaction_center == AZA_DA.center


def test_oxa_synthesis_step_is_vouched_as_oxa_diels_alder():
    step = _oxa_synthesis_step()
    assert _oxa_diels_alder(step) is True
    assert recognize_reaction_type(step) == _OXA_LABEL
    assert step.reaction_center == OXA_DA.center


def test_hetero_layer_a_refuses_a_mass_balancing_non_hetero_da_even_with_a_spoofed_center():
    # C2H4 + C3H5N = C5H9N balances, but a 1-aza-1,5-hexadiene is acyclic -- NOT an aza [4+2].  Handed the aza
    # centre adversarially, Layer A's independent re-derivation still refuses it (fail-closed).
    spoofed = SimpleNamespace(
        reactants=(parse_smiles("C=C"), parse_smiles("C=CC=N")),
        products=(parse_smiles("C=CCCC=N"),),     # acyclic, not the tetrahydropyridine adduct
        reaction_center=AZA_DA.center,
    )
    assert _aza_diels_alder(spoofed) is False


def test_hetero_layer_c_blocks_a_genuine_shape_with_no_readable_center():
    centreless = SimpleNamespace(
        reactants=(parse_smiles("C=CC=C"), parse_smiles("C=O")),
        products=(parse_smiles("C1C=CCCO1"),),    # dihydropyran: a genuine oxa [4+2] adduct
        reaction_center=None,
    )
    assert _oxa_diels_alder(centreless) is False


def test_the_four_da_recognizers_are_locked_apart_no_cross_poach():
    # each recognizer vouches ONLY its own family's genuine step -- the exact-equality centre check + Layer A
    # re-derivation keep alkene / alkyne / aza / oxa mutually exclusive.
    steps = {
        "alkene": _da_synthesis_step(), "alkyne": _alkyne_da_synthesis_step(),
        "aza": _aza_synthesis_step(), "oxa": _oxa_synthesis_step(),
    }
    recognizers = {"alkene": _diels_alder, "alkyne": _alkyne_diels_alder,
                   "aza": _aza_diels_alder, "oxa": _oxa_diels_alder}
    for step_name, step in steps.items():
        for rec_name, rec in recognizers.items():
            assert rec(step) is (step_name == rec_name), f"{rec_name} recognizer on {step_name} step"


def test_a_hetero_da_route_is_no_longer_fiction_blocked():
    thp, buta, imine = parse_smiles("C1C=CCCN1"), parse_smiles("C=CC=C"), parse_smiles("C=N")
    reg = TransformProviderRegistry((CappedScissionProvider(), AzaDielsAlderProvider()))
    res = search_routes(thp, reagents=(), available=(buta, imine), registry=reg, max_depth=2)
    assert len(res.routes) == 1
    assert route_reaction_type_blockers(res.routes[0]) == ()
