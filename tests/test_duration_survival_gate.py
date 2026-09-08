"""DURATION-SURVIVAL-01: the duration-aware survival gate wired into core E1 (queue item 3, core-E1 half).

ROUND 19 shipped ``stability_horizon`` as a STANDALONE primitive; ROUND 15 shipped only the serial-hold
DISCLOSURE (a note, never a verdict).  This battery pins the WIRE-IN: E1's ``_judge_transition`` now consumes
the sourced serial hold (DAG-HOLD-01) plus a SOURCED first-order decomposition rate to move the composability
verdict, and the whole-route composite survival is the PRODUCT of the per-transition fractions -- the survival
monoid functor ``S: Process -> ([0, 1], x)``.

The teeth are the same anti-fabrication discipline as the primitive: a rate is used ONLY where sourced for the
exact compound (matched on canonical structure), the gate only ever TIGHTENS a verdict (COMPOSABLE -> UNKNOWN ->
DEGENERATE, plus an affirmative DEGRADES -> DEGENERATE where the instantaneous table was silent), and where no
rate is sourced it is silent and byte-stable.  Crucially (evil-morty fold), the survival is read over the
INTERVENING sibling steps' OWN declared temperatures -- the temperatures the intermediate actually idles at --
never a producer/consumer endpoint's, and it fails closed when a hold temperature is undeclared or the rate is
non-finite.  N2O5 is the seeded calibration compound the fractions come from.
"""
from __future__ import annotations

import pytest

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.kinetics import DEFAULT_KINETICS, KineticRef
from smartchem.data.stability import DEFAULT_STABILITY, StabilityRef
from smartchem.experiment.composability import (
    Transition,
    TransitionStatus,
    _formula_str,
    _judge_transition,
    _survival_product,
)
from smartchem.experiment.dag import dag_composability
from smartchem.experiment.stability_horizon import decomposition_rate_for, surviving_fraction
from smartchem.smiles import parse_smiles
from tests.test_process_service import _convergent_40min_dag

_N2O5 = "O=[N+]([O-])O[N+](=O)[O-]"


def _n2o5():
    return parse_smiles(_N2O5)


def _env(t: float, prov: str = "duration-survival probe") -> ConditionEnvelope:
    return ConditionEnvelope(temperature=Interval(t, t, "K"), status=EvidenceStatus.EXPERIMENTAL, provenance=prov)


def _judge(intermediate, t, *, hold, hold_temp=None, table=DEFAULT_STABILITY, kinetics=DEFAULT_KINETICS):
    """Judge one transition whose endpoints are both at `t` K, with a single serial-hold segment of `hold`
    minutes held at `hold_temp` (default: the same `t`).  Endpoints feed only the instantaneous check; the hold
    segment's temperature feeds the duration gate -- so passing a different `hold_temp` decouples the two."""
    segments = None
    if hold is not None:
        th = t if hold_temp is None else hold_temp
        segments = ((Interval(th, th, "K"), float(hold)),)
    return _judge_transition(0, 1, intermediate, _env(t), _env(t), table, gate_segments=segments, kinetics=kinetics)


# --- the affirmative DEGRADES -> DEGENERATE flip, even where the stability table is SILENT --------------

def test_degrades_over_the_hold_flips_to_degenerate_where_the_onset_table_is_silent():
    # N2O5 has NO stability-table record, so the INSTANTANEOUS verdict is UNKNOWN (no hold).  Over a long hold
    # at 298 K its SOURCED first-order kinetics leave only ~28% -- a duration-aware refutation that turns the
    # silent UNKNOWN into an affirmative DEGENERATE.  This is the core-E1 wire-in the primitive owed.
    base = _judge(_n2o5(), 298.0, hold=None)
    assert base.status is TransitionStatus.UNKNOWN and base.surviving_fraction is None

    held = _judge(_n2o5(), 298.0, hold=600.0)
    assert held.status is TransitionStatus.DEGENERATE
    assert held.surviving_fraction is not None and held.surviving_fraction < 0.5
    assert "majority-destroyed" in held.reason and "duration-aware" in held.reason
    # the disclosed fraction rides in a KNOWN_SOURCED finding carrying the sourced Arrhenius provenance
    frac_findings = [f for f in held.findings if f.label == "duration-survival-fraction"]
    assert len(frac_findings) == 1 and frac_findings[0].provenance


def test_hotter_exposure_destroys_it_faster_still():
    # at the top of the sourced fit window (338 K) a 60-min hold leaves essentially nothing.
    held = _judge(_n2o5(), 338.0, hold=60.0)
    assert held.status is TransitionStatus.DEGENERATE
    assert held.surviving_fraction < 1e-6


# --- ANTI-FABRICATION: a refutation from an OUT-OF-WINDOW extrapolated rate is refused ------------------

def test_out_of_window_degrades_fails_closed_to_unknown_not_a_fabricated_degenerate():
    """A DEGENERATE from an EXTRAPOLATED rate is a fabricated refutation and must not flip the verdict.

    N2O5's sourced Arrhenius fit is valid 298-338 K.  Held at 360 K (above the window), the extrapolated rate
    destroys ~everything -> the pre-guard gate flipped this to DEGENERATE, a refutation resting on an
    unvalidated extrapolation (fabrication -- a wrong refutation is worse than none).  It must fail CLOSED to
    UNKNOWN, disclosing the extrapolated concern, NOT condemn the route.  This assertion goes RED on the
    pre-guard code.  The asymmetry is intentional: an extrapolated SURVIVES (colder, monotonically slower) is
    kept; only an extrapolated refutation is refused."""
    out = _judge(_n2o5(), 360.0, hold=60.0)                  # 360 K is above the 298-338 K fit window
    assert out.status is TransitionStatus.UNKNOWN
    assert out.surviving_fraction is not None and out.surviving_fraction < 0.5  # the forward fraction IS tiny...
    assert "EXTRAPOLAT" in out.reason.upper()                # ...but the verdict refuses to refute on it
    # the guard is SURGICAL: an in-window DEGRADES (330 K, inside 298-338) is still a legitimate DEGENERATE.
    in_win = _judge(_n2o5(), 330.0, hold=60.0)
    assert in_win.status is TransitionStatus.DEGENERATE


# --- MARGINAL holds the verdict at UNKNOWN, never a silent pass -----------------------------------------

def test_marginal_survival_is_unknown_with_the_fraction_disclosed():
    # 298 K / 60 min leaves ~88% -- between the 50% and 99% band edges: a disclosed concern, not affirmatively
    # cleared and not majority-destroyed, so the honest verdict is UNKNOWN (never COMPOSABLE).
    held = _judge(_n2o5(), 298.0, hold=60.0)
    assert held.status is TransitionStatus.UNKNOWN
    assert 0.5 < held.surviving_fraction < 0.99
    assert "MARGINAL" in held.reason


# --- THE evil-morty fold: survival follows the HOLD (intervening) temperature, not the endpoints --------

def test_survival_uses_the_hold_temperature_not_the_endpoints_both_directions():
    # cool endpoints (250 K) but a HOT idle hold (338 K, 60 min): the intermediate is destroyed during the hold.
    # The old endpoint-peak gate would have read 250 K and MISSED it -> a laundered near-survival.  Now caught.
    hot_hold = _judge(_n2o5(), 250.0, hold=60.0, hold_temp=338.0)
    assert hot_hold.status is TransitionStatus.DEGENERATE
    assert hot_hold.surviving_fraction < 0.5

    # hot endpoints (338 K) but a COOL idle hold (250 K, 60 min): the intermediate survives the hold.  The old
    # endpoint-peak gate would have read 338 K and minted a FALSE DEGENERATE.  Now it does not condemn.
    cool_hold = _judge(_n2o5(), 338.0, hold=60.0, hold_temp=250.0)
    assert cool_hold.status is not TransitionStatus.DEGENERATE
    assert cool_hold.surviving_fraction > 0.99


def test_an_undeclared_hold_segment_temperature_fails_closed():
    # a hold with a real duration but no declared temperature (the DAG could not model where the intermediate
    # idles): the gate never borrows an endpoint's temperature -- it stays silent (returns the base verdict).
    tr = _judge_transition(0, 1, _n2o5(), _env(298), _env(298), DEFAULT_STABILITY,
                           gate_segments=((None, 600.0),), kinetics=DEFAULT_KINETICS)
    assert tr.surviving_fraction is None
    assert tr.status is TransitionStatus.UNKNOWN  # the instantaneous base (no stability record), untouched


def test_the_composite_hold_survival_is_the_product_over_segments():
    # the survival monoid applied ALONG the hold: two intervening segments -> the fraction is the product of the
    # per-segment first-order survivals, each at its OWN temperature.
    rec = decomposition_rate_for(_n2o5())
    segments = ((Interval(298, 298, "K"), 30.0), (Interval(320, 320, "K"), 30.0))
    tr = _judge_transition(0, 1, _n2o5(), _env(298), _env(298), DEFAULT_STABILITY, gate_segments=segments)
    expected = surviving_fraction(rec, 298.0, 30.0 * 60.0) * surviving_fraction(rec, 320.0, 30.0 * 60.0)
    assert tr.surviving_fraction == pytest.approx(expected)


# --- SURVIVES confirms an instantaneous COMPOSABLE and never UPGRADES a weaker verdict ------------------

def _table_with_isolable_n2o5():
    # inject a SYNTHETIC stability record so the instantaneous verdict is COMPOSABLE (isolable, no onset),
    # letting us exercise the "tighten from COMPOSABLE" matrix.  Keyed by the same formula string resolve_stability uses.
    return DEFAULT_STABILITY.with_records(StabilityRef(
        _formula_str(_n2o5()), "dinitrogen pentoxide (SYNTHETIC TEST record)", None, None, None, True,
        "SYNTHETIC TEST record: isolable, no bench-range onset -- exercises the duration gate, not a real claim",
    ))


def test_survives_leaves_a_composable_base_composable():
    table = _table_with_isolable_n2o5()
    assert _judge(_n2o5(), 298.0, hold=None, table=table).status is TransitionStatus.COMPOSABLE  # base
    held = _judge(_n2o5(), 298.0, hold=1.0, table=table)  # 1 min at 298 K -> ~99.8% remains
    assert held.status is TransitionStatus.COMPOSABLE
    assert held.surviving_fraction is not None and held.surviving_fraction >= 0.99


def test_the_gate_tightens_a_composable_base_across_the_full_band():
    table = _table_with_isolable_n2o5()
    assert _judge(_n2o5(), 298.0, hold=1.0, table=table).status is TransitionStatus.COMPOSABLE   # SURVIVES
    assert _judge(_n2o5(), 298.0, hold=60.0, table=table).status is TransitionStatus.UNKNOWN     # MARGINAL
    assert _judge(_n2o5(), 298.0, hold=600.0, table=table).status is TransitionStatus.DEGENERATE  # DEGRADES


# --- fail-closed and byte-stable: no rate / no hold / non-finite rate -> the instantaneous verdict, untouched

def test_no_sourced_rate_leaves_the_verdict_and_adds_no_fraction():
    # acetic acid has NO sourced first-order decomposition rate: even with a long hold the gate is silent.
    acoh = parse_smiles("CC(=O)O")
    held = _judge(acoh, 300.0, hold=600.0)
    assert held.surviving_fraction is None
    assert not any(f.label == "duration-survival-fraction" for f in held.findings)


def test_no_positive_hold_is_silent():
    assert _judge(_n2o5(), 298.0, hold=None).surviving_fraction is None   # no modeled hold
    assert _judge(_n2o5(), 298.0, hold=0.0).surviving_fraction is None    # zero-minute hold


def test_a_non_finite_injected_rate_fails_closed_in_the_gate_without_crashing():
    # the data layer accepts a non-finite (Ea, A) (KineticRef has no isfinite guard).  A matched-but-malformed
    # rate must NOT raise inside the gate and abort the compile: the gate checks finiteness and stays silent.
    bad = DEFAULT_KINETICS.with_records(KineticRef(
        reactant_smiles=(("O=[N+]([O-])O[N+](=O)[O-]", 2),),
        product_smiles=(("[N+](=O)[O-]", 4), ("O=O", 1)),
        name="N2O5 (non-finite TEST record)", ea_kj_per_mol=float("inf"), log10_a=13.69, a_units="s^-1",
        temperature_range_k=(298.0, 338.0), phase="gas", provenance="fabricated non-finite Ea; fail-closed control",
    ))
    tr = _judge(_n2o5(), 320.0, hold=60.0, kinetics=bad)  # replaces the seed N2O5 record (same reactant/product/phase)
    assert tr.surviving_fraction is None                  # fail-closed, no crash
    assert tr.status is TransitionStatus.UNKNOWN


def test_the_gate_never_loosens_an_already_degenerate_base():
    # a non-isolable intermediate is DEGENERATE on the instantaneous fact; the gate returns it untouched (moot),
    # so a duration reading can never rescue a route the sourced isolability fact already refuted.
    ketene = parse_smiles("C=C=O")  # generated/consumed in situ -> isolable=False in the seed
    tr = _judge_transition(0, 1, ketene, _env(500), _env(500), DEFAULT_STABILITY,
                           gate_segments=((Interval(500, 500, "K"), 600.0),), kinetics=DEFAULT_KINETICS)
    assert tr.status is TransitionStatus.DEGENERATE
    assert tr.surviving_fraction is None  # the gate did not even assess it
    assert "not isolable" in tr.reason


# --- the survival monoid functor: composite survival is the PRODUCT of the assessed fractions -----------

def test_survival_product_is_the_monoid_homomorphism():
    m = parse_smiles("O")
    t1 = Transition(0, 1, m, TransitionStatus.COMPOSABLE, "r", None, (), surviving_fraction=0.8)
    t2 = Transition(1, 2, m, TransitionStatus.COMPOSABLE, "r", None, (), surviving_fraction=0.5)
    t_unassessed = Transition(2, 3, m, TransitionStatus.COMPOSABLE, "r", None, ())
    # S(g . f) = S(g) * S(f): survival composes multiplicatively along sequential composition
    assert _survival_product((t1, t2)) == pytest.approx(0.8 * 0.5)
    # an unassessed transition is skipped, not treated as 0 or 1 silently -- but the product is over the assessed
    assert _survival_product((t1, t_unassessed)) == pytest.approx(0.8)
    # NO assessed transition -> None (never misread as "100% survives" over an unassessed route)
    assert _survival_product((t_unassessed,)) is None
    assert _survival_product(()) is None


def test_surviving_fraction_is_digest_excluded_disclosure():
    # THE byte-stability lever: surviving_fraction is compare=False, so a route with no sourced rate keeps its
    # exact prior identity -- two transitions differing ONLY in the fraction are equal and share one digest.
    m = parse_smiles("O")
    bare = Transition(0, 1, m, TransitionStatus.COMPOSABLE, "r", None, ())
    with_frac = Transition(0, 1, m, TransitionStatus.COMPOSABLE, "r", None, (), surviving_fraction=0.42)
    assert bare == with_frac
    assert bare.digest == with_frac.digest


def test_surviving_fraction_out_of_range_is_refused():
    m = parse_smiles("O")
    for bad in (-0.1, 1.5):
        with pytest.raises(ValueError):
            Transition(0, 1, m, TransitionStatus.COMPOSABLE, "r", None, (), surviving_fraction=bad)


# --- end-to-end through dag_composability: the wire-in threads, and is OFF by default (byte-stable) -----

def _synthetic_acoh_decomposition_kinetics():
    # a transparently SYNTHETIC fast first-order decomposition for acetic acid (the held intermediate of the
    # convergent DAG) -- a TEST lever for the wiring, exactly like the injected StabilityRef in test_composability.
    return DEFAULT_KINETICS.with_records(KineticRef(
        reactant_smiles=(("CC(=O)O", 1),),
        product_smiles=(("C", 1), ("O=C=O", 1)),
        name="acetic acid decomposition (SYNTHETIC TEST rate)",
        ea_kj_per_mol=0.0,
        log10_a=6.0,  # k = 1e6 /s -> destroyed over any real hold; NOT a measurement
        a_units="s^-1",
        temperature_range_k=(1.0, 1000.0),
        provenance="SYNTHETIC TEST rate; not a real measurement -- exercises the DAG duration wire-in only",
    ))


def test_dag_composability_does_not_flip_a_convergent_join_on_a_schedule_avoidable_hold():
    """Move 6 (this was previously ``..._flips_a_held_edge_to_degenerate_only_with_the_injected_rate``).

    A convergent join's two branches are causally INDEPENDENT, so neither intermediate idles in EVERY schedule
    (make the fast-decomposing branch last and it goes straight into the join).  Forced-between is therefore EMPTY
    and the duration GATE stays silent: the DAG is ``UNKNOWN`` even WITH the injected acetic-acid rate.  The
    pre-Move-6 ``DEGENERATE`` here was an artifact of one arbitrary topological order -- the verdict flipped
    ``DEGENERATE``<->``UNKNOWN`` purely on which branch a caller listed first.  See
    ``tests/test_dag_linearization_invariance.py`` for the invariance law and for
    ``test_forced_between_hold_still_flips_degenerate_order_invariantly`` (a genuine UNAVOIDABLE hold that does flip)."""
    dag = _convergent_40min_dag()
    # OFF by default: the seed kinetics have no acetic-acid rate, so NO edge is duration-assessed.
    assert dag_composability(dag).verdict == "UNKNOWN"
    assert dag_composability(dag).route_surviving_fraction is None

    # WITH the injected rate: STILL not degenerate -- no intermediate is UNAVOIDABLY held, so the gate cannot fire
    # (a viable schedule saves the acetic-acid branch), and the verdict does not depend on the listing order.
    comp = dag_composability(dag, kinetics=_synthetic_acoh_decomposition_kinetics())
    assert comp.verdict != "DEGENERATE"
    assert not [t for t in comp.transitions if t.status is TransitionStatus.DEGENERATE]


def test_the_adjacent_zero_hold_edge_is_never_gated():
    # the ethanol edge is an adjacent handoff (no intervening sibling steps -> no hold segments), so even with a
    # matching rate it is not duration-assessed.
    dag = _convergent_40min_dag()
    etoh_rate = DEFAULT_KINETICS.with_records(KineticRef(
        reactant_smiles=(("CCO", 1),), product_smiles=(("C=C", 1), ("O", 1)),
        name="ethanol (SYNTHETIC TEST rate)", ea_kj_per_mol=0.0, log10_a=6.0, a_units="s^-1",
        temperature_range_k=(1.0, 1000.0), provenance="SYNTHETIC TEST rate; adjacent-handoff control",
    ))
    comp = dag_composability(dag, kinetics=etoh_rate)
    assessed = [t for t in comp.transitions if t.surviving_fraction is not None]
    assert assessed == []  # zero-hold edge is never duration-assessed, so no fraction is attached
