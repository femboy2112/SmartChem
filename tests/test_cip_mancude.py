"""Hostile controls for the bounded neutral mancude Rule-1a extension."""
from fractions import Fraction

import pytest

from experiments import cip_mancude_probe as probe
from smartchem import smiles


def _context(text):
    atoms, bonds = smiles._parse_skeleton(text)
    smiles._kekulize_in_place(atoms, bonds, sum(a.charge for a in atoms))
    elems, filled = smiles._fill_hydrogens(atoms, bonds)
    adj = {i: [] for i in range(len(elems))}
    for bond in filled:
        adj[bond.i].append((bond.j, bond.order))
        adj[bond.j].append((bond.i, bond.order))
    blocked, averages, _released = smiles._cip_mancude(atoms, bonds, adj)
    return blocked, averages, adj, elems


def test_source_absolutes_and_aromatic_kekule_reflection_false_centre_panel():
    result = probe.report()
    assert len(result["source_anchors"]) == 2
    assert result["family_comparisons"] == 96


def test_primary_fraction_examples_and_owner_not_represented_atom():
    blocked, average, adj, elems = _context("c1ccccn1")
    assert not blocked
    assert average[0] == average[4] == Fraction(13, 2)
    assert average[5] == 6                      # real pyridine N is still Z=7; its duplicate partner is C
    assert elems[5] == "N"
    # Fused ring: unique partner positions C,C,N average to 6 1/3, while the two-position C,N average
    # remains 6 1/2 despite unequal frequencies in the THREE complete Kekule matchings of quinoline.
    blocked, average, _adj, _elems = _context("c1ccc2ncccc2c1")
    assert not blocked
    assert average[3] == Fraction(19, 3)
    assert average[5] == Fraction(13, 2)
    blocked, average, _adj, _elems = _context("c1ncncc1")
    assert average[2] == 7                      # C between two N atoms: possible partners N,N


@pytest.mark.parametrize("sense,expected", [("@", "R"), ("@@", "S")])
def test_explicit_kekule_bypass_was_a_real_mislabel(sense, expected):
    # Independent RDKit accurate-CIP baseline exposed this shipped error: the @ explicit form returned S.
    # The original aromatic guard never saw uppercase atoms. Both routes now use the same fractions.
    for a, b in (("C1=CC=CC=N1", "C1=NC=CN=C1"), ("c1ccccn1", "c1nccnc1")):
        assert smiles.cip_labels(f"O[C{sense}H]({a}){b}") == (expected,)


def test_only_multiple_bond_duplicates_are_averaged_ring_closures_remain_integer():
    # A miniature synthetic ring closure isolates the distinction from full molecular parsing.
    adj = {0: [(1, 1), (2, 2)], 1: [(0, 1)], 2: [(0, 2)]}
    mass = [smiles._cip_mass(e, 0) for e in ("C", "C", "N")]     # ROUND 28: mass array threaded into the digraph
    node = smiles._cip_digraph(0, 1, frozenset((0, 1, 2)), adj, ["C", "C", "N"], mass,
                               frozenset(), [20], {0: Fraction(13, 2)})
    children = node[2]                                            # (z, mass, grandchildren, ez) 4-tuples (R28 mass, R34 ez)
    assert sorted(z for z, _m, _c, _e in children) == [Fraction(13, 2), 7]
    # ROUND 28 (birdperson LEAK 2): the mancude multiple-bond duplicate carries the OWNER's averaged Z -- a
    # Kekule/partner SUPERPOSITION, not one atom -- so its Rule-2 mass is None (no single-atom referent; Rule 2
    # DEFERS on it rather than fabricate).  The ring-closure integer-Z duplicate of the real N keeps a real mass.
    by_z = {z: m for z, m, _c, _e in children}
    assert by_z[Fraction(13, 2)] is None
    assert by_z[7] == smiles._cip_mass("N", 0)


@pytest.mark.parametrize("smi", ["C[C@H](O)C1=CC=[NH+]C=C1",
                                  "C[C@H](O)C1=CC=CC1=O"])
def test_unsupported_charged_or_exocyclic_systems_defer_on_both_input_routes(smi):
    assert smiles.cip_labels(smi) == ()


def test_an_unsupported_ring_in_an_atomic_number_decided_branch_stays_lazy():
    assert smiles.cip_labels("Cl[C@H](C)C=CC1=CC=[NH+]C=C1") == ("R",)


def test_existing_aromatic_pyridinium_parser_refusal_remains_explicit():
    # The parser's pre-existing aromatic matcher treats every [nH] as a donor. Charged aromatic
    # pyridinium is not admitted there; an explicit spelling reaches the CIP deferral above.
    with pytest.raises(smiles.SmilesError, match="could not assign a Kekulé structure"):
        smiles.cip_labels("C[C@H](O)c1cc[nH+]cc1")


def test_ring_bridge_is_not_a_resonance_partner():
    # The single bond between two benzenes is a bridge, even though both endpoint atoms are on rings.
    atoms, bonds = smiles._parse_skeleton("c1ccccc1-c2ccccc2")
    ring = smiles._cip_ring_edges(len(atoms), bonds)
    bridge = next(i for i, (a, b, _o) in enumerate(bonds) if (a, b) == (5, 6))
    assert bridge not in ring
    assert len(ring) == 12


@pytest.mark.parametrize("limit,value", [("_CIP_MANCUDE_MAX_ATOMS", 5),
                                        ("_CIP_MANCUDE_MAX_ATOMS", 0),
                                        ("_CIP_MANCUDE_MAX_MATCHINGS", 1),
                                        ("_CIP_MANCUDE_MAX_MATCHINGS", 0),
                                        ("_CIP_MANCUDE_WORK_BUDGET", 1),
                                        ("_CIP_MANCUDE_WORK_BUDGET", 0)])
def test_budget_exhaustion_does_not_publish_partial_averages(monkeypatch, limit, value):
    monkeypatch.setattr(smiles, limit, value)
    assert smiles.cip_labels("C[C@H](N)c1ccccc1") == ()
    assert smiles.cip_labels("C[C@H](N)C1=CC=CC=C1") == ()
    assert smiles.cip_labels("[C@H](F)(Cl)Br") == ("S",)  # unrelated ordinary naming still works


def test_isotope_and_true_duplicate_ties_and_ring_centres_are_still_deferred():
    assert smiles.cip_labels("O[C@H](c1ccccc1)c1ccc[13cH]c1") == ()
    assert smiles.cip_labels("O[C@H](c1ccccn1)C1=NC=CC=C1") == ()
    assert smiles.cip_labels("N[C@]1(F)CCCCO1") == ()
