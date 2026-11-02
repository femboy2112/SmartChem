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

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from experiments.sandbox_foundation import ammonia_equilibrium, aqueous_equilibrium, coupled_equilibrium
from experiments.sandbox_foundation.claim_tiers import REFUSED, STRUCTURALLY_CONSERVING
from experiments.sandbox_foundation.general_kernel import KernelError


class EquilibriumError(KernelError):
    """Fail-closed error for the general equilibrium interface."""


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
