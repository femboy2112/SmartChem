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

import hashlib
import json
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
    StaleCertificateError,
)


def _canon_num(x) -> str:
    """Lossless canonical encoding of a finite float for a certificate/identity digest (XIX-1D): float.hex() round-
    trips the exact IEEE-754 bits, so two coefficients that differ in the last ULP get distinct keys (unlike a rounded
    repr).  Non-finite values are refused upstream; a bool is encoded distinctly from the int it would coerce to."""
    if isinstance(x, bool):
        return f"bool:{x}"
    return float(x).hex()


def _species_key(sp: Species) -> tuple:
    """A collision-resistant identity key for a kernel Species: name + phase + charge + EXACT composition + substance.
    This is the same full identity the kernel's model digest binds (XVIII-1A) -- composition/charge/phase alone are not
    identity (ethanol vs dimethyl ether), so substance is carried too."""
    phase = getattr(sp.phase, "name", str(sp.phase))
    return (sp.name, phase, int(sp.charge), tuple((e, int(n)) for e, n in sp.composition), sp.substance)


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
        # XVI-P0.2: the mapping must be INJECTIVE -- two operator species aliased onto one kernel Species would merge
        # distinct chemical species (e.g. silently identify NH3 and NH4+), a laundering move a plain dict permits.
        mapped = list(self.species_table.values())
        if len(set(mapped)) != len(mapped):
            dup = sorted({sp.name for sp in mapped if mapped.count(sp) > 1})
            raise CoupledError(f"species_table is not injective: distinct operator species map to the same kernel "
                               f"Species {dup} -- a name alias cannot merge two chemically distinct species")
        # XVI-P0.2: the mapping must be chemically FAITHFUL -- a name may only map to a kernel Species whose
        # composition+charge match the operator's declared signature, so "NH4+" cannot be aliased onto a Na+ Species.
        # Fail-closed: an operator that declares no complete signature cannot be coupled (its faithfulness is unprovable).
        sig = getattr(self.operator, "species_signature", {})
        if not sig or any(nm not in sig for nm in self.operator.species):
            raise CoupledError(f"operator {type(self.operator).__name__} does not declare a complete species_signature; "
                               f"its species_table cannot be verified chemically faithful (fail-closed)")
        for nm, sp in self.species_table.items():
            sig_comp, sig_charge = sig[nm]
            if sp.composition != tuple(sig_comp) or sp.charge != sig_charge:
                raise CoupledError(
                    f"species_table[{nm!r}] maps to {sp.name!r} {sp.composition} q={sp.charge}, which does NOT match "
                    f"the operator's declared signature for {nm!r} ({tuple(sig_comp)} q={sig_charge}); a nominal "
                    f"species cannot be aliased onto a chemically incompatible element/charge signature")
        # XVII-A1: the operator must declare the typed whitelist of numerical solver verdicts it certifies as "closed".
        # Fail-closed: without it the world cannot tell a genuinely-solved state from a solver-refused one, so the
        # projection's numerical admissibility is unprovable and the coupling is refused.
        if not getattr(self.operator, "accepted_solver_verdicts", frozenset()):
            raise CoupledError(f"operator {type(self.operator).__name__} declares no accepted_solver_verdicts; its "
                               f"projections' numerical solver verdict cannot be judged (fail-closed)")
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
    distribution ratio for a phase boundary).  ``species_a`` and ``species_b`` MUST (a) have identical elemental
    composition and charge -- NECESSARY so the transfer conserves every element and charge globally -- AND (b) share
    the same phase-independent ``substance`` identity (XVI-P0.1) -- the constitutional discriminator that composition
    alone cannot supply.  (a) alone is insufficient: ethanol and dimethyl ether are both C2H6O/charge 0, so a transfer
    passing only (a) would launder one constitutional isomer into another -- a REACTION smuggled in as transport, yet
    stamped conserving because atoms balance.  With (b), only genuine same-substance phase/compartment transfers
    (CO2(aq)<->CO2(g); A in cell 0 <-> A in cell 1) are admitted; an identity-changing transfer is a reaction, not an
    interface, and is refused at construction.  CONSERVATION NEVER SUBSTITUTES FOR CHEMICAL IDENTITY."""
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
        # XVI-P0.1: composition+charge is NECESSARY BUT NOT SUFFICIENT.  A passive interface moves ONE substance; two
        # species of equal formula but different substance (ethanol vs dimethyl ether -- both C2H6O) are constitutional
        # isomers / distinct compounds, and transferring one into the other is a REACTION, not transport.  The shared-
        # substance requirement is the constitutional discriminator; because it is only reached after the composition/
        # charge gate above, a substance tag can never license a stoichiometry change (it cannot "launder" a formula).
        if self.species_a.substance != self.species_b.substance:
            raise CoupledError(
                f"interface {self.name!r} transfers between species of the SAME formula but DIFFERENT substance "
                f"({self.species_a.name!r} substance={self.species_a.substance!r} vs {self.species_b.name!r} "
                f"substance={self.species_b.substance!r}); same elemental composition is not chemical identity -- "
                f"these are constitutional isomers or distinct compounds. A transformation between them is a reaction "
                f"(declare it inside a compartment); a genuine phase transfer must declare a shared substance identity")
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
    reservoir_exchange: dict = field(default_factory=dict)   # {implicit-solvent component: endpoint net change (NOT independently verifiable)}
    external_flux: dict = field(default_factory=dict)            # XVIII-3 {component: independently-integrated E * q_ext over the run}
    raw_material_change: dict = field(default_factory=dict)      # XVIII-3 {component: measured E (n_final - n0)}
    ledger_adjusted_residual: dict = field(default_factory=dict)  # XVIII-3 {component: |raw_material_change - external_flux|}
    material_balance_closed: bool = True   # XVIII-3: every non-implicit-reservoir component's measured change == its integrated external flux
    charge_balance_claim: str = ""         # XVIII-3: CONSERVED (independently checked) | DEMOTED (implicit-solvent electroneutrality) | N/A
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
    # XIX-1B: per-compartment, per-sample fast-equilibrium DERIVED scalars (pH_activity, pH_concentration, ionic
    # strength, activity model, ...) captured FROM THE PROJECTION THAT PRODUCED THE SAMPLE -- the authoritative values
    # the chemical solver computed, so an observer reads them instead of recomputing an approximate pH in the renderer.
    # {compartment_name: (per-sample {scalar: value}, ...)}; a compartment with no fast equilibrium maps to ({}, ...).
    equilibrium_derived: dict = field(default_factory=dict)


class CoupledWorld:
    """A declared coupled world + its generic operator-split integrator.

    Build it from compartments, interfaces and boundaries; it validates every reference and the interface conservation
    gate at construction.  ``integrate`` advances it by Lie or Strang splitting; ``monolithic`` (no split) is available
    only when no compartment carries a fast-equilibrium projection (then the world is a pure ODE and can be integrated
    without splitting -- the reference for the convergence study)."""

    def __init__(self, compartments: list, interfaces: list = (), boundaries: list = (), *,
                 temperature_K: float = 298.15):
        if not compartments or any(type(c) is not Compartment for c in compartments):
            raise CoupledError("compartments must be a non-empty list of Compartment")
        names = [c.name for c in compartments]
        if len(set(names)) != len(names):
            raise CoupledError("duplicate compartment name")
        # XIX-1C: ONE world temperature, threaded into every fast-equilibrium projection (the integrator no longer
        # hard-codes 298.15 K in _project).  An operator whose constants are sourced only at 25 C fail-closes off its
        # domain through its own wrapped solver -- so an off-domain world temperature is REFUSED, never silently run
        # with gas physics at T and acid/base equilibria pinned at 25 C (a mixed-temperature simulation).
        if isinstance(temperature_K, bool) or not (isinstance(temperature_K, (int, float))
                                                   and math.isfinite(temperature_K) and temperature_K > 0):
            raise CoupledError("temperature_K must be a finite temperature > 0")
        self.temperature_K = float(temperature_K)
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

        # XIX-1D: snapshot a world-level execution certificate NOW -- every compartment's kernel certificate + species
        # order + volume + equilibrium-operator identity, every interface and boundary descriptor, and the world
        # temperature.  integrate() re-verifies it before advancing, so a post-construction mutation or rebind of ANY of
        # these (the coupled execution path reads compartment matrices / rate laws / interfaces directly, bypassing the
        # per-system integrate() guard) cannot silently execute a changed world under the stale certificate.
        self._world_certificate = self._compute_world_certificate()

    # ---------------------------------------------------------------- XIX-1D world execution certificate
    def _equilibrium_descriptor(self, c: Compartment):
        """A stable identity for a compartment's fast-equilibrium coupling: the operator TYPE, its activity model, the
        exact name->Species table (full species keys), and the declared reservoir components.  A rebind that swaps the
        operator, its activity model, or re-aliases a species moves this descriptor and is caught at integrate()."""
        if c.equilibrium is None:
            return None
        ec = c.equilibrium
        return {
            "operator_type": type(ec.operator).__name__,
            "activity_model": getattr(ec.operator, "activity_model", None),
            "table": sorted((nm, _species_key(sp)) for nm, sp in ec.species_table.items()),
            "reservoir_components": sorted(ec.reservoir_components),
        }

    def _compute_world_certificate(self) -> str:
        """Hash the whole executable world: temperature, every compartment (name, volume, species order, the kernel
        ChemicalSystem's own XVIII-2 certificate, equilibrium descriptor), and every interface/boundary descriptor.
        The per-compartment kernel certificate binds that compartment's float E/N and species identity+order; this
        world certificate binds everything ABOVE the single-compartment level that the coupled integrator executes."""
        comp = []
        for c in self.compartments:
            comp.append({
                "name": c.name,
                "volume_L": _canon_num(c.system.volume_L),
                "species": [_species_key(sp) for sp in c.system.species],
                "system_certificate": c.system._model_certificate,       # XVIII-2 per-system float E/N + species cert
                "equilibrium": self._equilibrium_descriptor(c),
            })
        ifaces = [{
            "name": i.name, "a": i.a, "b": i.b,
            "species_a": _species_key(i.species_a), "species_b": _species_key(i.species_b),
            "k_transfer": _canon_num(i.k_transfer), "partition": _canon_num(i.partition),
        } for i in self.interfaces]
        bounds = [{
            "name": b.name, "compartment": b.compartment, "species": _species_key(b.species), "mode": b.mode,
            "rate": _canon_num(b.rate), "k_transfer": _canon_num(b.k_transfer),
            "target_conc": _canon_num(b.target_conc),
        } for b in self.boundaries]
        payload = {"temperature_K": _canon_num(self.temperature_K),
                   "slots": [(cn, _species_key(sp)) for cn, sp in self._slots],
                   "compartments": comp, "interfaces": ifaces, "boundaries": bounds}
        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()

    def _verify_world_certificate(self) -> None:
        """XIX-1D: refuse to integrate if the live world no longer matches the certificate proven at construction.
        First re-verify EACH compartment's own kernel certificate (catches an in-place or rebound E/N on a compartment
        system -- the per-system check the coupled path would otherwise skip), then re-verify the world-level structure
        (operator / interface / boundary / temperature / species-order rebinds)."""
        for c in self.compartments:
            c.system._verify_certificate()                              # XVIII-2, now reached on the coupled path too
        if self._compute_world_certificate() != self._world_certificate:
            raise StaleCertificateError(
                "the coupled world's execution basis (compartments / interfaces / boundaries / operators / "
                "temperature) no longer matches the certificate proven at construction; it was mutated afterward and "
                "must not integrate under the stale world certificate (XIX-1D).")

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
        if not np.all(np.isfinite(y)):                                   # XVII-D3: a NaN/Inf inventory slips `< 0`
            raise CoupledError("initial inventories must be finite (no NaN/Inf)")
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

    def _transport_rhs_and_flux(self, y: np.ndarray):
        """T plus the per-boundary signed EXTERNAL flux (mol/s into the world).  Interface transfers are INTERNAL
        (conservative, a->b) and contribute to dy but NOT to the external accumulators; only ExternalBoundary terms are
        external flux.  Returns (dy, dflux) where dflux[k] is the signed mol/s boundary k injects into its species --
        the quantity XVIII-3 integrates independently of the inventory to close the material balance."""
        dy = np.zeros_like(y)
        for iface in self.interfaces:
            ia = self._slot[(iface.a, iface.species_a)]
            ib = self._slot[(iface.b, iface.species_b)]
            Va = self._comp[iface.a].system.volume_L
            Vb = self._comp[iface.b].system.volume_L
            J = iface.k_transfer * (y[ia] / Va - iface.partition * y[ib] / Vb)   # mol/s, a -> b
            dy[ia] -= J
            dy[ib] += J
        dflux = np.zeros(len(self.boundaries))
        for k, b in enumerate(self.boundaries):
            i = self._slot[(b.compartment, b.species)]
            if b.mode == "feed":
                fl = b.rate
            else:   # fixed_activity
                V = self._comp[b.compartment].system.volume_L
                fl = b.k_transfer * (b.target_conc - y[i] / V)
            dy[i] += fl
            dflux[k] = fl
        return dy, dflux

    def _transport_rhs(self, y: np.ndarray) -> np.ndarray:
        """T only (species RHS), for callers that do not track the external flux accumulators."""
        return self._transport_rhs_and_flux(y)[0]

    def _flow(self, y: np.ndarray, acc: np.ndarray, which: str, dt: float, rtol: float, atol: float):
        """Integrate one continuous operator ('reaction' | 'transport' | 'both') over [0, dt], carrying the per-boundary
        external-flux accumulators ``acc`` as AUGMENTED ODE state (XVIII-3) so each boundary's integral of q_ext is
        measured by the SAME quadrature that moves the inventory -- independent of the resulting inventory change.
        Returns (y_next, acc_next).  A reaction-only flow leaves the accumulators flat (boundaries are transport)."""
        if which not in ("reaction", "transport", "both"):
            raise CoupledError(f"unknown flow {which!r}")
        if dt == 0.0:
            return y.copy(), acc.copy()
        ny = len(y)
        want_reaction = which in ("reaction", "both")
        want_transport = which in ("transport", "both")
        nb = len(self.boundaries)

        def f(_t, z):
            yy = z[:ny]
            dy = np.zeros(ny)
            dflux = np.zeros(nb)
            if want_reaction:
                dy = dy + self._reaction_rhs(yy)
            if want_transport:
                t_dy, dflux = self._transport_rhs_and_flux(yy)
                dy = dy + t_dy
            return np.concatenate([dy, dflux])

        z0 = np.concatenate([y, acc])
        sol = solve_ivp(f, (0.0, dt), z0, method="BDF", rtol=rtol, atol=atol, t_eval=[dt])
        if not sol.success:
            raise CoupledError(f"{which} sub-integration failed: {sol.message}")
        zf = sol.y[:, -1]
        return zf[:ny], zf[ny:]

    def _project(self, y: np.ndarray):
        """P: re-speciate every fast-equilibrium compartment onto g(n) = 0 (instantaneous SNIA projection).  Returns
        ``(out, derived_by_comp)`` (XIX-1B): the projected inventory, and a {compartment: derived-scalars} map carrying
        the AUTHORITATIVE pH_activity / pH_concentration / ionic strength / activity model the chemical solver computed.

        XVI-P0.2: the returned species vector is NOT trusted on the operator's word.  Every projection result passes a
        fail-closed admission gate (``_admit_projection``) -- completeness, finiteness, nonnegativity, an accepted
        structural verdict, and conserved-component closure RECOMPUTED by the world from the returned species -- before
        a single amount is installed.  An inadmissible projection raises CoupledError and aborts the run rather than
        laundering an unverified or non-conserving vector into the world and certifying the trajectory."""
        if not self._has_equilibrium:
            return y, {}
        out = y.copy()
        derived_by_comp = {}
        for c in self.compartments:
            if c.equilibrium is None:
                continue
            ec = c.equilibrium
            V = c.system.volume_L
            # re-key the current inventory onto the operator's conserved components via the operator's OWN
            # conservation law (operator.component_totals) -- generic, so the coupled integrator carries no chemistry
            amounts = {nm: out[self._slot[(c.name, sp)]] for nm, sp in ec.species_table.items()}
            totals = ec.operator.component_totals(amounts)
            T = self.temperature_K            # XIX-1C: the world temperature, NOT a hard-coded 298.15 (a 25 C-only
            #                                   operator fail-closes off-domain through its own wrapped solver)
            state = ec.operator.speciate(totals, volume_L=V, temperature_K=T)
            # fail-closed: refuse a bad projection, never install it.  Pass the pre-projection species amounts and the
            # posed (V, T) so the gate can check elemental closure and metadata consistency independently.
            self._admit_projection(c, ec, state, totals, amounts, requested_volume_L=V, requested_temperature_K=T)
            for nm, sp in ec.species_table.items():
                out[self._slot[(c.name, sp)]] = state.species_amounts[nm]
            # XIX-1B: capture the AUTHORITATIVE derived scalars THIS projection computed (pH_activity, pH_concentration,
            # ionic strength, ...) so the observer reads the solver's result rather than recomputing an approximate pH;
            # tag the activity model and the posed V/T the gate verified the state against.
            d = dict(state.derived)
            d["activity_model"] = getattr(ec.operator, "activity_model", None)
            d["temperature_K"] = float(state.temperature_K)
            d["volume_L"] = float(state.volume_L)
            derived_by_comp[c.name] = d
        return out, derived_by_comp

    # XVII-A2: a scale-aware conservation tolerance.  The OLD 1e-6*max(1.0, |totals|) policy pinned a 1e-6 mol ABSOLUTE
    # floor even for a ~1e-12 mol trace inventory, so fabricating 1e-7 mol passed as "balanced".  The honest policy is
    # atol + rtol*scale, scaled to the ACTUAL conserved inventory (NO 1-mol floor): rtol = 1e-9 matches the wrapped
    # solvers' mass-balance closure target, and atol = 1e-15 mol (sub-femtomole) is a pure float-roundoff floor for the
    # scale -> 0 case.  For a 0.1 mol inventory tol ~ 1e-10; for a 1e-12 mol inventory tol ~ 1e-15 -- so a 1e-7 creation
    # is caught at every scale, while an honest machine-zero residual is never refused.
    _PROJECTION_RTOL = 1e-9
    _PROJECTION_ATOL = 1e-15      # mol: float-dust floor for the conservation observable (scale -> 0)
    _NONNEG_CONC_ATOL = 1e-12     # mol/L: the wrapped solvers' own nonnegativity floor; * volume -> a mol floor
    # XVIII-4A: the OUTER material-balance / feed-ledger tolerance -- scale-aware, NO 1-mol floor (the pre-XVIII
    # 1e-6*max(1.0, scale) pinned a 1e-6 mol ABSOLUTE floor that passed a trace-scale fabrication).  atol is a pure
    # float-dust floor; rtol keeps the prior relative sensitivity, now applied to the ACTUAL conserved inventory.
    _MATERIAL_RTOL = 1e-6
    _MATERIAL_ATOL = 1e-12

    @classmethod
    def _projection_tol(cls, totals_in: dict) -> float:
        scale = max([0.0] + [abs(float(v)) for v in totals_in.values()])
        return cls._PROJECTION_ATOL + cls._PROJECTION_RTOL * scale

    def _admit_projection(self, c, ec, state, totals_in, amounts_in, *,
                          requested_volume_L, requested_temperature_K) -> None:
        """XVI-P0.2 + XVII-A1/A2/A3 fail-closed admission of a fast-equilibrium projection.  The world verifies the
        CODOMAIN itself; it never trusts the operator's self-reported residuals, tier, verdict or metadata.  In order:
        state type/shape; completeness; per-species finiteness + nonnegativity; (A1) the NUMERICAL solver verdict is one
        the operator certifies as a closed solve; (A1) the state's self-reported (volume, temperature, component inputs)
        match the problem the world posed; the operator's structural (mass-balance) tier is accepted; and TWO
        independent conservation checks -- the operator's own component law recomputed on the returned species, AND (A3)
        the kernel's EXACT element/charge map recomputed on the returned species, which does not consult the operator's
        component law at all (so a complicit/wrong law that makes input and output agree on a false invariant is still
        caught).  Raises CoupledError on any violation (no partial install)."""
        from experiments.sandbox_foundation.general_equilibrium import EquilibriumState
        if type(state) is not EquilibriumState:
            raise CoupledError(f"compartment {c.name!r} fast-equilibrium returned a {type(state).__name__}, "
                               f"not an EquilibriumState")
        sa = state.species_amounts
        if type(sa) is not dict:
            raise CoupledError(f"compartment {c.name!r} projection returned a non-dict species map")
        # completeness: every kernel species the world must install has a value
        missing = [nm for nm in ec.species_table if nm not in sa]
        if missing:
            raise CoupledError(f"compartment {c.name!r} projection is missing required species {sorted(missing)}")
        tol = self._projection_tol(totals_in)
        # finiteness + nonnegativity of every installed amount.  Nonnegativity gets its OWN floor (a solver may dip a
        # concentration a roundoff below zero: _NONNEG_CONC_ATOL * volume), separate from the conservation tol -- the
        # two numerical facets (physical nonnegativity vs component loss) are not the same observable (XVII-A2).
        neg_tol = self._NONNEG_CONC_ATOL * float(c.system.volume_L) + self._PROJECTION_ATOL
        for nm in ec.species_table:
            v = sa[nm]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise CoupledError(f"compartment {c.name!r} projection returned a non-finite amount for {nm!r}: {v!r}")
            if float(v) < -neg_tol:
                raise CoupledError(f"compartment {c.name!r} projection returned a negative amount for {nm!r}: "
                                   f"{float(v):.3e} (nonnegativity tol {neg_tol:.3e})")
        # XVII-A1: the NUMERICAL solver verdict is an INDEPENDENT facet from the structural mass-balance tier.  A
        # perfectly mass-balanced projection resting on a solve the solver itself REFUSED is not scientifically
        # admissible.  The accepted set is the operator's typed whitelist (bound to its source/domain), not "nonempty".
        accepted = getattr(ec.operator, "accepted_solver_verdicts", frozenset())
        if not accepted:
            raise CoupledError(f"compartment {c.name!r} operator {type(ec.operator).__name__} declares no "
                               f"accepted_solver_verdicts; its numerical solve cannot be judged (fail-closed)")
        if state.solver_verdict not in accepted:
            raise CoupledError(f"compartment {c.name!r} projection carries solver_verdict {state.solver_verdict!r}, "
                               f"not an accepted verdict for {type(ec.operator).__name__} ({sorted(accepted)}); a "
                               f"numerically refused / out-of-domain solve is not admissible even if it is balanced")
        # XVII-A1 metadata: the returned state must describe the problem the world POSED (no forged provenance)
        if state.volume_L != requested_volume_L:
            raise CoupledError(f"compartment {c.name!r} projection reports volume_L {state.volume_L!r} != the posed "
                               f"{requested_volume_L!r}; it claims to have solved a different problem")
        if state.temperature_K != requested_temperature_K:
            raise CoupledError(f"compartment {c.name!r} projection reports temperature_K {state.temperature_K!r} != "
                               f"the posed {requested_temperature_K!r}; it claims to have solved a different problem")
        ci = state.component_inputs
        if type(ci) is not dict or set(ci) != set(totals_in):
            raise CoupledError(f"compartment {c.name!r} projection reports component_inputs over {sorted(ci) if isinstance(ci, dict) else ci!r}, "
                               f"not the components the projection was keyed on {sorted(totals_in)}")
        for k, tin in totals_in.items():
            cv = ci[k]
            if isinstance(cv, bool) or not isinstance(cv, (int, float)) or not math.isfinite(float(cv)) \
                    or abs(float(cv) - float(tin)) > tol:
                raise CoupledError(f"compartment {c.name!r} projection reports component_inputs[{k!r}]={cv!r}, which "
                                   f"does not match the inventory it was keyed on ({float(tin):.6g})")
        # the operator's own structural (mass-balance) verdict must be an ACCEPTED one (not REFUSED / unverified)
        if state.structural_tier != STRUCTURALLY_CONSERVING:
            raise CoupledError(f"compartment {c.name!r} projection returned structural_tier "
                               f"{state.structural_tier!r}, not {STRUCTURALLY_CONSERVING!r}; the solve is refused or "
                               f"unverified and its vector is not admitted")
        # INDEPENDENT closure #1 -- the operator's OWN component law recomputed on the RETURNED species == keyed inputs
        # (catches a wrong species map / operator self-inconsistency)
        totals_out = ec.operator.component_totals(sa)
        for comp, tin in totals_in.items():
            tout = float(totals_out.get(comp, 0.0))
            if not math.isfinite(tout) or abs(tout - float(tin)) > tol:
                raise CoupledError(
                    f"compartment {c.name!r} projection does NOT conserve component {comp!r}: keyed on {float(tin):.6g} "
                    f"but the returned species recompute to {tout:.6g} (residual {abs(tout - float(tin)):.3e} > tol "
                    f"{tol:.3e}); refusing to install a non-conserving speciation")
        # INDEPENDENT closure #2 (XVII-A3) -- the kernel's EXACT element/charge map, computed straight from the mapped
        # kernel Species' compositions.  This does NOT consult the operator's component_totals at all, so a complicit or
        # simply wrong component law (one that makes input and output agree on a false invariant) cannot hide a
        # fabricated/destroyed atom.  Every element/charge the table species carry EXCEPT the declared reservoir
        # components (set by the implicit solvent + electroneutrality) must be conserved across the projection.
        elements = {el for sp in ec.species_table.values() for el, _ in sp.composition}
        elements.add("charge")
        for el in sorted(elements):
            if el in ec.reservoir_components:
                continue
            e_in = sum(float(amounts_in[nm]) * (float(sp.charge) if el == "charge" else float(sp.count(el)))
                       for nm, sp in ec.species_table.items())
            e_out = sum(float(sa[nm]) * (float(sp.charge) if el == "charge" else float(sp.count(el)))
                        for nm, sp in ec.species_table.items())
            if not math.isfinite(e_out) or abs(e_out - e_in) > tol:
                raise CoupledError(
                    f"compartment {c.name!r} projection does NOT conserve element/charge {el!r} (checked independently "
                    f"of the operator's component law, via the kernel's exact composition map): {e_in:.6g} in -> "
                    f"{e_out:.6g} out (residual {abs(e_out - e_in):.3e} > tol {tol:.3e}); refusing a speciation that "
                    f"fabricates or destroys atoms")

    # ---------------------------------------------------------------- the stepper
    def _step(self, y: np.ndarray, acc: np.ndarray, dt: float, scheme: str, rtol: float, atol: float):
        """Advance one macro-step of the chosen operator-split scheme, threading the external-flux accumulators ``acc``
        through each continuous flow (XVIII-3).  The fast-equilibrium projection P re-speciates the inventory but does
        NOT exchange with an external boundary, so it leaves the accumulators unchanged.  Returns (y_next, acc_next,
        derived_by_comp) -- the last being the projection's authoritative derived scalars for this step (XIX-1B)."""
        if scheme == "lie":
            y, acc = self._flow(y, acc, "reaction", dt, rtol, atol)
            y, acc = self._flow(y, acc, "transport", dt, rtol, atol)
        elif scheme == "strang":
            y, acc = self._flow(y, acc, "reaction", dt / 2.0, rtol, atol)
            y, acc = self._flow(y, acc, "transport", dt, rtol, atol)
            y, acc = self._flow(y, acc, "reaction", dt / 2.0, rtol, atol)
        elif scheme == "monolithic":
            if self._has_equilibrium:
                raise CoupledError("monolithic integration is undefined when a compartment has a fast-equilibrium "
                                   "projection (the world is a DAE, not an ODE); use lie or strang")
            y, acc = self._flow(y, acc, "both", dt, rtol, atol)
        else:
            raise CoupledError("scheme must be 'lie', 'strang' or 'monolithic'")
        y_proj, derived = self._project(y)
        return y_proj, acc, derived

    def integrate(self, initial: dict, *, duration: float, n_steps: int, scheme: str = "strang",
                  n_samples: int | None = None, rtol: float = 1e-10, atol: float = 1e-14,
                  declared_kinetic_tier: str | None = None) -> CoupledTrajectory:
        """Advance the coupled world over ``duration`` seconds in ``n_steps`` equal macro-steps of the chosen scheme.

        Every macro-step records the state (or every (n_steps // n_samples)th, if n_samples is given).  Conservation,
        the feed ledger and positivity are MEASURED and the tier DERIVED (capped at STRUCTURALLY_CONSERVING, weakest-
        premise'd with the declared kinetic tier).  Missing kinetics anywhere fail closed (Wave A invariant)."""
        self._verify_world_certificate()          # XIX-1D: never integrate under a stale world/compartment certificate
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
        y, derived0 = self._project(y)                    # project the initial state onto equilibrium if declared
        comp0 = self._Eg @ y
        acc = np.zeros(len(self.boundaries))              # XVIII-3: per-boundary integrated external flux (mol)

        sample_every = 1 if not n_samples else max(1, n_steps // max(1, n_samples))
        times = [0.0]
        ys = [y.copy()]
        derived_samples = [derived0]                       # XIX-1B: derived scalars aligned with each sampled state
        for step in range(1, n_steps + 1):
            y, acc, derived = self._step(y, acc, dt, scheme, rtol, atol)
            if step % sample_every == 0 or step == n_steps:
                times.append(step * dt)
                ys.append(y.copy())
                derived_samples.append(derived)

        # XVIII-3 SIGNED EXTERNAL-FLUX LEDGER.  Each boundary's flux was accumulated INDEPENDENTLY as augmented ODE
        # state (acc[k] = integral of q_ext,k dt), so the material balance d(E n)/dt = E q_ext is CHECKED, not inferred
        # from the endpoint inventory diff.  external_flux maps each component to E * (integrated boundary flux);
        # raw_material_change is the MEASURED E (n_final - n0); their difference is the ledger residual.  A component
        # touched ONLY by an implicit-solvent reservoir (fast-equilibrium H/O/charge) has no boundary accumulator, so it
        # is reported (endpoint) but excluded from the strict balance -- that exclusion is now NARROW (implicit solvent
        # only), where the pre-XVIII ledger also exempted every fixed-activity-boundary component (the tautology).
        labels = self.component_labels
        comp_final = self._Eg @ ys[-1]
        raw_change_vec = comp_final - comp0
        ext_comp = np.zeros(len(labels))
        for k, b in enumerate(self.boundaries):
            ext_comp += self._Eg[:, self._slot[(b.compartment, b.species)]] * acc[k]

        implicit_reservoir = set(self.reservoir_components)     # fast-equilibrium solvent components (no boundary flux)
        checked_idx = [i for i, lab in enumerate(labels) if lab not in implicit_reservoir]

        scale = 0.0
        for i in checked_idx:
            scale = max(scale, abs(float(comp0[i])), abs(float(ext_comp[i])))
        tol = self._MATERIAL_ATOL + self._MATERIAL_RTOL * scale          # XVIII-4A: scale-aware, NO 1-mol floor

        external_flux = {labels[i]: float(ext_comp[i]) for i in range(len(labels))}
        raw_material_change = {labels[i]: float(raw_change_vec[i]) for i in range(len(labels))}
        ledger_residual = {labels[i]: abs(float(raw_change_vec[i] - ext_comp[i])) for i in range(len(labels))}

        min_amount = float("inf")
        max_conserved_drift = 0.0
        for yj in ys:
            min_amount = min(min_amount, float(yj.min()))
            comp_j = self._Eg @ yj
            for i in checked_idx:
                if abs(float(ext_comp[i])) == 0.0:          # a purely-internal (no external flux) component: drift only
                    max_conserved_drift = max(max_conserved_drift, abs(float(comp_j[i] - comp0[i])))

        max_material_residual = max([0.0] + [ledger_residual[labels[i]] for i in checked_idx])
        material_balance_closed = max_material_residual <= tol

        fed_components = set()
        for b in self.boundaries:
            if b.mode == "feed":
                j = self._slot[(b.compartment, b.species)]
                for i, lab in enumerate(labels):
                    if self._Eg[i, j] != 0.0:
                        fed_components.add(lab)
        checked_labels = {labels[i] for i in checked_idx}
        feed_ledger_residual = max([0.0] + [ledger_residual[lab] for lab in fed_components if lab in checked_labels])

        # implicit-solvent reservoir exchange: reported (endpoint), NOT independently verifiable (no boundary flux)
        reservoir_exchange = {labels[i]: float(raw_change_vec[i])
                              for i in range(len(labels)) if labels[i] in implicit_reservoir}

        # XVIII-3 charge/water: neutral water supplies H/O but cannot source NET charge.  Where "charge" is implicit-
        # reservoir-coupled, the charge-conservation claim is DEMOTED (a labeled electroneutrality approximation),
        # never silently exempted; otherwise charge is in the checked set and conserved independently.
        if "charge" not in labels:
            charge_balance_claim = "N/A (no charged species declared)"
        elif "charge" in implicit_reservoir:
            charge_balance_claim = ("DEMOTED: net charge is balanced against an implicit NEUTRAL-water reservoir via "
                                    "electroneutrality; neutral water sources H and O but cannot source net charge, so "
                                    "this is a LABELED charge-balance approximation, not an independently conserved "
                                    "quantity -- a conservation claim needs explicit counterions or a charge-carrying "
                                    "boundary/electrode.")
        else:
            charge_balance_claim = "CONSERVED (independently checked in the material balance)"

        pos_tol = max(atol * 100.0, 1e-10)
        positivity_held = min_amount >= -pos_tol
        conserved_components_held = material_balance_closed
        feed_ledger_closed = feed_ledger_residual <= tol
        solver_completed = True
        structural_ok = solver_completed and positivity_held and material_balance_closed
        structural_tier = STRUCTURALLY_CONSERVING if structural_ok else REFUSED
        admitted_tier = weakest(structural_tier, declared_kinetic_tier)

        notes = ()
        caveats = ()
        if not material_balance_closed:
            worst = max(checked_idx, key=lambda i: ledger_residual[labels[i]])
            lab = labels[worst]
            caveats += (f"the material balance did NOT close for component {lab!r}: measured change "
                        f"{raw_material_change[lab]:.3e} vs integrated external flux {external_flux[lab]:.3e} "
                        f"(ledger residual {ledger_residual[lab]:.3e} > tol {tol:.3e})",)
        if not positivity_held:
            caveats += (f"an inventory went negative (min {min_amount:.3e})",)
        if implicit_reservoir:
            note = (f"implicit-solvent reservoir components {sorted(implicit_reservoir)} exchange H/O/charge with a "
                    f"fast-equilibrium solvent and are reported (endpoint), not independently ledgered")
            if "charge" in implicit_reservoir:
                note += "; " + charge_balance_claim
            notes += (note,)

        receipt = CoupledReceipt(
            solver_completed=solver_completed, positivity_held=positivity_held,
            conserved_components_held=conserved_components_held, feed_ledger_closed=feed_ledger_closed,
            max_conserved_drift=max_conserved_drift, feed_ledger_residual=feed_ledger_residual,
            min_inventory=min_amount, tolerance=tol, scheme=scheme, structural_tier=structural_tier,
            declared_kinetic_tier=declared_kinetic_tier, admitted_tier=admitted_tier,
            reservoir_exchange=reservoir_exchange, external_flux=external_flux,
            raw_material_change=raw_material_change, ledger_adjusted_residual=ledger_residual,
            material_balance_closed=material_balance_closed, charge_balance_claim=charge_balance_claim, notes=notes)

        amounts = {c.name: tuple({sp: float(yj[self._slot[(c.name, sp)]]) for sp in c.system.species} for yj in ys)
                   for c in self.compartments}
        # XIX-1B: per-compartment derived scalars, one entry per SAMPLED state (a compartment without fast equilibrium
        # maps to an empty dict each sample).
        equilibrium_derived = {c.name: tuple(ds.get(c.name, {}) for ds in derived_samples)
                               for c in self.compartments}
        return CoupledTrajectory(
            times=tuple(times), compartments=tuple(c.name for c in self.compartments), amounts=amounts,
            component_labels=self.component_labels, scheme=scheme, steps=n_steps,
            max_conserved_drift=max_conserved_drift, feed_ledger_residual=feed_ledger_residual, min_amount=min_amount,
            solver_success=solver_completed, receipt=receipt, tier=admitted_tier, caveats=caveats,
            equilibrium_derived=equilibrium_derived)


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
    acc0 = np.zeros(len(world.boundaries))
    reference, _ = world._flow(y0, acc0, "both", float(duration), rtol, atol)   # the un-split truth (tight tolerance)
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
