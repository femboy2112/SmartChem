"""OPERATION XXII section 3 -- the numerical-resolution boundary must be EXPLICIT.

XXI-3 made the conservation tolerance per-component (scale_i = max(|C_i(0)|,|flux_i|), tol_i = atol + rtol*scale_i),
so a trace defect no longer hides under a bulk component's tolerance.  But tol_i still carries an ABSOLUTE floor
(atol = 1e-12 mol): a component whose entire inventory is 1e-15 mol can lose 1e-13 mol (100x its inventory) and still
fall below tol -- an inaccurate answer stamped accurate.  XXII-3 classifies each conserved component into a typed
RESOLUTION verdict and FAILS CLOSED on an unresolvable scale:

  VERIFIED_WITHIN_RESOLUTION                -- residual within tol AND the component is resolvable at its scale.
  VIOLATED                                  -- residual exceeds tol (a proven breach, at any scale).
  NUMERICALLY_UNRESOLVED_AT_REQUESTED_SCALE -- residual within tol but tol >= 0.5*scale, so a >=50%-of-inventory
                                               error would pass: conservation is NOT certifiable at this scale.

(The 4th directive state, source-domain-unsupported, is a hard PRE-integration refusal raised by the fast-equilibrium
admission gate -- XIX-1C temperature / XVII-A1 solver verdict -- never a completed-run per-component verdict.)
"""
from __future__ import annotations

from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
    ExternalBoundary,
    _CONS_UNRESOLVED,
    _CONS_VERIFIED,
    _CONS_VIOLATED,
)
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Species

BULK = Species.of("BULK", {"Q": 1}, charge=0, phase=Phase.AQUEOUS)
TRACE = Species.of("TRACE", {"Z": 1}, charge=0, phase=Phase.AQUEOUS)


def _world(species=(BULK, TRACE), boundaries=()):
    sysA = ChemicalSystem(list(species), [], volume_L=1.0)
    return CoupledWorld([Compartment("c", sysA)], boundaries=tuple(boundaries))


def _run(world, initial, *, loss=None, loss_sp=TRACE, loss_step=3, **kw):
    kw.setdefault("duration", 1.0)
    kw.setdefault("n_steps", 10)
    kw.setdefault("scheme", "strang")
    perturb = None
    if loss is not None:
        slot = world._slot[("c", loss_sp)]

        def perturb(step, y):
            if step == loss_step:
                y = y.copy()
                y[slot] -= loss
            return y
    return world.integrate(initial, _observer_perturb=perturb, **kw)


# ============================================================ the trace-resolution matrix (verified vs unresolved)
def test_one_mole_component_is_verified():
    r = _run(_world(), {"c": {BULK: 1.0, TRACE: 1.0}}).receipt
    assert r.component_resolution["Z"] == _CONS_VERIFIED
    assert r.component_resolution["Q"] == _CONS_VERIFIED
    assert r.material_balance_closed and r.structural_tier == "STRUCTURALLY_CONSERVING"


def test_micromole_component_is_resolved():
    r = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-6}}).receipt
    assert r.component_resolution["Z"] == _CONS_VERIFIED           # 1e-6 >> ~2*atol -> resolvable
    assert r.material_balance_closed


def test_picomole_component_is_unresolved():
    r = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-12}}).receipt   # genuinely conserved, but below resolution
    assert r.component_resolution["Z"] == _CONS_UNRESOLVED
    assert not r.material_balance_closed and r.structural_tier == "REFUSED"


def test_femtomole_component_is_unresolved_even_when_untouched():
    # an ultra-trace component that is perfectly conserved is still NOT CERTIFIABLE at 1e-15 mol -- honesty over a
    # vacuous "closed".  (The bulk component alongside it stays verified.)
    r = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-15}}).receipt
    assert r.component_resolution["Z"] == _CONS_UNRESOLVED
    assert r.component_resolution["Q"] == _CONS_VERIFIED
    assert "Z" in r.numerically_unresolved_components


def test_zero_inventory_component_is_verified_trivially():
    # TRACE never present -> scale 0, residual 0: resolvable trivially (tol bounds absolute creation-from-nothing)
    r = _run(_world(), {"c": {BULK: 1.0}}).receipt
    assert r.component_resolution["Z"] == _CONS_VERIFIED
    assert r.material_balance_closed


# ============================================================ the RED scenario: sub-floor loss, and a real breach
def test_hundredfold_trace_loss_below_the_floor_is_unresolved_not_closed():
    # the XXII-3 counterexample: lose 1e-13 mol from a 1e-15 mol inventory (100x).  residual < atol floor, so it is NOT
    # a proven violation -- but the scale is unresolvable, so it is NOT stamped conserved either.
    tr = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-15}}, loss=1e-13)
    r = tr.receipt
    assert r.component_resolution["Z"] == _CONS_UNRESOLVED
    assert not r.material_balance_closed
    assert any("NUMERICALLY_UNRESOLVED" in c for c in tr.caveats)


def test_large_trace_loss_above_the_floor_is_a_proven_violation():
    # lose 1e-10 mol (> tol ~1e-12) -> a PROVEN breach, classified VIOLATED (distinct from unresolved)
    tr = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-15}}, loss=1e-10)
    r = tr.receipt
    assert r.component_resolution["Z"] == _CONS_VIOLATED
    assert not r.material_balance_closed
    assert any("did NOT close" in c for c in tr.caveats)


def test_resolved_trace_loss_is_violated():
    # a resolvable 1e-6 mol component that loses 1e-7 mol is VIOLATED (resid 1e-7 > tol ~2e-12)
    tr = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-6}}, loss=1e-7)
    assert tr.receipt.component_resolution["Z"] == _CONS_VIOLATED


# ============================================================ large spectator does not mask the trace (XXI-3 + XXII-3)
def test_large_spectator_does_not_hide_an_unresolved_trace():
    # a 1000 mol spectator alongside a 1e-15 mol trace: the trace is judged on ITS OWN scale and flagged unresolved,
    # not swallowed by the spectator's enormous tolerance
    r = _run(_world(), {"c": {BULK: 1000.0, TRACE: 1e-15}}, loss=1e-13).receipt
    assert r.component_resolution["Q"] == _CONS_VERIFIED
    assert r.component_resolution["Z"] == _CONS_UNRESOLVED
    assert r.component_tolerance["Z"] < r.component_tolerance["Q"]   # genuinely per-component tolerances


# ============================================================ open system: feeding raises the resolvable scale
def test_open_feed_raises_the_resolvable_scale():
    # closed: the 1e-15 trace is unresolved
    r_closed = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-15}}).receipt
    assert r_closed.component_resolution["Z"] == _CONS_UNRESOLVED
    # open: feed TRACE at 0.01 mol/s for 1 s -> integrated flux scale ~1e-2, well above the floor -> resolvable
    feed = ExternalBoundary("feedZ", "c", TRACE, mode="feed", rate=0.01)
    r_open = _run(_world(boundaries=(feed,)), {"c": {BULK: 1.0, TRACE: 1e-15}}).receipt
    assert r_open.component_resolution["Z"] == _CONS_VERIFIED
    assert r_open.component_tolerance["Z"] > r_closed.component_tolerance["Z"]


# ============================================================ positivity resolution audit
def test_negative_trace_dip_within_the_floor_is_flagged_resolution_limited():
    tr = _run(_world(), {"c": {BULK: 1.0, TRACE: 1e-15}}, loss=1e-13)
    r = tr.receipt
    assert r.min_inventory < 0.0 and r.positivity_held        # it dipped negative but passed the ABSOLUTE floor ...
    assert r.positivity_resolution_limited                     # ... and that pass is surfaced as resolution-limited
    assert any("positivity is resolution-limited" in c for c in tr.caveats)


def test_healthy_world_is_not_positivity_resolution_limited():
    r = _run(_world(), {"c": {BULK: 1.0, TRACE: 1.0}}).receipt
    assert not r.positivity_resolution_limited


# ============================================================ the four states are distinct typed tokens
def test_resolution_tokens_are_distinct():
    assert len({_CONS_VERIFIED, _CONS_VIOLATED, _CONS_UNRESOLVED}) == 3
    assert _CONS_UNRESOLVED == "NUMERICALLY_UNRESOLVED_AT_REQUESTED_SCALE"
