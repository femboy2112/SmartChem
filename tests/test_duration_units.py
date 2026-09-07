"""The duration admission boundary uses minutes, including during route replay.

The prerelease baseline admitted hours, seconds, and even kelvin into the same field. These
controls pin explicit minute admission without claiming that a declared duration is a sourced
intermediate hold or wiring the standalone seconds-based survival primitive into core E1.
"""

import json

import pytest

from smartchem.conditions import ConditionEnvelope, EvidenceStatus, Interval
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.service import (
    _condition_envelope_from_payload,
    _condition_envelope_to_payload,
    _reconstruct_route,
    _steps_to_replay_payload,
)
from smartchem.smiles import parse_smiles


_PROVENANCE = "synthetic duration unit control; no experimental claim"


def _envelope(duration):
    return ConditionEnvelope(
        duration=duration, status=EvidenceStatus.EXPERIMENTAL, provenance=_PROVENANCE,
    )


def _route():
    water = parse_smiles("O")
    return ExperimentRoute.of(ExperimentStep.assembling(
        water, (water,), (water,), envelope=_envelope(Interval(30, 90, "min")),
    ))


@pytest.mark.parametrize("lo,hi", [(0, 0), (0, 1), (0.125, 0.5), (30, 90)])
def test_minutes_preserve_both_declared_bounds(lo, hi):
    env = _envelope(Interval(lo, hi, "min"))
    assert env.duration == Interval(lo, hi, "min")
    back = _condition_envelope_from_payload(json.loads(json.dumps(_condition_envelope_to_payload(env))))
    assert back == env
    assert back.digest == env.digest


def test_unspecified_duration_stays_unknown():
    env = ConditionEnvelope.unknown()
    assert env.duration is None
    assert _condition_envelope_from_payload(_condition_envelope_to_payload(env)) == env


@pytest.mark.parametrize("unit", ["h", "s", "ms", "day", "K", "atm", "minutes", "MIN", " min", "min "])
def test_other_units_require_conversion_before_declaration(unit):
    with pytest.raises(ValueError, match="duration intervals must use unit 'min'.*convert explicitly"):
        _envelope(Interval(1, 2, unit))


@pytest.mark.parametrize("duration", [True, 2, 2.0, "2 min", (1, 2, "min"), {"lo": 1, "hi": 2, "unit": "min"}])
def test_duration_requires_a_typed_interval(duration):
    with pytest.raises(TypeError, match="duration must be an Interval or None"):
        _envelope(duration)


@pytest.mark.parametrize("lo,hi", [(-2, -1), (-1, 0), (-1, 1)])
def test_negative_minute_bounds_are_refused(lo, hi):
    with pytest.raises(ValueError, match="duration must be nonnegative"):
        _envelope(Interval(lo, hi, "min"))


@pytest.mark.parametrize("bound", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("endpoint", ["lo", "hi"])
def test_nonfinite_duration_bounds_are_refused(endpoint, bound):
    values = {"lo": 0, "hi": 1, "unit": "min", endpoint: bound}
    with pytest.raises(ValueError, match="must be finite"):
        _envelope(Interval(**values))


@pytest.mark.parametrize("bound", [True, False, "1", None])
@pytest.mark.parametrize("endpoint", ["lo", "hi"])
def test_duration_bounds_are_not_coerced_from_other_types(endpoint, bound):
    values = {"lo": 0, "hi": 1, "unit": "min", endpoint: bound}
    with pytest.raises(TypeError, match="must be a real number"):
        _envelope(Interval(**values))


def test_reversed_duration_interval_is_refused():
    with pytest.raises(ValueError, match="must be <= hi"):
        _envelope(Interval(2, 1, "min"))


@pytest.mark.parametrize("unit", [None, False, 1, ["min"], ""])
def test_missing_or_untyped_duration_unit_is_refused(unit):
    with pytest.raises(ValueError, match="interval unit must be a non-empty string"):
        _envelope(Interval(1, 2, unit))


@pytest.mark.parametrize("unit", ["h", "s", "K", "minutes"])
def test_route_replay_rejects_duration_unit_swaps_at_construction(unit):
    payload = _steps_to_replay_payload(_route().steps)
    payload[0]["envelope"]["duration"]["unit"] = unit
    with pytest.raises(ValueError, match="duration intervals must use unit 'min'"):
        _reconstruct_route(json.loads(json.dumps(payload)))


@pytest.mark.parametrize("duration,error", [
    ({"lo": -1, "hi": 1, "unit": "min"}, ValueError),
    ({"lo": 2, "hi": 1, "unit": "min"}, ValueError),
    ({"lo": True, "hi": 1, "unit": "min"}, TypeError),
    ({"lo": 0, "hi": "1", "unit": "min"}, TypeError),
    ({"lo": 0, "hi": float("inf"), "unit": "min"}, ValueError),
    ({"lo": float("nan"), "hi": 1, "unit": "min"}, ValueError),
    ({"lo": 0, "hi": 1, "unit": None}, ValueError),
    ({"lo": 0, "hi": 1}, ValueError),
    ("30 min", ValueError),
])
def test_route_replay_refuses_malformed_duration_data(duration, error):
    payload = _steps_to_replay_payload(_route().steps)
    payload[0]["envelope"]["duration"] = duration
    with pytest.raises(error):
        _reconstruct_route(payload)


def test_legacy_minute_payload_and_route_identity_are_unchanged():
    # Recorded on 043a3cd before the admission guard: route identity must not change with validation.
    route = _route()
    env = route.steps[0].envelope
    assert env.digest == "fe8d6ce76a5f35bf5c50dfa8d058b830c79ffd4295778b292209a05b42bc8bad"
    assert route.digest == "7c0a7a4e000196ee257278aeae7a54f24a9afa1acd72c12566aec590b73473f6"
    assert _condition_envelope_to_payload(env) == {
        "temperature": None, "pressure": None, "duration": {"lo": 30.0, "hi": 90.0, "unit": "min"},
        "medium": "", "catalysts": [], "applied_field": "", "status": "EXPERIMENTAL",
        "provenance": _PROVENANCE, "source": None, "process": None,
    }
    back = _reconstruct_route(json.loads(json.dumps(_steps_to_replay_payload(route.steps))))
    assert back.digest == route.digest


def test_explicit_conversion_preserves_a_range_and_minute_identity():
    # 0.5--1.5 h == 1800--5400 s == 30--90 min. Unit conversion belongs to the caller.
    minutes = _envelope(Interval(30, 90, "min"))
    from_hours = _envelope(Interval(0.5 * 60, 1.5 * 60, "min"))
    from_seconds = _envelope(Interval(1800 / 60, 5400 / 60, "min"))
    assert from_hours.digest == from_seconds.digest == minutes.digest
