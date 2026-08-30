"""The sourced stability seed table -- proven sourced, isomer-specific, extensible, and loud on a miss."""
import pytest

from smartchem.conditions import Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.stability import (
    DEFAULT_STABILITY,
    SEED_STABILITY_REFS,
    StabilityRef,
    StabilityTable,
    stability_for,
    stability_for_named,
)


class TestSeedIsSourced:
    def test_every_seed_record_carries_provenance_and_is_below_certified(self):
        assert SEED_STABILITY_REFS
        for r in SEED_STABILITY_REFS:
            assert r.provenance.strip(), f"{r.name} has no provenance"
            assert r.status is not EvidenceStatus.UNSUPPORTED

    def test_a_record_with_no_provenance_is_refused(self):
        with pytest.raises(ValueError, match="provenance"):
            StabilityRef("H2O", "water", None, None, None, True, "   ")

    def test_temperatures_must_be_kelvin(self):
        with pytest.raises(ValueError, match="kelvin"):
            StabilityRef("H2O", "water", Interval(0, 100, "C"), None, None, True, "src")


class TestLookupAndExtension:
    def test_named_lookup_hits_the_seed(self):
        assert stability_for_named("C8H9NO2", "paracetamol").name == "paracetamol"

    def test_a_miss_is_a_loud_none_not_a_default(self):
        assert stability_for_named("C99H1", "unobtainium") is None
        assert stability_for("C99H1") is None

    def test_with_records_extends_for_any_chemical(self):
        table = DEFAULT_STABILITY.with_records(StabilityRef(
            "C7H6O2", "benzoic acid", Interval(395, 396, "K"), Interval(522, 523, "K"), None, True,
            "CRC: benzoic acid mp 122 C bp 249 C",
        ))
        assert table.for_named("C7H6O2", "benzoic acid").name == "benzoic acid"
        # the seed is preserved, and the default table is unchanged (immutability)
        assert table.for_named("C8H9NO2", "paracetamol") is not None
        assert DEFAULT_STABILITY.for_named("C7H6O2", "benzoic acid") is None

    def test_with_records_overrides_a_seed_record_for_the_same_compound(self):
        override = StabilityRef(
            "H2O", "water", Interval(273, 273, "K"), Interval(373, 373, "K"),
            Interval(9999, 9999, "K"), True, "caller's own sourced water record",
        )
        table = DEFAULT_STABILITY.with_records(override)
        assert table.for_named("H2O", "water").provenance == "caller's own sourced water record"


class TestIsomerAmbiguity:
    def test_formula_level_lookup_refuses_an_ambiguous_formula(self):
        # two isomers share C8H9NO2; a formula-level lookup must not attach one's onset to the other
        table = StabilityTable(()).with_records(
            StabilityRef("C8H9NO2", "paracetamol", None, None, Interval(523, 523, "K"), True, "a"),
            StabilityRef("C8H9NO2", "4-aminophenyl acetate", None, None, None, True, "b"),
        )
        assert table.for_formula("C8H9NO2") is None      # ambiguous -> refuse
        assert table.for_named("C8H9NO2", "paracetamol") is not None  # named is fine


class TestSurvivesTemperature:
    def test_below_onset_survives_at_onset_does_not(self):
        r = stability_for_named("C6H7NO", "4-aminophenol")  # onset 557 K
        assert r.survives_temperature(Interval(300, 400, "K")) is True
        assert r.survives_temperature(Interval(300, 600, "K")) is False

    def test_no_onset_is_none_not_survival(self):
        r = stability_for_named("H2O", "water")  # no decomposition onset tabulated
        assert r.survives_temperature(Interval(300, 400, "K")) is None
