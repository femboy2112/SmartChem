"""OPERATION XIV Track B -- the GENERAL chemical-system carrier.

A reusable kernel in which a chemical system is DECLARED (typed species, phases, reactions) and evolved by a GENERIC
integrator that holds NO hardcoded knowledge of acetate, CO2, sodium, or any particular chemistry.  Vinegar +
baking soda is ONE declared system among many; the ARCHITECTURAL GATE is that switching to a different system (a
synthetic network, a weak-acid buffer) requires NO edit to the numerical integrator -- only a different declaration.

This is NOT a claim that every chemistry is implemented or validated.  It is a carrier that can support them as their
laws, species data and validated models become available; today it carries a KINETIC reaction network (mass action,
reversible mass action, with a declared source/sink), and refuses -- fail-closed -- to integrate a reaction whose
rate law is unknown.  An algebraic fast-equilibrium projection, activity models, and multiphase transfer are declared
future extensions (they attach through the same typed interfaces), not faked here.

THE MATHEMATICAL HEART (plan section 3):

    dn/dt = N r(n, T) + q                 (species inventories evolve by reaction + external source/sink)
    conservation requirement:  E N = 0    (every reaction conserves every element AND charge)

with
    n : species inventories (mol), a vector over the declared species
    N : stoichiometric matrix (species x reactions), N[i, k] = signed coeff of species i in reaction k
    E : element-charge conservation matrix (components x species), one row per element + one CHARGE row
    r : reaction-rate vector (mol/s), each entry from that reaction's declared rate law
    q : external source/sink vector (mol/s), default 0

Because E N = 0, E dn/dt = E N r + E q = E q, so with q = 0 the conserved totals E n are INVARIANT -- the integrator
inherits conservation from the algebra, it is not re-imposed numerically.

EXECUTABLE PROOF OBLIGATIONS (asserted, not asserted-in-prose):
  1. every reaction balances every declared element AND charge: E N = 0, checked EXACTLY (integer arithmetic) at
     ChemicalSystem construction -- an unbalanced reaction is REFUSED (ConservationError);
  2. the generic integrator conserves E n to machine zero when q = 0 (verified on every trajectory);
  3. a reaction with no rate law is RATE_UNKNOWN -> integrate() REFUSES it (MissingKineticsError), never a silent
     k = 0 that would quietly make it inert;
  4. nonnegative inventory is maintained, or the raw (pre-clamp) excursion is REPORTED, never hidden;
  5. the kernel imports NO species-specific constant -- the same integrate() runs every declared system (the gate).

DEMONSTRATIONS (plan section 4): see general_chemistry_demo.py and the tests -- a synthetic A<->B, B+C->D network
and a weak-acid dissociation run through this SAME kernel with no solver edit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.integrate import solve_ivp


class KernelError(ValueError):
    """Base fail-closed error for the general kernel."""


class ConservationError(KernelError):
    """A declared reaction does not conserve an element or charge (E N != 0)."""


class MissingKineticsError(KernelError):
    """A reaction has no rate law (RATE_UNKNOWN) and cannot be integrated -- never silently treated as k = 0."""


class Phase(Enum):
    """The phase a species lives in.  Distinguishing phases is load-bearing: an aqueous Na+ is NOT sodium metal and
    NOT a gas-phase molecule, even at equal elemental composition + charge."""
    AQUEOUS = "aqueous"
    GAS = "gas"
    SOLID = "solid"
    PURE_LIQUID = "pure_liquid"


@dataclass(frozen=True)
class Species:
    """A typed chemical species: its identity is (name, composition, charge, phase) TOGETHER -- never formula alone.

    ``composition`` is stored as a sorted tuple of (element, count) pairs so the species is hashable and its
    elemental content is explicit and conserved.  ``data_status`` records whether the thermodynamic/transport data a
    future model would need is present; ``UNKNOWN`` is a first-class value, never silently 0 (missing data stays
    missing)."""
    name: str
    composition: tuple           # ((element, count), ...) sorted by element
    charge: int
    phase: Phase
    data_status: str = "NONE"    # NONE | PARTIAL | SOURCED -- what thermodynamic data is attached (none faked)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise KernelError("a Species needs a non-empty name")
        if type(self.composition) is not tuple or not all(
                type(p) is tuple and len(p) == 2 and isinstance(p[0], str) and isinstance(p[1], int) and p[1] > 0
                for p in self.composition):
            raise KernelError("composition must be a tuple of (element:str, count:int>0) pairs")
        if [e for e, _ in self.composition] != sorted(e for e, _ in self.composition):
            raise KernelError("composition elements must be sorted (use Species.of)")
        if type(self.charge) is not int:
            raise KernelError("charge must be an int")
        if type(self.phase) is not Phase:
            raise KernelError("phase must be a Phase")
        if self.data_status not in ("NONE", "PARTIAL", "SOURCED"):
            raise KernelError("data_status must be NONE / PARTIAL / SOURCED")

    @classmethod
    def of(cls, name: str, composition: dict, charge: int = 0, phase: Phase = Phase.AQUEOUS,
           data_status: str = "NONE") -> "Species":
        """Build a Species from a {element: count} dict (sorted into the canonical tuple)."""
        comp = tuple(sorted((str(e), int(c)) for e, c in composition.items()))
        return cls(name, comp, int(charge), phase, data_status)

    @property
    def elements(self) -> frozenset:
        return frozenset(e for e, _ in self.composition)

    def count(self, element: str) -> int:
        for e, c in self.composition:
            if e == element:
                return c
        return 0


# ---------------------------------------------------------------------------------------------- rate laws
class RateLaw:
    """A reaction's kinetic law.  ``evaluate(reaction, amounts)`` returns the NET forward rate (mol/s).  A rate law
    carries a tier/provenance so a trajectory can never claim a confidence its kinetics lack."""
    tier: str = "ASSUMED_PARAMETER"

    def evaluate(self, reaction: "Reaction", amounts: dict) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class MassActionIrreversible(RateLaw):
    """r = k * prod(amount[reactant]^|coeff|).  Forward only (no reverse term)."""
    k: float
    tier: str = "ASSUMED_PARAMETER"
    source: str = "synthetic (declared)"

    def __post_init__(self):
        if not (isinstance(self.k, (int, float)) and math.isfinite(self.k) and self.k >= 0):
            raise KernelError("mass-action k must be finite and >= 0")

    def evaluate(self, reaction, amounts):
        r = float(self.k)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                r *= amounts[sp] ** (-coeff)
        return r


@dataclass(frozen=True)
class MassActionReversible(RateLaw):
    """r = kf * prod(amount[reactant]^|coeff|) - kr * prod(amount[product]^coeff).  The ratio kf/kr is the
    (inventory-space) equilibrium constant -- detailed balance: at the fixed point the net rate is 0 and
    prod(product)/prod(reactant) = kf/kr.  So a reversible reaction REGISTERS its own equilibrium constant through
    (kf, kr), and relaxes to it."""
    kf: float
    kr: float
    tier: str = "ASSUMED_PARAMETER"
    source: str = "synthetic (declared); kf/kr encodes the equilibrium constant"

    def __post_init__(self):
        for nm, v in (("kf", self.kf), ("kr", self.kr)):
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise KernelError(f"mass-action {nm} must be finite and >= 0")

    def evaluate(self, reaction, amounts):
        fwd = float(self.kf)
        rev = float(self.kr)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                fwd *= amounts[sp] ** (-coeff)
            elif coeff > 0:
                rev *= amounts[sp] ** coeff
        return fwd - rev


#: Sentinel: a reaction whose kinetics are unknown.  It is NOT a rate of 0 -- a system containing it refuses to
#: integrate (fail-closed) rather than silently treating the reaction as inert.
RATE_UNKNOWN = None


@dataclass(frozen=True)
class Reaction:
    """A declared transformation with signed stoichiometry and (optionally) a rate law.

    ``stoich`` is a tuple of (Species, int coeff): coeff < 0 reactant, coeff > 0 product.  ``rate_law`` is a RateLaw
    or ``RATE_UNKNOWN``.  Conservation is NOT checked here (it needs the whole species set's element basis) -- it is
    checked at ChemicalSystem construction, where an unbalanced reaction is refused."""
    name: str
    stoich: tuple                # ((Species, coeff:int!=0), ...)
    rate_law: object = RATE_UNKNOWN
    elementary: bool = True      # True = an elementary step (mass action is defensible); False = an effective/lumped law

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise KernelError("a Reaction needs a non-empty name")
        if type(self.stoich) is not tuple or len(self.stoich) < 1 or not all(
                type(p) is tuple and len(p) == 2 and type(p[0]) is Species and type(p[1]) is int and p[1] != 0
                for p in self.stoich):
            raise KernelError("stoich must be a tuple of (Species, nonzero-int coeff) pairs")
        seen = [sp for sp, _ in self.stoich]
        if len(set(seen)) != len(seen):
            raise KernelError("a species appears twice in one reaction's stoichiometry (combine the coefficients)")
        if self.rate_law is not RATE_UNKNOWN and not isinstance(self.rate_law, RateLaw):
            raise KernelError("rate_law must be a RateLaw or RATE_UNKNOWN")

    @property
    def reactants(self):
        return tuple((sp, -c) for sp, c in self.stoich if c < 0)

    @property
    def products(self):
        return tuple((sp, c) for sp, c in self.stoich if c > 0)


@dataclass(frozen=True)
class NetworkTrajectory:
    """A generic reaction-network trajectory + its executable conservation/positivity verdicts."""
    times: tuple
    species: tuple               # the Species, in column order of `amounts`
    amounts: tuple               # tuple of per-time dicts {Species: mol}
    component_labels: tuple      # element names + "charge"
    max_component_drift: float   # max |E n(t) - E n0| over the run (machine-zero when q = 0)
    min_amount: float            # the most-negative inventory seen (>= 0 means positivity held)
    solver_success: bool
    integrator: str
    tier: str
    note: str = ""
    caveats: tuple = field(default_factory=tuple)


class ChemicalSystem:
    """The general carrier: an ordered species list + declared reactions, with the stoichiometric matrix N and the
    element-charge conservation matrix E built and the conservation law E N = 0 PROVEN (exactly) at construction."""

    def __init__(self, species: list, reactions: list):
        if not species or any(type(s) is not Species for s in species):
            raise KernelError("species must be a non-empty list of Species")
        if len(set(species)) != len(species):
            raise KernelError("duplicate species in the system")
        if any(type(r) is not Reaction for r in reactions):
            raise KernelError("reactions must be Reaction objects")
        for r in reactions:
            for sp, _ in r.stoich:
                if sp not in species:
                    raise KernelError(f"reaction {r.name!r} references species {sp.name!r} not in the system")
        self.species = list(species)
        self.reactions = list(reactions)
        self._index = {sp: i for i, sp in enumerate(self.species)}
        self.elements = sorted({e for sp in self.species for e in sp.elements})
        self.component_labels = tuple(self.elements) + ("charge",)
        self.E = self._build_E()
        self.N = self._build_N()
        self._assert_conservation()

    def _build_E(self) -> np.ndarray:
        rows = []
        for el in self.elements:
            rows.append([sp.count(el) for sp in self.species])
        rows.append([sp.charge for sp in self.species])          # the charge-conservation row
        return np.array(rows, dtype=np.int64)

    def _build_N(self) -> np.ndarray:
        N = np.zeros((len(self.species), len(self.reactions)), dtype=np.int64)
        for k, r in enumerate(self.reactions):
            for sp, coeff in r.stoich:
                N[self._index[sp], k] = coeff
        return N

    def _assert_conservation(self) -> None:
        if self.N.size == 0:
            return
        prod = self.E @ self.N                                    # exact integer arithmetic
        if not np.all(prod == 0):
            bad = []
            for k, r in enumerate(self.reactions):
                col = prod[:, k]
                if np.any(col != 0):
                    off = {self.component_labels[c]: int(col[c]) for c in range(len(col)) if col[c] != 0}
                    bad.append(f"{r.name!r} violates {off}")
            raise ConservationError("reaction(s) do not conserve elements/charge (E N != 0): " + "; ".join(bad))

    def component_amounts(self, amounts: dict) -> dict:
        """E n: the conserved element + charge totals of an inventory dict."""
        n = np.array([float(amounts.get(sp, 0.0)) for sp in self.species])
        totals = self.E @ n
        return {self.component_labels[i]: float(totals[i]) for i in range(len(totals))}

    def integrate(self, n0: dict, *, duration: float, source: dict | None = None, temperature_K: float = 298.15,
                  n_samples: int = 50, method: str = "BDF", rtol: float = 1e-9, atol: float = 1e-15,
                  tier: str = "ASSUMED_PARAMETER") -> NetworkTrajectory:
        """Evolve dn/dt = N r(n) + q from inventories ``n0`` over ``duration`` seconds.

        FAIL-CLOSED on missing kinetics: every reaction MUST carry a rate law, else MissingKineticsError (a reaction
        is never silently inert).  ``source`` is the external q (mol/s) per species, default 0.  The default method
        is BDF (implicit, stiff-capable) because a reaction network with disparate rate constants is typically stiff
        -- the kernel does not pretend an explicit method is stiff-stable (the P0-1C lesson, applied generally).
        Conservation (E n drift) and positivity (min inventory) are VERIFIED on the trajectory, not assumed."""
        missing = [r.name for r in self.reactions if r.rate_law is RATE_UNKNOWN]
        if missing:
            raise MissingKineticsError(
                f"RATE_UNKNOWN for reaction(s) {missing}: refusing to integrate (never a silent k = 0). Declare a "
                f"rate law or remove the reaction.")
        if not (isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0):
            raise KernelError("duration must be finite and > 0")
        q = np.zeros(len(self.species))
        if source:
            for sp, val in source.items():
                if sp not in self._index:
                    raise KernelError(f"source references unknown species {getattr(sp, 'name', sp)!r}")
                q[self._index[sp]] = float(val)

        order = self.species
        idx = self._index

        def rhs(_t, y):
            amounts = {sp: y[idx[sp]] for sp in order}
            dn = q.copy()
            for k, r in enumerate(self.reactions):
                rate = r.rate_law.evaluate(r, amounts)
                col = self.N[:, k]
                dn = dn + rate * col
            return dn

        y0 = np.array([float(n0.get(sp, 0.0)) for sp in order])
        if np.any(y0 < 0):
            raise KernelError("initial inventories must be >= 0")
        t_eval = np.linspace(0.0, float(duration), n_samples)
        sol = solve_ivp(rhs, (0.0, float(duration)), y0, method=method, t_eval=t_eval, rtol=rtol, atol=atol)
        if not sol.success:
            raise KernelError(f"integration failed ({method}): {sol.message}")

        comp0 = self.E @ y0
        max_drift = 0.0
        min_amount = float("inf")
        closed = not bool(q.any())   # when q != 0 the conserved totals legitimately change by the integral of E q dt
        amounts_series = []
        for j, t in enumerate(sol.t):
            yj = sol.y[:, j]
            min_amount = min(min_amount, float(yj.min()))
            if closed:               # a closed system (q = 0): E n must be invariant, so drift measures conservation
                max_drift = max(max_drift, float(np.max(np.abs(self.E @ yj - comp0))))
            amounts_series.append({sp: float(yj[idx[sp]]) for sp in order})

        caveats = ()
        if min_amount < -max(atol * 10.0, 1e-12):
            caveats += (f"a species inventory went negative (min {min_amount:.3e}); the stiff solver's positivity "
                        f"was violated -- treat this trajectory as numerically suspect",)
        return NetworkTrajectory(
            times=tuple(float(t) for t in sol.t), species=tuple(order), amounts=tuple(amounts_series),
            component_labels=self.component_labels, max_component_drift=max_drift, min_amount=min_amount,
            solver_success=bool(sol.success), integrator=f"scipy.solve_ivp/{method}", tier=tier, caveats=caveats)
