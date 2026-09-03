"""DAG-FLOW-01: a fan-out CONSERVES intermediate quantities -- computed exactly, never minted, never fabricated.

A convergent JOIN (a step fed by several intermediates) the limiting-reagent propagation already handled: the
scarcer branch limits it.  The DUAL -- a FAN-OUT, one intermediate consumed by several steps -- it did NOT:
:func:`dag_ceiling`'s ``available`` cache never decremented, so two consumers each read the FULL amount a single
producer made, minting usable copies (one mole produced, two consumed, with no deficit).  The first cut BLOCKED
that (raised); this brick REPLACES the block with the real accounting: the conserved max-yield LINEAR PROGRAM
(:mod:`smartchem.experiment.exact_lp`), which allocates the shared reactant across its competing consumers to
maximize the final target.  Choosing the yield-maximizing split invents no allocation policy -- a *ceiling* is by
definition the maximum over ALL conserved allocations, so the LP optimum IS the honest 100%-efficiency upper bound.

These tests pin: the fan-out is detected (:attr:`SynthesisDAG.fanout_points`), a fan-out ceiling is the exact
conserved number (half of the old mint, hand-computed), the solution never over-consumes any species (an
independent no-mint/no-deficit re-derivation), the LP is ALWAYS the number and the propagation is trusted for the
per-step breakdown only where it AGREES with the LP (a simple tree/chain -- NOT every non-fan-out DAG: a reused
by-product is non-fan-out yet the propagation mints on it, the red-team fold), a genuinely unbounded target refuses
with :class:`CeilingError` rather than fabricating a number, and join-shaped / linear DAGs are unaffected.
"""
from collections import Counter
from fractions import Fraction

import pytest

from smartchem.experiment import dag as dag_module
from smartchem.experiment.ceiling import CeilingError
from smartchem.experiment.dag import (
    DAGFlow,
    SynthesisDAG,
    _max_yield_lp,
    _propagate,
    dag_ceiling,
)
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
CH4 = parse_smiles("C")


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


def _conserved(dag, feed, flow):
    """Independently re-derive per-species consumed vs supplied from the LP extents (no simplex bookkeeping).

    Returns the set of species (by repr) that are OVER-consumed -- a mint/deficit.  Empty means conserved.
    """
    cons = Counter()
    supp = Counter()
    for step, extent in flow.step_extents:
        for m in step.reactants:
            cons[repr(m)] += extent
        for m in step.products:
            supp[repr(m)] += extent
    for m, amount in feed.items():
        supp[repr(m)] += Fraction(amount)
    produced = {repr(m) for step, _ in flow.step_extents for m in step.products}
    fed = {repr(m) for m in feed}
    violated = set()
    for species in cons:
        if species not in produced and species not in fed:
            continue  # excess leaf: unbounded supply, conservation trivially satisfiable
        if cons[species] > supp[species]:
            violated.add(species)
    return violated


class TestFanoutDetection:
    def test_a_fanout_dag_is_a_valid_structure(self):
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
        assert join_only_dag().fanout_points == ()

    def test_a_linear_dag_has_no_fanout(self):
        assert SynthesisDAG.of(_consume_to_acid(), _join()).fanout_points == ()


class TestFanoutCeilingIsComputed:
    """The DAG-FLOW-01 acceptance: a fan-out ceiling is the EXACT conserved max-yield number, not a block."""

    def test_dag_ceiling_computes_the_conserved_fanout_max(self):
        # 1 mol ethanol is produced and both consumers want it; the LP splits it 1/2 + 1/2, so the conserved
        # ceiling is 1/2 mol DIOL.  The old never-decrementing cache MINTED it to 1 (each consumer read the full
        # mole) -- exactly double.  This is the honest half.
        dag = fanout_dag()
        c = dag_ceiling(dag, {ETHENE: 1, WATER: 2, O2: 1, H2: 1})
        assert c.final_target_mol == Fraction(1, 2)

    def test_a_fanout_ceiling_carries_the_lp_flow_not_a_per_step_chain(self):
        # a single per-step 'limiting_reactant' would be a FALSE local claim about the coupled optimum, so per_step
        # is empty and the honest solution rides `flow` (the LP extents + the fed reactants fully consumed).
        c = dag_ceiling(fanout_dag(), {ETHENE: 1, WATER: 2, O2: 1, H2: 1})
        assert isinstance(c.flow, DAGFlow)
        assert c.per_step == ()
        assert len(c.flow.step_extents) == 4
        assert [repr(m) for m in c.flow.binding_reagents] == ["C2H4"]   # ethylene caps ethanol, which caps the join
        assert c.quantity.bucket.name == "CONSERVATION"
        assert "conserved max-yield LP" in c.explain()

    def test_the_fanout_solution_conserves_every_species(self):
        # independent of the simplex's own bookkeeping: no species is consumed beyond what is fed + produced.
        feed = {ETHENE: 1, WATER: 2, O2: 1, H2: 1}
        c = dag_ceiling(fanout_dag(), feed)
        assert _conserved(fanout_dag(), feed, c.flow) == set()

    def test_starving_the_shared_leaf_scales_the_fanout_ceiling(self):
        # halve the ethylene -> only 1/2 mol ethanol -> the two consumers split 1/4 each -> 1/4 mol DIOL.
        c = dag_ceiling(fanout_dag(), {ETHENE: Fraction(1, 2), WATER: 2, O2: 1, H2: 1})
        assert c.final_target_mol == Fraction(1, 4)


CH4b = CH4


def _shared_leaf_linear_dag():
    """A LINEAR DAG whose only shared reactant is a LEAF: H2 (external) is consumed by BOTH steps."""
    s1 = ExperimentStep.assembling(ETHANE, (ETHENE, H2), (ETHANE,))   # C2H4 + H2 -> C2H6
    s2 = ExperimentStep.assembling(CH4, (ETHANE, H2), (CH4, CH4))     # C2H6 + H2 -> 2 CH4
    return SynthesisDAG.of(s1, s2)


class TestSharedBoundedLeafIsComputed:
    """A finite LEAF shared across steps mints by the same never-decremented cache but `fanout_points` (produced
    intermediates only) is blind to it; `dag_ceiling`'s coupling detection is feed-aware and routes it to the LP."""

    def test_a_bounded_leaf_shared_across_steps_is_computed_conserved(self):
        dag = _shared_leaf_linear_dag()
        assert dag.fanout_points == ()                               # structural detector is blind to a leaf mint
        # H2 fed at 1 mol, consumed by both steps: the LP splits it (e1=e2=1/2), 2*CH4 per s2 -> 1 mol CH4.
        # The mint would have given 2 (each step read the full mole of H2).
        c = dag_ceiling(dag, {ETHENE: 10, H2: 1})
        assert c.final_target_mol == Fraction(1)
        assert isinstance(c.flow, DAGFlow)
        assert [repr(m) for m in c.flow.binding_reagents] == ["H2"]
        assert _conserved(dag, {ETHENE: 10, H2: 1}, c.flow) == set()

    def test_the_same_leaf_in_excess_still_ceilings_by_propagation(self):
        # a leaf ABSENT from feed is charged in excess (unbounded): it cannot mint, so it is not coupling and the
        # plain propagation ceilings it -- unchanged at 20 (10 C2H4 -> 10 C2H6 -> 20 CH4).
        dag = _shared_leaf_linear_dag()
        c = dag_ceiling(dag, {ETHENE: 10})
        assert c.final_target_mol == Fraction(20)
        assert c.flow is None                                        # non-coupled -> the per-step propagation path

    def test_a_bounded_leaf_shared_across_convergent_branches_is_computed(self):
        acro = parse_smiles("C=CC=O")          # acrolein  C3H4O
        allyloh = parse_smiles("C=CCO")        # allyl alcohol C3H6O
        ether = parse_smiles("CCOCC=C")        # ethyl allyl ether C5H10O
        a = ExperimentStep.assembling(ETOH, (ALD, H2), (ETOH,))          # CH3CHO + H2 -> ethanol
        b = ExperimentStep.assembling(allyloh, (acro, H2), (allyloh,))   # acrolein + H2 -> allyl alcohol
        s = ExperimentStep.assembling(ether, (ETOH, allyloh), (ether, WATER))
        dag = SynthesisDAG.of(a, b, s)
        assert dag.fanout_points == ()                               # H2 is a leaf; no INTERMEDIATE fan-out
        # both branches hydrogenate with the SAME 1 mol H2 -> split 1/2 each -> 1/2 mol ether.
        c = dag_ceiling(dag, {ALD: 1, acro: 1, H2: 1})
        assert c.final_target_mol == Fraction(1, 2)
        assert _conserved(dag, {ALD: 1, acro: 1, H2: 1}, c.flow) == set()


class TestDifferentialOracleAgainstPropagation:
    """dag_ceiling's number is ALWAYS the LP; the propagation is trusted for the per-step breakdown ONLY when its
    number matches the LP (a per-call agreement check).  On a simple tree/chain (no shared reactant, no reused
    by-product) they agree by construction, so per_step is exposed and the LP re-derivation reproduces it exactly."""

    def test_lp_equals_propagation_on_the_join_only_dag(self):
        dag = join_only_dag()
        feed = {ALD: 2, O2: 1, ETHENE: 1, WATER: 1}
        c = dag_ceiling(dag, feed)
        assert c.flow is None and c.per_step                       # they agreed -> per-step breakdown exposed
        lp_value, _ = _max_yield_lp(dag, feed)                     # the LP re-derivation on the same DAG
        prop_per, prop_final = _propagate(dag, feed)
        assert lp_value == prop_final == c.final_target_mol        # three agreeing derivations

    def test_lp_equals_propagation_on_a_linear_chain(self):
        dag = SynthesisDAG.of(_consume_to_acid(), _join())
        feed = {ETOH: 1, O2: 1, ETHANE: 1}
        c = dag_ceiling(dag, feed)
        assert c.flow is None
        assert _max_yield_lp(dag, feed)[0] == _propagate(dag, feed)[1] == c.final_target_mol


class TestUnboundedTargetRefuses:
    def test_a_target_bounded_by_no_finite_feed_raises_ceilingerror(self):
        # empty feed: every leaf is charged in excess, so nothing bounds DIOL -> no finite ceiling, refuse (not a
        # fabricated number, not a hang, not a crash).
        with pytest.raises(CeilingError):
            dag_ceiling(fanout_dag(), {})

    def test_a_partial_feed_leaving_a_sink_path_all_excess_raises(self):
        # feed only WATER (a co-product side input): no bounded reactant limits the ethanol->...->DIOL path.
        with pytest.raises(CeilingError):
            dag_ceiling(fanout_dag(), {WATER: 5})


class TestNoFalsePositiveOnConservingShapes:
    def test_a_join_dag_still_ceilings_unchanged(self):
        dag = join_only_dag()
        assert dag.fanout_points == ()
        c = dag_ceiling(dag, {ALD: 2, O2: 1, ETHENE: 1, WATER: 1})
        assert c.final_target_mol == Fraction(1)                     # branch B (1 ethanol) limits the join
        assert c.flow is None

    def test_a_linear_dag_still_ceilings(self):
        dag = SynthesisDAG.of(_consume_to_acid(), _join())
        assert dag.fanout_points == ()
        c = dag_ceiling(dag, {ETOH: 1, O2: 1, ETHANE: 1})
        assert c.final_target_mol == Fraction(1)                     # a plain path: 1 acid -> 1 diol
        assert c.flow is None


class TestBlockIsRetired:
    def test_dagflowerror_is_gone(self):
        # the honest first cut BLOCKED with DAGFlowError; the real accounting COMPUTES, so the exception is retired.
        assert not hasattr(dag_module, "DAGFlowError")

    def test_dag_ceiling_still_type_guards(self):
        with pytest.raises(TypeError):
            dag_ceiling(_producer(), {})                            # a step is not a DAG


BUTENE = parse_smiles("C=CCC")     # C4H8
BUTADIENE = parse_smiles("C=CC=C") # C4H6
BUTANE = parse_smiles("CCCC")      # C4H10


def _byproduct_reuse_dag():
    """A LINEAR DAG whose downstream step reuses a BY-PRODUCT of the upstream one: X makes butadiene AND H2 (H2 is
    a by-product, not X's target, not fed); Z consumes butadiene + 2 H2.  The H2 is a finite produced species the
    naive propagation NEVER credits (its cache tracks only step targets) -- so propagation reads H2 as excess and
    MINTS. `fanout_points` is blind to it (H2 is a leaf-shaped reactant, not a produced-intermediate edge), and the
    old routing predicate (target-or-fed only) missed it too.  The red-team's HIGH finding, pinned."""
    x = ExperimentStep.assembling(BUTADIENE, (BUTENE,), (BUTADIENE, H2))        # C4H8 -> C4H6 + H2  (H2 by-product)
    z = ExperimentStep.assembling(BUTANE, (BUTADIENE, H2, H2), (BUTANE,))       # C4H6 + 2 H2 -> C4H10 (sink)
    return SynthesisDAG.of(x, z)


class TestByproductReuseIsConservedNotMinted:
    """Red-team fold (workflow wonfm36zz, 2 HIGH one root): the number is ALWAYS the LP, which counts by-products,
    so a reused by-product can no longer mint through the propagation path."""

    def test_a_reused_byproduct_is_conserved_by_the_lp(self):
        dag = _byproduct_reuse_dag()
        assert dag.fanout_points == ()                             # structural detector is blind to the by-product
        # 1 mol butene -> 1 butadiene + 1 H2; the sink needs 1 butadiene + 2 H2 but only 1 H2 exists -> H2 limits.
        # true conserved max = 1/2 mol butane (uses 1/2 butadiene + 1 H2). The naive propagation MINTS it to 1.
        c = dag_ceiling(dag, {BUTENE: 1})
        assert c.final_target_mol == Fraction(1, 2)
        assert isinstance(c.flow, DAGFlow)                         # the LP won; per-step chain discarded
        assert c.per_step == ()
        assert _conserved(dag, {BUTENE: 1}, c.flow) == set()       # H2 not over-consumed

    def test_the_naive_propagation_alone_would_have_minted(self):
        # pin the defect the fold closes: the propagation, used alone, over-reports (reads the by-product H2 as
        # excess), so dag_ceiling's number DIFFERS from it -- which is exactly why the LP is always the authority.
        dag = _byproduct_reuse_dag()
        _, prop_final = _propagate(dag, {BUTENE: 1})
        assert prop_final == Fraction(1)                           # the mint (H2 treated as infinite)
        assert dag_ceiling(dag, {BUTENE: 1}).final_target_mol == Fraction(1, 2)   # the LP corrects it
