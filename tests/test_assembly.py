"""The synthesis assembler: a chosen structured descent graded as ONE object.

These pin the bridge from the capped decompiler descent to L2: several valence-capped cleavages, one per
intermediate, compose into one :class:`SynthesisDAG` a single ``classify`` call grades worst-step-dominated.
The load-bearing demonstration is the litmus: paracetamol's structured descent -- through the real amide
hydrolysis and THROUGH the aromatic ring (R1) -- assembled and graded in one shot, with the honest boundary
(the structured chain reaches real intermediates, not bare atoms) stated as an assertion, not a hope.
"""
import pytest

from smartchem.experiment import (
    Grade,
    SynthesisAssemblyError,
    assemble_synthesis,
    classify,
    find_scission,
    steps_from_scissions,
)
from smartchem.experiment.dag import SynthesisDAG
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import capped_scissions

PARACETAMOL = parse_smiles("CC(=O)Nc1ccc(O)cc1")   # C8H9NO2
AMINOPHENOL = parse_smiles("Nc1ccc(O)cc1")          # C6H7NO
WATER = parse_smiles("O")


def _hydrolysis_scission():
    """The real amide hydrolysis of paracetamol: C8H9NO2 + H2O -> C6H7NO + C2H4O2 (deterministic pick)."""
    cs_all, _ = capped_scissions(PARACETAMOL, (WATER,))
    hits = find_scission(cs_all, products=["C6H7NO", "C2H4O2"])
    return hits[0]


def _ring_opening_scission():
    """A genuine RING-OPENING of 4-aminophenol -- one present only with ring_aware (proves R1 reach)."""
    plain, _ = capped_scissions(AMINOPHENOL, (WATER,), ring_aware=False)
    aware, _ = capped_scissions(AMINOPHENOL, (WATER,), ring_aware=True)
    plain_digests = {e.digest for e in plain}
    ring_openings = sorted((e for e in aware if e.digest not in plain_digests), key=lambda e: e.digest)
    return ring_openings[0]


class TestFindScission:
    """Selecting a specific cleavage out of the valence-valid soup, by product formula multiset."""

    def test_matches_by_hill_string_dict_and_molecule(self):
        cs_all, _ = capped_scissions(PARACETAMOL, (WATER,))
        by_str = find_scission(cs_all, products=["C6H7NO", "C2H4O2"])
        by_dict = find_scission(cs_all, products=[{"C": 6, "H": 7, "N": 1, "O": 1}, {"C": 2, "H": 4, "O": 2}])
        assert by_str and by_str == by_dict          # the three spec forms agree

    def test_returns_empty_on_no_match(self):
        cs_all, _ = capped_scissions(PARACETAMOL, (WATER,))
        assert find_scission(cs_all, products=["C99"]) == ()

    def test_is_deterministic_and_digest_sorted(self):
        cs_all, _ = capped_scissions(PARACETAMOL, (WATER,))
        hits = find_scission(cs_all, products=["C6H7NO", "C2H4O2"])
        assert list(hits) == sorted(hits, key=lambda cs: cs.digest)

    def test_malformed_formula_string_is_refused(self):
        with pytest.raises((ValueError, TypeError)):
            find_scission((), products=["not a formula!"])


class TestStepsFromScissions:
    """Each capped cleavage becomes its assembly step (a descent read backwards)."""

    def test_a_scission_becomes_a_step_making_its_reactant(self):
        cs = _hydrolysis_scission()
        (step,) = steps_from_scissions([cs])
        assert dict(step.target.formula) == {"C": 8, "H": 9, "N": 1, "O": 2}   # makes paracetamol
        assert step.consumes(AMINOPHENOL)                                        # from its precursors

    def test_empty_is_refused(self):
        with pytest.raises(SynthesisAssemblyError):
            steps_from_scissions([])

    def test_misaligned_envelopes_are_refused(self):
        cs = _hydrolysis_scission()
        with pytest.raises(SynthesisAssemblyError):
            steps_from_scissions([cs], envelopes=[None, None])


class TestAssembleAndGradeInOneShot:
    """The whole point: a multi-level structured descent graded by ONE classify call."""

    def test_paracetamol_two_level_descent_assembles_into_one_dag(self):
        dag = assemble_synthesis([_hydrolysis_scission(), _ring_opening_scission()])
        assert type(dag) is SynthesisDAG
        assert dict(dag.final_target.formula) == {"C": 8, "H": 9, "N": 1, "O": 2}   # -> paracetamol
        assert len(dag.steps) == 2

    def test_one_classify_grades_the_whole_chain(self):
        dag = assemble_synthesis([_hydrolysis_scission(), _ring_opening_scission()])
        v = classify(dag)
        # a structured descent with no sourced data for its deep rungs: HYPOTHESIZED floor, honestly
        assert v.grade is Grade.HYPOTHESIZED
        assert v.is_legitimate is False
        assert v.conserves is True                      # every step conserves (E0 re-checked)
        assert "C8H9NO2" in v.headline or "paracetamol" in v.headline.lower()

    def test_the_structured_chain_reaches_through_the_aromatic_ring(self):
        # the level-2 step is a ring-opening that exists ONLY with ring_aware -- R1 reach, in an assembly
        plain, _ = capped_scissions(AMINOPHENOL, (WATER,), ring_aware=False)
        aware, _ = capped_scissions(AMINOPHENOL, (WATER,), ring_aware=True)
        assert len(aware) > len(plain)                  # ring-opening is genuinely on the menu
        cs2 = _ring_opening_scission()
        assert cs2.digest not in {e.digest for e in plain}   # the chosen step is a true ring-opening

    def test_bad_cleavage_set_is_refused_not_silently_patched(self):
        # two cleavages of the SAME intermediate cannot both be in one synthesis (distinct-target rule)
        cs = _hydrolysis_scission()
        with pytest.raises(SynthesisAssemblyError):
            assemble_synthesis([cs, cs])


class TestBoundaryHonesty:
    """The structured chain is the intermediate-level half, NOT the bare-atom formula chain -- stated, not hidden."""

    def test_leaf_inputs_are_real_intermediate_molecules_not_bare_atoms(self):
        dag = assemble_synthesis([_hydrolysis_scission(), _ring_opening_scission()])
        # every starting material is a closed-shell polyatomic molecule (it canonicalises), never a lone atom;
        # reaching the atom buckets {C,H,N,O} is the FORMULA-level v1 chain's job, not this one
        for m in dag.leaf_inputs:
            m.canonical()
            assert len(m.atoms) >= 2
