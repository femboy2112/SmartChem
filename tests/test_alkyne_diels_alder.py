"""ALKYNE-DIELS-ALDER-FAMILY-01: the alkyne-dienophile sibling of the [4+2] rule-calculus family.

Mirrors :mod:`tests.test_diels_alder` for :mod:`smartchem.diels_alder`'s alkyne-dienophile family: diene + alkyne
-> 1,4-cyclohexadiene (NOT 1,3 -- the verified chemistry).  Same guard/certificate discipline (shared, via
:func:`smartchem.diels_alder._guarded_retro`, with the alkene family), own rule/class/schema/centre so the two
never cross-poach.
"""
from __future__ import annotations

from smartchem.diels_alder import (
    ALKYNE_DA_CLASS, ALKYNE_DA_RETRO_SCHEMA, RETRO_ALKYNE_DA, AlkyneDielsAlderEdge, AlkyneDielsAlderProvider,
    _ALKYNE_DA_CENTER, _FORWARD_ALKYNE,
)
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentStep
from smartchem.rule_calculus import apply, verify
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import ScissionError
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY, CappedScissionProvider, TransformProviderRegistry


def _alkyne_da_transforms(smiles):
    return AlkyneDielsAlderProvider().enumerate_transforms(parse_smiles(smiles), (), budget=100000)[0]


# --- the rule itself ---

def test_retro_alkyne_da_rule_is_degree_preserving_and_round_trips():
    # A pericyclic reaction conserves valence at every atom, even with a triple-bonded dienophile.
    assert RETRO_ALKYNE_DA.left.degrees == RETRO_ALKYNE_DA.right.degrees == (2, 3, 3, 2, 3, 3)
    fwd = apply(_FORWARD_ALKYNE, _FORWARD_ALKYNE.left, tuple(range(6)))
    assert verify(fwd) and fwd.target == _FORWARD_ALKYNE.right       # diene+alkyne -> 1,4-cyclohexadiene
    retro = apply(RETRO_ALKYNE_DA, RETRO_ALKYNE_DA.left, tuple(range(6)))
    assert verify(retro) and retro.target == _FORWARD_ALKYNE.left    # round-trips back to diene+alkyne


# --- positives ---

def test_1_4_cyclohexadiene_disconnects_to_butadiene_plus_acetylene():
    # 1,4-cyclohexadiene has a 2-fold ring symmetry (both ring alkenes are equivalent), so the guarded enumerator
    # legitimately finds two distinct vertex-role matches that both yield the SAME product pair -- this is the
    # documented enumerate_matches behaviour (isomorphism dedup is deliberately not performed), not a bug.
    transforms = _alkyne_da_transforms("C1=CCC=CC1")
    assert transforms, "1,4-cyclohexadiene must disconnect to butadiene + acetylene"
    for t in transforms:
        assert t.reaction_class == ALKYNE_DA_CLASS
        assert {repr(m) for m in t.products} == {"C2H2", "C4H6"}
        assert t.equation() in ("C6H8 -> C2H2 + C4H6", "C6H8 -> C4H6 + C2H2")


def test_search_routes_finds_the_alkyne_da_route_only_with_the_provider():
    chd, buta, ac = parse_smiles("C1=CCC=CC1"), parse_smiles("C=CC=C"), parse_smiles("C#C")
    reg = TransformProviderRegistry((CappedScissionProvider(), AlkyneDielsAlderProvider()))
    with_da = search_routes(chd, reagents=(), available=(buta, ac), registry=reg, max_depth=2)
    assert len(with_da.routes) == 1
    assert [repr(m) for m in with_da.routes[0].steps[0].products] == ["C6H8"]
    # control: the single-cut default grammar genuinely misses it.
    without = search_routes(chd, reagents=(), available=(buta, ac), max_depth=2)
    assert len(without.routes) == 0


def test_the_edge_reverses_into_the_forward_synthesis():
    edge = _alkyne_da_transforms("C1=CCC=CC1")[0]
    step = ExperimentStep.from_transform(edge, envelope=None)
    assert {repr(m) for m in step.reactants} == {"C2H2", "C4H6"}
    assert [repr(m) for m in step.products] == ["C6H8"]


# --- guard negatives (each a coverage-loss drop, never a coerced witness) ---

def test_1_3_cyclohexadiene_has_no_alkyne_da_disconnection():
    # The two ring C=C are adjacent (conjugated 1,3-spacing), not the 1,4-symmetric spacing the alkyne pattern needs.
    assert _alkyne_da_transforms("C1=CC=CCC1") == ()


def test_benzene_is_excluded_by_construction():
    # Three ring double bonds; the pattern needs exactly two, so the induced-subgraph lock rejects every embedding.
    assert _alkyne_da_transforms("c1ccccc1") == ()


def test_cyclohexene_has_no_alkyne_da_disconnection():
    # Cyclohexene carries only ONE ring C=C; the alkyne-family retro pattern needs two (the ring alkene the retro
    # leaves behind, plus the diene's own), so it does not match at all.
    assert _alkyne_da_transforms("C1CC=CCC1") == ()


# --- the opt-in provider + the unchanged route/DAG seam ---

def test_the_provider_is_opt_in_absent_from_the_default_registry():
    assert "diels-alder-alkyne-retro" not in DEFAULT_TRANSFORM_REGISTRY.provider_ids


def test_the_other_oracle_classes_yield_no_alkyne_da_transform():
    for smiles in ("CC(=O)OC",   # methyl acetate (acyl class)
                   "CCOCC",      # diethyl ether (ether class)
                   "CCN",        # ethylamine (N-alkylation class)
                   "C1CC=CCC1",  # cyclohexene (the ALKENE DA family's own product -- not this family's pattern)
                   "C1CCCCC1"):  # cyclohexane (saturated near-miss)
        assert _alkyne_da_transforms(smiles) == (), f"{smiles} must not yield an alkyne DA transform"


def test_the_edge_self_verifies_conservation_and_da_ness():
    # A hand-built edge whose fragments balance MASS but are not a genuine alkyne [4+2] retro of the reactant is
    # refused (conservation alone does not prove DA-ness -- the second certificate is load-bearing).
    try:
        AlkyneDielsAlderEdge(ALKYNE_DA_RETRO_SCHEMA, parse_smiles("C=CCCC=C"),
                             (parse_smiles("C=C"), parse_smiles("C=CC=C")), (), ALKYNE_DA_CLASS)
        raise AssertionError("a mass-balancing non-alkyne-DA edge must be refused")
    except ScissionError:
        pass


def test_mixed_registry_enumerate_tags_alkyne_da_provenance():
    reg = TransformProviderRegistry((CappedScissionProvider(), AlkyneDielsAlderProvider()))
    ets, complete = reg.enumerate(parse_smiles("C1=CCC=CC1"), (), budget=100000)
    da = [e for e in ets if e.witness_kind == "DIELS_ALDER_ALKYNE"]
    assert da and all(e.provider_id == "diels-alder-alkyne-retro" for e in da) and complete


def test_alkyne_da_center_is_derived_from_the_forward_rule_and_distinct_from_the_alkene_one():
    from smartchem.diels_alder import _DA_CENTER, _synthesis_center
    assert _ALKYNE_DA_CENTER == _synthesis_center(_FORWARD_ALKYNE)
    assert _ALKYNE_DA_CENTER != _DA_CENTER


# --- the honest structural/feasibility boundary (dalembert) ---

def test_an_aromatic_diene_fragment_is_vouched_as_structural_type_feasibility_deferred():
    # Barrelene retro-disconnects to benzene + acetylene: a valid [4+2] TOPOLOGY whose diene fragment is aromatic
    # (benzene, a reluctant diene).  Guard 3 excludes aromatic ADDUCTS, not retro FRAGMENTS, so this IS emitted --
    # correct under the module's structural-type-validity contract.  Feasibility (benzene vs anthracene as a diene)
    # is Problem B, deferred.  Pinned so the boundary is deliberate, not a surprise, and so nobody "fixes" it by
    # dropping aromatic dienes (which would wrongly kill the genuine anthracene-type Diels-Alder).
    transforms = _alkyne_da_transforms("C1=CC2C=CC1C=C2")   # barrelene, C8H8
    assert transforms, "barrelene is a structurally valid alkyne-[4+2] adduct"
    assert all(t.reaction_class == ALKYNE_DA_CLASS for t in transforms)
    assert any({repr(m) for m in t.products} == {"C2H2", "C6H6"} for t in transforms)  # acetylene + benzene
