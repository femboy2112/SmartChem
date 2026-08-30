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

PARACETAMOL = known_compounds("C8H9NO2")[0].molecule
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
