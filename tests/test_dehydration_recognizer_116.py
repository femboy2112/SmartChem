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
from smartchem.category import Molecule
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
    # r2 controls: still inside the safe set after the red-team repair
    ("cyclopentanol -> cyclopentene", "OC1CCCC1", "C1=CCCC1"),
    ("cyclooctanol -> cyclooctene", "OC1CCCCCCC1", "C1=CCCCCCC1"),
    ("cyclohex-2-en-1-ol -> 1,3-cyclohexadiene", "OC1C=CCCC1", "C1=CC=CCC1"),
    ("cyclohexylmethanol -> methylenecyclohexane", "OCC1CCCCC1", "C=C1CCCCC1"),
    ("3-hydroxybutanal -> crotonaldehyde (beta-hydroxy carbonyl, deliberately in)", "CC(O)CC=O", "CC=CC=O"),
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
    # r2 red-team: anti-Bredt (rule a)
    ("1-norbornanol -> bicyclo[2.2.1]hept-1-ene", ("OC12CCC(CC1)C2",), ("C1=C2CCC(C1)C2", WATER)),
    ("1-adamantanol -> adamantene", ("OC12CC3CC(CC(C3)C1)C2",), ("C1=C2CC3CC(CC1C3)C2", WATER)),
    ("bicyclo[1.1.1]pentan-1-ol -> bridgehead alkene", ("OC12CC(C1)C2",), ("C1=C2CC1C2", WATER)),
    ("cubanol -> cubene", ("OC12C3C4C1C5C2C3C45",), ("C12=C3C4C1C5C2C3C45", WATER)),
    # r2 red-team: rearrangement-prone under the acid the ledger demands (rules b-e)
    ("cyclobutanol -> cyclobutene", ("OC1CCC1",), ("C1=CCC1", WATER)),
    ("cyclopropylmethanol -> methylenecyclopropane", ("OCC1CC1",), ("C=C1CC1", WATER)),
    ("1-cyclopropylethanol -> vinylcyclopropane", ("CC(O)C1CC1",), ("C=CC1CC1", WATER)),
    ("pinacol -> 2,3-dimethylbut-3-en-2-ol", ("CC(C)(O)C(C)(C)O",), ("C=C(C)C(C)(C)O", WATER)),
    ("3,3-dimethylbutan-2-ol -> 3,3-dimethylbut-1-ene (quaternary neighbour)", ("CC(O)C(C)(C)C",),
     ("C=CC(C)(C)C", WATER)),
    # r2 red-team: aromatic tautomers / anhydrobase / fulvene (rule f)
    ("cyclohexa-2,5-dienylmethanol -> p-isotoluene", ("OCC1C=CCC=C1",), ("C=C1C=CCC=C1", WATER)),
    ("cyclohexa-2,4-dienylmethanol -> o-isotoluene", ("OCC1C=CC=CC1",), ("C=C1C=CC=CC1", WATER)),
    ("1,4-dihydropyridin-4-ylmethanol -> 4-picoline anhydrobase", ("OCC1C=CNC=C1",), ("C=C1C=CNC=C1", WATER)),
    ("cyclopentadienylmethanol -> fulvene", ("OCC1C=CC=C1",), ("C=C1C=CC=C1", WATER)),
    # r3 red-team: gem-disubstituted aromatisation substrates (rule f')
    ("dienone-phenol alpha-ketol -> 4,4-dimethylcyclohexa-2,5-dienone", ("OC1CC(C)(C)C=CC1=O",),
     ("CC1(C)C=CC(=O)C=C1", WATER)),
    ("semibenzene", ("CC1(O)C=CC(C)(C)C=C1",), ("C=C1C=CC(C)(C)C=C1", WATER)),
    ("semibenzene 4-Me-4-Et", ("CC1(O)C=CC(C)(CC)C=C1",), ("C=C1C=CC(C)(CC)C=C1", WATER)),
    # r3 red-team: a heteroatom within two bonds of the new C=C (rule e')
    ("beta-hydroperoxy alcohol", ("CC(O)C(C)OO",), ("C=CC(C)OO", WATER)),
    ("beta-sulfonyl alcohol", ("CC(O)CS(=O)(=O)c1ccccc1",), ("C=CCS(=O)(=O)c1ccccc1", WATER)),
    ("beta-silyl alcohol (Peterson territory)", ("CC(O)C[Si](C)(C)C",), ("C=CC[Si](C)(C)C", WATER)),
    ("beta-silyl tertiary alcohol", ("CC(C)(O)C[Si](C)(C)C",), ("C=C(C)C[Si](C)(C)C", WATER)),
    ("beta-boryl alcohol (deboronation territory)", ("CC(O)CB(O)O",), ("C=CCB(O)O", WATER)),
]

#: ACCEPTED COVERAGE LOSS (r2): real dehydrations now outside the positive safe set.  They must ABSTAIN -- pinned so a
#: later widening is a deliberate, reviewed decision rather than drift.
COVERAGE_LOSS_STEPS = [
    ("bicyclo[3.3.1]nonan-1-ol -> bicyclo[3.3.1]non-1-ene (bridgehead; rule a)", ("OC12CCCC(CCC1)C2",),
     ("C1=C2CCCC(C2)CC1", WATER)),
    ("2-norbornanol -> norbornene (bridged system; rule a)", ("OC1CC2CCC1C2",), ("C1=CC2CCC1C2", WATER)),
    ("indan-1-ol -> indene (fused system; rules a, f)", ("OC1CCc2ccccc21",), ("C1=Cc2ccccc2C1", WATER)),
    ("cyclopent-3-en-1-ol -> cyclopentadiene (rule f)", ("OC1CC=CC1",), ("C1=CCC=C1", WATER)),
    ("cyclohepta-3,5-dien-1-ol -> cycloheptatriene (rule f)", ("OC1CC=CC=CC1",), ("C1=CC=CC=CC1", WATER)),
    # r3: rule (e') -- beta-halo / beta-amino / beta-alkoxy alcohols, 1,3-diols, heteroaryl and ring-heteroatom
    # neighbours, gem-dimethyl 2H-pyrans
    ("1-bromopropan-2-ol -> allyl bromide (beta-halo; e')", ("CC(O)CBr",), ("C=CCBr", WATER)),
    ("1-chloro-2-methylpropan-2-ol -> methallyl chloride (beta-halo; e')", ("CC(C)(O)CCl",), ("C=C(C)CCl", WATER)),
    ("1-aminopropan-2-ol -> allylamine (beta-amino; e')", ("CC(O)CN",), ("C=CCN", WATER)),
    ("1-methoxypropan-2-ol -> allyl methyl ether (beta-alkoxy; e')", ("CC(O)COC",), ("C=CCOC", WATER)),
    ("propane-1,3-diol -> allyl alcohol (1,3-diol; e')", ("OCCCO",), ("C=CCO", WATER)),
    ("1-(2-pyridyl)ethanol -> 2-vinylpyridine (heteroaryl; e')", ("CC(O)c1ccccn1",), ("C=Cc1ccccn1", WATER)),
    ("1-(2-furyl)ethanol -> 2-vinylfuran (heteroaryl; e')", ("CC(O)c1ccco1",), ("C=Cc1ccco1", WATER)),
    ("tetrahydropyran-4-ol -> 3,6-dihydro-2H-pyran (ring O; e')", ("OC1CCOCC1",), ("C1=CCOCC1", WATER)),
    ("2,2-dimethyl-2H-pyran (e', f')", ("CC1(C)CC(O)C=CO1",), ("CC1(C)C=CC=CO1", WATER)),
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

@pytest.mark.parametrize("label,reactants,products", COVERAGE_LOSS_STEPS, ids=[c[0] for c in COVERAGE_LOSS_STEPS])
def test_accepted_coverage_loss_abstains_in_production_and_witness(label, reactants, products):
    step = _step(reactants, products)
    assert recognize_reaction_type_outcome(step).kind == ABSTAIN, label
    assert not witnesses_dehydration(P(reactants[0]), P(products[0])).is_dehydration, label


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


def test_safe_set_rule_attribution():
    """Each r2 rule fires on the structure it names (so an abstain is the rule, not a mis-drawn SMILES)."""
    from smartchem.elimination import _Rings, _adjacency, _aromatisable_ring

    def rings(smi):
        m = P(smi)
        return m, _Rings(m.atoms, _adjacency(m))

    m, r = rings("OC12CCC(CC1)C2")                         # 1-norbornanol: the carbinol C is a bridgehead
    carbinol = next(i for i, a in enumerate(m.atoms) if a == "C" and any(m.atoms[n] == "O" for n, _ in
                                                                           _adjacency(m)[i]))
    assert r.monocycle(carbinol) is None                   # (a)
    m, r = rings("OC1CCC1")
    ring_c = next(i for i, a in enumerate(m.atoms) if a == "C")
    assert len(r.monocycle(ring_c)) == 4                   # (b)
    m, r = rings("CC(O)C1CC1")
    assert min(r.smallest_ring_through(i) or 99 for i, a in enumerate(m.atoms) if a == "C") == 3   # (c)
    m = P("C=C1C=CCC=C1")                                   # p-isotoluene ring: one sp3 CH2 short of conjugated
    adj = _adjacency(m)
    ring = {i for i, a in enumerate(m.atoms) if a == "C" and len([n for n, _ in adj[i] if m.atoms[n] == "C"]) >= 2}
    assert _aromatisable_ring(ring, m.atoms, adj)          # (f')
    m, r = rings("C=C1C=CC(C)(C)C=C1")                     # semibenzene: the one sp3 ring atom carries no H (r3)
    adj = _adjacency(m)
    ring = next(r.monocycle(i) for i in range(len(m.atoms)) if r.monocycle(i))
    assert len(ring) == 6
    assert _aromatisable_ring(ring, m.atoms, adj)          # (f')


def test_rule_e_prime_reads_two_bonds_and_excuses_only_a_beta_carbonyl():
    from smartchem.elimination import _adjacency, _neighbourhood_is_carbon

    def site(smi):
        m = P(smi)
        adj = _adjacency(m)
        o = next(i for i, a in enumerate(m.atoms) if a == "O" and any(m.atoms[h] == "H" for h, _ in adj[i])
                 and len([n for n, _ in adj[i] if m.atoms[n] != "H"]) == 1)
        ca = next(n for n, _ in adj[o] if m.atoms[n] == "C")
        return m, adj, o, ca

    m, adj, o, ca = site("CC(O)CBr")                        # beta-bromo: Br two bonds from C_beta
    cb = next(n for n, _ in adj[ca] if m.atoms[n] == "C" and any(m.atoms[x] == "Br" for x, _ in adj[n]))
    assert not _neighbourhood_is_carbon(o, ca, cb, m.atoms, adj)
    m, adj, o, ca = site("CC(O)CC=O")                       # beta-hydroxy aldehyde: the C=O on C_beta's neighbour
    cb = next(n for n, _ in adj[ca] if m.atoms[n] == "C" and any(
        m.atoms[x] == "C" and any(m.atoms[y] == "O" for y, _ in adj[x]) for x, _ in adj[n]))
    assert _neighbourhood_is_carbon(o, ca, cb, m.atoms, adj)


def _relabel(m, idxs, label):
    atoms = list(m.atoms)
    for i in idxs:
        atoms[i] = label
    return Molecule(tuple(atoms), m.bonds)


@pytest.mark.parametrize("label", ["D", "T"])
def test_isotope_labelled_species_are_refused_everywhere(label):
    """(g): a genuine ethanol -> ethene dehydration with one H relabelled D/T, built positionally so the ONLY difference
    from a vouched step is the label -- refused by the producer, the edge, the certificate, the oracle and the
    witness."""
    from smartchem.elimination import _hydrate
    ethene = P("C=C")
    h = next(i for i, a in enumerate(ethene.atoms) if a == "H")
    target = _relabel(ethene, [h], label)
    precursor = _hydrate(target, *sorted(next((b.i, b.j) for b in target.bonds if b.order == 2)))
    assert retro_dehydration_enumeration(target).edges == ()
    assert _forward_dehydrations(precursor) == []
    with pytest.raises(EliminationError):
        DehydrationEdge(DEHYDRATION_SCHEMA, target, (precursor,), (P("O"),), DEHYDRATION_CLASS)
    step = ExperimentStep.assembling(target, (precursor,), (target, P("O")))
    assert recognize_reaction_type(step) is None
    assert not witnesses_dehydration(precursor, target).is_dehydration
    plain = _hydrate(ethene, *sorted(next((b.i, b.j) for b in ethene.bonds if b.order == 2)))
    assert recognize_reaction_type(ExperimentStep.assembling(ethene, (plain,), (ethene, P("O")))) == DEHYDRATION_CLASS


def test_a_radical_precursor_is_refused():
    radical = P("[CH2]CCC(C)O")
    assert _forward_dehydrations(radical) == []
    assert retro_dehydration_enumeration(P("[CH2]CCC=C")).edges == ()


def test_the_producer_is_fast_on_a_large_target_and_honest_about_its_budget():
    """(h): the producer certifies only the site it built, so wall time no longer scales with every hydroxyl x every
    canonicalisation.  Generous bound (measured ~0.1 s); the exhaustive flag stays honest under a site budget."""
    import time
    big = P("C" + "CCCC=C" * 8 + "C")                       # 8 C=C sites, 112 atoms, every site in the safe set
    t0 = time.perf_counter()
    cut = retro_dehydration_enumeration(big, budget=1)
    full = retro_dehydration_enumeration(big)
    assert time.perf_counter() - t0 < 20
    assert (cut.exhaustive, cut.sites_examined, cut.sites_total) == (False, 1, 8) and len(cut.edges) == 2
    assert full.exhaustive and len(full.edges) == 16
    for edge in full.edges[:2]:
        assert recognize_reaction_type(ExperimentStep.from_transform(edge)) == DEHYDRATION_CLASS


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


@pytest.mark.parametrize("acid", ["conc. H2SO4", "Conc. H2SO4", "conc H2SO4", "concentrated sulfuric acid",
                                  "conc. H3PO4", "85% phosphoric acid", "85% H3PO4", "concentrated phosphoric acid",
                                  "TsOH", "p-toluenesulfonic acid", "KHSO4", "alumina", "Al2O3"])
def test_a_whitelisted_acid_catalyst_clears_the_requirement(acid):
    assert ActivatorRole.ACID_DEHYDRATION_CATALYST in classify_activator_roles(acid)
    assert step_activator_blockers(_dehydration_step("OC1CCCCC1", "C1=CCCCC1", catalysts=(acid,))) == ()


@pytest.mark.parametrize("other", ["hydrochloric acid", "HCl", "nitric acid", "acetic acid", "acid", "NaOH",
                                   "sodium ethoxide", "Pd/C", "POCl3",
                                   # r2: an UNQUALIFIED or dilute mineral acid may be aqueous -- it must not clear
                                   "H2SO4", "sulfuric acid", "h2so4", "H3PO4", "phosphoric acid",
                                   "dilute sulfuric acid", "CONC. H2SO4"])
def test_an_unlisted_reagent_leaves_the_step_blocked(other):
    assert len(step_activator_blockers(_dehydration_step("OC1CCCCC1", "C1=CCCCC1", catalysts=(other,)))) == 1


def test_the_acid_role_never_clears_another_classes_requirement():
    for acid in ("conc. H2SO4", "TsOH", "alumina"):
        roles = classify_activator_roles(acid)
        assert roles == frozenset({ActivatorRole.ACID_DEHYDRATION_CATALYST}), acid


def test_the_demotion_is_real_but_hard_not_fiction():
    route = ExperimentRoute.of(_dehydration_step("CCO", "C=C"))
    assert route_reaction_type_blockers(route) == ()        # type-valid: no NOT_A_REACTION blocker
    assert len(route_activator_blockers(route)) == 1         # the activator blocker rides hard_blockers


def test_rule_e_prime_excuses_an_acyl_heteroatom_only_through_its_own_acyl_carbon():
    """(e') is checked per BOND: the ester O of a beta-hydroxy ester is excused because it is reached through the
    acyl carbon on C_beta; the SAME ring O reached through C_alpha's ring CH2 (a beta-hydroxy gamma-lactone) is not.
    Production's bond walk and the witness's parent-set form agree on both."""
    from smartchem.elimination import _adjacency, _neighbourhood_is_carbon
    from smartchem.elimination_witness import _graph, _radius_two_is_carbon

    def ends(smi):
        m = P(smi)
        adj = _adjacency(m)
        o = next(i for i, a in enumerate(m.atoms) if a == "O" and len(adj[i]) == 2
                 and sum(m.atoms[h] == "H" for h, _ in adj[i]) == 1)
        ca = next(n for n, _ in adj[o] if m.atoms[n] == "C")
        return m, adj, o, ca

    # ethyl 3-hydroxybutanoate: C_beta = the CH2 next to C(=O)OEt -- excused through the acyl carbon
    m, adj, o, ca = ends("CCOC(=O)CC(C)O")
    cb = next(n for n, _ in adj[ca] if any(m.atoms[x] == "C" and any(m.atoms[y] == "O" for y, _ in adj[x])
                                           for x, _ in adj[n] if x != ca))
    assert _neighbourhood_is_carbon(o, ca, cb, m.atoms, adj)
    # beta-hydroxy gamma-lactone, OH on C4: ring O1 is two bonds from C_alpha via C5 -- NOT excused (it is also reached
    # through the acyl C2 on C_beta = C3, which must not launder the C5 path)
    m, adj, o, ca = ends("O=C1OCC(O)C1")
    cb = next(n for n, _ in adj[ca] if m.atoms[n] == "C" and any(
        m.atoms[x] == "C" and any(m.atoms[y] == "O" and order == 2 for y, order in adj[x]) for x, _ in adj[n]))
    assert not _neighbourhood_is_carbon(o, ca, cb, m.atoms, adj)
    # witness, on the TARGETS: the butenolide's ring O is at distance 2 via C5 (a non-acyl parent) -> refused; the
    # unsaturated ester's alkoxy O is reached only through the acyl carbon -> excused
    def alkene_ends(smi):
        t = P(smi)
        g = _graph(t)
        b = next(b for b in t.bonds if b.order == 2 and t.atoms[b.i] == "C" and t.atoms[b.j] == "C")

        def on_acyl(c):
            return any(t.atoms[x] == "C" and any(t.atoms[y] == "O" and g[x][y] == 2 for y in g[x]) for x in g[c])
        c_h = b.i if on_acyl(b.i) else b.j
        c_oh = b.j if c_h == b.i else b.i
        assert on_acyl(c_h) and not on_acyl(c_oh)
        return t, g, c_oh, c_h

    t, g, c_oh, c_h = alkene_ends("O=C1OCC=C1")
    assert not _radius_two_is_carbon(t.atoms, g, c_oh, c_h)
    t, g, c_oh, c_h = alkene_ends("CCOC(=O)C=CC")
    assert _radius_two_is_carbon(t.atoms, g, c_oh, c_h)


@pytest.mark.parametrize("target,distinct", [("C=Cc1cccc(C=C)c1", 2), ("C=Cc1ccc(C=C)cc1", 2),
                                             ("C=Cc1ccccc1C=C", 2), ("C=CC(C)C=C", 2)])
def test_the_producer_never_emits_one_precursor_twice(target, distinct):
    """I-C: the same precursor is never counted as two independent supplies.  meta-divinylbenzene's two vinyl
    hydrations give ONE compound in two Kekule spellings; a bond-order-aware prefilter emitted both (4 edges, 2
    compounds).  The connectivity-only key keeps the resonance-identity dedup exact."""
    from smartchem.smiles import resonance_identity
    edges = retro_dehydration_enumeration(P(target)).edges
    ids = [resonance_identity(e.products[0]) for e in edges]
    assert len(ids) == len(set(ids)) == distinct
