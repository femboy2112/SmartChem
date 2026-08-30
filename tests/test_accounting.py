"""E3 -- the physical-accounting attach layer, proven to reproduce-or-refuse, never invent."""
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment.accounting import account_route, account_step
from smartchem.experiment.bucket import Bucket
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles

KETENE = parse_smiles("C=C=O")
WATER = parse_smiles("O")
ACOH = parse_smiles("CC(=O)O")
AMP = parse_smiles("Nc1ccc(O)cc1")
ANH = parse_smiles("CC(=O)OC(=O)C")
PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")


class TestHeatIsEstablishedOrUnknown:
    def test_a_covered_reaction_gets_a_real_sourced_enthalpy(self):
        # ketene + water -> acetic acid: all three have sourced 0 K formation enthalpies
        step = ExperimentStep.assembling(ACOH, (KETENE, WATER), (ACOH,))
        heat = account_step(step).heat
        assert heat.bucket is Bucket.KNOWN_SOURCED
        assert isinstance(heat.value, float) and heat.value < 0  # exothermic
        assert account_step(step).is_exothermic is True

    def test_an_uncovered_species_makes_the_whole_enthalpy_unknown(self):
        # paracetamol has no 0 K formation enthalpy in the reference -> UNKNOWN, never a partial guess
        step = ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH))
        heat = account_step(step).heat
        assert heat.bucket is Bucket.UNKNOWN
        assert heat.value is None
        assert account_step(step).is_exothermic is None


class TestConditionsAreSourcedOrUnknown:
    def test_declared_conditions_are_known_sourced_undeclared_are_unknown(self):
        env = ConditionEnvelope(
            temperature=Interval(295, 320, "K"), medium="aqueous, mild acid",
            status=EvidenceStatus.EXPERIMENTAL, provenance="teaching synthesis",
        )
        sa = account_step(ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH),
                                                    reagents=(ANH,), envelope=env))
        assert sa.temperature.bucket is Bucket.KNOWN_SOURCED
        assert sa.medium.bucket is Bucket.KNOWN_SOURCED
        # pressure and duration were not declared -> loud UNKNOWN, not a default
        assert sa.pressure.bucket is Bucket.UNKNOWN
        assert sa.duration.bucket is Bucket.UNKNOWN

    def test_a_bare_step_degrades_to_all_unknown_conditions_without_crashing(self):
        sa = account_step(ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH)))
        assert all(
            q.bucket is Bucket.UNKNOWN for q in (sa.temperature, sa.pressure, sa.duration, sa.medium)
        )


class TestRouteAccounting:
    def test_account_route_has_one_entry_per_step(self):
        s1 = ExperimentStep.assembling(ACOH, (KETENE, WATER), (ACOH,))
        s2 = ExperimentStep.assembling(PARA, (ACOH, AMP), (PARA, WATER))  # toy consume of acetic acid
        route = ExperimentRoute.of(s1, s2)
        acc = account_route(route)
        assert len(acc.per_step) == 2
        assert acc.per_step[0].heat.bucket is Bucket.KNOWN_SOURCED
