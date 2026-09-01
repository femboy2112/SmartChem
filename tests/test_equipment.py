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
from smartchem.provenance import SourceCitation, SourceReview
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

    def test_render_keeps_declared_evidence_bucket_visible(self):
        item = equipment_for_envelope(_env(295, 310, "aqueous"))[0]
        rendered = item.render()
        assert "[COMPOSABILITY:" in rendered
        assert "not source-attested" in rendered

    def test_sourced_condition_render_includes_accepted_locator(self):
        env = ConditionEnvelope(
            temperature=Interval(295, 310, "K"),
            medium="aqueous",
            status=EvidenceStatus.EXPERIMENTAL,
            provenance="reviewed teaching synthesis",
            source=SourceCitation(
                "https://doi.org/10.1021/acs.jchemed.0c01512", SourceReview.ACCEPTED
            ),
        )
        rendered = equipment_for_envelope(env)[0].render()
        assert "[KNOWN_SOURCED:" in rendered
        assert "https://doi.org/10.1021/acs.jchemed.0c01512" in rendered

    def test_gentle_aqueous_heating_is_a_hotplate_and_volumetric(self):
        items = equipment_for_envelope(_env(295, 350, "aqueous, volumetric make-up"))
        assert EquipmentKind.HEATING in _kinds(items)
        assert EquipmentKind.MEASURING in _kinds(items)
        assert any("hotplate" in it.name or "water bath" in it.name for it in items)

    def test_strong_heat_does_not_auto_clear_an_open_flame(self):
        items = equipment_for_envelope(_env(298, 900, "aqueous"))
        assert any("electric" in it.name or "furnace" in it.name for it in items)
        assert not any("Bunsen" in it.name for it in items)

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

    def test_benign_water_record_does_not_require_a_fume_hood(self):
        water = parse_smiles("O")
        step = ExperimentStep.assembling(water, (water,), (water,), envelope=_env(295, 310, "aqueous"))
        items = equipment_for_step(step)
        assert EquipmentKind.CONTAINMENT not in _kinds(items)

    def test_species_flammability_vetoes_open_flame_independent_of_medium_spelling(self):
        ethanol = parse_smiles("CCO")
        acetaldehyde = parse_smiles("CC=O")
        hydrogen = parse_smiles("[H][H]")
        step = ExperimentStep.assembling(
            ethanol, (acetaldehyde, hydrogen), (ethanol,), envelope=_env(450, 500, "bulk reaction")
        )
        items = equipment_for_step(step)
        assert any("non-flame" in it.name for it in items)
        assert not any("Bunsen" in it.name for it in items)
