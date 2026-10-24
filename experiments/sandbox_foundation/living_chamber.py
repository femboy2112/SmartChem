"""Wave C (Round VII) -- THE FIRST LIVING CHEMICAL CHAMBER.

Ooh yeah, can do -- and it is SYNTHETIC / experimental, headless, and imports no LibGibson.  This composes two
pieces that were each verified on their own -- the source-backed 0-D aqueous equilibrium (aqueous_equilibrium.py)
and the conservative finite-volume interface discipline (twocell.py / mesh.py / interface.py) -- into a small,
physically accountable chemical world:

    a conserved material inventory crosses a physical boundary; local chemistry re-equilibrates; a real chemical
    observable (pH) changes; and the whole transition stays conservative, dimensionally valid and numerically checked.

THE STATE IS THE CONSERVED COMPONENT INVENTORY, NOT SIX FREE SPECIES.  Each `Chamber` carries only its analytical
totals -- n_acetate (mol), n_sodium (mol), volume (m^3), temperature (K).  The six concentrations
([HAc], [Ac-], [H+], [OH-], [Na+], [NaAc]) are NOT independent evolution coordinates: within the fast-equilibrium
model they are a pure function E(b) of the totals b, delivered by `AcetateWaterSystem.solve`.  Writing
  A = the component map (which species carry which component),   b = (n_acetate, n_sodium),   E(b) = speciation,
the round-trip identity  A . E(b) = b  is a checkable invariant (``Chamber.component_identity_residual``), not an
assumption -- it is exactly the solver's own mass balance, re-read at the component layer.

THE MEMBRANE PASSES ONLY NEUTRAL ACETIC ACID.  For one oriented internal face (tail -> head):
    J_HAc = g_HAc * (c_HAc[tail] - c_HAc[head])          [mol/s],   g_HAc = D*A_face/distance * valve   [m^3/s]
with the concentrations in mol/m^3.  The aqueous solver speaks mol/L, so the hinge is explicit and tested:
    c_HAc[mol/m^3] = SpeciationResult.hac_M * LITRES_PER_M3 ,   LITRES_PER_M3 = 1000 .
A wrong factor here is a thousand-fold error, so ``test_living_chamber`` pins it directly.  The face moves TOTAL
ACETATE by +/- (J_HAc * dt) on its two incident cells (equal and opposite), and it moves NOTHING ELSE: no sodium,
no individual ion, no charge, no water, no energy.  There is NO hydrogen-ion transport law and NO independent
Na+/Ac-/H+/OH- diffusion -- coupling charged species to independent Fick fluxes would violate local electroneutrality
(the Nernst-Planck obstruction, interface.py E3), so it is deliberately absent here.

THE ACCEPTED STEP (``step``):
  1. read each cell's conserved totals b;
  2. compute the current admitted local speciation E(b);
  3. compute each face's neutral-HAc flux from the (declared, passive) concentration-difference law;
  4. apply ONE oriented conservative component transfer per face (equal & opposite on total acetate only);
  5. enforce nonnegative component inventories and a timestep bound (a step that would export more neutral acid
     than the donor holds, or drive a total negative, is REFUSED or SUBSTEPPED -- never silently truncated);
  6. re-equilibrate both incident cells;
  7. verify component mass balance, local charge closure, and source applicability (the solver's own gate);
  8. hand back an immutable ``ChamberState`` carrying the resulting pH and species distribution per cell.

This is NOT a kinetic reaction rate: the interconversion HAc<->Ac- is an ALGEBRAIC local-equilibrium projection, not
a sourced rate law, and it is never labelled a rate.  The only time-dependent process is the explicit material
transport; the chemistry is the fast-equilibrium limit of it.

CONSERVATION LAWS (proved as checkable residuals; see the module-level helpers and ``test_living_chamber``):
  * global total acetate is invariant under internal transport (sum over cells unchanged to roundoff);
  * global total sodium is invariant -- indeed per cell, since the membrane admits no sodium at all;
  * every internal face contributes equal-and-opposite amounts (the transfer is a signed pair, by construction);
  * local electroneutrality is re-established by each admitted equilibrium solve (charge_balance_residual ~ 0);
  * the component trajectory is INDEPENDENT of how often a frame is presented (rendering is a pure read).

FREE ENERGY -- what is proved and what is NOT (a weaker true theorem over a stronger false one).  For the NEUTRAL-HAc
transport step ALONE, under the model's own ideal-dilute neutral-solute assumption (a_HAc ~ c_HAc), the flux is
down the HAc chemical-potential gradient: sign(J_HAc) = sign(mu_HAc[tail] - mu_HAc[head]) with mu_HAc = mu0 + RT ln
(c_HAc/c_ref), so J_HAc * (mu[tail]-mu[head]) >= 0 and the transport operator is dissipative in HAc
(``transport_dissipation_margin`` must be >= 0 for every face).  That is the honest, provable statement.  A GLOBAL
Lyapunov / free-energy certificate for the FULL coupled system (transport + re-speciation + the nonideal Davies
activity model + the optional ion pair) is NOT claimed: the equilibrium projection redistributes acetate across
HAc/Ac-/NaAc and the activity coefficients couple all charged species, and no single global free-energy functional
with a proven monotone discrete decrease has been established under the sourced Davies(+pair) model.  That obstruction
is named, not papered over (``FREE_ENERGY_OBSTRUCTION``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Optional

import numpy as np

from experiments.sandbox_foundation.aqueous_equilibrium import (
    AcetateWaterSystem, SpeciationResult, solve)
from experiments.sandbox_foundation.twocell import InvalidParameterError, SandboxError

LITRES_PER_M3 = 1000.0   # 1 m^3 = 1000 L -- the mol/L <-> mol/m^3 hinge; a wrong factor here is a 1000x error.

# Numerical controls, out in the open (same discipline as aqueous_equilibrium / twocell: a tolerance reflects what
# the step GENUINELY achieves, never widened to drag a fixture green).
TRANSFER_NEGATIVE_ATOL_MOL = 1e-15   # a component total may dip this far below 0 on roundoff; more is a real failure
CONSERVATION_ATOL_MOL = 1e-12        # global-total drift a transport step may show (should be ~machine zero)
AVAILABILITY_RTOL = 1e-9             # slack on the "cannot export more HAc than the donor holds" bound
MAX_SUBSTEPS = 10000                 # adaptive-substep budget (Wave F): a world needing more chunks than this is too
#   stiff for explicit substepping at the requested dt -> fail CLOSED rather than grind or over-export.

FREE_ENERGY_OBSTRUCTION = (
    "No global free-energy Lyapunov is claimed for the full coupled system: the equilibrium projection redistributes "
    "acetate across HAc/Ac-/NaAc and the nonideal Davies activity coefficients couple the charged species, so a single "
    "global functional with a proven monotone discrete decrease is not established under the sourced Davies(+ion-pair) "
    "model. Proved instead: the neutral-HAc transport step alone is down the HAc chemical-potential gradient "
    "(transport_dissipation_margin >= 0), under the model's ideal-dilute neutral-solute assumption a_HAc ~ c_HAc.")


class ChamberError(SandboxError):
    """A fail-closed refusal in the living-chamber layer (bad geometry, an un-admitted local solve, a step that would
    violate conservation or export more neutral acid than exists)."""


# --------------------------------------------------------------------------------------------- conserved component cell
@dataclass(frozen=True)
class Chamber:
    """A well-mixed aqueous compartment described by its CONSERVED analytical components only.

    n_acetate_mol = total acetate (HAc + Ac- + NaAc), n_sodium_mol = total sodium (Na+ + NaAc), both >= 0 and in mol;
    volume_m3 > 0; temperature_K fixed (298.15 K for the current sourced data).  The local speciation is DERIVED from
    these totals by the sourced aqueous solver -- it is never stored as independent state."""
    n_acetate_mol: float
    n_sodium_mol: float
    volume_m3: float
    temperature_K: float = 298.15
    activity_model: str = "davies"
    include_ion_pair: bool = False

    def __post_init__(self):
        for nm, v in (("n_acetate_mol", self.n_acetate_mol), ("n_sodium_mol", self.n_sodium_mol)):
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise InvalidParameterError(f"{nm}={v!r} must be a finite amount >= 0 mol")
        if not (math.isfinite(self.volume_m3) and self.volume_m3 > 0):
            raise InvalidParameterError(f"volume_m3={self.volume_m3!r} must be finite and > 0")
        if self.activity_model not in ("ideal", "davies"):
            raise InvalidParameterError("activity_model must be 'ideal' or 'davies'")

    # -- component inventory b = (acetate, sodium) --------------------------------------------------
    @property
    def total_acetate_M(self) -> float:
        return self.n_acetate_mol / (self.volume_m3 * LITRES_PER_M3)

    @property
    def sodium_M(self) -> float:
        return self.n_sodium_mol / (self.volume_m3 * LITRES_PER_M3)

    def components(self) -> np.ndarray:
        """b = (n_acetate_mol, n_sodium_mol): the authoritative conserved inventory of this cell."""
        return np.array([self.n_acetate_mol, self.n_sodium_mol], dtype=float)

    def system(self) -> AcetateWaterSystem:
        return AcetateWaterSystem(
            total_acetic_M=self.total_acetate_M, sodium_M=self.sodium_M, temperature_K=self.temperature_K,
            activity_model=self.activity_model, include_ion_pair=self.include_ion_pair)

    def speciate(self) -> SpeciationResult:
        """E(b): the admitted local equilibrium speciation.  Raises (fail closed) if the solver cannot certify it."""
        return solve(self.system())

    # -- A . E(b) = b : the component map applied to the speciation recovers the totals (in mol) -----
    def recovered_components(self, sp: SpeciationResult) -> np.ndarray:
        """A E(b): recover (acetate, sodium) totals in mol from a solved speciation (mol/L -> mol).  Acetate is
        carried by HAc + Ac- + NaAc; sodium by Na+ + NaAc."""
        litres = self.volume_m3 * LITRES_PER_M3
        acetate = (sp.hac_M + sp.ac_minus_M + sp.naac_M) * litres
        sodium = (sp.na_plus_M + sp.naac_M) * litres
        return np.array([acetate, sodium], dtype=float)

    def component_identity_residual(self, sp: Optional[SpeciationResult] = None) -> float:
        """max |A E(b) - b| (mol): the conserved inventory survives the local speciation.  ~0 to the solver's own
        mass-balance tolerance.  Falsifier #8."""
        sp = sp if sp is not None else self.speciate()
        return float(np.max(np.abs(self.recovered_components(sp) - self.components())))

    def n_hac_mol(self, sp: Optional[SpeciationResult] = None) -> float:
        """The amount of NEUTRAL acetic acid present (mol) -- the physical bound on what a face can export in a step."""
        sp = sp if sp is not None else self.speciate()
        return float(sp.hac_M * self.volume_m3 * LITRES_PER_M3)

    def c_hac_mol_per_m3(self, sp: Optional[SpeciationResult] = None) -> float:
        """Neutral-HAc concentration in mol/m^3 (the transport-side unit): hac_M [mol/L] * 1000."""
        sp = sp if sp is not None else self.speciate()
        return float(sp.hac_M * LITRES_PER_M3)

    def mu_hac_over_RT(self, sp: Optional[SpeciationResult] = None) -> float:
        """Reduced HAc chemical potential mu/RT = ln(c_HAc/c_ref) under the ideal-dilute neutral-solute assumption
        (a_HAc ~ c_HAc), with c_ref = 1 mol/L.  -inf if no HAc is present; used only for the down-gradient witness."""
        sp = sp if sp is not None else self.speciate()
        return math.log(sp.hac_M) if sp.hac_M > 0.0 else -math.inf

    def with_components(self, *, n_acetate_mol=None, n_sodium_mol=None) -> "Chamber":
        return replace(self,
                       n_acetate_mol=self.n_acetate_mol if n_acetate_mol is None else float(n_acetate_mol),
                       n_sodium_mol=self.n_sodium_mol if n_sodium_mol is None else float(n_sodium_mol))


# --------------------------------------------------------------------------------------------- selective membrane
@dataclass(frozen=True)
class Membrane:
    """An oriented internal face (tail -> head) that passes ONLY neutral acetic acid (HAc).

    g_HAc_m3_per_s = D_HAc * area / distance >= 0 is the passive conductance (m^3/s); ``valve`` in [0, 1] scales it
    (0 = shut wall, 1 = fully open).  The face transports HAc only: no Na+, no Ac-, no H+/OH-, no charge, no energy."""
    tail: int
    head: int
    g_HAc_m3_per_s: float
    valve: float = 1.0

    def __post_init__(self):
        if self.tail == self.head:
            raise InvalidParameterError("a membrane must join two DISTINCT cells")
        if not (isinstance(self.tail, int) and isinstance(self.head, int) and self.tail >= 0 and self.head >= 0):
            raise InvalidParameterError("membrane cell indices must be non-negative ints")
        if not (math.isfinite(self.g_HAc_m3_per_s) and self.g_HAc_m3_per_s >= 0):
            raise InvalidParameterError("g_HAc_m3_per_s must be finite and >= 0")
        if not (math.isfinite(self.valve) and 0.0 <= self.valve <= 1.0):
            raise InvalidParameterError("valve must be in [0, 1]")

    @property
    def conductance(self) -> float:
        """Effective HAc conductance g*valve (m^3/s); 0 for a shut valve or an impermeable (g=0) wall."""
        return self.g_HAc_m3_per_s * self.valve

    def with_valve(self, valve: float) -> "Membrane":
        return replace(self, valve=float(valve))


# --------------------------------------------------------------------------------------------- the closed world
@dataclass(frozen=True)
class ChamberWorld:
    """A closed world: a tuple of chambers joined by membranes.  Closed = no external reservoir; the only transfers
    are internal neutral-HAc fluxes, so global totals are conserved.  All chambers share one temperature (isothermal
    world; the sourced data is 25 C)."""
    chambers: tuple
    membranes: tuple = ()

    def __post_init__(self):
        if not self.chambers or not all(isinstance(c, Chamber) for c in self.chambers):
            raise InvalidParameterError("chambers must be a non-empty tuple of Chamber")
        n = len(self.chambers)
        temps = {c.temperature_K for c in self.chambers}
        if len(temps) != 1:
            raise InvalidParameterError("a closed isothermal world: every chamber must share one temperature")
        for m in self.membranes:
            if not isinstance(m, Membrane):
                raise InvalidParameterError("membranes must be Membrane instances")
            if m.tail >= n or m.head >= n:
                raise InvalidParameterError(f"membrane cell index out of range (have {n} chambers)")

    def totals(self) -> np.ndarray:
        """Global conserved inventory (acetate_mol, sodium_mol) summed over all chambers."""
        return np.sum([c.components() for c in self.chambers], axis=0)

    def speciate_all(self) -> tuple:
        """E over every cell; raises (fail closed) if any local solve is not admitted."""
        return tuple(c.speciate() for c in self.chambers)

    def charge_residuals(self, specs: Optional[tuple] = None) -> np.ndarray:
        """Per-cell |charge-balance residual| (mol/L) from the admitted solve -- local electroneutrality witness."""
        specs = specs if specs is not None else self.speciate_all()
        return np.array([sp.charge_balance_residual for sp in specs], dtype=float)

    def pH(self, specs: Optional[tuple] = None) -> np.ndarray:
        specs = specs if specs is not None else self.speciate_all()
        return np.array([sp.pH for sp in specs], dtype=float)

    def set_valve(self, face: int, valve: float) -> "ChamberWorld":
        ms = list(self.membranes)
        ms[face] = ms[face].with_valve(valve)
        return replace(self, membranes=tuple(ms))

    def transport_dt_max(self) -> float:
        """A conservative explicit-Euler bound: the step must not export more neutral acid from any cell than the
        cell holds.  dt_max = min over donor cells of (n_HAc / total outgoing conductance*c_HAc).  inf if nothing can
        move (all valves shut / no HAc).  This is the sizing used by policy='substep'."""
        specs = self.speciate_all()
        c = np.array([self.chambers[i].c_hac_mol_per_m3(specs[i]) for i in range(len(self.chambers))])
        n_hac = np.array([self.chambers[i].n_hac_mol(specs[i]) for i in range(len(self.chambers))])
        outflow_rate = np.zeros(len(self.chambers))      # mol/s leaving each cell at the current speciation
        for m in self.membranes:
            j = m.conductance * (c[m.tail] - c[m.head])  # mol/s tail->head
            if j > 0:
                outflow_rate[m.tail] += j
            elif j < 0:
                outflow_rate[m.head] += -j
        lim = math.inf
        for i in range(len(self.chambers)):
            if outflow_rate[i] > 0:
                lim = min(lim, n_hac[i] / outflow_rate[i])
        return lim


# --------------------------------------------------------------------------------------------- the accepted step
@dataclass(frozen=True)
class TransferLedgerEntry:
    """One signed neutral-HAc transfer across a face in a (sub)step: amount_mol moves tail -> head (of TOTAL acetate;
    the carrier is neutral HAc).  Equal-and-opposite by construction -- the SAME amount is added to head and removed
    from tail, so a per-face pair sums to exactly zero."""
    face: int
    tail: int
    head: int
    amount_mol: float
    flux_mol_per_s: float


@dataclass(frozen=True)
class ChamberState:
    """An immutable observation of the world at one tick: the authoritative totals live in the chambers; the derived
    speciation, pH, per-cell charge residual, and the transfer ledger for the step that produced this state travel
    alongside for a (read-only) presenter.  Rendering a ChamberState changes nothing (Wave D / falsifier #15)."""
    world: ChamberWorld
    tick: int
    time_s: float
    specs: tuple                      # SpeciationResult per cell
    ledger: tuple = ()                # TransferLedgerEntry for the step that produced this state

    @property
    def pH(self) -> np.ndarray:
        return np.array([sp.pH for sp in self.specs], dtype=float)

    @property
    def totals(self) -> np.ndarray:
        return self.world.totals()

    def charge_residuals(self) -> np.ndarray:
        return np.array([sp.charge_balance_residual for sp in self.specs], dtype=float)


def _face_fluxes(world: ChamberWorld, specs: tuple) -> np.ndarray:
    """J_HAc per face (mol/s), tail -> head, from the current speciation.  Pure function of the concentration field."""
    c = np.array([world.chambers[i].c_hac_mol_per_m3(specs[i]) for i in range(len(world.chambers))])
    return np.array([m.conductance * (c[m.tail] - c[m.head]) for m in world.membranes], dtype=float)


def transport_dissipation_margin(world: ChamberWorld, specs: Optional[tuple] = None) -> float:
    """min over faces of  J_HAc * (mu_HAc[tail] - mu_HAc[head]) / RT  (reduced).  >= 0 means every face moves HAc DOWN
    its chemical-potential gradient (the provable dissipation property of the neutral transport; NOT a global Lyapunov
    -- see FREE_ENERGY_OBSTRUCTION).  A face with zero flux contributes 0.  Falsifier #16 / C3 free-energy."""
    specs = specs if specs is not None else world.speciate_all()
    mu = [world.chambers[i].mu_hac_over_RT(specs[i]) for i in range(len(world.chambers))]
    j = _face_fluxes(world, specs)
    margins = []
    for k, m in enumerate(world.membranes):
        if j[k] == 0.0:
            margins.append(0.0)
            continue
        dmu = mu[m.tail] - mu[m.head]
        # c_HAc[tail] > c_HAc[head]  <=>  j > 0  <=>  mu[tail] > mu[head] (mu monotone in c): product >= 0.
        margins.append(float(j[k] * dmu) if math.isfinite(dmu) else (0.0 if j[k] == 0.0 else math.inf))
    return float(min(margins)) if margins else math.inf


def _one_substep(world: ChamberWorld, h: float, step_index: int, policy: str) -> tuple:
    """Apply a single explicit-Euler neutral-HAc transfer of duration h and re-equilibrate.  Returns (new_world,
    ledger_entries).  Fails closed (ChamberError) if the step would export more HAc than a donor holds or drive a
    total negative -- that is the caller's signal to reduce dt / substep, never a silent truncation."""
    specs = world.speciate_all()
    j = _face_fluxes(world, specs)
    n = len(world.chambers)
    delta = np.zeros(n)                                   # net acetate change per cell this substep (mol)
    outflow = np.zeros(n)                                 # acetate leaving each cell (mol) -- the HAc-availability bound
    entries = []
    for k, m in enumerate(world.membranes):
        amt = float(j[k] * h)                             # mol tail -> head
        delta[m.tail] -= amt
        delta[m.head] += amt
        if amt > 0:
            outflow[m.tail] += amt
        elif amt < 0:
            outflow[m.head] += -amt
        entries.append(TransferLedgerEntry(face=k, tail=m.tail, head=m.head, amount_mol=amt, flux_mol_per_s=float(j[k])))
    # falsifier #14: cannot export more neutral acid than the donor holds, and no total may go negative.
    n_hac = np.array([world.chambers[i].n_hac_mol(specs[i]) for i in range(n)])
    new_acetate = np.array([world.chambers[i].n_acetate_mol for i in range(n)]) + delta
    for i in range(n):
        if outflow[i] > n_hac[i] * (1.0 + AVAILABILITY_RTOL) + TRANSFER_NEGATIVE_ATOL_MOL:
            raise ChamberError(
                f"substep would export {outflow[i]:g} mol HAc from cell {i} but it holds only {n_hac[i]:g} mol "
                f"(policy={policy!r}); reduce dt or substep")
        if new_acetate[i] < -TRANSFER_NEGATIVE_ATOL_MOL:
            raise ChamberError(f"substep would drive cell {i} total acetate negative ({new_acetate[i]:g} mol)")
    new_acetate = np.clip(new_acetate, 0.0, None)         # clip roundoff-level negatives; sodium is NEVER touched
    new_chambers = tuple(world.chambers[i].with_components(n_acetate_mol=new_acetate[i]) for i in range(n))
    new_world = replace(world, chambers=new_chambers)
    new_world.speciate_all()                              # re-equilibrate (fail closed if any local solve is refused)
    return new_world, entries


def step(world: ChamberWorld, dt: float, *, step_index: int = 0, policy: str = "raise") -> tuple:
    """Advance the world by dt with the essential state transition (see module docstring).  policy='raise' (default)
    refuses a dt that would over-export neutral acid; policy='substep' consumes dt in an ADAPTIVE sequence of smaller
    transfers, re-equilibrating between.  Returns (new_world, ledger)."""
    if not (math.isfinite(dt) and dt >= 0):
        raise InvalidParameterError("dt must be finite and >= 0")
    if dt == 0.0 or not world.membranes:
        return world, ()
    if policy == "raise":
        world, entries = _one_substep(world, dt, step_index, policy)
        return world, tuple(entries)
    if policy != "substep":
        raise InvalidParameterError(f"unknown policy {policy!r} (expected 'raise' or 'substep')")
    # ADAPTIVE substep (Wave F fix).  transport_dt_max is a single-STATE bound, so sizing the substep count ONCE from
    # the initial speciation is unsafe on a heterogeneous multi-cell world: a cell that starts empty of HAc does not
    # enter the bound, then fills and would over-export under a fixed step size (evil-morty Finding 1, reproduced even
    # for a MODERATE g-ratio).  Instead consume dt in chunks, RE-EVALUATING the bound on the CURRENT re-equilibrated
    # world each chunk (h = min(remaining, dt_max) <= dt_max), so no substep over-exports and the sequence COMPLETES
    # for any non-stiff world.  A genuinely stiff world (a face that empties a cell far faster than dt_max resolves)
    # would need unboundedly many chunks: that fails CLOSED -- early, via the budget check -- rather than silently
    # grinding or over-exporting.
    ledger = []
    remaining = dt
    for _ in range(MAX_SUBSTEPS):
        if remaining <= 0.0:
            return world, tuple(ledger)
        dt_max = world.transport_dt_max()
        if math.isfinite(dt_max) and dt_max > 0.0 and remaining / dt_max > MAX_SUBSTEPS:
            raise ChamberError(
                f"transport too stiff for explicit substepping: would need > {MAX_SUBSTEPS} substeps (remaining "
                f"{remaining:g} s, current dt_max {dt_max:g} s); reduce dt or the face conductances")
        h = remaining if (not math.isfinite(dt_max) or remaining <= dt_max) else dt_max
        world, entries = _one_substep(world, h, step_index, policy)
        ledger.extend(entries)
        remaining -= h
    raise ChamberError(
        f"substep did not consume dt within MAX_SUBSTEPS={MAX_SUBSTEPS} (remaining {remaining:g} s); the transport "
        "is too stiff for explicit substepping at this dt -- reduce dt or the face conductances")


def run(world: ChamberWorld, dt: float, n_steps: int, *, policy: str = "raise", schedule: Optional[dict] = None,
        presenter=None, calls_per_tick: int = 0) -> list:
    """Evolve the world for n_steps of dt, returning the trajectory [ChamberState, ...] (length n_steps+1, the first
    is the initial condition).  ``schedule`` maps a tick index to {face: valve} valve changes applied BEFORE that
    tick's step (a recorded model input).  ``presenter`` + ``calls_per_tick`` exercise the renderer-disabled
    invariant: the trajectory is byte-identical for calls_per_tick = 0, 1, or many (falsifier #15)."""
    if n_steps < 0:
        raise InvalidParameterError("n_steps must be >= 0")
    schedule = {int(k): dict(v) for k, v in (schedule or {}).items()}
    traj = [ChamberState(world=world, tick=0, time_s=0.0, specs=world.speciate_all(), ledger=())]
    _present(presenter, traj[-1], calls_per_tick)
    t = 0.0
    for k in range(n_steps):
        if k in schedule:
            for face, valve in schedule[k].items():
                world = world.set_valve(int(face), float(valve))
        world, ledger = step(world, dt, step_index=k, policy=policy)
        t += dt
        traj.append(ChamberState(world=world, tick=k + 1, time_s=t, specs=world.speciate_all(), ledger=ledger))
        _present(presenter, traj[-1], calls_per_tick)
    return traj


def _present(presenter, state: "ChamberState", calls: int) -> None:
    """Call a (read-only) presenter ``calls`` times.  A presenter touches nothing authoritative; this exists only to
    PROVE that -- the trajectory must not depend on how often (or whether) a state is rendered."""
    if presenter is None:
        return
    for _ in range(max(0, int(calls))):
        presenter(state)


# --------------------------------------------------------------------------------------------- conservation audit
def conservation_report(before: ChamberWorld, after: ChamberWorld) -> dict:
    """The closed-world balance across a transport step: change in GLOBAL totals (should be ~0 -- internal transport
    conserves), and the per-cell sodium change (should be EXACTLY 0 -- the membrane admits no sodium)."""
    d = after.totals() - before.totals()
    sodium_moved = float(np.max(np.abs(
        np.array([a.n_sodium_mol for a in after.chambers]) - np.array([b.n_sodium_mol for b in before.chambers]))))
    return {
        "global_acetate_drift_mol": float(abs(d[0])),
        "global_sodium_drift_mol": float(abs(d[1])),
        "max_per_cell_sodium_change_mol": sodium_moved,
        "conserves": bool(abs(d[0]) <= CONSERVATION_ATOL_MOL and abs(d[1]) <= CONSERVATION_ATOL_MOL
                          and sodium_moved <= CONSERVATION_ATOL_MOL),
    }


# --------------------------------------------------------------------------------------------- flagship worlds (C4)
def _molar_to_mol(conc_M: float, volume_m3: float) -> float:
    return conc_M * volume_m3 * LITRES_PER_M3


def make_chamber(*, acetate_M: float, sodium_M: float, volume_m3: float = 1.0e-6, activity_model: str = "davies",
                 include_ion_pair: bool = False, temperature_K: float = 298.15) -> Chamber:
    """Build a Chamber from molar concentrations and a volume (default 1 mL) -- the convenient scenario constructor."""
    return Chamber(n_acetate_mol=_molar_to_mol(acetate_M, volume_m3), n_sodium_mol=_molar_to_mol(sodium_M, volume_m3),
                   volume_m3=volume_m3, temperature_K=temperature_K, activity_model=activity_model,
                   include_ion_pair=include_ion_pair)


def two_chamber_world(*, left: Chamber, right: Chamber, g_HAc_m3_per_s: float = 1.0e-9, valve: float = 1.0
                      ) -> ChamberWorld:
    """Two chambers joined by one HAc-selective membrane (0 -> 1).  A shut valve (or g=0) is an impermeable wall."""
    return ChamberWorld(chambers=(left, right), membranes=(Membrane(0, 1, g_HAc_m3_per_s, valve),))
