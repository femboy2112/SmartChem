"""Round-III Wave-C regression guards: the two false-FIT / fail-open holes the fresh hostile review
(evil-morty directed + dalembert structure-theorem) proved, and the parent then fixed.

F1 (P0, release-blocking): ``_physical_axis`` dropped any route demand on a dimension the profile
ceiling left ``None`` while it constrained a DIFFERENT dimension -> a temp-only bench rode a real
pressure demand (or a pressure-only bench a real temperature demand) straight to FIT. D6's all-``None``
guard fired only when the ceiling constrained NOTHING; the fix applies it PER DIMENSION.

F2 (fail-open): ``_monetary_axis``'s ``if x and y and x != y`` denomination guards skipped on an EMPTY
string, so a cost that failed to record its currency/unit was treated as commensurable with any budget.
The fix is fail-closed: to compare cash at all, BOTH sides must declare a currency AND a unit, matching.
"""
from __future__ import annotations

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import _monetary_axis, _physical_axis, assess
from smartchem.capability.enums import CapabilityStatus
from smartchem.capability.presets import isopentyl_capability_fit_bench
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.constraints import PhysicalBounds
from smartchem.experiment import routes as rt
from smartchem.experiment.affordability import CostVector
from smartchem.experiment.readiness import evaluate_route
from smartchem.identity_parse import InputKind, resolve_target

_CERT = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)


# -- F1: physical axis is fail-closed PER DIMENSION -----------------------------------------------------------

def test_f1_temp_only_ceiling_does_not_launder_a_real_pressure_demand():
    """dalembert's kill: a bench that declares a temperature ceiling but NO pressure bound must NOT ride a
    real pressure demand to FIT. The demanded-but-unbounded dimension is UNKNOWN (fail-closed)."""
    demand = PhysicalBounds.of(max_temperature_k=350.0, max_pressure_atm=100.0)  # a real 100 atm demand
    temp_only = PhysicalBounds.of(max_temperature_k=500.0)  # NO pressure ceiling
    assert _physical_axis(demand, temp_only).status is CapabilityStatus.UNKNOWN


def test_f1_pressure_only_ceiling_does_not_launder_a_real_temperature_demand():
    """evil-morty's kill (symmetric): a pressure-only bench must NOT ride a real temperature demand to FIT."""
    demand = PhysicalBounds.of(max_temperature_k=416.15, max_pressure_atm=1.0)
    pressure_only = PhysicalBounds.of(max_pressure_atm=2.0)  # NO temperature ceiling
    assert _physical_axis(demand, pressure_only).status is CapabilityStatus.UNKNOWN


def test_f1_monotonicity_adding_an_unrelated_bound_never_launders_unknown_to_fit():
    """dalembert's incision: the SAME 100 atm demand under three ceilings must be monotone --
    all-None -> UNKNOWN, temp-only -> UNKNOWN (the fixed hole, was FIT), temp+pressure(<demand) -> BLOCKED.
    Adding an unrelated temperature bound must NEVER flip an unmet pressure demand UNKNOWN -> FIT."""
    demand = PhysicalBounds.of(max_pressure_atm=100.0)
    assert _physical_axis(demand, PhysicalBounds.unconstrained()).status is CapabilityStatus.UNKNOWN
    assert _physical_axis(demand, PhysicalBounds.of(max_temperature_k=500.0)).status is CapabilityStatus.UNKNOWN
    assert _physical_axis(
        demand, PhysicalBounds.of(max_temperature_k=500.0, max_pressure_atm=2.0)
    ).status is CapabilityStatus.BLOCKED


def test_f1_fully_declared_ceiling_covering_every_demanded_dimension_still_fits():
    """The fix must NOT be over-strict: a ceiling that declares every dimension the route demands, all
    within, is still FIT -- the atmospheric-floor declaration is exactly what keeps the FIT positive alive."""
    demand = PhysicalBounds.of(max_temperature_k=416.15, max_pressure_atm=1.0, min_pressure_atm=1.0)
    full = PhysicalBounds.of(max_temperature_k=500.0, max_pressure_atm=2.0, min_pressure_atm=1.0)
    assert _physical_axis(demand, full).status is CapabilityStatus.FIT


# -- F2: monetary axis is fail-closed on an empty/undeclared denominator ---------------------------------------

def _budget():
    return CostVector(cash=200.0, currency="USD", unit="USD")


def test_f2_empty_denominator_is_unknown_not_a_wildcard_fit():
    """A cost that failed to record its currency AND unit (empty strings) must NOT compare as commensurable
    with a USD/USD budget -- an unestablished basis is UNKNOWN, never a raw-number FIT."""
    assert _monetary_axis(CostVector(cash=5.0, currency="", unit=""), _budget()).status is CapabilityStatus.UNKNOWN


def test_f2_empty_unit_alone_is_unknown():
    assert _monetary_axis(CostVector(cash=5.0, currency="USD", unit=""), _budget()).status is CapabilityStatus.UNKNOWN


def test_f2_matching_denomination_still_compares_and_fits():
    """The fail-closed guard must NOT break the legitimate same-denomination compare."""
    assert _monetary_axis(CostVector(cash=5.0, currency="USD", unit="USD"), _budget()).status is CapabilityStatus.FIT


def test_f2_mismatched_denomination_is_unknown():
    got = _monetary_axis(CostVector(cash=5.0, currency="USD", unit="metric ton"), _budget())
    assert got.status is CapabilityStatus.UNKNOWN


# -- end-to-end on the real searched route: the exploit shape now blocks, the FIT positive survives -----------

def _isopentyl_route():
    tgt = resolve_target("isopentyl acetate", InputKind.NAME).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in ("water", "acetic acid"))
    hv = (resolve_target("isopentyl alcohol", InputKind.AUTO).canonical(),)
    res = rt.search_routes(tgt, reagents=reag, available=hv, max_depth=3, registry=_CERT)
    for route in res.routes:
        if any(st.envelope.procedure is not None for st in route.steps):
            return route
    raise AssertionError("expected a procedure-backed isopentyl route")


def test_f1_partial_bench_on_the_real_route_no_longer_false_fits():
    """evil-morty's exact exploit: the shipped FIT bench with physical_bounds overridden to pressure-only
    (no temperature ceiling) against the real searched isopentyl route (a real reflux/distillation heat demand)
    must NOT reach overall FIT -- physical goes UNKNOWN, overall UNKNOWN."""
    route = _isopentyl_route()
    reqs = compile_capability_requirements(route)
    bench = isopentyl_capability_fit_bench(physical_bounds=PhysicalBounds.of(max_pressure_atm=2.0))
    a = assess(bench, reqs, evaluate_route(route))
    assert a.physical.status is CapabilityStatus.UNKNOWN
    assert a.overall is not CapabilityStatus.FIT


def test_real_isopentyl_physical_axis_reads_unknown_never_fit_under_the_fully_declared_bench():
    """Round V X-high (D14, supersedes the Round-IV "physical still FITs" pin). The real isopentyl route's heat
    demand is stated only in PROSE ("reflux", "cool to room temperature") plus a DISTILL op with no typed
    temperature, and its whole-step peak was withdrawn (P-X2: the only number the source gives is the distillate HEAD
    range -- a LOWER bound on the heat demand, never a whole-step peak). An unread demand can never be certified, so
    even the fully-declared bench reads physical UNKNOWN -- never FIT -- and the verdict names the D14 law. The
    "F1 did not over-constrain" liveness now lives where it belongs: a fully-declared ceiling over a TYPED demand
    still FITs (``test_f1_fully_declared_ceiling_covering_every_demanded_dimension_still_fits``)."""
    route = _isopentyl_route()
    reqs = compile_capability_requirements(route)
    a = assess(isopentyl_capability_fit_bench(), reqs, evaluate_route(route))
    assert a.physical.status is CapabilityStatus.UNKNOWN
    assert reqs.physical.max_temperature_k is None  # P-X2: no whole-step peak is claimed
    assert any("D13" in r or "D14" in r for r in a.physical.reasons)
    assert a.overall is CapabilityStatus.UNKNOWN
