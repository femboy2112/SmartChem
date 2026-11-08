"""OPERATION XXV Phase IV -- the reactive grid: fixed points, analytic limits, conservation, an independent expm
reference, a CALIBRATED splitting-order study, an FV spatial-convergence study, positivity, replay and the frame
contract."""
from __future__ import annotations

import ast
import dataclasses
import json
import math
import random
import re
from types import MappingProxyType
from pathlib import Path

import numpy as np
import pytest

from experiments.sandbox_foundation import reactive_grid_xxv as rg
from experiments.sandbox_foundation import claim_tiers as ct
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER, InvalidClaimTierError
from experiments.sandbox_foundation.general_coupled import CoupledWorld, ExternalBoundary
from experiments.sandbox_foundation.general_kernel import ConservationError, Phase, SourceDomainError, Species

A = Species.of("A", {"X": 1})
B = Species.of("B", {"X": 1})
SC = rg.SyntheticConductance
WALLS = frozenset({((1, 0), (2, 0)), ((1, 3), (2, 3)), ((0, 2), (1, 2))})
LOCAL = frozenset({(1, 1), (2, 1), (1, 2)})


def main_spec(**kw):
    base = dict(nx=4, ny=4, species=(A, B), conductance=(("A", SC(0.4)), ("B", SC(0.05))), walls=WALLS,
                valves=(("gate", (1, 1), (2, 1)),), sources=(((0, 0), "A", 2e-3),), sinks=(((3, 3), "B", 0.02),),
                reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, LOCAL),))
    base.update(kw)
    return rg.ReactiveGridSpec(**base)


INIT = {(0, 0): {"A": 0.05}, (3, 0): {"B": 0.02}, (1, 2): {"A": 0.01}}
SEGS = (rg.ValveSegment("closed", 4.0), rg.ValveSegment("open", 4.0, {"gate"}))


def _rel_err(spec, run, ref):
    scale = max(max(v.values()) for v in ref.values())
    return max(abs(run.final[c][s] - ref[s][c]) for c in spec.cells() for s in ref) / scale


@pytest.fixture(scope="module")
def mono():
    return rg.run_reactive_grid(main_spec(), INIT, SEGS, scheme="monolithic", dt=4.0)


@pytest.fixture(scope="module")
def ladder():
    """Lie and Strang errors vs the independent expm reference at dt = 1, 1/2, 1/4, 1/8 on the non-commuting grid."""
    spec = main_spec()
    ref = rg.reference_solution_coupled(spec, INIT, SEGS)
    dts = (1.0, 0.5, 0.25, 0.125)
    return {sch: [_rel_err(spec, rg.run_reactive_grid(spec, INIT, SEGS, scheme=sch, dt=dt), ref) for dt in dts]
            for sch in ("lie", "strang")} | {"dts": dts}


# ---------------------------------------------------------------- fixed points
def test_zero_flow_fixed_point_all_walls():
    probe = rg.ReactiveGridSpec(3, 3, (A,), (("A", SC(0.2)),))
    spec = rg.ReactiveGridSpec(3, 3, (A,), (("A", SC(0.2)),), walls=frozenset(probe.all_faces()))
    init = {c: {"A": 0.001 * (k + 1)} for k, c in enumerate(spec.cells())}
    r = rg.run_reactive_grid(spec, init, (rg.ValveSegment("s", 50.0),), dt=10.0)
    assert all(r.final[c]["A"] == init[c]["A"] for c in spec.cells())


def test_uniform_state_fixed_point_without_reaction():
    spec = rg.ReactiveGridSpec(3, 3, (A, B), (("A", SC(0.4)), ("B", SC(0.05))))
    init = {c: {"A": 0.004, "B": 0.001} for c in spec.cells()}
    r = rg.run_reactive_grid(spec, init, (rg.ValveSegment("s", 50.0),), dt=10.0)
    assert all(r.final[c]["A"] == 0.004 and r.final[c]["B"] == 0.001 for c in spec.cells())


def test_uniform_state_at_the_kf_over_kr_ratio_is_a_fixed_point_and_off_ratio_is_not():
    rx = (("iso", (("A", -1), ("B", 1)), 0.5, 0.25, None),)              # dyadic: kf cA == kr cB exactly in floats
    spec = rg.ReactiveGridSpec(3, 3, (A, B), (("A", SC(0.4)), ("B", SC(0.05))), reactions=rx)
    eq = {c: {"A": 0.125, "B": 0.25} for c in spec.cells()}               # B/A = kf/kr = 2
    r = rg.run_reactive_grid(spec, eq, (rg.ValveSegment("s", 20.0),), scheme="strang", dt=5.0)
    assert all(r.final[c]["A"] == 0.125 and r.final[c]["B"] == 0.25 for c in spec.cells())
    off = {c: {"A": 0.25, "B": 0.125} for c in spec.cells()}             # control: the reaction is live off the ratio
    r2 = rg.run_reactive_grid(spec, off, (rg.ValveSegment("s", 20.0),), scheme="strang", dt=5.0)
    assert r2.final[(0, 0)]["B"] / r2.final[(0, 0)]["A"] == pytest.approx(2.0, rel=1e-6)


# ---------------------------------------------------------------- analytic limits and symmetry
def test_one_face_analytic_transfer_per_species_conductance():
    spec = rg.ReactiveGridSpec(2, 1, (A, B), (("A", SC(0.03)), ("B", SC(0.007))))
    r = rg.run_reactive_grid(spec, {(0, 0): {"A": 0.01, "B": 0.01}}, (rg.ValveSegment("s", 30.0),), dt=1.0)
    for sp, k in (("A", 0.03), ("B", 0.007)):
        expect = 0.005 + 0.005 * math.exp(-2 * k * 30.0)
        assert r.final[(0, 0)][sp] == pytest.approx(expect, rel=1e-8)
        assert r.final[(1, 0)][sp] == pytest.approx(0.01 - expect, rel=1e-8)


def test_face_flux_is_exactly_antisymmetric_and_reverses_with_the_gradient(mono):
    spec = main_spec()
    amounts = {c: dict(v) for c, v in mono.frames[1].amounts.items()}
    for a, b in spec.open_faces({"gate"}):
        for s in ("A", "B"):
            assert rg.face_flux(spec, amounts, s, a, b) == -rg.face_flux(spec, amounts, s, b, a)
    sw = {c: dict(v) for c, v in amounts.items()}
    sw[(0, 0)]["A"], sw[(1, 0)]["A"] = amounts[(1, 0)]["A"], amounts[(0, 0)]["A"]
    assert rg.face_flux(spec, sw, "A", (0, 0), (1, 0)) == -rg.face_flux(spec, amounts, "A", (0, 0), (1, 0))


def test_mirror_symmetry_with_a_localized_reaction():
    def run(col):
        spec = rg.ReactiveGridSpec(3, 3, (A, B), (("A", SC(0.4)), ("B", SC(0.05))),
                                   reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, frozenset({(col, 1)})),))
        return rg.run_reactive_grid(spec, {(col, 1): {"A": 0.01}}, (rg.ValveSegment("s", 10.0),),
                                    scheme="monolithic", dt=10.0)
    a, b = run(0), run(2)
    for (i, j) in a.spec.cells():
        for s in ("A", "B"):
            assert a.final[(i, j)][s] == pytest.approx(b.final[(2 - i, j)][s], rel=1e-9, abs=1e-18)


def test_wall_is_impermeable_while_an_open_face_is_not():
    walled = rg.ReactiveGridSpec(2, 1, (A,), (("A", SC(0.5)),), walls=frozenset({((0, 0), (1, 0))}))
    r = rg.run_reactive_grid(walled, {(0, 0): {"A": 0.01}}, (rg.ValveSegment("s", 20.0),), dt=5.0)
    assert r.final[(1, 0)]["A"] == 0.0 and r.final[(0, 0)]["A"] == 0.01
    opened = rg.ReactiveGridSpec(2, 1, (A,), (("A", SC(0.5)),))
    r2 = rg.run_reactive_grid(opened, {(0, 0): {"A": 0.01}}, (rg.ValveSegment("s", 20.0),), dt=5.0)
    assert r2.final[(1, 0)]["A"] > 1e-3


def test_valve_contrast_sealed_reacting_pocket_holds_its_total_until_opened():
    pocket = (2, 2)
    spec = rg.ReactiveGridSpec(3, 3, (A, B), (("A", SC(0.4)), ("B", SC(0.05))),
                               walls=frozenset({((1, 2), (2, 2))}), valves=(("gate", (2, 1), (2, 2)),),
                               reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, frozenset({pocket})),))
    segs = (rg.ValveSegment("closed", 10.0), rg.ValveSegment("open", 20.0, {"gate"}))
    r = rg.run_reactive_grid(spec, {pocket: {"A": 0.003}, (0, 0): {"A": 0.01}}, segs, dt=1.0)
    closed = [f for f in r.frames if f.segment == "closed"]
    opened = [f for f in r.frames if f.segment == "open"]
    for f in closed:
        assert f.amounts[pocket]["A"] + f.amounts[pocket]["B"] == pytest.approx(0.003, rel=1e-13)
    assert closed[-1].amounts[pocket]["B"] > 1e-4                        # the reaction ran inside the sealed pocket
    assert all(f.amounts[(2, 1)]["B"] == 0.0 for f in closed)            # nothing crossed the closed valve
    assert opened[-1].amounts[pocket]["A"] + opened[-1].amounts[pocket]["B"] < 0.0029   # drains once open


# ---------------------------------------------------------------- conservation
def test_internal_reaction_conserves_the_element_total_and_unbalanced_reaction_is_refused():
    spec = main_spec(sources=(), sinks=())
    r = rg.run_reactive_grid(spec, INIT, SEGS, scheme="strang", dt=0.5)
    x0 = r.frames[0].total_mol["A"] + r.frames[0].total_mol["B"]
    for f in r.frames:
        assert f.total_mol["A"] + f.total_mol["B"] == pytest.approx(x0, rel=1e-12)
    assert abs(r.frames[-1].total_mol["B"] - r.frames[0].total_mol["B"]) > 1e-3      # species totals DID change
    for led in r.ledgers:
        assert set(led.component_resolution.values()) == {"VERIFIED_WITHIN_RESOLUTION"}
        assert led.execution_identity_basis == "AUDITED_BUILTIN"
    with pytest.raises(ConservationError):
        main_spec(reactions=(("bad", (("A", -1), ("B", 2)), 0.3, 0.1, None),))


def test_boundary_ledger_closes_per_step(mono):
    for led in mono.ledgers:
        for lab, (change, ext) in led.material.items():
            assert abs(change - ext) <= 1e-12 + 1e-6 * max(abs(change), abs(ext))
        for lab, res in led.component_max_residual.items():
            assert res <= led.component_tolerance[lab]


# ---------------------------------------------------------------- independent reference
def test_engine_matches_the_independent_expm_reference(mono):
    spec = main_spec()
    assert spec.nx >= 4 and spec.ny >= 4 and spec.walls and spec.valves
    assert spec.conductance_of("A").k_Lps != spec.conductance_of("B").k_Lps
    assert spec.reactions[0].cells is not None and len(spec.reactions[0].cells) < len(spec.cells())
    ref = rg.reference_solution_coupled(spec, INIT, SEGS)
    err = _rel_err(spec, mono, ref)
    print(f"\nmonolithic vs expm reference: rel err {err:.3e}")
    assert err < 1e-6


def test_reference_refuses_a_nonlinear_network():
    spec = main_spec(species=(A, Species.of("A2", {"X": 2}), B),
                     conductance=(("A", SC(0.4)), ("A2", SC(0.1)), ("B", SC(0.05))),
                     reactions=(("dim", (("A", -2), ("A2", 1)), 0.3, 0.1, None),), sinks=())
    with pytest.raises(rg.GridError, match="first order"):
        rg.reference_generator(spec)


# ---------------------------------------------------------------- splitting (calibrated)
def test_splitting_orders_on_a_noncommuting_grid(ladder):
    spec = main_spec()
    for valves in (frozenset(), frozenset({"gate"})):
        assert rg.splitting_commutator_norm(spec, valves) > 0.1               # the comparison is NOT vacuous
    lie, strang = ladder["lie"], ladder["strang"]
    lie_r = [lie[k] / lie[k + 1] for k in range(3)]
    st_r = [strang[k] / strang[k + 1] for k in range(3)]
    print(f"\nLie errors {lie}  ratios {lie_r}\nStrang errors {strang}  ratios {st_r}")
    assert all(1.8 <= x <= 2.4 for x in lie_r)
    assert all(3.5 <= x <= 4.3 for x in st_r)
    assert all(e_lie > 4 * e_st for e_lie, e_st in zip(lie, strang))


def test_time_step_refinement_fitted_orders_and_monolithic_step_independence(ladder, mono):
    ld = np.log(np.array(ladder["dts"]))
    p_lie = float(np.polyfit(ld, np.log(ladder["lie"]), 1)[0])
    p_st = float(np.polyfit(ld, np.log(ladder["strang"]), 1)[0])
    print(f"\nfitted orders: Lie {p_lie:.4f}  Strang {p_st:.4f}")
    assert 0.9 <= p_lie <= 1.2 and 1.85 <= p_st <= 2.1
    fine = rg.run_reactive_grid(main_spec(), INIT, SEGS, scheme="monolithic", dt=0.5)
    scale = max(max(v.values()) for v in fine.final.values())
    assert max(abs(fine.final[c][s] - mono.final[c][s]) for c in fine.spec.cells() for s in ("A", "B")) < 1e-8 * scale


def test_control_uniform_conductance_and_uniform_reaction_commute_so_splitting_is_exact():
    spec = main_spec(conductance=(("A", SC(0.1)), ("B", SC(0.1))), sources=(), sinks=(),
                     reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, None),))
    for valves in (frozenset(), frozenset({"gate"})):
        assert rg.splitting_commutator_norm(spec, valves) == 0.0
    ref = rg.reference_solution_coupled(spec, INIT, SEGS)
    err = _rel_err(spec, rg.run_reactive_grid(spec, INIT, SEGS, scheme="lie", dt=1.0), ref)
    print(f"\ncommuting control: Lie dt=1 rel err {err:.3e}")
    assert err < 1e-7                                        # vs ~4.5e-2 on the non-commuting grid at the same dt


# ---------------------------------------------------------------- spatial convergence
def test_spatial_convergence_of_the_fv_diffusion_decay_rate():
    """Property of the finite-volume discretisation of u_t = D u_xx (no-flux ends) with the STATED D -- not an
    empirical validation.  A cosine mode on N cells decays at the discrete eigenvalue (4D/dx^2) sin^2(pi/2N), whose
    relative distance to the continuum D (pi/L)^2 is (pi/N)^2/12 + O(N^-4): it must fall ~4x per doubling."""
    D, Lm, area = 1e-9, 1e-3, 1e-6
    U = Species.of("u", {"X": 1})
    lam_c = D * (math.pi / Lm) ** 2
    errs = []
    for N in (8, 16, 32, 64):
        dx = Lm / N
        cond = rg.DerivedConductance(D, area, dx, ASSUMED_PARAMETER, "ASSUMED illustrative value (no source)", 298.15)
        spec = rg.ReactiveGridSpec(N, 1, (U,), (("u", cond),), cell_volume_L=area * dx * 1000.0)
        V = spec.cell_volume_L
        mode = np.cos(math.pi * (np.arange(N) + 0.5) / N)
        t_end = 1.0 / lam_c
        run = rg.run_reactive_grid(spec, {(i, 0): {"u": V * (1.0 + 0.5 * mode[i])} for i in range(N)},
                                   (rg.ValveSegment("s", t_end),), scheme="monolithic", dt=t_end / 4, rtol=1e-12,
                                   atol=1e-22)
        n = np.array([run.final[(i, 0)]["u"] for i in range(N)])
        lam = -math.log(((n - n.mean()) @ mode) / (mode @ mode) / (0.5 * V)) / t_end
        lam_d = (4 * D / dx ** 2) * math.sin(math.pi / (2 * N)) ** 2
        assert abs(lam - lam_d) / lam_d < 1e-8                  # time integration is not polluting the measurement
        assert run.conductance_report["u"]["kind"] == rg.CONDUCTANCE_DERIVED
        errs.append(abs(lam - lam_c) / lam_c)
    ratios = [errs[k] / errs[k + 1] for k in range(3)]
    orders = [math.log2(x) for x in ratios]
    print(f"\nspatial rel errors {errs}\nratios {ratios}  observed orders {orders}")
    assert all(3.8 <= x <= 4.2 for x in ratios)


def test_derived_conductance_value_temperature_and_geometry_discipline():
    c = rg.DerivedConductance(2e-9, 1e-4, 1e-2, ASSUMED_PARAMETER, "ASSUMED", 298.15)
    assert c.k_Lps == pytest.approx(2e-9 * 1e-4 / 1e-2 * 1000.0, rel=1e-15) and c.kind == rg.CONDUCTANCE_DERIVED
    V = 1e-4 * 1e-2 * 1000.0
    with pytest.raises(rg.GridSourceDomainError) as exc:
        rg.ReactiveGridSpec(2, 1, (A,), (("A", rg.DerivedConductance(2e-9, 1e-4, 1e-2, ASSUMED_PARAMETER, "ASSUMED",
                                                                     310.15)),), cell_volume_L=V)
    assert isinstance(exc.value, SourceDomainError)
    rg.ReactiveGridSpec(2, 1, (A,), (("A", c),), cell_volume_L=V)                       # on-temperature, consistent
    with pytest.raises(rg.GridError, match="V = A dx"):
        rg.ReactiveGridSpec(2, 1, (A,), (("A", c),), cell_volume_L=2 * V)
    with pytest.raises(InvalidClaimTierError):
        rg.DerivedConductance(2e-9, 1e-4, 1e-2, "TRUST_ME", "x", 298.15)
    with pytest.raises(rg.GridError, match="citation"):
        rg.DerivedConductance(2e-9, 1e-4, 1e-2, ASSUMED_PARAMETER, " ", 298.15)


def test_conductance_kind_and_synthetic_reaction_label_are_reported(mono):
    assert mono.conductance_report["A"]["kind"] == rg.CONDUCTANCE_SYNTHETIC == "SYNTHETIC"
    rep = mono.reaction_report[0]
    assert rep["provenance"] == "SYNTHETIC" and not any("citation" in k or "source" in k for k in rep)
    with pytest.raises(rg.GridError, match="no source"):
        main_spec(reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, None, "Smith 1999"),))
    with pytest.raises(TypeError):
        rg.GridReaction("iso", (("A", -1), ("B", 1)), 0.3, 0.1, None, "SOURCED")      # provenance is not settable


# ---------------------------------------------------------------- positivity and trace species
def test_trace_species_beside_a_bulk_species_stays_accurate_and_nonnegative():
    C = Species.of("C", {"X": 1})
    spec = rg.ReactiveGridSpec(3, 3, (A, B, C), (("A", SC(0.4)), ("B", SC(0.05)), ("C", SC(0.2))),
                               reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, frozenset({(1, 1)})),))
    init = {(0, 0): {"A": 1.0}, (2, 2): {"C": 1e-12}}
    segs = (rg.ValveSegment("s", 10.0),)
    r = rg.run_reactive_grid(spec, init, segs, scheme="monolithic", dt=10.0, atol=1e-24)
    ref = rg.reference_solution_coupled(spec, init, segs)
    for c in spec.cells():
        assert r.final[c]["C"] >= 0.0
        assert abs(r.final[c]["C"] - ref["C"][c]) <= 1e-6 * 1e-12
    assert all(led.positivity_verdict == "HELD" for led in r.ledgers)


def test_a_trace_species_alone_in_its_component_is_refused_as_unresolved_not_certified():
    T = Species.of("T", {"Q": 1})
    spec = rg.ReactiveGridSpec(2, 1, (A, T), (("A", SC(0.4)), ("T", SC(0.2))))
    with pytest.raises(rg.GridError, match="NUMERICALLY_UNRESOLVED"):
        rg.run_reactive_grid(spec, {(0, 0): {"A": 1.0, "T": 1e-12}}, (rg.ValveSegment("s", 1.0),), dt=1.0)


def _with_feed(world, compartment, species, rate):
    """The same cells and faces with one extra feed boundary: a world the (now refusing) spec cannot declare."""
    return CoupledWorld(world.compartments, world.interfaces,
                        list(world.boundaries) + [ExternalBoundary("smuggled", compartment, species, "feed", rate=rate)],
                        temperature_K=world.temperature_K)


def test_over_drain_is_refused_with_the_raw_minimum_reported(monkeypatch):
    # finding 6a: a negative feed is refused at declaration (a drain must be a declared first-order sink) ...
    with pytest.raises(rg.GridError, match=">= 0"):
        rg.ReactiveGridSpec(2, 1, (A,), (("A", SC(0.1)),), sources=(((0, 0), "A", -1e-3),))
    # ... and the run-time positivity gate behind that refusal still holds when the drain is smuggled into the world.
    spec = rg.ReactiveGridSpec(2, 1, (A,), (("A", SC(0.1)),))
    real = rg.build_reactive_world
    monkeypatch.setattr(rg, "build_reactive_world",
                        lambda sp, ov=frozenset(): _with_feed(real(sp, ov), rg.cell_name((0, 0)), A, -1e-3))
    with pytest.raises(rg.GridError, match="VIOLATED") as exc:
        rg.run_reactive_grid(spec, {(0, 0): {"A": 1e-3}}, (rg.ValveSegment("s", 5.0),), dt=0.5)
    msg = str(exc.value)
    assert "c0_0/A" in msg and re.search(r"'c0_0/A': -\d", msg)


# ---------------------------------------------------------------- replay, continuation, frames
def test_deterministic_replay_gives_bit_identical_frame_digests(mono):
    again = rg.run_reactive_grid(main_spec(), INIT, SEGS, scheme="monolithic", dt=4.0)
    d1 = [rg.frame_digest(mono, f) for f in mono.frames]
    d2 = [rg.frame_digest(again, f) for f in again.frames]
    assert d1 == d2 and len(set(d1)) == len(d1)
    nudged = {**INIT, (0, 0): {"A": math.nextafter(0.05, 1.0)}}
    other = rg.run_reactive_grid(main_spec(), nudged, SEGS, scheme="monolithic", dt=4.0)
    assert rg.frame_digest(other, other.frames[-1]) != d1[-1]           # the digest sees a one-ulp change


def test_continuation_reproduces_the_full_run_exactly():
    spec = main_spec()
    full = rg.run_reactive_grid(spec, INIT, SEGS, scheme="strang", dt=0.5)
    half = rg.run_reactive_grid(spec, INIT, SEGS[:1], scheme="strang", dt=0.5)
    cont = rg.run_reactive_grid(spec, None, SEGS[1:], scheme="strang", dt=0.5, start=half)
    assert len(cont.frames) == len(full.frames)
    for a, b in zip(cont.frames, full.frames):
        assert (a.step, a.time_s, a.segment) == (b.step, b.time_s, b.segment)
        assert {c: dict(v) for c, v in a.amounts.items()} == {c: dict(v) for c, v in b.amounts.items()}
    assert [rg.frame_digest(cont, f) for f in cont.frames] == [rg.frame_digest(full, f) for f in full.frames]
    # Re-cutting the SAME schedule into different segments: bit-identical when the grid has no boundary terms.  With a
    # source/sink the kernel carries each boundary's flux integral as augmented BDF state and resets it per segment,
    # so the solver's error norm (and step choice) differs -- measured, bounded at solver tolerance, not hidden.
    for kw, exact in ((dict(sources=(), sinks=()), True), ({}, False)):
        sp = main_spec(**kw)
        one = rg.run_reactive_grid(sp, INIT, (rg.ValveSegment("x", 4.0), rg.ValveSegment("y", 4.0)), dt=0.5)
        two = rg.run_reactive_grid(sp, INIT, (rg.ValveSegment("x", 8.0),), dt=0.5)
        d = max(abs(one.final[c][s] - two.final[c][s]) for c in sp.cells() for s in ("A", "B"))
        assert d == 0.0 if exact else d < 1e-9 * 0.05, d
    with pytest.raises(rg.GridError, match="dt"):
        rg.run_reactive_grid(spec, None, SEGS[1:], scheme="strang", dt=0.25, start=half)
    with pytest.raises(rg.GridError, match="unique"):
        rg.run_reactive_grid(spec, None, SEGS[:1], scheme="strang", dt=0.5, start=half)


def test_frame_contract_typed_faces_receipt_and_read_only(mono):
    from experiments.sandbox_foundation.libgibson_frame_example import to_frame, validate_frame
    spec = mono.spec
    closed_frame = [f for f in mono.frames if f.segment == "closed"][-1]
    fd = rg.frame_dict(mono, closed_frame)
    json.dumps(fd, allow_nan=False)
    assert fd["quantities"]["amount_mol"]["unit"] == "mol"
    assert fd["quantities"]["face_flux_mol_per_s"]["unit"] == "mol/s"
    assert fd["quantities"]["face_flux_mol_per_s"]["quantity"] == "molar_flow_rate"
    gate = [f for f in fd["faces"] if f["valve"] == "gate"][0]
    assert gate["state"] == "VALVE_CLOSED" and gate["valve_open"] is False and gate["face_flux_mol_per_s"]["A"] == 0.0
    assert sum(f["state"] == "WALL" for f in fd["faces"]) == len(WALLS)
    open_face = [f for f in fd["faces"] if f["tail"] == [0, 0] and f["head"] == [1, 0]][0]
    amounts = {c: dict(v) for c, v in closed_frame.amounts.items()}
    assert open_face["face_flux_mol_per_s"]["A"] == rg.face_flux(spec, amounts, "A", (0, 0), (1, 0)) != 0.0
    opened = rg.frame_dict(mono, mono.frames[-1])
    assert [f for f in opened["faces"] if f["valve"] == "gate"][0]["state"] == "VALVE_OPEN"
    rec = fd["receipt"]
    assert rec["numerically_verified"] is True and rec["label"] == "UNADMITTED(SYNTHETIC)+NUMERICS-VERIFIED"
    assert any(k.endswith("positivity_depth_over_floor") for k in rec["numerics"]["residuals"])
    snap, ifaces = rg.to_snapshot(mono, mono.frames[-1])
    frame = to_frame(snap, ifaces)
    assert validate_frame(frame) == [] and frame["trust"]["numerically_verified"] is True
    before = dict(mono.final[(0, 0)])
    fd["fields"]["A"]["amount_mol"][0] = 99.0
    fd["faces"][0]["face_flux_mol_per_s"]["A"] = 99.0
    assert dict(mono.final[(0, 0)]) == before and rg.frame_dict(mono, closed_frame) != fd
    with pytest.raises(TypeError):
        mono.final[(0, 0)]["A"] = 1.0


@pytest.mark.parametrize("kw, match", [
    (dict(species=(Species.of("Na+", {"Na": 1}, 1, Phase.AQUEOUS),), conductance=(("Na+", SC(0.1)),), sources=(),
          sinks=(), reactions=()), "NEUTRAL"),
    (dict(nx=10), "9x9"),
    (dict(nx=65, ny=1, walls=frozenset(), valves=(), sources=(), sinks=(), reactions=()), "64"),
    (dict(conductance=(("A", SC(0.4)),)), "every species"),
    (dict(reactions=(("iso", (("A", -1), ("Z", 1)), 0.3, 0.1, None),)), "not in spec.species"),
    (dict(reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, frozenset({(7, 7)})),)), "subset"),
    (dict(walls=frozenset({((0, 0), (2, 0))})), "axis-adjacent"),
])
def test_declaration_refusals(kw, match):
    with pytest.raises(rg.GridError, match=match):
        main_spec(**kw)


def test_a_solid_must_not_diffuse():
    S = Species.of("S", {"X": 1}, 0, Phase.SOLID)
    with pytest.raises(rg.GridError, match="SOLID"):
        rg.ReactiveGridSpec(2, 1, (S,), (("S", SC(0.1)),))
    spec = rg.ReactiveGridSpec(2, 1, (S, A), (("S", SC(0.0)), ("A", SC(0.1))))
    ifaces = rg.build_reactive_world(spec).interfaces
    assert ifaces and all(i.species_a.name != "S" for i in ifaces)
    r = rg.run_reactive_grid(spec, {(0, 0): {"S": 0.01, "A": 0.01}}, (rg.ValveSegment("s", 10.0),), dt=5.0)
    assert r.final[(1, 0)]["S"] == 0.0 and r.final[(0, 0)]["S"] == 0.01 and r.final[(1, 0)]["A"] > 0.0


# ---------------------------------------------------------------- no chemistry in the engine
_BANNED_WORDS = re.compile(r"\b(Ca|CO2|CO3|HCO3|HAc|NaHCO3|NaCl|H2O|Na|Cl|H\+|OH)\b")
_BANNED_SUBSTR = ("calcit", "acet", "carbonat", "vinegar", "sodium", "calcium", "chlorid", "phosphat", "ammon")


def _code_without_docstrings(path: Path) -> tuple:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return ast.unparse(tree), literals


@pytest.mark.parametrize("module", ["reactive_grid_xxv.py", "particles_xxv.py"])
def test_no_chemical_name_special_cases_in_the_engine(module):
    code, literals = _code_without_docstrings(Path(rg.__file__).with_name(module))
    assert not _BANNED_WORDS.search(code), _BANNED_WORDS.search(code)
    low = code.lower()
    assert not [w for w in _BANNED_SUBSTR if re.search(r"(?<![a-z])" + w, low)]   # word starts (InterfaceTransfer is fine)
    assert not literals & {"A", "B", "C", "S", "T", "u", "X", "Q", "iso", "dissolve"}   # no test-species names either


def test_the_source_scan_is_calibrated_it_flags_planted_chemistry(tmp_path):
    planted = tmp_path / "planted.py"
    planted.write_text('"""calcite is fine in a docstring."""\n'
                       'def f(sp):\n    """acetate too."""\n    return 2.0 if sp.name == "CO2" else _acetate_k\n')
    code, literals = _code_without_docstrings(planted)
    assert _BANNED_WORDS.search(code)
    assert [w for w in _BANNED_SUBSTR if re.search(r"(?<![a-z])" + w, code.lower())] == ["acet"]
    assert "calcit" not in code.lower()                                   # docstrings are excluded, as intended


# ---------------------------------------------------------------- red-team regressions (XXV-4 fix round)
C = Species.of("C", {"X": 1})


def test_a_foreign_receipt_cannot_ride_a_grid_frame(mono):
    """Finding 1 (probe p4): an ADMITTED receipt minted for an unrelated mechanism made a SYNTHETIC frame read
    ADMITTED / supported_prediction.  The public projections now take no receipt; the private path checks identity."""
    from experiments.sandbox_foundation.snapshot import ModelRunReceipt
    from experiments.sandbox_foundation.tests.test_snapshot import _verified_executable
    verified, _, policy = _verified_executable()
    foreign = ModelRunReceipt.from_executable(verified, policy, rg.run_receipt(mono).numerics)
    assert foreign.admitted and foreign.model_identity != rg.model_identity(mono)     # the forgery is real
    frame = mono.frames[-1]
    with pytest.raises(TypeError):
        rg.frame_dict(mono, frame, receipt=foreign)
    with pytest.raises(TypeError):
        rg.to_snapshot(mono, frame, receipt=foreign)
    with pytest.raises(TypeError):
        rg.frame_digest(mono, frame, foreign)
    with pytest.raises(rg.GridError, match="model identity"):
        rg._to_snapshot(mono, frame, foreign)
    rec = rg.frame_dict(mono, frame)["receipt"]
    assert rec["admitted"] is False and rec["model_identity"] == rg.model_identity(mono)


def test_continuation_refuses_a_forged_start_and_binds_the_start_state_into_identity():
    """Finding 2 (probe p3): ``dataclasses.replace(half, final=<+1 mol>)`` injected a mole at the hand-off with the
    identity unchanged and every ledger green.  The start is now re-checked against its own frames and ledgers, and the
    state each segment starts from is part of the identity."""
    spec = rg.ReactiveGridSpec(2, 1, (A,), (("A", SC(0.05)),))
    init = {(0, 0): {"A": 0.01}}
    s1, s2 = rg.ValveSegment("s1", 2.0), rg.ValveSegment("s2", 2.0)
    half = rg.run_reactive_grid(spec, init, (s1,), dt=1.0)
    full = rg.run_reactive_grid(spec, init, (s1, s2), dt=1.0)
    honest = rg.run_reactive_grid(spec, None, (s2,), dt=1.0, start=half)
    assert [{c: dict(v) for c, v in f.amounts.items()} for f in honest.frames] == \
        [{c: dict(v) for c, v in f.amounts.items()} for f in full.frames]
    assert rg.model_identity(honest) == rg.model_identity(full)          # the honest cut is invisible
    inj = {c: dict(v) for c, v in half.final.items()}
    inj[(1, 0)]["A"] += 1.0
    forged = MappingProxyType({c: MappingProxyType(v) for c, v in inj.items()})
    with pytest.raises(rg.GridError, match="last frame"):
        rg.run_reactive_grid(spec, None, (s2,), dt=1.0, start=dataclasses.replace(half, final=forged))
    frames = half.frames[:-1] + (dataclasses.replace(half.frames[-1], amounts=forged),)
    with pytest.raises(rg.GridError, match="does not close"):
        rg.run_reactive_grid(spec, None, (s2,), dt=1.0, start=dataclasses.replace(half, final=forged, frames=frames))
    # A forgery made consistent end to end (final, frame AND ledger flux) is not detectable from the record alone --
    # but it can never share the honest chain's identity, because the state s2 starts from is hashed into it.
    led = half.ledgers[-1]
    mat = dict(led.material)
    mat["X"] = (mat["X"][0] + 1.0, mat["X"][1] + 1.0)
    deep = dataclasses.replace(half, final=forged, frames=frames,
                               ledgers=(dataclasses.replace(led, material=MappingProxyType(mat)),))
    out = rg.run_reactive_grid(spec, None, (s2,), dt=1.0, start=deep)
    assert rg.model_identity(out) != rg.model_identity(honest)
    with pytest.raises(rg.GridError, match="initial_digest"):
        rg.run_reactive_grid(spec, None, (s2,), dt=1.0,
                             start=dataclasses.replace(half, initial_digest="0" * 64))


def test_known_gap_the_kernel_floor_holds_a_trace_dip_deeper_than_the_trace_inventory():
    """KNOWN GAP (red-team finding 6b) -- asserted as CURRENT behaviour, deliberately not fixed here.

    The coupled kernel's positivity floor is ABS_FLOOR (1e-10 mol) + POS_REL_FLOOR * max_t |n_j|.  A 1e-12 mol trace
    species beside a 1 mol bulk species of the same component, drained by a -1e-11 mol/s feed, reaches about -4e-11
    mol (~40x its whole inventory) and still reads HELD_WITHIN_PHYSICAL_FLOOR.  The repair (relative floor on the
    POSITIVE peak; never HELD when |min| exceeds that peak) was attempted and reverted: it flips the pinned XXII
    contract test_xxii_s3_numerical_resolution::test_negative_trace_dip_within_the_floor_is_flagged_resolution_limited.
    The grid closes its own route to this state (a negative feed is refused at declaration, finding 6a); the kernel
    does surface ``positivity_resolution_limited``.  If the kernel is repaired, this test must be rewritten."""
    spec = rg.ReactiveGridSpec(2, 1, (A, C), (("A", SC(0.1)), ("C", SC(0.1))))
    world = _with_feed(rg.build_reactive_world(spec), rg.cell_name((1, 0)), C, -1e-11)
    tr = world.integrate(rg._initial_state(spec, {(0, 0): {"A": 1.0}, (1, 0): {"C": 1e-12}}), duration=5.0, n_steps=5,
                         scheme="strang", rtol=1e-10, atol=1e-14, require_certified_execution=True)
    r = tr.receipt
    assert min(r.negative_minima.values()) < -10 * 1e-12               # deeper than C's whole inventory, ten times
    assert r.positivity_verdict == "HELD_WITHIN_PHYSICAL_FLOOR" and r.positivity_held      # the gap, pinned
    assert r.positivity_resolution_limited                              # what the kernel does say about it


def test_a_resolution_limited_positivity_pass_is_refused_not_certified(monkeypatch):
    """Finding 6, grid side of 6b: the kernel passes the trace dip above (HELD_WITHIN_PHYSICAL_FLOOR) but flags it
    positivity_resolution_limited.  The grid previously ignored the flag and certified the segment; it now refuses it,
    as it refuses a trace component the ledger cannot resolve.  The drain is smuggled past the declaration (6a)."""
    spec = rg.ReactiveGridSpec(2, 1, (A, C), (("A", SC(0.1)), ("C", SC(0.1))))
    real = rg.build_reactive_world
    monkeypatch.setattr(rg, "build_reactive_world",
                        lambda sp, ov=frozenset(): _with_feed(real(sp, ov), rg.cell_name((1, 0)), C, -1e-11))
    with pytest.raises(rg.GridError, match=rg.RESOLUTION_LIMITED_POSITIVITY) as exc:
        rg.run_reactive_grid(spec, {(0, 0): {"A": 1.0}, (1, 0): {"C": 1e-12}}, (rg.ValveSegment("s", 5.0),), dt=1.0)
    assert re.search(r"'c1_0/C': -\d", str(exc.value))                  # the raw minimum travels with the refusal


def test_spec_containers_are_frozen_so_a_finished_runs_identity_cannot_move():
    """Finding 8 (probe p9): caller lists for sources/sinks/valves were stored by reference."""
    src, snk, vlv = [((0, 0), "A", 1e-3)], [[[1, 0], "A", 0.01]], [["v", [0, 0], [1, 0]]]
    spec = rg.ReactiveGridSpec(2, 1, (A,), (("A", SC(0.1)),), sources=src, sinks=snk, valves=vlv)
    for items in (spec.sources, spec.sinks, spec.valves):
        assert type(items) is tuple and all(type(e) is tuple for e in items)
    assert all(type(e[0]) is tuple for e in spec.sources + spec.sinks)
    assert all(type(e[1]) is tuple and type(e[2]) is tuple for e in spec.valves)
    run = rg.run_reactive_grid(spec, {(0, 0): {"A": 0.01}}, (rg.ValveSegment("s", 2.0),), dt=1.0)
    mid = rg.model_identity(run)
    src[0] = ((1, 0), "A", 5.0)
    snk[0][0][0] = 0
    vlv.append(["w", [0, 0], [1, 0]])
    assert rg.model_identity(run) == mid


def test_derived_conductances_on_one_grid_must_share_one_mesh():
    """Finding 9 (probe p5 case 1): same D, same grid, A*dx = V for each species, yet k differed 100x."""
    D, V = 1e-9, 1.0
    cA = rg.DerivedConductance(D, 1e-2, 1e-1, ASSUMED_PARAMETER, "same D", 298.15)
    cB = rg.DerivedConductance(D, 1e-1, 1e-2, ASSUMED_PARAMETER, "same D", 298.15)
    with pytest.raises(rg.GridError, match="one mesh"):
        rg.ReactiveGridSpec(2, 1, (A, B), (("A", cA), ("B", cB)), cell_volume_L=V)
    cB2 = rg.DerivedConductance(3 * D, 1e-2, 1e-1, ASSUMED_PARAMETER, "another D", 298.15)
    ok = rg.ReactiveGridSpec(2, 1, (A, B), (("A", cA), ("B", cB2)), cell_volume_L=V)       # one mesh, two D: fine
    assert ok.conductance_of("B").k_Lps == pytest.approx(3 * ok.conductance_of("A").k_Lps, rel=1e-15)


def test_the_commutator_sees_the_affine_source_and_the_control_discriminates():
    """Finding 10 (probe p5 case 5): uniform conductance + uniform reaction commute, but a source feeding the reacting
    species does not commute with the reaction; the old ||[T, R]|| read 0 while Lie splitting was first-order wrong."""
    kw = dict(conductance=(("A", SC(0.1)), ("B", SC(0.1))), reactions=(("iso", (("A", -1), ("B", 1)), 0.3, 0.1, None),))
    fed = rg.ReactiveGridSpec(2, 1, (A, B), sources=(((0, 0), "A", 1e-3),), **kw)
    unfed = rg.ReactiveGridSpec(2, 1, (A, B), **kw)
    init, segs = {(0, 0): {"A": 0.01}}, (rg.ValveSegment("s", 4.0),)

    def lie_err(spec):
        ref = rg.reference_solution_coupled(spec, init, segs)
        lie = rg.run_reactive_grid(spec, init, segs, scheme="lie", dt=1.0)
        return max(abs(lie.final[c][s] - ref[s][c]) for c in spec.cells() for s in ("A", "B"))
    assert rg.splitting_commutator_norm(unfed) == 0.0 and lie_err(unfed) < 1e-11
    assert rg.splitting_commutator_norm(fed) > 1e-4 and lie_err(fed) > 1e-4


def test_a_solid_can_neither_be_fed_nor_drained():
    """Finding 11 (probe p5 case 4)."""
    S = Species.of("S", {"X": 1}, 0, Phase.SOLID)
    base = dict(species=(S, A), conductance=(("S", SC(0.0)), ("A", SC(0.1))))
    with pytest.raises(rg.GridError, match="SOLID"):
        rg.ReactiveGridSpec(2, 1, sinks=(((0, 0), "S", 0.5),), **base)
    with pytest.raises(rg.GridError, match="SOLID"):
        rg.ReactiveGridSpec(2, 1, sources=(((1, 0), "S", 1e-3),), **base)
    rg.ReactiveGridSpec(2, 1, sources=(((1, 0), "A", 1e-3),), sinks=(((0, 0), "A", 0.5),), **base)


def test_one_face_carries_at_most_one_valve():
    """Finding 13 (probe p5 case 3): valve 'b' open, the frame reported the face CLOSED under valve 'b'."""
    with pytest.raises(rg.GridError, match="share face"):
        rg.ReactiveGridSpec(2, 1, (A,), (("A", SC(0.1)),), valves=(("a", (0, 0), (1, 0)), ("b", (1, 0), (0, 0))))


@pytest.mark.parametrize("tier", sorted(ct.CLAIM_TIERS))
def test_an_input_diffusivity_carries_only_an_input_tier(tier):
    """Finding 14 (probe p10): the top claim tier was accepted on a bare string.  Only the assumed tier survives: a cited
    D is provenance (D_citation), not CALIBRATED_TO_MEASUREMENT (a fit with a preserved fit/validation split)."""
    if tier in (ct.ASSUMED_PARAMETER, ct.UNVERIFIED):
        assert rg.DerivedConductance(1e-9, 1e-2, 1e-1, tier, "cited", 298.15).D_source_tier == tier
    else:
        with pytest.raises(rg.GridError, match="input diffusivity"):
            rg.DerivedConductance(1e-9, 1e-2, 1e-1, tier, "cited", 298.15)


def test_reference_face_enumeration_agrees_with_the_executing_world_on_random_specs():
    """The expm reference enumerates faces itself (no spec.all_faces/open_faces/_face), so a geometry bug in the
    engine is not common-mode.  Checked against the interfaces the integrator actually executes; the control drops
    the walls from the reference and must then disagree."""
    rng = random.Random(20261108)
    discriminated = 0
    for _ in range(80):
        nx, ny = rng.randint(1, 5), rng.randint(1, 5)
        faces = [tuple(f) for f in sorted(rg.reference_open_faces(nx, ny, (), ()), key=sorted)]
        faces = [f if rng.random() < 0.5 else f[::-1] for f in faces]          # orientation must not matter
        rng.shuffle(faces)
        nw = rng.randint(0, len(faces) // 2)
        walls, rest = faces[:nw], faces[nw:]
        valves = tuple((f"v{k}", a, b) for k, (a, b) in enumerate(rest[:rng.randint(0, len(rest))]))
        open_set = frozenset(nm for nm, _, _ in valves if rng.random() < 0.5)
        spec = rg.ReactiveGridSpec(nx, ny, (A,), (("A", SC(0.1)),), walls=frozenset(walls), valves=valves)
        executed = {frozenset((i.a, i.b)) for i in rg.build_reactive_world(spec, open_set).interfaces}
        engine = {frozenset(map(rg.cell_name, f)) for f in spec.open_faces(open_set)}
        ref = {frozenset(map(rg.cell_name, f))                            # the RAW caller walls/valves, not the spec's
               for f in rg.reference_open_faces(nx, ny, walls, valves, open_set)}
        assert executed == engine == ref
        if walls:
            no_walls = {frozenset(map(rg.cell_name, f))
                        for f in rg.reference_open_faces(nx, ny, (), valves, open_set)}
            assert no_walls != executed
            discriminated += 1
    assert discriminated > 20
