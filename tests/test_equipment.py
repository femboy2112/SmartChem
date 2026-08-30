"""E4's equipment layer -- proven to make the right apparatus 'click' from declared conditions."""
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.experiment.bucket import Bucket
from smartchem.experiment.equipment import (
    EquipmentKind,
    equipment_for_envelope,
    equipment_for_step,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles


def _env(tlo, thi, medium="", pres=None):
    kw = dict(temperature=Interval(tlo, thi, "K"), medium=medium,
              status=EvidenceStatus.EXPERIMENTAL, provenance="lit")
    if pres:
        kw["pressure"] = Interval(pres[0], pres[1], "atm")
    return ConditionEnvelope(**kw)


def _kinds(items):
    return {it.kind for it in items}


class TestEnvelopeInference:
    def test_undeclared_conditions_give_a_loud_undetermined(self):
        items = equipment_for_envelope(ConditionEnvelope.unknown())
        assert len(items) == 1 and items[0].bucket is Bucket.UNKNOWN

    def test_gentle_aqueous_heating_is_a_hotplate_and_volumetric(self):
        items = equipment_for_envelope(_env(295, 350, "aqueous, volumetric make-up"))
        assert EquipmentKind.HEATING in _kinds(items)
        assert EquipmentKind.MEASURING in _kinds(items)
        assert any("hotplate" in it.name or "water bath" in it.name for it in items)

    def test_strong_nonflammable_heat_is_a_bunsen_burner(self):
        items = equipment_for_envelope(_env(298, 900, "aqueous"))
        assert any("Bunsen" in it.name for it in items)

    def test_flammable_medium_forbids_the_open_flame(self):
        items = equipment_for_envelope(_env(298, 400, "ethanol, reflux"))
        assert any("NO open flame" in it.name for it in items)
        assert not any("Bunsen" in it.name for it in items)

    def test_elevated_pressure_needs_a_sealed_vessel(self):
        items = equipment_for_envelope(_env(298, 320, "aqueous", pres=(5, 10)))
        assert EquipmentKind.PRESSURE in _kinds(items)
        assert any("pressure vessel" in it.name or "autoclave" in it.name for it in items)

    def test_every_inferred_item_names_its_triggering_condition(self):
        items = equipment_for_envelope(_env(295, 900, "aqueous", pres=(5, 10)))
        for it in items:
            if it.bucket is not Bucket.UNKNOWN:
                assert it.reason  # the tag: why this apparatus is on the list


class TestStepInferenceAddsContainment:
    def test_a_hazardous_step_recommends_a_fume_hood(self):
        # paracetamol synthesis species carry sourced hazards -> containment attached (inform, never neuter)
        amp = parse_smiles("Nc1ccc(O)cc1")
        anh = parse_smiles("CC(=O)OC(=O)C")
        para = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        acoh = parse_smiles("CC(=O)O")
        step = ExperimentStep.assembling(para, (amp, anh), (para, acoh),
                                         envelope=_env(295, 350, "aqueous"))
        items = equipment_for_step(step)
        assert EquipmentKind.CONTAINMENT in _kinds(items)
        assert any("fume hood" in it.name for it in items)
