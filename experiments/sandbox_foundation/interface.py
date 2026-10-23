"""Wave E -- the PASSIVE MATERIAL INTERFACE as a physical law, plus one minimal valve/membrane apparatus.

Ooh yeah, can do!  Everything here is SYNTHETIC / idealized / isothermal and says so.  This is NOT a falling-sand
renderer, NOT a CFD engine, NOT an equipment catalogue, and NOT a multiphase model.  A finite numerical check is
NOT a universal proof.

THE WHOLE POINT (the architectural moonshot): a wall / valve / membrane is NOT an equipment-specific event hand-coded
per gadget.  It is ONE physical INTERFACE LAW applied per oriented face -- the passive-interface contract derived in
mesh.py:

    J_f = -L_f . Delta(mu)_f ,   L_f = g_f * c_lm,f / (R T) >= 0   ==>   Delta(mu)_f . J_f = -L_f (Delta(mu)_f)^2 <= 0.

An interface is then fully described by ONE per-face, per-species conductance g_f,i [m^3/s] and ONE per-face valve
parameter theta_f in [0, 1]:
    * g_f,i == 0          -> the face is a WALL for species i (impermeable): no flux, no dissipation.
    * g_f,i  > 0          -> the face is PERMEABLE to species i: downhill Fickian transport under the contract.
    * g_f,X > 0, g_f,Y==0 -> a SELECTIVELY PERMEABLE membrane (passes X, blocks Y).
    * theta_f             -> a reversible VALVE multiplying every species' conductance on face f; theta=0 is shut,
                            theta=1 is wide open, and it NEVER creates or destroys matter (it only scales a
                            conservative, B_space-mediated transfer).

CONSERVATION is inherited, not re-proved: the accepted update is dn = B_space @ J, and ones^T B_space == 0, so every
internal transfer has equal-and-opposite ledger entries BY CONSTRUCTION, for any g and any valve setting.  Closing
every face between two groups of cells makes them INDEPENDENTLY conserved compartments -- a legitimate case, because
a spatial mesh need not be a connected TRANSPORT network (the geometry is connected; the transport is not).

E3 -- THE CHARGED-SPECIES OBSTRUCTION (handled honestly, not faked): independent Fick fluxes of Na+, Ac-, H+, OH-
do NOT enforce local electroneutrality.  Global charge conservation (E @ N and the B_space column-sum) is NECESSARY
but NOT SUFFICIENT: each ion would diffuse down its OWN gradient at its OWN mobility, separating charge locally with
no electric field to oppose it -- an unphysical result dressed up as a validated electrolyte model.  The correct law
is Nernst-Planck with an electrical-potential closure:

    J_i = -L_i ( grad(mu_i) + z_i F grad(phi) ) ,   closed by local electroneutrality  sum_i z_i c_i = 0
                                                     (or Poisson  -eps grad^2 phi = F sum_i z_i c_i),

which introduces a potential field phi this mesh DOES NOT carry (no electrostatic degree of freedom, no Poisson
solve, no electroneutral projection).  So ionic transport is DEFERRED with that dependency documented, and this
prototype FAILS CLOSED on any charged species (see Apparatus.__post_init__ / ChargedTransportNotAdmitted).  The
first prototype transports NEUTRAL tracers only.  Fabricating ion dynamics is the one unforgivable move; we refuse.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .mesh import (  # the geometry, the conservation backbone, and the passive-interface contract
    FICK, FluxEvent, Mesh, assert_passive, face_dissipation, face_fick_flux)
from .twocell import (  # reuse the ledger / errors / positivity discipline, never redefine
    INTERFACE, InvalidParameterError, Ledger, NegativeAmountError, SandboxError, _check_pos, _substeps)


class ChargedTransportNotAdmitted(SandboxError):
    """A species carrying net charge was handed to the passive-Fick apparatus.  Independent Fick fluxes do not
    enforce local electroneutrality; the required Nernst-Planck / electroneutral closure is DEFERRED (see module
    docstring E3).  This is a fail-closed refusal, NOT a silent fake electrolyte (red-team #14)."""


@dataclass(frozen=True)
class Tracer:
    """A passive, NEUTRAL tracer.  `charge` is carried ONLY so the apparatus can REFUSE a nonzero one (E3); it is
    not a transport driver here -- that would need the deferred Nernst-Planck law."""
    name: str
    charge: int = 0

    def __post_init__(self):
        if isinstance(self.charge, bool) or not isinstance(self.charge, (int, np.integer)):
            raise InvalidParameterError(f"tracer {self.name!r} charge must be an integer, got {self.charge!r}")


@dataclass(frozen=True, eq=False)
class Apparatus:
    """2-3+ connected control volumes with configurable MATERIAL BOUNDARIES, each governed by the one passive-
    interface law.  The boundary physics lives entirely in `base_conductance` (F, S) and `valves` (F,); there is no
    per-gadget special case.

    base_conductance[f, i]  m^3/s : the OPEN permeability of face f to species i (0 = a wall for that species).
    valves[f] in [0, 1]           : a reversible multiplier on face f's whole conductance column (0 = shut).
    T_K                           : the isothermal temperature the chemical-potential / mobility law uses.

    The EFFECTIVE conductance is g = valves[:,None] * base_conductance.  Everything downstream (flux, dissipation,
    positivity bound, conservation) reads `g` only, so opening/closing a valve is just a reversible change of g."""
    species: tuple
    mesh: Mesh
    base_conductance: np.ndarray            # (F, S) m^3/s, >= 0
    valves: tuple = None                    # (F,) in [0, 1]; None = all wide open
    T_K: float = 298.15

    def __post_init__(self):
        species = tuple(self.species)
        S = len(species)
        if S < 1 or len({t.name for t in species}) != S:
            raise InvalidParameterError("species must be a non-empty tuple of uniquely-named Tracers")
        charged = [t.name for t in species if int(t.charge) != 0]
        if charged:                          # E3: fail closed -- the deferred Nernst-Planck law owns ionic transport
            raise ChargedTransportNotAdmitted(
                f"species {charged} carry net charge; independent Fick fluxes do not enforce local "
                "electroneutrality, so ionic transport is DEFERRED (needs the Nernst-Planck electrical-potential "
                "closure this mesh has no phi field for -- see interface.py E3). Use neutral tracers only")
        _check_pos(self.T_K, "T_K")
        F = self.mesh.n_faces
        g0 = np.array(self.base_conductance, dtype=float)
        if g0.shape != (F, S):
            raise InvalidParameterError(f"base_conductance must be (n_faces={F}, n_species={S}), got {g0.shape}")
        if not np.all(np.isfinite(g0)) or np.any(g0 < 0):
            raise InvalidParameterError("base_conductance must be finite and >= 0 (a conductance is never negative)")
        g0.setflags(write=False)
        v = np.ones(F) if self.valves is None else np.array(self.valves, dtype=float)
        if v.shape != (F,) or not np.all(np.isfinite(v)) or np.any(v < 0.0) or np.any(v > 1.0):
            raise InvalidParameterError("valves must be one finite value per face in [0, 1]")
        v.setflags(write=False)
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "base_conductance", g0)
        object.__setattr__(self, "valves", tuple(float(x) for x in v))

    @property
    def g(self) -> np.ndarray:
        """Effective per-face/species conductance (F, S) m^3/s = valve * base.  A shut valve (theta=0) or a wall
        column (base=0) zeroes the flux for those faces/species."""
        return np.asarray(self.valves, float)[:, None] * self.base_conductance

    def with_valves(self, valves) -> "Apparatus":
        """A NEW apparatus with reset valve parameters (immutable -- reversible by construction)."""
        return Apparatus(self.species, self.mesh, self.base_conductance, tuple(valves), self.T_K)

    def set_valve(self, face: int, theta: float) -> "Apparatus":
        """A NEW apparatus with face `face`'s valve set to theta (the single-face convenience of with_valves)."""
        v = list(self.valves)
        v[face] = theta
        return self.with_valves(v)

    def transport_dt_max(self) -> float:
        """min over (cell, species) of V_i / sum_{faces incident to i} g_f[s] -- the explicit-Euler positivity
        bound, identical in form to mesh/twocell (inf if nothing couples -- e.g. every valve shut)."""
        coupling = np.abs(self.mesh.B_space) @ self.g           # (C, S)
        V = np.asarray(self.mesh.volumes_m3, float)[:, None]
        with np.errstate(divide="ignore"):
            lim = np.where(coupling > 0, V / np.where(coupling > 0, coupling, 1.0), math.inf)
        return float(np.min(lim, initial=math.inf))

    def concentration(self, n: np.ndarray) -> np.ndarray:
        return np.asarray(n, float) / np.asarray(self.mesh.volumes_m3, float)[:, None]

    def dissipation(self, n: np.ndarray) -> np.ndarray:
        """Per-face/species passive-interface witness Delta(mu).J (F, S) W, each <= 0 (the contract)."""
        return face_dissipation(self.mesh, self.g, self.concentration(n), self.T_K)


def transport(apparatus: Apparatus, n: np.ndarray, dt: float, *, policy: str = "raise",
              ledger: Optional[Ledger] = None, events: Optional[list] = None, step: int = 0,
              certify_passive: bool = True) -> np.ndarray:
    """One explicit-Euler passive-interface transport step on the apparatus.  dn = B_space @ J with J the Fickian
    face flux under the EFFECTIVE (valve-scaled) conductance.  Conservative by construction (ones^T B_space == 0);
    positivity-guarded (refuses, never clamps); records equal-and-opposite per-face ledger entries.  When
    certify_passive, every face's dissipation witness is asserted <= 0 BEFORE the state is accepted -- a passive
    interface that tried to inject free energy is refused.  Returns the new amounts (C, S) mol.

    NO reaction sources are ever added here (this is a passive INTERFACE operator, not a reaction operator) and NO
    external energy/work is drawn (the only ledger entries are INTERFACE transfers that sum to zero per face)."""
    mesh = apparatus.mesh
    V = np.asarray(mesh.volumes_m3, float)
    B = mesh.B_space
    g = apparatus.g
    n = np.array(n, dtype=float)
    if n.shape != (mesh.n_cells, len(apparatus.species)):
        raise InvalidParameterError(f"n must be (n_cells={mesh.n_cells}, n_species={len(apparatus.species)})")
    if np.any(n < 0):
        raise NegativeAmountError("negative amount into passive transport")
    dt_max = apparatus.transport_dt_max()
    nsub = _substeps(dt, dt_max, policy, "apparatus transport")
    h = dt / nsub
    for sub in range(nsub):
        c = n / V[:, None]
        if certify_passive:                 # the second law BEFORE we commit: no face may inject free energy
            assert_passive(mesh, g, c, apparatus.T_K)
        J = face_fick_flux(mesh, g, c)                              # (F, S) mol/s along tail -> head
        n_new = n + h * (B @ J)
        if np.any(n_new < 0):
            raise NegativeAmountError("apparatus transport would create a negative amount (refused, not clamped)")
        if ledger is not None or events is not None:
            for k, f in enumerate(mesh.faces):
                # each face emits TWO equal-and-opposite entries, one per incident cell, from ITS perspective:
                # the head GAINS +h*J, the tail LOSES -h*J; their sum is exactly 0 (IEEE a == -(-a)).
                for cell, orient in ((int(f.head), +1), (int(f.tail), -1)):
                    for s, t in enumerate(apparatus.species):
                        amt = float(orient * h * J[k, s])
                        if events is not None:
                            events.append(FluxEvent(k, t.name, amt, orient, h, FICK, cell, step, sub))
                        if ledger is not None:
                            ledger.add(step=step, operator="interface", kind=INTERFACE, quantity=t.name,
                                       cell=cell, amount=amt, unit="mol", note=f"face {k} (valve={apparatus.valves[k]:g})")
        n = n_new
    return n


# --------------------------------------------------------------------------------------------- the minimal apparatus
def two_chamber_valve(volumes=(1.0e-6, 1.0e-6), area=1.0e-4, distance=1.0e-2, species=None,
                      conductance=None, theta: float = 1.0, T_K: float = 298.15) -> Apparatus:
    """The smallest valve apparatus: 2 chambers joined by ONE face whose valve is `theta`.  `conductance` is the
    OPEN per-species permeability (default: equal for every species).  theta=0 shut, theta=1 open."""
    from .mesh import chain_mesh
    species = (Tracer("T"),) if species is None else tuple(species)
    S = len(species)
    mesh = chain_mesh(volumes, [area], [distance])
    base = np.full((1, S), 1.0e-8) if conductance is None else np.asarray(conductance, float).reshape(1, S)
    return Apparatus(species, mesh, base, (theta,), T_K)


def three_chamber_membrane(volumes=(1.0e-6, 1.0e-6, 1.0e-6), area=1.0e-4, distance=1.0e-2,
                           species=None, left_pass=None, right_pass=None,
                           valves=(1.0, 1.0), T_K: float = 298.15) -> Apparatus:
    """3 chambers in a chain with TWO material boundaries.  `left_pass`/`right_pass` are per-species booleans
    selecting which species each membrane passes (a wall for the rest) -- i.e. selective permeability.  A face that
    passes species i gets conductance 1e-8, a wall gets 0; the valves scale each face reversibly."""
    from .mesh import chain_mesh
    species = (Tracer("X"), Tracer("Y")) if species is None else tuple(species)
    S = len(species)
    left_pass = (True,) * S if left_pass is None else tuple(left_pass)
    right_pass = (True,) * S if right_pass is None else tuple(right_pass)
    mesh = chain_mesh(volumes, [area, area], [distance, distance])
    base = np.array([[1.0e-8 if p else 0.0 for p in left_pass],
                     [1.0e-8 if p else 0.0 for p in right_pass]], dtype=float)
    return Apparatus(species, mesh, base, tuple(valves), T_K)
