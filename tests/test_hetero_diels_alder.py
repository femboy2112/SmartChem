"""HETERO-DIELS-ALDER-FAMILY-01: the first NON-all-carbon [4+2] rule-calculus families.

Covers :mod:`smartchem.diels_alder`'s heteroatom-dienophile families -- aza (diene + imine -> tetrahydropyridine)
and oxa (diene + carbonyl -> dihydropyran).  Each family is the all-carbon alkene rule with dienophile vertex 5
relabeled ``C -> heteroatom``; the kernel matches by LABEL, so the guards (via ``_guarded_retro``), the degree
pattern, and the opt-in seam are shared verbatim, while the heteroatom-bearing reaction centre keeps every family
provably disjoint (verified: no cross-poach).  Same guard/certificate discipline as the all-carbon siblings.
"""
from __future__ import annotations

import pytest

from smartchem.category import Bond, Molecule
from smartchem.diels_alder import (
    AZA_DA, AZA_DIENE_DA, OXA_DA, OXA_DIENE_DA, THIA_DA, AlkyneDielsAlderProvider, AzaDielsAlderProvider,
    AzaDieneDielsAlderProvider, DielsAlderProvider, HeteroDielsAlderEdge, OxaDielsAlderProvider,
    OxaDieneDielsAlderProvider, ThiaDielsAlderProvider, _ALKYNE_DA_CENTER, _DA_CENTER, _synthesis_center,
)
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentStep
from smartchem.rule_calculus import BondGraph, Edge, apply, verify
from smartchem.rule_calculus_bridge import valence_sane
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import ScissionError
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY, CappedScissionProvider, TransformProviderRegistry

# (family, provider_factory, adduct_smiles, dienophile_smiles, {product formulae})
_AZA = (AZA_DA, AzaDielsAlderProvider, "C1C=CCCN1", "C=N", {"C4H6", "CH3N"})
_OXA = (OXA_DA, OxaDielsAlderProvider, "C1C=CCCO1", "C=O", {"C4H6", "CH2O"})
_THIA = (THIA_DA, ThiaDielsAlderProvider, "C1C=CCCS1", "C=S", {"C4H6", "CH2S"})
_CASES = [_AZA, _OXA, _THIA]
_IDS = ["aza", "oxa", "thia"]

# The DIENE-position families (item B): the heteroatom is a diene terminus, not the dienophile.  Same shape as the
# dienophile cases but a distinct adduct regio-isomer (X adjacent to the ring C=C), an all-carbon (ethene) dienophile,
# and -- the load-bearing new property -- a synthesis centre SHARED with the same-heteroatom dienophile family.
# (family, provider_factory, adduct_smiles, dienophile_smiles, {product formulae}, dienophile_sibling_family)
_AZA_DIENE = (AZA_DIENE_DA, AzaDieneDielsAlderProvider, "N1C=CCCC1", "C=C", {"C2H4", "C3H5N"}, AZA_DA)
_OXA_DIENE = (OXA_DIENE_DA, OxaDieneDielsAlderProvider, "O1C=CCCC1", "C=C", {"C2H4", "C3H4O"}, OXA_DA)
_DIENE_CASES = [_AZA_DIENE, _OXA_DIENE]
_DIENE_IDS = ["aza-diene", "oxa-diene"]


def _transforms(provider, smiles):
    return provider.enumerate_transforms(parse_smiles(smiles), (), budget=100000)[0]


# --- the rule itself ---

@pytest.mark.parametrize("family,_prov,_add,_dp,_frags", _CASES, ids=_IDS)
def test_hetero_rule_is_degree_preserving_and_round_trips(family, _prov, _add, _dp, _frags):
    # A pericyclic reaction conserves valence at every atom, heteroatom dienophile included (imine/carbonyl is a
    # double bond exactly like an alkene, so the degree pattern is the alkene family's).
    assert family.forward.left.degrees == family.forward.right.degrees == (2, 3, 3, 2, 2, 2)
    fwd = apply(family.forward, family.forward.left, tuple(range(6)))
    assert verify(fwd) and fwd.target == family.forward.right       # diene + hetero-dienophile -> heterocycle
    retro = apply(family.retro, family.retro.left, tuple(range(6)))
    assert verify(retro) and retro.target == family.forward.left    # round-trips back to diene + dienophile


# --- positives ---

@pytest.mark.parametrize("family,prov,adduct,_dp,frags", _CASES, ids=_IDS)
def test_hetero_adduct_disconnects_to_diene_plus_dienophile(family, prov, adduct, _dp, frags):
    transforms = _transforms(prov(), adduct)
    assert transforms, f"{adduct} must disconnect to a diene + hetero dienophile"
    for t in transforms:
        assert t.reaction_class == family.class_label
        assert {repr(m) for m in t.products} == frags


@pytest.mark.parametrize("family,prov,adduct,dienophile,_frags", _CASES, ids=_IDS)
def test_search_routes_finds_the_hetero_da_route_only_with_the_provider(family, prov, adduct, dienophile, _frags):
    target, buta, dp = parse_smiles(adduct), parse_smiles("C=CC=C"), parse_smiles(dienophile)
    reg = TransformProviderRegistry((CappedScissionProvider(), prov()))
    with_da = search_routes(target, reagents=(), available=(buta, dp), registry=reg, max_depth=2)
    assert len(with_da.routes) == 1
    assert [repr(m) for m in with_da.routes[0].steps[0].products] == [repr(parse_smiles(adduct))]
    without = search_routes(target, reagents=(), available=(buta, dp), max_depth=2)
    assert len(without.routes) == 0   # control: the single-cut default grammar genuinely misses it


@pytest.mark.parametrize("family,prov,adduct,_dp,frags", _CASES, ids=_IDS)
def test_the_edge_reverses_into_the_forward_synthesis(family, prov, adduct, _dp, frags):
    edge = _transforms(prov(), adduct)[0]
    step = ExperimentStep.from_transform(edge, envelope=None)
    assert {repr(m) for m in step.reactants} == frags
    assert [repr(m) for m in step.products] == [repr(parse_smiles(adduct))]


# --- guard negatives (each a coverage-loss drop, never a coerced witness) ---

@pytest.mark.parametrize("prov,saturated,aromatic", [
    (AzaDielsAlderProvider, "C1CCCCN1", "c1ccncc1"),   # piperidine (no ring C=C); pyridine (aromatic)
    (OxaDielsAlderProvider, "C1CCCCO1", "c1ccoc1"),    # oxane (no ring C=C); furan (aromatic)
    (ThiaDielsAlderProvider, "C1CCCCS1", "c1ccsc1"),   # thiane (no ring C=C); thiophene (aromatic)
], ids=_IDS)
def test_saturated_and_aromatic_heterocycles_do_not_match(prov, saturated, aromatic):
    assert _transforms(prov(), saturated) == ()
    assert _transforms(prov(), aromatic) == ()


def test_the_all_carbon_and_sibling_families_do_not_cross_poach():
    # each family's rule fixes its dienophile atom's LABEL, so an all-carbon ring never matches a hetero rule and a
    # hetero adduct never matches the all-carbon (or the other heteroatom's) rule.
    assert _transforms(AzaDielsAlderProvider(), "C1C=CCCO1") == ()      # aza rule on the oxa adduct
    assert _transforms(OxaDielsAlderProvider(), "C1C=CCCN1") == ()      # oxa rule on the aza adduct
    assert _transforms(ThiaDielsAlderProvider(), "C1C=CCCN1") == ()     # thia rule on the aza adduct
    assert _transforms(ThiaDielsAlderProvider(), "C1C=CCCO1") == ()     # thia rule on the oxa adduct
    assert _transforms(AzaDielsAlderProvider(), "C1C=CCCS1") == ()      # aza rule on the thia adduct
    assert _transforms(DielsAlderProvider(), "C1C=CCCN1") == ()         # alkene rule on the aza adduct
    assert _transforms(DielsAlderProvider(), "C1C=CCCO1") == ()         # alkene rule on the oxa adduct
    assert _transforms(DielsAlderProvider(), "C1C=CCCS1") == ()         # alkene rule on the thia adduct
    assert _transforms(AlkyneDielsAlderProvider(), "C1C=CCCN1") == ()   # alkyne rule on the aza adduct
    assert _transforms(AzaDielsAlderProvider(), "C1CC=CCC1") == ()      # aza rule on all-carbon cyclohexene
    assert _transforms(ThiaDielsAlderProvider(), "C1CC=CCC1") == ()     # thia rule on all-carbon cyclohexene


# --- the opt-in providers + the unchanged route/DAG seam ---

def test_the_providers_are_opt_in_absent_from_the_default_registry():
    assert "diels-alder-aza-retro" not in DEFAULT_TRANSFORM_REGISTRY.provider_ids
    assert "diels-alder-oxa-retro" not in DEFAULT_TRANSFORM_REGISTRY.provider_ids


@pytest.mark.parametrize("family,prov,_add,_dp,_frags", _CASES, ids=_IDS)
def test_the_other_oracle_classes_yield_no_hetero_da_transform(family, prov, _add, _dp, _frags):
    for smiles in ("CC(=O)OC",   # methyl acetate (acyl class)
                   "CCOCC",      # diethyl ether (ether class)
                   "CCN",        # ethylamine (N-alkylation class)
                   "C1CCCCC1"):  # cyclohexane (saturated near-miss)
        assert _transforms(prov(), smiles) == (), f"{smiles} must not yield a {family.hetero_label} DA transform"


@pytest.mark.parametrize("family,prov,adduct,_dp,_frags", _CASES, ids=_IDS)
def test_mixed_registry_enumerate_tags_hetero_da_provenance(family, prov, adduct, _dp, _frags):
    reg = TransformProviderRegistry((CappedScissionProvider(), prov()))
    ets, complete = reg.enumerate(parse_smiles(adduct), (), budget=100000)
    hetero = [e for e in ets if e.witness_kind == family.witness_kind]
    assert hetero and all(e.provider_id == family.provider_id for e in hetero) and complete


# --- the second (DA-ness) certificate is load-bearing ---

@pytest.mark.parametrize("family,_prov,adduct,_dp,_frags", _CASES, ids=_IDS)
def test_the_edge_self_verifies_conservation_and_da_ness(family, _prov, adduct, _dp, _frags):
    # A hand-built edge whose fragments balance MASS but are not a genuine hetero [4+2] retro of the reactant is
    # refused (conservation alone does not prove DA-ness -- the second certificate is load-bearing).  For aza,
    # C5H9N = C2H4 + C3H5N balances but is not the guarded retro (butadiene + methanimine); likewise for oxa.
    wrong = {"N": ("C=C", "C=CC=N"), "O": ("C=C", "C=CC=O"), "S": ("C=C", "C=CC=S")}[family.hetero_label]
    with pytest.raises(ScissionError):
        HeteroDielsAlderEdge(family.schema, parse_smiles(adduct),
                             (parse_smiles(wrong[0]), parse_smiles(wrong[1])), (), family.class_label, family)


# --- the reaction centre is derived from the rule, and the four DA families are mutually distinct ---

@pytest.mark.parametrize("family,_prov,_add,_dp,_frags", _CASES, ids=_IDS)
def test_hetero_center_is_derived_from_the_forward_rule(family, _prov, _add, _dp, _frags):
    assert family.center == _synthesis_center(family.forward)


def test_the_five_dienophile_da_centres_are_all_distinct():
    centres = [_DA_CENTER, _ALKYNE_DA_CENTER, AZA_DA.center, OXA_DA.center, THIA_DA.center]
    assert len({c for c in centres}) == 5        # no two DIENOPHILE-position families share a synthesis centre
    # the hetero centres carry the family's (C, heteroatom, .) bond pairs no all-carbon centre carries.
    assert any(pair[:2] == ("C", "N") for pair in AZA_DA.center.formed)
    assert any(pair[:2] == ("C", "O") for pair in OXA_DA.center.formed)
    assert any(pair[:2] == ("C", "S") for pair in THIA_DA.center.formed)


# --- the #83 valence ceiling is now LOAD-BEARING (ring N/O are in-scope atoms) ---

def test_the_valence_ceiling_now_gates_ring_heteroatoms():
    # An oxygen at coordination 4 is impossible in EVERY charge state (ceiling 3) -> refused; a 3-coordinate ring N
    # is legitimate (ceiling 5) -> admitted.  These ceilings only START mattering once heteroatoms are in scope.
    o4 = BondGraph(("O", "C", "C", "C", "C"),
                   frozenset({Edge(0, 1, 1), Edge(0, 2, 1), Edge(0, 3, 1), Edge(0, 4, 1)}))
    n3 = BondGraph(("N", "C", "C", "C"), frozenset({Edge(0, 1, 1), Edge(0, 2, 1), Edge(0, 3, 1)}))
    assert valence_sane(o4) is False
    assert valence_sane(n3) is True


# --- guard 2c: the round-9 oxocarbenium/iminium NEUTRAL-VALENCE false-vouch kill (evil-morty + dalembert) ---

def _graph_mol(atoms, bonds):
    # a hand-built Molecule graph (bypasses the parser, which would assign a formal charge and be refused upstream)
    return Molecule(tuple(atoms), frozenset(Bond(i, j, o) for i, j, o in bonds))


def test_guard_2c_blocks_the_oxocarbenium_false_vouch():
    # A dihydropyran with an exocyclic O-CH3 puts the ring O at bond-order 3 -- an oxocarbenium drawn neutral.
    # valence_sane's charge-agnostic ceiling (O=3) admits the graph, but guard 2c bounds the centre O by its
    # NEUTRAL valence (2), so the over-valence retro is DROPPED: no charged fragment gets posed as a carbonyl.
    oxa_o3 = _graph_mol(["C", "C", "C", "C", "C", "O", "C"],
                        [(0, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1), (5, 6, 1)])
    assert OxaDielsAlderProvider().enumerate_transforms(oxa_o3, (), budget=100000)[0] == ()


def test_guard_2c_blocks_the_iminium_false_vouch():
    # A tetrahydropyridine with TWO exocyclic N-CH3 puts the ring N at bond-order 4 -- an iminium drawn neutral;
    # N's neutral valence is 3, so guard 2c drops it.
    aza_n4 = _graph_mol(["C", "C", "C", "C", "C", "N", "C", "C"],
                        [(0, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1), (5, 6, 1), (5, 7, 1)])
    assert AzaDielsAlderProvider().enumerate_transforms(aza_n4, (), budget=100000)[0] == ()


def test_guard_2c_keeps_the_n_substituted_aza_da_real_neutral_case():
    # An N-METHYL tetrahydropyridine (ring N at bond-order 3) IS a real NEUTRAL tertiary-amine aza-DA adduct
    # (N-methylmethanimine + butadiene); N's neutral valence is 3, so guard 2c KEEPS it -- zero loss on real
    # chemistry, the substituted case included.
    aza_n3 = _graph_mol(["C", "C", "C", "C", "C", "N", "C"],
                        [(0, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1), (5, 6, 1)])
    ts = AzaDielsAlderProvider().enumerate_transforms(aza_n3, (), budget=100000)[0]
    assert len(ts) == 1 and ts[0].reaction_class == AZA_DA.class_label


def test_guard_2c_blocks_the_thiocarbenium_false_vouch():
    # ITEM A -- the round-9 kill ONE ELEMENT OVER.  An S-methylated dihydrothiopyran puts the ring S at bond-order 3
    # (a sulfonium/thiocarbenium drawn neutral).  valence_sane admits it (S ceiling 6), but guard 2c bounds the
    # centre S by its NEUTRAL valence (2, in _NEUTRAL_VALENCE), so the over-valence retro is DROPPED -- proven
    # load-bearing: WITHOUT the S bound this ring emits the garbage fragments C2S + C4 as a false-vouch.
    thia_s3 = _graph_mol(["C", "C", "C", "C", "C", "S", "C"],
                         [(0, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1), (5, 6, 1)])
    assert ThiaDielsAlderProvider().enumerate_transforms(thia_s3, (), budget=100000)[0] == ()


# --- item B: the DIENE-position families -- positives, the shared-centre COLLISION, and Layer-A-only separation ---

@pytest.mark.parametrize("family,prov,adduct,_dp,frags,_sib", _DIENE_CASES, ids=_DIENE_IDS)
def test_hetero_diene_adduct_disconnects_to_diene_plus_alkene(family, prov, adduct, _dp, frags, _sib):
    transforms = _transforms(prov(), adduct)
    assert transforms, f"{adduct} must disconnect to a 1-hetero-diene + an alkene dienophile"
    for t in transforms:
        assert t.reaction_class == family.class_label
        assert {repr(m) for m in t.products} == frags


@pytest.mark.parametrize("family,prov,adduct,_dp,_frags,_sib", _DIENE_CASES, ids=_DIENE_IDS)
def test_hetero_diene_family_is_a_terminus_relabel(family, prov, adduct, _dp, _frags, _sib):
    # the heteroatom sits at diene vertex 0 (a 1-hetero-1,3-diene), not the dienophile vertex 5.
    assert family.hetero_vertex == 0 and family.position == "diene"
    assert family.forward.left.labels[0] == family.hetero_label
    assert family.forward.left.degrees == family.forward.right.degrees == (2, 3, 3, 2, 2, 2)


@pytest.mark.parametrize("family,_prov,_add,_dp,_frags,sibling", _DIENE_CASES, ids=_DIENE_IDS)
def test_the_diene_and_dienophile_families_SHARE_a_synthesis_centre(family, _prov, _add, _dp, _frags, sibling):
    # THE crown finding (verified on the kernel): the (C,X,.) formed/broken multiset is invariant to WHERE the single
    # heteroatom sits in the six-ring, so a diene-position family and its same-heteroatom dienophile family have the
    # IDENTICAL synthesis centre.  This is why Layer B (exact-equality centre) is NOT a separator for them -- Layer A
    # is (proven by the no-cross-poach test below).
    assert family.center == sibling.center
    assert family.center == _synthesis_center(family.forward)


@pytest.mark.parametrize("family,prov,adduct,_dp,_frags,sibling", _DIENE_CASES, ids=_DIENE_IDS)
def test_diene_and_dienophile_families_do_not_cross_poach_despite_shared_centre(family, prov, adduct,
                                                                                _dp, _frags, sibling):
    from smartchem.diels_alder import AzaDielsAlderProvider as _Aza, OxaDielsAlderProvider as _Oxa
    dienophile_prov = {"N": _Aza, "O": _Oxa}[family.hetero_label]
    dienophile_adduct = {"N": "C1C=CCCN1", "O": "C1C=CCCO1"}[family.hetero_label]
    # the DIENE rule finds nothing on the DIENOPHILE adduct (X isolated from the ring C=C) ...
    assert _transforms(prov(), dienophile_adduct) == ()
    # ... and the DIENOPHILE rule finds nothing on the DIENE adduct (X adjacent to the ring C=C).
    assert _transforms(dienophile_prov(), adduct) == ()
    # sanity: each DOES disconnect its own adduct, so the empties above are genuine non-matches, not dead providers.
    assert _transforms(prov(), adduct)
    assert _transforms(dienophile_prov(), dienophile_adduct)
