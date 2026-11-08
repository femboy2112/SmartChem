"""#116 -- alcohol DEHYDRATION (1,2-elimination, alcohol -> alkene + H2O): the 26th reaction-type class.

Pins: the recognizer vouches genuine dehydrations generator-independently (and the independent witness agrees);
every adversarial look-alike ABSTAINS (and the witness rejects it too); no existing class claims a dehydration step
and the dehydration recognizer claims no other class's step; conservation; the generator's fail-closed certificate;
BOTH regiochemistries with no selectivity claim; and the activator ledger's acid-catalyst requirement.
"""
from __future__ import annotations

import dataclasses
from collections import Counter

import pytest

from smartchem.conditions import ConditionEnvelope, EvidenceStatus
from smartchem.elimination import (
    DEHYDRATION_CLASS,
    DEHYDRATION_SCHEMA,
    DehydrationEdge,
    EliminationError,
    _forward_dehydrations,
    retro_dehydration_edges,
    retro_dehydration_enumeration,
)
from smartchem.elimination_witness import witnesses_dehydration
from smartchem.experiment.activator_ledger import (
    ActivatorRole,
    classify_activator_roles,
    route_activator_blockers,
    step_activator_blockers,
)
from smartchem.experiment.event_search import EventType, classify_event
from smartchem.experiment.reaction_type_oracle import (
    ABSTAIN,
    _RECOGNIZERS,
    _dehydration,
    recognize_reaction_type,
    recognize_reaction_type_outcome,
    route_reaction_type_blockers,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep, StepError
from smartchem.lateral_rewrite import ELECTRO_6PI, rewrite_edges
from smartchem.smiles import parse_smiles, resonance_identity

P = parse_smiles
WATER = "O"


def _step(reactants, products, catalysts=None):
    """A step built from raw SMILES multisets (never through the generator). ``products[0]`` is the target."""
    step = ExperimentStep.assembling(P(products[0]), tuple(P(x) for x in reactants), tuple(P(x) for x in products))
    if catalysts is not None:
        env = ConditionEnvelope(catalysts=tuple(catalysts), status=EvidenceStatus.EXPERIMENTAL, provenance="test")
        step = dataclasses.replace(step, envelope=env)
    return step


def _dehydration_step(precursor, target, catalysts=None):
    return _step((precursor,), (target, WATER), catalysts=catalysts)


def _fired(step):
    out = []
    for name, pred in _RECOGNIZERS:
        try:
            if pred(step):
                out.append(name)
        except Exception:
            pass
    return out


POSITIVES = [
    ("ethanol -> ethene", "CCO", "C=C"),
    ("cyclohexanol -> cyclohexene", "OC1CCCCC1", "C1=CCCCC1"),
    ("tert-butanol -> isobutene", "CC(C)(C)O", "C=C(C)C"),
    ("2-butanol -> 1-butene", "CCC(C)O", "C=CCC"),
    ("2-butanol -> 2-butene", "CCC(C)O", "CC=CC"),
    ("1-phenylethanol -> styrene", "CC(O)c1ccccc1", "C=Cc1ccccc1"),
]

#: (label, reactants, products) -- every one must ABSTAIN overall, never vouch as dehydration.
ADVERSARIAL_STEPS = [
    ("1,4-butanediol -> THF + H2O (ring-closing etherification)", ("OCCCCO",), ("C1CCOC1", WATER)),
    ("neopentyl alcohol -> 2-methyl-2-butene (1,2-shift)", ("CC(C)(C)CO",), ("CC=C(C)C", WATER)),
    ("3,3-dimethylbutan-2-ol -> 2,3-dimethylbut-2-ene (1,2-shift)", ("CC(O)C(C)(C)C",), ("CC(C)=C(C)C", WATER)),
    ("1-butanol -> 2-butene (remote alkene)", ("CCCCO",), ("CC=CC", WATER)),
    ("3-hydroxybutanal -> methyl vinyl ketone (skeleton change)", ("CC(O)CC=O",), ("C=CC(C)=O", WATER)),
    ("cyclohexa-2,4-dien-1-ol -> benzene (aromatisation)", ("OC1C=CC=CC1",), ("c1ccccc1", WATER)),
    ("ethane-1,1-diol -> acetaldehyde (masked carbonyl)", ("CC(O)O",), ("CC=O", WATER)),
    ("ethylene glycol -> vinyl alcohol (enol)", ("OCCO",), ("C=CO", WATER)),
    ("vinyl alcohol -> ethyne", ("C=CO",), ("C#C", WATER)),
    ("allyl alcohol -> allene (cumulene)", ("C=CCO",), ("C=C=C", WATER)),
    ("acetic acid -> ketene", ("CC(=O)O",), ("C=C=O", WATER)),
    ("ethyl methyl ether -> ethene + methanol", ("CCOC",), ("C=C", "CO")),
    ("ethyl methyl ether -> propene + H2O (glue fiction)", ("CCOC",), ("C=CC", WATER)),
    ("oxirane -> vinyl alcohol (epoxide -> enol isomer)", ("C1CO1",), ("C=CO",)),
    ("bromoethane -> ethene + HBr (HX slice, out of scope)", ("CCBr",), ("C=C", "Br")),
    ("butane-1,4-diol -> butadiene + 2 H2O (two waters)", ("OCCCCO",), ("C=CC=C", WATER, WATER)),
    ("2-methoxyethanol -> methyl vinyl ether (enol ether)", ("COCCO",), ("C=COC", WATER)),
    ("cyclopropanol -> cyclopropene (3-ring)", ("OC1CC1",), ("C1=CC1", WATER)),
]


# -- positives -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,precursor,target", POSITIVES, ids=[p[0] for p in POSITIVES])
def test_handbuilt_dehydration_is_vouched_and_witnessed(label, precursor, target):
    step = _dehydration_step(precursor, target)
    assert recognize_reaction_type(step) == DEHYDRATION_CLASS
    assert _fired(step) == [DEHYDRATION_CLASS]                       # exactly one recognizer claims it
    assert classify_event(step) is EventType.INTRAMOLECULAR_COPRODUCT
    res = witnesses_dehydration(P(precursor), P(target))
    assert res.is_dehydration, res.note


@pytest.mark.parametrize("label,precursor,target", POSITIVES, ids=[p[0] for p in POSITIVES])
def test_the_generator_derives_the_same_precursor(label, precursor, target):
    want = resonance_identity(P(precursor))
    edges = retro_dehydration_edges(P(target))
    assert want in {resonance_identity(e.products[0]) for e in edges}
    gen_step = ExperimentStep.from_transform(next(e for e in edges if resonance_identity(e.products[0]) == want))
    assert recognize_reaction_type(gen_step) == DEHYDRATION_CLASS


def test_both_regiochemistries_are_derivable_with_no_selectivity_claim():
    # forward: 2-butanol reaches BOTH 1-butene and 2-butene; retro: 1-butene comes from BOTH 1- and 2-butanol.
    forward = {resonance_identity(m) for m in _forward_dehydrations(P("CCC(C)O"))}
    assert forward == {resonance_identity(P("C=CCC")), resonance_identity(P("CC=CC"))}
    retro = {resonance_identity(e.products[0]) for e in retro_dehydration_edges(P("C=CCC"))}
    assert retro == {resonance_identity(P("CCCCO")), resonance_identity(P("CCC(C)O"))}
    # the two products of one alcohol are recognised identically: no ranking, no preferred isomer.
    assert recognize_reaction_type(_dehydration_step("CCC(C)O", "C=CCC")) == \
        recognize_reaction_type(_dehydration_step("CCC(C)O", "CC=CC")) == DEHYDRATION_CLASS
    # and the edge carries no selectivity field at all.
    assert [f.name for f in dataclasses.fields(DehydrationEdge)] == \
        ["schema_version", "reactant", "products", "reagents", "reaction_class"]


def test_the_registry_entry_names_the_class_the_generator_stamps():
    assert _RECOGNIZERS[-1] == (DEHYDRATION_CLASS, _dehydration)
    assert len(_RECOGNIZERS) == 26


# -- adversarial -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,reactants,products", ADVERSARIAL_STEPS, ids=[a[0] for a in ADVERSARIAL_STEPS])
def test_adversarial_step_abstains(label, reactants, products):
    step = _step(reactants, products)
    assert _dehydration(step) is False
    outcome = recognize_reaction_type_outcome(step)
    assert outcome.kind == ABSTAIN, (label, outcome)


@pytest.mark.parametrize("label,reactants,products", ADVERSARIAL_STEPS, ids=[a[0] for a in ADVERSARIAL_STEPS])
def test_the_witness_also_rejects_every_adversary(label, reactants, products):
    res = witnesses_dehydration(P(reactants[0]), P(products[0]))
    assert not res.is_dehydration, label


@pytest.mark.parametrize("label,reactants,products", ADVERSARIAL_STEPS, ids=[a[0] for a in ADVERSARIAL_STEPS])
def test_the_generator_never_emits_an_adversarial_precursor(label, reactants, products):
    bad = resonance_identity(P(reactants[0]))
    assert bad not in {resonance_identity(e.products[0]) for e in retro_dehydration_edges(P(products[0]))}


def test_the_retro_from_benzene_and_allene_is_empty_but_exhaustive():
    for smi in ("c1ccccc1", "C=C=C", "C1=CC1", "C=CO"):
        enum = retro_dehydration_enumeration(P(smi))
        assert enum.edges == () and enum.exhaustive, smi


def test_a_fabricated_same_formula_precursor_is_refused_by_the_edge_certificate():
    # dimethyl ether has ethanol's formula, so conservation passes -- the re-derivation is what refuses it.
    with pytest.raises(EliminationError):
        DehydrationEdge(DEHYDRATION_SCHEMA, P("C=C"), (P("COC"),), (P("O"),), DEHYDRATION_CLASS)


# -- exactly one recognizer, in both directions ----------------------------------------------------------------------

#: genuine steps of OTHER classes: the dehydration recognizer must claim none of them.
OTHER_CLASS_STEPS = [
    ("lactonization", ("OCCCC(=O)O",), ("O=C1CCCO1", WATER)),
    ("Fischer esterification", ("CC(=O)O", "CCO"), ("CC(=O)OCC", WATER)),
    ("etherification", ("CO", "CO"), ("COC", WATER)),
    ("Diels-Alder", ("C=CC=C", "C=C"), ("C1CCC=CC1",)),
    ("hydrogenation", ("C=C", "[H][H]"), ("CC",)),
    ("imine condensation", ("CC(C)=O", "CN"), ("CN=C(C)C", WATER)),
]


@pytest.mark.parametrize("label,reactants,products", OTHER_CLASS_STEPS, ids=[o[0] for o in OTHER_CLASS_STEPS])
def test_dehydration_claims_no_other_class_step(label, reactants, products):
    step = _step(reactants, products)
    assert _dehydration(step) is False
    assert recognize_reaction_type(step) != DEHYDRATION_CLASS


def test_dehydration_claims_no_lateral_step():
    step = ExperimentStep.from_transform(rewrite_edges(ELECTRO_6PI, P("C1=CCCC=C1"))[0], envelope=None)
    assert _dehydration(step) is False


# -- conservation ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,precursor,target", POSITIVES, ids=[p[0] for p in POSITIVES])
def test_precursor_formula_is_target_plus_water(label, precursor, target):
    total = Counter(P(target).formula) + Counter({"H": 2, "O": 1})
    assert Counter(P(precursor).formula) == total


def test_a_nonconserving_dehydration_step_is_refused():
    with pytest.raises(StepError):
        _step(("CCO",), ("C=C",))                       # the water is missing


# -- the activator ledger: acid catalyst required --------------------------------------------------------------------

def test_dehydration_without_a_catalyst_is_demoted_naming_the_role():
    (reason,) = step_activator_blockers(_dehydration_step("OC1CCCCC1", "C1=CCCCC1"))
    assert DEHYDRATION_CLASS in reason and "acid dehydration catalyst" in reason
    assert "REAL-BUT-HARD" in reason and "NOT a claim of" in reason


@pytest.mark.parametrize("acid", ["H2SO4", "conc. H2SO4", "sulfuric acid", "concentrated sulfuric acid", "H3PO4",
                                  "phosphoric acid", "TsOH", "p-toluenesulfonic acid", "KHSO4", "alumina", "Al2O3"])
def test_a_whitelisted_acid_catalyst_clears_the_requirement(acid):
    assert ActivatorRole.ACID_DEHYDRATION_CATALYST in classify_activator_roles(acid)
    assert step_activator_blockers(_dehydration_step("OC1CCCCC1", "C1=CCCCC1", catalysts=(acid,))) == ()


@pytest.mark.parametrize("other", ["hydrochloric acid", "HCl", "nitric acid", "acetic acid", "acid", "NaOH",
                                   "sodium ethoxide", "Pd/C", "POCl3"])
def test_an_unlisted_reagent_leaves_the_step_blocked(other):
    assert len(step_activator_blockers(_dehydration_step("OC1CCCCC1", "C1=CCCCC1", catalysts=(other,)))) == 1


def test_the_acid_role_never_clears_another_classes_requirement():
    for acid in ("H2SO4", "TsOH", "alumina"):
        roles = classify_activator_roles(acid)
        assert roles == frozenset({ActivatorRole.ACID_DEHYDRATION_CATALYST}), acid


def test_the_demotion_is_real_but_hard_not_fiction():
    route = ExperimentRoute.of(_dehydration_step("CCO", "C=C"))
    assert route_reaction_type_blockers(route) == ()        # type-valid: no NOT_A_REACTION blocker
    assert len(route_activator_blockers(route)) == 1         # the activator blocker rides hard_blockers
