"""The smallest COMPOSITIONAL geometry: an N-cell chain with ORIENTED faces (demonstrated on three cells).

Ooh yeah, can do!  Everything here is IDEALIZED / SYNTHETIC and says so.  This is NOT a mesh engine, NOT a PDE
solver, and NOT real laboratory chemistry.  A finite numerical check is NOT a universal proof.

UNITS (SI), identical to twocell.py:  volume m^3 | amount mol | concentration mol/m^3 | time s | diffusivity m^2/s |
area m^2 | distance m | g = D*Area/Distance m^3/s.

ONE reusable structure: the ORIENTED FACE.  Face f joins `tail` -> `head` (orientation is a free labelling choice;
physics must not depend on it).  The spatial incidence matrix B_space (cells x faces) has
        B_space[head, f] = +1,   B_space[tail, f] = -1,
so a flow J_f [mol/s] ALONG the orientation (tail -> head) updates the cells by  dn/dt = B_space @ J.  Every face
column holds exactly one +1 and one -1, hence  ones^T @ B_space == 0 : a CLOSED system conserves every species
total BY CONSTRUCTION (the discrete divergence theorem), independent of any constitutive model.

FLUX EVENTS: every internal face emits, per step and per quantity, exactly TWO FluxEvents -- one for each incident
control volume -- each computed from ITS OWN perspective with twocell.diffusive_inflow (coef*(x_other - x_self)).
The two amounts are exact IEEE negatives of each other (a-b == -(b-a), and rounding is sign-symmetric), so the
per-face interface residual is exactly 0 as a real arithmetic property, not a tautology.  The accepted state
transition is computed through a DIFFERENT code path (one-sided face flux J pushed through B_space), so the
ledger-vs-transition comparison in `transition_residual` is a genuine cross-check, not the same number twice.

CONSTITUTIVE MODEL (declared, idealized): Fick's law, two-point finite-volume flux per face,
        J_f[s] = g_f[s] * (c_tail[s] - c_head[s]),   g_f[s] = D[s] * Area_f / Distance_f.

NUMERICAL TREATMENT: explicit Euler, first order in dt.  For every cell i and species s the update is a CONVEX
COMBINATION of concentrations (weights 1 - h*sum_f g/V_i  and  h*g_f/V_i) iff
        dt <= dt_max = min_{i,s} V_i / sum_{f incident to i} g_f[s]
(the generalisation of twocell's min(V)/g_max).  Under the bound: discrete maximum principle, no negative amount.
Over the bound: policy="raise" (default) raises TimestepError; policy="substep" substeps with an explicit flag;
a last-line NegativeAmountError guard fires on any negative accepted amount (e.g. an over-large prescribed outflow).

COUPLED REACTION-DIFFUSION (included, Lie splitting, first order in dt): the semi-discrete law
        dn/dt = (I_cells (x) N) r(c) + (B_space (x) I_species) J + b_external
is written out verbatim, with explicit Kronecker matrices, in `coupled_rhs` (a diagnostic / reference right-hand
side).  `reaction_step_mesh` reuses twocell.reaction_cell per cell (implicit Radau in extent space).  The splitting
error is MEASURED against an independent monolithic expm in the tests; it is NOT proved small in general.

Determinism: no RNG; states are immutable; identical inputs give bit-identical outputs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from .twocell import (  # reuse, never redefine
    EXTERNAL, INTERFACE, REACTION, InvalidParameterError, Ledger, Mechanism, NegativeAmountError, SandboxError,
    SolverSettings, SpeciesBoundary, StepReport, System, _check_pos, _substeps,
    diffusive_inflow, reaction_cell)

# Structural ceilings: a malformed / adversarial huge topology is a BOUNDED typed refusal, never an allocation.
MAX_CELLS = 4096
MAX_FACES = 16384
MAX_SPECIES_MESH = 1024


# --------------------------------------------------------------------------------------------- errors
class TopologyError(SandboxError, ValueError):
    """Invalid mesh topology (bad index, self-loop, non-adjacent chain face, bounds exceeded, ...)."""


class MissingFaceError(TopologyError):
    """A face that the declared topology requires is absent (or the mesh is disconnected / an event is missing)."""


class DuplicateFaceError(TopologyError):
    """The same unordered cell pair is joined by more than one face (or an event is duplicated)."""


# --------------------------------------------------------------------------------------------- geometry
@dataclass(frozen=True)
class Face:
    """An oriented internal face tail -> head.  area [m^2] and distance [m] (centre-to-centre) must be finite > 0."""
    tail: int
    head: int
    area_m2: float
    distance_m: float

    def __post_init__(self):
        for nm, v in (("tail", self.tail), ("head", self.head)):
            if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
                raise TopologyError(f"face {nm}={v!r} must be an integer cell index")
        _check_pos(self.area_m2, "face area")        # negative / zero / NaN area -> InvalidParameterError
        _check_pos(self.distance_m, "face distance")


@dataclass(frozen=True, eq=False)
class Mesh:
    """Cells with volumes and a tuple of oriented Faces.

    topology="chain": the faces must be EXACTLY the N-1 adjacent pairs {i, i+1} once each (either orientation).
    topology="graph": any simple connected graph (no self-loop, no duplicate unordered pair)."""
    volumes_m3: tuple
    faces: tuple
    topology: str = "chain"

    def __post_init__(self):
        C = len(self.volumes_m3)
        if C < 1 or C > MAX_CELLS:
            raise TopologyError(f"{C} cells outside [1, MAX_CELLS={MAX_CELLS}] (bounded refusal)")
        if len(self.faces) > MAX_FACES:
            raise TopologyError(f"{len(self.faces)} faces exceeds MAX_FACES={MAX_FACES} (bounded refusal)")
        if self.topology not in ("chain", "graph"):
            raise TopologyError(f"unknown topology {self.topology!r}")
        for v in self.volumes_m3:
            _check_pos(v, "volume")
        seen: dict = {}
        for k, f in enumerate(self.faces):
            if not isinstance(f, Face):
                raise TopologyError(f"faces[{k}] is not a Face")
            if not (0 <= f.tail < C and 0 <= f.head < C):
                raise TopologyError(f"face {k} references a cell outside [0, {C})")
            if f.tail == f.head:
                raise TopologyError(f"face {k} is a self-loop on cell {f.tail}")
            key = frozenset((int(f.tail), int(f.head)))
            if key in seen:
                raise DuplicateFaceError(f"face {k} duplicates face {seen[key]} (cells {sorted(key)})")
            seen[key] = k
        if self.topology == "chain":
            want = {frozenset((i, i + 1)) for i in range(C - 1)}
            missing = want - set(seen)
            if missing:
                raise MissingFaceError(f"chain is missing face(s) between cells "
                                       f"{sorted(tuple(sorted(m)) for m in missing)}")
            extra = set(seen) - want
            if extra:
                raise TopologyError(f"non-adjacent face(s) in a chain: {sorted(tuple(sorted(m)) for m in extra)}")
        else:  # graph: connected (union-find)
            parent = list(range(C))

            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            for f in self.faces:
                parent[find(int(f.tail))] = find(int(f.head))
            if len({find(i) for i in range(C)}) > 1:
                raise MissingFaceError("mesh is disconnected: a face is missing between components")
        B = np.zeros((C, len(self.faces)))
        for k, f in enumerate(self.faces):
            B[f.head, k] = +1.0
            B[f.tail, k] = -1.0
        B.setflags(write=False)
        object.__setattr__(self, "_B", B)

    @property
    def n_cells(self) -> int:
        return len(self.volumes_m3)

    @property
    def n_faces(self) -> int:
        return len(self.faces)

    @property
    def B_space(self) -> np.ndarray:
        """Spatial incidence matrix (cells x faces): +1 at the head cell, -1 at the tail cell of each face."""
        return self._B

    def column_sums(self) -> np.ndarray:
        """ones^T @ B_space -- must be the zero vector (every face column sums to zero)."""
        return np.ones(self.n_cells) @ self._B


def chain_mesh(volumes_m3, areas_m2, distances_m) -> Mesh:
    """N cells in a row, N-1 faces oriented left -> right (cell i -> cell i+1)."""
    N = len(volumes_m3)
    if len(areas_m2) != N - 1 or len(distances_m) != N - 1:
        raise TopologyError("a chain of N cells needs N-1 areas and N-1 distances")
    return Mesh(tuple(volumes_m3), tuple(Face(i, i + 1, areas_m2[i], distances_m[i]) for i in range(N - 1)), "chain")


# --------------------------------------------------------------------------------------------- system + state
@dataclass(frozen=True, eq=False)
class MeshSystem:
    species: tuple
    diffusivity_m2_per_s: tuple
    mesh: Mesh
    species_boundaries: Optional[tuple] = None   # one SpeciesBoundary per CELL (None = all closed)
    mechanism: Optional[Mechanism] = None

    def __post_init__(self):
        S = len(self.species)
        if S > MAX_SPECIES_MESH or len(set(self.species)) != S:
            raise InvalidParameterError("species must be unique and within MAX_SPECIES_MESH")
        if len(self.diffusivity_m2_per_s) != S:
            raise InvalidParameterError("one diffusivity per species")
        for d in self.diffusivity_m2_per_s:
            _check_pos(d, "diffusivity", strict=False)
        sb = tuple(SpeciesBoundary() for _ in range(self.mesh.n_cells)) if self.species_boundaries is None \
            else tuple(self.species_boundaries)
        if len(sb) != self.mesh.n_cells:
            raise InvalidParameterError("one SpeciesBoundary per cell")
        for b in sb:
            if b.kind == "prescribed_flow" and len(b.flow_mol_per_s) != S:
                raise InvalidParameterError("prescribed flow needs one entry per species")
        object.__setattr__(self, "species_boundaries", sb)
        if self.mechanism is not None and tuple(self.mechanism.species) != tuple(self.species):
            raise InvalidParameterError("mechanism species must equal system species")

    @classmethod
    def from_two_cell(cls, system: System) -> "MeshSystem":
        """The 2-cell, 1-face mesh equivalent of a twocell.System (species transport + mechanism only)."""
        return cls(system.species, system.diffusivity_m2_per_s,
                   chain_mesh(system.volumes_m3, [system.area_m2], [system.distance_m]),
                   system.species_boundaries, system.mechanism)

    @property
    def g(self) -> np.ndarray:
        """Per-face, per-species mass-transfer coefficient D*Area/Distance, shape (F, S), m^3/s."""
        D = np.asarray(self.diffusivity_m2_per_s, float)
        A = np.array([f.area_m2 for f in self.mesh.faces], float)
        d = np.array([f.distance_m for f in self.mesh.faces], float)
        return (A / d)[:, None] * D[None, :]

    @property
    def inventory_matrix(self) -> np.ndarray:
        return self.mechanism.E if self.mechanism is not None else np.eye(len(self.species))

    def transport_dt_max(self) -> float:
        """min over (cell, species) of V_i / sum_{faces incident to i} g_f[s]  (inf if nothing couples)."""
        coupling = np.abs(self.mesh.B_space) @ self.g                     # (C, S)
        V = np.asarray(self.mesh.volumes_m3, float)[:, None]
        with np.errstate(divide="ignore"):
            lim = np.where(coupling > 0, V / np.where(coupling > 0, coupling, 1.0), math.inf)
        return float(np.min(lim, initial=math.inf))


@dataclass(frozen=True, eq=False)
class MeshState:
    n: np.ndarray   # (C, S) mol
    t: float = 0.0  # s

    def __post_init__(self):
        n = np.array(self.n, dtype=float)
        if n.ndim != 2 or not (np.all(np.isfinite(n)) and math.isfinite(self.t)):
            raise InvalidParameterError("state must be a finite (C, S) array")
        if np.any(n < 0):
            raise NegativeAmountError("negative initial amount")
        n.setflags(write=False)
        object.__setattr__(self, "n", n)

    def concentration(self, system: MeshSystem) -> np.ndarray:
        return self.n / np.asarray(system.mesh.volumes_m3, float)[:, None]

    def evolve(self, *, n=None, t=None) -> "MeshState":
        return MeshState(self.n if n is None else n, self.t if t is None else t)


# --------------------------------------------------------------------------------------------- flux events
@dataclass(frozen=True)
class FluxEvent:
    """One face's contribution to ONE incident control volume for one quantity over one (sub)step.

    amount        signed transfer INTO `cell` over `timestep` [mol] (positive = gain), computed from that cell's
                  own perspective.
    orientation   +1 if `cell` is the face's head, -1 if it is the tail (so B_space[cell, face] == orientation).
    timestep      the substep length h [s] the amount accumulated over.
    constitutive_model  the declared closure that produced the amount.
    cell, step, substep  provenance (extra to the six core fields; defaults keep the core call signature)."""
    face: int
    quantity: str
    amount: float
    orientation: int
    timestep: float
    constitutive_model: str
    cell: int = -1
    step: int = 0
    substep: int = 0


FICK = "fick-two-point-fv (SYNTHETIC)"


def _external_flows(system: MeshSystem) -> np.ndarray:
    ext = np.zeros((system.mesh.n_cells, len(system.species)))
    for i, b in enumerate(system.species_boundaries):
        if b.kind == "prescribed_flow":
            ext[i] = b.flow_mol_per_s
    return ext


# --------------------------------------------------------------------------------------------- operators
def transport_step_mesh(system: MeshSystem, state: MeshState, dt: float, *, policy: str = "raise",
                        flux_fn: Callable = diffusive_inflow, ledger: Optional[Ledger] = None,
                        events: Optional[list] = None, step: int = 0):
    """Explicit-Euler FV diffusion on the oriented-face mesh, plus prescribed external flows."""
    mesh = system.mesh
    dt_max = system.transport_dt_max()
    nsub = _substeps(dt, dt_max, policy, "mesh transport")
    h = dt / nsub
    V = np.asarray(mesh.volumes_m3, float)
    B = mesh.B_space
    g = system.g
    ext = _external_flows(system)
    n = np.array(state.n)
    for sub in range(nsub):
        c = n / V[:, None]
        # (1) per-side flux events, each from its OWN cell's perspective (ledger path)
        sub_events = []
        for k, f in enumerate(mesh.faces):
            for cell, other, orient in ((f.tail, f.head, -1), (f.head, f.tail, +1)):
                inflow = flux_fn(g[k], c[cell], c[other], orient)   # mol/s into `cell`
                for s, nm in enumerate(system.species):
                    sub_events.append(FluxEvent(k, nm, float(h * inflow[s]), orient, h, FICK, int(cell), step, sub))
        # (2) the ACCEPTED transition: one-sided flux ALONG the orientation pushed through B_space (state path)
        c_tail = np.array([c[f.tail] for f in mesh.faces]).reshape(mesh.n_faces, -1)
        c_head = np.array([c[f.head] for f in mesh.faces]).reshape(mesh.n_faces, -1)
        J = g * (c_tail - c_head)                                   # (F, S) mol/s along tail -> head
        n_new = n + h * (B @ J) + h * ext
        if np.any(n_new < 0):
            raise NegativeAmountError("mesh transport step would create a negative amount (refused, nothing clamped)")
        if events is not None:
            events.extend(sub_events)
        if ledger is not None:
            for e in sub_events:
                ledger.add(step=step, operator="transport", kind=INTERFACE, quantity=e.quantity, cell=e.cell,
                           amount=e.amount, unit="mol", note=f"face {e.face}")
            for i in range(mesh.n_cells):
                for s, nm in enumerate(system.species):
                    if ext[i, s] != 0.0:
                        ledger.add(step=step, operator="transport", kind=EXTERNAL, quantity=nm, cell=i,
                                   amount=float(h * ext[i, s]), unit="mol", note="prescribed flow")
        n = n_new
    return state.evolve(n=n), StepReport("transport", step, dt, nsub, nsub > 1, False, dt_max)


def reaction_step_mesh(system: MeshSystem, state: MeshState, dt: float, *,
                       settings: SolverSettings = SolverSettings(), ledger: Optional[Ledger] = None, step: int = 0):
    """Per-cell closed-cell reaction (twocell.reaction_cell, implicit Radau in extent space)."""
    mech = system.mechanism
    if mech is None:
        raise InvalidParameterError("system has no mechanism")
    _check_pos(dt, "dt", strict=False)
    n = np.array(state.n)
    rep = StepReport("reaction", step, dt, solver={"method": settings.method, "rtol": settings.rtol,
                                                   "atol": settings.atol, "pos_tol": settings.pos_tol,
                                                   "seed": settings.seed})
    for i in range(system.mesh.n_cells):
        n1, xi, cl, cres = reaction_cell(mech, n[i], system.mesh.volumes_m3[i], dt, settings)
        src = n1 - n[i]
        rep.extents[i] = xi
        rep.clamped = rep.clamped or cl
        rep.clamp_residual = max(rep.clamp_residual, cres)
        if ledger is not None:
            for s, nm in enumerate(system.species):
                ledger.add(step=step, operator="reaction", kind=REACTION, quantity=nm, cell=i,
                           amount=float(src[s]), unit="mol", note=f"SYNTHETIC:{mech.label}")
        n[i] = n1
    return state.evolve(n=n), rep


MESH_OPERATORS = {"transport": transport_step_mesh, "reaction": reaction_step_mesh}


@dataclass
class MeshRunResult:
    state: MeshState
    ledger: Ledger
    events: list
    reports: list


def run_mesh(system: MeshSystem, state0: MeshState, t_end: float, n_steps: int, sequence=("transport",), *,
             ledger: Optional[Ledger] = None, events: Optional[list] = None) -> MeshRunResult:
    """Lie (sequential) splitting: each macro-step applies every operator in `sequence` over the full dt."""
    if n_steps < 1:
        raise InvalidParameterError("n_steps >= 1")
    dt = _check_pos(t_end, "t_end") / n_steps
    ledger = Ledger() if ledger is None else ledger
    events = [] if events is None else events
    state, reports = state0, []
    for k in range(n_steps):
        for name in sequence:
            if name == "transport":
                state, rep = transport_step_mesh(system, state, dt, ledger=ledger, events=events, step=k)
            else:
                state, rep = MESH_OPERATORS[name](system, state, dt, ledger=ledger, step=k)
            reports.append(rep)
    return MeshRunResult(state.evolve(t=state0.t + t_end), ledger, events, reports)


# --------------------------------------------------------------------------------------------- the coupled law, verbatim
def coupled_rhs(system: MeshSystem, n: np.ndarray) -> np.ndarray:
    """dn/dt = (I_cells (x) N) r + (B_space (x) I_species) J + b_external, with n flattened cell-major
    (index = cell*S + s) and J flattened face-major (index = face*S + s).  Returns shape (C, S), mol/s.
    A diagnostic / reference RHS; the steppers use the split operators above."""
    mesh = system.mesh
    C, F, S = mesh.n_cells, mesh.n_faces, len(system.species)
    V = np.asarray(mesh.volumes_m3, float)
    c = np.asarray(n, float) / V[:, None]
    if system.mechanism is not None:
        N = system.mechanism.N
        r = np.concatenate([V[i] * system.mechanism.rate_vector(c[i]) for i in range(C)])  # extent rate, mol/s
        react = np.kron(np.eye(C), N) @ r
    else:
        react = np.zeros(C * S)
    J = (system.g * np.array([c[f.tail] - c[f.head] for f in mesh.faces]).reshape(F, S)).reshape(F * S)
    spatial = np.kron(mesh.B_space, np.eye(S)) @ J
    return (react + spatial + _external_flows(system).reshape(C * S)).reshape(C, S)


# --------------------------------------------------------------------------------------------- audits
def interface_report(events: list, system: MeshSystem, *, strict: bool = False) -> dict:
    """Group events by (step, substep, face, quantity).  Every expected group must hold EXACTLY two events, on the
    two distinct incident cells, with opposite orientation.  Reports the max |sum| over well-formed groups
    (interface residual, must be exactly 0), plus MISSING (absent / lone) and DUPLICATED (extra / repeated cell)
    groups.  strict=True raises MissingFaceError / DuplicateFaceError instead of returning them."""
    mesh = system.mesh
    groups: dict = {}
    times = set()
    for e in events:
        groups.setdefault((e.step, e.substep, e.face, e.quantity), []).append(e)
        times.add((e.step, e.substep))
    missing, duplicated, residual = [], [], 0.0
    for (st, sub) in sorted(times):
        for k, f in enumerate(mesh.faces):
            for nm in system.species:
                evs = groups.get((st, sub, k, nm), [])
                cells = sorted(e.cell for e in evs)
                if len(evs) < 2:
                    missing.append((st, sub, k, nm))
                elif len(evs) > 2 or cells != sorted((int(f.tail), int(f.head))):
                    duplicated.append((st, sub, k, nm))
                else:
                    residual = max(residual, abs(math.fsum(e.amount for e in evs)))
    if strict and missing:
        raise MissingFaceError(f"missing face event group(s): {missing[:5]}")
    if strict and duplicated:
        raise DuplicateFaceError(f"duplicated face event group(s): {duplicated[:5]}")
    return {"interface_residual": residual, "missing": missing, "duplicated": duplicated}


def transition_residual(system: MeshSystem, state0: MeshState, state1: MeshState, ledger: Ledger,
                        operator: str = "transport") -> float:
    """max |(n1 - n0)[cell, s] - sum of the ledger's INTERFACE + EXTERNAL entries for that cell/species|.
    Compares the RECORDED per-face events with the ACTUAL accepted state transition."""
    idx = {nm: i for i, nm in enumerate(system.species)}
    acc = np.zeros_like(state0.n)
    for e in ledger.filter(operator=operator).entries:
        if e.kind in (INTERFACE, EXTERNAL):
            acc[e.cell, idx[e.quantity]] += e.amount
    return float(np.max(np.abs((state1.n - state0.n) - acc), initial=0.0))


def audit_mesh(system: MeshSystem, state0: MeshState, state1: MeshState, ledger: Ledger) -> dict:
    """Global balance: change of inventory minus RECORDED external flows (interface / reaction terms must cancel
    / conserve on their own -- which is what is being tested)."""
    idx = {nm: i for i, nm in enumerate(system.species)}
    ext = np.zeros(len(system.species))
    for e in ledger.entries:
        if e.kind == EXTERNAL and e.quantity in idx:
            ext[idx[e.quantity]] += e.amount
    dn = state1.n.sum(axis=0) - state0.n.sum(axis=0)
    inv = system.inventory_matrix @ (dn - ext)
    return {"inventory_residual": float(np.max(np.abs(inv), initial=0.0)), "external_amount_mol": ext}
