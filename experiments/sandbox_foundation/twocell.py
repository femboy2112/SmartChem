"""The TWO-CELL UNIVERSE: the smallest falsifiable proof-of-shape for "admitted mechanism drives local physical state".

Ooh yeah, can do!  Everything here is IDEALIZED / SYNTHETIC and says so.  This is NOT a PDE engine and NOT
real laboratory chemistry.  A finite numerical check is NOT a universal proof.

DOMAIN: two adjacent control volumes, cell 0 ("A") and cell 1 ("B"), joined by ONE explicit interface.

UNITS (SI):  volume m^3 | amount mol | concentration mol/m^3 | time s | temperature K (absolute, > 0) |
energy J | power W | heat capacity J/K | diffusivity m^2/s | area m^2 | distance m | conductivity W/(m K).

CONSTITUTIVE MODELS (all declared, all idealized):
* Species transport: Fick's law, two-point finite-volume flux across the interface,
      inflow_into_self [mol/s] = g * (c_other - c_self),   g = D*Area/Distance  [m^3/s],
  i.e. the face flux is a function of the two cell-centre concentrations only (first-order FV).
* Thermal energy: constant heat capacity, U = C*T (J), U's zero is the 0 K reference, no phase change, no
  composition dependence.  T is DERIVED from U; there is no independent T degree of freedom in the State.
  Fourier's law, two-point flux:  Q_into_self [W] = G * (T_other - T_self),  G = k*Area/Distance  [W/K].
* Reaction: elementary mass-action with USER-SUPPLIED rate constants, thermally neutral (dH = 0 declared),
  volume-constant cells, rate r = k_f * prod(c^order_f) - k_r * prod(c^order_r)  [mol/(m^3 s)].

NUMERICAL TREATMENT (positivity / stability / stiffness / error):
* Transport + conduction: explicit (forward) Euler, first order in dt.  For each cell the update is a CONVEX
  COMBINATION of cell/neighbour/reservoir values provided dt <= dt_max = min_i (capacity_i / total_coupling_i)
  (capacity = V_i or C_i).  Under that bound the discrete maximum principle holds => no new extrema, no
  negative concentration, T stays > 0, no oscillation.  Over the bound the step RAISES (policy="raise", default)
  or SUBSTEPS with an explicit flag (policy="substep"); it never silently goes negative.  A last-line guard
  raises NegativeAmountError on any negative amount regardless (e.g. an over-large prescribed outflow).
* Reaction: solved in EXTENT space xi (n = n0 + N xi) so element/charge conservation holds by construction up to
  roundoff; scipy.integrate.solve_ivp with the implicit L-stable Radau method (stiffness-safe), rtol/atol declared
  in SolverSettings.  Rates are evaluated on max(c, 0).  A result in [-pos_tol, 0) is clamped to 0 WITH
  report.clamped=True; below -pos_tol it raises.  Local error is controlled to ~rtol/atol (NOT a proof).
* Composition: Lie (sequential) operator splitting, first order in dt; error vs a monolithic solve is MEASURED.
* Determinism: no RNG anywhere (seed=None); states are immutable; identical inputs give bit-identical outputs.
"""
from __future__ import annotations

import math
from dataclasses import InitVar, dataclass, field
from typing import Callable, Optional, Sequence

import numpy as np
from scipy.integrate import solve_ivp

CELL_NAMES = ("A", "B")
UNITS = {
    "volume": "m^3", "amount": "mol", "concentration": "mol/m^3", "time": "s", "temperature": "K",
    "energy": "J", "power": "W", "heat_capacity": "J/K", "diffusivity": "m^2/s", "area": "m^2",
    "distance": "m", "conductivity": "W/(m K)", "rate": "mol/(m^3 s)",
}
DT_RTOL = 1e-12  # slack on the dt bound so dt == dt_max is admitted despite roundoff


# --------------------------------------------------------------------------------------------- errors
class SandboxError(Exception):
    """Base for every fail-closed refusal in the sandbox."""


class InvalidParameterError(SandboxError, ValueError):
    pass


class TimestepError(SandboxError):
    pass


class NegativeAmountError(SandboxError):
    pass


class NonPhysicalTemperatureError(SandboxError):
    pass


class ConstitutionError(SandboxError):
    """A mechanism whose E.N != 0 (element or charge not balanced)."""


class MissingKineticParameter(SandboxError):
    """A rate parameter was not supplied; the rate is UNKNOWN, never silently zero."""


class InfeasibleExtentError(SandboxError):
    pass


class UndeclaredControllerError(SandboxError):
    pass


def _check_pos(x, name, strict=True):
    ok = isinstance(x, (int, float, np.floating, np.integer)) and math.isfinite(x) and (x > 0 if strict else x >= 0)
    if not ok:
        raise InvalidParameterError(f"{name}={x!r} must be a finite number {'> 0' if strict else '>= 0'}")
    return float(x)


# --------------------------------------------------------------------------------------------- ledger
INTERFACE, EXTERNAL, REACTION, CONTROLLER, RESERVOIR_ACCOUNT = (
    "INTERFACE", "EXTERNAL", "REACTION", "CONTROLLER", "RESERVOIR_ACCOUNT")


@dataclass(frozen=True)
class LedgerEntry:
    """One signed transfer INTO `cell` (positive = gain).  quantity is a species name or "energy"."""
    step: int
    operator: str
    kind: str
    quantity: str
    cell: int
    amount: float
    unit: str
    note: str = ""


@dataclass
class Ledger:
    entries: list = field(default_factory=list)

    def add(self, **kw) -> None:
        self.entries.append(LedgerEntry(**kw))

    def filter(self, *, operator=None, kind=None, quantity=None, cell=None, kinds=None) -> "Ledger":
        out = []
        for e in self.entries:
            if operator is not None and e.operator != operator:
                continue
            if kind is not None and e.kind != kind:
                continue
            if kinds is not None and e.kind not in kinds:
                continue
            if quantity is not None and e.quantity != quantity:
                continue
            if cell is not None and e.cell != cell:
                continue
            out.append(e)
        return Ledger(out)

    def total(self) -> float:
        return math.fsum(e.amount for e in self.entries)


@dataclass
class StepReport:
    operator: str
    step: int
    dt: float
    substeps: int = 1
    substepped: bool = False
    clamped: bool = False
    dt_limit: Optional[float] = None
    extents: dict = field(default_factory=dict)
    solver: Optional[dict] = None
    clamp_residual: float = 0.0  # max |E @ (clip - raw)| from any non-conservative species clip; 0 if none / exact


# --------------------------------------------------------------------------------------------- boundaries
@dataclass(frozen=True)
class SpeciesBoundary:
    """kind: 'closed' | 'prescribed_flow' (external molar flow, mol/s per species, + = INTO the cell)."""
    kind: str = "closed"
    flow_mol_per_s: Optional[tuple] = None

    def __post_init__(self):
        if self.kind not in ("closed", "prescribed_flow"):
            raise InvalidParameterError(f"unknown species boundary kind {self.kind!r}")
        if self.kind == "closed" and self.flow_mol_per_s is not None:
            raise InvalidParameterError("a closed boundary cannot carry a flow")
        if self.kind == "prescribed_flow":
            if self.flow_mol_per_s is None or not all(math.isfinite(x) for x in self.flow_mol_per_s):
                raise InvalidParameterError("prescribed_flow needs finite per-species flows")


@dataclass(frozen=True)
class ThermalBoundary:
    """kind: 'adiabatic' | 'heater' (power_W >= 0 into the cell) | 'reservoir' (fixed T_res via conductance G_res)."""
    kind: str = "adiabatic"
    power_W: float = 0.0
    T_res_K: float = 0.0
    G_res_W_per_K: float = 0.0

    def __post_init__(self):
        if self.kind not in ("adiabatic", "heater", "reservoir"):
            raise InvalidParameterError(f"unknown thermal boundary kind {self.kind!r}")
        if self.kind == "heater":
            _check_pos(self.power_W, "power_W", strict=False)
        if self.kind == "reservoir":
            _check_pos(self.T_res_K, "T_res_K")
            _check_pos(self.G_res_W_per_K, "G_res_W_per_K", strict=False)


# --------------------------------------------------------------------------------------------- mechanism
@dataclass(frozen=True)
class ReactionRate:
    """User-supplied elementary mass-action constants.  None = NOT SUPPLIED => the rate is UNKNOWN (raises)."""
    k_f: Optional[float] = None
    k_r: Optional[float] = None
    reversible: bool = True


@dataclass(frozen=True, eq=False)
class Mechanism:
    """A constitution-balanced mechanism, COMPLEX-primary.

    The authoritative data are the REACTANT complex and the PRODUCT complex: `reactant` and `product` are
    (S x R) NON-NEGATIVE multiplicity matrices (species rows x reaction columns).  The net stoichiometric
    matrix N = product - reactant is a DERIVED projection -- it loses the per-side multiplicities and so is
    NOT an identity authority: A + B -> 2B and A -> B share the net column [-1, +1], and only the complexes
    tell them apart.  Element/charge conservation lives on the net: E @ N = 0 (E's rows are elements + 'charge').

    Mass-action kinetics, evaluated on c clipped to >= 0:
        r_j = k_f,j * prod_i c_i^{order_f[i,j]}   -   k_r,j * prod_i c_i^{order_r[i,j]}   (reverse term iff reversible)
    For an ELEMENTARY reaction (the default) the kinetic orders ARE the complex multiplicities:
    order_f = reactant, order_r = product.  A NON-ELEMENTARY / empirical law (kinetics="empirical") MUST supply
    its own `forward_orders` (and `reverse_orders` if any reaction is reversible); `rate_law_note` records the
    law's validity regime / units.  Orders are NEVER inferred for an empirical law, and NEVER read off the net
    column -- that historical bug silently dropped catalysts (net 0) and autocatalysts (product on both sides).
    `label` says what it IS (SYNTHETIC)."""
    species: tuple
    reactant: np.ndarray
    product: np.ndarray
    element_labels: tuple
    E: np.ndarray
    rates: tuple
    label: str = "SYNTHETIC"
    forward_orders: Optional[np.ndarray] = None
    reverse_orders: Optional[np.ndarray] = None
    kinetics: str = "elementary"
    rate_law_note: str = ""
    validate: InitVar[bool] = True

    def __post_init__(self, validate):
        reactant = np.array(self.reactant, dtype=float)
        product = np.array(self.product, dtype=float)
        E = np.array(self.E, dtype=float)
        S = len(self.species)
        if reactant.ndim != 2 or reactant.shape[0] != S or reactant.shape != product.shape:
            raise InvalidParameterError("reactant and product must both be (S, R) with one row per species")
        R = reactant.shape[1]
        if E.ndim != 2 or E.shape != (len(self.element_labels), S):
            raise InvalidParameterError("E must be (len(element_labels), S)")
        if R != len(self.rates):
            raise InvalidParameterError("one ReactionRate per reaction column is required")
        if np.any(reactant < 0) or np.any(product < 0):
            raise InvalidParameterError("reactant/product are complex multiplicities and must be >= 0 "
                                        "(a NET column is not a complex -- use Mechanism.from_net for a "
                                        "reaction with no species shared across its two sides)")
        N = product - reactant
        if self.kinetics not in ("elementary", "empirical"):
            raise InvalidParameterError(f"unknown kinetics kind {self.kinetics!r}")
        if self.kinetics == "elementary":
            if self.forward_orders is not None or self.reverse_orders is not None:
                raise InvalidParameterError("elementary kinetics take their orders from the complexes; pass "
                                            "kinetics='empirical' to supply forward_orders/reverse_orders")
            order_f, order_r = reactant, product
        else:  # empirical: orders are supplied, never inferred
            if self.forward_orders is None:
                raise InvalidParameterError("empirical kinetics require explicit forward_orders")
            order_f = np.array(self.forward_orders, dtype=float)
            if self.reverse_orders is None:
                if any(rate.reversible for rate in self.rates):
                    raise InvalidParameterError("empirical kinetics with a reversible reaction require reverse_orders")
                order_r = np.zeros_like(order_f)
            else:
                order_r = np.array(self.reverse_orders, dtype=float)
            for nm, o in (("forward_orders", order_f), ("reverse_orders", order_r)):
                if o.shape != (S, R):
                    raise InvalidParameterError(f"{nm} must be (S, R)")
                if np.any(o < 0):
                    raise InvalidParameterError(f"{nm} must be >= 0")
        for arr in (reactant, product, E, N, order_f, order_r):
            arr.setflags(write=False)
        object.__setattr__(self, "reactant", reactant)
        object.__setattr__(self, "product", product)
        object.__setattr__(self, "E", E)
        object.__setattr__(self, "N", N)            # derived; cached read-only for the many N @ xi call sites
        object.__setattr__(self, "order_f", order_f)
        object.__setattr__(self, "order_r", order_r)
        if validate:
            if not np.any(E):  # empty or all-zero E: E @ N == 0 is vacuous -- it certifies conservation of nothing
                raise ConstitutionError("vacuous element inventory (empty or all-zero E) cannot certify conservation")
            res = E @ N
            if np.max(np.abs(res), initial=0.0) != 0.0:  # integer-valued test mechanisms => exact zero demanded
                raise ConstitutionError(f"E.N != 0 (element/charge imbalance):\n{res}")

    @classmethod
    def from_net(cls, species, N, element_labels, E, rates, *, label="SYNTHETIC", forward_orders=None,
                 reverse_orders=None, kinetics="elementary", rate_law_note="", validate=True) -> "Mechanism":
        """Build from a NET stoichiometric matrix.  VALID ONLY when no species appears on both sides of a
        reaction (no catalyst, no autocatalysis): then reactant = max(-N, 0), product = max(N, 0) recover the
        complexes exactly.  A reaction WITH a shared species (e.g. A + B -> 2B) has an ambiguous net column --
        construct Mechanism(species, reactant, product, ...) directly for those."""
        N = np.array(N, dtype=float)
        return cls(species, np.clip(-N, 0.0, None), np.clip(N, 0.0, None), element_labels, E, rates,
                   label=label, forward_orders=forward_orders, reverse_orders=reverse_orders,
                   kinetics=kinetics, rate_law_note=rate_law_note, validate=validate)

    @property
    def n_reactions(self) -> int:
        return self.N.shape[1]

    def constitution_residual(self) -> np.ndarray:
        return self.E @ self.N

    def require_complete(self) -> None:
        for r, rate in enumerate(self.rates):
            for nm, v in (("k_f", rate.k_f), ("k_r", rate.k_r if rate.reversible else 0.0)):
                if v is None:
                    raise MissingKineticParameter(f"reaction {r}: {nm} not supplied; rate is UNKNOWN (never silently 0)")
                _check_pos(v, f"reaction {r} {nm}", strict=False)

    def rate_vector(self, c: np.ndarray) -> np.ndarray:
        """Per-reaction mass-action rate, mol/(m^3 s), on c clipped to >= 0.  Kinetic orders are the
        reactant/product COMPLEX multiplicities (elementary) or the explicit empirical orders -- never the net
        column, so a catalyst (net 0) and an autocatalyst (shared product) keep their rate dependence."""
        self.require_complete()
        c = np.clip(np.asarray(c, dtype=float), 0.0, None)
        r = np.empty(self.n_reactions)
        for j, rate in enumerate(self.rates):
            r[j] = rate.k_f * np.prod(c ** self.order_f[:, j])
            if rate.reversible:
                r[j] -= rate.k_r * np.prod(c ** self.order_r[:, j])
        return r

    def source_density(self, c: np.ndarray) -> np.ndarray:
        """Stoichiometric source N @ r, mol/(m^3 s)."""
        return self.N @ self.rate_vector(c)

    def extent_bounds(self, n: np.ndarray, j: int) -> tuple:
        """(xi_min, xi_max) keeping every amount >= 0 for reaction j alone (limiting-reactant caps)."""
        col = self.N[:, j]
        fwd = min((n[i] / -col[i] for i in range(len(col)) if col[i] < 0), default=math.inf)
        back = min((n[i] / col[i] for i in range(len(col)) if col[i] > 0), default=math.inf)
        return (-back, fwd)

    def apply_extent(self, n: np.ndarray, j: int, xi: float) -> np.ndarray:
        lo, hi = self.extent_bounds(n, j)
        if not (lo <= xi <= hi):
            raise InfeasibleExtentError(f"extent {xi} outside limiting-reactant window [{lo}, {hi}]")
        return n + self.N[:, j] * xi


@dataclass(frozen=True)
class SolverSettings:
    method: str = "Radau"   # implicit, L-stable: stiffness-safe
    rtol: float = 1e-10
    atol: float = 1e-13
    pos_tol: float = 1e-11  # mol: clamp window for roundoff-level negatives
    seed: Optional[int] = None  # no RNG used; recorded for provenance


# --------------------------------------------------------------------------------------------- system + state
@dataclass(frozen=True, eq=False)
class System:
    species: tuple
    volumes_m3: tuple
    heat_capacity_J_per_K: tuple
    diffusivity_m2_per_s: tuple
    area_m2: float
    distance_m: float
    conductivity_W_per_mK: float
    species_boundaries: tuple = (SpeciesBoundary(), SpeciesBoundary())
    thermal_boundaries: tuple = (ThermalBoundary(), ThermalBoundary())
    mechanism: Optional[Mechanism] = None

    def __post_init__(self):
        S = len(self.species)
        if len(self.volumes_m3) != 2 or len(self.heat_capacity_J_per_K) != 2:
            raise InvalidParameterError("exactly two cells")
        for v in self.volumes_m3:
            _check_pos(v, "volume")
        for c in self.heat_capacity_J_per_K:
            _check_pos(c, "heat capacity")
        if len(self.diffusivity_m2_per_s) != S:
            raise InvalidParameterError("one diffusivity per species")
        for d in self.diffusivity_m2_per_s:
            _check_pos(d, "diffusivity", strict=False)
        _check_pos(self.area_m2, "area")
        _check_pos(self.distance_m, "distance")
        _check_pos(self.conductivity_W_per_mK, "conductivity", strict=False)
        for b in self.species_boundaries:
            if b.kind == "prescribed_flow" and len(b.flow_mol_per_s) != S:
                raise InvalidParameterError("prescribed flow needs one entry per species")
        if self.mechanism is not None and tuple(self.mechanism.species) != tuple(self.species):
            raise InvalidParameterError("mechanism species must equal system species")

    @property
    def g(self) -> np.ndarray:
        """Interface mass-transfer coefficient per species, m^3/s."""
        return np.asarray(self.diffusivity_m2_per_s, float) * self.area_m2 / self.distance_m

    @property
    def G(self) -> float:
        """Interface thermal conductance, W/K."""
        return self.conductivity_W_per_mK * self.area_m2 / self.distance_m

    @property
    def inventory_matrix(self) -> np.ndarray:
        return self.mechanism.E if self.mechanism is not None else np.eye(len(self.species))

    def transport_dt_max(self) -> float:
        gmax = float(np.max(self.g, initial=0.0))
        return math.inf if gmax == 0.0 else min(self.volumes_m3) / gmax

    def thermal_dt_max(self) -> float:
        lim = math.inf
        for i in range(2):
            tb = self.thermal_boundaries[i]
            coupling = self.G + (tb.G_res_W_per_K if tb.kind == "reservoir" else 0.0)
            if coupling > 0:
                lim = min(lim, self.heat_capacity_J_per_K[i] / coupling)
        return lim


@dataclass(frozen=True, eq=False)
class State:
    """Immutable (read-only arrays).  Holds amounts and ENERGY; temperature is DERIVED, never stored."""
    n: np.ndarray   # (2, S) mol
    U: np.ndarray   # (2,)  J
    t: float = 0.0  # s

    def __post_init__(self):
        n = np.array(self.n, dtype=float)
        U = np.array(self.U, dtype=float)
        if not (np.all(np.isfinite(n)) and np.all(np.isfinite(U)) and math.isfinite(self.t)):
            raise InvalidParameterError("non-finite state")
        if np.any(n < 0):
            raise NegativeAmountError("negative initial amount")
        n.setflags(write=False)
        U.setflags(write=False)
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "U", U)

    @classmethod
    def make(cls, system: System, n, T_K, t: float = 0.0) -> "State":
        T = np.asarray(T_K, float)
        if T.shape != (2,) or not np.all(np.isfinite(T)) or np.any(T <= 0):
            raise NonPhysicalTemperatureError("temperatures must be finite and > 0 K")
        n = np.asarray(n, float)
        if n.shape != (2, len(system.species)):
            raise InvalidParameterError("n must be (2, S)")
        return cls(n, np.asarray(system.heat_capacity_J_per_K, float) * T, t)

    def temperature(self, system: System) -> np.ndarray:
        return self.U / np.asarray(system.heat_capacity_J_per_K, float)

    def concentration(self, system: System) -> np.ndarray:
        return self.n / np.asarray(system.volumes_m3, float)[:, None]

    def evolve(self, *, n=None, U=None, t=None) -> "State":
        return State(self.n if n is None else n, self.U if U is None else U, self.t if t is None else t)


# --------------------------------------------------------------------------------------------- operators
def diffusive_inflow(coef: float, x_self, x_other, side: int):
    """Two-point flux INTO `self` from its own side's perspective.  Computed per side so the ledger-level
    cancellation J_AB + J_BA == 0 is a real property (IEEE a-b == -(b-a) exactly), not a tautology."""
    return coef * (x_other - x_self)


def _substeps(dt: float, dt_max: float, policy: str, what: str) -> int:
    _check_pos(dt, "dt", strict=False)
    if dt <= dt_max * (1 + DT_RTOL):
        return 1
    if policy == "raise":
        raise TimestepError(f"{what}: dt={dt} exceeds the positivity/monotonicity bound dt_max={dt_max}")
    if policy == "substep":
        return int(math.ceil(dt / dt_max * (1 - DT_RTOL)))
    raise InvalidParameterError(f"unknown dt policy {policy!r}")


def transport_step(system: System, state: State, dt: float, *, policy: str = "raise",
                   flux_fn: Callable = diffusive_inflow, ledger: Optional[Ledger] = None, step: int = 0):
    """Explicit-Euler FV transport of every species across the interface, plus prescribed external flows."""
    dt_max = system.transport_dt_max()
    nsub = _substeps(dt, dt_max, policy, "transport")
    h = dt / nsub
    V = np.asarray(system.volumes_m3, float)
    n = np.array(state.n)
    S = len(system.species)
    for _ in range(nsub):
        c = n / V[:, None]
        inflow = np.zeros((2, S))
        for side in (0, 1):
            inflow[side] = flux_fn(system.g, c[side], c[1 - side], side)  # mol/s into this cell
        ext = np.zeros((2, S))
        for i, b in enumerate(system.species_boundaries):
            if b.kind == "prescribed_flow":
                ext[i] = b.flow_mol_per_s
        n_new = n + h * (inflow + ext)
        if np.any(n_new < 0):
            raise NegativeAmountError("transport step would create a negative amount (refused, nothing clamped)")
        if ledger is not None:
            for s, nm in enumerate(system.species):
                for side in (0, 1):
                    ledger.add(step=step, operator="transport", kind=INTERFACE, quantity=nm, cell=side,
                               amount=h * inflow[side, s], unit="mol", note="A|B face")
                    if ext[side, s] != 0.0:
                        ledger.add(step=step, operator="transport", kind=EXTERNAL, quantity=nm, cell=side,
                                   amount=h * ext[side, s], unit="mol", note="prescribed flow")
        n = n_new
    rep = StepReport("transport", step, dt, nsub, nsub > 1, False, dt_max)
    return state.evolve(n=n), rep


def thermal_step(system: System, state: State, dt: float, *, policy: str = "raise",
                 flux_fn: Callable = diffusive_inflow, ledger: Optional[Ledger] = None, step: int = 0):
    """Explicit-Euler conduction across the interface + heaters + fixed-T reservoirs (each logging its own side)."""
    dt_max = system.thermal_dt_max()
    nsub = _substeps(dt, dt_max, policy, "thermal")
    h = dt / nsub
    C = np.asarray(system.heat_capacity_J_per_K, float)
    U = np.array(state.U)
    for _ in range(nsub):
        T = U / C
        Q = np.zeros(2)
        ext = []
        for side in (0, 1):
            Q[side] += flux_fn(system.G, T[side], T[1 - side], side)  # W into this cell
            tb = system.thermal_boundaries[side]
            if tb.kind == "heater":
                Q[side] += tb.power_W
                ext.append((side, h * tb.power_W, "heater", None))
            elif tb.kind == "reservoir":
                q = tb.G_res_W_per_K * (tb.T_res_K - T[side])
                Q[side] += q
                ext.append((side, h * q, "reservoir", -h * q))
        U_new = U + h * Q
        if np.any(U_new <= 0):
            raise NonPhysicalTemperatureError("conduction step would produce T <= 0 K")
        if ledger is not None:
            for side in (0, 1):
                ledger.add(step=step, operator="thermal", kind=INTERFACE, quantity="energy", cell=side,
                           amount=h * flux_fn(system.G, T[side], T[1 - side], side), unit="J", note="A|B face")
            for side, amt, note, own in ext:
                ledger.add(step=step, operator="thermal", kind=EXTERNAL, quantity="energy", cell=side,
                           amount=amt, unit="J", note=note)
                if own is not None:  # the reservoir's OWN account of the same exchange
                    ledger.add(step=step, operator="thermal", kind=RESERVOIR_ACCOUNT, quantity="energy",
                               cell=side, amount=own, unit="J", note="reservoir own account")
        U = U_new
    return state.evolve(U=U), StepReport("thermal", step, dt, nsub, nsub > 1, False, dt_max)


@dataclass(frozen=True)
class DeclaredController:
    """The ONLY sanctioned way to impose a temperature: an explicit, named external controller."""
    name: str


def apply_controller(system: System, state: State, controller, cell: int, T_target_K: float, *,
                     ledger: Optional[Ledger] = None, step: int = 0) -> State:
    if not isinstance(controller, DeclaredController) or not controller.name:
        raise UndeclaredControllerError("temperature cannot be set independently of energy without a DeclaredController")
    _check_pos(T_target_K, "T_target_K")
    C = system.heat_capacity_J_per_K[cell]
    dE = C * T_target_K - state.U[cell]
    U = np.array(state.U)
    U[cell] += dE
    if ledger is not None:
        ledger.add(step=step, operator="controller", kind=CONTROLLER, quantity="energy", cell=cell,
                   amount=float(dE), unit="J", note=controller.name)
    return state.evolve(U=U)


def reaction_cell(mech: Mechanism, n0: np.ndarray, V: float, dt: float, settings: SolverSettings):
    """Integrate one closed cell over dt in extent space (n = n0 + N xi, so E @ (n - n0) = 0 by construction).
    Returns (n1, xi, clamped, clamp_residual).

    Positivity restoration for a sub-pos_tol integrator overshoot:
      * R == 1: clamp the single EXTENT to its limiting-reactant window, landing the accepted state back in
        n0 + im(N) so conservation stays exact to roundoff (a componentwise species clip would instead leave
        im(N) and silently create matter).  The limiting amount then sits at 0 +/- roundoff, which can be a few
        ulp NEGATIVE when its net coefficient is not a power of two (e.g. 96.73 - 3*(96.73/3) < 0), so the
        roundoff clip below is still applied so State accepts the result.
      * R > 1: a general conservative multi-reaction projection is an LP, deferred (see
        docs/research/V2_0_PHYSICAL_MECHANISM_CONTRACT.md); the componentwise clip below is the fallback.
    Either way the accepted state is clipped to >= 0 and the clip's conservation displacement
    max|E @ (clip - pre)| is RETURNED as clamp_residual -- surfaced, never hidden.  A clip that displaces
    conservation past pos_tol, or an overshoot past -pos_tol before any clamp, FAILS CLOSED."""
    mech.require_complete()
    R = mech.n_reactions
    if dt == 0.0:
        return np.array(n0), np.zeros(R), False, 0.0

    def f(_t, xi):
        return V * mech.rate_vector((n0 + mech.N @ xi) / V)

    sol = solve_ivp(f, (0.0, dt), np.zeros(R), method=settings.method, rtol=settings.rtol, atol=settings.atol)
    if not sol.success:
        raise SandboxError(f"reaction integrator failed: {sol.message}")
    xi = sol.y[:, -1]
    n1 = n0 + mech.N @ xi
    lo = float(np.min(n1, initial=math.inf))
    clamped = False
    clamp_residual = 0.0
    if lo < 0:
        if lo < -settings.pos_tol:
            raise NegativeAmountError(f"reaction produced amount {lo} < -pos_tol")
        if R == 1:
            lo_x, hi_x = mech.extent_bounds(n0, 0)          # window that keeps every amount >= 0 for this reaction
            xi = np.array([min(max(float(xi[0]), lo_x), hi_x)])
            n1 = n0 + mech.N @ xi                            # conservative: back into n0 + im(N)
        n1_pre = n1
        n1 = np.clip(n1_pre, 0.0, None)                     # clip roundoff/limiting negatives so State accepts n1
        clamp_residual = float(np.max(np.abs(mech.E @ (n1 - n1_pre)), initial=0.0))
        if clamp_residual > settings.pos_tol:               # a conservation leak past tolerance is a real failure
            raise NegativeAmountError(
                f"positivity clip displaced element/charge by {clamp_residual} > pos_tol={settings.pos_tol}")
        clamped = True
    return n1, xi, clamped, clamp_residual


def reaction_step(system: System, state: State, dt: float, *, cells: Sequence[int] = (0, 1),
                  settings: SolverSettings = SolverSettings(), ledger: Optional[Ledger] = None, step: int = 0):
    mech = system.mechanism
    if mech is None:
        raise InvalidParameterError("system has no mechanism")
    _check_pos(dt, "dt", strict=False)
    n = np.array(state.n)
    rep = StepReport("reaction", step, dt, solver={"method": settings.method, "rtol": settings.rtol,
                                                   "atol": settings.atol, "pos_tol": settings.pos_tol,
                                                   "seed": settings.seed})
    for i in cells:
        n1, xi, cl, cres = reaction_cell(mech, n[i], system.volumes_m3[i], dt, settings)
        src = n1 - n[i]                     # the ACTUAL accepted transition (incl. any clamp), not the raw N @ xi
        rep.extents[CELL_NAMES[i]] = xi
        rep.clamped = rep.clamped or cl
        rep.clamp_residual = max(rep.clamp_residual, cres)
        if ledger is not None:
            for s, nm in enumerate(system.species):
                ledger.add(step=step, operator="reaction", kind=REACTION, quantity=nm, cell=i,
                           amount=float(src[s]), unit="mol", note=f"SYNTHETIC:{mech.label}")
        n[i] = n1
    return state.evolve(n=n), rep


OPERATORS = {"transport": transport_step, "thermal": thermal_step, "reaction": reaction_step}


@dataclass
class RunResult:
    state: State
    ledger: Ledger
    reports: list


def run(system: System, state0: State, t_end: float, n_steps: int, sequence=("transport", "reaction"), *,
        ledger: Optional[Ledger] = None) -> RunResult:
    """Lie (sequential) splitting: each macro-step applies every operator in `sequence` over the full dt.
    A sequence item is a name or (name, kwargs)."""
    if n_steps < 1:
        raise InvalidParameterError("n_steps >= 1")
    dt = _check_pos(t_end, "t_end") / n_steps
    ledger = Ledger() if ledger is None else ledger
    state, reports = state0, []
    for k in range(n_steps):
        for item in sequence:
            name, kw = (item, {}) if isinstance(item, str) else item
            state, rep = OPERATORS[name](system, state, dt, ledger=ledger, step=k, **kw)
            reports.append(rep)
    return RunResult(state.evolve(t=state0.t + t_end), ledger, reports)


# --------------------------------------------------------------------------------------------- reports / audit
def _pair_sums(ledger: Ledger, kind: str, operator: str):
    groups: dict = {}
    for e in ledger.filter(kind=kind, operator=operator).entries:
        groups.setdefault((e.step, e.quantity), []).append(e.amount)
    return {k: math.fsum(v) for k, v in groups.items()}


def transport_report(ledger: Ledger, operator: str = "transport") -> dict:
    """Built ONLY from the operator's own entries.  interface_residual is J_AB + J_BA (must be exactly 0)."""
    sums = _pair_sums(ledger, INTERFACE, operator)
    ext: dict = {}
    for e in ledger.filter(kind=EXTERNAL, operator=operator).entries:
        ext[e.quantity] = ext.get(e.quantity, 0.0) + e.amount
    return {"interface_residual": max((abs(v) for v in sums.values()), default=0.0), "external": ext}


def reaction_report(ledger: Ledger, mech: Mechanism) -> dict:
    """Built ONLY from reaction entries: max |E @ source| over (step, cell) -> element+charge residual."""
    vec: dict = {}
    idx = {nm: i for i, nm in enumerate(mech.species)}
    for e in ledger.filter(operator="reaction", kind=REACTION).entries:
        vec.setdefault((e.step, e.cell), np.zeros(len(mech.species)))[idx[e.quantity]] += e.amount
    res = max((float(np.max(np.abs(mech.E @ v))) for v in vec.values()), default=0.0)
    return {"element_charge_residual": res}


def audit(system: System, state0: State, state1: State, ledger: Ledger) -> dict:
    """Global balance: change of inventory minus RECORDED external flows.  Interface / reaction terms are
    not in the budget -- they must cancel / conserve on their own, which is exactly what is being tested."""
    idx = {nm: i for i, nm in enumerate(system.species)}
    ext = np.zeros(len(system.species))
    ext_E = 0.0
    for e in ledger.entries:
        if e.kind == EXTERNAL and e.quantity in idx:
            ext[idx[e.quantity]] += e.amount
        elif e.kind in (EXTERNAL, CONTROLLER) and e.quantity == "energy":
            ext_E += e.amount
    M = system.inventory_matrix
    dn = state1.n.sum(axis=0) - state0.n.sum(axis=0)
    inv = M @ (dn - ext)
    return {
        "inventory_residual": float(np.max(np.abs(inv), initial=0.0)),
        "energy_residual": float(state1.U.sum() - state0.U.sum() - ext_E),
        "external_energy_J": ext_E,
        "external_amount_mol": ext,
    }
