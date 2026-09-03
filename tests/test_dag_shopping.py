"""SHOP-LEAF-02: the quantity-aware shopping requirement over a DAG -- the INVERSE of the max-yield ceiling.

DAG-FLOW-01 answered "given this feed, what is the most final target I can make?" (a ceiling whose fan-out
allocation is a RANGE).  This is the inverse a chemist actually shops with: "to make THIS much final target, how
much of each external input must I buy?"  Unlike the forward ceiling, the inverse is UNIQUELY DETERMINED for an
admissible DAG -- every intermediate has exactly one producer (the distinct-targets invariant), so producing a
fixed amount forces every reaction extent, and the per-species net (consumed minus produced, with by-products
CREDITED) is exact.

These tests pin: a linear chain and a convergent tree give exact per-leaf quantities (with an exact rational when
a branch produces a multiple of its target); a by-product is CREDITED against a downstream purchase (buy 1 mol H2,
not 2, when a prior step liberates one); a fan-out is DETERMINED here even though its forward ceiling is a range; a
surplus co-product is reported, not bought; the requirement scales linearly with the target; and the ONE genuinely
coupled case -- a species produced by more than one step (a target that is also a by-product elsewhere) -- REFUSES
with :class:`ShoppingUnderdeterminedError` rather than fabricate a number, exactly as an unbounded ceiling refuses.
"""
from fractions import Fraction

import pytest

from smartchem.experiment.ceiling import CeilingError
from smartchem.experiment.dag import (
    DAGShoppingRequirement,
    ShoppingUnderdeterminedError,
    SynthesisDAG,
    _ident,
    dag_ceiling,
    dag_shopping_requirement,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

ETHENE = parse_smiles("C=C")
WATER = parse_smiles("O")
ETOH = parse_smiles("CCO")
O2 = parse_smiles("O=O")
ACOH = parse_smiles("CC(=O)O")
H2 = parse_smiles("[H][H]")
ETHANE = parse_smiles("CC")
ALD = parse_smiles("CC=O")
BUTENE = parse_smiles("C=CCC")        # 1-butene  C4H8
BUTADIENE = parse_smiles("C=CC=C")    # 1,3-butadiene C4H6
BUTANE = parse_smiles("CCCC")         # C4H10
ETOAC = parse_smiles("CC(=O)OCC")     # ethyl acetate
CPROP = parse_smiles("C1CC1")         # cyclopropane C3H6
PROPENE = parse_smiles("CC=C")        # propene C3H6 -- an isomer of cyclopropane (distinct canonical identity)
PROPANE = parse_smiles("CCC")         # C3H8


def _amount(pairs, molecule) -> Fraction | None:
    """The mol assigned to ``molecule`` in a ``(Molecule, Fraction)`` tuple, matched by canonical identity."""
    key = _ident(molecule)
    for m, amount in pairs:
        if _ident(m) == key:
            return amount
    return None


# -- fixtures: valid, balanced DAGs -------------------------------------------------------------------------
def linear_chain():
    """ETHENE + WATER -> ETOH ; ETOH + O2 -> ACOH + WATER.  The step-2 by-product water credits step-1's demand."""
    hydrate = ExperimentStep.assembling(ETOH, (ETHENE, WATER), (ETOH,))
    oxidize = ExperimentStep.assembling(ACOH, (ETOH, O2), (ACOH, WATER))
    return SynthesisDAG.of(hydrate, oxidize)


def butadiene_dag():
    """BUTENE -> BUTADIENE + H2 ; BUTADIENE + 2 H2 -> BUTANE.  The liberated H2 partly credits the hydrogenation."""
    dehydro = ExperimentStep.assembling(BUTADIENE, (BUTENE,), (BUTADIENE, H2))
    hydro = ExperimentStep.assembling(BUTANE, (BUTADIENE, H2, H2), (BUTANE,))
    return SynthesisDAG.of(dehydro, hydro)


def convergent_tree():
    """A join: ETHENE+WATER->ETOH and 2 ALD + O2 -> 2 ACOH, then ETOH + ACOH -> ETOAC + WATER (the sink)."""
    make_etoh = ExperimentStep.assembling(ETOH, (ETHENE, WATER), (ETOH,))
    make_acoh = ExperimentStep.assembling(ACOH, (ALD, ALD, O2), (ACOH, ACOH))   # 2 ACOH per run -> a 1/2 extent
    esterify = ExperimentStep.assembling(ETOAC, (ETOH, ACOH), (ETOAC, WATER))
    return SynthesisDAG.of(make_etoh, make_acoh, esterify)


def surplus_dag():
    """ETOH -> ETHENE + WATER ; ETHENE + H2 -> ETHANE.  Water is a co-product nothing consumes (a surplus output)."""
    dehydrate = ExperimentStep.assembling(ETHENE, (ETOH,), (ETHENE, WATER))
    hydrogenate = ExperimentStep.assembling(ETHANE, (ETHENE, H2), (ETHANE,))
    return SynthesisDAG.of(dehydrate, hydrogenate)


def coupled_dag():
    """WATER is the TARGET of step 1 AND a by-product of step 3 -- produced by two steps, so the buy is a range."""
    make_water = ExperimentStep.assembling(WATER, (O2, H2, H2), (WATER, WATER))
    hydrate = ExperimentStep.assembling(ETOH, (WATER, ETHENE), (ETOH,))
    oxidize = ExperimentStep.assembling(ACOH, (ETOH, O2), (ACOH, WATER))
    return SynthesisDAG.of(make_water, hydrate, oxidize)


class TestLinearChainQuantities:
    def test_a_linear_chain_gives_exact_per_leaf_quantities(self):
        req = dag_shopping_requirement(linear_chain(), 1)
        assert isinstance(req, DAGShoppingRequirement)
        assert _amount(req.requirements, ETHENE) == 1
        assert _amount(req.requirements, O2) == 1

    def test_the_step2_byproduct_water_is_credited_to_zero_not_bought(self):
        # step 1 consumes 1 water, step 2 liberates 1 water -> net 0: water is neither bought nor a surplus.
        req = dag_shopping_requirement(linear_chain(), 1)
        assert _amount(req.requirements, WATER) is None       # not on the shopping list
        assert _amount(req.co_products, WATER) is None        # and not a surplus either -- exactly balanced

    def test_the_final_target_is_never_on_the_shopping_list(self):
        req = dag_shopping_requirement(linear_chain(), 1)
        assert _amount(req.requirements, ACOH) is None
        assert _amount(req.co_products, ACOH) is None          # THE product, not a co-product


class TestByproductCredit:
    def test_liberated_hydrogen_is_credited_so_you_buy_one_not_two(self):
        # BUTADIENE + 2 H2 needs 2 H2; the dehydrogenation liberates 1 H2 -> buy only 1 (the DAG-FLOW-01 fold, inverted).
        req = dag_shopping_requirement(butadiene_dag(), 1)
        assert _amount(req.requirements, BUTENE) == 1
        assert _amount(req.requirements, H2) == 1              # NOT 2 -- the by-product H2 is credited

    def test_the_credit_scales_with_the_target(self):
        req = dag_shopping_requirement(butadiene_dag(), 3)
        assert _amount(req.requirements, BUTENE) == 3
        assert _amount(req.requirements, H2) == 3              # 6 consumed - 3 liberated


class TestConvergentTree:
    def test_a_convergent_tree_quantifies_both_branches(self):
        req = dag_shopping_requirement(convergent_tree(), 1)
        assert _amount(req.requirements, ETHENE) == 1
        assert _amount(req.requirements, ALD) == 1

    def test_a_branch_that_makes_two_targets_per_run_gives_an_exact_rational(self):
        # the acid branch makes 2 ACOH per run, so making 1 ACOH runs it at extent 1/2 -> 1/2 mol O2.
        req = dag_shopping_requirement(convergent_tree(), 1)
        assert _amount(req.requirements, O2) == Fraction(1, 2)


class TestFanoutIsDetermined:
    def test_the_shared_intermediate_fanout_has_a_unique_shopping_list(self):
        # the DAG-FLOW-01 fan-out fixture: ethanol produced once, consumed by two steps.  The FORWARD ceiling is a
        # range (allocation), but the INVERSE is unique -- you must make enough ethanol for BOTH consumers.
        from tests.test_dag_flow import fanout_dag
        req = dag_shopping_requirement(fanout_dag(), 1)
        assert _amount(req.requirements, ETHENE) == 2         # 2 ethanol needed -> 2 ethene
        assert _amount(req.requirements, O2) == 1
        assert _amount(req.requirements, H2) == 1
        assert _amount(req.requirements, WATER) is None       # the two by-product waters exactly feed the hydration


class TestCoProductSurplus:
    def test_a_surplus_coproduct_is_reported_not_bought(self):
        req = dag_shopping_requirement(surplus_dag(), 1)
        assert _amount(req.requirements, ETOH) == 1
        assert _amount(req.requirements, H2) == 1
        assert _amount(req.requirements, WATER) is None       # not bought
        assert _amount(req.co_products, WATER) == 1           # a surplus OUTPUT (the dehydration liberates it)


class TestScalesLinearly:
    def test_doubling_the_target_doubles_every_requirement(self):
        one = dict((_ident(m), a) for m, a in dag_shopping_requirement(convergent_tree(), 1).requirements)
        two = dict((_ident(m), a) for m, a in dag_shopping_requirement(convergent_tree(), 2).requirements)
        assert one.keys() == two.keys()
        assert all(two[k] == 2 * one[k] for k in one)


class TestDifferentialOracleHolds:
    def test_feeding_the_requirement_forward_reproduces_the_target(self):
        # the function asserts this internally; pin it externally too -- the requirement, fed to the forward
        # max-yield ceiling, makes EXACTLY the requested amount (two derivations sharing no arithmetic).
        for dag, target in ((linear_chain(), 2), (butadiene_dag(), 1), (convergent_tree(), Fraction(3, 2))):
            req = dag_shopping_requirement(dag, target)
            forward = dag_ceiling(dag, {m: a for m, a in req.requirements})
            assert forward.final_target_mol == Fraction(target)


class TestCoupledRefuses:
    def test_a_species_produced_by_two_steps_refuses_rather_than_fabricate(self):
        with pytest.raises(ShoppingUnderdeterminedError, match="more than one NET producer"):
            dag_shopping_requirement(coupled_dag(), 1)

    def test_the_refusal_names_the_offending_species_and_the_followon(self):
        with pytest.raises(ShoppingUnderdeterminedError, match="COST-VEC-01"):
            dag_shopping_requirement(coupled_dag(), 1)


def spectator_medium_dag():
    """WATER is a reaction MEDIUM in the hydration: consumed 2, regenerated 1 (net 1).  Its producer must not
    over-run.  mk_water = 2 H2 + O2 -> 2 H2O (target WATER); hydrate = ETHENE + 2 WATER -> ETOH + WATER (sink)."""
    mk_water = ExperimentStep.assembling(WATER, (H2, H2, O2), (WATER, WATER))
    hydrate = ExperimentStep.assembling(ETOH, (ETHENE, WATER, WATER), (ETOH, WATER))
    return SynthesisDAG.of(mk_water, hydrate)


def autocatalytic_dag():
    """s1 = cyclopropane + propene -> 2 propene (target propene CONSUMES its own target -- autocatalytic); the
    extent is the internal-make FLOOR.  s2 = propene + H2 -> propane (sink)."""
    isomerize = ExperimentStep.assembling(PROPENE, (CPROP, PROPENE), (PROPENE, PROPENE))
    hydro = ExperimentStep.assembling(PROPANE, (PROPENE, H2), (PROPANE,))
    return SynthesisDAG.of(isomerize, hydro)


class TestRedTeamFolds:
    """SHOP-LEAF-02 red-team folds (workflow wj716si7g): the guard now counts NET producers (not gross), the
    back-propagation charges NET consumption (a regenerated medium does not over-run its producer), the oracle is
    TWO-SIDED (tightness certifies each buy is a real lower bound, not merely sufficient), and a self-consuming
    step's requirement is the internal-make floor.  The genuine multi-net-producer range still refuses."""

    def test_a_regenerated_medium_does_not_over_run_its_producer(self):
        # gross-vs-net over-refusal + over-run fold: water is a partly-regenerated medium (net consumed 1, not 2),
        # so mk_water runs at extent 1/2 -> buy H2=1, O2=1/2, ETHENE=1 -- NOT H2=2/O2=1 (the gross over-buy), and
        # NOT a ShoppingUnderdeterminedError (the old gross guard's false "it's a range" refusal).
        req = dag_shopping_requirement(spectator_medium_dag(), 1)
        assert _amount(req.requirements, ETHENE) == 1
        assert _amount(req.requirements, H2) == 1
        assert _amount(req.requirements, O2) == Fraction(1, 2)
        assert _amount(req.requirements, WATER) is None       # the regenerated medium nets to zero
        assert _amount(req.co_products, WATER) is None

    def test_a_self_consuming_autocatalytic_step_gives_the_internal_make_floor(self):
        # cyclopropane and propene are distinct isomers (C3H6); the isomerization consumes its own target.  Making
        # every intermediate internally, the floor is buy 1 cyclopropane + 1 H2 (the self-seed is internal).
        assert _ident(CPROP) != _ident(PROPENE)               # genuinely distinct species, an admissible DAG
        req = dag_shopping_requirement(autocatalytic_dag(), 1)
        assert _amount(req.requirements, CPROP) == 1
        assert _amount(req.requirements, H2) == 1

    def test_every_reported_quantity_is_tight_a_real_lower_bound(self):
        # the two-sided oracle made explicit: for the by-product DAG, H2=1 is TIGHT -- feeding the reported amount
        # makes exactly the target, but HALVING it makes strictly less.  A dropped-credit over-report (H2=2) would
        # NOT be tight (H2=1 already suffices via the liberated H2), which is exactly what the oracle now rejects.
        dag = butadiene_dag()
        req = dag_shopping_requirement(dag, 1)
        h2 = _amount(req.requirements, H2)
        assert h2 == 1
        assert dag_ceiling(dag, {m: a for m, a in req.requirements}).final_target_mol == 1        # sufficient
        halved = {m: (a / 2 if _ident(m) == _ident(H2) else a) for m, a in req.requirements}
        assert dag_ceiling(dag, halved).final_target_mol < 1                                      # and tight

    def test_a_genuine_multi_net_producer_still_refuses(self):
        # the legit refusal is preserved: coupled_dag's water is NET-produced by TWO steps (a real range).
        with pytest.raises(ShoppingUnderdeterminedError, match="more than one NET producer"):
            dag_shopping_requirement(coupled_dag(), 1)


class TestInputGuards:
    def test_a_non_dag_is_refused(self):
        with pytest.raises(TypeError):
            dag_shopping_requirement("not a dag", 1)

    @pytest.mark.parametrize("bad", [0, -1, -5])
    def test_a_nonpositive_target_is_refused(self, bad):
        with pytest.raises(CeilingError):
            dag_shopping_requirement(linear_chain(), bad)

    @pytest.mark.parametrize("bad", [1.5, 1.0, True])
    def test_a_float_or_bool_target_is_refused_exactness_is_load_bearing(self, bad):
        with pytest.raises(CeilingError):
            dag_shopping_requirement(linear_chain(), bad)


class TestNonVacuous:
    def test_a_real_synthesis_always_has_a_nonempty_shopping_list(self):
        for maker in (linear_chain, butadiene_dag, convergent_tree, surplus_dag):
            req = dag_shopping_requirement(maker(), 1)
            assert req.requirements                              # never a vacuous empty list

    def test_the_extents_cover_every_step(self):
        dag = convergent_tree()
        req = dag_shopping_requirement(dag, 1)
        assert len(req.step_extents) == len(dag.steps)
        assert all(x > 0 for _s, x in req.step_extents)         # every step runs; none is a no-op
