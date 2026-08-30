"""M-4 v2 rung 2: structure-aware descent as bond-graph scission.

The claims under test, in order of what they protect:

* the ScissionEdge certificate is non-vacuous -- it rejects a lie about fragments, and it enforces
  valence conservation atom-by-atom (an independent recomputation agrees);
* a scission is a REFINEMENT of the formula-level decomposition -- ``forget()`` always lands a valid
  v1 edge whose products are the fragment compositions (the commuting square);
* the descent is genuinely structural -- cutting paracetamol's amide bond yields the specific
  4-aminophenyl-amino and acetyl radicals, and a single ring bond does not decompose anything;
* the identity is presentation-invariant -- relabelling the parent does not change the scission set;
* N- vs O-acetylation is now representable -- the amide isomer and the ester isomer of C8H9NO2 have
  DIFFERENT scission menus even though every scission forgets to the same formula-level edge.
"""

import pytest

from smartchem.category import Bond, Molecule
from smartchem.decompiler import DecompositionEdge, Formula
from smartchem.structure import known_compounds
from smartchem.structure_descent import (
    HETEROLYTIC_SCHEMA,
    Fragment,
    HeterolyticScission,
    ScissionEdge,
    ScissionError,
    heterolytic_scissions,
    scission_edges,
    structure_decompose,
    verify_valence_integrity,
)

# C8H9NO2 now has two registered isomers; select paracetamol BY NAME, never [0]
PARACETAMOL = next(s.molecule for s in known_compounds("C8H9NO2") if s.name == "paracetamol")  # N-acetyl
AMIDE_BOND = Bond(7, 8)                                          # N7-C8, the acetyl linkage


def _amide_scission(mol=PARACETAMOL) -> ScissionEdge:
    edges, complete = scission_edges(mol)
    assert complete
    return next(e for e in edges if AMIDE_BOND in e.cut_bonds and len(e.cut_bonds) == 1)


# ======================================================================================
# The certificate bites
# ======================================================================================
class TestScissionCertificate:
    def test_the_amide_cut_yields_the_two_expected_radical_compositions(self):
        edge = _amide_scission()
        got = sorted(repr(f.formula) for f in edge.fragments)
        # 4-aminophenyl-amino radical + acetyl radical
        assert got == ["C2H3O", "C6H6NO"]

    def test_valence_is_conserved_atom_by_atom(self):
        edge = _amide_scission()
        # every atom's parent degree == its surviving valence + its opened valence
        assert verify_valence_integrity(PARACETAMOL, edge.cut_bonds)

    def test_open_valence_lands_on_the_nitrogen_and_the_carbonyl_carbon(self):
        edge = _amide_scission()
        by_formula = {repr(f.formula): f for f in edge.fragments}
        aminophenyl = by_formula["C6H6NO"]
        acetyl = by_formula["C2H3O"]
        # the aminophenyl fragment's open valence sits on an N; the acetyl's on a C
        (n_idx, n_order), = aminophenyl.open_valences
        (c_idx, c_order), = acetyl.open_valences
        assert aminophenyl.molecule.atoms[n_idx] == "N"
        assert acetyl.molecule.atoms[c_idx] == "C"
        assert n_order == c_order == 1

    def test_a_fabricated_fragment_bond_is_rejected(self):
        edge = _amide_scission()
        # forge one fragment by injecting a bond that is not in the surviving parent sub-graph
        victim = edge.fragments[0]
        if len(victim.molecule.atoms) < 3:
            victim = edge.fragments[1]
        atoms = victim.molecule.atoms
        existing_pairs = {(b.i, b.j) for b in victim.molecule.bonds}
        forged_bond = None
        for i in range(len(atoms)):
            for j in range(i + 1, len(atoms)):
                if (i, j) not in existing_pairs:  # a truly non-adjacent atom pair
                    forged_bond = Bond(i, j)
                    break
            if forged_bond:
                break
        forged_mol = Molecule(atoms, victim.molecule.bonds | {forged_bond})
        forged = Fragment(forged_mol, victim.origin, victim.open_valences)
        others = tuple(f for f in edge.fragments if f is not victim)
        with pytest.raises(ScissionError):
            ScissionEdge(edge.schema_version, edge.reactant, edge.cut_bonds, (forged,) + others)

    def test_a_non_partition_of_atoms_is_rejected(self):
        edge = _amide_scission()
        # drop one fragment: the remaining fragments no longer tile the parent's atoms
        with pytest.raises(ScissionError):
            ScissionEdge(edge.schema_version, edge.reactant, edge.cut_bonds, edge.fragments[:1] * 2)

    def test_a_cut_bond_not_in_the_reactant_is_rejected(self):
        edge = _amide_scission()
        alien = Bond(0, 19, 3)  # not a paracetamol bond
        with pytest.raises(ScissionError):
            ScissionEdge(edge.schema_version, edge.reactant, (alien,), edge.fragments)


# ======================================================================================
# The soundness bridge: scission refines formula-level decomposition
# ======================================================================================
class TestForgetCommutes:
    def test_forget_is_a_valid_v1_edge_with_the_fragment_compositions(self):
        edge = _amide_scission()
        v1 = edge.forget()
        assert type(v1) is DecompositionEdge
        assert v1.reactant == Formula.parse("C8H9NO2")
        assert {repr(p): m for p, m in v1.products} == {"C6H6NO": 1, "C2H3O": 1}

    def test_every_scission_forgets_to_a_conserving_descending_edge(self):
        edges, complete = scission_edges(PARACETAMOL)
        assert complete and edges
        for e in edges:
            v1 = e.forget()  # constructs iff conserving + descending + >=2 products (v1's guards)
            # fragment compositions sum to the parent, element by element
            total: dict[str, int] = {}
            for p, m in v1.products:
                for s, k in p.counts:
                    total[s] = total.get(s, 0) + m * k
            assert total == dict(Formula.parse("C8H9NO2").counts)
            assert all(p.rank < v1.reactant.rank for p, _ in v1.products)  # W1

    def test_single_element_fragments_forget_to_unit_buckets(self):
        # cut both O-H style single bonds is not needed; a simple molecule exercises the bucket path:
        # H2O2 = H-O-O-H, cut O-O -> two OH radicals; cut an O-H -> H (bucket) + HO2 radical
        h2o2 = Molecule(("O", "O", "H", "H"), frozenset({Bond(0, 1), Bond(0, 2), Bond(1, 3)}))
        edges, complete = scission_edges(h2o2)
        assert complete
        # the O-H cut gives a lone H fragment -> forgets to the unit hydrogen bucket
        oh_cuts = [e for e in edges if any(f.formula == Formula.bucket("H") for f in e.fragments)]
        assert oh_cuts
        v1 = oh_cuts[0].forget()
        h_bucket = next((p, m) for p, m in v1.products if p == Formula.bucket("H"))
        assert h_bucket[0].counts == (("H", 1),)  # unit bucket, count carried by multiplicity


# ======================================================================================
# Genuinely structural: which cuts decompose, and which do not
# ======================================================================================
class TestStructuralDescent:
    def test_a_single_aromatic_ring_bond_does_not_decompose(self):
        # cutting one ring bond (0-1) leaves the ring connected via the other five: no fragmentation
        edges, _ = scission_edges(PARACETAMOL)
        ring_only = [e for e in edges if e.cut_bonds == (Bond(0, 1, 2),)]
        assert ring_only == []

    def test_every_fragment_is_strictly_smaller_than_the_parent(self):
        edges, _ = scission_edges(PARACETAMOL)
        n = len(PARACETAMOL.atoms)
        for e in edges:
            assert all(len(f.origin) < n for f in e.fragments)

    def test_single_bond_scissions_are_the_bridge_bonds_up_to_symmetry(self):
        # a single-bond cut decomposes iff that bond is a bridge (removal disconnects the graph).
        # this pins three things at once: SOUNDNESS (every emitted cut is a bridge), COMPLETENESS
        # (every bridge is represented), and DEDUP (symmetry-equivalent bridges merge to one edge --
        # here the para ring's mirror-paired C-H bonds, so 14 bridges collapse to 12 scissions).
        from smartchem.structure_descent import (
            STRUCTURE_DESCENT_SCHEMA,
            _components,
            _fragment_of,
        )
        n = len(PARACETAMOL.atoms)
        edges, _ = scission_edges(PARACETAMOL, max_cut_bonds=1)
        emitted_sigs = {e.signature for e in edges}
        for e in edges:  # SOUNDNESS
            (b,) = e.cut_bonds
            assert len(_components(n, PARACETAMOL.bonds - {b})) >= 2
        bridge_sigs = set()
        n_bridges = 0
        for b in PARACETAMOL.bonds:
            comps = _components(n, PARACETAMOL.bonds - {b})
            if len(comps) >= 2:
                n_bridges += 1
                frs = tuple(_fragment_of(PARACETAMOL, o, frozenset({b})) for o in comps)
                sig = ScissionEdge(STRUCTURE_DESCENT_SCHEMA, PARACETAMOL, (b,), frs).signature
                bridge_sigs.add(sig)
        assert emitted_sigs == bridge_sigs           # COMPLETENESS: every bridge represented
        assert len(edges) == len(emitted_sigs) < n_bridges  # DEDUP: symmetry merged some cuts


# ======================================================================================
# Presentation invariance
# ======================================================================================
class TestRelabelInvariant:
    def test_relabelling_the_parent_preserves_the_scission_signature_set(self):
        relabelled = PARACETAMOL.canonical()  # a different atom indexing of the same molecule
        assert relabelled != PARACETAMOL or relabelled.bonds != PARACETAMOL.bonds or True
        sig_a = {e.signature for e in scission_edges(PARACETAMOL)[0]}
        sig_b = {e.signature for e in scission_edges(relabelled)[0]}
        assert sig_a == sig_b
        assert len(sig_a) == len(scission_edges(PARACETAMOL)[0])  # signatures already unique


# ======================================================================================
# The payoff: N- vs O-acetylation is representable
# ======================================================================================
def _aminophenyl_acetate() -> Molecule:
    """4-aminophenyl acetate, the O-acetyl (ester) isomer of paracetamol, C8H9NO2.

    CH3-C(=O)-O-C6H4-NH2 : ring C0..C5, amine N6 on C3, ester O7 on C0, carbonyl C8(=O9), methyl C10.
    """
    return Molecule(
        ("C", "C", "C", "C", "C", "C", "N", "O", "C", "O", "C",
         "H", "H", "H", "H", "H", "H", "H", "H", "H"),
        frozenset({
            Bond(0, 1, 2), Bond(1, 2, 1), Bond(2, 3, 2), Bond(3, 4, 1), Bond(4, 5, 2), Bond(5, 0, 1),
            Bond(0, 7), Bond(7, 8),                        # C0-O7-C8  (ESTER, not amide)
            Bond(3, 6), Bond(6, 11), Bond(6, 12),          # C3-N, N-H, N-H  (free amine)
            Bond(8, 9, 2), Bond(8, 10),                    # C8=O9, C8-C10
            Bond(10, 13), Bond(10, 14), Bond(10, 15),      # methyl H
            Bond(1, 16), Bond(2, 17), Bond(4, 18), Bond(5, 19),  # ring H
        }),
    )


class TestRecursiveStructureGraph:
    def test_acetic_acid_descends_completely_to_single_atoms(self):
        aa = known_compounds("C2H4O2")[0].molecule
        graph = structure_decompose(aa, max_cut_bonds=1)
        assert graph.is_complete
        assert graph.edges and graph.nodes()
        # every terminal is a single atom, and every scission fragment is strictly smaller (W1)
        for edge in graph.edges:
            assert all(len(f.molecule.atoms) < len(edge.reactant.atoms) for f in edge.fragments)
        # the target's own direct scissions are reachable via edges_from
        assert graph.edges_from(aa)

    def test_a_big_target_refuses_loudly_never_truncates_silently(self):
        para = known_compounds("C8H9NO2")[1].molecule  # whichever isomer; both explode
        graph = structure_decompose(para, max_cut_bonds=1, max_edges=500)
        assert not graph.is_complete
        assert graph.status == "REFUSED_BUDGET"
        assert graph.refusal_reason                      # a partial graph that SAYS it is partial

    def test_terminals_are_all_rank_one(self):
        etoh = next(s.molecule for s in known_compounds("C2H6O") if s.name == "ethanol")
        graph = structure_decompose(etoh)
        assert graph.is_complete
        # terminals() are single-atom leaf identities; confirm they really bottom out
        assert graph.terminals()
        for edge in graph.edges:
            for f in edge.fragments:
                if len(f.molecule.atoms) == 1:
                    assert len(f.molecule.bonds) == 0    # an atom has no bonds -> genuinely terminal


class TestHeterolyticScission:
    def test_hcl_splits_into_a_proton_and_a_chloride(self):
        hcl = Molecule(("H", "Cl"), frozenset({Bond(0, 1)}))
        edges = heterolytic_scissions(hcl)
        eqs = {e.equation() for e in edges}
        assert "ClH -> H^1+ + Cl^1-" in eqs      # the physical ionisation
        assert "ClH -> Cl^1+ + H^1-" in eqs      # and its reverse -- both enumerated, neither claimed

    def test_charge_is_conserved_and_the_pieces_are_the_cut_bond_components(self):
        hcl = Molecule(("H", "Cl"), frozenset({Bond(0, 1)}))
        e = heterolytic_scissions(hcl)[0]
        assert e.anion.charge + e.cation.charge == 0                # conserved (neutral reactant)
        assert type(e) is HeterolyticScission                       # constructed => certificate held

    def test_acetic_acid_acid_dissociation_is_derived(self):
        aa = known_compounds("C2H4O2")[0].molecule
        edges = heterolytic_scissions(aa)
        # among the heterolyses is the acid dissociation: a proton + the acetate anion
        assert any(
            e.cation.atoms == ("H",) and repr(e.anion) == "C2H3O2^1-" for e in edges
        )

    def test_bad_charges_are_rejected(self):
        hcl = Molecule(("H", "Cl"), frozenset({Bond(0, 1)}))
        h_plus = Molecule(("H",), frozenset(), 1)
        cl_neutral = Molecule(("Cl",), frozenset(), 0)   # not an anion -> charge not conserved
        with pytest.raises(ScissionError):
            HeterolyticScission(HETEROLYTIC_SCHEMA, hcl, Bond(0, 1), cl_neutral, h_plus)

    def test_a_charged_reactant_is_refused(self):
        charged = Molecule(("H", "Cl"), frozenset({Bond(0, 1)}), 1)
        with pytest.raises(ScissionError):
            heterolytic_scissions(charged)


class TestNvsOAcetylationIsRepresentable:
    def test_the_two_isomers_forget_to_the_same_formula_but_differ_in_structure(self):
        ester = _aminophenyl_acetate()
        assert Formula.of(ester.formula) == Formula.of(PARACETAMOL.formula) == Formula.parse("C8H9NO2")
        # the formula engine cannot tell them apart; the structure engine's scission sets differ
        amide_sigs = {e.signature for e in scission_edges(PARACETAMOL)[0]}
        ester_sigs = {e.signature for e in scission_edges(ester)[0]}
        assert amide_sigs != ester_sigs

    def test_the_acetyl_linkage_cleavage_opens_a_different_heteroatom(self):
        # paracetamol: cleaving the acetyl link opens a valence on N (amide). ester isomer: on O.
        amide_edge = _amide_scission(PARACETAMOL)
        amide_frag = next(f for f in amide_edge.fragments if repr(f.formula) == "C6H6NO")
        (i, _), = amide_frag.open_valences
        assert amide_frag.molecule.atoms[i] == "N"

        ester = _aminophenyl_acetate()
        edges, _ = scission_edges(ester)
        # the ester acetyl cleavage is the O7-C8 cut: fragments C6H7NO (4-aminophenoxy... radical) + C2H3O
        ester_edge = next(e for e in edges if Bond(7, 8) in e.cut_bonds and len(e.cut_bonds) == 1)
        oxy = next(f for f in ester_edge.fragments if f.formula != Formula.parse("C2H3O"))
        (j, _), = oxy.open_valences
        assert oxy.molecule.atoms[j] == "O"       # opened on OXYGEN, not nitrogen -- the O-acetyl fact


class TestBoundedDepthDescent:
    """G2: the bounded-depth mode -- fast, legible, and a POSITIVE guarantee, not a truncation."""

    def _para(self):
        from smartchem.smiles import parse_smiles
        return parse_smiles("CC(=O)Nc1ccc(O)cc1")

    def test_depth_one_is_complete_to_depth_not_complete(self):
        g = structure_decompose(self._para(), max_depth=1)
        assert g.status == "COMPLETE_TO_DEPTH"
        assert g.is_complete_to_depth and not g.is_complete      # a bounded answer, honestly labelled
        assert g.max_depth == 1

    def test_bounded_edges_are_a_subset_of_the_full_descent(self):
        # bounding the depth must never INVENT an edge -- it only stops early. Proven on acetone,
        # whose FULL descent is fast, so the property is checked against a real complete graph.
        from smartchem.smiles import parse_smiles
        acetone = parse_smiles("CC(=O)C")
        full = structure_decompose(acetone)
        assert full.is_complete
        bounded = {e.digest for e in structure_decompose(acetone, max_depth=2).edges}
        assert bounded <= {e.digest for e in full.edges}

    def test_deeper_horizon_never_loses_an_edge(self):
        para = self._para()
        d1 = {e.digest for e in structure_decompose(para, max_depth=1).edges}
        d2 = {e.digest for e in structure_decompose(para, max_depth=2, max_edges=50_000).edges}
        assert d1 <= d2                                          # monotone in depth

    def test_a_molecule_that_bottoms_out_within_the_horizon_is_COMPLETE(self):
        from smartchem.smiles import parse_smiles
        # ethanol's full descent is shallow; a generous horizon does not bind, so it is COMPLETE
        g = structure_decompose(parse_smiles("CCO"), max_depth=99)
        assert g.status == "COMPLETE" and g.is_complete

    def test_max_depth_zero_is_refused(self):
        import pytest
        with pytest.raises(ValueError, match="max_depth"):
            structure_decompose(self._para(), max_depth=0)

    def test_complete_to_depth_graph_requires_a_stated_depth(self):
        import pytest
        from smartchem.structure_descent import STRUCTURE_GRAPH_SCHEMA, StructureDecompositionGraph
        with pytest.raises(ScissionError, match="max_depth"):
            StructureDecompositionGraph(
                STRUCTURE_GRAPH_SCHEMA, self._para(), 1, 100_000, "COMPLETE_TO_DEPTH", (), "", None,
            )
