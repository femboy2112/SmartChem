"""OPERATION XXV Phase IV -- the reactive spatial grid (3.0 RESEARCH ONLY): reaction + transport on the general kernel.

WHAT THIS IS.  XXIV's bounded finite-volume grid (``spatial_grid_xxiv``; reused for cell naming and face orientation,
left byte-stable) gains three things:

  1. REACTIONS.  Generic reversible mass action ``(name, ((species, coeff), ...), kf, kr, cells_or_None)`` executed
     by the kernel's AUDITED ``MassActionReversible`` inside each cell's ``ChemicalSystem`` (so E N = 0 is proven in
     exact integers at construction and an unbalanced reaction raises ``ConservationError``).  ``cells=None`` means
     every cell; a set localises the reaction.  Every reaction here is SYNTHETIC (caller-declared kf/kr): it carries
     the label and is refused if it tries to carry a source citation.
  2. PER-SPECIES, TYPED FACE CONDUCTANCE.  ``SyntheticConductance(k)`` is an assumed coefficient.
     ``DerivedConductance`` computes k = D A / dx from a stated diffusivity (with its tier, citation and temperature):
     the two-point finite-volume flux of Fick's law on a uniform mesh of square cells, V = A dx.  A species with k = 0
     gets no interface at all (a SOLID must have k = 0: it does not diffuse).
  3. AN INDEPENDENT REFERENCE for first-order networks: ``reference_solution_coupled`` assembles the full
     (n_species * n_cells + 1) augmented affine generator [[L (+) K, q], [0, 0]] from its OWN face enumeration
     (``reference_open_faces``, written independently of the spec's face list) and the stoichiometry and propagates it
     with ``scipy.linalg.expm``.  It never builds a CoupledWorld.

SPLITTING.  The engine runs the kernel's Lie / Strang / monolithic macro-steps.  With one conductance shared by all
species and the same reaction in every cell, transport (I_s (x) L) and reaction (K (x) I_c) commute and every
splitting is exact -- a splitting comparison on such a grid proves nothing.  ``splitting_commutator_norm`` measures
||[T_aug, R_aug]|| on the AUGMENTED affine generators (the source vector q rides with transport) so a test can
establish non-commutation before it claims an order.

TEMPERATURE AND DOMAIN.  ``T_K`` is explicit; a DerivedConductance whose diffusivity was stated at another temperature
is REFUSED (``GridSourceDomainError``, same 0.01 K match rule as ``admissibility``): no temperature law for D is
modelled.  ``model_domain`` states the declared regime (isothermal, ideal concentration basis, well-mixed cells,
neutral species).

WHAT IT IS NOT.  Not empirically validated: a spatial-convergence study measures the finite-volume discretisation of
the diffusion PDE with the stated D, not agreement with any measurement.  Reactions are synthetic.  The frames are a
read-only projection of the integrated state.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
from scipy.linalg import expm

from experiments.sandbox_foundation import admissibility as _adm
from experiments.sandbox_foundation.claim_tiers import (ASSUMED_PARAMETER, CALIBRATED_TO_MEASUREMENT, UNVERIFIED,
                                                        rank as _tier_rank)
from experiments.sandbox_foundation.general_coupled import (Compartment, CoupledWorld, ExternalBoundary,
                                                            InterfaceTransfer)
from experiments.sandbox_foundation.general_kernel import (ChemicalSystem, MassActionReversible, Phase, Reaction,
                                                           SourceDomainError, Species)
from experiments.sandbox_foundation.spatial_grid_xxiv import GridError, _face, cell_name

MAX_SIDE_2D = 9                  # a genuinely 2-D grid stays the XXIV bounded prototype
MAX_STRIP = 64                   # a 1-D strip (nx == 1 or ny == 1) may be longer, for mesh studies

SYNTHETIC = "SYNTHETIC"
CONDUCTANCE_SYNTHETIC = "SYNTHETIC"
CONDUCTANCE_DERIVED = "DERIVED_FROM_DIFFUSIVITY"
SYNTHETIC_RATE_SOURCE = "SYNTHETIC: caller-declared kf/kr; no source citation"
DEFAULT_MODEL_DOMAIN = ("isothermal; ideal concentration basis (activity == concentration); well-mixed cells; "
                        "neutral species only; no advection")
FRAME_SCHEMA = "xxv-reactive-grid-frame-v1"
# The claim tiers an INPUT diffusivity can honestly carry: assumed, or fitted to a measured dataset.  The other tiers
# describe a solve (STRUCTURALLY_CONSERVING .. BENCHMARKED) or a validated prediction (PREDICTIVE_WITHIN_...), or are
# the refusal floor (OUT_OF_DOMAIN / REFUSED) -- none is a property a bare caller-supplied D can have.
D_INPUT_TIERS = frozenset({ASSUMED_PARAMETER, UNVERIFIED, CALIBRATED_TO_MEASUREMENT})

QUANTITIES = MappingProxyType({
    "amount_mol": MappingProxyType({"quantity": "amount_of_substance", "unit": "mol", "kind": "CANONICAL",
                                    "location": "cell"}),
    "concentration_mol_per_L": MappingProxyType({"quantity": "amount_concentration", "unit": "mol/L",
                                                 "kind": "MODEL_DERIVED", "location": "cell"}),
    "face_flux_mol_per_s": MappingProxyType({"quantity": "molar_flow_rate", "unit": "mol/s", "kind": "MODEL_DERIVED",
                                             "location": "face",
                                             "basis": "instantaneous k_s (c_tail - c_head) at the frame state; "
                                                      "positive = tail -> head; not integrated over the step"}),
    "valve_open": MappingProxyType({"quantity": "face_state", "unit": "1", "kind": "CANONICAL", "location": "face"}),
    "time_s": MappingProxyType({"quantity": "time", "unit": "s", "kind": "CANONICAL", "location": "global"}),
})


class GridSourceDomainError(GridError, SourceDomainError):
    """A sourced constant (a stated diffusivity) would execute away from the temperature it was stated at."""


def _finite(x, what, *, positive=False, nonneg=False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise GridError(f"{what} must be a finite number")
    if positive and not x > 0:
        raise GridError(f"{what} must be > 0")
    if nonneg and not x >= 0:
        raise GridError(f"{what} must be >= 0")
    return float(x)


# ============================================================ typed conductance
@dataclass(frozen=True)
class SyntheticConductance:
    """An ASSUMED face conductance (L/s).  No physical derivation; every result reports it as SYNTHETIC."""
    k_Lps: float
    kind: str = field(default=CONDUCTANCE_SYNTHETIC, init=False)

    def __post_init__(self):
        _finite(self.k_Lps, "SyntheticConductance.k_Lps", nonneg=True)

    def describe(self) -> dict:
        return {"kind": self.kind, "k_Lps": float(self.k_Lps), "basis": "caller-declared coefficient"}


@dataclass(frozen=True)
class DerivedConductance:
    """k = D A / dx (m^3/s) x 1000 = L/s: the two-point flux of Fick's law between two cell centres dx apart through a
    face of area A.  D is the only sourced input; its tier, citation and temperature travel with it."""
    D_m2ps: float
    area_m2: float
    dx_m: float
    D_source_tier: str
    D_citation: str
    D_T_K: float
    kind: str = field(default=CONDUCTANCE_DERIVED, init=False)
    k_Lps: float = field(default=0.0, init=False)

    def __post_init__(self):
        _finite(self.D_m2ps, "D_m2ps", positive=True)
        _finite(self.area_m2, "area_m2", positive=True)
        _finite(self.dx_m, "dx_m", positive=True)
        _finite(self.D_T_K, "D_T_K", positive=True)
        _tier_rank(self.D_source_tier)                         # an unknown tier token raises
        if self.D_source_tier not in D_INPUT_TIERS:
            raise GridError(f"D_source_tier {self.D_source_tier!r} is not a tier an input diffusivity can carry; "
                            f"expected one of {sorted(D_INPUT_TIERS)}")
        if not isinstance(self.D_citation, str) or not self.D_citation.strip():
            raise GridError("DerivedConductance needs a non-empty D_citation (state where D came from)")
        object.__setattr__(self, "k_Lps", float(self.D_m2ps) * float(self.area_m2) / float(self.dx_m) * 1000.0)

    def describe(self) -> dict:
        return {"kind": self.kind, "k_Lps": float(self.k_Lps), "D_m2ps": float(self.D_m2ps),
                "area_m2": float(self.area_m2), "dx_m": float(self.dx_m), "D_source_tier": self.D_source_tier,
                "D_citation": self.D_citation, "D_T_K": float(self.D_T_K), "basis": "k = D*A/dx"}


_CONDUCTANCE_TYPES = (SyntheticConductance, DerivedConductance)


# ============================================================ reactions
@dataclass(frozen=True)
class GridReaction:
    """A SYNTHETIC reversible mass-action reaction on the grid.  ``stoich`` names species; ``cells`` None = all."""
    name: str
    stoich: tuple
    kf: float
    kr: float
    cells: frozenset | None = None
    provenance: str = field(default=SYNTHETIC, init=False)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise GridError("a reaction needs a non-empty name")
        if type(self.stoich) is not tuple or not self.stoich or not all(
                type(p) is tuple and len(p) == 2 and isinstance(p[0], str)
                and type(p[1]) is int and p[1] != 0 for p in self.stoich):
            raise GridError(f"reaction {self.name!r}: stoich must be ((species_name, nonzero int), ...)")
        _finite(self.kf, f"reaction {self.name!r} kf", nonneg=True)
        _finite(self.kr, f"reaction {self.name!r} kr", nonneg=True)
        if self.cells is not None:
            object.__setattr__(self, "cells", frozenset(tuple(c) for c in self.cells))

    @classmethod
    def coerce(cls, r) -> "GridReaction":
        if type(r) is cls:
            return r
        if type(r) is not tuple:
            raise GridError("a reaction is (name, ((species, coeff), ...), kf, kr, cells_or_None)")
        if len(r) != 5:
            raise GridError(f"reaction tuple must have exactly 5 fields; a SYNTHETIC reaction carries no source "
                            f"citation or extra provenance (got {len(r)})")
        name, stoich, kf, kr, cells = r
        return cls(name, tuple(tuple(p) for p in stoich), kf, kr, None if cells is None else frozenset(cells))

    def describe(self) -> dict:
        return {"name": self.name, "stoich": [[s, int(c)] for s, c in self.stoich], "kf": float(self.kf),
                "kr": float(self.kr), "cells": None if self.cells is None else sorted([list(c) for c in self.cells]),
                "provenance": self.provenance, "rate_law": "MassActionReversible (concentration basis)"}


# ============================================================ the spec
@dataclass(frozen=True)
class ReactiveGridSpec:
    nx: int
    ny: int
    species: tuple                       # (Species, ...) -- NEUTRAL only
    conductance: tuple                   # ((species_name, SyntheticConductance | DerivedConductance), ...) every species
    T_K: float = 298.15
    model_domain: str = DEFAULT_MODEL_DOMAIN
    cell_volume_L: float = 1.0
    walls: frozenset = frozenset()
    valves: tuple = ()                   # ((name, (i, j), (i2, j2)), ...)
    sources: tuple = ()                  # (((i, j), species_name, rate mol/s), ...)
    sinks: tuple = ()                    # (((i, j), species_name, k L/s), ...) outflow to c_ext = 0
    reactions: tuple = ()                # (GridReaction | 5-tuple, ...)

    def __post_init__(self):
        for nm in ("nx", "ny"):
            v = getattr(self, nm)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise GridError(f"{nm} must be a positive int")
        if self.nx > 1 and self.ny > 1:
            if self.nx > MAX_SIDE_2D or self.ny > MAX_SIDE_2D:
                raise GridError(f"a 2-D grid is capped at {MAX_SIDE_2D}x{MAX_SIDE_2D}")
        elif max(self.nx, self.ny) > MAX_STRIP:
            raise GridError(f"a 1-D strip is capped at {MAX_STRIP} cells")
        if type(self.species) is not tuple or not self.species or any(type(s) is not Species for s in self.species):
            raise GridError("species must be a non-empty tuple of kernel Species")
        if any(s.charge != 0 for s in self.species):
            raise GridError("only NEUTRAL species are transported (single-ion bulk transport separates charge)")
        names = [s.name for s in self.species]
        if len(set(names)) != len(names):
            raise GridError("species names must be unique")
        _finite(self.T_K, "T_K", positive=True)
        if not isinstance(self.model_domain, str) or not self.model_domain.strip():
            raise GridError("model_domain must state the declared modelling regime")
        _finite(self.cell_volume_L, "cell_volume_L", positive=True)

        cond = tuple(tuple(p) for p in self.conductance)
        if sorted(n for n, _ in cond) != sorted(names) or len(cond) != len(names):
            raise GridError("conductance must assign exactly one conductance to every species")
        by_name = {s.name: s for s in self.species}
        for nm, c in cond:
            if type(c) not in _CONDUCTANCE_TYPES:
                raise GridError(f"conductance for {nm!r} must be SyntheticConductance or DerivedConductance")
            if by_name[nm].phase is Phase.SOLID and c.k_Lps != 0.0:
                raise GridError(f"species {nm!r} is a SOLID: its face conductance must be 0 (a solid does not diffuse)")
            if type(c) is DerivedConductance:
                if abs(c.D_T_K - float(self.T_K)) > _adm.TEMPERATURE_MATCH_TOL_K:
                    raise GridSourceDomainError(
                        f"diffusivity for {nm!r} was stated at {c.D_T_K:.2f} K but the grid runs at {self.T_K:.2f} K; "
                        f"no temperature law for D is modelled, so it is refused rather than extrapolated")
                v_geom = c.area_m2 * c.dx_m * 1000.0
                if abs(v_geom - self.cell_volume_L) > 1e-9 * self.cell_volume_L:
                    raise GridError(f"DerivedConductance geometry for {nm!r} implies a cell volume A*dx = {v_geom!r} L "
                                    f"but cell_volume_L = {self.cell_volume_L!r}: k = D A / dx is the FV flux only on "
                                    f"square cells with V = A dx")
        derived = [(nm, c) for nm, c in cond if type(c) is DerivedConductance]
        for nm, c in derived[1:]:
            ref_nm, ref = derived[0]
            if (abs(c.dx_m - ref.dx_m) > 1e-9 * ref.dx_m or abs(c.area_m2 - ref.area_m2) > 1e-9 * ref.area_m2):
                raise GridError(f"DerivedConductance geometry for {nm!r} (A={c.area_m2!r} m^2, dx={c.dx_m!r} m) differs "
                                f"from {ref_nm!r} (A={ref.area_m2!r} m^2, dx={ref.dx_m!r} m): one grid has one mesh, so "
                                f"every derived conductance must share its face area and cell spacing")
        object.__setattr__(self, "conductance", cond)

        # Freeze every caller container: a finished run's identity must not move when the caller's list does.
        try:
            valves = tuple((name, tuple(a), tuple(b)) for name, a, b in self.valves)
            sources = tuple((tuple(ij), sp, val) for ij, sp, val in self.sources)
            sinks = tuple((tuple(ij), sp, val) for ij, sp, val in self.sinks)
        except (TypeError, ValueError):
            raise GridError("valves are (name, (i, j), (i2, j2)); sources/sinks are ((i, j), species, value)") from None
        object.__setattr__(self, "valves", valves)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "sinks", sinks)

        object.__setattr__(self, "walls", frozenset(_face(a, b) for a, b in self.walls))
        valid = set(self.all_faces())
        for f in self.walls:
            if f not in valid:
                raise GridError(f"wall {f} is not a face between axis-adjacent cells of the grid")
        seen, valved = set(), {}
        for name, a, b in self.valves:
            f = _face(a, b)
            if f not in valid or f in self.walls:
                raise GridError(f"valve {name!r} {f} must be an existing, non-wall face")
            if name in seen:
                raise GridError(f"duplicate valve name {name!r}")
            if f in valved:
                raise GridError(f"valves {valved[f]!r} and {name!r} share face {f}: one face carries at most one valve")
            seen.add(name)
            valved[f] = name
        cells = set(self.cells())
        for tag, items in (("source", self.sources), ("sink", self.sinks)):
            for ij, sp, val in items:
                if tuple(ij) not in cells:
                    raise GridError(f"{tag} cell {ij} is outside the grid")
                if sp not in by_name:
                    raise GridError(f"{tag} species {sp!r} is not declared")
                if by_name[sp].phase is Phase.SOLID:
                    raise GridError(f"{tag} species {sp!r} is a SOLID: a solid neither diffuses nor crosses a "
                                    f"boundary, so it cannot be fed or drained")
                # A source is a FEED (rate >= 0).  A drain must be a declared first-order sink: a constant negative
                # feed keeps removing material after the inventory is gone, which no physical boundary does.
                _finite(val, f"{tag} value", positive=(tag == "sink"), nonneg=(tag == "source"))

        rx = tuple(GridReaction.coerce(r) for r in self.reactions)
        if len({r.name for r in rx}) != len(rx):
            raise GridError("reaction names must be unique")
        for r in rx:
            for sp, _ in r.stoich:
                if sp not in by_name:
                    raise GridError(f"reaction {r.name!r} names species {sp!r} that is not in spec.species")
            if len({sp for sp, _ in r.stoich}) != len(r.stoich):
                raise GridError(f"reaction {r.name!r} lists a species twice")
            if r.cells is not None:
                if not r.cells or not r.cells <= cells:
                    raise GridError(f"reaction {r.name!r} cells must be a non-empty subset of the grid")
        object.__setattr__(self, "reactions", rx)
        # E N = 0 proven in exact integers by the kernel (ConservationError on an unbalanced reaction).
        ChemicalSystem(list(self.species), list(self._kernel_reactions().values()), volume_L=self.cell_volume_L)

    # ---------------------------------------------------------------- geometry
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

    def open_faces(self, open_valves) -> list:
        open_valves = frozenset(open_valves)
        unknown = open_valves - set(self.valve_faces())
        if unknown:
            raise GridError(f"unknown valve(s) {sorted(unknown)}")
        closed = {f for nm, f in self.valve_faces().items() if nm not in open_valves}
        return [f for f in self.all_faces() if f not in self.walls and f not in closed]

    # ---------------------------------------------------------------- lookups
    def species_named(self, name: str) -> Species:
        for s in self.species:
            if s.name == name:
                return s
        raise GridError(f"unknown species {name!r}")

    def conductance_of(self, name: str):
        for nm, c in self.conductance:
            if nm == name:
                return c
        raise GridError(f"no conductance for {name!r}")

    def _kernel_reactions(self) -> dict:
        by_name = {s.name: s for s in self.species}
        return {r.name: Reaction(r.name, tuple((by_name[s], c) for s, c in r.stoich),
                                 MassActionReversible(float(r.kf), float(r.kr), source=SYNTHETIC_RATE_SOURCE))
                for r in self.reactions}

    def describe(self) -> dict:
        """A canonical, JSON-safe description: the model identity's spec part."""
        return {
            "nx": self.nx, "ny": self.ny, "T_K": float(self.T_K), "model_domain": self.model_domain,
            "cell_volume_L": float(self.cell_volume_L),
            "species": [[s.name, [list(p) for p in s.composition], s.charge, s.phase.value, s.substance]
                        for s in self.species],
            "conductance": {nm: c.describe() for nm, c in self.conductance},
            "walls": sorted([list(a), list(b)] for a, b in self.walls),
            "valves": sorted([nm, list(a), list(b)] for nm, (a, b) in self.valve_faces().items()),
            "sources": [[list(ij), sp, float(v)] for ij, sp, v in self.sources],
            "sinks": [[list(ij), sp, float(v)] for ij, sp, v in self.sinks],
            "reactions": [r.describe() for r in self.reactions],
        }


def build_reactive_world(spec: ReactiveGridSpec, open_valves=frozenset()) -> CoupledWorld:
    """One CoupledWorld per valve configuration: a Compartment per cell (with the reactions localised to it), one
    InterfaceTransfer per open face per species with k > 0, and the declared boundary terms."""
    kr = spec._kernel_reactions()
    comps = []
    for c in spec.cells():
        here = [kr[r.name] for r in spec.reactions if r.cells is None or c in r.cells]
        comps.append(Compartment(cell_name(c), ChemicalSystem(list(spec.species), here, volume_L=spec.cell_volume_L)))
    ifaces = []
    for a, b in spec.open_faces(open_valves):
        for s in spec.species:
            k = float(spec.conductance_of(s.name).k_Lps)
            if k > 0.0:
                ifaces.append(InterfaceTransfer(f"{cell_name(a)}->{cell_name(b)}:{s.name}", cell_name(a), cell_name(b),
                                                s, s, k_transfer=k))
    bounds = []
    for k, (ij, sp, rate) in enumerate(spec.sources):
        bounds.append(ExternalBoundary(f"source{k}", cell_name(ij), spec.species_named(sp), "feed", rate=float(rate)))
    for k, (ij, sp, kk) in enumerate(spec.sinks):
        bounds.append(ExternalBoundary(f"sink{k}", cell_name(ij), spec.species_named(sp), "fixed_activity",
                                       k_transfer=float(kk), target_conc=0.0))
    return CoupledWorld(comps, ifaces, bounds, temperature_K=float(spec.T_K))


# ============================================================ the run
@dataclass(frozen=True)
class ValveSegment:
    name: str
    duration_s: float
    open_valves: frozenset = frozenset()

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise GridError("a segment needs a non-empty name")
        _finite(self.duration_s, "segment duration", positive=True)
        object.__setattr__(self, "open_valves", frozenset(self.open_valves))


@dataclass(frozen=True)
class ReactiveFrame:
    """One immutable observation at global step ``step`` (time = step * dt), derived only from the integrated state."""
    index: int
    step: int
    time_s: float
    segment: str
    open_valves: tuple
    amounts: MappingProxyType            # {(i, j): {species: mol}}
    total_mol: MappingProxyType          # {species: grid total}


@dataclass(frozen=True)
class SegmentLedger:
    segment: str
    n_steps: int
    material: MappingProxyType           # {component: (measured change, integrated external flux)}
    component_tolerance: MappingProxyType
    component_max_residual: MappingProxyType   # per-step max |E n(t) - E n0 - E integral q dt|
    component_resolution: MappingProxyType
    positivity_verdict: str
    negative_minima: MappingProxyType
    execution_identity_basis: str
    structural_tier: str


@dataclass(frozen=True)
class ReactiveRun:
    spec: ReactiveGridSpec
    scheme: str
    dt: float
    rtol: float
    atol: float
    segments: tuple
    frames: tuple
    ledgers: tuple
    final: MappingProxyType              # {(i, j): {species: mol}}
    step_count: int
    initial_digest: str                  # identity of the state the FIRST run of this chain started from
    segment_start_digests: tuple = ()    # exact digest of the state each segment was integrated FROM (one per segment)

    @property
    def conductance_report(self) -> dict:
        return {nm: c.describe() for nm, c in self.spec.conductance}

    @property
    def reaction_report(self) -> list:
        return [r.describe() for r in self.spec.reactions]


def _canon(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _initial_state(spec: ReactiveGridSpec, initial: dict) -> dict:
    by_name = {s.name: s for s in spec.species}
    cells = set(spec.cells())
    state = {cell_name(c): {s: 0.0 for s in spec.species} for c in spec.cells()}
    for ij, inv in initial.items():
        if tuple(ij) not in cells:
            raise GridError(f"initial inventory for {ij} is outside the grid")
        for nm, v in inv.items():
            if nm not in by_name:
                raise GridError(f"initial inventory names undeclared species {nm!r}")
            state[cell_name(tuple(ij))][by_name[nm]] = _finite(v, f"initial amount {ij}/{nm}", nonneg=True)
    return state


def _state_digest(spec, state) -> str:
    return _canon([[cell_name(c), [[s.name, float(state[cell_name(c)][s]).hex()] for s in spec.species]]
                   for c in spec.cells()])


def _amounts(spec, state) -> MappingProxyType:
    return MappingProxyType({c: MappingProxyType({s.name: float(state[cell_name(c)][s]) for s in spec.species})
                             for c in spec.cells()})


def _make_frame(spec, index, step, dt, seg, state) -> ReactiveFrame:
    amounts = _amounts(spec, state)
    tot = {s.name: math.fsum(amounts[c][s.name] for c in spec.cells()) for s in spec.species}
    return ReactiveFrame(index, step, step * dt, seg.name, tuple(sorted(seg.open_valves)), amounts,
                         MappingProxyType(tot))


def _component_coeff(spec, label: str) -> dict:
    """{species: coefficient} of one conserved component row (an element of the composition, or 'charge')."""
    if label == "charge":
        return {s.name: float(s.charge) for s in spec.species}
    if not any(el == label for s in spec.species for el, _ in s.composition):
        raise GridError(f"start ledger names component {label!r} that no species of the spec carries")
    return {s.name: float(dict(s.composition).get(label, 0)) for s in spec.species}


def _component_total(spec, amounts, coeff: dict) -> float:
    return math.fsum(coeff[s.name] * float(amounts[c][s.name]) for c in spec.cells() for s in spec.species)


def _verify_start(spec: ReactiveGridSpec, start: "ReactiveRun", dt: float) -> None:
    """Re-derive what a continuation would otherwise trust.  ``start.final`` must be EXACTLY its last frame, the
    frame chain must be one frame per global step, and every recorded segment ledger must close on the frames it
    covers: |E n(end) - E n(begin) - integrated external flux| <= that ledger's own component tolerance.  A hand-off
    state edited between segments (or a frame edited without its ledger) is refused."""
    if type(start.segments) is not tuple or type(start.frames) is not tuple or type(start.ledgers) is not tuple:
        raise GridError("start is not a well-formed ReactiveRun")
    if len(start.ledgers) != len(start.segments) or len(start.segment_start_digests) != len(start.segments):
        raise GridError("start must carry one ledger and one start-state digest per segment")
    if len(start.frames) != start.step_count + 1 or any(f.index != k or f.step != k for k, f in enumerate(start.frames)):
        raise GridError("start frames are not one frame per global step")
    cells, names = spec.cells(), [s.name for s in spec.species]

    def exact(amounts):
        if set(amounts) != set(cells) or any(set(amounts[c]) != set(names) for c in cells):
            raise GridError("start state does not cover exactly the spec's cells and species")
        return [[float(amounts[c][nm]).hex() for nm in names] for c in cells]
    if exact(start.final) != exact(start.frames[-1].amounts):
        raise GridError("start.final is not the state of start's last frame: the continuation hand-off was edited")

    def digest(amounts):
        return _state_digest(spec, {cell_name(c): {s: float(amounts[c][s.name]) for s in spec.species} for c in cells})
    if digest(start.frames[0].amounts) != start.initial_digest:
        raise GridError("start's first frame is not the state its initial_digest records")
    s0 = 0
    for k, (seg, led) in enumerate(zip(start.segments, start.ledgers)):
        n = _segment_steps(seg, dt)
        if led.segment != seg.name or led.n_steps != n:
            raise GridError(f"start ledger {led.segment!r} does not match segment {seg.name!r}")
        if led.positivity_verdict not in (_adm.POSITIVITY_HELD, _adm.POSITIVITY_WITHIN_FLOOR) \
                or led.structural_tier != "STRUCTURALLY_CONSERVING":
            raise GridError(f"start segment {seg.name!r} ledger is not an admitted segment")
        begin, end = start.frames[s0], start.frames[s0 + n]
        if any(f.segment != seg.name for f in start.frames[s0 + 1:s0 + n + 1]):
            raise GridError(f"start frames {s0 + 1}..{s0 + n} do not belong to segment {seg.name!r}")
        if digest(begin.amounts) != start.segment_start_digests[k]:
            raise GridError(f"start segment {seg.name!r} did not begin from the state its start digest records")
        if not led.material or set(led.material) != set(led.component_tolerance):
            raise GridError(f"start segment {seg.name!r} ledger does not gate every component it reports")
        for lab, (_change, flux) in led.material.items():
            co = _component_coeff(spec, lab)
            resid = _component_total(spec, end.amounts, co) - _component_total(spec, begin.amounts, co) - float(flux)
            if not abs(resid) <= float(led.component_tolerance[lab]):
                raise GridError(f"start segment {seg.name!r}: component {lab!r} does not close on its frames "
                                f"(residual {resid!r} mol > tolerance {float(led.component_tolerance[lab])!r}): the "
                                f"recorded run was edited")
        s0 += n
    if s0 != start.step_count:
        raise GridError("start segments do not account for its step count")


def _segment_steps(seg: ValveSegment, dt: float) -> int:
    n = int(round(seg.duration_s / dt))
    if n < 1 or abs(n * dt - seg.duration_s) > 1e-9 * seg.duration_s:
        raise GridError(f"segment {seg.name!r} duration {seg.duration_s!r} s is not an integer multiple of dt={dt!r}")
    return n


def run_reactive_grid(spec: ReactiveGridSpec, initial, segments, *, scheme: str = "strang", dt: float,
                      rtol: float = 1e-10, atol: float = 1e-14, start: ReactiveRun | None = None) -> ReactiveRun:
    """Integrate the valve schedule through the ONE generic coupled integrator (``CoupledWorld.integrate`` with
    ``require_certified_execution=True``).  Each segment is a separate integration continued from the previous final
    state.  A segment whose receipt does not hold positivity (caller-independent floor), close its per-step
    per-component material ledger, or keep a STRUCTURALLY_CONSERVING tier is REFUSED (raised, raw minima reported).

    ``start`` continues a previous run of the same spec / scheme / dt / tolerances from its final state (``initial``
    must then be None); frame indices and global steps continue, so two continued half-runs reproduce one run of the
    same total schedule bit-for-bit."""
    if type(spec) is not ReactiveGridSpec:
        raise GridError("spec must be a ReactiveGridSpec")
    if scheme not in ("lie", "strang", "monolithic"):
        raise GridError("scheme must be 'lie', 'strang' or 'monolithic'")
    dt = _finite(dt, "dt", positive=True)
    segments = tuple(segments)
    if not segments or any(type(s) is not ValveSegment for s in segments):
        raise GridError("segments must be a non-empty sequence of ValveSegment")
    if start is None:
        if initial is None:
            raise GridError("initial inventory is required (or pass start= to continue a run)")
        state = _initial_state(spec, initial)
        frames = [_make_frame(spec, 0, 0, dt, segments[0], state)]
        ledgers, step0, init_digest = [], 0, _state_digest(spec, state)
        start_digests = []
    else:
        if initial is not None:
            raise GridError("pass either initial or start, not both")
        if type(start) is not ReactiveRun or start.spec != spec:
            raise GridError("start must be a ReactiveRun of the SAME spec")
        if (start.scheme, start.dt, start.rtol, start.atol) != (scheme, dt, rtol, atol):
            raise GridError("continuation must keep the scheme, dt and tolerances of the run it continues")
        _verify_start(spec, start, dt)                        # re-derived, not trusted
        state = {cell_name(c): {s: float(start.final[c][s.name]) for s in spec.species} for c in spec.cells()}
        frames, ledgers = list(start.frames), list(start.ledgers)
        step0, init_digest = start.step_count, start.initial_digest
        start_digests = list(start.segment_start_digests)
    all_names = [s.name for s in (start.segments if start is not None else ())] + [s.name for s in segments]
    if len(set(all_names)) != len(all_names):
        raise GridError("segment names must be unique across a run (frames bind to their segment's ledger by name)")
    step = step0
    for seg in segments:
        n = _segment_steps(seg, dt)
        start_digests.append(_state_digest(spec, state))      # the state this segment is integrated FROM
        world = build_reactive_world(spec, seg.open_valves)
        traj = world.integrate(state, duration=float(seg.duration_s), n_steps=n, scheme=scheme, rtol=rtol, atol=atol,
                               require_certified_execution=True)
        rc = traj.receipt
        if not (rc.positivity_held and rc.material_balance_closed and rc.structural_tier == "STRUCTURALLY_CONSERVING"):
            raise GridError(f"segment {seg.name!r} refused: positivity {rc.positivity_verdict} (raw minima "
                            f"{dict(rc.negative_minima)}), material balance closed={rc.material_balance_closed} "
                            f"{dict(rc.component_resolution)}, first violation {rc.first_violation}")
        if len(traj.times) != n + 1:
            raise GridError("internal: expected one sample per macro-step")
        for j in range(1, n + 1):
            st = {cn: traj.amounts[cn][j] for cn in traj.compartments}
            frames.append(_make_frame(spec, len(frames), step + j, dt, seg, st))
        step += n
        ledgers.append(SegmentLedger(
            seg.name, n,
            MappingProxyType({lab: (float(rc.raw_material_change[lab]), float(rc.external_flux[lab]))
                              for lab in rc.raw_material_change}),
            MappingProxyType(dict(rc.component_tolerance)), MappingProxyType(dict(rc.component_max_residual)),
            MappingProxyType(dict(rc.component_resolution)), rc.positivity_verdict,
            MappingProxyType(dict(rc.negative_minima)), rc.execution_identity_basis, rc.structural_tier))
        state = {cn: dict(traj.amounts[cn][-1]) for cn in traj.compartments}
    return ReactiveRun(spec, scheme, dt, float(rtol), float(atol), tuple(start.segments if start else ()) + segments,
                       tuple(frames), tuple(ledgers), _amounts(spec, state), step, init_digest, tuple(start_digests))


# ============================================================ the independent reference (first-order networks)
def reference_open_faces(nx: int, ny: int, walls, valves, open_valves=frozenset()) -> frozenset:
    """The reference's OWN face enumeration, written independently of ``ReactiveGridSpec.all_faces/open_faces`` and
    of the canonical orientation: every unordered pair of cells one unit apart along x or y, minus walls and minus
    faces whose valve is not in ``open_valves``.  Faces are returned as frozensets of two cells."""
    def pair(a, b):
        return frozenset((tuple(a), tuple(b)))
    faces = set()
    for x in range(nx):
        for y in range(ny):
            for dx_, dy_ in ((1, 0), (0, 1)):
                if x + dx_ < nx and y + dy_ < ny:
                    faces.add(pair((x, y), (x + dx_, y + dy_)))
    names = {v[0] for v in valves}
    if not set(open_valves) <= names:
        raise GridError(f"unknown valve(s) {sorted(set(open_valves) - names)}")
    faces -= {pair(a, b) for a, b in walls}
    faces -= {pair(a, b) for name, a, b in valves if name not in open_valves}
    return frozenset(faces)


def reference_generator(spec: ReactiveGridSpec, open_valves=frozenset()):
    """(T, R, q, index): the transport generator T (faces + sinks), the reaction generator R, and the source vector q
    of dn/dt = (T + R) n + q, assembled directly from the face list and the stoichiometry with numpy.  State index
    (species s, cell c) -> s * n_cells + c.  Only first-order networks are linear: a reaction with kf > 0 must have
    reactant order 1, and one with kr > 0 product order 1; anything else is refused."""
    cells = [(x, y) for x in range(spec.nx) for y in range(spec.ny)]       # the reference's own cell order
    nc, ns = len(cells), len(spec.species)
    ci = {c: k for k, c in enumerate(cells)}
    si = {s.name: k for k, s in enumerate(spec.species)}
    V = float(spec.cell_volume_L)
    T = np.zeros((ns * nc, ns * nc))
    R = np.zeros((ns * nc, ns * nc))
    q = np.zeros(ns * nc)
    for s in spec.species:
        g = float(spec.conductance_of(s.name).k_Lps) / V
        if g == 0.0:
            continue
        o = si[s.name] * nc
        for face in reference_open_faces(spec.nx, spec.ny, spec.walls, spec.valves, open_valves):
            a, b = tuple(face)
            ia, ib = o + ci[a], o + ci[b]
            T[ia, ia] -= g
            T[ib, ia] += g
            T[ib, ib] -= g
            T[ia, ib] += g
    for ij, sp, k in spec.sinks:
        i = si[sp] * nc + ci[tuple(ij)]
        T[i, i] -= float(k) / V
    for ij, sp, rate in spec.sources:
        q[si[sp] * nc + ci[tuple(ij)]] += float(rate)
    for r in spec.reactions:
        reac = [(s, -c) for s, c in r.stoich if c < 0]
        prod = [(s, c) for s, c in r.stoich if c > 0]
        if (r.kf > 0 and (len(reac) != 1 or reac[0][1] != 1)) or (r.kr > 0 and (len(prod) != 1 or prod[0][1] != 1)):
            raise GridError(f"reaction {r.name!r} is not first order in each active direction; the linear reference "
                            f"does not cover it")
        for c in cells:
            if r.cells is not None and c not in r.cells:
                continue
            for s, nu in r.stoich:
                row = si[s] * nc + ci[c]
                if r.kf > 0:                                  # V * kf * (n_R / V) = kf * n_R  (mol/s)
                    R[row, si[reac[0][0]] * nc + ci[c]] += nu * float(r.kf)
                if r.kr > 0:
                    R[row, si[prod[0][0]] * nc + ci[c]] -= nu * float(r.kr)
    return T, R, q, {(s.name, c): si[s.name] * nc + ci[c] for s in spec.species for c in cells}


def splitting_commutator_norm(spec: ReactiveGridSpec, open_valves=frozenset()) -> float:
    """||[T_aug, R_aug]||_F on the AUGMENTED affine generators T_aug = [[T, q], [0, 0]] (boundaries belong to the
    transport sub-flow) and R_aug = [[R, 0], [0, 0]]:  [T_aug, R_aug] = [[T R - R T, -R q], [0, 0]].  Zero means
    Lie/Strang splitting of dn/dt = (T + R) n + q is exact for this configuration; a source feeding a reacting species
    makes it nonzero even when T and R commute."""
    T, R, q, _ = reference_generator(spec, open_valves)
    m = T.shape[0]
    Ta, Ra = np.zeros((m + 1, m + 1)), np.zeros((m + 1, m + 1))
    Ta[:m, :m], Ta[:m, m] = T, q
    Ra[:m, :m] = R
    return float(np.linalg.norm(Ta @ Ra - Ra @ Ta))


def reference_solution_coupled(spec: ReactiveGridSpec, initial: dict, segments) -> dict:
    """Exact affine propagation exp([[T + R, q], [0, 0]] t), segment by segment, over the full species x cell state.
    Returns {species: {(i, j): mol}}."""
    T0, _, _, idx = reference_generator(spec, frozenset())
    m = T0.shape[0]
    n = np.zeros(m)
    for ij, inv in initial.items():
        for nm, v in inv.items():
            n[idx[(nm, tuple(ij))]] = float(v)
    for seg in segments:
        T, R, q, _ = reference_generator(spec, seg.open_valves)
        A = np.zeros((m + 1, m + 1))
        A[:m, :m] = T + R
        A[:m, m] = q
        n = (expm(A * float(seg.duration_s)) @ np.append(n, 1.0))[:m]
    return {s.name: {c: float(n[idx[(s.name, c)]]) for c in spec.cells()} for s in spec.species}


# ============================================================ projection: receipt, snapshot, frame dict
def model_identity(run: ReactiveRun) -> str:
    """Content identity of the run's model AND of every state a segment was integrated from: a continuation that
    starts from a different state can never share an identity with the honest chain (which, being bit-exact, shares
    the identity of the uncut run of the same schedule)."""
    return _canon({"engine": "reactive_grid_xxv", "spec": run.spec.describe(), "scheme": run.scheme,
                   "dt": float(run.dt).hex(), "rtol": float(run.rtol).hex(), "atol": float(run.atol).hex(),
                   "initial": run.initial_digest,
                   "segments": [[s.name, float(s.duration_s).hex(), sorted(s.open_valves)] for s in run.segments],
                   "segment_start_states": list(run.segment_start_digests)})


def run_numerics(run: ReactiveRun) -> dict:
    """The receipt's numerics block from the MEASURED per-segment ledgers: every conserved component's per-step max
    residual against its own tolerance, and the positivity depth relative to the caller-independent physical floor."""
    tol, res = {}, {}
    scale = {s.name: 0.0 for s in run.spec.species}
    for f in run.frames:
        for c in run.spec.cells():
            for s in run.spec.species:
                scale[s.name] = max(scale[s.name], abs(f.amounts[c][s.name]))
    for k, led in enumerate(run.ledgers):
        for lab, t in led.component_tolerance.items():
            tol[f"seg{k}:ledger:{lab}"] = float(t)
            res[f"seg{k}:ledger:{lab}"] = float(led.component_max_residual[lab])
        depth = 0.0
        for key, m in led.negative_minima.items():
            sp = key.split("/", 1)[1]
            floor = CoupledWorld._POS_ABS_FLOOR + _adm.POS_REL_FLOOR * scale[sp]
            depth = max(depth, -float(m) / floor)
        tol[f"seg{k}:positivity_depth_over_floor"] = 1.0
        res[f"seg{k}:positivity_depth_over_floor"] = depth
    return {"solver": f"general_coupled.CoupledWorld.integrate scheme={run.scheme} (scipy BDF per sub-flow)",
            "convergence_status": "CONVERGED", "dt_s": float(run.dt), "rtol": float(run.rtol),
            "atol": float(run.atol), "tolerances": tol, "residuals": res,
            "notes": ["residuals certify conservation and positivity only; splitting and spatial truncation error are "
                      "NOT bounded by this receipt"]}


def run_receipt(run: ReactiveRun):
    from experiments.sandbox_foundation.snapshot import ModelRunReceipt
    return ModelRunReceipt.unadmitted_transport(model_identity(run), run_numerics(run))


def to_snapshot(run: ReactiveRun, frame: ReactiveFrame):
    """A PhysicalWorldSnapshot (the existing renderer contract) built from a PRIVATE copy of one frame, carrying the
    run's OWN ModelRunReceipt (derived here; a caller cannot supply one).  Returns (snapshot, oriented interfaces as
    cell-index pairs)."""
    return _to_snapshot(run, frame, run_receipt(run))


def _to_snapshot(run: ReactiveRun, frame: ReactiveFrame, receipt):
    from experiments.sandbox_foundation.snapshot import PhysicalWorldSnapshot
    if receipt.model_identity != model_identity(run):
        raise GridError("a receipt can only travel with the run whose model identity it carries")
    spec = run.spec
    cells = spec.cells()
    idx = {c: k for k, c in enumerate(cells)}
    amt = np.array([[frame.amounts[c][s.name] for s in spec.species] for c in cells])
    open_faces = spec.open_faces(frame.open_valves)
    valve_of = {f: nm for nm, f in spec.valve_faces().items()}
    seg_k = [s.name for s in run.segments].index(frame.segment)
    led = run.ledgers[seg_k]
    snap = PhysicalWorldSnapshot(
        tuple(s.name for s in spec.species), [spec.cell_volume_L * 1e-3] * len(cells), amt,
        np.ones_like(amt, dtype=bool),
        units={"amount": "mol", "volume": "m^3", "time": "s", "concentration": "mol/m^3"},
        model_tick=frame.step, physical_time_s=frame.time_s,
        conservation_diagnostics={"grid_total_mol": dict(frame.total_mol),
                                  "segment_component_resolution": dict(led.component_resolution),
                                  "segment_positivity_verdict": led.positivity_verdict,
                                  "segment_structural_tier": led.structural_tier},
        numerical_uncertainty={"note": "conservation/positivity residuals in the receipt; splitting and spatial "
                                       "truncation error unbounded"},
        boundary_material=tuple(f"valve:{valve_of[f]}:open" if f in valve_of else "open face" for f in open_faces),
        evidence={"provenance": "SYNTHETIC reactions; conductance kinds per species in conductance_kinds",
                  "conductance_kinds": {nm: c.kind for nm, c in spec.conductance},
                  "temperature_K": float(spec.T_K), "model_domain": spec.model_domain,
                  "claim": "computed projection only -- not a measurement, not a validated physical prediction"},
        display_hints={"layout": "grid2d", "nx": spec.nx, "ny": spec.ny, "cell_ij": [list(c) for c in cells]},
        receipt=receipt)
    return snap, tuple((idx[a], idx[b]) for a, b in open_faces)


def face_flux(spec: ReactiveGridSpec, amounts, species_name: str, tail, head) -> float:
    """F_{tail->head} = k_s (c_tail - c_head) (mol/s) at the given state; exactly antisymmetric under tail <-> head."""
    V = spec.cell_volume_L
    k = float(spec.conductance_of(species_name).k_Lps)
    return k * (amounts[tuple(tail)][species_name] / V - amounts[tuple(head)][species_name] / V)


def frame_dict(run: ReactiveRun, frame: ReactiveFrame) -> dict:
    """A renderer-neutral, strict-JSON frame built fresh from the immutable run: every quantity carries a unit and a
    quantity identity (``quantities``), faces carry their valve state and per-species instantaneous flux.  It is a new
    plain dict on every call, so a renderer writing into it cannot reach the run.  The receipt is the run's own, derived
    here; a caller cannot supply one."""
    spec = run.spec
    receipt = run_receipt(run)
    snap, _ = _to_snapshot(run, frame, receipt)
    cells = spec.cells()
    open_set = set(spec.open_faces(frame.open_valves))
    valve_of = {f: nm for nm, f in spec.valve_faces().items()}
    amounts = {c: dict(frame.amounts[c]) for c in cells}
    faces = []
    for f in spec.all_faces():
        a, b = f
        if f in spec.walls:
            state = "WALL"
        elif f in valve_of:
            state = "VALVE_OPEN" if f in open_set else "VALVE_CLOSED"
        else:
            state = "OPEN"
        flux = {s.name: (face_flux(spec, amounts, s.name, a, b) if f in open_set else 0.0) for s in spec.species}
        faces.append({"tail": list(a), "head": list(b), "state": state, "valve": valve_of.get(f),
                      "valve_open": (f in open_set) if f in valve_of else None, "face_flux_mol_per_s": flux})
    return {
        "schema": FRAME_SCHEMA, "frame_index": frame.index, "step": frame.step, "time_s": frame.time_s,
        "segment": frame.segment, "open_valves": list(frame.open_valves),
        "quantities": {k: dict(v) for k, v in QUANTITIES.items()},
        "temperature_K": float(spec.T_K), "model_domain": spec.model_domain,
        "cells": [list(c) for c in cells], "cell_volume_L": float(spec.cell_volume_L),
        "fields": {s.name: {"amount_mol": [amounts[c][s.name] for c in cells],
                            "concentration_mol_per_L": [amounts[c][s.name] / spec.cell_volume_L for c in cells]}
                   for s in spec.species},
        "faces": faces,
        "conductance": run.conductance_report, "reactions": run.reaction_report,
        "receipt": json.loads(json.dumps(receipt.to_dict(), default=list)),
        "snapshot": {"schema_version": snap.schema_version, "model_digest": snap.model_digest,
                     "evidence_digest": snap.evidence_digest},
    }


def frame_digest(run: ReactiveRun, frame: ReactiveFrame) -> str:
    return _canon(frame_dict(run, frame))
