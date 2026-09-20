"""LATERAL-REWRITE-SEAM-01 (item C): [3,3] sigmatropic isomerizations (Cope + Claisen) -- the FIRST rank-flat
(1->1) transform family, and the first whose ``forget()`` is intentionally undefined (the W1 boundary).

Covers the seam's sound core: the kernel-verified [3,3] rules, the guarded standalone enumeration, the rank-flat
edge's double certificate, the two 1->1 oracle recognizers, and the REACHABLE consumer -- a hand-assembled route
containing a Claisen step is VOUCHED (not demoted) by the production reaction-type oracle.  Search auto-discovery is
DEFERRED (W1): a lateral edge's ``forget()`` RAISES, so it cannot ride the decompiler/search conditions path.
Design + boundary: docs/research/RULE_CALCULUS_LATERAL_REWRITE_SEAM_v0.1.md.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from smartchem.experiment.reaction_type_oracle import (
    _claisen_rearrangement, _cope_rearrangement, _diels_alder, recognize_reaction_type, route_reaction_type_blockers,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.lateral_rewrite import (
    CLAISEN, COPE, LateralRewriteEdge, LateralRewriteError, rewrite_edges, sigmatropic_rewrites,
)
from smartchem.diels_alder import DielsAlderProvider, _DA_CENTER
from smartchem.rule_calculus import apply, verify
from smartchem.smiles import parse_smiles, resonance_identity

_COPE_LABEL = "Cope [3,3] sigmatropic rearrangement (1,5-diene -> [3,3] isomer)"
_CLAISEN_LABEL = ("Claisen [3,3] sigmatropic rearrangement (allyl vinyl ether -> gamma,delta-unsaturated carbonyl)")

# (family, a substrate that gives a NON-degenerate [3,3] isomer, its label)
_COPE = (COPE, "C=CC(C)CC=C", _COPE_LABEL)          # 3-methylhexa-1,5-diene (parent is degenerate; this is not)
_CLAISEN = (CLAISEN, "C=CCCC=O", _CLAISEN_LABEL)    # pent-4-enal <- allyl vinyl ether
_CASES = [_COPE, _CLAISEN]
_IDS = ["cope", "claisen"]


# --- the rule is a degree-preserving kernel rewrite that round-trips ---

@pytest.mark.parametrize("family,_sub,_label", _CASES, ids=_IDS)
def test_the_sigmatropic_rule_is_degree_preserving_and_round_trips(family, _sub, _label):
    assert family.forward.left.degrees == family.forward.right.degrees == (2, 3, 2, 2, 3, 2)
    fwd = apply(family.forward, family.forward.left, tuple(range(6)))
    assert verify(fwd) and fwd.target == family.forward.right
    retro = apply(family.retro, family.retro.left, tuple(range(6)))
    assert verify(retro) and retro.target == family.forward.left


# --- the standalone enumeration produces a real, distinct isomer ---

@pytest.mark.parametrize("family,substrate,_label", _CASES, ids=_IDS)
def test_enumeration_yields_a_single_distinct_isomer(family, substrate, _label):
    mol = parse_smiles(substrate)
    isomers = sigmatropic_rewrites(family, mol)
    assert isomers, f"{substrate} must admit a guarded [3,3] rewrite"
    for iso in isomers:
        assert iso.formula == mol.formula                                   # a real isomerization
        assert resonance_identity(iso) != resonance_identity(mol)           # structurally DISTINCT (non-degenerate)


def test_the_parent_cope_is_degenerate_and_drops():
    # 1,5-hexadiene [3,3]-Cope maps to ITSELF; the canonical non-degeneracy guard drops the self-map (a raw
    # graph-digest check would MISS it -- the product graph is a renumbered presentation of the same molecule).
    assert sigmatropic_rewrites(COPE, parse_smiles("C=CCCC=C")) == ()


# --- the rank-flat edge, its double certificate, and the W1 boundary ---

@pytest.mark.parametrize("family,substrate,_label", _CASES, ids=_IDS)
def test_the_edge_builds_and_reverses_into_a_1to1_synthesis_step(family, substrate, _label):
    edge = rewrite_edges(family, parse_smiles(substrate))[0]
    step = ExperimentStep.from_transform(edge, envelope=None)
    assert len(step.reactants) == 1 and len(step.products) == 1                # rank-flat
    assert step.products[0].formula == step.reactants[0].formula              # conserves (an isomerization)
    assert step.reaction_center == family.center


@pytest.mark.parametrize("family,substrate,bogus_smiles", [
    (COPE, "C=CC(C)CC=C", "CC1=CCCCC1"),    # 1-methylcyclohexene: C7H12, balances 3-methylhexadiene, NOT a [3,3]
    (CLAISEN, "C=CCCC=O", "O=C1CCCC1"),     # cyclopentanone: C5H8O, balances pent-4-enal, NOT a [3,3]
], ids=_IDS)
def test_a_fabricated_lateral_edge_is_refused(family, substrate, bogus_smiles):
    # a same-formula isomer that is NOT a guarded [3,3] rewrite of the reactant is refused (conservation alone
    # proves nothing -- every isomer balances mass, so the re-derivation certificate is load-bearing).
    from smartchem.structure_descent import ScissionError
    reactant, bogus = parse_smiles(substrate), parse_smiles(bogus_smiles)
    assert bogus.formula == reactant.formula                        # the bogus product genuinely balances mass ...
    with pytest.raises(ScissionError):                             # ... yet is refused because it is not a [3,3]
        LateralRewriteEdge(family.schema, reactant, (bogus,), (), family.class_label, family)


@pytest.mark.parametrize("family,substrate,_label", _CASES, ids=_IDS)
def test_forget_raises_the_w1_boundary(family, substrate, _label):
    edge = rewrite_edges(family, parse_smiles(substrate))[0]
    with pytest.raises(LateralRewriteError):
        edge.forget()


# --- the oracle recognizers vouch a genuine [3,3] step; the reachable consumer is a hand-built route ---

@pytest.mark.parametrize("family,substrate,label", _CASES, ids=_IDS)
def test_a_sigmatropic_step_is_vouched_as_its_class(family, substrate, label):
    edge = rewrite_edges(family, parse_smiles(substrate))[0]
    step = ExperimentStep.from_transform(edge, envelope=None)
    assert recognize_reaction_type(step) == label


@pytest.mark.parametrize("family,substrate,_label", _CASES, ids=_IDS)
def test_a_hand_built_sigmatropic_route_is_vouched_not_demoted(family, substrate, _label):
    # THE reachable consumer: without the recognizer this 1->1 step would be demoted "unrecognized reaction type";
    # with it, the route is clean.  (A route need not come from search_routes -- ExperimentRoute.of accepts a
    # hand-assembled or literature step, which is exactly the lateral seam's consumer while search auto-discovery
    # stays W1-deferred.)
    edge = rewrite_edges(family, parse_smiles(substrate))[0]
    route = ExperimentRoute.of(ExperimentStep.from_transform(edge, envelope=None))
    assert route_reaction_type_blockers(route) == ()


# --- soundness: Layer A re-derivation, Layer C fail-closed, and no cross-poach ---

def test_layer_a_refuses_a_non_sigmatropic_isomerization_even_with_a_spoofed_center():
    # 1-hexene -> cyclohexane balances (both C6H12) and is a 1->1 "isomerization", but it is NOT a [3,3] shift.
    # Handed the Cope centre adversarially, Layer A's re-derivation still refuses it (fail-closed).
    spoofed = SimpleNamespace(reactants=(parse_smiles("C=CCCCC"),), products=(parse_smiles("C1CCCCC1"),),
                              reaction_center=COPE.center)
    assert _cope_rearrangement(spoofed) is False


def test_layer_c_blocks_a_genuine_shape_with_no_readable_center():
    genuine = rewrite_edges(CLAISEN, parse_smiles("C=CCCC=O"))[0]
    centreless = SimpleNamespace(reactants=tuple(genuine.products), products=(genuine.reactant,),
                                 reaction_center=None)
    assert _claisen_rearrangement(centreless) is False


def test_cope_and_claisen_do_not_cross_poach_and_da_shapes_do_not_either():
    cope_step = ExperimentStep.from_transform(rewrite_edges(COPE, parse_smiles("C=CC(C)CC=C"))[0], envelope=None)
    claisen_step = ExperimentStep.from_transform(rewrite_edges(CLAISEN, parse_smiles("C=CCCC=O"))[0], envelope=None)
    assert _cope_rearrangement(cope_step) and not _claisen_rearrangement(cope_step)
    assert _claisen_rearrangement(claisen_step) and not _cope_rearrangement(claisen_step)
    # a 2->1 DA step is never vouched by a 1->1 sigmatropic recognizer (shape early-out) ...
    da_edge = DielsAlderProvider().enumerate_transforms(parse_smiles("C1CC=CCC1"), (), budget=100000)[0][0]
    da_step = ExperimentStep.from_transform(da_edge, envelope=None)
    assert not _cope_rearrangement(da_step) and not _claisen_rearrangement(da_step)
    # ... and a 1->1 sigmatropic step is never vouched by the 2->1 DA recognizer.
    assert not _diels_alder(cope_step) and not _diels_alder(claisen_step)


def test_the_sigmatropic_centres_are_distinct_from_each_other_and_from_da():
    assert len({COPE.center, CLAISEN.center, _DA_CENTER}) == 3
    # the [3,3] centre forms exactly one sigma and migrates two pi -- no net ring closure, unlike a [4+2].
    assert COPE.center.n_components == 1 and CLAISEN.center.n_components == 1
