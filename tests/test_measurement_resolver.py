"""Vitals check for the v0.9 measurement-method vocabulary + resolver (FREEZE decision 5).

Purely additive tissue: nothing consumes ``MeasurementMethod`` or ``classify_measurement_strings`` yet
(a sibling wave wires them in), so these tests stand alone and prove the incision cures the right thing --
a closed, specific, fail-closed method vocabulary that never launders the coarse tier into a verdict.
"""
from smartchem.capability.enums import (
    MEASUREMENT_TIER_OF,
    MeasurementCapability,
    MeasurementMethod,
)
from smartchem.capability.measurement_resolver import classify_measurement_strings


def test_enum_has_exactly_the_three_forced_methods():
    # Decision 5 freezes exactly three genuine instrument methods -- no FeCl3 spot test, no percent yield.
    assert set(MeasurementMethod) == {
        MeasurementMethod.MASS,
        MeasurementMethod.MELTING_POINT,
        MeasurementMethod.INFRARED_SPECTROSCOPY,
    }


def test_tier_map_covers_every_method_and_groups_correctly():
    # The display/grouping map is total over the enum and matches decision 5's tiering.
    assert MEASUREMENT_TIER_OF == {
        MeasurementMethod.MASS: MeasurementCapability.CHEAP_INSTRUMENT,
        MeasurementMethod.MELTING_POINT: MeasurementCapability.CHEAP_INSTRUMENT,
        MeasurementMethod.INFRARED_SPECTROSCOPY: MeasurementCapability.ANALYTICAL_INSTRUMENT,
    }


def test_infrared_is_the_only_analytical_instrument():
    # The M28 anatomy: IR is the sole ANALYTICAL_INSTRUMENT, so a tier-level verdict would over-admit it.
    analytical = [
        method
        for method, tier in MEASUREMENT_TIER_OF.items()
        if tier is MeasurementCapability.ANALYTICAL_INSTRUMENT
    ]
    assert analytical == [MeasurementMethod.INFRARED_SPECTROSCOPY]


def test_known_strings_resolve_case_insensitively():
    recognized, ignored, unrecognized = classify_measurement_strings(
        ("Analytical Balance", "  infrared spectrometer  ", "MELTING POINT APPARATUS")
    )
    assert recognized == {
        MeasurementMethod.MASS,
        MeasurementMethod.INFRARED_SPECTROSCOPY,
        MeasurementMethod.MELTING_POINT,
    }
    assert ignored == frozenset()
    assert unrecognized == ()


def test_unknown_strings_land_in_unrecognized_never_silently_accepted():
    recognized, ignored, unrecognized = classify_measurement_strings(
        ("rotary evaporator", "gc-ms", "analytical balance")
    )
    # The one known string resolves; the two strangers are carried, not dropped, not guessed.
    assert recognized == {MeasurementMethod.MASS}
    assert ignored == frozenset()
    assert set(unrecognized) == {"rotary evaporator", "gc-ms"}
    # Fail-closed: an unrecognized string never leaks into the recognized-method set.
    assert MeasurementMethod.MASS in recognized
    assert len(recognized) == 1


def test_empty_input_yields_all_empty():
    recognized, ignored, unrecognized = classify_measurement_strings(())
    assert recognized == frozenset()
    assert ignored == frozenset()
    assert unrecognized == ()


def test_unrecognized_is_a_deterministic_deduped_tuple():
    _, _, unrecognized = classify_measurement_strings(
        ("gc-ms", "rotary evaporator", "gc-ms")
    )
    # First-seen order, de-duplicated -- a stable tuple, not a reordered set.
    assert unrecognized == ("gc-ms", "rotary evaporator")
