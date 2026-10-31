"""OPERATION XII P2 -- the type-3 INTRAMOLECULAR_COPRODUCT event's first real producer (lactonization).

The load-bearing soundness pins:

* the generator produces a STRUCTURALLY VALID type-3 event: a hydroxy-acid precursor (larger, one connected
  molecule) -> lactone target + water, which ``classify_event`` classifies ``INTRAMOLECULAR_COPRODUCT``;
* INTRAMOLECULARITY is proven AT THE GENERATOR (the P1 hard constraint): it only opens IN-RING ester linkages, so the
  precursor stays one connected molecule and the forward condensation closes a bond within it -- the generator can
  NEVER emit an intermolecular 1->many fragmentation (a retro-Diels-Alder has the identical type-3 SHAPE but no ester
  ring to open, so zero edges);
* the RE-DERIVATION certificate is load-bearing: conservation alone proves nothing (a same-formula isomer balances
  mass yet is refused because it does not lactonize to the target);
* RECOGNITION vs REACHABILITY: the generator is a reachability producer; the 24-class oracle (which has no
  lactonization recognizer) honestly DEMOTES the step as unrecognized rather than false-vouching it -- standalone,
  not wired into any search.
"""
from __future__ import annotations

import pytest

from smartchem.category import Config
from smartchem.experiment.event_search import EventType, classify_event
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.step import ExperimentStep
from smartchem.intramolecular_condensation import (
    INTRAMOLECULAR_CONDENSATION_SCHEMA,
    LACTONIZATION_CLASS,
    IntramolecularCondensationEdge,
    IntramolecularCondensationError,
    LactonizationEnumeration,
    _WATER,
    retro_lactonization_edges,
    retro_lactonization_enumeration,
)
from smartchem.smiles import parse_smiles

GBL = parse_smiles("O=C1CCCO1")      # gamma-butyrolactone (5-membered cyclic ester)


def _only_step(target):
    edges = retro_lactonization_edges(target)
    assert len(edges) == 1, f"expected one lactonization edge, got {len(edges)}"
    return ExperimentStep.from_transform(edges[0])


def test_lactonization_generator_produces_a_type3_event():
    step = _only_step(GBL)
    assert classify_event(step) is EventType.INTRAMOLECULAR_COPRODUCT
    # one connected larger precursor -> target + a water coproduct (the certified type-3 shape)
    assert len(step.reactants) == 1
    assert len(step.reactants[0].atoms) > len(step.target.atoms)
    assert Config.of(*step.byproducts) == Config.of(_WATER)


@pytest.mark.parametrize("smiles", [
    "O=C1CCO1", "O=C1CCCO1", "O=C1CCCCO1",   # beta / gamma / delta lactones
    "O=C1OCC(=O)OC1",                          # glycolide (dilactone)
    "O=c1ccc2ccccc2o1",                        # coumarin (aromatic lactone)
    "O=C1OCC(O)C(O)C1O",                       # a polyol lactone (gluconolactone-shaped)
])
def test_generator_covers_lactones_of_several_shapes(smiles):
    step = _only_step(parse_smiles(smiles))
    assert classify_event(step) is EventType.INTRAMOLECULAR_COPRODUCT
    assert len(step.reactants[0].atoms) > len(step.target.atoms)


def test_polyol_lactone_is_not_dropped_by_formula_dedup():
    """REGRESSION (evil-morty P2 residual, root-caused): a polyol lactone's hydroxy-acid precursor reaches SEVERAL
    same-formula lactones under the forward re-derivation.  Deduping by ``repr()`` (which is the FORMULA string)
    collapsed them and discarded the genuine target -> a false negative.  Deduping by structural identity keeps it."""
    assert len(retro_lactonization_edges(parse_smiles("O=C1OCC(O)C(O)C1O"))) == 1


def test_acyclic_ester_yields_no_edge():
    # methyl acetate's ester bond is NOT on a ring -- opening it would fragment the molecule, so it is no
    # intramolecular lactonization and the generator emits nothing (fail-closed).
    assert retro_lactonization_edges(parse_smiles("CC(=O)OC")) == ()


@pytest.mark.parametrize("name,smiles", [
    ("succinic anhydride", "O=C1CCC(=O)O1"),      # cyclic ANHYDRIDE: acyl bridge O's far atom is a 2nd carbonyl C
    ("glutaric anhydride", "O=C1CCCC(=O)O1"),
    ("maleic anhydride", "O=C1C=CC(=O)O1"),
    ("ethylene carbonate", "O=C1OCCO1"),          # cyclic CARBONATE: acyl C bears a 2nd single-bonded O
    ("oxazolidinone", "O=C1OCCN1"),               # cyclic CARBAMATE: acyl C bears an N
])
def test_non_lactone_acyl_rings_are_rejected(name, smiles):
    """The lactone guard (evil-morty P2 review): the acyl carbon must bear EXACTLY ONE heteroatom besides its =O, so
    an anhydride / carbonate / carbamate ring is NOT opened and mislabeled 'intramolecular-lactonization'.  Each of
    these is a genuine intramolecular condensation of a DIFFERENT family whose precursor is NOT a hydroxy acid, so
    the generator -- which claims hydroxy-acid -> lactone -- correctly emits nothing (fail-closed to a true claim)."""
    assert retro_lactonization_edges(parse_smiles(smiles)) == ()


def test_diacid_precursor_is_refused_by_rederivation():
    """CLAIM-3 regression (evil-morty broke the pre-fix version): a DIACID is not a hydroxy acid, and succinic acid
    -> succinic anhydride is anhydride formation, not lactonization.  A hand-built edge with a diacid 'precursor'
    (which balances mass and is one connected molecule) must be REFUSED -- the re-derivation no longer reads a
    carboxyl -OH as an alcohol, so the diacid reaches no lactonization of the target."""
    with pytest.raises(IntramolecularCondensationError):
        IntramolecularCondensationEdge(
            INTRAMOLECULAR_CONDENSATION_SCHEMA, parse_smiles("O=C1CCC(=O)O1"),     # succinic anhydride target
            (parse_smiles("OC(=O)CCC(=O)O"),), (_WATER,), LACTONIZATION_CLASS)     # succinic ACID (a diacid)


def test_generator_structurally_cannot_emit_an_intermolecular_fragmentation():
    """THE P1 HARD CONSTRAINT, discharged at the generator: a retro-Diels-Alder (cyclohexene -> butadiene + ethylene)
    has the IDENTICAL type-3 shape as a lactonization, but the generator only opens in-ring ESTER linkages, so a
    molecule with no ester ring yields ZERO edges -- the generator can never produce an intermolecular fragmentation,
    which is exactly the connectivity property classify_event (shape only) cannot certify."""
    assert retro_lactonization_edges(parse_smiles("C1=CCCCC1")) == ()   # cyclohexene: no ester, no edge
    # and the precursor the generator DOES produce is one connected molecule (intramolecular by construction)
    (edge,) = retro_lactonization_edges(GBL)
    assert edge.products[0].is_connected()


def test_fabricated_precursor_is_refused_by_the_rederivation_certificate():
    """Conservation alone proves NOTHING: a same-formula isomer (C4H8O3, balancing lactone + water) that does NOT
    lactonize to gamma-butyrolactone is refused -- the forward re-derivation is the load-bearing certificate."""
    fake = parse_smiles("COC(=O)CCO")             # a C4H8O3 ester-alcohol, not the GBL hydroxy-acid precursor
    assert fake.formula == parse_smiles("OCCCC(=O)O").formula   # same formula -> conservation would pass
    with pytest.raises(IntramolecularCondensationError):
        IntramolecularCondensationEdge(
            INTRAMOLECULAR_CONDENSATION_SCHEMA, GBL, (fake,), (_WATER,), LACTONIZATION_CLASS)


def test_nonwater_coproduct_is_refused():
    (edge,) = retro_lactonization_edges(GBL)
    with pytest.raises(IntramolecularCondensationError):
        IntramolecularCondensationEdge(
            INTRAMOLECULAR_CONDENSATION_SCHEMA, GBL, edge.products, (parse_smiles("O"), parse_smiles("O")),
            LACTONIZATION_CLASS)


def test_charged_or_stateful_target_yields_no_edge():
    from smartchem.category import Molecule
    charged = Molecule(GBL.atoms, GBL.bonds, charge=-1)
    assert retro_lactonization_edges(charged) == ()


def test_recognition_is_separate_from_reachability():
    """The generator is a REACHABILITY producer; the 24-class oracle has no lactonization recognizer, so it honestly
    DEMOTES the step as unrecognized (None) rather than false-vouching a structurally-valid-but-unrecognized event.
    This pins that the generator never mints recognition -- adding a recognizer is a separate, gated step."""
    step = _only_step(GBL)
    assert recognize_reaction_type(step) is None


def test_generated_step_conserves_and_round_trips_through_the_certificate():
    # the ExperimentStep certificate (an independent Reaction build) accepts the generated step: it conserves.
    step = _only_step(GBL)
    assert step.schema_version  # built without raising -> conservation re-checked and passed
    # the edge's own equation names the synthesis direction precursor -> target + water
    (edge,) = retro_lactonization_edges(GBL)
    assert "->" in edge.equation() and "H2O" in repr(edge.reagents[0].formula) or edge.reagents == (_WATER,)


# ------------------------------------------------------------------- OPERATION XIII section 9: enumeration exhaustiveness
GLYCOLIDE = parse_smiles("O=C1OCC(=O)OC1")   # a DILACTONE: two in-ring ester sites (symmetric -> one deduped edge)


def test_enumeration_reports_exhaustive_for_a_normal_lactone():
    e = retro_lactonization_enumeration(GBL)
    assert isinstance(e, LactonizationEnumeration)
    assert e.exhaustive is True
    assert e.sites_total == e.sites_examined >= 1
    # the edge tuple matches the backward-compatible helper exactly.
    assert e.edges == retro_lactonization_edges(GBL)


def test_a_truncating_budget_is_reported_not_exhaustive():
    """Glycolide has TWO candidate ring-ester sites.  budget=1 scans only one, so the enumeration is NOT exhaustive
    and its edge set is a LOWER BOUND -- the record says so (the section-9 interface debt discharged), rather than
    letting a truncated scan masquerade as complete."""
    full = retro_lactonization_enumeration(GLYCOLIDE)
    assert full.sites_total == 2 and full.exhaustive is True
    cut = retro_lactonization_enumeration(GLYCOLIDE, budget=1)
    assert cut.exhaustive is False
    assert cut.sites_examined == 1 and cut.sites_total == 2
    assert len(cut.edges) <= len(full.edges)   # a lower bound, never more than the exhaustive set


def test_empty_results_are_vacuously_exhaustive():
    # a charged target and an acyclic ester both yield no candidate sites -> empty AND exhaustive (nothing to miss).
    from smartchem.category import Molecule
    charged = Molecule(GBL.atoms, GBL.bonds, charge=-1)
    for e in (retro_lactonization_enumeration(charged),
              retro_lactonization_enumeration(parse_smiles("CC(=O)OC"))):   # methyl acetate (acyclic)
        assert e.edges == () and e.exhaustive is True and e.sites_total == 0


def test_budget_must_be_a_positive_int():
    for bad in (0, -1):
        with pytest.raises(IntramolecularCondensationError):
            retro_lactonization_enumeration(GBL, budget=bad)


def test_exhaustive_flag_invariant_is_guarded():
    # the record cannot be constructed with a flag that contradicts the site counts (checks-derived-from-subject trap
    # avoided: the flag is a real statement about coverage, enforced at construction).
    with pytest.raises(IntramolecularCondensationError):
        LactonizationEnumeration(edges=(), exhaustive=True, sites_total=2, sites_examined=1, budget=1)
    # the consistent record is accepted.
    ok = LactonizationEnumeration(edges=(), exhaustive=False, sites_total=2, sites_examined=1, budget=1)
    assert ok.exhaustive is False


def test_backward_compatibility_of_the_edge_tuple_helper():
    # the original tuple API is unchanged for every shipped case.
    for smi in ("O=C1CCCO1", "O=C1CCO1", "O=C1CCCCO1", "O=C1OCC(=O)OC1", "O=c1ccc2ccccc2o1", "O=C1OCC(O)C(O)C1O"):
        assert retro_lactonization_edges(parse_smiles(smi)) == \
            retro_lactonization_enumeration(parse_smiles(smi)).edges
