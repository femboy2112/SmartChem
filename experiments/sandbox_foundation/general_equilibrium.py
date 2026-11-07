"""OPERATION XV Wave B (P1) -- the general EQUILIBRIUM-OPERATOR interface + a first ADAPTER.

The kinetic kernel (general_kernel.py) evolves dn/dt = N r + q.  A great deal of aqueous chemistry is NOT a slow
kinetic relaxation but a FAST equilibrium: an algebraic constraint g(n) = 0 on the conserved-component inventories,
solved to speciation without fabricated high reaction rates (the plan's section 2/3 warning).  This module adds that
second operator KIND -- the EquilibriumOperator -- and, crucially, proves the ARCHITECTURE GATE: the existing,
already-verified aqueous equilibrium solver (aqueous_equilibrium.solve) becomes a CONSUMER of the general interface
through a thin ADAPTER, with NO rewrite of its numerics.  The plan is explicit: "Use an adapter first.  Once the
adapter proves useful, factor genuine shared mathematics without changing results unnecessarily."

WHAT IS (deliberately) HERE, and what is NOT:
  * EquilibriumOperator -- the interface: speciate conserved-component INVENTORIES (mol) at a volume + temperature
    into equilibrium species amounts (mol), algebraically.  Keyed on conserved components, so it composes with the
    kernel's E n totals.
  * EquilibriumState -- the typed result: species amounts, the conservation closure of the fast equilibrium, derived
    scalars (pH, ...), and an evidential tier (never self-certified above what the wrapped solver earns).
  * AcetateWaterEquilibriumOperator -- the first adapter, wrapping aqueous_equilibrium.solve.

NOT here (they belong to Wave C, and are not faked as speculative empty types now): Compartment, InterfaceTransfer,
ExternalBoundary, the operator-split coupled integrator.  They attach through this same interface when the coupled
world needs them.

IDENTITY NOTE: the wrapped solver reports concentrations by ROLE (h_plus_M, ac_minus_M, ...), not kernel Species
objects.  This adapter is the EXPLICIT bridge the plan permits ("Do not create a second incompatible species identity
system without an explicit adapter"): it returns amounts keyed by canonical species NAME, and the Wave C coupling will
map those names to kernel Species through a declared species table.  No second solver and no second identity model is
introduced -- the verified numerics are reused verbatim.
"""
from __future__ import annotations

import dataclasses
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from experiments.sandbox_foundation import ammonia_equilibrium, aqueous_equilibrium, coupled_equilibrium
from experiments.sandbox_foundation.claim_tiers import REFUSED, STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_kernel import KernelError


class EquilibriumError(KernelError):
    """Fail-closed error for the general equilibrium interface."""


def _canon(v):
    """XXIII-2b (F2): a lossless, order-stable, JSON-safe encoding of a solve parameter for a world certificate.
    Floats go through float.hex (exact IEEE-754 bits); a bool is kept distinct from the int it would coerce to; sets
    and dicts are sorted; a dataclass (e.g. a SourcedConstant record) is encoded field by field.  Anything else is
    refused rather than repr()'d -- a collision-prone fallback is how two different worlds end up sharing a signature."""
    if isinstance(v, bool):
        return f"bool:{v}"
    if isinstance(v, int):
        return f"int:{v}"
    if isinstance(v, float):
        return f"float:{v.hex()}"
    if isinstance(v, str):
        return f"str:{v}"
    if v is None:
        return "None"
    if isinstance(v, (tuple, list)):
        return ["seq"] + [_canon(x) for x in v]
    if isinstance(v, (set, frozenset)):
        return ["set"] + sorted((_canon(x) for x in v), key=repr)
    if isinstance(v, dict):
        return ["map"] + sorted(([_canon(k), _canon(x)] for k, x in v.items()), key=repr)
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return [type(v).__qualname__] + [[f.name, _canon(getattr(v, f.name))] for f in dataclasses.fields(v)]
    raise EquilibriumError(f"cannot canonically encode a {type(v).__name__} solve parameter for a certificate")


def _dataclass_defaults(cls, names: tuple) -> list:
    """The DEFAULT values ``cls`` will hand its solver for the named fields -- the sourced constants an adapter relies
    on by omission (it never passes them), which are therefore operative solve parameters all the same."""
    by_name = {f.name: f for f in dataclasses.fields(cls)}
    return [[nm, _canon(by_name[nm].default)] for nm in names]


def _module_constants(module, names: tuple) -> list:
    """Module-level constants a wrapped solver reads AT CALL TIME -- read live here, so a post-construction rebind of
    one moves the descriptor instead of quietly changing the physics."""
    return [[nm, _canon(getattr(module, nm))] for nm in names]


@dataclass(frozen=True)
class EquilibriumState:
    """The typed result of solving a fast equilibrium through the general interface."""
    species_amounts: dict        # {species_name: mol} at equilibrium
    volume_L: float
    temperature_K: float
    component_inputs: dict        # {component: total mol supplied}
    component_residuals: dict     # {component: |amount recovered in species - supplied|} -- fast-equilibrium closure
    derived: dict                 # MODEL_DERIVED scalars (pH, ionic strength, ...); a quantity not supplied is absent
    structural_tier: str          # STRUCTURALLY_CONSERVING if every conserved component closed, else REFUSED
    solver_verdict: str           # the WRAPPED solver's own chemistry verdict (its provenance, passed through)
    assumptions: tuple = ()       # declared modelling assumptions (e.g. water treated as an implicit reservoir)
    caveats: tuple = field(default_factory=tuple)


class EquilibriumOperator(ABC):
    """Solve g(n) = 0: map conserved-component inventories (mol) to equilibrium species amounts (mol), algebraically.

    ``components`` is the frozenset of conserved components the operator speciates; ``species`` is the tuple of
    species names it returns.  A component it does not model is REFUSED, never silently ignored.

    ``species_signature`` (XVI-P0.2) declares the expected (composition, charge) of every species NAME the operator
    returns -- the composition tuple in the same canonical (element, count) form a kernel Species uses, plus the
    integer charge.  It lets a consumer (EquilibriumCoupling) verify that the kernel Species a name is mapped to is
    chemically FAITHFUL to the name (so "NH4+" cannot be aliased onto a sodium Species), fail-closed: a coupling
    refuses an operator that does not declare a complete signature.  An empty default forces every real operator to
    declare it.

    ``accepted_solver_verdicts`` (XVII-A1) is the TYPED whitelist of ``solver_verdict`` strings this operator's wrapped
    numerical solver is entitled to emit for a state that genuinely CLOSED -- bound to that solver's source and
    applicability domain.  A structural (mass-balance) verdict and a NUMERICAL (solver) verdict are independent facets:
    a projection can be perfectly mass-balanced yet rest on a solve the solver itself REFUSED (routes disagreed, a
    balance did not close, a constant was requested out of its sourced temperature domain).  A consumer admits a
    projection only if its ``solver_verdict`` is in this set; an empty default is fail-closed (an operator that
    declares no accepted verdict cannot have its numerical state judged, so it cannot be coupled)."""
    components: frozenset = frozenset()
    species: tuple = ()
    species_signature: dict = {}     # {species_name: (composition_tuple, charge)} -- for faithfulness checking
    accepted_solver_verdicts: frozenset = frozenset()   # XVII-A1: solver_verdict strings a closed solve may carry

    @abstractmethod
    def speciate(self, component_amounts: dict, *, volume_L: float,
                 temperature_K: float = 298.15) -> EquilibriumState:
        ...

    def descriptor(self) -> list:
        """XXIII-2b (F2): a canonical descriptor of EVERY parameter that changes what ``speciate`` returns -- instance
        options (activity model, ion pairing, ...), the sourced constants the wrapped solver consumes, and the class-level
        declarations the world relies on.  The coupled world binds it into its certificate, so a post-construction toggle
        is DETECTED, not executed.  The base REFUSES (NotImplementedError): an operator that does not bind its own solve
        parameters -- including a subclass that inherits a parent's descriptor while replacing its physics -- gives the
        world no certified execution identity (fail-closed, the same treatment as an UNVERIFIABLE rate law)."""
        raise NotImplementedError

    def _class_descriptor(self) -> list:
        """The class-level part every in-tree descriptor shares: exact type, components, species, signature, verdicts."""
        t = type(self)
        return [t.__module__, t.__qualname__, _canon(self.components), _canon(self.species),
                _canon(self.species_signature), _canon(self.accepted_solver_verdicts)]

    def _validate(self, component_amounts: dict, volume_L: float, temperature_K: float) -> None:
        if isinstance(volume_L, bool) or not (isinstance(volume_L, (int, float))
                                              and math.isfinite(volume_L) and volume_L > 0):
            raise EquilibriumError("volume_L must be a finite reactor volume > 0 (litres)")
        if isinstance(temperature_K, bool) or not (isinstance(temperature_K, (int, float))
                                                   and math.isfinite(temperature_K) and temperature_K > 0):
            raise EquilibriumError("temperature_K must be a finite temperature > 0")
        if type(component_amounts) is not dict:
            raise EquilibriumError("component_amounts must be a {component: mol} dict")
        for comp, val in component_amounts.items():
            if comp not in self.components:
                raise EquilibriumError(
                    f"component {comp!r} is not modelled by {type(self).__name__} (has {sorted(self.components)}); "
                    f"an unknown component is refused, never ignored")
            if isinstance(val, bool) or not (isinstance(val, (int, float)) and math.isfinite(val) and val >= 0):
                raise EquilibriumError(f"component amount for {comp!r} must be a finite mol value >= 0")


class AcetateWaterEquilibriumOperator(EquilibriumOperator):
    """Adapter: the verified aqueous_equilibrium.solve(AcetateWaterSystem) as a general EquilibriumOperator.

    Conserved components ACETATE and SODIUM are supplied as inventories (mol); water/H/O are handled through the
    wrapped solver's implicit solvent reservoir (a declared assumption, since water is in vast excess), and H+/OH-/
    charge are determined by the acid/water equilibria + electroneutrality.  The numerics are the existing solver's,
    unchanged."""
    components = frozenset({"acetate", "sodium"})
    species = ("HAc", "Ac-", "H+", "OH-", "Na+", "NaAc")
    species_signature = {                                    # XVI-P0.2 (composition, charge) per returned species name
        "HAc": ((("C", 2), ("H", 4), ("O", 2)), 0),
        "Ac-": ((("C", 2), ("H", 3), ("O", 2)), -1),
        "H+": ((("H", 1),), 1),
        "OH-": ((("H", 1), ("O", 1)), -1),
        "Na+": ((("Na", 1),), 1),
        "NaAc": ((("C", 2), ("H", 3), ("Na", 1), ("O", 2)), 0),
    }
    accepted_solver_verdicts = frozenset({                   # XVII-A1: the aqueous solver's "the math closed" verdicts
        aqueous_equilibrium.SOLVED_WITHIN_IDEAL_MODEL,
        aqueous_equilibrium.SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    })   # NUMERICALLY_UNVERIFIED / OUT_OF_SOURCE_DOMAIN ride on raised exceptions; if one ever reaches a state, refuse

    def __init__(self, *, activity_model: str = "ideal", include_ion_pair: bool = False):
        if activity_model not in ("ideal", "davies"):
            raise EquilibriumError("activity_model must be 'ideal' or 'davies'")
        self.activity_model = activity_model
        self.include_ion_pair = bool(include_ion_pair)

    def descriptor(self) -> list:
        # XXIII-2b (F2): include_ion_pair was the unbound knob -- two different worlds, one certificate.  Bound now,
        # with the activity model, the Ka/Kw/K_assoc records AcetateWaterSystem supplies by default, and the module
        # constants aqueous_equilibrium.solve reads at call time.
        return self._class_descriptor() + [
            ["activity_model", _canon(self.activity_model)],
            ["include_ion_pair", _canon(self.include_ion_pair)],
            ["system_defaults", _dataclass_defaults(aqueous_equilibrium.AcetateWaterSystem, ("Ka", "Kw", "K_assoc"))],
            ["module_constants", _module_constants(aqueous_equilibrium, ("DAVIES_A_25C", "C_REF"))],
        ]

    def speciate(self, component_amounts: dict, *, volume_L: float,
                 temperature_K: float = 298.15) -> EquilibriumState:
        self._validate(component_amounts, volume_L, temperature_K)
        acetate_mol = float(component_amounts.get("acetate", 0.0))
        sodium_mol = float(component_amounts.get("sodium", 0.0))
        V = float(volume_L)

        system = aqueous_equilibrium.AcetateWaterSystem(
            total_acetic_M=acetate_mol / V, sodium_M=sodium_mol / V, temperature_K=temperature_K,
            activity_model=self.activity_model, include_ion_pair=self.include_ion_pair)
        res = aqueous_equilibrium.solve(system)                          # the VERIFIED numerics, verbatim

        amounts = {
            "HAc": res.hac_M * V, "Ac-": res.ac_minus_M * V, "H+": res.h_plus_M * V,
            "OH-": res.oh_minus_M * V, "Na+": res.na_plus_M * V, "NaAc": res.naac_M * V,
        }
        # fast-equilibrium conservation closure: every acetate-bearing and sodium-bearing species summed back
        acetate_out = amounts["HAc"] + amounts["Ac-"] + amounts["NaAc"]
        sodium_out = amounts["Na+"] + amounts["NaAc"]
        residuals = {"acetate": abs(acetate_out - acetate_mol), "sodium": abs(sodium_out - sodium_mol)}
        tol = 1e-9 * max(1.0, acetate_mol, sodium_mol)
        structural_tier = STRUCTURALLY_CONSERVING if all(r <= tol for r in residuals.values()) else REFUSED

        derived = {
            "pH": res.pH, "pH_concentration": res.pH_concentration, "pH_activity": res.pH_activity,
            "ionic_strength_M": res.ionic_strength_M, "gamma_monovalent": res.gamma_monovalent,
            "charge_balance_residual": res.charge_balance_residual,
            "solver_agreement_residual": res.solver_agreement_residual,
        }
        return EquilibriumState(
            species_amounts=amounts, volume_L=V, temperature_K=float(temperature_K),
            component_inputs={"acetate": acetate_mol, "sodium": sodium_mol}, component_residuals=residuals,
            derived=derived, structural_tier=structural_tier, solver_verdict=res.verdict,
            assumptions=("water is an implicit solvent reservoir (not a finite conserved inventory); H+/OH- are set "
                         "by the acid + water autodissociation equilibria and electroneutrality",),
            caveats=tuple(res.caveats))

    def component_totals(self, species_amounts: dict) -> dict:
        """The operator's OWN conservation law: reconstruct its conserved-component inventories from species amounts
        (acetate = HAc + Ac- + NaAc; sodium = Na+ + NaAc).  Used by the coupled world to re-key a current inventory
        onto the operator's components before projecting -- generic, so the coupled integrator carries no chemistry."""
        g = species_amounts.get
        return {"acetate": g("HAc", 0.0) + g("Ac-", 0.0) + g("NaAc", 0.0),
                "sodium": g("Na+", 0.0) + g("NaAc", 0.0)}


class AmmoniaWaterEquilibriumOperator(EquilibriumOperator):
    """Adapter: the Wave D ammonia_equilibrium.solve as a general EquilibriumOperator -- a weak BASE buffer, a
    chemistry DISTINCT from acetate, through the SAME Wave B interface (no second solver, no second identity system).

    Conserved components: ammonia (total N as NH3 + NH4+), strong_base (Na+ spectator), strong_acid (Cl- spectator).
    Water/H/O and the H+/OH- balance ride on the implicit solvent reservoir + electroneutrality, exactly as the
    acetate operator.  Na+/Cl- are pure spectators passed through unchanged (their presence sets the charge offset S
    the speciation solves against)."""
    components = frozenset({"ammonia", "strong_base", "strong_acid"})
    species = ("NH3", "NH4+", "H+", "OH-", "Na+", "Cl-")
    species_signature = {                                    # XVI-P0.2 (composition, charge) per returned species name
        "NH3": ((("H", 3), ("N", 1)), 0),
        "NH4+": ((("H", 4), ("N", 1)), 1),
        "H+": ((("H", 1),), 1),
        "OH-": ((("H", 1), ("O", 1)), -1),
        "Na+": ((("Na", 1),), 1),
        "Cl-": ((("Cl", 1),), -1),
    }
    accepted_solver_verdicts = frozenset({ammonia_equilibrium.SOLVED_IDEAL})   # XVII-A1; REFUSED is not admissible

    def descriptor(self) -> list:
        # XXIII-2b (F2): no instance options; ammonia_equilibrium.solve reads its Ka/Kw as module globals at call time.
        return self._class_descriptor() + [
            ["module_constants", _module_constants(ammonia_equilibrium, ("KA_NH4", "KW"))],
        ]

    def speciate(self, component_amounts: dict, *, volume_L: float,
                 temperature_K: float = 298.15) -> EquilibriumState:
        self._validate(component_amounts, volume_L, temperature_K)
        ammonia_mol = float(component_amounts.get("ammonia", 0.0))
        base_mol = float(component_amounts.get("strong_base", 0.0))
        acid_mol = float(component_amounts.get("strong_acid", 0.0))
        V = float(volume_L)

        system = ammonia_equilibrium.AmmoniaWaterSystem(
            total_ammonia_M=ammonia_mol / V, strong_base_M=base_mol / V, strong_acid_M=acid_mol / V,
            temperature_K=temperature_K)
        res = ammonia_equilibrium.solve(system)                           # the VERIFIED two-route numerics, verbatim

        amounts = {
            "NH3": res.nh3_M * V, "NH4+": res.nh4_M * V, "H+": res.h_M * V, "OH-": res.oh_M * V,
            "Na+": base_mol, "Cl-": acid_mol,                              # strong ions: inert spectators, passed through
        }
        ammonia_out = amounts["NH3"] + amounts["NH4+"]
        residuals = {"ammonia": abs(ammonia_out - ammonia_mol),
                     "strong_base": abs(amounts["Na+"] - base_mol), "strong_acid": abs(amounts["Cl-"] - acid_mol)}
        tol = 1e-9 * max(1.0, ammonia_mol, base_mol, acid_mol)
        structural_tier = STRUCTURALLY_CONSERVING if all(r <= tol for r in residuals.values()) else REFUSED

        derived = {"pH": res.pH, "ionic_strength_M": res.ionic_strength_M,
                   "charge_balance_residual": res.charge_balance_residual,
                   "solver_agreement_residual": res.solver_agreement_residual}
        return EquilibriumState(
            species_amounts=amounts, volume_L=V, temperature_K=float(temperature_K),
            component_inputs={"ammonia": ammonia_mol, "strong_base": base_mol, "strong_acid": acid_mol},
            component_residuals=residuals, derived=derived, structural_tier=structural_tier,
            solver_verdict=res.verdict,
            assumptions=("water is an implicit solvent reservoir; H+/OH- set by the base + water equilibria and "
                         "electroneutrality; ideal concentration standard state (Davies is a declared P4 extension)",),
            caveats=tuple(res.caveats))

    def component_totals(self, species_amounts: dict) -> dict:
        """ammonia = NH3 + NH4+; strong_base = Na+; strong_acid = Cl- (the operator's own conservation law)."""
        g = species_amounts.get
        return {"ammonia": g("NH3", 0.0) + g("NH4+", 0.0),
                "strong_base": g("Na+", 0.0), "strong_acid": g("Cl-", 0.0)}


class MixedAcetateCarbonateEquilibriumOperator(EquilibriumOperator):
    """Adapter: the verified coupled_equilibrium.solve(VinegarBicarbonateSystem) -- the mixed acetic-acid/acetate +
    carbonic-acid/bicarbonate/carbonate LIQUID speciation -- as a general EquilibriumOperator.  This is the operator
    the unified vinegar/bicarbonate world (XVIII-5) needs in a cell holding BOTH acid and inorganic carbon; because the
    wrapped solver handles the carbon=0 (pure acetate) and acetate=0 (pure carbonate) limits, ONE operator serves both
    cells before and after the valve opens -- no chemistry branch in the integrator.  The numerics are the existing
    coupled solver's, unchanged.  CO2(aq) is a LIQUID species here; its gas exchange is a separate Henry
    InterfaceTransfer in the coupled world, never folded into this closed-liquid speciation."""
    components = frozenset({"acetate", "carbon", "sodium"})
    species = ("HAc", "Ac-", "CO2(aq)", "HCO3-", "CO3-2", "H+", "OH-", "Na+")
    species_signature = {                                    # XVI-P0.2 (composition, charge) per returned species name
        "HAc": ((("C", 2), ("H", 4), ("O", 2)), 0),
        "Ac-": ((("C", 2), ("H", 3), ("O", 2)), -1),
        "CO2(aq)": ((("C", 1), ("O", 2)), 0),
        "HCO3-": ((("C", 1), ("H", 1), ("O", 3)), -1),
        "CO3-2": ((("C", 1), ("O", 3)), -2),
        "H+": ((("H", 1),), 1),
        "OH-": ((("H", 1), ("O", 1)), -1),
        "Na+": ((("Na", 1),), 1),
    }
    accepted_solver_verdicts = frozenset({                   # XVII-A1: the coupled solver's "the math closed" verdicts
        coupled_equilibrium.SOLVED_WITHIN_IDEAL_MODEL,
        coupled_equilibrium.SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    })

    def __init__(self, *, activity_model: str = "davies"):
        if activity_model not in ("ideal", "davies"):
            raise EquilibriumError("activity_model must be 'ideal' or 'davies'")
        self.activity_model = activity_model

    def descriptor(self) -> list:
        # XXIII-2b (F2): the activity model, the Ka/K1/K2/Kw records VinegarBicarbonateSystem supplies by default, and
        # the module constants coupled_equilibrium.solve reads at call time.
        return self._class_descriptor() + [
            ["activity_model", _canon(self.activity_model)],
            ["system_defaults", _dataclass_defaults(coupled_equilibrium.VinegarBicarbonateSystem,
                                                    ("Ka", "K1", "K2", "Kw"))],
            ["module_constants", _module_constants(coupled_equilibrium, ("DAVIES_A_25C", "C_REF"))],
        ]

    def speciate(self, component_amounts: dict, *, volume_L: float,
                 temperature_K: float = 298.15) -> EquilibriumState:
        self._validate(component_amounts, volume_L, temperature_K)
        acetate_mol = float(component_amounts.get("acetate", 0.0))
        carbon_mol = float(component_amounts.get("carbon", 0.0))
        sodium_mol = float(component_amounts.get("sodium", 0.0))
        V = float(volume_L)

        system = coupled_equilibrium.VinegarBicarbonateSystem(
            total_acetate_M=acetate_mol / V, total_carbon_M=carbon_mol / V, sodium_M=sodium_mol / V,
            activity_model=self.activity_model, T_K=temperature_K)          # T domain guarded by the wrapped solver
        res = coupled_equilibrium.solve(system)                             # the VERIFIED coupled numerics, verbatim

        amounts = {
            "HAc": res.hac_M * V, "Ac-": res.ac_minus_M * V, "CO2(aq)": res.co2aq_M * V,
            "HCO3-": res.hco3_M * V, "CO3-2": res.co3_M * V, "H+": res.h_plus_M * V,
            "OH-": res.oh_minus_M * V, "Na+": res.na_plus_M * V,
        }
        acetate_out = amounts["HAc"] + amounts["Ac-"]
        carbon_out = amounts["CO2(aq)"] + amounts["HCO3-"] + amounts["CO3-2"]
        sodium_out = amounts["Na+"]
        residuals = {"acetate": abs(acetate_out - acetate_mol), "carbon": abs(carbon_out - carbon_mol),
                     "sodium": abs(sodium_out - sodium_mol)}
        tol = 1e-9 * max(1.0, acetate_mol, carbon_mol, sodium_mol)
        structural_tier = STRUCTURALLY_CONSERVING if all(r <= tol for r in residuals.values()) else REFUSED

        derived = {
            "pH": res.pH, "pH_concentration": res.pH_concentration, "pH_activity": res.pH_activity,
            "ionic_strength_M": res.ionic_strength_M, "gamma_monovalent": res.gamma_monovalent,
            "charge_balance_residual": res.charge_balance_residual,
            "solver_agreement_residual": res.solver_agreement_residual,
        }
        return EquilibriumState(
            species_amounts=amounts, volume_L=V, temperature_K=float(temperature_K),
            component_inputs={"acetate": acetate_mol, "carbon": carbon_mol, "sodium": sodium_mol},
            component_residuals=residuals, derived=derived, structural_tier=structural_tier,
            solver_verdict=res.verdict,
            assumptions=("water is an implicit solvent reservoir; H+/OH- set by the acid/carbonate + water equilibria "
                         "and electroneutrality; CO2(aq) is a LIQUID species -- gas exchange is a separate Henry "
                         "interface, not folded into this closed-liquid speciation",),
            caveats=tuple(res.caveats))

    def component_totals(self, species_amounts: dict) -> dict:
        """acetate = HAc + Ac-; carbon = CO2(aq) + HCO3- + CO3-2; sodium = Na+ (the operator's own conservation law)."""
        g = species_amounts.get
        return {"acetate": g("HAc", 0.0) + g("Ac-", 0.0),
                "carbon": g("CO2(aq)", 0.0) + g("HCO3-", 0.0) + g("CO3-2", 0.0),
                "sodium": g("Na+", 0.0)}


# ============================================================================== XXIV-1A operator authority (F2-gap)
# RED (probe P1, receipt RED_receipt_7314e2a.json): XXIII-2b bound an operator's OWN descriptor() whenever it was defined
# on the operator's exact type -- so a caller-defined operator whose descriptor omitted an operative parameter (the
# X1:X2 partition fraction) was certified: two worlds with different physics shared ONE certificate, both ran under
# ``require_certified_execution`` with ``execution_identity_basis='AUDITED_BUILTIN'``, and a post-construction mutation of
# the omitted parameter ran certified.  The descriptor was a self-attested claim -- the same defect XXIII-2 closed for
# rate laws.  GREEN: the rate-law authority architecture, applied to operators:
#   AUDITED_BUILTIN            the CLOSED table below: (module, qualname) -> audit-closure digest of the reviewed source
#                              (class + in-tree bases + every helper / wrapped-solver function it references).  No public
#                              call adds to it; editing an audited operator or its solver without re-pinning DEMOTES it.
#   CALLER_ATTESTED_EXTENSION  ``register_attested_equilibrium_operator(cls, attested_by=...)``: the descriptor is bound
#                              (mutations of bound parameters are caught), but it is a CLAIM: never certified, refused
#                              under strict mode unless ``accept_attested_extensions=True``, tier floored.
#   UNVERIFIABLE               everything else -- INCLUDING an unaudited operator that defines its own descriptor().
# Exact type only (a subclass inherits nothing), a post-seal method swap or an instance-level override of speciate /
# descriptor / component_totals demotes.  HONEST BOUNDARY: an in-process trusted-code authority, NOT cryptographic and
# NOT independent validation of the operator's chemistry.
from experiments.sandbox_foundation.general_kernel import (  # noqa: E402  (placed with the authority it implements)
    AUDITED_BUILTIN, CALLER_ATTESTED_EXTENSION, UNVERIFIABLE_AUTHORITY, _audit_closure, _method_snapshot, _SealRecord,
    _seal_class)

_OPERATOR_METHODS = ("speciate", "descriptor", "component_totals")

#: The CLOSED operator audit table (XXIV-1A audit event, 2026-11-07).  Re-pin on any edit to the operator OR to a hashed
#: dependency (``audit_closure_inventory`` lists them; the wrapped solve() and its helpers are inside the closure).
_AUDITED_OPERATOR_PINS: dict = {
    ("experiments.sandbox_foundation.general_equilibrium", "AcetateWaterEquilibriumOperator"):
        "8fafc13be0224835e34f65f1d97179c814b4e98e27340f70110e223bbe39d8de",
    ("experiments.sandbox_foundation.general_equilibrium", "AmmoniaWaterEquilibriumOperator"):
        "538ef74ae69a5c2e4325e7c93f1f0c5fc444ce42bb516f273cbb500fcfa16440",
    ("experiments.sandbox_foundation.general_equilibrium", "MixedAcetateCarbonateEquilibriumOperator"):
        "604e23537ff0a34fcb18af090f8daad6c0f72166e98615daee8b9be8851a5e52",
}
_AUDITED_OPERATORS: dict = {}           # type -> _SealRecord (only _seal_audited_operator writes here)
_ATTESTED_OPERATORS: dict = {}          # type -> _SealRecord (register_attested_equilibrium_operator writes here)
_OPERATOR_AUDIT_FAILURES: dict = {}


def _check_operator_class(cls) -> None:
    if not (isinstance(cls, type) and issubclass(cls, EquilibriumOperator)):
        raise KernelError("expected an EquilibriumOperator subclass")
    for name in ("speciate", "descriptor"):
        if name not in cls.__dict__:
            raise KernelError(f"{cls.__qualname__} does not define its own {name}(); an inherited {name} does not "
                              f"describe this class's physics, so it cannot be audited or attested")


def _seal_audited_operator(cls):
    return _seal_class(cls, pins=_AUDITED_OPERATOR_PINS, sealed=_AUDITED_OPERATORS, failures=_OPERATOR_AUDIT_FAILURES,
                       methods=_OPERATOR_METHODS, check=_check_operator_class)


def register_attested_equilibrium_operator(cls, *, attested_by: str):
    """Register a plugin EquilibriumOperator as a CALLER-ATTESTED extension (a labeled claim, never an audit).  Its
    descriptor is bound into the world certificate, but ``execution_identity_certified`` stays False, strict mode
    refuses it unless ``accept_attested_extensions=True``, and the tier is floored.  Returns the class unchanged."""
    _check_operator_class(cls)
    if not (isinstance(attested_by, str) and attested_by.strip()):
        raise KernelError("register_attested_equilibrium_operator requires a non-empty attested_by")
    if (cls.__module__, cls.__qualname__) in _AUDITED_OPERATOR_PINS or cls in _AUDITED_OPERATORS:
        raise KernelError(f"{cls.__qualname__} is governed by the closed operator audit table; it cannot be attested")
    try:
        digest = _audit_closure(cls)[0]
    except (KernelError, OSError, SyntaxError):
        digest = "UNAVAILABLE"
    _ATTESTED_OPERATORS[cls] = _SealRecord(CALLER_ATTESTED_EXTENSION, _method_snapshot(cls, _OPERATOR_METHODS), digest,
                                           attested_by.strip())
    return cls


def equilibrium_operator_authority(op) -> str:
    """AUDITED_BUILTIN, CALLER_ATTESTED_EXTENSION or UNVERIFIABLE for an operator INSTANCE (exact type, intact methods,
    no instance-level override of an operative method)."""
    t = type(op)
    inst = getattr(op, "__dict__", {})
    if any(name in inst for name in _OPERATOR_METHODS):
        return UNVERIFIABLE_AUTHORITY
    for table in (_AUDITED_OPERATORS, _ATTESTED_OPERATORS):
        rec = table.get(t)
        if rec is not None:
            return rec.authority if _method_snapshot(t, _OPERATOR_METHODS) == rec.methods else UNVERIFIABLE_AUTHORITY
    return UNVERIFIABLE_AUTHORITY


def equilibrium_operator_attestation(cls) -> str:
    rec = _ATTESTED_OPERATORS.get(cls)
    return rec.attested_by if rec is not None else ""


def operator_audit_status() -> dict:
    sealed = {(t.__module__, t.__qualname__) for t in _AUDITED_OPERATORS}
    return {key: ("SEALED" if key in sealed else _OPERATOR_AUDIT_FAILURES.get(key, "NOT_LOADED"))
            for key in _AUDITED_OPERATOR_PINS}


assert AUDITED_BUILTIN  # re-exported authority token (the tier names are shared with the rate-law registry)
for _cls in (AcetateWaterEquilibriumOperator, AmmoniaWaterEquilibriumOperator, MixedAcetateCarbonateEquilibriumOperator):
    _seal_audited_operator(_cls)
del _cls
