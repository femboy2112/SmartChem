"""E2 -- the stoichiometric ceiling, proven exact, limiting-reagent-correct, and route-propagating."""
from fractions import Fraction

import pytest

from smartchem.experiment.ceiling import (
    CeilingError,
    route_ceiling,
    stoichiometric_ceiling,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles

AMP = parse_smiles("Nc1ccc(O)cc1")
ANH = parse_smiles("CC(=O)OC(=O)C")
PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
ACOH = parse_smiles("CC(=O)O")
WATER = parse_smiles("O")
ETOH = parse_smiles("CCO")
EA = parse_smiles("CCOC(=O)C")


class TestSingleStepCeiling:
    def test_limiting_reagent_litmus(self):
        # 4-aminophenol + acetic anhydride -> paracetamol + acetic acid; aminophenol limits at 1:1.5
        step = ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH), reagents=(ANH,))
        c = stoichiometric_ceiling(step, {AMP: 1, ANH: Fraction(3, 2)})
        assert c.limiting_reactant == AMP
        assert c.max_target_mol == Fraction(1)
        assert c.quantity.bucket.value == "CONSERVATION"

    def test_the_other_reagent_can_limit(self):
        step = ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH), reagents=(ANH,))
        c = stoichiometric_ceiling(step, {AMP: 5, ANH: 2})
        assert c.limiting_reactant == ANH
        assert c.max_target_mol == Fraction(2)

    def test_exactness_a_float_amount_is_refused(self):
        step = ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER))
        with pytest.raises(CeilingError, match="exact"):
            stoichiometric_ceiling(step, {ACOH: 1.0})

    def test_no_specified_reactant_is_refused(self):
        step = ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER))
        with pytest.raises(CeilingError, match="nothing to limit"):
            stoichiometric_ceiling(step, {})

    def test_a_non_reactant_feed_entry_is_refused(self):
        step = ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER))
        with pytest.raises(CeilingError, match="not a reactant"):
            stoichiometric_ceiling(step, {WATER: 1})


class TestRoutePropagation:
    def test_ceiling_propagates_through_a_two_step_route(self):
        # step 1: anhydride + water -> 2 acetic acid; step 2: acetic acid + ethanol -> ethyl acetate + water
        s1 = ExperimentStep.assembling(ACOH, (ANH, WATER), (ACOH, ACOH))
        s2 = ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER))
        route = ExperimentRoute.of(s1, s2)
        # 1 mol anhydride -> up to 2 mol acetic acid -> up to 2 mol ethyl acetate (ethanol in excess)
        rc = route_ceiling(route, {ANH: 1, WATER: 10, ETOH: 10})
        assert rc.per_step[0].max_target_mol == Fraction(2)
        assert rc.final_target_mol == Fraction(2)

    def test_intermediate_scarcity_limits_the_final_step(self):
        # only 0.5 mol anhydride -> 1 mol acetic acid -> 1 mol ethyl acetate
        s1 = ExperimentStep.assembling(ACOH, (ANH, WATER), (ACOH, ACOH))
        s2 = ExperimentStep.assembling(EA, (ACOH, ETOH), (EA, WATER))
        rc = route_ceiling(ExperimentRoute.of(s1, s2), {ANH: Fraction(1, 2), WATER: 10, ETOH: 10})
        assert rc.final_target_mol == Fraction(1)
