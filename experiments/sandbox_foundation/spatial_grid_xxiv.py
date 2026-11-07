"""OPERATION XXIV Phase V -- the first spatial crystal (3.0 RESEARCH ONLY): a finite-volume 2D grid on the general kernel.

WHAT THIS IS.  A bounded nx x ny grid (nx, ny <= 9) of well-mixed cells.  Every cell is a ``Compartment`` of the
general coupled world; every shared face between axis-adjacent cells is a pair of equal-and-opposite signed fluxes,
one ``InterfaceTransfer`` per transported species:

    F_{i->j,s} = k_f (c_{i,s} - c_{j,s}) = -F_{j->i,s}             (two-point finite-volume flux, k_f in L/s)

A WALL is a face that does not exist.  A VALVE is a face that exists only while open (the open set is a per-segment
schedule; each segment is a separate integration, continued from the previous one's final state).  One declared
SOURCE (a constant feed, mol/s) and one declared SINK (first-order outflow to a zero-concentration exterior) are the
only exchanges with the outside.  No reaction is declared: the grid transports NEUTRAL species only (a charged
species is refused -- single-ion bulk transport would separate charge, XXIII F3) and invents no chemistry.

THE CONSERVATION IDENTITY (proved, then measured).  For each species, stack the cell inventories into n.  Then

    dn/dt = L n + q + b(n),     L = sum over open faces f=(i,j) of (k_f / V) (e_j - e_i)(e_i - e_j)^T
    1^T L = 0  as an identity, because each face adds -k_f/V and +k_f/V to the SAME column i (and likewise for j):
    every face's contribution cancels EXACTLY in floating point (x - x = 0); a column summed over several faces is
    zero only up to floating-point summation roundoff (~1e-17 for k_f/V = 0.05), which the tests bound explicitly,

so d(1^T n)/dt = 1^T q + 1^T b(n): the grid total changes ONLY through the declared boundary terms.  Integrated:
total(t) - total(0) = integral(q + b) dt -- exactly the external ledger the coupled receipt verifies at every
accepted step.  ``reference_operator`` builds L, q and the sink row INDEPENDENTLY of the coupled world (from the face
list, with numpy), and ``reference_solution`` integrates the affine system exactly with a matrix exponential: an
independently derived reference discretization of the same semi-discrete law (the time discretisation of the
coupled path -- operator-split, per-step stiff solves -- is the thing being checked against it).

WHAT IT IS NOT.  Not a PDE solver with a convergence proof in dx (a face conductance k_f is a declared ASSUMED
coefficient, not D A / dx of a measured diffusivity); not a falling-sand engine; not chemistry.  The frames are a
PROJECTION of the computed state: they are derived only from it, are immutable, and nothing a renderer does to a
frame can reach the state (frames are rebuilt from private copies).
"""
from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
from scipy.linalg import expm

from experiments.sandbox_foundation.general_coupled import (Compartment, CoupledWorld, ExternalBoundary,
                                                            InterfaceTransfer)
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, KernelError, Species

MAX_SIDE = 9


class GridError(KernelError):
    """Fail-closed error for the spatial grid prototype."""


def cell_name(ij) -> str:
    return f"c{ij[0]}_{ij[1]}"


def _face(a, b) -> tuple:
    a, b = tuple(a), tuple(b)
    return (a, b) if a < b else (b, a)                      # orientation: lexicographic tail -> head (a free choice)


@dataclass(frozen=True)
class GridSpec:
    nx: int
    ny: int
    species: tuple                                          # (Species, ...) -- NEUTRAL only
    cell_volume_L: float = 1.0
    k_face_Lps: float = 0.05                                # ASSUMED face conductance (synthetic)
    walls: frozenset = frozenset()                          # {((i, j), (i2, j2)), ...} faces that do not exist
    valves: tuple = ()                                      # ((name, (i, j), (i2, j2)), ...) faces open only on schedule
    source: tuple | None = None                             # ((i, j), species_name, rate mol/s)
    sink: tuple | None = None                               # ((i, j), species_name, k L/s) outflow to c_ext = 0

    def __post_init__(self):
        for nm in ("nx", "ny"):
            v = getattr(self, nm)
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= MAX_SIDE:
                raise GridError(f"{nm} must be an int in 1..{MAX_SIDE} (a bounded prototype)")
        if not self.species or any(type(s) is not Species for s in self.species):
            raise GridError("species must be a non-empty tuple of kernel Species")
        if any(s.charge != 0 for s in self.species):
            raise GridError("only NEUTRAL species are transported (single-ion bulk transport separates charge)")
        if len({s.name for s in self.species}) != len(self.species):
            raise GridError("species names must be unique")
        for nm in ("cell_volume_L", "k_face_Lps"):
            v = getattr(self, nm)
            if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
                raise GridError(f"{nm} must be finite and > 0")
        object.__setattr__(self, "walls", frozenset(_face(a, b) for a, b in self.walls))
        valid = set(self.all_faces())
        for f in self.walls:
            if f not in valid:
                raise GridError(f"wall {f} is not a face between axis-adjacent cells of the grid")
        names = set()
        for name, a, b in self.valves:
            f = _face(a, b)
            if f not in valid or f in self.walls:
                raise GridError(f"valve {name!r} {f} must be an existing, non-wall face")
            if name in names:
                raise GridError(f"duplicate valve name {name!r}")
            names.add(name)
        for tag, b in (("source", self.source), ("sink", self.sink)):
            if b is None:
                continue
            (ij, sp, val) = b
            if not (0 <= ij[0] < self.nx and 0 <= ij[1] < self.ny):
                raise GridError(f"{tag} cell {ij} is outside the grid")
            if sp not in {s.name for s in self.species}:
                raise GridError(f"{tag} species {sp!r} is not declared")
            if not (isinstance(val, (int, float)) and math.isfinite(val)) or (tag == "sink" and val <= 0):
                raise GridError(f"{tag} value must be finite (and > 0 for a sink conductance)")

    def cells(self) -> list:
        return [(i, j) for j in range(self.ny) for i in range(self.nx)]

    def all_faces(self) -> list:
        out = []
        for i, j in self.cells():
            if i + 1 < self.nx:
                out.append(((i, j), (i + 1, j)))
            if j + 1 < self.ny:
                out.append(((i, j), (i, j + 1)))
        return out

    def valve_faces(self) -> dict:
        return {name: _face(a, b) for name, a, b in self.valves}

    def open_faces(self, open_valves: frozenset) -> list:
        unknown = set(open_valves) - set(self.valve_faces())
        if unknown:
            raise GridError(f"unknown valve(s) {sorted(unknown)}")
        closed = {f for nm, f in self.valve_faces().items() if nm not in open_valves}
        return [f for f in self.all_faces() if f not in self.walls and f not in closed]


def build_world(spec: GridSpec, open_valves: frozenset = frozenset()) -> CoupledWorld:
    by_name = {s.name: s for s in spec.species}
    comps = [Compartment(cell_name(c), ChemicalSystem(list(spec.species), [], volume_L=spec.cell_volume_L))
             for c in spec.cells()]
    ifaces = [InterfaceTransfer(f"{cell_name(a)}->{cell_name(b)}:{s.name}", cell_name(a), cell_name(b), s, s,
                                k_transfer=spec.k_face_Lps)
              for a, b in spec.open_faces(frozenset(open_valves)) for s in spec.species]
    bounds = []
    if spec.source is not None:
        ij, sp, rate = spec.source
        bounds.append(ExternalBoundary("source", cell_name(ij), by_name[sp], "feed", rate=float(rate)))
    if spec.sink is not None:
        ij, sp, k = spec.sink
        bounds.append(ExternalBoundary("sink", cell_name(ij), by_name[sp], "fixed_activity", k_transfer=float(k),
                                       target_conc=0.0))
    return CoupledWorld(comps, ifaces, bounds)


@dataclass(frozen=True)
class Segment:
    name: str
    duration_s: float
    n_steps: int
    open_valves: frozenset = frozenset()


@dataclass(frozen=True)
class GridFrame:
    """One immutable observation: amounts[(i, j)][species] (mol), derived ONLY from the integrated state."""
    index: int
    time_s: float
    segment: str
    open_valves: tuple
    amounts: MappingProxyType
    total_mol: MappingProxyType                             # grid total per species (the conserved observable)


@dataclass(frozen=True)
class GridRun:
    spec: GridSpec
    segments: tuple
    frames: tuple
    receipts: tuple                                         # one CoupledReceipt per segment
    final: MappingProxyType                                 # {(i, j): {species: mol}}
    ledger: tuple = field(default_factory=tuple)            # per segment: {species: (total change, external flux)}


def _state_from(spec, initial: dict) -> dict:
    by_name = {s.name: s for s in spec.species}
    state = {cell_name(c): {} for c in spec.cells()}
    for ij, inv in initial.items():
        if tuple(ij) not in set(spec.cells()):
            raise GridError(f"initial inventory for {ij} is outside the grid")
        for nm, v in inv.items():
            if nm not in by_name:
                raise GridError(f"initial inventory names undeclared species {nm!r}")
            if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise GridError(f"initial amount for {ij}/{nm} must be finite and >= 0")
            state[cell_name(ij)][by_name[nm]] = float(v)
    return state


def run_grid(spec: GridSpec, initial: dict, segments, *, rtol: float = 1e-10, atol: float = 1e-14,
             n_samples: int | None = None) -> GridRun:
    """Integrate the valve schedule through the ONE generic coupled integrator.  A segment whose receipt does not
    hold positivity or close its material ledger is REFUSED (raised), never clipped and continued."""
    segments = tuple(segments)
    if not segments or any(type(s) is not Segment for s in segments):
        raise GridError("segments must be a non-empty sequence of Segment")
    state = _state_from(spec, initial)
    frames, receipts, ledger = [], [], []
    t0 = 0.0
    for seg in segments:
        world = build_world(spec, frozenset(seg.open_valves))
        traj = world.integrate(state, duration=float(seg.duration_s), n_steps=int(seg.n_steps), rtol=rtol,
                               atol=atol, n_samples=n_samples)
        rc = traj.receipt
        if not (rc.positivity_held and rc.material_balance_closed):
            raise GridError(f"segment {seg.name!r} refused: positivity {rc.positivity_verdict} (raw minima "
                            f"{dict(rc.negative_minima)}), material balance closed={rc.material_balance_closed}")
        for j, t in enumerate(traj.times):
            amounts = {c: MappingProxyType({s.name: float(traj.amounts[cell_name(c)][j][s]) for s in spec.species})
                       for c in spec.cells()}
            tot = {s.name: math.fsum(amounts[c][s.name] for c in spec.cells()) for s in spec.species}
            frames.append(GridFrame(len(frames), t0 + float(t), seg.name, tuple(sorted(seg.open_valves)),
                                    MappingProxyType(amounts), MappingProxyType(tot)))
        receipts.append(rc)
        ledger.append(MappingProxyType({lab: (float(rc.raw_material_change[lab]), float(rc.external_flux[lab]))
                                        for lab in rc.raw_material_change}))
        state = {cn: dict(traj.amounts[cn][-1]) for cn in traj.compartments}
        t0 += float(seg.duration_s)
    final = MappingProxyType({c: MappingProxyType({s.name: float(state[cell_name(c)][s]) for s in spec.species})
                              for c in spec.cells()})
    return GridRun(spec, segments, tuple(frames), tuple(receipts), final, tuple(ledger))


# ============================================================ the independent reference discretization
def reference_operator(spec: GridSpec, open_valves: frozenset, species_name: str):
    """(L, q, cells) for ONE species: dn/dt = L n + q, built from the face list with numpy -- no CoupledWorld."""
    cells = spec.cells()
    idx = {c: k for k, c in enumerate(cells)}
    n = len(cells)
    L = np.zeros((n, n))
    g = spec.k_face_Lps / spec.cell_volume_L
    for a, b in spec.open_faces(frozenset(open_valves)):
        ia, ib = idx[a], idx[b]
        L[ia, ia] -= g                                      # J_ab = k (n_a - n_b) / V leaves a ...
        L[ib, ia] += g                                      # ... and enters b (same column: this face's pair cancels exactly)
        L[ib, ib] -= g
        L[ia, ib] += g
    q = np.zeros(n)
    if spec.source is not None and spec.source[1] == species_name:
        q[idx[tuple(spec.source[0])]] += float(spec.source[2])
    if spec.sink is not None and spec.sink[1] == species_name:
        L[idx[tuple(spec.sink[0])], idx[tuple(spec.sink[0])]] -= float(spec.sink[2]) / spec.cell_volume_L
    return L, q, cells


def reference_solution(spec: GridSpec, initial: dict, segments) -> dict:
    """Exact affine propagation exp([[L, q], [0, 0]] t) segment by segment, per species."""
    out = {}
    for s in spec.species:
        cells = spec.cells()
        n = np.array([float(initial.get(c, {}).get(s.name, 0.0)) for c in cells])
        for seg in segments:
            L, q, _ = reference_operator(spec, frozenset(seg.open_valves), s.name)
            m = len(cells)
            A = np.zeros((m + 1, m + 1))
            A[:m, :m], A[:m, m] = L, q
            n = (expm(A * float(seg.duration_s)) @ np.append(n, 1.0))[:m]
        out[s.name] = {c: float(n[k]) for k, c in enumerate(cells)}
    return out


def face_flux(spec: GridSpec, amounts: dict, species_name: str, tail, head) -> float:
    """F_{tail->head} = k (c_tail - c_head) from the TAIL's perspective (call with tail/head swapped for the other)."""
    V = spec.cell_volume_L
    return spec.k_face_Lps * (amounts[tuple(tail)][species_name] / V - amounts[tuple(head)][species_name] / V)


# ============================================================ projection (frames -> renderer-neutral contract)
def to_snapshot(run: GridRun, frame: GridFrame):
    """A PhysicalWorldSnapshot (the existing LibGibson-facing contract) built from a PRIVATE copy of one frame."""
    from experiments.sandbox_foundation.snapshot import PhysicalWorldSnapshot
    spec = run.spec
    cells = spec.cells()
    amt = np.array([[frame.amounts[c][s.name] for s in spec.species] for c in cells])
    open_faces = spec.open_faces(frozenset(frame.open_valves))
    idx = {c: k for k, c in enumerate(cells)}
    seg_k = [s.name for s in run.segments].index(frame.segment)
    rc = run.receipts[seg_k]
    valve_of = {f: nm for nm, f in spec.valve_faces().items()}
    material = tuple(f"valve:{valve_of[f]}:open" if f in valve_of else "open face" for f in open_faces)
    snap = PhysicalWorldSnapshot(
        tuple(s.name for s in spec.species), [spec.cell_volume_L * 1e-3] * len(cells), amt,
        np.ones_like(amt, dtype=bool), units={"amount": "mol", "volume": "m^3", "time": "s",
                                              "concentration": "mol/m^3"},
        model_tick=frame.index, physical_time_s=frame.time_s,
        conservation_diagnostics={"grid_total_mol": dict(frame.total_mol),
                                  "segment_material_balance_closed": bool(rc.material_balance_closed),
                                  "segment_positivity_verdict": rc.positivity_verdict,
                                  "segment_structural_tier": rc.structural_tier},
        numerical_uncertainty={"note": "per-component ledger tolerance 1e-12 + 1e-6 x scale (coupled receipt)"},
        boundary_material=material,
        evidence={"provenance": "SYNTHETIC grid; face conductance ASSUMED; no chemistry declared",
                  "claim": "computed projection only -- not a measurement, not a validated physical prediction"},
        display_hints={"layout": "grid2d", "nx": spec.nx, "ny": spec.ny, "cell_ij": [list(c) for c in cells],
                       "walls": sorted([list(a), list(b)] for a, b in spec.walls),
                       "closed_valves": sorted(nm for nm in spec.valve_faces() if nm not in frame.open_valves)})
    interfaces = tuple((idx[a], idx[b]) for a, b in open_faces)
    return snap, interfaces


def render_html(run: GridRun, species_name: str, title: str = "XXIV spatial crystal") -> str:
    """A deterministic, self-contained HTML/SVG view of one species' field over the frames.  Pure projection: it
    reads frame values and receipt verdicts only, and labels itself computational."""
    spec = run.spec
    data = [[round(f.amounts[c][species_name], 12) for c in spec.cells()] for f in run.frames]
    vmax = max(max(row) for row in data) or 1.0
    meta = [{"t": round(f.time_s, 6), "seg": f.segment, "valves": list(f.open_valves),
             "total": round(f.total_mol[species_name], 12)} for f in run.frames]
    verdicts = [{"positivity": r.positivity_verdict, "balance_closed": bool(r.material_balance_closed),
                 "tier": r.structural_tier} for r in run.receipts]
    walls = [[list(a), list(b)] for a, b in sorted(spec.walls)]
    valves = {nm: [list(a), list(b)] for nm, (a, b) in spec.valve_faces().items()}
    payload = json.dumps({"nx": spec.nx, "ny": spec.ny, "cells": [list(c) for c in spec.cells()], "data": data,
                          "vmax": vmax, "meta": meta, "verdicts": verdicts, "walls": walls, "valves": valves,
                          "segments": [s.name for s in run.segments]}, sort_keys=True)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font:14px system-ui;background:#111;color:#ddd;margin:16px}}svg{{background:#000}}
.cap{{max-width:640px;color:#aaa}}</style></head><body><h1>{html.escape(title)}</h1>
<p class="cap">Species <b>{html.escape(species_name)}</b>. Computed by the SmartChem coupled kernel (research only).
Cell colour = amount (mol); thick lines = walls; dashed = valves (red closed, green open). A projection of the
integrated state -- not a measurement, not a validated prediction.</p>
<svg id="g" width="{60 * spec.nx}" height="{60 * spec.ny}"></svg><br>
<input id="s" type="range" min="0" max="{len(data) - 1}" value="0" style="width:{60 * spec.nx}px">
<pre id="m"></pre><script>
const D={payload};const g=document.getElementById('g');const m=document.getElementById('m');
function draw(k){{let s='';D.cells.forEach((c,i)=>{{const v=D.data[k][i]/D.vmax;
s+=`<rect x="${{c[0]*60}}" y="${{c[1]*60}}" width="60" height="60" fill="rgb(${{Math.round(255*v)}},${{Math.round(90*v)}},${{Math.round(255*(1-v)*0.4)}})"/>`;}});
const line=(a,b,st)=>{{const x=a[0]==b[0]?a[0]*60:Math.max(a[0],b[0])*60, y=a[1]==b[1]?a[1]*60:Math.max(a[1],b[1])*60;
return a[0]==b[0]?`<line x1="${{x}}" y1="${{y}}" x2="${{x+60}}" y2="${{y}}" ${{st}}/>`:`<line x1="${{x}}" y1="${{y}}" x2="${{x}}" y2="${{y+60}}" ${{st}}/>`;}};
D.walls.forEach(w=>s+=line(w[0],w[1],'stroke="#fff" stroke-width="5"'));const mt=D.meta[k];
Object.entries(D.valves).forEach(([n,f])=>s+=line(f[0],f[1],`stroke="${{mt.valves.includes(n)?'#3c3':'#e33'}}" stroke-width="5" stroke-dasharray="6 4"`));
g.innerHTML=s;const vd=D.verdicts[D.segments.indexOf(mt.seg)];
m.textContent=`t=${{mt.t}} s  segment=${{mt.seg}}  open valves=${{mt.valves.join(',')||'none'}}\\ngrid total=${{mt.total}} mol  positivity=${{vd.positivity}}  balance closed=${{vd.balance_closed}}  tier=${{vd.tier}}`;}}
document.getElementById('s').oninput=e=>draw(+e.target.value);draw(0);</script></body></html>
"""
