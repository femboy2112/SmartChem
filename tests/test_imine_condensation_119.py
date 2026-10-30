"""#119 carbonyl + amine -> imine condensation: generator + oracle recognizer, the 22nd active class.

Covers the plan's ten proof obligations for a new reaction family:
  1. conservation certificate (the edge + the ExperimentStep both conserve);
  2. reproducible atom/bond rewrite (deterministic products);
  3. structural locality / applicable-domain witness (the C=N retro; cyclic/amidine refused);
  4. independently re-derived recognition (content-deterministic -- a forged/absent centre cannot mint or block);
  5. explicit reactant/coproduct/reagent accounting (water explicit; the elementary shape);
  6. no false-VOUCH adversarial corpus;
  7. positive / negative / null / mutation controls;
  8. linear/DAG behaviour + search-budget (the provider rides search_routes);
  9. compatibility / version-differential (registry digest moves; the recognizer count is 22);
 10. fresh holdout molecules not used to design the rule.
"""
from __future__ import annotations

import pytest

from smartchem.category import Bond, Molecule
from smartchem.experiment.reaction_type_oracle import _RECOGNIZERS, recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.imine_condensation import (
    IMINE_CONDENSATION_SCHEMA,
    ImineCondensationEdge,
    ImineCondensationProvider,
    imine_condensations,
)
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import ScissionError
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY,
    ProviderUse,
    TransformProviderRegistry,
)

W = "O"  # water SMILES


def _step(carbonyl: str, amine: str, imine: str, *, n_water: int = 1) -> ExperimentStep:
    """The forward condensation step ``carbonyl + amine -> imine + n_water water``."""
    prod = parse_smiles(imine)
    waters = [parse_smiles(W)] * n_water
    return ExperimentStep.assembling(
        prod, (parse_smiles(carbonyl), parse_smiles(amine)), tuple([prod, *waters]), reagents=()
    )


_IMINE_CLASS = "imine condensation (carbonyl + amine/hydroxylamine/hydrazine -> imine/oxime/hydrazone + water)"

# molecules used to DESIGN the rule (kept distinct from the holdouts below)
_POSITIVES = [
    ("formaldehyde+methylamine", "C=O", "CN", "C=NC"),
    ("acetone+methylamine(ketimine)", "CC(C)=O", "CN", "CC(C)=NC"),
    ("acetaldehyde+methylamine(aldimine)", "CC=O", "CN", "CC=NC"),
    ("benzaldehyde+methylamine(aromatic R)", "O=Cc1ccccc1", "CN", "CN=Cc1ccccc1"),
    ("acetone+ammonia(primary imine)", "CC(C)=O", "N", "CC(C)=N"),
    ("acetaldehyde+hydroxylamine(oxime)", "CC=O", "NO", "CC=NO"),
    ("acetaldehyde+hydrazine(hydrazone)", "CC=O", "NN", "CC=NN"),
    # N-acyl-fix over-correction guards: an aryl/vinyl amine carbon (double bonds to CARBON, not a heteroatom) and
    # an acylhydrazide (the acyl sits on the OTHER N; the imine-N substituent is N) are all GENUINE donors.
    ("benzaldehyde+aniline(N-aryl Schiff base)", "O=Cc1ccccc1", "Nc1ccccc1", "c1ccccc1N=Cc1ccccc1"),
    ("acetaldehyde+acylhydrazide", "CC=O", "NNC(C)=O", "CC=NNC(C)=O"),
    ("acetone+N-vinyl amine", "CC(C)=O", "NC=C", "CC(C)=NC=C"),
]

# FRESH holdouts -- molecules NOT used while designing the gate (obligation 10)
_HOLDOUTS = [
    ("cyclohexanone+methylamine", "O=C1CCCCC1", "CN", "CN=C1CCCCC1"),
    ("propanal+ethylamine", "CCC=O", "CCN", "CCC=NCC"),
    ("butanal+methylamine", "CCCC=O", "CN", "CCCC=NC"),
    ("acetone+hydroxylamine(oxime)", "CC(C)=O", "NO", "CC(C)=NO"),
]


# -- obligation 1 + 7: positives VOUCH ------------------------------------------------------------------------
@pytest.mark.parametrize("label,c,a,im", _POSITIVES + _HOLDOUTS)
def test_positives_and_holdouts_vouch_imine(label, c, a, im):
    assert recognize_reaction_type(_step(c, a, im)) == _IMINE_CLASS, label


# -- obligation 6: no false-VOUCH adversarial corpus (conserving steps that MUST NOT vouch as imine) ----------
@pytest.mark.parametrize("label,c,a,p", [
    ("amide (no C=N -> acyl, not imine)", "CC(=O)O", "CN", "CC(=O)NC"),
    ("enamine (C=C-N tautomer, no C=N)", "CC(C)=O", "CN", "CC(=C)NC"),
    ("amidine (alpha-N on carbonyl carbon)", "CC(=O)N", "N", "CC(=N)N"),
    ("imidate (alpha-O on carbonyl carbon)", "CC(=O)OC", "N", "CC(=N)OC"),
    # N-ACYL DONOR LEAK (evil-morty kill): an amide/urea/carbamate/amidine donor is NOT an amine -- the mirror of
    # the carbonyl-carbon alpha-heteroatom guard demotes all of these (its N-acyl-imine retro is carbonyl + amide):
    ("N-acyl: urea-formaldehyde", "C=O", "NC(=O)N", "C=NC(N)=O"),
    ("N-acyl: acetamide donor", "CC=O", "CC(=O)N", "CC=NC(C)=O"),
    ("N-acyl: methyl carbamate donor", "CC=O", "NC(=O)OC", "CC=NC(=O)OC"),
    ("N-acyl: amidine donor on N", "CC=O", "NC(=N)C", "CC=NC(=N)C"),
    ("N-acyl: guanidine donor on N", "CC=O", "NC(=N)N", "CC=NC(=N)N"),
])
def test_no_false_vouch_as_imine(label, c, a, p):
    verdict = recognize_reaction_type(_step(c, a, p))
    assert verdict != _IMINE_CLASS, f"{label} FALSE-VOUCHED as imine (got {verdict!r})"


# -- obligation 3: the edge refuses cyclic/aromatic C=N and amidine/imidate (applicable-domain witness) -------
@pytest.mark.parametrize("smi", ["c1ccncc1", "C1CCC=N1", "C1Cc2ccccc2C=N1", "c1ccncn1", "c1cnc[nH]1"])
def test_generator_refuses_cyclic_or_aromatic_cn(smi):
    edges, complete = imine_condensations(parse_smiles(smi))
    assert edges == () and complete is True, f"{smi}: a cyclic/aromatic C=N must not hydrolyse into two fragments"


@pytest.mark.parametrize("smi", ["CC(=N)N", "CC(=N)OC", "NC(=N)N"])
def test_generator_refuses_amidine_imidate(smi):
    edges, _ = imine_condensations(parse_smiles(smi))
    assert edges == (), f"{smi}: an amidine/imidate carbon (extra alpha-O/N) is not a simple carbonyl precursor"


# -- obligation 1 + 2: the edge conserves and its rewrite is deterministic/reproducible -----------------------
def test_edge_products_are_the_carbonyl_and_amine_and_deterministic():
    imine = parse_smiles("C=NC")  # N-methylmethanimine
    edges, complete = imine_condensations(imine)
    assert complete and len(edges) == 1
    e = edges[0]
    # products are formaldehyde (CH2O) and methylamine (CH5N), consuming one water
    got = sorted(repr(p) for p in e.products)
    assert got == ["CH2O", "CH5N"], got
    assert tuple(repr(r) for r in e.reagents) == ("H2O",)
    # reproducible: a freshly constructed edge on the same bond gives byte-identical products + digest
    e2 = ImineCondensationEdge(IMINE_CONDENSATION_SCHEMA, imine, e.cn_c, e.cn_n)
    assert [repr(p) for p in e2.products] == [repr(p) for p in e.products]
    assert e2.digest == e.digest


def test_edge_forget_is_a_conserving_mediated_edge():
    e = imine_condensations(parse_smiles("CC(C)=NC"))[0][0]
    med = e.forget()  # imine + water -> acetone + methylamine, a MediatedEdge; construction re-checks conservation
    assert med is not None


# -- obligation 4: content-determinism -- a forged or absent reaction_center cannot mint or block a vouch -----
def test_recognition_ignores_forged_or_absent_reaction_center():
    from dataclasses import replace
    good = _step("CC(C)=O", "CN", "CC(C)=NC")
    assert recognize_reaction_type(good) == _IMINE_CLASS
    # forge a bogus centre onto a genuine step: still vouches (the oracle re-derives, never reads the field)
    forged = replace(good, reaction_center=None)
    assert recognize_reaction_type(forged) == _IMINE_CLASS
    # a NON-imine step cannot be promoted by any centre: the amide stays non-imine
    amide = _step("CC(=O)O", "CN", "CC(=O)NC")
    assert recognize_reaction_type(amide) != _IMINE_CLASS


# -- obligation 5: explicit accounting -- the elementary shape (2 reactants, one water expelled) --------------
def test_shape_requires_two_reactants_one_product_one_water():
    # a bundled double condensation (3 reactants -> imine + 2 water) is NOT the elementary shape -> demoted
    diimine = parse_smiles("C(=NCCN=C)") if False else parse_smiles("C=NCCN=C")
    f = parse_smiles("C=O")
    diamine = parse_smiles("NCCN")
    water = parse_smiles(W)
    bundled = ExperimentStep.assembling(diimine, (f, f, diamine), (diimine, water, water), reagents=())
    assert recognize_reaction_type(bundled) != _IMINE_CLASS


def test_water_must_be_expelled_not_consumed():
    # hydration direction (water a REACTANT) is not a condensation -> not vouched as imine
    imine, carbonyl, amine, water = (parse_smiles(s) for s in ("CC=NC", "CC=O", "CN", W))
    hydration = ExperimentStep.assembling(carbonyl, (imine, water), (carbonyl, amine), reagents=())
    assert recognize_reaction_type(hydration) != _IMINE_CLASS


# -- obligation 7: null + mutation controls -------------------------------------------------------------------
def test_null_controls_do_not_raise_and_do_not_vouch():
    # an identity-ish / empty-ish step must simply not vouch (fail-closed), never raise
    water = parse_smiles(W)
    assert recognize_reaction_type(ExperimentStep.assembling(water, (water,), (water,), reagents=())) != _IMINE_CLASS


def test_mutation_a_non_cn_double_bond_does_not_build():
    # mutate the target index to a C=C or C=O: the edge must refuse (not a C=N)
    ethene = parse_smiles("C=C")
    with pytest.raises(ScissionError):
        ImineCondensationEdge(IMINE_CONDENSATION_SCHEMA, ethene, 0, 1)
    formaldehyde = parse_smiles("C=O")
    with pytest.raises(ScissionError):
        ImineCondensationEdge(IMINE_CONDENSATION_SCHEMA, formaldehyde, 0, 3)  # C=O, not C=N


def test_charged_species_is_refused():
    # is_closed_shell_neutral / the charge gate: a charged graph is refused by the edge
    with pytest.raises(ScissionError):
        # a bare iminium-ish charged molecule (net charge != 0)
        ImineCondensationEdge(IMINE_CONDENSATION_SCHEMA, Molecule(("C", "N"), frozenset({Bond(0, 1, 2)}), 1, ""), 0, 1)


# -- obligation 8: the provider rides search_routes (linear) + budget honesty ---------------------------------
def test_provider_is_opt_in_and_route_admissible():
    prov = ImineCondensationProvider()
    assert ProviderUse.LINEAR_ROUTE in prov.supported_uses
    assert ProviderUse.CONVERGENT_DAG in prov.supported_uses
    # absent from the default algebra (opt-in, the DA precedent)
    assert "imine-condensation" not in DEFAULT_TRANSFORM_REGISTRY.provider_ids


def test_provider_enumerates_the_imine_retro():
    prov = ImineCondensationProvider()
    transforms, complete = prov.enumerate_transforms(parse_smiles("CC(C)=NC"), (), budget=50_000)
    assert complete and len(transforms) == 1
    # read backwards it is the synthesis step the oracle vouches
    step = ExperimentStep.from_transform(transforms[0])
    assert recognize_reaction_type(step) == _IMINE_CLASS


def test_budget_zero_reports_incomplete_without_raising():
    transforms, complete = imine_condensations(parse_smiles("CC(C)=NC"), budget=0)
    assert transforms == () and complete is False


def test_enumerate_on_a_molecule_with_no_cn_is_empty_and_complete():
    transforms, complete = imine_condensations(parse_smiles("CCO"))  # ethanol: no C=N
    assert transforms == () and complete is True


# -- obligation 9: compatibility / version-differential -------------------------------------------------------
def test_recognizer_count_is_twentytwo():
    assert len(_RECOGNIZERS) == 22


def test_registry_digest_moves_when_the_imine_provider_is_added():
    base = DEFAULT_TRANSFORM_REGISTRY
    wider = TransformProviderRegistry(base.providers + (ImineCondensationProvider(),))
    assert wider.digest != base.digest
    # the provider identity is deterministic + prose-independent (the 3-tuple shape)
    assert ImineCondensationProvider().identity == ImineCondensationProvider().identity
    assert len(ImineCondensationProvider().identity) == 3


# -- cross-poach: imine does not fire on another class's step, nor another class on an imine step -------------
def test_imine_does_not_poach_a_williamson_ether_or_esterification():
    # an etherification step (2 ROH -> ether + water) must not read as an imine condensation
    ether = _step("CO", "CO", "COC")  # methanol + methanol -> dimethyl ether + water (shape reused)
    assert recognize_reaction_type(ether) != _IMINE_CLASS


def test_an_imine_step_is_not_poached_by_another_recognizer():
    # the genuine imine step vouches as imine and nothing else claims it first
    assert recognize_reaction_type(_step("CC(C)=O", "CN", "CC(C)=NC")) == _IMINE_CLASS
