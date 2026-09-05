"""CANON-KEKULE-01 (item 3): resonance-canonical identity, and its differential tripwires.

``resonance_canonical`` lifts the SMILES parser's minimal-constitution placement onto an arbitrary ``Molecule`` so a
scission FRAGMENT unifies with the SAME species parsed from SMILES.  It touches the one primitive every transform
family rests on, so per the standing discipline it is guarded not only by "does aspirin compile now" but by
differential property tests: relabel-invariance (it never depends on atom order), NON-over-unification (genuine
positional isomers and tautomers keep DISTINCT identities), and idempotence (no parsed molecule's identity moves, so
no frozen digest / golden fixture ripples).
"""
from smartchem.category import Bond, Molecule
from smartchem.contracts import canonical_digest
from smartchem.experiment.routes import _ident
from smartchem.compilation_ir import _structure_ident
from smartchem.service import build_recompile_request, run_compilation
from smartchem.smiles import parse_smiles, resonance_canonical, resonance_identity


def _digest(m):
    return canonical_digest(resonance_canonical(m))


# -- the fix's acceptance: aspirin is producible, and the fragment unifies with its registered stock ---------------

def test_aspirin_is_producible_after_resonance_identity():
    """The item-3 acceptance: aspirin compiles to its real disconnection, previously a false NO_ROUTE.

    Capped-scission always EMITTED aspirin + acetic acid -> acetic anhydride + salicylic acid, but the ortho-
    disubstituted salicylate fragment carried a different Kekulé pattern than registered salicylic acid, so the
    literal-bond-order canonicaliser called them different molecules.  Resonance identity unifies them.
    """
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Oc1ccccc1C(=O)O", helper_reagents=("acetic acid",),
        stock_materials=("salicylic acid", "acetic anhydride"), max_depth=2))
    assert resp.compilation_ir.candidate_count >= 1
    assert any("C4H6O3" in d.equation and "C7H6O3" in d.equation and "C9H8O4" in d.equation
               for d in resp.ranked_route_dossiers)  # acetic anhydride + salicylic acid -> aspirin (+ acetic acid)


def test_a_kekule_flipped_fragment_unifies_with_its_parsed_form():
    """A Molecule built with the OTHER Kekulé ring pattern (not via the parser) unifies under resonance identity.

    Constructed by flipping only the aromatic ring's single<->double alternation on parsed salicylic acid -- a genuine
    resonance form (every atom's total bond order preserved) that plain ``canonical()`` treats as distinct.
    """
    sal = parse_smiles("O=C(O)c1ccccc1O")
    ring = _aromatic_ring_indices(sal)
    flipped = _flip_ring_kekule(sal, ring)
    # plain canonical DISTINGUISHES the two Kekulé forms (that is the bug) ...
    assert canonical_digest(sal.canonical()) != canonical_digest(flipped.canonical())
    # ... resonance identity UNIFIES them (that is the fix).
    assert _digest(sal) == _digest(flipped)
    assert resonance_identity(sal) == resonance_identity(flipped)


# -- relabel-invariance: identity never depends on atom order or SMILES spelling ----------------------------------

def test_resonance_identity_is_spelling_invariant_for_ortho_and_meta_aromatics():
    for spellings in [
        ("O=C(O)c1ccccc1O", "Oc1ccccc1C(=O)O", "OC(=O)c1ccccc1O"),           # salicylic acid (ortho)
        ("Cc1cccc(C)c1", "Cc1cccc(c1)C", "c1cc(C)cc(C)c1"),                    # m-xylene (meta)
        ("CC(=O)Oc1ccccc1C(=O)O", "O=C(O)c1ccccc1OC(C)=O"),                    # aspirin (ortho)
    ]:
        digs = {_digest(parse_smiles(s)) for s in spellings}
        assert len(digs) == 1, spellings


def test_resonance_canonical_is_atom_permutation_invariant():
    # relabel the atoms of a molecule arbitrarily; the resonance identity must not move.
    m = parse_smiles("O=C(O)c1ccccc1O")
    n = len(m.atoms)
    perm = list(range(n))
    perm = perm[3:] + perm[:3]  # a fixed nontrivial rotation of the labels
    relabelled = Molecule(
        tuple(m.atoms[perm.index(i)] for i in range(n)),
        frozenset(Bond(perm[b.i], perm[b.j], b.order) for b in m.bonds),
        m.charge, m.state,
    )
    assert _digest(relabelled) == _digest(m)


# -- NON-over-unification: the soundness guard (the dangerous failure mode) ----------------------------------------

def test_positional_double_bond_isomers_stay_distinct():
    # 1-butene vs 2-butene: same formula, DIFFERENT per-atom pi-demand -> must never unify.
    assert _digest(parse_smiles("C=CCC")) != _digest(parse_smiles("CC=CC"))
    # 1-pentene / 2-pentene likewise.
    assert _digest(parse_smiles("C=CCCC")) != _digest(parse_smiles("CC=CCC"))


def test_keto_enol_and_constitutional_isomers_stay_distinct():
    # keto vs enol tautomer (H-placement differs -> distinct sigma-skeleton -> never conflated).
    assert _digest(parse_smiles("CC=O")) != _digest(parse_smiles("C=CO"))       # acetaldehyde vs ethenol
    # constitutional isomers of one formula stay distinct.
    assert _digest(parse_smiles("CCO")) != _digest(parse_smiles("COC"))          # ethanol vs dimethyl ether
    assert _digest(parse_smiles("CC(=O)OC")) != _digest(parse_smiles("CCOC=O"))  # methyl acetate vs ethyl formate


def test_ortho_meta_para_cresol_stay_distinct():
    # the three cresol regioisomers must remain three identities (resonance unifies Kekulé forms, never regiochemistry).
    digs = {_digest(parse_smiles(s)) for s in ("Cc1ccccc1O", "Cc1cccc(O)c1", "Cc1ccc(O)cc1")}
    assert len(digs) == 3


# -- idempotence: no parsed molecule's identity moves (the frozen-digest / fixture no-ripple guarantee) ------------

def test_resonance_canonical_is_idempotent_on_parsed_molecules():
    for smi in ["CC(=O)Nc1ccc(O)cc1", "CC(=O)OC(C)=O", "CC(=O)O", "Nc1ccc(O)cc1", "O", "CO", "CCO",
                "c1ccccc1", "CC(=O)OCCC(C)C", "COC(=O)c1ccccc1O", "O=C(O)c1ccccc1O", "N#N", "O=C=O"]:
        m = parse_smiles(smi)
        assert canonical_digest(m.canonical()) == _digest(m), smi        # parse digest UNCHANGED
        assert _digest(m) == _digest(resonance_canonical(m)), smi        # applying it twice is a no-op


def test_resonance_identity_is_bounded_on_a_large_conjugated_input():
    """evil-morty DoS fold: ``_ident`` is the search hot path, so it must stay fast on a large conjugated molecule.

    A 122-atom explicit-Kekulé nested para-phenylene enumerated ~4000 Kekulé placements (~18 s, each a full
    canonicalization) before the caps.  The heavy-atom guard (>64 heavy) / placement cap (>128 placements) now fall
    it back to the plain literal identity in milliseconds.
    """
    import time
    smi = "C1=CC=CC=C1"
    for _ in range(11):
        smi = f"C1=CC=C({smi})C=C1"   # 12 nested rings, 72 heavy atoms -- over the heavy-atom guard
    m = parse_smiles(smi)
    start = time.perf_counter()
    _ident(m)
    assert time.perf_counter() - start < 3.0   # was ~18 s pre-fix; a generous bound that still catches a regression


def test_ident_and_structure_ident_are_byte_identical():
    for smi in ["O=C(O)c1ccccc1O", "CC(=O)Oc1ccccc1C(=O)O", "CCO", "O", "c1ccccc1", "CC(=O)Nc1ccc(O)cc1"]:
        m = parse_smiles(smi)
        assert _ident(m) == _structure_ident(m), smi


# -- helpers: build an alternate-Kekulé Molecule WITHOUT going through the parser (fragment surgery) --------------

def _aromatic_ring_indices(m: Molecule) -> list[int]:
    """The 6 carbons of the (single) benzene ring: carbons in a 6-cycle of ring bonds."""
    carbons = [i for i, s in enumerate(m.atoms) if s == "C"]
    adj = {i: set() for i in carbons}
    for b in m.bonds:
        if b.i in adj and b.j in adj:
            adj[b.i].add(b.j)
            adj[b.j].add(b.i)
    ring = [c for c in carbons if len(adj[c]) == 2 or len(adj[c]) == 3]
    # keep only carbons every one of whose ring-neighbours is also a ring carbon of degree>=2 (the fused hexagon)
    return [c for c in ring if len(adj[c]) >= 2]


def _flip_ring_kekule(m: Molecule, ring: list[int]) -> Molecule:
    """Swap single<->double on the six ring C-C bonds, preserving every atom's total bond order (a resonance form)."""
    ringset = set(ring)
    new_bonds = []
    for b in m.bonds:
        if b.i in ringset and b.j in ringset and m.atoms[b.i] == "C" == m.atoms[b.j]:
            new_bonds.append(Bond(b.i, b.j, 1 if b.order == 2 else 2))
        else:
            new_bonds.append(b)
    return Molecule(m.atoms, frozenset(new_bonds), m.charge, m.state)
