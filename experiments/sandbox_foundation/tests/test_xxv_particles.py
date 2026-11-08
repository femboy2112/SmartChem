"""OPERATION XXV Phase IV -- solid inventory + grains as an exact projection, the illustrative granular automaton, and
its operator-split coupling to the reactive grid."""
from __future__ import annotations

import json
import math
from fractions import Fraction

import pytest

from experiments.sandbox_foundation import particles_xxv as px
from experiments.sandbox_foundation import reactive_grid_xxv as rg
from experiments.sandbox_foundation.general_kernel import Phase, Species

S = Species.of("S", {"X": 1}, 0, Phase.SOLID)
U = Species.of("u", {"X": 1})
Q = px.GRAIN_QUANTUM_MOL
SC = rg.SyntheticConductance
KF = 0.01


def _spec(nx, ny, **kw):
    base = dict(species=(S, U), conductance=(("S", SC(0.0)), ("u", SC(0.05))))
    base.update(kw)
    return rg.ReactiveGridSpec(nx, ny, **base)


def _proj(spec, inv):
    return px.GrainProjection.of(spec.cells(), [inv.get(c, 0.0) for c in spec.cells()])


COUPLED_SPEC = _spec(3, 4, walls=frozenset({((1, 1), (1, 2))}), valves=(("trap", (0, 2), (0, 3)),),
                     reactions=(("dissolve", (("S", -1), ("u", 1)), KF, 0.0, None),))
COUPLED_INIT = {(0, 0): {"S": 3e-4}, (1, 0): {"S": 2e-4}, (2, 1): {"S": 1e-4}}
COUPLED_SEGS = (rg.ValveSegment("s1", 2.0), rg.ValveSegment("s2", 2.0, {"trap"}),
                rg.ValveSegment("s3", 2.0, {"trap"}))


def _coupled(seed=1):
    return px.run_coupled_particles(COUPLED_SPEC, COUPLED_INIT, COUPLED_SEGS, solid="S", dt=0.5,
                                    sweeps_per_segment=2, seed=seed)


@pytest.fixture(scope="module")
def coupled():
    return _coupled()


# ---------------------------------------------------------------- the projection
def test_projection_invariant_is_exact_and_an_unbacked_grain_is_refused():
    cells = [(k, 0) for k in range(6)]
    inv = [0.0, 3e-4, Fraction(7, 2 ** 22), 1e-9, 2.0 ** -20, 0.1]
    p = px.GrainProjection.of(cells, inv)
    assert p.invariant_holds()
    assert p.grains[:5] == (0, 314, 1, 0, 1) and p.residual[2] == Fraction(3, 2 ** 22) and p.residual[4] == 0
    assert all(0 <= r < Q for r in p.residual)
    assert p.total_grains * Q + sum(p.residual) == sum(Fraction(x) for x in inv)
    with pytest.raises(px.ParticleError, match="inventory"):
        px.GrainProjection(((0, 0),), Q, (Fraction(0),), (1,), (Fraction(0),))          # a grain with no inventory
    with pytest.raises(px.ParticleError, match="inventory"):
        px.GrainProjection(((0, 0),), Q, (5 * Q,), (6,), (-Q,))                       # an extra grain, balanced residual
    with pytest.raises(px.ParticleError, match="dyadic"):
        px.GrainProjection.of(cells, inv, Fraction(1, 1000))
    spec = _spec(2, 1)
    auto = px.automaton_for(spec)
    with pytest.raises(px.ParticleError, match="no inventory backs"):
        px.transfer_grains(_proj(spec, {(0, 0): 0.5 * float(Q)}), auto, (0, 0), (1, 0), 1)
    walled = _spec(2, 1, walls=frozenset({((0, 0), (1, 0))}))
    with pytest.raises(px.ParticleError, match="closed"):
        px.transfer_grains(_proj(walled, {(0, 0): 1e-3}), px.automaton_for(walled), (0, 0), (1, 0), 1)
    moved, tr = px.transfer_grains(_proj(spec, {(0, 0): 1e-3}), auto, (0, 0), (1, 0), 3)
    assert tr.amount_mol == 3 * Q and moved.grains[1] == 3 and moved.total_inventory == Fraction(1e-3)


# ---------------------------------------------------------------- the automaton
def test_automaton_sweeps_conserve_exactly_and_every_transfer_is_whole_quanta():
    spec = _spec(4, 5, walls=frozenset({((1, 2), (1, 3)), ((2, 1), (2, 2)), ((0, 3), (1, 3))}))
    inv = {(i, j): (1 + 3 * i + 7 * j) * 1.7e-5 for i in range(4) for j in range(3)}
    proj = _proj(spec, inv)
    auto = px.automaton_for(spec, capacity=40, seed=3)
    n_moved = 0
    for sweep in range(15):
        before = proj
        proj, transfers = px.ca_sweep(proj, auto, sweep)
        assert proj.invariant_holds()
        assert proj.total_inventory == before.total_inventory and proj.total_grains == before.total_grains
        delta = {c: Fraction(0) for c in spec.cells()}
        for t in transfers:
            assert t.amount_mol == t.n_grains * Q and t.n_grains >= 1
            assert auto.open(t.src, t.dst)
            delta[t.src] -= t.amount_mol
            delta[t.dst] += t.amount_mol
        for k, c in enumerate(spec.cells()):                    # the field moved by EXACTLY the recorded transfers
            assert proj.inventory[k] == before.inventory[k] + delta[c]
            assert proj.residual[k] == before.residual[k]          # residual (sub-quantum) inventory never moves
            if proj.grains[k] > before.grains[k]:
                assert proj.grains[k] <= 40                         # arrivals respect the declared capacity
        n_moved += len(transfers)
    assert n_moved > 0


def test_a_wall_blocks_the_fall_and_its_absence_does_not():
    walled = _spec(1, 4, walls=frozenset({((0, 1), (0, 2))}))
    free = _spec(1, 4)
    for spec, stop in ((walled, (0, 1)), (free, (0, 3))):
        proj = _proj(spec, {(0, 0): 1e-4})
        auto = px.automaton_for(spec)
        for sweep in range(6):
            proj, _ = px.ca_sweep(proj, auto, sweep)
        g = dict(zip(proj.cells, proj.grains))
        assert g[stop] == Fraction(1e-4) // Q and sum(g.values()) == g[stop]
        assert proj.residual[proj.at((0, 0))] == Fraction(1e-4) - (Fraction(1e-4) // Q) * Q


def test_a_closed_valve_holds_grains_until_it_opens():
    spec = _spec(1, 3, valves=(("v", (0, 1), (0, 2)),))
    proj = _proj(spec, {(0, 0): 5e-5})
    for sweep in range(4):
        proj, _ = px.ca_sweep(proj, px.automaton_for(spec, frozenset()), sweep)
    assert proj.grains[proj.at((0, 2))] == 0 and proj.grains[proj.at((0, 1))] > 0
    proj, tr = px.ca_sweep(proj, px.automaton_for(spec, {"v"}), 4)
    assert proj.grains[proj.at((0, 1))] == 0 and tr[0].dst == (0, 2)


def test_seeded_tie_break_is_deterministic_and_the_seed_is_actually_used():
    spec = _spec(3, 2)
    start = _proj(spec, {(1, 0): float(3 * Q), (1, 1): float(Q)})       # cell below is full at capacity 1

    def outcome(seed):
        proj, tr = px.ca_sweep(start, px.automaton_for(spec, capacity=1, seed=seed), 0)
        return tuple((t.src, t.dst, t.n_grains, t.kind) for t in tr), proj.grains

    outcomes = {seed: outcome(seed) for seed in range(16)}
    assert all(outcome(seed) == outcomes[seed] for seed in range(16))    # replay
    dsts = {o[0][0][1] for o in outcomes.values()}
    assert dsts == {(0, 0), (2, 0)}                                       # both sides chosen by some seed
    assert all(o[0][0][3] == "slide" and len(o[0]) == 1 for o in outcomes.values())


# ---------------------------------------------------------------- the coupled run
def test_coupled_run_labels_and_the_ledger_invariant_at_every_frame(coupled):
    assert coupled.automaton_label == px.ILLUSTRATIVE_GRANULAR_AUTOMATON
    assert coupled.dissolution_label == px.SYNTHETIC_FIRST_ORDER_DISSOLUTION
    assert coupled.spec.reactions[0].provenance == "SYNTHETIC" and coupled.spec.reactions[0].kr == 0.0
    assert {f.stage for f in coupled.frames} == {"initial", "kernel", "automaton", "handoff"}
    for f in coupled.frames:
        p = f.projection
        assert p.invariant_holds()
        assert p.total_grains * p.quantum + sum(p.residual, Fraction(0)) == p.total_inventory
    assert len(coupled.transfers) > 0


def test_grains_equal_the_field_inventory_after_each_coupled_dissolution_step(coupled):
    kernel_frames = [f for f in coupled.frames if f.stage == "kernel"]
    k = 0
    for run in coupled.kernel_runs:
        for kf in run.frames[1:]:
            pf = kernel_frames[k]
            field = [Fraction(kf.amounts[c]["S"]) for c in coupled.spec.cells()]
            assert list(pf.projection.inventory) == field
            assert pf.projection.total_grains * Q + sum(pf.projection.residual) == sum(field)
            k += 1
    assert k == len(kernel_frames)
    totals = [f.projection.total_grains for f in coupled.frames]
    stages = [f.stage for f in coupled.frames]
    for i in range(1, len(totals)):
        if stages[i] == "automaton":
            assert totals[i] == totals[i - 1]                     # the automaton never creates or destroys grains
        elif stages[i] == "kernel":
            assert totals[i] <= totals[i - 1]                     # kr = 0: dissolution only, no invented precipitation
    assert totals[-1] < totals[0]


def test_coupled_solid_ledger_closes_exactly_and_tracks_the_analytic_decay(coupled):
    p0 = coupled.frames[0].projection.total_inventory
    pf = coupled.frames[-1].projection.total_inventory
    total = p0
    for led, run in zip(coupled.ledgers, coupled.kernel_runs):
        assert led.automaton_net_mol == 0
        cells = coupled.spec.cells()
        start = max(Fraction(run.frames[0].amounts[c]["S"]) for c in cells)
        assert abs(led.handoff_rounding_mol) <= len(cells) * start * Fraction(1, 2 ** 53)
        du = run.frames[-1].total_mol["u"] - run.frames[0].total_mol["u"]
        assert float(led.kernel_solid_change_mol) == pytest.approx(-du, rel=1e-9)   # solid lost == solute gained
        total += led.kernel_solid_change_mol + led.automaton_net_mol + led.handoff_rounding_mol
    assert total == pf                                                  # exact telescoping closure
    t_end = sum(s.duration_s for s in COUPLED_SEGS)
    assert float(pf) == pytest.approx(float(p0) * math.exp(-KF * t_end), rel=1e-7)


def test_coupled_replay_is_bit_identical(coupled):
    again = _coupled()
    assert [px.particle_frame_digest(again, f) for f in again.frames] == \
        [px.particle_frame_digest(coupled, f) for f in coupled.frames]
    fd = px.particle_frame_dict(coupled, coupled.frames[-1])
    json.dumps(fd, allow_nan=False)
    assert fd["automaton"] == "ILLUSTRATIVE_GRANULAR_AUTOMATON" and fd["ledger_invariant_exact"] is True
    assert fd["quantities"]["grains"]["unit"] == "1" and fd["quantities"]["solid_inventory_mol"]["unit"] == "mol"
    fd["grains"][0] = 10 ** 6
    assert px.particle_frame_dict(coupled, coupled.frames[-1])["grains"][0] != 10 ** 6


def test_coupled_run_refuses_a_non_solid_ledger_species():
    with pytest.raises(px.ParticleError, match="SOLID"):
        px.run_coupled_particles(COUPLED_SPEC, COUPLED_INIT, COUPLED_SEGS, solid="u", dt=0.5, sweeps_per_segment=1)


# ---------------------------------------------------------------- red-team regressions (XXV-4 fix round)
W = Species.of("w", {"X": 2})


@pytest.mark.parametrize("rx, match", [
    (("dissolve", (("S", -1), ("u", 1)), 1e-3, 5.0, None), "kr"),                  # probe p6: kr > 0 nucleates
    (("grow", (("u", -1), ("S", 1)), 1e-3, 0.0, None), "PRODUCES"),               # forward precipitation
    (("pair", (("S", -1), ("u", -1), ("w", 1)), 1e-3, 0.0, None), "first-order"),
    (("dimer", (("S", -2), ("w", 1)), 1e-3, 0.0, None), "first-order"),
])
def test_a_reaction_that_could_create_solid_or_is_not_first_order_dissolution_is_refused(rx, match):
    """Finding 7 (probe p6): kr = 5 created 10442 grains in cells holding no solid, under the dissolution label."""
    spec = _spec(1, 3, species=(S, U, W), conductance=(("S", SC(0.0)), ("u", SC(0.05)), ("w", SC(0.05))),
                 reactions=(rx,))
    with pytest.raises(px.ParticleError, match=match):
        px.run_coupled_particles(spec, {(0, 0): {"u": 0.01}}, (rg.ValveSegment("s", 4.0),), solid="S", dt=1.0,
                                 sweeps_per_segment=0)


def test_the_dissolution_label_is_derived_from_the_validated_law(coupled):
    assert px.solid_law_label(COUPLED_SPEC, "S") == px.SYNTHETIC_FIRST_ORDER_DISSOLUTION == coupled.dissolution_label
    inert = _spec(1, 2)
    run = px.run_coupled_particles(inert, {(0, 0): {"S": 2.0 ** -10}}, (rg.ValveSegment("s", 1.0),), solid="S",
                                   dt=1.0, sweeps_per_segment=1)
    assert run.dissolution_label == px.NO_SOLID_REACTION
    assert px.particle_frame_dict(run, run.frames[-1])["dissolution"] == "NO_SOLID_REACTION"


def test_an_inexact_initial_inventory_is_refused_not_rounded_off_the_ledger():
    """Finding 15 (probe p6): Fraction(1, 3) was silently float-rounded with no ledger entry."""
    spec = _spec(1, 2)
    segs = (rg.ValveSegment("s", 1.0),)
    for inv in ({(0, 0): {"S": Fraction(1, 3)}}, {(0, 0): {"S": 1e-3, "u": Fraction(1, 10)}}):
        with pytest.raises(px.ParticleError, match="not exactly representable"):
            px.run_coupled_particles(spec, inv, segs, solid="S", dt=1.0, sweeps_per_segment=1)
    exact = Fraction(3, 2 ** 22)                                         # dyadic: a float holds it exactly
    run = px.run_coupled_particles(spec, {(0, 0): {"S": exact}}, segs, solid="S", dt=1.0, sweeps_per_segment=1)
    assert run.frames[0].projection.inventory[0] == exact
