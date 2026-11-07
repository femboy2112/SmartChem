"""OPERATION XXIV Phase V -- the spatial-crystal prototype: limits, conservation identity, reference discretization,
positivity gate and projection contract."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from experiments.sandbox_foundation import spatial_grid_xxiv as sg
from experiments.sandbox_foundation.general_kernel import Phase, Species

T = Species.of("tracer", {"Q": 1}, 0, Phase.AQUEOUS)
U = Species.of("solute", {"Z": 1}, 0, Phase.AQUEOUS)


def _grid5(**kw):
    base = dict(nx=5, ny=5, species=(T, U), k_face_Lps=0.05,
                walls=frozenset({((2, 0), (2, 1)), ((2, 1), (2, 2)), ((2, 3), (2, 4)), ((1, 2), (2, 2)),
                                 ((2, 2), (3, 2))}),
                valves=(("gate", (2, 2), (2, 3)),),
                source=((0, 0), "tracer", 2e-4), sink=((4, 4), "tracer", 0.02))
    base.update(kw)
    return sg.GridSpec(**base)


INIT5 = {(0, 0): {"tracer": 0.01, "solute": 0.002}, (4, 0): {"solute": 0.004}, (2, 2): {"tracer": 0.003}}
SEGS = (sg.Segment("closed", 20.0, 40), sg.Segment("open", 40.0, 80, frozenset({"gate"})))


@pytest.fixture(scope="module")
def run5():
    return sg.run_grid(_grid5(), INIT5, SEGS)


def test_interior_operator_conserves_each_face_exactly_and_columns_to_roundoff():
    spec = _grid5(source=None, sink=None)
    one = sg.GridSpec(2, 1, (T,))
    L1, _, _ = sg.reference_operator(one, frozenset(), "tracer")
    assert np.all(L1.sum(axis=0) == 0.0)                                         # ONE face: the pair cancels bit-exactly
    for valves in (frozenset(), frozenset({"gate"})):
        L, q, _ = sg.reference_operator(spec, valves, "tracer")
        assert not q.any()
        assert np.max(np.abs(L.sum(axis=0))) <= 8 * np.finfo(float).eps * np.max(np.abs(L))   # summation roundoff only


def test_matches_the_independent_reference_discretization(run5):
    ref = sg.reference_solution(_grid5(), INIT5, SEGS)
    for s in ("tracer", "solute"):
        scale = max(ref[s].values())
        err = max(abs(run5.final[c][s] - ref[s][c]) for c in _grid5().cells())
        assert err / scale < 1e-6, (s, err)


def test_global_conservation_identity_closes_against_the_boundary_ledger(run5):
    for rc, led in zip(run5.receipts, run5.ledger):
        assert rc.material_balance_closed and rc.positivity_held
        for lab, (change, ext) in led.items():
            assert abs(change - ext) <= 1e-12 + 1e-6 * max(abs(change), abs(ext), 1e-30), lab
    assert run5.ledger[0]["Z"][1] == 0.0                                          # solute: no boundary term at all
    first, last = run5.frames[0].total_mol["solute"], run5.frames[-1].total_mol["solute"]
    assert last == pytest.approx(first, rel=1e-12)


def test_zero_flux_limit_all_walls():
    spec = sg.GridSpec(3, 3, (T,), walls=frozenset(sg.GridSpec(3, 3, (T,)).all_faces()))
    init = {c: {"tracer": 0.001 * (k + 1)} for k, c in enumerate(spec.cells())}
    r = sg.run_grid(spec, init, (sg.Segment("s", 50.0, 10),))
    assert all(r.final[c]["tracer"] == init[c]["tracer"] for c in spec.cells())


def test_uniform_state_limit_is_a_fixed_point():
    spec = sg.GridSpec(3, 3, (T,))
    init = {c: {"tracer": 0.004} for c in spec.cells()}
    r = sg.run_grid(spec, init, (sg.Segment("s", 50.0, 10),))
    assert all(r.final[c]["tracer"] == 0.004 for c in spec.cells())


def test_single_interface_matches_the_analytic_relaxation():
    spec = sg.GridSpec(2, 1, (T,), k_face_Lps=0.03, cell_volume_L=1.0)
    r = sg.run_grid(spec, {(0, 0): {"tracer": 0.01}}, (sg.Segment("s", 30.0, 60),))
    mean = 0.005
    expect = mean + (0.01 - mean) * math.exp(-2 * 0.03 * 30.0)
    assert r.final[(0, 0)]["tracer"] == pytest.approx(expect, rel=1e-8)
    assert r.final[(1, 0)]["tracer"] == pytest.approx(0.01 - expect, rel=1e-8)


def test_face_flux_is_exactly_antisymmetric_and_reverses_with_the_gradient(run5):
    spec = _grid5()
    amounts = {c: dict(v) for c, v in run5.frames[5].amounts.items()}
    for a, b in spec.open_faces(frozenset({"gate"})):
        f_ab = sg.face_flux(spec, amounts, "tracer", a, b)
        assert f_ab == -sg.face_flux(spec, amounts, "tracer", b, a)
    swapped = {c: {"tracer": amounts[(1, 0)]["tracer"] if c == (0, 0) else amounts[(0, 0)]["tracer"]
                   if c == (1, 0) else amounts[c]["tracer"]} for c in amounts}
    assert sg.face_flux(spec, swapped, "tracer", (0, 0), (1, 0)) == -sg.face_flux(spec, amounts, "tracer", (0, 0), (1, 0))


def test_mirror_symmetry_physics_does_not_depend_on_face_orientation():
    spec = sg.GridSpec(3, 3, (T,))
    a = sg.run_grid(spec, {(0, 1): {"tracer": 0.01}}, (sg.Segment("s", 20.0, 20),))
    b = sg.run_grid(spec, {(2, 1): {"tracer": 0.01}}, (sg.Segment("s", 20.0, 20),))
    for (i, j) in spec.cells():
        assert a.final[(i, j)]["tracer"] == pytest.approx(b.final[(2 - i, j)]["tracer"], rel=1e-9, abs=1e-18)


def test_boundary_closure_source_only_grows_by_exactly_the_feed():
    spec = sg.GridSpec(3, 3, (T,), source=((1, 1), "tracer", 1e-4))
    r = sg.run_grid(spec, {}, (sg.Segment("s", 10.0, 10),))
    assert r.frames[-1].total_mol["tracer"] == pytest.approx(1e-3, rel=1e-10)


def test_closed_valve_isolates_and_opening_it_continues_the_state(run5):
    closed = [f for f in run5.frames if f.segment == "closed"]
    opened = [f for f in run5.frames if f.segment == "open"]
    assert all(f.amounts[(2, 2)]["tracer"] == 0.003 for f in closed)             # walled pocket + closed gate: sealed
    assert dict(closed[-1].amounts[(2, 3)]) == dict(opened[0].amounts[(2, 3)])   # continuation, no jump
    assert opened[-1].amounts[(2, 2)]["tracer"] < 0.003                           # gate open: the pocket drains


def test_positivity_gate_refuses_an_over_drain_and_preserves_the_raw_value():
    spec = sg.GridSpec(2, 1, (T,), source=((0, 0), "tracer", -1e-3))
    with pytest.raises(sg.GridError, match="VIOLATED") as exc:
        sg.run_grid(spec, {(0, 0): {"tracer": 1e-3}}, (sg.Segment("s", 5.0, 10),))
    assert "c0_0/tracer" in str(exc.value)


@pytest.mark.parametrize("kw, match", [
    (dict(species=(Species.of("Na+", {"Na": 1}, 1, Phase.AQUEOUS),)), "NEUTRAL"),
    (dict(nx=10), "1..9"),
    (dict(walls=frozenset({((0, 0), (2, 0))})), "axis-adjacent"),
    (dict(valves=(("v", (2, 0), (2, 1)),)), "non-wall"),
])
def test_declaration_refusals(kw, match):
    with pytest.raises(sg.GridError, match=match):
        _grid5(**kw)


def test_projection_is_deterministic_typed_and_cannot_write_back(run5):
    from experiments.sandbox_foundation.libgibson_frame_example import to_frame, validate_frame
    snap, ifaces = sg.to_snapshot(run5, run5.frames[-1])
    frame = to_frame(snap, ifaces)
    assert validate_frame(frame) == []
    assert frame["quantity_kinds"]["amount_mol"] == "CANONICAL" and frame["display_hints"]["layout"] == "grid2d"
    again = sg.run_grid(_grid5(), INIT5, SEGS)
    assert to_frame(*sg.to_snapshot(again, again.frames[-1]))["model_digest"] == frame["model_digest"]
    before = dict(run5.final[(0, 0)])
    frame["fields"]["tracer"]["amount_mol"][0] = 99.0                             # a renderer scribbles on its copy
    assert dict(run5.final[(0, 0)]) == before
    with pytest.raises(TypeError):
        run5.final[(0, 0)]["tracer"] = 1.0                                        # the run itself is read-only


def test_html_view_is_a_labeled_projection(run5):
    doc = sg.render_html(run5, "tracer")
    assert "not a measurement" in doc and doc == sg.render_html(run5, "tracer")
    payload = json.loads(doc.split("const D=")[1].split(";const g=")[0])
    assert len(payload["data"]) == len(run5.frames) and payload["verdicts"][0]["balance_closed"] is True
