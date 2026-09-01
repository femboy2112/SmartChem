"""E6 -- the bench handling profile: byproduct ledger, off-gasses, hazards, and the care level.

These tests pin the honesty invariants the layer exists to enforce:
* the byproduct ledger is EXACT stoichiometry (a CONSERVATION fact), including coefficients > 1;
* off-gasses are detected by TWO sourced signals (a GHS gas classification, or a Clausius-Clapeyron phase
  call at the step's own conditions), and by neither where the data is absent (a loud UNKNOWN fate);
* the care level is worst-dominated over SOURCED facts, and species records alone never license unattended
  species present is positively assessed -- an unassessed species holds it at UNKNOWN (never a false "safe");
* resolution is isomer-keyed (ethanol and dimethyl ether, both C2H6O, never borrow each other's record).
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from smartchem.contracts import EvidenceStatus
from smartchem.data.hazards import HazardRef
from smartchem.experiment.bucket import Bucket
from smartchem.experiment.handling import (
    ByproductEntry,
    CareLevel,
    Fate,
    RouteHandling,
    handling_of_step,
    verify_handling,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles


# -- fixtures: the litmus family, all covered by the sourced hazard/stability seeds --------------------
def _para():
    return parse_smiles("CC(=O)Nc1ccc(O)cc1")  # paracetamol C8H9NO2


def _pap():
    return parse_smiles("Nc1ccc(O)cc1")  # 4-aminophenol C6H7NO


def _ketene():
    return parse_smiles("C=C=O")  # ketene C2H2O (non-isolable, toxic+flammable gas)


def _ac2o():
    return parse_smiles("CC(=O)OC(C)=O")  # acetic anhydride C4H6O3


def _acoh():
    return parse_smiles("CC(=O)O")  # acetic acid C2H4O2


def _ketene_step() -> ExperimentStep:
    """paracetamol -> 4-aminophenol + ketene: the anhydrous skeleton, ketene as an off-gas byproduct."""
    return ExperimentStep.assembling(_pap(), (_para(),), (_pap(), _ketene()))


def _acetylation_step() -> ExperimentStep:
    """4-aminophenol + acetic anhydride -> paracetamol + acetic acid (the real synthesis)."""
    return ExperimentStep.assembling(_para(), (_pap(), _ac2o()), (_para(), _acoh()), reagents=(_ac2o(),))


# =========================================================================================================
class TestByproductLedger:
    def test_ketene_byproduct_is_one_per_target_and_offgas(self) -> None:
        h = handling_of_step(_ketene_step())
        assert len(h.byproducts) == 1
        bp = h.byproducts[0]
        assert bp.hazard_name == "ketene"
        assert bp.moles_per_target == Fraction(1, 1)
        assert bp.fate is Fate.OFFGAS
        assert bp.is_offgas

    def test_coefficient_greater_than_one_is_exact(self) -> None:
        # methane combustion: CH4 + 2 O2 -> CO2 + 2 H2O ; target CO2, byproduct 2 water per CO2
        ch4, o2 = parse_smiles("C"), parse_smiles("O=O")
        co2, h2o = parse_smiles("O=C=O"), parse_smiles("O")
        step = ExperimentStep.assembling(co2, (ch4, o2, o2), (co2, h2o, h2o))
        h = handling_of_step(step)
        water = [b for b in h.byproducts if b.molecule.formula == h2o.formula]
        assert len(water) == 1
        assert water[0].moles_per_target == Fraction(2, 1)  # exact: two water per CO2

    def test_single_product_step_has_no_byproducts(self) -> None:
        # an assembly with a single product: pap + ketene -> paracetamol (nothing else comes off)
        step = ExperimentStep.assembling(_para(), (_pap(), _ketene()), (_para(),))
        h = handling_of_step(step)
        assert h.byproducts == ()
        assert h.offgases == ()


class TestOffGasDetection:
    def test_ghs_gas_class_marks_offgas_without_temperature(self) -> None:
        # ketene carries H220 (flammable gas): a sourced statement of physical state -> OFFGAS even undeclared T
        h = handling_of_step(_ketene_step())  # no temperature declared
        assert h.offgases and h.offgases[0].hazard_name == "ketene"

    def test_clausius_clapeyron_places_phase_at_step_temperature(self) -> None:
        # acetic acid (bp ~391 K) is a gas above its bp, condensed below -- from sourced bp + dHvap
        step = _acetylation_step()
        hot = handling_of_step(step, temperature_k=420.0)
        cold = handling_of_step(step, temperature_k=350.0)
        acid_hot = [b for b in hot.byproducts if b.hazard_name == "acetic acid"][0]
        acid_cold = [b for b in cold.byproducts if b.hazard_name == "acetic acid"][0]
        assert acid_hot.fate is Fate.OFFGAS
        assert acid_cold.fate is Fate.CONDENSED

    def test_phase_is_unknown_when_temperature_undeclared(self) -> None:
        # acetic acid has a sourced bp+dHvap AND a non-gas GHS code (H226 liquid); with NO declared T the
        # Clausius-Clapeyron call is honestly skipped -> its fate is UNKNOWN, not a guessed CONDENSED.
        h = handling_of_step(_acetylation_step())  # no temperature declared
        acid = [b for b in h.byproducts if b.hazard_name == "acetic acid"][0]
        assert acid.fate is Fate.UNKNOWN


class TestCareLadder:
    def test_toxic_nonisolable_offgas_needs_active_control(self) -> None:
        h = handling_of_step(_ketene_step())
        assert h.care is CareLevel.NEEDS_ACTIVE_CONTROL
        # BOTH sourced triggers named: non-isolable AND toxic off-gas
        blob = " ".join(h.care_reasons).lower()
        assert "non-isolable" in blob
        assert "toxic off-gas" in blob
        assert h.toxic_offgases and h.toxic_offgases[0].hazard_name == "ketene"

    def test_known_hazard_no_blocker_is_attention(self) -> None:
        h = handling_of_step(_acetylation_step())
        assert h.care is CareLevel.ATTENTION_ADVISED
        assert h.unassessed == ()  # every species in the real synthesis is sourced
        assert h.finding.bucket is Bucket.KNOWN_SOURCED
        assert h.finding.value == "ATTENTION_ADVISED"

    def test_unassessed_species_holds_at_unknown_never_safe(self) -> None:
        # cyclopropane -> propene: neither in the hazard seed -> cannot certify safe to leave unattended
        cp, pr = parse_smiles("C1CC1"), parse_smiles("CC=C")
        step = ExperimentStep.assembling(pr, (cp,), (pr,))
        h = handling_of_step(step)
        assert h.care is CareLevel.UNKNOWN
        assert h.care is not CareLevel.PROCEED_UNATTENDED  # the anti-vacuous-green guard
        assert h.unassessed  # the gap is listed loudly
        assert h.finding.bucket is Bucket.UNKNOWN
        assert h.finding.value is None  # no smuggled verdict under the UNKNOWN bucket

    def test_all_benign_assessed_proceeds_unattended(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # PROCEED is reachable only when EVERY species carries a positive (benign) assessed record.
        benign = HazardRef(
            formula="C3H6", name="benign-test", ghs_codes=(), summary="assessed benign",
            reactivity=(), exposure="", regulatory="", provenance="test",
            status=EvidenceStatus.ESTABLISHED,
        )
        monkeypatch.setattr("smartchem.experiment.handling.molecule_hazards", lambda m: benign)
        monkeypatch.setattr("smartchem.experiment.handling.resolve_stability", lambda m, t: None)
        cp, pr = parse_smiles("C1CC1"), parse_smiles("CC=C")
        step = ExperimentStep.assembling(pr, (cp,), (pr,))
        h = handling_of_step(step)
        assert h.care is CareLevel.UNKNOWN
        assert "NOT established" in " ".join(h.care_reasons)
        assert h.unassessed == ()

    def test_known_hazard_not_masked_by_unknown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # a step with one known corrosive AND unassessed species reports the known floor (ATTENTION), not a
        # bare UNKNOWN that would bury the corrosive -- but it NOTES the gap.  acetic acid -> methane + CO2:
        # three DISTINCT formulas, so the resolver can single out the assessed one.
        acid = HazardRef(
            formula="C2H4O2", name="acetic acid", ghs_codes=("H314",), summary="corrosive",
            reactivity=(), exposure="", regulatory="", provenance="test",
            status=EvidenceStatus.ESTABLISHED,
        )
        acoh = _acoh()

        def _selective(m):
            return acid if m.formula == acoh.formula else None  # only acetic acid is assessed

        monkeypatch.setattr("smartchem.experiment.handling.molecule_hazards", _selective)
        monkeypatch.setattr("smartchem.experiment.handling.resolve_stability", lambda m, t: None)
        ch4, co2 = parse_smiles("C"), parse_smiles("O=C=O")
        step = ExperimentStep.assembling(ch4, (acoh,), (ch4, co2))  # acetic acid -> methane + CO2
        h = handling_of_step(step)
        assert h.care is CareLevel.ATTENTION_ADVISED
        assert h.unassessed  # the methane/CO2 gaps are surfaced even though ATTENTION dominates
        assert any("unassessed" in r.lower() for r in h.care_reasons)


class TestIsomerSafety:
    def test_ethanol_and_dimethyl_ether_do_not_borrow(self) -> None:
        # both are C2H6O; ethanol is a flammable LIQUID (H225), DME an extremely flammable GAS (H220).
        # A byproduct that is DME must read OFFGAS; one that is ethanol must not -- no formula-borrow.
        etoh, dme = parse_smiles("CCO"), parse_smiles("COC")
        acid = _acoh()
        # ester saponification-shaped step producing ethanol as a byproduct
        estep = ExperimentStep.assembling(acid, (parse_smiles("CCOC(C)=O"), parse_smiles("O")),
                                          (acid, etoh))
        he = handling_of_step(estep, temperature_k=350.0)
        etoh_bp = [b for b in he.byproducts if b.hazard_name == "ethanol"]
        assert etoh_bp and etoh_bp[0].fate is not Fate.OFFGAS  # ethanol liquid at 350 K, not a gas
        # same formula C2H6O, opposite record -- resolution is structure-keyed, never formula-borrowed
        from smartchem.experiment.handling import _resolve_hazard
        assert _resolve_hazard(dme).name == "dimethyl ether"  # H220 gas
        assert _resolve_hazard(etoh).name == "ethanol"        # H225 liquid


class TestRouteHandling:
    def test_route_care_is_worst_step_dominated(self) -> None:
        # step 1 (acetylation, ATTENTION) -> feeds paracetamol into step 2 (-> pap + ketene, NEEDS_CONTROL)
        s1 = _acetylation_step()
        s2 = _ketene_step()
        route = ExperimentRoute.of(s1, s2)
        rh = verify_handling(route)
        assert isinstance(rh, RouteHandling)
        assert rh.care is CareLevel.NEEDS_ACTIVE_CONTROL  # the ketene step dominates
        # the whole-synthesis off-gas inventory aggregates across steps
        assert any(b.hazard_name == "ketene" for b in rh.all_offgases)
        assert len(rh.all_byproducts) >= 2  # acetic acid + ketene across the two steps

    def test_route_all_benign_still_cannot_license_unattended_operation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        benign = HazardRef(
            formula="X", name="benign-test", ghs_codes=(), summary="assessed benign",
            reactivity=(), exposure="", regulatory="", provenance="test",
            status=EvidenceStatus.ESTABLISHED,
        )
        monkeypatch.setattr("smartchem.experiment.handling.molecule_hazards", lambda m: benign)
        monkeypatch.setattr("smartchem.experiment.handling.resolve_stability", lambda m, t: None)
        cp, pr = parse_smiles("C1CC1"), parse_smiles("CC=C")
        route = ExperimentRoute.of(ExperimentStep.assembling(pr, (cp,), (pr,)))
        assert verify_handling(route).care is CareLevel.UNKNOWN


class TestInputValidation:
    def test_handling_rejects_non_step(self) -> None:
        with pytest.raises(TypeError):
            handling_of_step("not a step")  # type: ignore[arg-type]

    def test_verify_rejects_non_route(self) -> None:
        with pytest.raises(TypeError):
            verify_handling(_ketene_step())  # a step is not a route

    def test_byproduct_entry_rejects_nonpositive_amount(self) -> None:
        with pytest.raises(ValueError):
            ByproductEntry(_ketene(), Fraction(0, 1), Fate.OFFGAS, "ketene", "x")

    def test_route_handling_rejects_empty(self) -> None:
        with pytest.raises(TypeError):
            RouteHandling(())


def test_stephandling_explain_is_chemist_facing() -> None:
    h = handling_of_step(_ketene_step())
    text = h.explain()
    assert "NEEDS_ACTIVE_CONTROL" in text
    assert "ketene" in text
    assert "OFFGAS" in text
