"""OPERATION XIV Track B / XV Wave A -- the GENERAL chemical-system carrier.

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
    r : reaction-rate vector (mol/s), each entry V * r_vol from that reaction's declared (concentration-basis) law
    q : external source/sink vector (mol/s), default 0

Because E N = 0, E dn/dt = E N r + E q = E q, so with q = 0 the conserved totals E n are INVARIANT -- the integrator
inherits conservation from the algebra, it is not re-imposed numerically.  With q != 0 the totals change by EXACTLY
the integral of E q, and that ledger is verified independently (XV-1D).

CONCENTRATION / VOLUME BASIS (XV-1C):  a ChemicalSystem owns a first-class positive reactor volume ``volume_L``.
A rate law is written in the textbook CONCENTRATION form and returns a VOLUMETRIC rate r_vol (mol L^-1 s^-1) from
concentrations c_i = n_i / V; the kernel converts to the MOLAR rate r_mol = V * r_vol before applying it to the
inventory ODE.  So for a bimolecular A + B -> C, dn_C/dt = V * k * c_A * c_B = k * n_A * n_B / V -- the conventional
concentration-rate convention, with k carrying order-dependent units (an n-th order k is L^(n-1) mol^-(1-n) s^-1).
The STANDARD STATE for the concentration basis is 1 mol/L with ideal-solution activities taken equal to
concentrations; kf/kr is therefore the CONCENTRATION equilibrium quotient Kc under that ideal standard state, NOT an
activity-based thermodynamic K-degree (the plan's warning: no dimensionless-K claim for arbitrary order/phase).

EXACT CONSERVATION (XV-1A):  E N = 0 is proven with UNBOUNDED PYTHON INTEGERS at construction, never a fixed-width
machine-word product.  A NumPy int64 matrix product can OVERFLOW (e.g. 2^62 A -> 2^62 B with A=4X, B=8X has a true
imbalance of 2^64 that wraps to 0), which would be a FALSE conservation certificate.  The NumPy matrices are kept as
derived EXECUTION artifacts for the float RHS; they are not the authority establishing conservation.

EXECUTABLE PROOF OBLIGATIONS (asserted, not asserted-in-prose):
  1. every reaction balances every declared element AND charge: E N = 0, checked EXACTLY (unbounded Python integer
     arithmetic) at ChemicalSystem construction -- an unbalanced reaction is REFUSED (ConservationError);
  2. the generic integrator conserves E n to machine zero when q = 0, and closes the external ledger
     E (n_final - n0) = integral(E q dt) when q != 0 (both VERIFIED on every trajectory);
  3. a reaction with no rate law is RATE_UNKNOWN -> integrate() REFUSES it (MissingKineticsError), never a silent
     k = 0 that would quietly make it inert;
  4. nonnegative inventory is maintained, or the raw (pre-clamp) excursion is REPORTED, never hidden;
  5. the kernel imports NO species-specific constant -- the same integrate() runs every declared system (the gate);
  6. the trajectory's evidential tier is DERIVED from measured checks (XV-1E), capped at STRUCTURALLY_CONSERVING;
     a caller cannot supply a stronger tier and thereby make an unverified model predictive.

DEMONSTRATIONS (plan section 4): see general_chemistry_demo.py and the tests -- a synthetic A<->B, B+C->D network
and a weak-acid dissociation run through this SAME kernel with no solver edit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.integrate import solve_ivp

from experiments.sandbox_foundation.claim_tiers import (
    ASSUMED_PARAMETER,
    REFUSED,
    STRUCTURALLY_CONSERVING,
    rank,
    weakest,
)


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


def _as_strict_positive_int(value, what: str) -> int:
    """Coerce to a strictly-positive Python int WITHOUT silent float truncation (XV-1B).

    A bool, a non-integer float (1.9), or a value <= 0 is REJECTED rather than quietly repaired -- an element count
    of 1.9 is malformed input, not "1"."""
    if isinstance(value, bool):
        raise KernelError(f"{what} must be a positive integer, not a bool")
    if isinstance(value, int):
        iv = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise KernelError(f"{what} must be an integer (got {value!r}); counts are not silently truncated")
        iv = int(value)
    else:
        raise KernelError(f"{what} must be an integer (got {type(value).__name__})")
    if iv <= 0:
        raise KernelError(f"{what} must be strictly positive (got {iv})")
    return iv


@dataclass(frozen=True)
class Species:
    """A typed chemical species: its identity is (name, composition, charge, phase) TOGETHER -- never formula alone.

    ``composition`` is stored as a sorted tuple of (element, count) pairs with UNIQUE elements (XV-1B), so the species
    is hashable and its elemental content is explicit, canonical and conserved.  ``data_status`` records whether the
    thermodynamic/transport data a future model would need is present; ``NONE`` is a first-class value, never silently
    treated as 0 (missing data stays missing)."""
    name: str
    composition: tuple           # ((element, count), ...) sorted by element, elements unique
    charge: int
    phase: Phase
    data_status: str = "NONE"    # NONE | PARTIAL | SOURCED -- what thermodynamic data is attached (none faked)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise KernelError("a Species needs a non-empty name")
        if type(self.composition) is not tuple or not all(
                type(p) is tuple and len(p) == 2 and isinstance(p[0], str) and p[0].strip()
                and type(p[1]) is int and not isinstance(p[1], bool) and p[1] > 0
                for p in self.composition):
            raise KernelError("composition must be a tuple of (element:str, count:int>0) pairs")
        elems = [e for e, _ in self.composition]
        if elems != sorted(elems):
            raise KernelError("composition elements must be sorted (use Species.of)")
        if len(set(elems)) != len(elems):                     # XV-1B: no duplicate element hiding a larger count
            raise KernelError(f"composition has a duplicate element {sorted({e for e in elems if elems.count(e) > 1})};"
                              f" element counts must be canonical and unique")
        if type(self.charge) is not int or isinstance(self.charge, bool):
            raise KernelError("charge must be an int")
        if type(self.phase) is not Phase:
            raise KernelError("phase must be a Phase")
        if self.data_status not in ("NONE", "PARTIAL", "SOURCED"):
            raise KernelError("data_status must be NONE / PARTIAL / SOURCED")

    @classmethod
    def of(cls, name: str, composition: dict, charge: int = 0, phase: Phase = Phase.AQUEOUS,
           data_status: str = "NONE") -> "Species":
        """Build a Species from a {element: count} dict (sorted into the canonical tuple).  Counts must be strictly
        positive integers -- a float count is rejected, never truncated (XV-1B)."""
        if type(composition) is not dict or not composition:
            raise KernelError("composition must be a non-empty {element: count} dict")
        comp = tuple(sorted((str(e), _as_strict_positive_int(c, f"count for element {e!r}"))
                            for e, c in composition.items()))
        if isinstance(charge, bool) or type(charge) is not int:
            raise KernelError("charge must be an int")
        return cls(name, comp, int(charge), phase, data_status)

    @property
    def elements(self) -> frozenset:
        return frozenset(e for e, _ in self.composition)

    def count(self, element: str) -> int:
        """The (unique, canonical) count of ``element`` in this species; 0 if absent."""
        for e, c in self.composition:
            if e == element:
                return c
        return 0


# ---------------------------------------------------------------------------------------------- rate laws
class RateLaw:
    """A reaction's kinetic law in the CONCENTRATION basis.  ``evaluate(reaction, concentrations)`` returns the NET
    forward VOLUMETRIC rate r_vol (mol L^-1 s^-1) from a {Species: concentration mol/L} map; the kernel multiplies by
    the reactor volume V to obtain the molar rate (XV-1C).  A rate law carries a tier/provenance so a trajectory can
    never claim a confidence its kinetics lack."""
    tier: str = ASSUMED_PARAMETER

    def evaluate(self, reaction: "Reaction", concentrations: dict) -> float:
        raise NotImplementedError

    @staticmethod
    def _reactant_order(reaction: "Reaction") -> int:
        return sum(-coeff for _, coeff in reaction.stoich if coeff < 0)


@dataclass(frozen=True)
class MassActionIrreversible(RateLaw):
    """r_vol = k * prod(c[reactant]^|coeff|)  (mol L^-1 s^-1).  Forward only (no reverse term).

    ``k`` has order-dependent units: for overall reactant order n, k is L^(n-1) mol^(1-n) s^-1 (so r_vol is always
    mol L^-1 s^-1).  ``elementary`` is the caller's declaration that mass action is defensible for this step."""
    k: float
    tier: str = ASSUMED_PARAMETER
    source: str = "synthetic (declared)"

    def __post_init__(self):
        if isinstance(self.k, bool) or not (isinstance(self.k, (int, float)) and math.isfinite(self.k) and self.k >= 0):
            raise KernelError("mass-action k must be finite and >= 0")

    def evaluate(self, reaction, concentrations):
        r = float(self.k)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                r *= concentrations[sp] ** (-coeff)
        return r


@dataclass(frozen=True)
class MassActionReversible(RateLaw):
    """r_vol = kf * prod(c[reactant]^|coeff|) - kr * prod(c[product]^coeff)  (mol L^-1 s^-1).

    The ratio kf/kr is the CONCENTRATION equilibrium quotient Kc -- detailed balance: at the fixed point r_vol = 0 and
    prod(c_product)/prod(c_reactant) = kf/kr.  Kc is defined on the ideal concentration standard state (1 mol/L,
    activities == concentrations); it is NOT the activity-based thermodynamic K-degree, and no such claim is made."""
    kf: float
    kr: float
    tier: str = ASSUMED_PARAMETER
    source: str = "synthetic (declared); kf/kr encodes the concentration equilibrium quotient Kc"

    def __post_init__(self):
        for nm, v in (("kf", self.kf), ("kr", self.kr)):
            if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise KernelError(f"mass-action {nm} must be finite and >= 0")

    def evaluate(self, reaction, concentrations):
        fwd = float(self.kf)
        rev = float(self.kr)
        for sp, coeff in reaction.stoich:
            if coeff < 0:
                fwd *= concentrations[sp] ** (-coeff)
            elif coeff > 0:
                rev *= concentrations[sp] ** coeff
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
                type(p) is tuple and len(p) == 2 and type(p[0]) is Species
                and type(p[1]) is int and not isinstance(p[1], bool) and p[1] != 0
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
class VerificationReceipt:
    """A DERIVED, non-self-certifying evidence receipt for a trajectory (XV-1E).

    Every verification field is a MEASURED fact about the integration; none is caller-supplied.  ``declared_kinetic_
    tier`` is the ONLY caller input -- the honest provenance of the rate laws -- and it can only ever LOWER the
    admitted tier (weakest-premise), never inflate it: ``structural_tier`` caps the kernel at STRUCTURALLY_CONSERVING
    (the bare kernel does no independent-algorithm, reference-solver, or measured-data check), so no declared tier can
    make an unverified model BENCHMARKED/CALIBRATED/PREDICTIVE.  If a check fails the structural tier collapses to
    REFUSED and caps everything there."""
    solver_completed: bool
    positivity_held: bool
    external_ledger_closed: bool          # E (n(t) - n0) == integral(E q dt) within tolerance (reduces to drift when closed)
    conservation_residual: float          # max |E n(t) - E n0| over the run (RAW change; ~0 for a closed system)
    external_ledger_residual: float       # max |E n(t) - E n0 - (E q) t| (LEDGER-closed residual; ~0 closed AND open)
    min_inventory: float
    tolerance: float
    structural_tier: str                  # DERIVED: STRUCTURALLY_CONSERVING if every check passed, else REFUSED
    declared_kinetic_tier: str            # caller INPUT: provenance of the rate laws (default ASSUMED_PARAMETER)
    admitted_tier: str                    # DERIVED AUTHORITY = weakest(structural_tier, declared_kinetic_tier)
    notes: tuple = ()


@dataclass(frozen=True)
class NetworkTrajectory:
    """A generic reaction-network trajectory + its executable conservation/positivity verdicts."""
    times: tuple
    species: tuple               # the Species, in column order of `amounts`
    amounts: tuple               # tuple of per-time dicts {Species: mol}
    component_labels: tuple      # element names + "charge"
    volume_L: float              # the reactor volume the concentration basis used
    max_component_drift: float   # max |E n(t) - E n0| over the run (RAW; machine-zero when q = 0)
    external_ledger_residual: float  # max |E n(t) - E n0 - (E q) t| over the run (LEDGER-closed residual)
    min_amount: float            # the most-negative inventory seen (>= 0 means positivity held)
    solver_success: bool
    integrator: str
    receipt: VerificationReceipt
    tier: str                    # == receipt.admitted_tier (the DERIVED authority), surfaced for display
    note: str = ""
    caveats: tuple = field(default_factory=tuple)


class ChemicalSystem:
    """The general carrier: an ordered species list + declared reactions + a reactor volume, with the stoichiometric
    matrix N and the element-charge conservation matrix E built and the conservation law E N = 0 PROVEN (EXACTLY, in
    unbounded Python integers) at construction."""

    def __init__(self, species: list, reactions: list, volume_L: float = 1.0):
        if not species or any(type(s) is not Species for s in species):
            raise KernelError("species must be a non-empty list of Species")
        if len(set(species)) != len(species):
            raise KernelError("duplicate species in the system")
        if any(type(r) is not Reaction for r in reactions):
            raise KernelError("reactions must be Reaction objects")
        if isinstance(volume_L, bool) or not (isinstance(volume_L, (int, float))
                                              and math.isfinite(volume_L) and volume_L > 0):
            raise KernelError("volume_L must be a finite reactor volume > 0 (litres)")
        for r in reactions:
            for sp, _ in r.stoich:
                if sp not in species:
                    raise KernelError(f"reaction {r.name!r} references species {sp.name!r} not in the system")
        self.species = list(species)
        self.reactions = list(reactions)
        self.volume_L = float(volume_L)
        self._index = {sp: i for i, sp in enumerate(self.species)}
        self.elements = sorted({e for sp in self.species for e in sp.elements})
        self.component_labels = tuple(self.elements) + ("charge",)
        # the EXACT (unbounded-integer) authorities for the conservation proof:
        self._E_int = [[sp.count(el) for sp in self.species] for el in self.elements]
        self._E_int.append([sp.charge for sp in self.species])          # the charge-conservation row
        self._N_int = [[0] * len(self.reactions) for _ in self.species]
        for k, r in enumerate(self.reactions):
            for sp, coeff in r.stoich:
                self._N_int[self._index[sp]][k] = coeff
        self._assert_conservation()                                     # proven (exactly) BEFORE any numpy cast
        # derived EXECUTION artifacts for the float RHS (NOT the conservation authority -- float64 so a genuinely
        # balanced huge-coefficient system, already certified exactly above, does not overflow a C long):
        self.E = np.array(self._E_int, dtype=float)
        self.N = (np.array(self._N_int, dtype=float) if self.reactions
                  else np.zeros((len(self.species), 0), dtype=float))

    def _assert_conservation(self) -> None:
        """Prove E N = 0 with UNBOUNDED PYTHON INTEGERS (XV-1A): a fixed-width int64 product can wrap on large
        coefficients and FALSELY certify an unbalanced reaction.  This product cannot overflow."""
        if not self.reactions:
            return
        ncomp, nsp, nrxn = len(self._E_int), len(self.species), len(self.reactions)
        bad = []
        for k in range(nrxn):
            off = {}
            for c in range(ncomp):
                s = 0
                for i in range(nsp):                                    # pure Python int: exact, no wraparound
                    s += self._E_int[c][i] * self._N_int[i][k]
                if s != 0:
                    off[self.component_labels[c]] = s
            if off:
                bad.append(f"{self.reactions[k].name!r} violates {off}")
        if bad:
            raise ConservationError("reaction(s) do not conserve elements/charge (E N != 0): " + "; ".join(bad))

    def component_amounts(self, amounts: dict) -> dict:
        """E n: the conserved element + charge totals of an inventory dict."""
        for sp in amounts:
            if sp not in self._index:
                raise KernelError(f"component_amounts references unknown species {getattr(sp, 'name', sp)!r}")
        n = np.array([float(amounts.get(sp, 0.0)) for sp in self.species])
        totals = self.E @ n
        return {self.component_labels[i]: float(totals[i]) for i in range(len(totals))}

    def integrate(self, n0: dict, *, duration: float, source: dict | None = None, temperature_K: float = 298.15,
                  n_samples: int = 50, method: str = "BDF", rtol: float = 1e-9, atol: float = 1e-15,
                  declared_kinetic_tier: str = ASSUMED_PARAMETER) -> NetworkTrajectory:
        """Evolve dn/dt = N r(n) + q from inventories ``n0`` over ``duration`` seconds (concentration basis, XV-1C).

        FAIL-CLOSED on missing kinetics: every reaction MUST carry a rate law, else MissingKineticsError.  ``source``
        is the external q (mol/s) per species, default 0 (XV-1D: finite, typed, known species only; the external
        ledger is verified independently).  The default method is BDF (implicit, stiff-capable) because a reaction
        network with disparate rate constants is typically stiff.  Conservation, the external ledger and positivity
        are VERIFIED on the trajectory (XV-1E) and the evidential tier is DERIVED from those checks, never the
        caller's word (``declared_kinetic_tier`` can only lower the admitted tier, never inflate it)."""
        missing = [r.name for r in self.reactions if r.rate_law is RATE_UNKNOWN]
        if missing:
            raise MissingKineticsError(
                f"RATE_UNKNOWN for reaction(s) {missing}: refusing to integrate (never a silent k = 0). Declare a "
                f"rate law or remove the reaction.")
        if not (isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0):
            raise KernelError("duration must be finite and > 0")
        rank(declared_kinetic_tier)                                     # a typo in the declared tier fails loudly
        for sp in n0:                                                   # XV-1D: no unknown initial species silently ignored
            if sp not in self._index:
                raise KernelError(f"initial inventory references unknown species {getattr(sp, 'name', sp)!r}")
        q = np.zeros(len(self.species))
        if source:
            for sp, val in source.items():
                if sp not in self._index:
                    raise KernelError(f"source references unknown species {getattr(sp, 'name', sp)!r}")
                if isinstance(val, bool) or not (isinstance(val, (int, float)) and math.isfinite(val)):
                    raise KernelError(f"source rate for {sp.name!r} must be a finite mol/s value")
                q[self._index[sp]] = float(val)

        order = self.species
        idx = self._index
        V = self.volume_L

        def rhs(_t, y):
            conc = {sp: y[idx[sp]] / V for sp in order}                 # mol/L
            dn = q.copy()
            for k, r in enumerate(self.reactions):
                r_vol = r.rate_law.evaluate(r, conc)                    # mol L^-1 s^-1
                dn = dn + (V * r_vol) * self.N[:, k]                    # molar rate mol/s
            return dn

        y0 = np.array([float(n0.get(sp, 0.0)) for sp in order])
        if np.any(y0 < 0):
            raise KernelError("initial inventories must be >= 0")
        t_eval = np.linspace(0.0, float(duration), n_samples)
        sol = solve_ivp(rhs, (0.0, float(duration)), y0, method=method, t_eval=t_eval, rtol=rtol, atol=atol)
        if not sol.success:
            raise KernelError(f"integration failed ({method}): {sol.message}")

        comp0 = self.E @ y0                                             # conserved totals at t0
        comp_rate = self.E @ q                                          # d(E n)/dt from the external feed (components/s)
        max_drift = 0.0                                                 # RAW change in conserved totals
        max_ledger_residual = 0.0                                       # LEDGER-closed residual (closed AND open)
        min_amount = float("inf")
        amounts_series = []
        for j, t in enumerate(sol.t):
            yj = sol.y[:, j]
            min_amount = min(min_amount, float(yj.min()))
            comp_j = self.E @ yj
            max_drift = max(max_drift, float(np.max(np.abs(comp_j - comp0))))
            # independent ledger: the SOLVER's integrated totals vs the DECLARED feed integral (E q) t -- not a tautology
            max_ledger_residual = max(max_ledger_residual, float(np.max(np.abs(comp_j - comp0 - comp_rate * t))))
            amounts_series.append({sp: float(yj[idx[sp]]) for sp in order})

        # DERIVED verification (XV-1E): tolerance scales with the magnitude of material present/moved
        scale = max(1.0, float(np.max(np.abs(comp0))) if comp0.size else 1.0,
                    float(np.max(np.abs(comp_rate))) * float(duration) if comp_rate.size else 0.0)
        ledger_tol = 1e-6 * scale
        pos_tol = max(atol * 10.0, 1e-12)
        positivity_held = min_amount >= -pos_tol
        external_ledger_closed = max_ledger_residual <= ledger_tol
        solver_completed = bool(sol.success)
        notes = ()
        if not external_ledger_closed:
            notes += (f"external material ledger did NOT close (residual {max_ledger_residual:.3e} > tol "
                      f"{ledger_tol:.3e}); the integrated inventories do not match the declared source integral",)
        structural_ok = solver_completed and positivity_held and external_ledger_closed
        structural_tier = STRUCTURALLY_CONSERVING if structural_ok else REFUSED
        admitted_tier = weakest(structural_tier, declared_kinetic_tier)
        receipt = VerificationReceipt(
            solver_completed=solver_completed, positivity_held=positivity_held,
            external_ledger_closed=external_ledger_closed, conservation_residual=max_drift,
            external_ledger_residual=max_ledger_residual, min_inventory=min_amount, tolerance=ledger_tol,
            structural_tier=structural_tier, declared_kinetic_tier=declared_kinetic_tier,
            admitted_tier=admitted_tier, notes=notes)

        caveats = ()
        if min_amount < -pos_tol:
            caveats += (f"a species inventory went negative (min {min_amount:.3e}); the stiff solver's positivity "
                        f"was violated -- treat this trajectory as numerically suspect",)
        if not external_ledger_closed:
            caveats += notes
        return NetworkTrajectory(
            times=tuple(float(t) for t in sol.t), species=tuple(order), amounts=tuple(amounts_series),
            component_labels=self.component_labels, volume_L=V, max_component_drift=max_drift,
            external_ledger_residual=max_ledger_residual, min_amount=min_amount,
            solver_success=solver_completed, integrator=f"scipy.solve_ivp/{method}", receipt=receipt,
            tier=admitted_tier, caveats=caveats)
