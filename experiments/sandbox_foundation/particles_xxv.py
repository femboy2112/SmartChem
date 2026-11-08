"""OPERATION XXV Phase IV -- a conservative solid inventory with discrete grains as a PROJECTION (3.0 RESEARCH ONLY).

STATE VS PROJECTION.  The state is the per-cell solid inventory n_i (mol), held exactly as ``fractions.Fraction`` (a
float inventory from the kernel converts exactly: every float is a dyadic rational).  Grains are DERIVED from it with
a dyadic quantum q (default 2**-20 mol):

    grains_i = floor(n_i / q),     residual_i = n_i - grains_i q,     0 <= residual_i < q

so  sum_i grains_i q + sum_i residual_i == sum_i n_i  holds EXACTLY at every frame (``GrainProjection`` re-checks it
at construction and refuses any grain count the inventory does not back).  A grain therefore cannot exist without
inventory: grains appear or vanish only when an inventory change (here SYNTHETIC first-order dissolution in the kernel)
moves a residual across a quantum boundary.

THE AUTOMATON.  ``ILLUSTRATIVE_GRANULAR_AUTOMATON`` -- a deterministic gravity cellular automaton, not calibrated
granular physics.  Gravity points to +j (row index increasing).  In one sweep, rows are visited bottom-up and cells
left to right; only grains present at the start of the sweep move (at most one cell per sweep):
  * FALL: up to (room below) grains move to (i, j+1) if that face is open (not a wall, not a closed valve);
  * SLIDE: if the fall is blocked (closed face, bottom row excluded, or the cell below is at capacity), ONE grain may
    move sideways to (i+-1, j) when that face and the face below the neighbour are open and both cells have room;
    when both sides qualify the choice is a seeded deterministic draw (``random.Random(f"{seed}:{sweep}:{i}:{j}")``).
Every move is a MATERIAL TRANSFER of exactly n_grains * q mol of solid between cells, recorded as a ``GrainTransfer``;
the inventory is updated by the same transfer, so a sweep changes no total (checked exactly, fail-closed).

COUPLING.  Solids carry face conductance 0 in the reactive grid (they never diffuse).  ``run_coupled_particles``
alternates a kernel segment (reaction + transport) with a fixed number of automaton sweeps -- an operator split,
declared as such; its splitting error is not bounded here.  The kernel is float: handing the exact post-sweep
inventory back to it rounds each cell to the nearest float (<= half an ulp).  That rounding is not hidden: it is an
exact ``handoff_rounding_mol`` term in the solid ledger.

DISSOLUTION.  The sourced, audited calcite rate law is not reused: it produces charged ions, and the grid transports
neutral species only.  The dissolution coupled here is a SYNTHETIC first-order law (a ``GridReaction`` solid -> solute
with kr = 0: rate = kf * n_solid / V), labelled ``SYNTHETIC_FIRST_ORDER_DISSOLUTION``.  No nucleation or precipitation
rate is modelled, so grains are never created from solution: ``run_coupled_particles`` REFUSES any reaction that
produces the solid, has kr != 0 (a mass-action reverse rate needs no solid present), or is not exactly solid -> products
at first order.  The label is derived from that validation (``NO_SOLID_REACTION`` when no reaction touches the solid).
An initial inventory that a float cannot hold exactly is refused rather than rounded off the ledger.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from fractions import Fraction
from types import MappingProxyType

from experiments.sandbox_foundation.general_kernel import Phase
from experiments.sandbox_foundation.reactive_grid_xxv import (ReactiveGridSpec, ValveSegment, _face,
                                                              run_reactive_grid)
from experiments.sandbox_foundation.spatial_grid_xxiv import GridError

GRAIN_QUANTUM_MOL = Fraction(1, 2 ** 20)
ILLUSTRATIVE_GRANULAR_AUTOMATON = "ILLUSTRATIVE_GRANULAR_AUTOMATON"
SYNTHETIC_FIRST_ORDER_DISSOLUTION = "SYNTHETIC_FIRST_ORDER_DISSOLUTION"
NO_SOLID_REACTION = "NO_SOLID_REACTION"


class ParticleError(GridError):
    """Fail-closed error for the solid ledger / grain projection."""


def _exact(x) -> Fraction:
    if isinstance(x, bool):
        raise ParticleError("an inventory cannot be a bool")
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            raise ParticleError("an inventory must be finite")
        return Fraction(x)                                    # exact: a float is a dyadic rational
    raise ParticleError(f"an inventory must be a Fraction, int or float (got {type(x).__name__})")


def _is_dyadic(q: Fraction) -> bool:
    d = q.denominator
    return d & (d - 1) == 0


@dataclass(frozen=True)
class GrainProjection:
    """Per-cell solid inventory (the state) and its exact grain/residual projection."""
    cells: tuple
    quantum: Fraction
    inventory: tuple                     # Fraction per cell (mol)
    grains: tuple                        # int per cell
    residual: tuple                      # Fraction per cell (mol), in [0, quantum)

    def __post_init__(self):
        if type(self.quantum) is not Fraction or not self.quantum > 0 or not _is_dyadic(self.quantum):
            raise ParticleError("the grain quantum must be a positive dyadic Fraction (e.g. Fraction(1, 2**20))")
        n = len(self.cells)
        if not (len(self.inventory) == len(self.grains) == len(self.residual) == n):
            raise ParticleError("cells, inventory, grains and residual must have equal length")
        for c, inv, g, r in zip(self.cells, self.inventory, self.grains, self.residual):
            if type(inv) is not Fraction or type(r) is not Fraction:
                raise ParticleError("inventory and residual must be exact Fractions")
            if type(g) is not int:
                raise ParticleError("a grain count must be an int")
            if inv < 0:
                raise ParticleError(f"negative solid inventory {inv} in cell {c}")
            if g != inv // self.quantum or r != inv - g * self.quantum:
                raise ParticleError(f"cell {c}: {g} grain(s) + residual {r} are not the projection of inventory {inv} "
                                    f"(a grain needs inventory behind it; grains are derived, never declared)")

    @classmethod
    def of(cls, cells, inventory, quantum: Fraction = GRAIN_QUANTUM_MOL) -> "GrainProjection":
        inv = tuple(_exact(x) for x in inventory)
        if type(quantum) is not Fraction:
            raise ParticleError("the grain quantum must be a Fraction")
        g = tuple(int(x // quantum) for x in inv)
        return cls(tuple(tuple(c) for c in cells), quantum, inv, g, tuple(x - k * quantum for x, k in zip(inv, g)))

    def at(self, cell) -> int:
        return self.cells.index(tuple(cell))

    @property
    def total_inventory(self) -> Fraction:
        return sum(self.inventory, Fraction(0))

    @property
    def total_grains(self) -> int:
        return sum(self.grains)

    def invariant_holds(self) -> bool:
        """sum grains*q + sum residual == sum inventory, exactly, and per cell."""
        q = self.quantum
        per_cell = all(g * q + r == inv for g, r, inv in zip(self.grains, self.residual, self.inventory))
        return per_cell and self.total_grains * q + sum(self.residual, Fraction(0)) == self.total_inventory


@dataclass(frozen=True)
class GrainTransfer:
    sweep: int
    src: tuple
    dst: tuple
    n_grains: int
    amount_mol: Fraction                 # == n_grains * quantum, exactly
    kind: str                            # "fall" | "slide"


@dataclass(frozen=True)
class GranularAutomaton:
    nx: int
    ny: int
    passable: frozenset                  # open faces (canonical orientation)
    capacity: int | None = None          # max grains per cell (an illustrative packing limit), None = unbounded
    seed: int = 0
    label: str = field(default=ILLUSTRATIVE_GRANULAR_AUTOMATON, init=False)

    def __post_init__(self):
        if self.capacity is not None and (type(self.capacity) is not int or self.capacity < 1):
            raise ParticleError("capacity must be a positive int or None")
        if type(self.seed) is not int:
            raise ParticleError("seed must be an int")
        object.__setattr__(self, "passable", frozenset(_face(a, b) for a, b in self.passable))

    def open(self, a, b) -> bool:
        return _face(a, b) in self.passable

    def room(self, grains: dict, c) -> int | None:
        return None if self.capacity is None else max(0, self.capacity - grains[c])


def automaton_for(spec: ReactiveGridSpec, open_valves=frozenset(), *, capacity=None, seed=0) -> GranularAutomaton:
    """The automaton's open faces are exactly the grid's open faces for this valve state (walls and closed valves
    block grains the same way they block solutes)."""
    return GranularAutomaton(spec.nx, spec.ny, frozenset(spec.open_faces(open_valves)), capacity, seed)


def transfer_grains(proj: GrainProjection, automaton: GranularAutomaton, src, dst, n_grains: int, *, sweep: int = -1,
                    kind: str = "fall"):
    """Move ``n_grains`` whole grains (n_grains * q mol of solid) across one open face.  Refused if the source does
    not hold that many grains (no inventory backs them) or the face is closed."""
    src, dst = tuple(src), tuple(dst)
    if type(n_grains) is not int or n_grains < 1:
        raise ParticleError("n_grains must be a positive int")
    if abs(src[0] - dst[0]) + abs(src[1] - dst[1]) != 1:
        raise ParticleError(f"{src} -> {dst} is not a single face")
    if not automaton.open(src, dst):
        raise ParticleError(f"face {src} -> {dst} is closed (wall or closed valve)")
    i, j = proj.at(src), proj.at(dst)
    if proj.grains[i] < n_grains:
        raise ParticleError(f"cell {src} holds {proj.grains[i]} grain(s); moving {n_grains} would create solid that "
                            f"no inventory backs")
    amt = n_grains * proj.quantum
    inv = list(proj.inventory)
    inv[i] -= amt
    inv[j] += amt
    return (GrainProjection.of(proj.cells, inv, proj.quantum),
            GrainTransfer(sweep, src, dst, n_grains, amt, kind))


def ca_sweep(proj: GrainProjection, automaton: GranularAutomaton, sweep: int):
    """One deterministic sweep (see module docstring).  Returns (new projection, transfers).  The exact solid total
    is checked unchanged before returning (fail-closed)."""
    if (automaton.nx * automaton.ny) != len(proj.cells):
        raise ParticleError("automaton and projection disagree on the grid size")
    q = proj.quantum
    inv = {c: proj.inventory[k] for k, c in enumerate(proj.cells)}
    grains = {c: proj.grains[k] for k, c in enumerate(proj.cells)}
    mobile = dict(grains)
    transfers = []

    def move(src, dst, k, kind):
        inv[src] -= k * q
        inv[dst] += k * q
        grains[src] -= k
        grains[dst] += k
        transfers.append(GrainTransfer(sweep, src, dst, k, k * q, kind))

    def has_room(c):
        r = automaton.room(grains, c)
        return r is None or r > 0

    for j in range(automaton.ny - 1, -1, -1):
        for i in range(automaton.nx):
            c = (i, j)
            m = mobile[c]
            if m == 0 or j + 1 >= automaton.ny:
                continue
            below = (i, j + 1)
            if automaton.open(c, below):
                room = automaton.room(grains, below)
                k = m if room is None else min(m, room)
                if k:
                    move(c, below, k, "fall")
                    m -= k
            if m > 0:
                cands = []
                for d in (-1, 1):
                    side = (i + d, j)
                    if (0 <= side[0] < automaton.nx and automaton.open(c, side)
                            and automaton.open(side, (side[0], j + 1)) and has_room(side)
                            and has_room((side[0], j + 1))):
                        cands.append(side)
                if cands:
                    pick = cands[0] if len(cands) == 1 else \
                        cands[0 if random.Random(f"{automaton.seed}:{sweep}:{i}:{j}").random() < 0.5 else 1]
                    move(c, pick, 1, "slide")
                    m -= 1
            mobile[c] = m
    out = GrainProjection.of(proj.cells, [inv[c] for c in proj.cells], q)
    if out.total_inventory != proj.total_inventory or out.total_grains != proj.total_grains:
        raise ParticleError("internal: an automaton sweep changed the solid total")
    return out, tuple(transfers)


# ============================================================ coupled run
@dataclass(frozen=True)
class ParticleFrame:
    index: int
    time_s: float
    stage: str                           # initial | kernel | automaton | handoff
    segment: str
    sweep: int | None
    projection: GrainProjection
    amounts: MappingProxyType            # {(i, j): {species: mol}} -- the solid entry is float(inventory) for display


@dataclass(frozen=True)
class SolidLedger:
    segment: str
    kernel_solid_change_mol: Fraction    # exact, from the kernel's float states
    automaton_net_mol: Fraction          # sum over sweeps of (total after - total before): must be exactly 0
    grains_moved: int
    n_transfers: int
    handoff_rounding_mol: Fraction       # exact sum over cells of (float(n) - n) when handing back to the kernel
    max_cell_rounding_mol: Fraction


@dataclass(frozen=True)
class ParticleRun:
    spec: ReactiveGridSpec
    solid: str
    quantum: Fraction
    automaton_label: str
    dissolution_label: str
    kernel_runs: tuple
    frames: tuple
    transfers: tuple
    ledgers: tuple
    final: MappingProxyType


def _amounts_with(spec, base: dict, solid: str, proj: GrainProjection) -> MappingProxyType:
    out = {}
    for k, c in enumerate(proj.cells):
        row = dict(base[c])
        row[solid] = float(proj.inventory[k])
        out[c] = MappingProxyType(row)
    return MappingProxyType(out)


def solid_law_label(spec: ReactiveGridSpec, solid: str) -> str:
    """Validate every reaction touching ``solid`` as SYNTHETIC first-order dissolution (solid is the sole reactant,
    coefficient -1, kr == 0) and return the label that validation earns.  Anything that could create solid from
    solution is refused: there is no nucleation or precipitation law here to label it with."""
    touching = [r for r in spec.reactions if any(sp == solid for sp, _ in r.stoich)]
    for r in touching:
        if dict(r.stoich)[solid] > 0:
            raise ParticleError(f"reaction {r.name!r} PRODUCES the solid {solid!r}: no nucleation/precipitation law is "
                                f"modelled, so grains may not be created from solution")
        if r.kr != 0.0:
            raise ParticleError(f"reaction {r.name!r} has kr = {r.kr!r}: its reverse mass-action rate precipitates "
                                f"{solid!r} even where no solid exists (nucleation); dissolution requires kr == 0")
        if [(sp, c) for sp, c in r.stoich if c < 0] != [(solid, -1)]:
            raise ParticleError(f"reaction {r.name!r} is not first-order dissolution: {solid!r} must be its only "
                                f"reactant, with coefficient -1")
    return SYNTHETIC_FIRST_ORDER_DISSOLUTION if touching else NO_SOLID_REACTION


def _float_exactly(v, what: str) -> float:
    x = _exact(v)
    f = float(x)
    if Fraction(f) != x:
        raise ParticleError(f"initial amount {what} = {x} is not exactly representable as a float; the kernel would "
                            f"round it off the ledger (by {Fraction(f) - x} mol) -- pass the float you mean")
    return f


def run_coupled_particles(spec: ReactiveGridSpec, initial: dict, segments, *, solid: str, dt: float,
                          sweeps_per_segment: int, scheme: str = "strang", capacity: int | None = None, seed: int = 0,
                          quantum: Fraction = GRAIN_QUANTUM_MOL, rtol: float = 1e-10,
                          atol: float = 1e-14) -> ParticleRun:
    """Alternate [kernel segment] -> [sweeps_per_segment automaton sweeps] -> [exact-ledgered float handoff]."""
    sp = spec.species_named(solid)
    if sp.phase is not Phase.SOLID:
        raise ParticleError(f"{solid!r} is not a SOLID species")
    if type(sweeps_per_segment) is not int or sweeps_per_segment < 0:
        raise ParticleError("sweeps_per_segment must be an int >= 0")
    law_label = solid_law_label(spec, solid)
    segments = tuple(segments)
    if not segments or any(type(s) is not ValveSegment for s in segments):
        raise ParticleError("segments must be a non-empty sequence of ValveSegment")
    cells = spec.cells()
    names = [s.name for s in spec.species]
    state = {c: {nm: 0.0 for nm in names} for c in cells}
    for ij, inv in initial.items():
        for nm, v in inv.items():
            state[tuple(ij)][nm] = _float_exactly(v, f"{tuple(ij)}/{nm}")
    proj = GrainProjection.of(cells, [state[c][solid] for c in cells], quantum)
    frames = [ParticleFrame(0, 0.0, "initial", segments[0].name, None, proj, _amounts_with(spec, state, solid, proj))]
    transfers, ledgers, kernel_runs = [], [], []
    t0, sweep_no = 0.0, 0
    for seg in segments:
        run = run_reactive_grid(spec, {c: dict(state[c]) for c in cells}, (seg,), scheme=scheme, dt=dt, rtol=rtol,
                                atol=atol)
        kernel_runs.append(run)
        before = proj.total_inventory
        for f in run.frames[1:]:
            proj = GrainProjection.of(cells, [f.amounts[c][solid] for c in cells], quantum)
            base = {c: dict(f.amounts[c]) for c in cells}
            frames.append(ParticleFrame(len(frames), t0 + f.time_s, "kernel", seg.name, None, proj,
                                        _amounts_with(spec, base, solid, proj)))
        state = {c: dict(run.final[c]) for c in cells}
        kernel_change = proj.total_inventory - before
        auto = automaton_for(spec, seg.open_valves, capacity=capacity, seed=seed)
        net, moved, ntr = Fraction(0), 0, 0
        for _ in range(sweeps_per_segment):
            b = proj.total_inventory
            proj, tr = ca_sweep(proj, auto, sweep_no)
            net += proj.total_inventory - b
            moved += sum(t.n_grains for t in tr)
            ntr += len(tr)
            transfers.extend(tr)
            frames.append(ParticleFrame(len(frames), t0 + seg.duration_s, "automaton", seg.name, sweep_no, proj,
                                        _amounts_with(spec, state, solid, proj)))
            sweep_no += 1
        handed = [float(x) for x in proj.inventory]
        diffs = [Fraction(h) - x for h, x in zip(handed, proj.inventory)]
        proj = GrainProjection.of(cells, handed, quantum)
        for k, c in enumerate(cells):
            state[c][solid] = handed[k]
        frames.append(ParticleFrame(len(frames), t0 + seg.duration_s, "handoff", seg.name, None, proj,
                                    _amounts_with(spec, state, solid, proj)))
        ledgers.append(SolidLedger(seg.name, kernel_change, net, moved, ntr, sum(diffs, Fraction(0)),
                                   max((abs(d) for d in diffs), default=Fraction(0))))
        t0 += seg.duration_s
    final = MappingProxyType({c: MappingProxyType(dict(state[c])) for c in cells})
    return ParticleRun(spec, solid, quantum, ILLUSTRATIVE_GRANULAR_AUTOMATON, law_label,
                       tuple(kernel_runs), tuple(frames), tuple(transfers), tuple(ledgers), final)


def particle_frame_dict(run: ParticleRun, frame: ParticleFrame) -> dict:
    """Renderer-neutral, strict-JSON view of one particle frame (a fresh dict per call; writes cannot reach the run).
    Exact Fractions are serialised as 'p/q' strings next to their float display value."""
    p = frame.projection
    return {
        "schema": "xxv-particle-frame-v1", "frame_index": frame.index, "time_s": frame.time_s, "stage": frame.stage,
        "segment": frame.segment, "sweep": frame.sweep, "solid": run.solid,
        "automaton": run.automaton_label, "dissolution": run.dissolution_label,
        "quantities": {
            "solid_inventory_mol": {"quantity": "amount_of_substance", "unit": "mol", "kind": "CANONICAL",
                                    "exact": "Fraction p/q string"},
            "grains": {"quantity": "grain_count", "unit": "1", "kind": "MODEL_DERIVED",
                       "basis": f"floor(n / q), q = {p.quantum} mol"},
            "residual_mol": {"quantity": "amount_of_substance", "unit": "mol", "kind": "MODEL_DERIVED",
                             "basis": "n - grains * q"}},
        "grain_quantum_mol": str(p.quantum),
        "cells": [list(c) for c in p.cells],
        "solid_inventory_mol": [str(x) for x in p.inventory],
        "solid_inventory_mol_float": [float(x) for x in p.inventory],
        "grains": list(p.grains),
        "residual_mol": [str(x) for x in p.residual],
        "fields": {nm: [frame.amounts[c][nm] for c in p.cells] for nm in (s.name for s in run.spec.species)},
        "ledger_invariant_exact": p.invariant_holds(),
    }


def particle_frame_digest(run: ParticleRun, frame: ParticleFrame) -> str:
    return hashlib.sha256(json.dumps(particle_frame_dict(run, frame), sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()
