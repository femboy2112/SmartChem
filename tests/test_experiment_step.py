"""E0 -- the certified experiment step and route, proven universal and conserving.

The step is trusted only as far as it is checked: conservation is re-derived through
:class:`~smartchem.category.Reaction` (an independent path), and the tests exercise that on molecules
the data tables never heard of, so a passing step is a real conservation certificate, not a whitelist hit.
"""
import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment.step import ExperimentRoute, ExperimentStep, StepError
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import capped_scissions


def _env(prov="lit"):
    return ConditionEnvelope(
        temperature=Interval(298, 330, "K"), status=EvidenceStatus.EXPERIMENTAL, provenance=prov
    )


class TestStepIsUniversalAndConserving:
    def test_arbitrary_off_registry_molecule_makes_a_step(self):
        # ethyl acetate is not in any stability/conditions seed table; E0 must still certify it
        ea = parse_smiles("CCOC(=O)C")
        acoh = parse_smiles("CC(=O)O")
        etoh = parse_smiles("CCO")
        water = parse_smiles("O")
        step = ExperimentStep.assembling(ea, (acoh, etoh), (ea, water))
        assert step.target == ea
        assert set(step.byproducts) == {water}

    def test_a_non_conserving_step_is_refused_by_the_independent_certificate(self):
        acoh = parse_smiles("CC(=O)O")
        water = parse_smiles("O")
        # acetic acid -> water is not mass-balanced; Reaction's own dict-accumulation check must catch it
        with pytest.raises(StepError, match="conserve"):
            ExperimentStep.assembling(water, (acoh,), (water,))

    def test_target_must_be_a_product(self):
        from smartchem.experiment.step import STEP_SCHEMA
        acoh = parse_smiles("CC(=O)O")
        ea = parse_smiles("CCOC(=O)C")
        etoh = parse_smiles("CCO")
        water = parse_smiles("O")
        # acetic acid is not among the products, so it cannot be this step's target
        with pytest.raises(StepError, match="target must appear"):
            ExperimentStep(STEP_SCHEMA, acoh, (acoh, etoh), (ea, water), (), ConditionEnvelope.unknown())

    def test_reagents_must_be_a_subset_of_reactants(self):
        acoh = parse_smiles("CC(=O)O")
        ea = parse_smiles("CCOC(=O)C")
        etoh = parse_smiles("CCO")
        water = parse_smiles("O")
        stray = parse_smiles("N")  # ammonia: not among the reactants
        with pytest.raises(StepError, match="subset"):
            ExperimentStep.assembling(ea, (acoh, etoh), (ea, water), reagents=(stray,))


class TestStepFromCappedScission:
    def test_reverse_of_a_hydrolysis_is_a_conserving_synthesis(self):
        # a descent read backwards is an assembly: hydrolysis of ethyl acetate -> esterification of it
        ea = parse_smiles("CCOC(=O)C")
        water = parse_smiles("O")
        edges, complete = capped_scissions(ea, (water,))
        assert complete and edges
        step = ExperimentStep.from_capped_scission(edges[0], envelope=_env())
        # the synthesis makes the original reactant, conserving (the certificate would have raised)
        assert step.target == ea
        assert step.is_declared


class TestRouteLinearity:
    def test_a_linear_route_carries_each_intermediate_forward(self):
        anh = parse_smiles("CC(=O)OC(=O)C")
        water = parse_smiles("O")
        acoh = parse_smiles("CC(=O)O")
        etoh = parse_smiles("CCO")
        ea = parse_smiles("CCOC(=O)C")
        s1 = ExperimentStep.assembling(acoh, (anh, water), (acoh, acoh), envelope=_env())
        s2 = ExperimentStep.assembling(ea, (acoh, etoh), (ea, water), envelope=_env())
        route = ExperimentRoute.of(s1, s2)
        assert route.n_transitions == 1
        assert route.final_target == ea
        assert route.intermediates == (acoh,)

    def test_a_non_linear_route_is_refused(self):
        # step 1 makes acetic acid, step 2 does not consume it -> no carried intermediate
        anh = parse_smiles("CC(=O)OC(=O)C")
        water = parse_smiles("O")
        acoh = parse_smiles("CC(=O)O")
        etoh = parse_smiles("CCO")
        s1 = ExperimentStep.assembling(acoh, (anh, water), (acoh, acoh), envelope=_env())
        # a genuinely non-consuming second step: diethyl ether from two ethanols (no acetic acid)
        dee = parse_smiles("CCOCC")
        s2 = ExperimentStep.assembling(dee, (etoh, etoh), (dee, water), envelope=_env())
        with pytest.raises(StepError, match="not linear"):
            ExperimentRoute.of(s1, s2)

    def test_single_step_route_is_legal(self):
        acoh = parse_smiles("CC(=O)O")
        etoh = parse_smiles("CCO")
        ea = parse_smiles("CCOC(=O)C")
        water = parse_smiles("O")
        route = ExperimentRoute.of(
            ExperimentStep.assembling(ea, (acoh, etoh), (ea, water), envelope=_env())
        )
        assert route.n_transitions == 0
