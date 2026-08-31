"""M4 -- convergent synthesis DAGs: two sub-routes feeding one step.

A convergent synthesis is a DAG, not a chain: two branches make two intermediates and one step joins them.
These tests pin the structure (edges, topological order, the convergence point, the single-sink/acyclic/
distinct-target invariants), the genuinely new computation -- the CONVERGENT CEILING, where the scarcer branch
limits the join -- and that the reused rungs (E1 composability per edge, M1/M2 per step) aggregate correctly.

The worked example is the convergent synthesis of ethyl acetate:
    branch A: 2 CH3CHO + O2 -> 2 CH3COOH   (make the acid)
    branch B: C2H4 + H2O   -> C2H6O        (make the alcohol)
    join    : CH3COOH + C2H6O -> ethyl acetate + H2O   (Fischer esterification -- consumes BOTH)
"""
import pytest

from smartchem.experiment.dag import (
    DAGError,
    SynthesisDAG,
    dag_ceiling,
    verify_dag,
)
from smartchem.experiment.feasibility import FeasibilityDirection, FeasibilityGrade
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles
from fractions import Fraction

ALD = parse_smiles("CC=O")        # acetaldehyde
O2 = parse_smiles("O=O")
ACOH = parse_smiles("CC(=O)O")    # acetic acid
ETHENE = parse_smiles("C=C")      # ethylene
WATER = parse_smiles("O")
ETOH = parse_smiles("CCO")        # ethanol
EA = parse_smiles("CCOC(=O)C")    # ethyl acetate
# seeded small molecules for a thermo-reachable convergent DAG
CO = parse_smiles("[C-]#[O+]")
CO2 = parse_smiles("O=C=O")
H2 = parse_smiles("[H][H]")
CH4 = parse_smiles("C")


def branch_acid():   # 2 CH3CHO + O2 -> 2 CH3COOH
    return ExperimentStep.assembling(ACOH, (ALD, ALD, O2), (ACOH, ACOH))


def branch_alcohol():  # C2H4 + H2O -> C2H6O
    return ExperimentStep.assembling(ETOH, (ETHENE, WATER), (ETOH,))


def esterify():      # CH3COOH + C2H6O -> ethyl acetate + H2O
    return ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER))


def ethyl_acetate_dag():
    return SynthesisDAG.of(branch_acid(), branch_alcohol(), esterify())


class TestConvergentStructure:
    def test_the_dag_is_convergent_with_one_join(self):
        dag = ethyl_acetate_dag()
        assert dag.is_convergent
        assert dag.convergence_points == (2,)            # the esterification (index 2) joins both branches
        assert repr(dag.final_target) == "C4H8O2"        # ethyl acetate

    def test_the_edges_are_the_two_branches_feeding_the_join(self):
        dag = ethyl_acetate_dag()
        edges = {(i, j, repr(m)) for i, j, m in dag.edges}
        assert edges == {(0, 2, "C2H4O2"), (1, 2, "C2H6O")}   # acid->join, alcohol->join

    def test_topological_order_places_producers_before_the_join(self):
        order = [repr(s.target) for s in ethyl_acetate_dag().topological_order()]
        assert order.index("C2H4O2") < order.index("C4H8O2")
        assert order.index("C2H6O") < order.index("C4H8O2")

    def test_leaf_inputs_are_the_external_starting_materials(self):
        leaves = {repr(m) for m in ethyl_acetate_dag().leaf_inputs}
        assert leaves == {"C2H4O", "O2", "C2H4", "H2O"}   # acetaldehyde, oxygen, ethylene, water

    def test_a_linear_shaped_dag_is_valid_but_not_convergent(self):
        # alcohol -> esterify (with acetic acid as an external leaf, not a branch): a path, not a fork
        dag = SynthesisDAG.of(branch_alcohol(), esterify())
        assert not dag.is_convergent
        assert dag.convergence_points == ()
        assert repr(dag.final_target) == "C4H8O2"


class TestConvergentCeiling:
    """The genuinely new computation: the limiting-reagent max propagated through the DAG."""

    def test_the_scarcer_branch_limits_the_join(self):
        dag = ethyl_acetate_dag()
        # branch A can make 2 acetic acid; branch B can make 1 ethanol -> the join is limited to 1 ethyl acetate
        c = dag_ceiling(dag, {ALD: 2, O2: 1, ETHENE: 1, WATER: 1})
        assert c.final_target_mol == Fraction(1)
        assert repr(c.per_step[-1].limiting_reactant) == "C2H6O"     # ethanol (branch B) limits the join

    def test_starving_a_branch_drops_the_convergent_ceiling(self):
        dag = ethyl_acetate_dag()
        # halve the ethylene -> branch B makes only 1/2 ethanol -> the join ceiling halves, still B-limited
        c = dag_ceiling(dag, {ALD: 2, O2: 1, ETHENE: Fraction(1, 2), WATER: 1})
        assert c.final_target_mol == Fraction(1, 2)
        assert repr(c.per_step[-1].limiting_reactant) == "C2H6O"

    def test_the_ceiling_is_a_conservation_quantity(self):
        c = dag_ceiling(ethyl_acetate_dag(), {ALD: 2, O2: 1, ETHENE: 1, WATER: 1})
        assert c.quantity.bucket.name == "CONSERVATION"


class TestMalformedDagsRefused:
    def test_two_unconsumed_targets_is_not_one_synthesis(self):
        with pytest.raises(DAGError):
            SynthesisDAG.of(branch_acid(), branch_alcohol())    # acid AND alcohol both unconsumed -> 2 sinks

    def test_two_steps_making_the_same_target_are_refused(self):
        with pytest.raises(DAGError):
            SynthesisDAG.of(branch_alcohol(), branch_alcohol(), esterify())   # ethanol produced twice

    def test_a_cycle_is_refused(self):
        butane = parse_smiles("CCCC")
        isobutane = parse_smiles("CC(C)C")
        cyclobutane = parse_smiles("C1CCC1")
        s_p = ExperimentStep.assembling(butane, (isobutane,), (butane,))          # isobutane -> butane
        s_q = ExperimentStep.assembling(isobutane, (butane,), (isobutane,))       # butane -> isobutane (cycle)
        s_r = ExperimentStep.assembling(cyclobutane, (butane,), (cyclobutane, H2))  # butane -> cyclobutane (sink)
        with pytest.raises(DAGError):
            SynthesisDAG.of(s_p, s_q, s_r)

    def test_verify_and_ceiling_require_a_dag(self):
        with pytest.raises(TypeError):
            verify_dag(branch_acid())
        with pytest.raises(TypeError):
            dag_ceiling(branch_acid(), {})


class TestReusedRungsAggregateOverTheDag:
    """M1/M2 are per-step and shape-agnostic; verify_dag maps them and aggregates worst-step-dominated."""

    def sabatier_dag(self):
        # a seeded convergent DAG (all species in the thermo seed) so per-step ΔG is DERIVED:
        #   A: 2 CO + O2 -> 2 CO2            (favorable)
        #   B: 2 H2O -> 2 H2 + O2            (water splitting -- UNFAVORABLE)
        #   join: CO2 + 4 H2 -> CH4 + 2 H2O  (Sabatier -- favorable) ; consumes CO2 (A) and H2 (B)
        a = ExperimentStep.assembling(CO2, (CO, CO, O2), (CO2, CO2))
        b = ExperimentStep.assembling(H2, (WATER, WATER), (H2, H2, O2))
        join = ExperimentStep.assembling(CH4, (CO2, H2, H2, H2, H2), (CH4, WATER, WATER))
        return SynthesisDAG.of(a, b, join)

    def test_per_step_feasibility_is_derived_and_the_worst_step_dominates(self):
        dag = self.sabatier_dag()
        assert dag.is_convergent and dag.convergence_points == (2,)
        v = verify_dag(dag)
        # every step's ΔG is DERIVED (all species seeded, near 298 K)
        assert all(f.grade is FeasibilityGrade.DERIVED for f in v.feasibility)
        assert v.feasibility[0].direction is FeasibilityDirection.FAVORABLE      # CO oxidation
        assert v.feasibility[1].direction is FeasibilityDirection.UNFAVORABLE    # water splitting
        assert v.feasibility[2].direction is FeasibilityDirection.FAVORABLE      # Sabatier
        assert v.feasibility_verdict == "UNFAVORABLE"                            # the endergonic branch dominates

    def test_the_endergonic_branch_makes_the_equilibrium_verdict_negligible(self):
        v = verify_dag(self.sabatier_dag())
        assert v.equilibrium_verdict == "NEGLIGIBLE"     # water-splitting's K << 1 caps the whole DAG

    def test_explain_names_the_convergent_shape(self):
        text = verify_dag(self.sabatier_dag()).explain()
        assert "convergent" in text
        assert "1 join" in text
