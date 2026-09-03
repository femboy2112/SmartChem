"""DAG-FLOW-01: a fan-out conserves intermediate quantities -- or the quantitative claim is BLOCKED, not fabricated.

A convergent JOIN (a step fed by several intermediates) the ceiling already handles: the scarcer branch limits it.
The DUAL -- a FAN-OUT, one intermediate consumed by several steps -- it did NOT: :func:`dag_ceiling`'s ``available``
cache is never decremented, so two consumers each read the FULL amount a single producer made, minting usable copies
(one mole produced, two consumed, with no deficit).  Per the repo's discipline (block quantitative claims rather than
fabricate an unmodelled allocation split), a fan-out DAG now raises :class:`DAGFlowError`.

These tests pin: the fan-out is detected (:attr:`SynthesisDAG.fanout_points`, the structural DUAL of the join), a
valid fan-out STRUCTURE still constructs (only the ceiling is unsound), the ceiling BLOCKS it with an honest message,
and a join-shaped or linear DAG is unaffected (no false positive, no regression to the existing convergent ceiling).
"""
from fractions import Fraction

import pytest

from smartchem.experiment.dag import DAGError, DAGFlowError, SynthesisDAG, dag_ceiling
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

ETHENE = parse_smiles("C=C")
WATER = parse_smiles("O")
ETOH = parse_smiles("CCO")        # C2H6O -- the fanned-out intermediate (produced once, consumed by two steps)
O2 = parse_smiles("O=O")
ACOH = parse_smiles("CC(=O)O")    # C2H4O2
H2 = parse_smiles("[H][H]")
ETHANE = parse_smiles("CC")       # C2H6
DIOL = parse_smiles("OCCCCO")     # C4H10O2 -- the joined final target
ALD = parse_smiles("CC=O")        # acetaldehyde (for the join-only control DAG)


def _producer():        # C2H4 + H2O -> C2H6O           (make ethanol, the shared intermediate)
    return ExperimentStep.assembling(ETOH, (ETHENE, WATER), (ETOH,))


def _consume_to_acid():   # C2H6O + O2 -> C2H4O2 + H2O   (first consumer of ethanol)
    return ExperimentStep.assembling(ACOH, (ETOH, O2), (ACOH, WATER))


def _consume_to_ethane():  # C2H6O + H2 -> C2H6 + H2O    (SECOND consumer of ethanol -- the fan-out)
    return ExperimentStep.assembling(ETHANE, (ETOH, H2), (ETHANE, WATER))


def _join():            # C2H4O2 + C2H6 -> C4H10O2       (join the two consumers' products)
    return ExperimentStep.assembling(DIOL, (ACOH, ETHANE), (DIOL,))


def fanout_dag():
    """Ethanol is produced ONCE (step 0) and consumed by TWO steps (a fan-out); a sink joins their products."""
    return SynthesisDAG.of(_producer(), _consume_to_acid(), _consume_to_ethane(), _join())


def join_only_dag():
    """A JOIN with NO fan-out: two producers each feed one step (the ethyl-acetate esterification)."""
    ea = parse_smiles("CCOC(=O)C")
    acid = ExperimentStep.assembling(ACOH, (ALD, ALD, O2), (ACOH, ACOH))
    alcohol = ExperimentStep.assembling(ETOH, (ETHENE, WATER), (ETOH,))
    esterify = ExperimentStep.assembling(ea, (ACOH, ETOH), (ea, WATER))
    return SynthesisDAG.of(acid, alcohol, esterify)


class TestFanoutDetection:
    def test_a_fanout_dag_is_a_valid_structure(self):
        # a fan-out is admissible: an intermediate CAN legitimately feed two steps.  Only the CEILING is unsound,
        # so construction must NOT refuse it (the block belongs to the quantity computation, not the structure).
        dag = fanout_dag()
        assert repr(dag.final_target) == "C4H10O2"

    def test_fanout_points_names_the_producer_of_the_shared_intermediate(self):
        dag = fanout_dag()
        assert dag.fanout_points == (0,)                              # step 0 makes ethanol, consumed by two steps
        assert [repr(dag.steps[i].target) for i in dag.fanout_points] == ["C2H6O"]

    def test_fanout_is_the_dual_of_convergence_not_the_same(self):
        dag = fanout_dag()
        assert dag.convergence_points == (3,)                        # the JOIN (in-degree 2): the sink
        assert dag.fanout_points == (0,)                             # the FORK (out-degree 2): the producer
        assert set(dag.convergence_points).isdisjoint(dag.fanout_points)

    def test_a_join_only_dag_has_no_fanout(self):
        assert join_only_dag().fanout_points == ()                   # a join is not a fork -- no false positive

    def test_a_linear_dag_has_no_fanout(self):
        # acid-maker -> join (with ethane as an external leaf): a path, out-degree 1 at every producer
        assert SynthesisDAG.of(_consume_to_acid(), _join()).fanout_points == ()


class TestFanoutCeilingIsBlocked:
    def test_dag_ceiling_blocks_a_fanout_one_produced_two_consumed(self):
        # the DAG-FLOW-01 acceptance: an intermediate produced ONCE, consumed by TWO steps.  The old accounting
        # handed each consumer the full produced amount (mint); the quantitative claim is now BLOCKED.
        dag = fanout_dag()
        with pytest.raises(DAGFlowError):
            dag_ceiling(dag, {ETHENE: 1, WATER: 2, O2: 1, H2: 1})    # 1 mol ethanol produced; two consumers want it

    def test_the_block_names_the_shared_intermediate_and_cites_the_rule(self):
        # faithfulness: the refusal must say WHY (the named fanned-out intermediate) and cite the rule, so it can
        # never be mistaken for a generic failure or silently swallowed.
        dag = fanout_dag()
        with pytest.raises(DAGFlowError) as exc:
            dag_ceiling(dag, {ETHENE: 1, WATER: 2, O2: 1, H2: 1})
        msg = str(exc.value)
        assert "C2H6O" in msg                                        # the fanned-out intermediate is named
        assert "DAG-FLOW-01" in msg and "BLOCKED" in msg

    def test_dagflowerror_is_a_dagerror(self):
        # an existing `except DAGError` still catches it -- the block is a typed DAG error, not an escaping surprise.
        with pytest.raises(DAGError):
            dag_ceiling(fanout_dag(), {ETHENE: 1, WATER: 2, O2: 1, H2: 1})


class TestNoFalsePositiveOnConservingShapes:
    def test_a_join_dag_still_ceilings_unchanged(self):
        # the existing convergent ceiling (the scarcer branch limits the join) is untouched: a JOIN is not a fan-out.
        dag = join_only_dag()
        assert dag.fanout_points == ()
        c = dag_ceiling(dag, {ALD: 2, O2: 1, ETHENE: 1, WATER: 1})
        assert c.final_target_mol == Fraction(1)                     # branch B (1 ethanol) limits the join

    def test_a_linear_dag_still_ceilings(self):
        dag = SynthesisDAG.of(_consume_to_acid(), _join())
        assert dag.fanout_points == ()
        c = dag_ceiling(dag, {ETOH: 1, O2: 1, ETHANE: 1})
        assert c.final_target_mol == Fraction(1)                     # a plain path: 1 acid -> 1 diol
