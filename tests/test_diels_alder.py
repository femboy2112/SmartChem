"""DIELS-ALDER-FAMILY-01: the first NEW structural reaction family compiled onto the rule_calculus kernel.

Acceptance pins for :mod:`smartchem.diels_alder` -- guarded all-carbon [4+2] retro-disconnections. These are the
ordinary regression gates (positives, guard negatives, round-trip, fail-closed class witness, independent verifier);
the adversarial gate (evil-morty/dalembert) runs SEPARATELY from acceptance per the 4-round meta-lesson, and its kills
land as their own pins. Design + boundaries: ``docs/research/RULE_CALCULUS_DIELS_ALDER_FAMILY_v0.1.md``.
"""
from __future__ import annotations

from dataclasses import replace

from smartchem.diels_alder import (
    DA_CLASS, DA_RETRO_SCHEMA, RETRO_DA, DielsAlderProvider, DielsAlderRetroEdge, _FORWARD,
    class_witness, independently_reconstructs, retro_da_disconnections,
)
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentStep
from smartchem.rule_calculus import BondGraph, Edge, apply, verify
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import ScissionError
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY, CappedScissionProvider, TransformProviderRegistry,
)

_CHX = [(0, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1)]  # cyclohexene ring


def _g(labels, edges):
    return BondGraph(tuple(labels), frozenset(Edge(*e) for e in edges))


def _n(graph):
    return len(retro_da_disconnections(graph)[0])


# --- the rule itself ---

def test_retro_da_rule_is_degree_preserving_and_round_trips():
    # A pericyclic reaction conserves valence at every atom, so the fixed-vertex degree lock accepts it.
    assert RETRO_DA.left.degrees == RETRO_DA.right.degrees == (2, 3, 3, 2, 2, 2)
    fwd = apply(_FORWARD, _FORWARD.left, tuple(range(6)))
    assert verify(fwd) and fwd.target == _FORWARD.right          # diene+dienophile -> cyclohexene
    retro = apply(RETRO_DA, RETRO_DA.left, tuple(range(6)))
    assert verify(retro) and retro.target == _FORWARD.left       # cyclohexene -> diene+dienophile (round-trip)


# --- positives ---

def test_cyclohexene_disconnects_once_after_dedup():
    audits, complete = retro_da_disconnections(_g("C" * 6, _CHX))
    assert complete and len(audits) == 1
    a = audits[0]
    assert a.reaction_class == DA_CLASS
    assert a.diene_vertices == (0, 1, 2, 3) and a.dienophile_vertices == (4, 5)


def test_a_ring_substituent_rides_along_and_does_not_block_the_disconnection():
    # 4-methylcyclohexene: the extra carbon hangs off a ring atom (not among the six), so the induced-subgraph lock
    # is untouched and the disconnection still fires.
    assert _n(_g("C" * 7, _CHX + [(3, 6, 1)])) == 1


# --- guard negatives (each a coverage-loss drop, never a coerced witness) ---

def test_cyclohexane_has_no_disconnection():
    assert _n(_g("C" * 6, [(0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1)])) == 0


def test_benzene_is_excluded_by_construction():
    # Three ring double bonds; the pattern needs exactly one, and five consecutive singles never embed in benzene.
    assert _n(_g("C" * 6, [(0, 1, 2), (1, 2, 1), (2, 3, 2), (3, 4, 1), (4, 5, 2), (0, 5, 1)])) == 0


def test_cyclohexadiene_is_excluded_by_the_induced_subgraph_lock():
    # Two ring double bonds -> the six matched carbons do not induce the single-C=C pattern.
    assert _n(_g("C" * 6, [(0, 1, 2), (1, 2, 1), (2, 3, 2), (3, 4, 1), (4, 5, 1), (0, 5, 1)])) == 0


def test_a_bridge_that_keeps_the_fragments_joined_is_dropped_by_the_global_split_guard():
    # An external carbon bridging a diene-side and a dienophile-side ring atom (a norbornene-type bicyclic) means the
    # retro does NOT actually disconnect -> guard 5 drops it (bridged retro-DA is deferred, honest coverage loss).
    assert _n(_g("C" * 7, _CHX + [(0, 6, 1), (4, 6, 1)])) == 0


def test_a_heteroatom_in_the_ring_is_out_of_the_all_carbon_scope():
    assert _n(_g(list("CCCCC") + ["O"], _CHX)) == 0


# --- fail-closed class witness (derived from the match, not the rule id) ---

def test_class_witness_is_none_on_a_non_da_net_change():
    # A witness whose net bond change is not the [4+2] signature yields NO class, even if it verifies.
    graph = _g("C" * 2, [(0, 1, 1)])
    from smartchem.rule_calculus import BondGraph as BG, BondRule
    trivial = BondRule("noop", BG(("C", "C"), frozenset({Edge(0, 1, 1)})), BG(("C", "C"), frozenset({Edge(0, 1, 1)})))
    w = apply(trivial, graph, (0, 1))
    assert verify(w)
    assert class_witness(w) is None


def test_class_witness_rejects_a_tampered_target():
    # Swap the witness target for a same-shape wrong graph: the kernel verify inside class_witness fails closed.
    w = apply(RETRO_DA, RETRO_DA.left, tuple(range(6)))
    assert class_witness(w) == DA_CLASS
    fake = replace(w, target=_g("C" * 6, _CHX))  # not the true retro product
    assert class_witness(fake) is None


# --- independent verifier (separate representation from the enumerator) ---

def test_independent_verifier_confirms_the_true_reconstruction():
    w = apply(RETRO_DA, RETRO_DA.left, tuple(range(6)))
    assert independently_reconstructs(RETRO_DA.left, w.target, w.match) is True


def test_independent_verifier_rejects_a_wrong_reconstruction():
    w = apply(RETRO_DA, RETRO_DA.left, tuple(range(6)))
    wrong_target = _g("C" * 6, [(0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 4, 1), (4, 5, 1), (0, 5, 1)])  # cyclohexane
    assert independently_reconstructs(wrong_target, w.target, w.match) is False


# --- the opt-in provider + the unchanged route/DAG seam ---


def _da_transforms(smiles):
    return DielsAlderProvider().enumerate_transforms(parse_smiles(smiles), (), budget=100000)[0]


def test_the_provider_is_opt_in_absent_from_the_default_registry():
    assert "diels-alder-retro" not in DEFAULT_TRANSFORM_REGISTRY.provider_ids


def test_provider_disconnects_cyclohexene_to_butadiene_plus_ethylene():
    transforms = _da_transforms("C1CC=CCC1")
    assert len(transforms) == 1
    edge = transforms[0]
    assert edge.reaction_class == DA_CLASS
    assert {repr(m) for m in edge.products} == {"C2H4", "C4H6"}   # ethylene + butadiene
    assert edge.equation() == "C6H10 -> C2H4 + C4H6"


def test_the_da_edge_reverses_into_the_forward_synthesis():
    edge = _da_transforms("C1CC=CCC1")[0]
    step = ExperimentStep.from_transform(edge, envelope=None)
    assert {repr(m) for m in step.reactants} == {"C2H4", "C4H6"}   # diene + dienophile ...
    assert [repr(m) for m in step.products] == ["C6H10"]           # ... -> cyclohexene


def test_the_three_existing_classes_and_hostile_near_misses_yield_no_da_transform():
    # The acyl / ether / N-alkylation substrates+products, and aromatic / polyene / acyclic near-misses, are NOT
    # [4+2] adducts -> the provider emits nothing for them (soundness: DA does not poach the other classes).
    for smiles in ("CC(=O)OC",        # methyl acetate (acyl class)
                   "CCOCC",           # diethyl ether (ether class)
                   "CCN",             # ethylamine (N-alkylation class)
                   "c1ccccc1",        # benzene (aromatic near-miss)
                   "C1C=CC=CC1",      # 1,3-cyclohexadiene (polyene near-miss)
                   "C=CCCC=C",        # 1,5-hexadiene (acyclic mass-balancing near-miss)
                   "C1CCCCC1"):       # cyclohexane (saturated near-miss)
        assert _da_transforms(smiles) == (), f"{smiles} must not yield a DA transform"


def test_the_edge_self_verifies_conservation_and_da_ness():
    # A hand-built edge whose fragments balance MASS but are not a genuine [4+2] retro of the reactant is refused
    # (conservation alone does not prove DA-ness -- the second certificate is load-bearing).
    try:
        DielsAlderRetroEdge(DA_RETRO_SCHEMA, parse_smiles("C=CCCC=C"),
                            (parse_smiles("C=C"), parse_smiles("C=CC=C")), (), DA_CLASS)
        raise AssertionError("a mass-balancing non-DA edge must be refused")
    except ScissionError:
        pass


def test_mixed_registry_enumerate_tags_da_provenance():
    reg = TransformProviderRegistry((CappedScissionProvider(), DielsAlderProvider()))
    ets, complete = reg.enumerate(parse_smiles("C1CC=CCC1"), (), budget=100000)
    da = [e for e in ets if e.witness_kind == "DIELS_ALDER"]
    assert len(da) == 1 and da[0].provider_id == "diels-alder-retro" and complete


def test_search_routes_finds_the_da_route_only_with_the_provider():
    chx, buta, eth = parse_smiles("C1CC=CCC1"), parse_smiles("C=CC=C"), parse_smiles("C=C")
    reg = TransformProviderRegistry((CappedScissionProvider(), DielsAlderProvider()))
    with_da = search_routes(chx, reagents=(), available=(buta, eth), registry=reg, max_depth=2)
    assert len(with_da.routes) == 1
    assert [repr(m) for m in with_da.routes[0].steps[0].products] == ["C6H10"]
    # control: the single-cut default grammar genuinely misses it.
    without = search_routes(chx, reagents=(), available=(buta, eth), max_depth=2)
    assert len(without.routes) == 0


def test_forget_is_a_valid_formula_level_decomposition():
    edge = _da_transforms("C1CC=CCC1")[0]
    fe = edge.forget()
    assert fe.equation() == "C6H10 -> C2H4 + C4H6"
