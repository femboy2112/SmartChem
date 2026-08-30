"""M-4 v2 rung 2b: capped scission -- a mediated reaction DERIVED from the bond graph.

The litmus, mechanized: cut paracetamol's amide bond, split water across the two open ends, and the
closed products are -- proven by canonical graph-equality against the sourced structure registry --
4-aminophenol and acetic acid.  Not asserted, not hand-entered: derived and checked.

The claims under test:

* the derivation lands the real hydrolysis, and its products ARE the registered compounds;
* the valence-preservation certificate is non-vacuous (it rejects a rewrite that loses or invents
  valence, a duplicate-bond cap, and an unconsumed reagent);
* ``forget()`` is the bridge -- the derived rewrite becomes exactly the MediatedEdge the review layer
  already ingests, so it inherits the sourced energetics, hazards, and conditions unchanged;
* N- vs O-acetylation: the amide isomer and the ester isomer both hydrolyse to the same pair, but
  the STRUCTURE says which bond broke -- a C-N bond in one, a C-O bond in the other.
"""

from smartchem.category import Bond, Molecule
from smartchem.decompiler_mediated import MediatedEdge
from smartchem.decompiler_review import HazardFlag, screen_edge
from smartchem.decompiler_conditions import reaction_conditions
from smartchem.structure import known_compounds
from smartchem.structure_descent import CappedScission, ScissionError, capped_scissions

import pytest

# C8H9NO2 now has two registered isomers (paracetamol + the O-acetyl ester); select BY NAME, never [0]
PARACETAMOL = next(s.molecule for s in known_compounds("C8H9NO2") if s.name == "paracetamol")
WATER = Molecule(("O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2)}))
AMINOPHENOL = known_compounds("C6H7NO")[0].molecule.canonical()
ACETIC = known_compounds("C2H4O2")[0].molecule.canonical()


def _hydrolysis(reactant=PARACETAMOL):
    edges, complete = capped_scissions(reactant, (WATER,))
    assert complete
    for e in edges:
        if {p.canonical() for p in e.products} == {AMINOPHENOL, ACETIC}:
            return e
    raise AssertionError("no capped scission yielded {4-aminophenol, acetic acid}")


def _aminophenyl_acetate() -> Molecule:
    """4-aminophenyl acetate -- the O-acetyl (ester) isomer of paracetamol, C8H9NO2."""
    return Molecule(
        ("C", "C", "C", "C", "C", "C", "N", "O", "C", "O", "C",
         "H", "H", "H", "H", "H", "H", "H", "H", "H"),
        frozenset({
            Bond(0, 1, 2), Bond(1, 2, 1), Bond(2, 3, 2), Bond(3, 4, 1), Bond(4, 5, 2), Bond(5, 0, 1),
            Bond(0, 7), Bond(7, 8),                        # C0-O7-C8  (ESTER)
            Bond(3, 6), Bond(6, 11), Bond(6, 12),          # free amine
            Bond(8, 9, 2), Bond(8, 10),
            Bond(10, 13), Bond(10, 14), Bond(10, 15),
            Bond(1, 16), Bond(2, 17), Bond(4, 18), Bond(5, 19),
        }),
    )


# ======================================================================================
# The litmus: the real hydrolysis, derived and proven
# ======================================================================================
class TestParacetamolHydrolysisIsDerived:
    def test_products_are_exactly_4_aminophenol_and_acetic_acid(self):
        edge = _hydrolysis()
        assert {p.canonical() for p in edge.products} == {AMINOPHENOL, ACETIC}

    def test_the_broken_reactant_bond_is_the_amide_C_N(self):
        edge = _hydrolysis()
        # the cut incident to a reactant atom (index < 20) that is the acetyl linkage: N7-C8
        reactant_cut = [b for b in edge.cut if b.i < 20 and b.j < 20]
        assert Bond(7, 8) in reactant_cut  # the amide bond; the O-acetyl isomer would break a C-O

    def test_valence_is_preserved_everywhere(self):
        # every atom keeps its starting valence -- the certificate held at construction, re-read here
        edge = _hydrolysis()
        assert type(edge) is CappedScission  # constructed => certificate passed

    def test_the_engine_enumerates_many_rewrites_and_the_registry_picks_the_real_one(self):
        edges, _ = capped_scissions(PARACETAMOL, (WATER,))
        product_sets = {tuple(sorted(repr(p) for p in e.products)) for e in edges}
        assert len(product_sets) > 1                       # honest enumeration, not a single answer
        assert ("C2H4O2", "C6H7NO") in product_sets        # and the real hydrolysis is among them


# ======================================================================================
# The certificate bites
# ======================================================================================
class TestCappedScissionCertificate:
    def test_a_rewrite_that_loses_valence_is_rejected(self):
        # cut the amide bond but cap only ONE end: an atom is left with less valence than it started
        with pytest.raises(ScissionError):
            CappedScission(
                "smartchem.structure_descent/capped-scission-v2",
                PARACETAMOL, (WATER,),
                cut=tuple(sorted((Bond(7, 8), Bond(20, 21)))),   # amide + one water O-H
                caps=(Bond(7, 21),),                             # only one cap -> C8 and the H dangle
            )

    def test_an_unconsumed_reagent_is_rejected(self):
        # break only a reactant bond and re-form it, leaving water untouched: water passes through
        with pytest.raises(ScissionError):
            CappedScission(
                "smartchem.structure_descent/capped-scission-v2",
                PARACETAMOL, (WATER,),
                cut=(Bond(7, 8),),
                caps=(Bond(7, 8),),   # duplicate of the surviving pair anyway -> also caught
            )

    def test_products_are_all_strictly_smaller_than_the_reactant(self):
        edge = _hydrolysis()
        assert all(len(p.atoms) < len(PARACETAMOL.atoms) for p in edge.products)


# ======================================================================================
# The bridge: forget() -> MediatedEdge, straight into the existing review layer
# ======================================================================================
class TestForgetFlowsIntoReview:
    def test_forget_is_the_real_hydrolysis_mediated_edge(self):
        edge = _hydrolysis()
        med = edge.forget()
        assert type(med) is MediatedEdge
        assert med.equation() == "C8H9NO2 + H2O -> C2H4O2 + C6H7NO"

    def test_the_derived_edge_carries_sourced_hazards_and_conditions(self):
        med = _hydrolysis().forget()
        profile = screen_edge(med)
        names = {h.name for h in profile.species_hazards}
        assert {"4-aminophenol", "acetic acid"} <= names
        assert HazardFlag.DOCUMENTED_HAZARD in profile.flags
        # the sourced hydrolysis conditions attach by reaction signature -- structure -> data, wired
        env = reaction_conditions(med)
        assert env.is_declared and "aqueous" in env.medium

    def test_energetics_stay_honestly_unknown(self):
        # 4-aminophenol's sources disagree, so the derived edge is ENERGETICS_UNKNOWN, not a fake number
        profile = screen_edge(_hydrolysis().forget())
        assert HazardFlag.ENERGETICS_UNKNOWN in profile.flags


# ======================================================================================
# N- vs O-acetylation: same products, different broken bond
# ======================================================================================
class TestGeneralMultiCutCapping:
    """max_reactant_cuts > 1: two bonds cut, two reagents consumed, open valences bipartite-matched.
    A diester hydrolyses to two acids + a diol -- a reaction a single-bond cut cannot reach."""

    def _diester(self) -> Molecule:
        # ethylene glycol diformate, H-C(=O)-O-CH2-CH2-O-C(=O)-H  (C4H6O4)
        return Molecule(
            ("C", "O", "O", "C", "C", "O", "C", "O", "H", "H", "H", "H", "H", "H"),
            frozenset({
                Bond(0, 1, 2), Bond(0, 2), Bond(2, 3), Bond(3, 4), Bond(4, 5), Bond(5, 6),
                Bond(6, 7, 2), Bond(0, 8), Bond(6, 9), Bond(3, 10), Bond(3, 11),
                Bond(4, 12), Bond(4, 13),
            }),
        )

    def test_double_hydrolysis_is_derived_with_two_waters(self):
        from collections import Counter
        diester = self._diester()
        formic = Molecule(("C", "O", "O", "H", "H"),
                          frozenset({Bond(0, 1, 2), Bond(0, 2), Bond(2, 3), Bond(0, 4)})).canonical()
        glycol = Molecule(
            ("C", "C", "O", "O", "H", "H", "H", "H", "H", "H"),
            frozenset({Bond(0, 1), Bond(0, 2), Bond(1, 3), Bond(2, 8), Bond(3, 9),
                       Bond(0, 4), Bond(0, 5), Bond(1, 6), Bond(1, 7)})).canonical()
        edges, complete = capped_scissions(diester, (WATER,), max_reactant_cuts=2, budget=200_000)
        assert complete
        target = Counter([formic, formic, glycol])
        hits = [e for e in edges if Counter(p.canonical() for p in e.products) == target]
        assert hits, "the diester's double hydrolysis to 2 formic acid + ethylene glycol was not derived"
        # it consumes TWO water and every atom keeps its valence (the certificate passed at build)
        assert hits[0].forget().equation() == "C4H6O4 + 2 H2O -> 2 CH2O2 + C2H6O2"

    def test_single_cut_default_is_unchanged(self):
        # max_reactant_cuts defaults to 1: the paracetamol hydrolysis is found exactly as before
        edge = _hydrolysis()
        assert {p.canonical() for p in edge.products} == {AMINOPHENOL, ACETIC}


class TestAmideVersusEsterHydrolysis:
    def test_both_isomers_hydrolyse_to_the_same_pair_but_break_different_bonds(self):
        amide_edge = _hydrolysis(PARACETAMOL)
        ester = _aminophenyl_acetate()
        ester_edge = _hydrolysis(ester)
        # same products (chemically true: amide and ester hydrolysis both give aminophenol + acetic)
        assert {p.canonical() for p in amide_edge.products} == {p.canonical() for p in ester_edge.products}
        # but the STRUCTURE says which bond broke: a C-N bond in the amide, a C-O bond in the ester
        amide_hetero = {
            tuple(sorted((PARACETAMOL.atoms[b.i], PARACETAMOL.atoms[b.j])))
            for b in amide_edge.cut if b.i < 20 and b.j < 20
        }
        ester_hetero = {
            tuple(sorted((ester.atoms[b.i], ester.atoms[b.j])))
            for b in ester_edge.cut if b.i < 20 and b.j < 20
        }
        assert ("C", "N") in amide_hetero
        assert ("C", "O") in ester_hetero
        assert amide_hetero != ester_hetero


class TestGeneralCapping:
    """G3: any-order cuts + a full perfect matching over open ends -> higher-order and ring-forming
    rewrites the order-1 reactant-to-reagent bijection could not represent. Soundness is unchanged
    (the CappedScission certificate filters every candidate); only the reach grew."""

    def test_olefin_metathesis_is_an_order_two_whole_bond_swap(self):
        from smartchem.smiles import parse_smiles
        butene, ethylene, propene = parse_smiles("CC=CC"), parse_smiles("C=C"), parse_smiles("CC=C")
        edges, complete = capped_scissions(butene, (ethylene,), budget=200_000)
        assert complete
        # 2-butene + ethylene -> 2 propene: two C=C cut, two C=C formed -- pure order-2, impossible
        # for an order-1 capper
        hit = [e for e in edges if [p.canonical() for p in e.products].count(propene) == 2]
        assert hit, "metathesis to two propene was not derived"
        assert hit[0].forget().equation() == "C4H8 + C2H4 -> 2 C3H6"

    def test_ring_forming_cap_produces_a_cyclic_product(self):
        # reactant-end-to-reactant-end caps close a ring in a product -- needs >=2 cuts and the full
        # perfect matching (a reactant-to-reagent bijection can only ever produce trees/acyclic joins)
        from smartchem.smiles import parse_smiles
        glycol, water = parse_smiles("OCCO"), parse_smiles("O")
        edges, _ = capped_scissions(glycol, (water,), max_reactant_cuts=2, budget=300_000)

        def is_ring(m):
            return len(m.atoms) > 2 and len(m.bonds) >= len(m.atoms)   # a connected graph with a cycle

        assert any(is_ring(p) for e in edges for p in e.products), "no ring-forming rewrite was derived"

    def test_order_one_hydrolysis_is_unchanged(self):
        # the whole existing capability is a subset: the real paracetamol hydrolysis still derives
        edges, _ = capped_scissions(PARACETAMOL, (WATER,))
        assert any({p.canonical() for p in e.products} == {AMINOPHENOL, ACETIC} for e in edges)

    def test_every_emitted_edge_forgets_to_a_valid_mediated_edge(self):
        # regression for the element-product forget bug the general capper surfaced (a capped H2/O2
        # product must bucket to unit elements, not a multi-atom element formula)
        from smartchem.smiles import parse_smiles
        glycol, water = parse_smiles("OCCO"), parse_smiles("O")
        edges, _ = capped_scissions(glycol, (water,), max_reactant_cuts=2, budget=300_000)
        for e in edges:
            e.forget()                         # must not raise -- every rewrite has a formula-level image
