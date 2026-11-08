"""#116 -- the FIFTH blind attack's corpus, committed so the 1.7.0 deferral is reproducible from the repository.

These assertions pin a DEFECT, not a feature.  On the deferred candidate (fourth implementation ``8796ee3``) every
KNOWN_FALSE_VOUCH case below is vouched end to end under a declared conc. H2SO4: the production recognizer
(``_dehydrates_to``), the independent witness, the reaction-type oracle and the activator ledger (no blocker) all
agree, so the step reads as runnable although acid sends the substrate somewhere else.  That common-mode false VOUCH
inside the declared domain is what triggered the stopping rule (``docs/research/V1_7_DEHYDRATION_DEFER.md`` section 3,
attack 5).

A successor design must REFUSE every KNOWN_FALSE_VOUCH case (and keep the control vouched).  When it does, flip these
assertions; do not edit the corpus to make a failure go away -- a failure here means the recognizer changed, so the
attack corpora must be replayed and a fresh adversary run.

SUSPECTED_OPEN cases are recorded, not confirmed: whether the dehydration beats the competing acid chemistry
(decarboxylation, nitrile hydration) depends on temperature, which the class does not model.
"""
from __future__ import annotations

import dataclasses

import pytest

from smartchem.conditions import ConditionEnvelope, EvidenceStatus
from smartchem.elimination import DEHYDRATION_CLASS, _dehydrates_to
from smartchem.elimination_witness import witnesses_dehydration
from smartchem.experiment.activator_ledger import step_activator_blockers
from smartchem.experiment.event_search import (
    DEHYDRATION_PRODUCER,
    LACTONIZATION_PRODUCER,
    search_event_routes,
)
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles as P

WATER = "O"

#: (label, precursor, vouched alkene, the competing acid channel named by attack 5)
KNOWN_FALSE_VOUCH = [
    # Friedel-Crafts cyclialkylation onto the pendant arene
    ("FC: 2-methyl-4-phenylbutan-2-ol -> prenylbenzene", "CC(C)(O)CCc1ccccc1", "CC(C)=CCc1ccccc1",
     "1,1-dimethylindan"),
    ("FC: 2-methyl-4-phenylbutan-2-ol -> 2-methyl-4-phenylbut-1-ene", "CC(C)(O)CCc1ccccc1", "C=C(C)CCc1ccccc1",
     "1,1-dimethylindan"),
    ("FC: 2-methyl-5-phenylpentan-2-ol -> 2-methyl-5-phenylpent-2-ene", "CC(C)(O)CCCc1ccccc1", "CC(C)=CCCc1ccccc1",
     "1,1-dimethyltetralin"),
    ("FC: 4-phenylbutan-2-ol -> 1-phenylbut-2-ene", "CC(O)CCc1ccccc1", "CC=CCc1ccccc1", "1-methylindan"),
    ("FC: 5-phenylpentan-2-ol -> 5-phenylpent-2-ene", "CC(O)CCCc1ccccc1", "CC=CCCc1ccccc1", "1-methyltetralin"),
    # Nazarov / indanone cyclisation of the vouched dienone or aryl vinyl ketone
    ("Nazarov: 5-hydroxy-2-methylhex-1-en-3-one -> 2-methylhexa-1,4-dien-3-one", "C=C(C)C(=O)CC(C)O",
     "C=C(C)C(=O)C=CC", "cyclopentenone"),
    ("Nazarov: 1-(cyclohexenyl)-3-hydroxybutan-1-one -> cyclohexenyl propenyl ketone", "CC(O)CC(=O)C1=CCCCC1",
     "CC=CC(=O)C1=CCCCC1", "hydrindenone"),
    ("indanone: 3-hydroxy-1-phenylbutan-1-one -> crotonophenone", "CC(O)CC(=O)c1ccccc1", "CC=CC(=O)c1ccccc1",
     "3-methylindan-1-one"),
    # intramolecular hydroalkoxylation (the OH traps the cation of its own alkene; cf. butane-1,4-diol -> THF)
    ("hydroalkoxylation: 4-methylpent-4-en-1-ol -> 4-methylpenta-1,4-diene", "OCCCC(C)=C", "C=CCC(C)=C",
     "2,2-dimethyltetrahydrofuran"),
    ("hydroalkoxylation: 5-methylhex-4-en-1-ol -> 5-methylhexa-1,4-diene", "OCCCC=C(C)C", "C=CCC=C(C)C",
     "2,2-dimethyltetrahydropyran"),
    ("hydroalkoxylation: sulcatol -> 6-methylhepta-1,5-diene", "CC(O)CCC=C(C)C", "C=CCCC=C(C)C",
     "2,2,6-trimethyltetrahydropyran"),
    ("hydroalkoxylation: sulcatol -> 2-methylhepta-2,5-diene", "CC(O)CCC=C(C)C", "CC=CCC=C(C)C",
     "2,2,6-trimethyltetrahydropyran"),
    # aromatic-tautomer ring at radius 2 (acid aromatises it)
    ("radius-2 p-isotoluene", "CC(C)(O)CCC1C=CC(=C)C=C1", "CC(C)=CCC1C=CC(=C)C=C1", "aromatised arene"),
    ("radius-2 o-isotoluene", "CC(C)(O)CCC1C=CC=CC1=C", "CC(C)=CCC1C=CC=CC1=C", "aromatised arene"),
    ("radius-2 semibenzene", "CC(C)(O)CCC1(C)C=CC(=C)C=C1", "CC(C)=CCC1(C)C=CC(=C)C=C1", "aromatised arene"),
    # acid-labile esters
    ("acid-labile: tert-butyl 3-hydroxybutanoate -> tert-butyl crotonate", "CC(O)CC(=O)OC(C)(C)C",
     "CC=CC(=O)OC(C)(C)C", "isobutene + acid"),
    ("acid-labile: vinyl 3-hydroxybutanoate -> vinyl crotonate", "CC(O)CC(=O)OC=C", "CC=CC(=O)OC=C",
     "acetaldehyde + acid"),
]

#: recorded from attack 5; the vouch is confirmed, the competing chemistry is suspected and temperature-dependent
SUSPECTED_OPEN = [
    ("beta-keto acid: 2-acetyl-3-hydroxybutanoic acid", "CC(O)C(C(C)=O)C(=O)O", "CC=C(C(C)=O)C(=O)O",
     "decarboxylation"),
    ("malonic acid: 2-(1-hydroxyethyl)malonic acid", "CC(O)C(C(=O)O)C(=O)O", "CC=C(C(=O)O)C(=O)O",
     "decarboxylation"),
    ("nitrile: 3-hydroxybutanenitrile -> crotononitrile", "CC(O)CC#N", "CC=CC#N", "hot conc. H2SO4 hydrates CN"),
]

CONTROL = ("cyclohexanol -> cyclohexene", "OC1CCCCC1", "C1=CCCCC1")


def _acid_step(pre: str, tgt: str) -> ExperimentStep:
    s = ExperimentStep.assembling(P(tgt), (P(pre),), (P(tgt), P(WATER)))
    env = ConditionEnvelope(catalysts=("conc. H2SO4",), status=EvidenceStatus.EXPERIMENTAL, provenance="attack 5")
    return dataclasses.replace(s, envelope=env)


def _vouched_end_to_end(pre: str, tgt: str) -> bool:
    s = _acid_step(pre, tgt)
    return (
        _dehydrates_to(P(pre), P(tgt))
        and witnesses_dehydration(P(pre), P(tgt)).is_dehydration
        and recognize_reaction_type(s) == DEHYDRATION_CLASS
        and step_activator_blockers(s) == ()
    )


@pytest.mark.parametrize(("label", "pre", "tgt", "acid_gives"), KNOWN_FALSE_VOUCH, ids=[c[0] for c in KNOWN_FALSE_VOUCH])
def test_attack5_known_false_vouch_reproduces(label, pre, tgt, acid_gives):
    # DEFECT PIN: the deferred candidate vouches a step that acid sends to `acid_gives`.  A successor flips this.
    assert _vouched_end_to_end(pre, tgt), label


@pytest.mark.parametrize(("label", "pre", "tgt", "competitor"), SUSPECTED_OPEN, ids=[c[0] for c in SUSPECTED_OPEN])
def test_attack5_suspected_cases_are_vouched(label, pre, tgt, competitor):
    assert _vouched_end_to_end(pre, tgt), label


def test_attack5_control_stays_vouched():
    _label, pre, tgt = CONTROL
    assert _vouched_end_to_end(pre, tgt)


@pytest.mark.parametrize(
    ("target", "stock"),
    [
        ("CC(C)=CCc1ccccc1", "CC(C)(O)CCc1ccccc1"),      # FC cyclialkylation substrate
        ("C=CCC(C)=C", "OCCCC(C)=C"),                    # hydroalkoxylation substrate
        ("C=C(C)C(=O)C=CC", "C=C(C)C(=O)CC(C)O"),        # Nazarov substrate
    ],
)
def test_attack5_false_vouch_reaches_the_public_route_search(target, stock):
    """DEFECT PIN at route level: with dehydration enabled the public search returns a COMPLETE one-step route to the
    hazard target; the default grammar (1.6.0-identical) returns none."""
    with_dehydration = search_event_routes(
        P(target), reagents=(), available=(P(stock),),
        coproduct_producers=(LACTONIZATION_PRODUCER, DEHYDRATION_PRODUCER),
    )
    assert with_dehydration.receipt.complete
    assert [len(r.steps) for r in with_dehydration.routes] == [1]
    assert recognize_reaction_type(with_dehydration.routes[0].steps[0]) == DEHYDRATION_CLASS

    default = search_event_routes(P(target), reagents=(), available=(P(stock),))
    assert default.receipt.complete
    assert default.routes == ()
