"""OPERATION XV Wave C (P2) -- the general COUPLED reactive world.

Wave A gave a single-compartment kinetic carrier (dn/dt = N r + q, conservation E N = 0 proven exactly).  Wave B
gave the fast-equilibrium operator g(n) = 0 as a second operator KIND, with the verified aqueous solver composing in
through an adapter.  Wave C couples MANY compartments -- a solid/liquid/gas/two-cell world -- by (a) transport across
typed interfaces, (b) external boundaries (open feeds and fixed-activity reservoirs), and (c) per-compartment fast
equilibrium -- and evolves the whole thing with a GENERIC operator-split integrator that holds NO specific chemistry.

THE ARCHITECTURAL GATE (the only thing this module *claims* to establish): a coupled world is DECLARED (compartments,
interfaces, boundaries) and advanced by one integrator whose code never mentions acetate, CO2, or diffusion of any
particular species.  Two unrelated coupled systems -- a synthetic two-cell reaction-diffusion network and an acetate
buffer under an acetic-acid feed with a fast-equilibrium projection -- run through the SAME ``CoupledWorld.integrate``
with no edit to the integrator.  That, and exact conservation, and a MEASURED splitting error, are what is proven.

OPERATOR SPLITTING, AND WHY ITS ERROR IS MEASURED NOT HIDDEN
------------------------------------------------------------
The world's generator is a sum of operators that do not commute: reaction R (within each compartment), transport T
(across interfaces + feeds), and -- where declared -- a fast-equilibrium projection P (algebraic, per compartment).
Advancing exp(dt (R + T)) is replaced by a SPLIT product, which is only approximate because [R, T] != 0:

    Lie (first order) :  phi_dt  =  R(dt) . T(dt)                 . P      local error O(dt^2), global O(dt^1)
    Strang (2nd order):  phi_dt  =  R(dt/2) . T(dt) . R(dt/2)     . P      local error O(dt^3), global O(dt^2)

The equilibrium projection P is an instantaneous algebraic map (not a time-dt flow), applied once per macro-step after
the continuous operators -- the sequential non-iterative approach (SNIA) standard in reactive-transport codes; its
coupling to R, T is first-order regardless of the R/T scheme, and this is stated, never papered over.  For the pure-
kinetic case (no P) the split is between the two FLOWS R and T, where Lie/Strang orders are classical and testable.

``splitting_convergence`` MEASURES the global splitting error of each scheme against a MONOLITHIC reference (R and T
integrated together, no split, tight tolerance) and fits the observed order from the error-vs-dt slope.  A claim that
"Strang is second order here" is therefore a measured fact about this system, with the number attached -- and the
experiment is only meaningful because R and T are chosen NOT to commute (verified: the Lie error is nonzero and larger
than Strang at equal dt).  A commuting pair would make the split exact and prove nothing (a-control-must-discriminate).

CONSERVATION IN THE COUPLED WORLD
---------------------------------
Each sub-operator conserves, so the composition conserves:
  * R conserves every element and charge in each compartment (Wave A: E N = 0, proven exactly).
  * T is conservative BY CONSTRUCTION: an interface may transfer only between two species of IDENTICAL elemental
    composition and charge (differing at most in name/phase -- CO2(g) <-> CO2(aq), or A in cell 0 <-> A in cell 1);
    what leaves compartment a (-J) enters compartment b (+J), so every global element/charge total is untouched.  A
    transfer that would change chemical identity is a REACTION and belongs inside a compartment, not on an interface
    -- an interface between mismatched species is REFUSED (fail-closed).
  * A feed boundary adds q (mol/s) to one species; the global totals then change by EXACTLY integral(E q dt), and the
    ledger is verified independently (the measured inventory change vs the integrated boundary flux, not a tautology).
  * A fixed-activity boundary and a fast-equilibrium implicit-solvent reservoir EXCHANGE material with an external
    reservoir; the elements they touch are declared ``reservoir_components`` and are NOT claimed conserved -- their net
    exchange is ledgered and reported.  Every OTHER element/charge is globally invariant and asserted so.

So the global conservation gate asserts exact invariance on every non-reservoir component, closes the feed ledger, and
reports (never hides) the reservoir exchange.  The trajectory's evidential tier is DERIVED from these measured checks
and capped at STRUCTURALLY_CONSERVING, weakest-premise'd with every compartment's declared kinetic tier (Wave A/1E
discipline): a coupled prediction is never stronger than its least-verified piece.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp

from experiments.sandbox_foundation.claim_tiers import (
    REFUSED,
    STRUCTURALLY_CONSERVING,
    rank,
    weakest,
)
from experiments.sandbox_foundation.general_equilibrium import EquilibriumOperator
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    KernelError,
    Species,
)


class CoupledError(KernelError):
    """Fail-closed error for the general coupled world."""


# ----------------------------------------------------------------------------- fast-equilibrium coupling
@dataclass(frozen=True)
class EquilibriumCoupling:
    """Attach a Wave B EquilibriumOperator to a compartment as its fast-equilibrium projection P.

    ``species_table`` maps each operator species NAME (its wire identity) to the kernel Species object the coupled
    world tracks -- the explicit adapter bridge the Wave B docstring promised Wave C would build (no second identity
    system is invented; the names are mapped once, here).  ``reservoir_components`` are the elements/charge the
    operator exchanges with its implicit solvent reservoir (for the acetate-water operator: H, O and charge are set by
    the water autodissociation + electroneutrality against an implicit water reservoir, so they are NOT conserved over
    the explicit species); every other element the species carry (here C and Na) IS conserved by the projection and is
    asserted invariant by the coupled world."""
    operator: EquilibriumOperator
    species_table: dict               # {operator_species_name: kernel Species}
    reservoir_components: frozenset = frozenset()   # elements/"charge" exchanged with the implicit reservoir

    def __post_init__(self):
        if not isinstance(self.operator, EquilibriumOperator):
            raise CoupledError("EquilibriumCoupling.operator must be an EquilibriumOperator")
        if type(self.species_table) is not dict or not self.species_table:
            raise CoupledError("species_table must be a non-empty {operator_species_name: Species} dict")
        missing = [nm for nm in self.operator.species if nm not in self.species_table]
        if missing:
            raise CoupledError(f"species_table is missing operator species {missing}")
        for nm, sp in self.species_table.items():
            if nm not in self.operator.species:
                raise CoupledError(f"species_table names {nm!r} which the operator does not produce")
            if type(sp) is not Species:
                raise CoupledError(f"species_table[{nm!r}] must be a Species")
        if type(self.reservoir_components) is not frozenset:
            object.__setattr__(self, "reservoir_components", frozenset(self.reservoir_components))


@dataclass(frozen=True)
class Compartment:
    """A named control volume: its own kernel ChemicalSystem (species/reactions/volume) and an optional fast
    equilibrium.  The compartment's reactions run as the R operator within this volume; transport and boundaries act
    on its inventory from outside; the projection (if any) re-speciates it after the continuous step."""
    name: str
    system: ChemicalSystem
    equilibrium: object = None        # EquilibriumCoupling or None

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise CoupledError("a Compartment needs a non-empty name")
        if type(self.system) is not ChemicalSystem:
            raise CoupledError("Compartment.system must be a ChemicalSystem")
        if self.equilibrium is not None:
            if type(self.equilibrium) is not EquilibriumCoupling:
                raise CoupledError("Compartment.equilibrium must be an EquilibriumCoupling or None")
            for nm, sp in self.equilibrium.species_table.items():
                if sp not in self.system._index:
                    raise CoupledError(f"equilibrium species {nm!r} ({sp.name!r}) is not in compartment {self.name!r}")
            labels = set(self.system.component_labels)
            bad = [c for c in self.equilibrium.reservoir_components if c not in labels]
            if bad:
                raise CoupledError(f"reservoir_components {bad} are not components of compartment {self.name!r} "
                                   f"(have {sorted(labels)})")


@dataclass(frozen=True)
class InterfaceTransfer:
    """A conservative transport flux between two compartments: J_{a->b} = k_transfer * (c_a - partition * c_b) (mol/s),
    with c = n/V the concentration in each compartment.  At the flux zero, c_a = partition * c_b -- the declared
    interface equilibrium (partition = 1 for simple diffusion toward equal concentration; partition encodes a Henry /
    distribution ratio for a phase boundary).  ``species_a`` and ``species_b`` MUST have identical elemental
    composition and charge (only name/phase may differ) so the transfer conserves every element and charge globally;
    an identity-changing transfer is a reaction, not an interface, and is refused at world construction."""
    name: str
    a: str                            # compartment name (source side for a positive flux)
    b: str                            # compartment name (sink side for a positive flux)
    species_a: Species
    species_b: Species
    k_transfer: float                 # L/s (volumetric mass-transfer coefficient); >= 0
    partition: float = 1.0            # dimensionless c_a/c_b at interface equilibrium; > 0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise CoupledError("an InterfaceTransfer needs a non-empty name")
        if self.a == self.b:
            raise CoupledError(f"interface {self.name!r} connects compartment {self.a!r} to itself")
        if type(self.species_a) is not Species or type(self.species_b) is not Species:
            raise CoupledError("species_a and species_b must be Species")
        if self.species_a.composition != self.species_b.composition or self.species_a.charge != self.species_b.charge:
            raise CoupledError(
                f"interface {self.name!r} transfers between species of different composition/charge "
                f"({self.species_a.name!r} {self.species_a.composition} q={self.species_a.charge} vs "
                f"{self.species_b.name!r} {self.species_b.composition} q={self.species_b.charge}); a transfer that "
                f"changes chemical identity is a reaction, not an interface")
        if isinstance(self.k_transfer, bool) or not (isinstance(self.k_transfer, (int, float))
                                                     and math.isfinite(self.k_transfer) and self.k_transfer >= 0):
            raise CoupledError("k_transfer must be a finite L/s coefficient >= 0")
        if isinstance(self.partition, bool) or not (isinstance(self.partition, (int, float))
                                                    and math.isfinite(self.partition) and self.partition > 0):
            raise CoupledError("partition must be a finite ratio > 0")


@dataclass(frozen=True)
class ExternalBoundary:
    """An open-system exchange with the world's exterior, acting on one species of one compartment.

    mode == "feed":            adds a constant q = ``rate`` (mol/s) to the species (q may be negative = removal).  The
                               elements it carries change by exactly integral(E q dt); the feed ledger verifies that.
    mode == "fixed_activity":  a Dirichlet reservoir holding the species at concentration ``target_conc`` (mol/L) via
                               J = k_transfer * (target_conc - c) (mol/s into the compartment).  The elements it
                               carries are reservoir-coupled (NOT claimed conserved); the net exchange is ledgered."""
    name: str
    compartment: str
    species: Species
    mode: str                         # "feed" | "fixed_activity"
    rate: float = 0.0                 # feed: mol/s (signed)
    k_transfer: float = 0.0           # fixed_activity: L/s
    target_conc: float = 0.0          # fixed_activity: mol/L

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise CoupledError("an ExternalBoundary needs a non-empty name")
        if type(self.species) is not Species:
            raise CoupledError("ExternalBoundary.species must be a Species")
        if self.mode == "feed":
            if isinstance(self.rate, bool) or not (isinstance(self.rate, (int, float)) and math.isfinite(self.rate)):
                raise CoupledError("feed rate must be a finite mol/s value")
        elif self.mode == "fixed_activity":
            if isinstance(self.k_transfer, bool) or not (isinstance(self.k_transfer, (int, float))
                                                         and math.isfinite(self.k_transfer) and self.k_transfer >= 0):
                raise CoupledError("fixed_activity k_transfer must be a finite L/s coefficient >= 0")
            if isinstance(self.target_conc, bool) or not (isinstance(self.target_conc, (int, float))
                                                          and math.isfinite(self.target_conc) and self.target_conc >= 0):
                raise CoupledError("fixed_activity target_conc must be a finite mol/L value >= 0")
        else:
            raise CoupledError("ExternalBoundary.mode must be 'feed' or 'fixed_activity'")


@dataclass(frozen=True)
class CoupledReceipt:
    """DERIVED, non-self-certifying evidence for a coupled trajectory (Wave A/1E discipline, lifted to the world)."""
    solver_completed: bool
    positivity_held: bool
    conserved_components_held: bool       # every NON-reservoir element/charge invariant within tolerance
    feed_ledger_closed: bool              # measured inventory change == integrated feed flux
    max_conserved_drift: float            # max |global E n(t) - E n0| over non-reservoir components
    feed_ledger_residual: float           # max |measured change - integrated flux| over fed components
    min_inventory: float
    tolerance: float
    scheme: str
    structural_tier: str                  # STRUCTURALLY_CONSERVING if every check passed, else REFUSED
    declared_kinetic_tier: str            # weakest declared tier over all compartments' rate laws
    admitted_tier: str                    # DERIVED = weakest(structural_tier, declared_kinetic_tier)
    reservoir_exchange: dict = field(default_factory=dict)   # {component: net moles exchanged with a reservoir}
    notes: tuple = ()


@dataclass(frozen=True)
class CoupledTrajectory:
    """A coupled-world trajectory: the sampled times, per-compartment inventory series, and the receipt."""
    times: tuple
    compartments: tuple                   # compartment names, in slot order
    amounts: dict                         # {compartment_name: (per-time {Species: mol}, ...)}
    component_labels: tuple               # the UNION of element names + "charge" over all compartments
    scheme: str
    steps: int
    max_conserved_drift: float
    feed_ledger_residual: float
    min_amount: float
    solver_success: bool
    receipt: CoupledReceipt
    tier: str
    caveats: tuple = ()


class CoupledWorld:
    """A declared coupled world + its generic operator-split integrator.

    Build it from compartments, interfaces and boundaries; it validates every reference and the interface conservation
    gate at construction.  ``integrate`` advances it by Lie or Strang splitting; ``monolithic`` (no split) is available
    only when no compartment carries a fast-equilibrium projection (then the world is a pure ODE and can be integrated
    without splitting -- the reference for the convergence study)."""

    def __init__(self, compartments: list, interfaces: list = (), boundaries: list = ()):
        if not compartments or any(type(c) is not Compartment for c in compartments):
            raise CoupledError("compartments must be a non-empty list of Compartment")
        names = [c.name for c in compartments]
        if len(set(names)) != len(names):
            raise CoupledError("duplicate compartment name")
        self.compartments = list(compartments)
        self._comp = {c.name: c for c in compartments}
        self.interfaces = list(interfaces)
        self.boundaries = list(boundaries)

        for iface in self.interfaces:
            if type(iface) is not InterfaceTransfer:
                raise CoupledError("interfaces must be InterfaceTransfer objects")
            for side, sp in ((iface.a, iface.species_a), (iface.b, iface.species_b)):
                if side not in self._comp:
                    raise CoupledError(f"interface {iface.name!r} references unknown compartment {side!r}")
                if sp not in self._comp[side].system._index:
                    raise CoupledError(f"interface {iface.name!r} references species {sp.name!r} absent from "
                                       f"compartment {side!r}")
        for b in self.boundaries:
            if type(b) is not ExternalBoundary:
                raise CoupledError("boundaries must be ExternalBoundary objects")
            if b.compartment not in self._comp:
                raise CoupledError(f"boundary {b.name!r} references unknown compartment {b.compartment!r}")
            if b.species not in self._comp[b.compartment].system._index:
                raise CoupledError(f"boundary {b.name!r} references species {b.species.name!r} absent from "
                                   f"compartment {b.compartment!r}")

        # global slot layout: (compartment_name, Species) in a fixed order
        self._slots = [(c.name, sp) for c in self.compartments for sp in c.system.species]
        self._slot = {key: i for i, key in enumerate(self._slots)}
        self.n_slots = len(self._slots)

        # the union of components (elements + charge), and which are reservoir-coupled by SOME compartment
        comp_labels = set()
        reservoir = set()
        for c in self.compartments:
            comp_labels.update(c.system.component_labels)
            if c.equilibrium is not None:
                reservoir.update(c.equilibrium.reservoir_components)
        self.component_labels = tuple(sorted(lab for lab in comp_labels if lab != "charge")) + \
            (("charge",) if "charge" in comp_labels else ())
        self.reservoir_components = frozenset(reservoir)
        self.conserved_components = tuple(c for c in self.component_labels if c not in self.reservoir_components)

        # global component matrix E_glob (component x slot): element/charge content of each slot's species
        self._Eg = np.zeros((len(self.component_labels), self.n_slots))
        for j, (_cname, sp) in enumerate(self._slots):
            for i, lab in enumerate(self.component_labels):
                self._Eg[i, j] = float(sp.charge) if lab == "charge" else float(sp.count(lab))
        self._has_equilibrium = any(c.equilibrium is not None for c in self.compartments)

    # ---------------------------------------------------------------- state <-> global vector
    def _pack(self, initial: dict) -> np.ndarray:
        for cname, inv in initial.items():
            if cname not in self._comp:
                raise CoupledError(f"initial inventory references unknown compartment {cname!r}")
            for sp in inv:
                if sp not in self._comp[cname].system._index:
                    raise CoupledError(f"initial inventory for {cname!r} references unknown species "
                                       f"{getattr(sp, 'name', sp)!r}")
        y = np.zeros(self.n_slots)
        for j, (cname, sp) in enumerate(self._slots):
            y[j] = float(initial.get(cname, {}).get(sp, 0.0))
        if np.any(y < 0):
            raise CoupledError("initial inventories must be >= 0")
        return y

    def _unpack(self, y: np.ndarray) -> dict:
        out = {c.name: {} for c in self.compartments}
        for j, (cname, sp) in enumerate(self._slots):
            out[cname][sp] = float(y[j])
        return out

    def global_components(self, state) -> dict:
        """E n over the WHOLE world (every compartment): the global element + charge totals."""
        y = state if isinstance(state, np.ndarray) else self._pack(state)
        totals = self._Eg @ y
        return {self.component_labels[i]: float(totals[i]) for i in range(len(totals))}

    # ---------------------------------------------------------------- the three operators
    def _reaction_rhs(self, y: np.ndarray) -> np.ndarray:
        """R: within-compartment reaction only (no transport, no feed).  Reuses each compartment's kernel rate laws."""
        dy = np.zeros_like(y)
        for c in self.compartments:
            sys = c.system
            if not sys.reactions:
                continue
            V = sys.volume_L
            conc = {sp: y[self._slot[(c.name, sp)]] / V for sp in sys.species}
            for k, r in enumerate(sys.reactions):
                r_vol = r.rate_law.evaluate(r, conc)          # mol L^-1 s^-1
                molar = V * r_vol                              # mol/s
                for i, sp in enumerate(sys.species):
                    coeff = sys.N[i, k]
                    if coeff != 0.0:
                        dy[self._slot[(c.name, sp)]] += molar * coeff
        return dy

    def _transport_rhs(self, y: np.ndarray) -> np.ndarray:
        """T: interface fluxes + external boundaries (feed and fixed-activity).  Conservative across interfaces by
        construction; feed/fixed-activity inject or exchange with the exterior."""
        dy = np.zeros_like(y)
        for iface in self.interfaces:
            ia = self._slot[(iface.a, iface.species_a)]
            ib = self._slot[(iface.b, iface.species_b)]
            Va = self._comp[iface.a].system.volume_L
            Vb = self._comp[iface.b].system.volume_L
            J = iface.k_transfer * (y[ia] / Va - iface.partition * y[ib] / Vb)   # mol/s, a -> b
            dy[ia] -= J
            dy[ib] += J
        for b in self.boundaries:
            i = self._slot[(b.compartment, b.species)]
            if b.mode == "feed":
                dy[i] += b.rate
            else:   # fixed_activity
                V = self._comp[b.compartment].system.volume_L
                dy[i] += b.k_transfer * (b.target_conc - y[i] / V)
        return dy

    def _flow(self, y: np.ndarray, which: str, dt: float, rtol: float, atol: float) -> np.ndarray:
        """Integrate one continuous operator ('reaction' | 'transport' | 'both') over [0, dt]."""
        if dt == 0.0:
            return y.copy()
        if which == "reaction":
            def f(_t, s):
                return self._reaction_rhs(s)
        elif which == "transport":
            def f(_t, s):
                return self._transport_rhs(s)
        elif which == "both":
            def f(_t, s):
                return self._reaction_rhs(s) + self._transport_rhs(s)
        else:
            raise CoupledError(f"unknown flow {which!r}")
        sol = solve_ivp(f, (0.0, dt), y, method="BDF", rtol=rtol, atol=atol, t_eval=[dt])
        if not sol.success:
            raise CoupledError(f"{which} sub-integration failed: {sol.message}")
        return sol.y[:, -1]

    def _project(self, y: np.ndarray) -> np.ndarray:
        """P: re-speciate every fast-equilibrium compartment onto g(n) = 0 (instantaneous SNIA projection)."""
        if not self._has_equilibrium:
            return y
        out = y.copy()
        for c in self.compartments:
            if c.equilibrium is None:
                continue
            ec = c.equilibrium
            V = c.system.volume_L
            # re-key the current inventory onto the operator's conserved components via the operator's OWN
            # conservation law (operator.component_totals) -- generic, so the coupled integrator carries no chemistry
            amounts = {nm: out[self._slot[(c.name, sp)]] for nm, sp in ec.species_table.items()}
            totals = ec.operator.component_totals(amounts)
            state = ec.operator.speciate(totals, volume_L=V, temperature_K=298.15)
            for nm, sp in ec.species_table.items():
                out[self._slot[(c.name, sp)]] = state.species_amounts[nm]
        return out

    # ---------------------------------------------------------------- the stepper
    def _step(self, y: np.ndarray, dt: float, scheme: str, rtol: float, atol: float) -> np.ndarray:
        if scheme == "lie":
            y = self._flow(y, "reaction", dt, rtol, atol)
            y = self._flow(y, "transport", dt, rtol, atol)
        elif scheme == "strang":
            y = self._flow(y, "reaction", dt / 2.0, rtol, atol)
            y = self._flow(y, "transport", dt, rtol, atol)
            y = self._flow(y, "reaction", dt / 2.0, rtol, atol)
        elif scheme == "monolithic":
            if self._has_equilibrium:
                raise CoupledError("monolithic integration is undefined when a compartment has a fast-equilibrium "
                                   "projection (the world is a DAE, not an ODE); use lie or strang")
            y = self._flow(y, "both", dt, rtol, atol)
        else:
            raise CoupledError("scheme must be 'lie', 'strang' or 'monolithic'")
        return self._project(y)

    def integrate(self, initial: dict, *, duration: float, n_steps: int, scheme: str = "strang",
                  n_samples: int | None = None, rtol: float = 1e-10, atol: float = 1e-14,
                  declared_kinetic_tier: str | None = None) -> CoupledTrajectory:
        """Advance the coupled world over ``duration`` seconds in ``n_steps`` equal macro-steps of the chosen scheme.

        Every macro-step records the state (or every (n_steps // n_samples)th, if n_samples is given).  Conservation,
        the feed ledger and positivity are MEASURED and the tier DERIVED (capped at STRUCTURALLY_CONSERVING, weakest-
        premise'd with the declared kinetic tier).  Missing kinetics anywhere fail closed (Wave A invariant)."""
        for c in self.compartments:
            miss = [r.name for r in c.system.reactions if r.rate_law is None]
            if miss:
                raise CoupledError(f"compartment {c.name!r} has RATE_UNKNOWN reaction(s) {miss}; refusing to integrate")
        if not (isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0):
            raise CoupledError("duration must be finite and > 0")
        if not (isinstance(n_steps, int) and not isinstance(n_steps, bool) and n_steps >= 1):
            raise CoupledError("n_steps must be an integer >= 1")
        if declared_kinetic_tier is None:
            tiers = [r.rate_law.tier for c in self.compartments for r in c.system.reactions if r.rate_law is not None]
            declared_kinetic_tier = weakest(*tiers) if tiers else STRUCTURALLY_CONSERVING
        rank(declared_kinetic_tier)

        dt = float(duration) / n_steps
        y = self._pack(initial)
        y = self._project(y)                              # project the initial state onto equilibrium if declared
        comp0 = self._Eg @ y

        sample_every = 1 if not n_samples else max(1, n_steps // max(1, n_samples))
        times = [0.0]
        ys = [y.copy()]
        for step in range(1, n_steps + 1):
            y = self._step(y, dt, scheme, rtol, atol)
            if step % sample_every == 0 or step == n_steps:
                times.append(step * dt)
                ys.append(y.copy())

        # feed ledger: the DECLARED constant feed integral (component basis), independent of the trajectory
        feed_rate_comp = np.zeros(len(self.component_labels))
        for b in self.boundaries:
            if b.mode == "feed":
                j = self._slot[(b.compartment, b.species)]
                feed_rate_comp += self._Eg[:, j] * b.rate
        # a fixed-activity boundary EXCHANGES its species' components with an external reservoir (an open sweep/purge),
        # so those components are ledgered, not asserted conserved -- same status as an implicit-solvent reservoir
        fixed_activity_components = set()
        for b in self.boundaries:
            if b.mode == "fixed_activity":
                j = self._slot[(b.compartment, b.species)]
                for i, lab in enumerate(self.component_labels):
                    if self._Eg[i, j] != 0.0:
                        fixed_activity_components.add(lab)
        ledgered = set(self.reservoir_components) | fixed_activity_components
        cons_idx = [i for i, lab in enumerate(self.component_labels) if lab not in ledgered]
        res_idx = [i for i, lab in enumerate(self.component_labels) if lab in ledgered]

        max_conserved_drift = 0.0
        max_feed_residual = 0.0
        min_amount = float("inf")
        for t, yj in zip(times, ys):
            min_amount = min(min_amount, float(yj.min()))
            comp_j = self._Eg @ yj
            change = comp_j - comp0
            for i in cons_idx:
                # a conserved (non-reservoir) component changes ONLY by its feed integral
                resid = abs(change[i] - feed_rate_comp[i] * t)
                max_feed_residual = max(max_feed_residual, resid)
                if feed_rate_comp[i] == 0.0:
                    max_conserved_drift = max(max_conserved_drift, abs(change[i]))
        reservoir_exchange = {}
        if res_idx:
            comp_final = self._Eg @ ys[-1]
            for i in res_idx:
                reservoir_exchange[self.component_labels[i]] = float(comp_final[i] - comp0[i])

        scale = max(1.0, float(np.max(np.abs(comp0))) if comp0.size else 1.0)
        tol = 1e-6 * scale
        pos_tol = max(atol * 100.0, 1e-10)
        positivity_held = min_amount >= -pos_tol
        conserved_components_held = max_conserved_drift <= tol
        feed_ledger_closed = max_feed_residual <= tol
        solver_completed = True
        structural_ok = solver_completed and positivity_held and conserved_components_held and feed_ledger_closed
        structural_tier = STRUCTURALLY_CONSERVING if structural_ok else REFUSED
        admitted_tier = weakest(structural_tier, declared_kinetic_tier)

        notes = ()
        caveats = ()
        if not conserved_components_held:
            caveats += (f"a conserved component drifted by {max_conserved_drift:.3e} > tol {tol:.3e}",)
        if not feed_ledger_closed:
            caveats += (f"the feed ledger did not close (residual {max_feed_residual:.3e} > tol {tol:.3e})",)
        if not positivity_held:
            caveats += (f"an inventory went negative (min {min_amount:.3e})",)
        if ledgered:
            notes += (f"ledgered components {sorted(ledgered)} exchange with an external/implicit reservoir "
                      f"(fast-equilibrium solvent and/or a fixed-activity boundary) and are not claimed conserved; "
                      f"net exchange reported",)

        receipt = CoupledReceipt(
            solver_completed=solver_completed, positivity_held=positivity_held,
            conserved_components_held=conserved_components_held, feed_ledger_closed=feed_ledger_closed,
            max_conserved_drift=max_conserved_drift, feed_ledger_residual=max_feed_residual,
            min_inventory=min_amount, tolerance=tol, scheme=scheme, structural_tier=structural_tier,
            declared_kinetic_tier=declared_kinetic_tier, admitted_tier=admitted_tier,
            reservoir_exchange=reservoir_exchange, notes=notes)

        amounts = {c.name: tuple({sp: float(yj[self._slot[(c.name, sp)]]) for sp in c.system.species} for yj in ys)
                   for c in self.compartments}
        return CoupledTrajectory(
            times=tuple(times), compartments=tuple(c.name for c in self.compartments), amounts=amounts,
            component_labels=self.component_labels, scheme=scheme, steps=n_steps,
            max_conserved_drift=max_conserved_drift, feed_ledger_residual=max_feed_residual, min_amount=min_amount,
            solver_success=solver_completed, receipt=receipt, tier=admitted_tier, caveats=caveats)


def splitting_convergence(world: CoupledWorld, initial: dict, *, duration: float, steps_list: list,
                          schemes: tuple = ("lie", "strang"), rtol: float = 1e-11,
                          atol: float = 1e-14) -> dict:
    """MEASURE the operator-splitting error of each scheme against a MONOLITHIC reference (R and T integrated together,
    no split, tight tolerance), and fit the observed global order from the log-log slope of error vs dt.

    Returns, per scheme: the dt grid, the final-state L-infinity error vs the monolithic reference at each dt, and the
    least-squares fitted order (slope of log(error) vs log(dt)).  This is an HONEST measurement -- the fitted order is
    whatever the numbers say; a scheme whose operators happen to commute would show ~0 error and the experiment would
    be vacuous, so the caller should confirm the Lie error is both nonzero and larger than Strang at equal dt."""
    if world._has_equilibrium:
        raise CoupledError("splitting_convergence needs a monolithic reference, which is undefined with a fast-"
                           "equilibrium projection; run it on the pure-kinetic (reaction+transport) world")
    y0 = world._pack(initial)
    reference = world._flow(y0, "both", float(duration), rtol, atol)     # the un-split truth (tight tolerance)
    out = {"reference_linf": float(np.max(np.abs(reference)))}
    for scheme in schemes:
        dts, errs = [], []
        for n in steps_list:
            traj = world.integrate(initial, duration=duration, n_steps=n, scheme=scheme, n_samples=1,
                                   rtol=rtol, atol=atol)
            # reconstruct the final global vector from the trajectory's last sample
            yf = np.zeros(world.n_slots)
            for j, (cname, sp) in enumerate(world._slots):
                yf[j] = traj.amounts[cname][-1][sp]
            dts.append(float(duration) / n)
            errs.append(float(np.max(np.abs(yf - reference))))
        order = None
        pos = [(d, e) for d, e in zip(dts, errs) if e > 0]
        if len(pos) >= 2:
            ld = np.log(np.array([d for d, _ in pos]))
            le = np.log(np.array([e for _, e in pos]))
            order = float(np.polyfit(ld, le, 1)[0])
        out[scheme] = {"dts": dts, "errors": errs, "fitted_order": order}
    return out
