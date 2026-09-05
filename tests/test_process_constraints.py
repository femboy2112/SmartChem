"""Synthetic records test process accounting; none is a chemical procedure."""
from dataclasses import FrozenInstanceError, replace

import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.process_constraints import (
    PROCESS_BOUNDS_SCHEMA, Agitation, Attention, ProcessBounds, ProcessFit,
    ProcessFitStatus, ProcessRequirements, evaluate_process,
)
from smartchem.provenance import SourceCitation, SourceReview


def requirement(**changes):
    fields = dict(
        elapsed_minutes=Interval(20, 30, "min"), active_minutes=Interval(5, 10, "min"),
        attention=Attention.PERIODIC, check_interval_minutes=90,
        agitation=Agitation.PERIODIC, equipment=("fixture-a",), workup_included=True,
        provenance="Synthetic software fixture; not chemistry evidence.",
    )
    fields.update(changes)
    return ProcessRequirements(**fields)


def envelope(process=None):
    process = requirement() if process is None else process
    if not process.is_declared:
        return ConditionEnvelope.unknown()
    return ConditionEnvelope(process=process)


def fit(bounds, *processes):
    return evaluate_process(tuple(envelope(p) for p in (processes or (requirement(),))), bounds)


def test_unknown_requirements_and_unconstrained_are_distinct_from_fit():
    unknown = ProcessRequirements.unknown()
    assert not unknown.is_declared
    assert unknown.equipment is None
    assert not unknown.workup_included
    assert not ProcessBounds.unconstrained().constrains_anything
    assert fit(ProcessBounds(), unknown).status is ProcessFitStatus.UNCONSTRAINED
    assessed = fit(ProcessBounds.quick(), unknown)
    assert assessed.status is ProcessFitStatus.UNKNOWN
    assert assessed.gaps
    assert not assessed.exclusions


def test_every_preset_is_explicit_and_editable():
    quick = ProcessBounds.preset("quick")
    assert quick == ProcessBounds.quick()
    assert (quick.max_step_minutes, quick.max_total_minutes, quick.max_active_minutes) == (60, 120, 60)
    assert quick.allowed_attention is None
    assert quick.available_equipment is None
    assert Agitation.CONTINUOUS not in quick.allowed_agitation
    low = ProcessBounds.preset("low-touch")
    assert (low.max_step_minutes, low.max_total_minutes, low.max_active_minutes) == (10080, 20160, 60)
    assert set(low.allowed_attention) == {Attention.PASSIVE, Attention.PERIODIC}
    assert set(low.allowed_agitation) == {Agitation.NONE, Agitation.PERIODIC}
    assert low.min_check_interval_minutes == 60
    assert replace(low, max_active_minutes=123).max_active_minutes == 123
    assert ProcessBounds.preset("unconstrained") == ProcessBounds()
    with pytest.raises(ValueError, match="unknown process preset"):
        ProcessBounds.preset("unattended-safe")


@pytest.mark.parametrize("name", ["max_step_minutes", "max_total_minutes", "max_active_minutes",
                                 "min_check_interval_minutes"])
@pytest.mark.parametrize("bad", [True, False, "30", [], {}, 1j])
def test_bounds_reject_nonnumeric_and_mutable_values(name, bad):
    with pytest.raises(TypeError):
        ProcessBounds(**{name: bad})


@pytest.mark.parametrize("name", ["max_step_minutes", "max_total_minutes", "max_active_minutes",
                                 "min_check_interval_minutes"])
@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), float("-inf")])
def test_bounds_reject_negative_and_nonfinite_values(name, bad):
    with pytest.raises(ValueError):
        ProcessBounds(**{name: bad})


def test_huge_integers_raise_validation_error_instead_of_numeric_overflow():
    for name in ("max_step_minutes", "max_total_minutes", "max_active_minutes", "min_check_interval_minutes"):
        with pytest.raises(ValueError, match="finite"):
            ProcessBounds(**{name: 10 ** 1000})
    with pytest.raises(ValueError, match="finite"):
        requirement(check_interval_minutes=10 ** 1000)


def test_bounds_canonicalize_numbers_sets_and_freeze():
    one = ProcessBounds(max_step_minutes=30, allowed_attention=(Attention.PERIODIC, Attention.PASSIVE,
                                                              Attention.PERIODIC),
                        available_equipment=(" fixture-b ", "fixture-a", "fixture-a"))
    two = ProcessBounds(max_step_minutes=30.0, allowed_attention=(Attention.PASSIVE, Attention.PERIODIC),
                        available_equipment=("fixture-a", "fixture-b"))
    assert one.digest == two.digest
    assert type(one.max_step_minutes) is float
    assert one.schema_version == PROCESS_BOUNDS_SCHEMA
    assert one.available_equipment == ("fixture-a", "fixture-b")
    with pytest.raises(FrozenInstanceError):
        one.max_step_minutes = 40
    with pytest.raises(ValueError):
        ProcessBounds(schema_version="v999")


@pytest.mark.parametrize("changes", [
    {"allowed_attention": [Attention.PASSIVE]}, {"allowed_attention": ("PASSIVE",)},
    {"allowed_attention": (Agitation.NONE,)}, {"allowed_agitation": [Agitation.NONE]},
    {"allowed_agitation": ("NONE",)}, {"allowed_agitation": (Attention.PASSIVE,)},
    {"available_equipment": ["fixture-a"]}, {"available_equipment": ("",)},
    {"available_equipment": ("  ",)}, {"available_equipment": (None,)},
])
def test_bounds_reject_untyped_sets(changes):
    with pytest.raises(TypeError):
        ProcessBounds(**changes)


@pytest.mark.parametrize("changes", [
    {"elapsed_minutes": 30}, {"active_minutes": [0, 2]},
    {"attention": "PERIODIC"}, {"agitation": "NONE"},
    {"attention": Agitation.PERIODIC}, {"agitation": Attention.PERIODIC},
    {"check_interval_minutes": True}, {"check_interval_minutes": "60"},
    {"equipment": ["fixture-a"]}, {"equipment": ("  ",)},
    {"workup_included": 1}, {"provenance": []}, {"source": "https://example.org"},
])
def test_requirements_reject_untyped_values(changes):
    with pytest.raises(TypeError):
        requirement(**changes)


@pytest.mark.parametrize("name", ["elapsed_minutes", "active_minutes"])
@pytest.mark.parametrize("bad", [Interval(-1, 2, "min"), Interval(0, 1, "h"), Interval(0, 1, "s")])
def test_requirements_enforce_nonnegative_minutes(name, bad):
    with pytest.raises(ValueError):
        requirement(**{name: bad})


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf")])
def test_check_interval_must_be_positive_finite(bad):
    with pytest.raises(ValueError):
        requirement(check_interval_minutes=bad)


def test_declared_requirements_need_real_provenance_and_no_source_only_record():
    for fields in ({"equipment": ()}, {"workup_included": True}, {"attention": Attention.PASSIVE}):
        with pytest.raises(ValueError, match="provenance"):
            ProcessRequirements(**fields)
    with pytest.raises(ValueError, match="provenance"):
        requirement(provenance="  ")
    with pytest.raises(ValueError, match="accompany"):
        ProcessRequirements(provenance="source only")
    with pytest.raises(ValueError, match="accompany"):
        ProcessRequirements(source=SourceCitation("https://example.org/fixture"))


def test_requirements_canonicalize_and_freeze():
    one = requirement(check_interval_minutes=90, equipment=(" fixture-b ", "fixture-a", "fixture-a"))
    two = requirement(check_interval_minutes=90.0, equipment=("fixture-a", "fixture-b"))
    assert one.digest == two.digest
    assert type(one.check_interval_minutes) is float
    assert one.equipment == ("fixture-a", "fixture-b")
    with pytest.raises(FrozenInstanceError):
        one.workup_included = False


@pytest.mark.parametrize("name", ["peak_temperature_k", "min_pressure_atm", "max_pressure_atm"])
@pytest.mark.parametrize("bad", [True, False, "1", [], {}, 1j])
def test_whole_step_extrema_reject_nonnumeric_or_mutable_values(name, bad):
    with pytest.raises(TypeError):
        requirement(**{name: bad})


@pytest.mark.parametrize("name", ["peak_temperature_k", "min_pressure_atm", "max_pressure_atm"])
@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), float("-inf"), 10 ** 1000])
def test_whole_step_extrema_must_be_finite_positive(name, bad):
    with pytest.raises(ValueError):
        requirement(**{name: bad})


def test_whole_step_pressure_order_and_canonical_identity():
    with pytest.raises(ValueError, match="min_pressure_atm cannot exceed"):
        requirement(min_pressure_atm=2, max_pressure_atm=1)
    left = requirement(peak_temperature_k=400, min_pressure_atm=1, max_pressure_atm=1)
    right = requirement(peak_temperature_k=400.0, min_pressure_atm=1.0, max_pressure_atm=1.0)
    assert left.digest == right.digest
    assert type(left.peak_temperature_k) is float
    assert type(left.min_pressure_atm) is float
    assert type(left.max_pressure_atm) is float
    assert left.digest != replace(left, peak_temperature_k=500).digest
    assert left.digest != replace(left, min_pressure_atm=0.5).digest
    assert left.digest != replace(left, max_pressure_atm=2).digest
    with pytest.raises(FrozenInstanceError):
        left.peak_temperature_k = 500


@pytest.mark.parametrize("name", ["peak_temperature_k", "min_pressure_atm", "max_pressure_atm"])
def test_whole_step_extrema_are_independent_declared_facts_requiring_provenance(name):
    unknown = ProcessRequirements.unknown()
    assert getattr(unknown, name) is None
    assert not unknown.is_declared
    with pytest.raises(ValueError, match="non-empty provenance"):
        ProcessRequirements(**{name: 1})
    declared = ProcessRequirements(**{name: 1, "provenance": "Synthetic software fixture."})
    assert declared.is_declared
    # An extremum cannot silently establish scope for the other requirements.
    assert not declared.workup_included
    assert fit(ProcessBounds.quick(), declared).status is ProcessFitStatus.UNKNOWN


def test_workup_scope_and_reaction_temperature_do_not_fill_unknown_process_extrema():
    process = requirement()
    assert process.workup_included
    assert process.peak_temperature_k is None
    assert process.min_pressure_atm is None
    assert process.max_pressure_atm is None
    physical = ConditionEnvelope(temperature=Interval(290, 300, "K"), pressure=Interval(1, 1, "atm"),
                                 process=process, status=EvidenceStatus.EXPERIMENTAL,
                                 provenance="Synthetic software fixture.")
    assert physical.process.peak_temperature_k is None
    assert physical.process.min_pressure_atm is None
    assert physical.process.max_pressure_atm is None


def test_impossible_active_duration_is_rejected_without_assuming_interval_correlation():
    with pytest.raises(ValueError, match="entire elapsed range"):
        requirement(elapsed_minutes=Interval(5, 10, "min"), active_minutes=Interval(11, 20, "min"))
    # Overlapping uncertainty ranges can still represent physically possible pairs.
    assert requirement(elapsed_minutes=Interval(5, 15, "min"),
                       active_minutes=Interval(1, 20, "min")).is_declared


def test_positive_control_and_one_dimension_mutations():
    base = requirement()
    assert fit(ProcessBounds.quick(), base).status is ProcessFitStatus.FITS
    assert fit(ProcessBounds.low_touch(), base).status is ProcessFitStatus.FITS
    mutations = (
        {"elapsed_minutes": Interval(30, 10081, "min")},
        {"active_minutes": Interval(1, 61, "min")},
        {"attention": Attention.CONTINUOUS, "check_interval_minutes": None},
        {"check_interval_minutes": 59},
        {"agitation": Agitation.CONTINUOUS},
    )
    for mutation in mutations:
        result = fit(ProcessBounds.low_touch(), replace(base, **mutation))
        assert result.status is ProcessFitStatus.EXCLUDED, mutation
        assert result.exclusions


@pytest.mark.parametrize("field", ["elapsed_minutes", "active_minutes", "attention", "agitation"])
def test_deleting_constrained_dimension_changes_fit_to_unknown(field):
    result = fit(ProcessBounds.low_touch(), requirement(**{field: None}))
    assert result.status is ProcessFitStatus.UNKNOWN
    assert any(field in gap for gap in result.gaps)


def test_periodic_missing_check_interval_is_unknown_but_passive_needs_none():
    bounds = ProcessBounds(min_check_interval_minutes=60)
    assert fit(bounds, requirement(check_interval_minutes=None)).status is ProcessFitStatus.UNKNOWN
    assert fit(bounds, requirement(attention=Attention.PASSIVE, check_interval_minutes=None)).status is ProcessFitStatus.FITS
    assert fit(bounds, requirement(attention=None)).status is ProcessFitStatus.UNKNOWN
    assert fit(bounds, requirement(attention=Attention.CONTINUOUS, check_interval_minutes=None)).status is ProcessFitStatus.EXCLUDED
    assert fit(ProcessBounds(min_check_interval_minutes=0),
               requirement(attention=Attention.CONTINUOUS, check_interval_minutes=None)).status is ProcessFitStatus.FITS


@pytest.mark.parametrize("attention", [Attention.PASSIVE, Attention.CONTINUOUS])
def test_nonperiodic_modes_cannot_hide_explicit_required_check_intervals(attention):
    with pytest.raises(ValueError, match="requires periodic attention"):
        requirement(attention=attention, check_interval_minutes=5)


def test_unknown_attention_cannot_hide_a_known_check_interval_violation():
    requirements = requirement(attention=None, check_interval_minutes=5)
    result = fit(ProcessBounds.low_touch(), requirements)
    assert result.status is ProcessFitStatus.EXCLUDED
    assert any("required check interval 5" in reason for reason in result.exclusions)
    assert any("attention" in gap for gap in result.gaps)
    # Paying only the known interval debt still leaves the missing mode unresolved.
    relaxed = fit(ProcessBounds.low_touch(), replace(requirements, check_interval_minutes=90))
    assert relaxed.status is ProcessFitStatus.UNKNOWN
    assert not relaxed.exclusions
    # Removing the independent allowed-attention bound must not erase the known
    # violation or the missing mode needed to assess attention demands.
    minimum_only = fit(ProcessBounds(min_check_interval_minutes=60), requirements)
    assert minimum_only.status is ProcessFitStatus.EXCLUDED
    assert minimum_only.exclusions and minimum_only.gaps


def test_missing_unconstrained_dimensions_do_not_create_false_gaps():
    p = ProcessRequirements(elapsed_minutes=Interval(1, 5, "min"), workup_included=True,
                            provenance="Synthetic software fixture.")
    assert fit(ProcessBounds(max_step_minutes=5), p).status is ProcessFitStatus.FITS
    result = fit(ProcessBounds(max_active_minutes=5), p)
    assert result.status is ProcessFitStatus.UNKNOWN
    assert len(result.gaps) == 1


def test_whole_step_scope_is_required_for_every_active_process_bound():
    for bounds in (ProcessBounds(max_step_minutes=30), ProcessBounds(allowed_attention=(Attention.PERIODIC,)),
                   ProcessBounds(allowed_agitation=(Agitation.PERIODIC,)), ProcessBounds(available_equipment=("fixture-a",))):
        result = fit(bounds, requirement(workup_included=False))
        assert result.status is ProcessFitStatus.UNKNOWN
        assert any("workup" in gap for gap in result.gaps)


def test_boundary_equality_is_permitted_and_route_active_is_a_sum():
    base = requirement()
    bounds = ProcessBounds(max_step_minutes=30, max_total_minutes=60, max_active_minutes=20,
                           min_check_interval_minutes=90)
    assert fit(bounds, base, base).status is ProcessFitStatus.FITS
    for changes in ({"max_step_minutes": 29.9}, {"max_total_minutes": 59.9},
                    {"max_active_minutes": 19.9}, {"min_check_interval_minutes": 90.1}):
        assert fit(replace(bounds, **changes), base, base).status is ProcessFitStatus.EXCLUDED


def test_known_violation_wins_over_unknown_and_preserves_both_reasons():
    result = fit(ProcessBounds(max_total_minutes=20, max_active_minutes=5),
                 requirement(), ProcessRequirements.unknown())
    assert result.status is ProcessFitStatus.EXCLUDED
    assert len(result.exclusions) == 2
    assert result.gaps
    result = fit(ProcessBounds(max_total_minutes=120), requirement(), ProcessRequirements.unknown())
    assert result.status is ProcessFitStatus.UNKNOWN
    assert not result.exclusions


def test_total_uses_upper_bounds_not_midpoints_or_averages():
    p = requirement(elapsed_minutes=Interval(0, 50, "min"), active_minutes=Interval(0, 30, "min"))
    assert fit(ProcessBounds(max_total_minutes=90), p, p).status is ProcessFitStatus.EXCLUDED
    assert fit(ProcessBounds(max_active_minutes=50), p, p).status is ProcessFitStatus.EXCLUDED


def test_finite_individual_durations_cannot_crash_sum_via_overflow():
    p = requirement(elapsed_minutes=Interval(0, 1e308, "min"), active_minutes=Interval(0, 1e308, "min"))
    result = fit(ProcessBounds(max_total_minutes=1e308, max_active_minutes=1e308), p, p)
    assert result.status is ProcessFitStatus.EXCLUDED
    assert len(result.exclusions) == 2


def test_equipment_requires_entire_declared_set_and_distinguishes_none_from_unknown():
    bounds = ProcessBounds(available_equipment=("fixture-a",))
    assert fit(bounds).status is ProcessFitStatus.FITS
    assert fit(bounds, requirement(equipment=("fixture-a", "fixture-b"))).status is ProcessFitStatus.EXCLUDED
    assert fit(bounds, requirement(equipment=None)).status is ProcessFitStatus.UNKNOWN
    assert fit(ProcessBounds(available_equipment=()), requirement(equipment=())).status is ProcessFitStatus.FITS
    assert fit(ProcessBounds(available_equipment=()), requirement(equipment=None)).status is ProcessFitStatus.UNKNOWN
    assert fit(ProcessBounds(available_equipment=())).status is ProcessFitStatus.EXCLUDED


def test_empty_allowed_sets_are_active_exclusions_not_unconstrained():
    for bounds in (ProcessBounds(allowed_attention=()), ProcessBounds(allowed_agitation=())):
        assert bounds.constrains_anything
        assert fit(bounds).status is ProcessFitStatus.EXCLUDED
        assert fit(bounds, ProcessRequirements.unknown()).status is ProcessFitStatus.UNKNOWN


def test_no_inference_from_temperature_medium_or_legacy_duration():
    e = ConditionEnvelope(temperature=Interval(290, 300, "K"), duration=Interval(1, 2, "min"),
                          medium="synthetic fixture", status=EvidenceStatus.EXPERIMENTAL,
                          provenance="Synthetic software fixture.")
    result = evaluate_process((e,), ProcessBounds.quick())
    assert result.status is ProcessFitStatus.UNKNOWN
    for field in ("elapsed_minutes", "active_minutes", "agitation", "workup"):
        assert any(field in gap for gap in result.gaps)


def test_reviewed_source_does_not_fill_unknown_fields_or_validate_process():
    p = ProcessRequirements(attention=Attention.PASSIVE, workup_included=True,
                            provenance="Synthetic citation fixture; no real evidence.",
                            source=SourceCitation("https://example.org/fixture", SourceReview.ACCEPTED))
    assert fit(ProcessBounds.quick(), p).status is ProcessFitStatus.UNKNOWN
    assert fit(ProcessBounds(allowed_attention=(Attention.PASSIVE,)), p).status is ProcessFitStatus.FITS


def test_empty_route_is_unknown_only_when_constrained_and_inputs_are_typed():
    assert evaluate_process((), ProcessBounds.quick()).status is ProcessFitStatus.UNKNOWN
    assert evaluate_process((), ProcessBounds()).status is ProcessFitStatus.UNCONSTRAINED
    with pytest.raises(TypeError):
        evaluate_process(({},), ProcessBounds())
    with pytest.raises(TypeError):
        evaluate_process((envelope(),), {})


@pytest.mark.parametrize("args", [
    ("FITS",), (ProcessFitStatus.EXCLUDED,), (ProcessFitStatus.UNKNOWN,),
    (ProcessFitStatus.FITS, (), ("unknown",)), (ProcessFitStatus.UNCONSTRAINED, (), ("unknown",)),
    (ProcessFitStatus.UNKNOWN, ("violation",), ("unknown",)),
    (ProcessFitStatus.FITS, [], ()), (ProcessFitStatus.UNKNOWN, (), ("",)),
])
def test_fit_record_cannot_misrepresent_disposition(args):
    with pytest.raises((TypeError, ValueError)):
        ProcessFit(*args)


def test_description_reports_selected_dimensions_and_empty_inventory():
    assert ProcessBounds().describe() == "unconstrained"
    text = ProcessBounds(max_step_minutes=5, max_total_minutes=10, max_active_minutes=2,
                         allowed_attention=(Attention.PASSIVE,), allowed_agitation=(Agitation.NONE,),
                         min_check_interval_minutes=60, available_equipment=()).describe()
    for part in ("step<=5 min", "route<=10 min", "active route<=2 min", "attention=passive",
                 "agitation=none", "check interval>=60 min", "equipment=none"):
        assert part in text


class TestElapsedFloor:
    """A SOURCED lower bound (whole-step ceiling unknown) may only EXCLUDE, never confirm a fit."""

    def test_floor_over_a_step_limit_excludes_even_with_no_ceiling(self):
        # min_elapsed 84, no ceiling; step limit 60 -> proven too long -> EXCLUDED.
        req = requirement(elapsed_minutes=None, min_elapsed_minutes=84)
        result = fit(ProcessBounds(max_step_minutes=60), req)
        assert result.status is ProcessFitStatus.EXCLUDED
        assert any("minimum elapsed 84 min exceeds step limit 60 min" in e for e in result.exclusions)

    def test_floor_under_a_limit_never_launders_an_unknown_ceiling_into_a_pass(self):
        # THE soundness point: floor 30 < limit 60, but the ceiling is unknown -> UNKNOWN (a gap), NOT FITS.
        req = requirement(elapsed_minutes=None, min_elapsed_minutes=30)
        result = fit(ProcessBounds(max_step_minutes=60), req)
        assert result.status is ProcessFitStatus.UNKNOWN
        assert any("elapsed_minutes is undeclared" in g for g in result.gaps)

    def test_active_floor_over_the_active_limit_excludes(self):
        req = requirement(active_minutes=None, elapsed_minutes=None, min_active_minutes=70)
        result = fit(ProcessBounds(max_active_minutes=60), req)
        assert result.status is ProcessFitStatus.EXCLUDED
        assert any("minimum active 70 min exceeds active limit 60 min" in e for e in result.exclusions)

    def test_route_total_floor_sum_excludes_despite_unknown_ceilings(self):
        # Two steps, each a known 40-min floor, no ceilings; route total limit 60 -> sum 80 > 60 -> EXCLUDED.
        step = requirement(elapsed_minutes=None, min_elapsed_minutes=40)
        result = fit(ProcessBounds(max_total_minutes=60), step, step)
        assert result.status is ProcessFitStatus.EXCLUDED
        assert any("known minimum elapsed sum" in e for e in result.exclusions)

    def test_a_floor_makes_the_record_declared(self):
        assert ProcessRequirements(min_elapsed_minutes=30, provenance="fixture").is_declared

    def test_floor_cannot_exceed_a_declared_ceiling(self):
        with pytest.raises(ValueError):
            ProcessRequirements(min_elapsed_minutes=50, elapsed_minutes=Interval(10, 40, "min"),
                                provenance="fixture")

    def test_min_active_cannot_exceed_min_elapsed(self):
        with pytest.raises(ValueError):
            ProcessRequirements(min_active_minutes=50, min_elapsed_minutes=40, provenance="fixture")

    def test_min_active_cannot_exceed_the_declared_elapsed_ceiling(self):
        # active is a subset of elapsed: an active floor above the elapsed ceiling is impossible
        # (mirrors the interval guard active_minutes.lo <= elapsed_minutes.hi).
        with pytest.raises(ValueError):
            ProcessRequirements(min_active_minutes=100, elapsed_minutes=Interval(0, 50, "min"),
                                provenance="fixture")

    def test_route_total_floor_sum_counts_interval_lower_bounds_too(self):
        # A mixed route: step A a floor-only 40 min (no ceiling), step B an interval [40, 50]. The
        # per-step ceiling check sees only B (50 <= 60) and a floors-only sum would see only A, but
        # the KNOWN minimum total 40 + 40 = 80 > the 60-min route limit must EXCLUDE -- an interval
        # .lo is a known minimum too, so it cannot be ignored by the route floor sum.
        a = requirement(elapsed_minutes=None, min_elapsed_minutes=40)
        b = requirement(elapsed_minutes=Interval(40, 50, "min"))
        result = fit(ProcessBounds(max_total_minutes=60), a, b)
        assert result.status is ProcessFitStatus.EXCLUDED
        assert any("known minimum elapsed sum 80 min" in e for e in result.exclusions)

    @pytest.mark.parametrize("bad", [-5, 0, float("inf"), float("nan")])
    def test_a_nonpositive_or_nonfinite_floor_is_rejected(self, bad):
        with pytest.raises((ValueError, TypeError)):
            ProcessRequirements(min_elapsed_minutes=bad, provenance="fixture")
