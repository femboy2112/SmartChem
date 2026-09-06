"""M-5 -- the Experiment Compiler: a decompiler route assessed and rendered as an evidence dossier.

The decompiler (``smartchem.structure_descent`` / ``smartchem.decompiler``) answers *what could this
compound come apart into, conserving everything?*  Read backwards, a descent is an **assembly** -- a
candidate synthesis route.  This package takes such a route and does four things a working chemist
needs, each under one governing discipline.

Universality (the load-bearing design fact)
-------------------------------------------
This is a REASONING ENGINE over whatever sourced data it is given, not an encyclopedia of a few
compounds.  The formal layers -- conservation (E0), the composability *logic* (E1), the stoichiometric
ceiling (E2), equipment-from-declared-conditions -- run on ANY :class:`~smartchem.category.Molecule` the
SMILES front door parses, with no whitelist.  The *data* layers (stability thresholds, conditions) accept
any molecule, are injectable per call (a chemist brings the compound and its sourced facts), and degrade
to a LOUD ``UNKNOWN`` on a gap -- never a crash, never a silent guess.

The rungs
---------
* **E0 -- certify the step** (:mod:`.step`): reactants -> products conserving mass and charge
  (re-verified through :class:`~smartchem.category.Reaction`), carrying a *declared* (sourced) or
  *unknown* :class:`~smartchem.conditions.ConditionEnvelope`.
* **E1 -- verify composability** (:mod:`.composability`): does each intermediate *survive the transition*
  to the next step's conditions?  Constraint satisfaction over SOURCED stability windows, never a
  prediction: ``COMPOSABLE`` / ``DEGENERATE(reason)`` / ``UNKNOWN``.
* **E2 -- the stoichiometric ceiling** (:mod:`.ceiling`): the 100%-efficiency maximum by limiting
  reagent -- exact rational conservation, an idealised UPPER BOUND labelled as one (single-step and
  propagated over a whole route).
* **E3 -- attach the physical accounting** (:mod:`.accounting`): heat (established thermochemistry) plus
  temperature/pressure/time/solvent from SOURCED conditions, ``UNKNOWN`` where unsourced.
* **E4 -- draft the procedure** (:mod:`.drafter`) and infer the **equipment** (:mod:`.equipment`), plus
  the **constraint fitter**: given a target bench (max T, max P, reagents/equipment on hand) select the
  routes that fit and refuse the ones that do not.

Every number falls in exactly one :class:`~smartchem.experiment.bucket.Bucket` and says which.
"""
from __future__ import annotations

from .accounting import PhysicalAccounting, StepAccounting, account_route, account_step
from .assembly import (
    SynthesisAssemblyError,
    assemble_synthesis,
    find_scission,
    steps_from_scissions,
)
from .bucket import Bucket, Quantity, unknown
from .ceiling import (
    CeilingError,
    RouteCeiling,
    StoichiometricCeiling,
    route_ceiling,
    stoichiometric_ceiling,
)
from .classify import (
    Grade,
    UnifiedVerdict,
    classify,
    classify_dag,
    classify_reaction,
    classify_route,
    classify_step,
)
from .compile import CompiledSynthesis, compile_synthesis
from .formation import DerivedFormation, formation_enthalpy_0k
from .composability import (
    Composability,
    Transition,
    TransitionStatus,
    verify_composability,
)
from .dag import (
    DAGCeiling,
    DAGComposability,
    DAGError,
    DAGFlow,
    DAGShoppingRequirement,
    DAGThermoRollup,
    DAGVerification,
    ShoppingUnderdeterminedError,
    SynthesisDAG,
    dag_ceiling,
    dag_composability,
    dag_shopping_requirement,
    dag_thermo_rollup,
    verify_dag,
)
from .drafter import (
    ConstraintBox,
    DraftedProcedure,
    ProcedureReadiness,
    RouteDossier,
    RouteFit,
    RouteFitStatus,
    draft_route_dossier,
    draft_procedure,
    fit_route,
    fit_routes,
    rank_routes,
)
from .equilibrium import (
    EquilibriumExtent,
    RouteEquilibrium,
    StepEquilibrium,
    equilibrium_of_step,
    verify_equilibrium,
)
from .equipment import EquipmentItem, EquipmentKind, equipment_for_envelope, equipment_for_step
from .eyring import RouteEyring, StepEyring, eyring_of_step, rate_agreement, verify_eyring
from .feasibility import (
    FeasibilityDirection,
    FeasibilityGrade,
    RouteFeasibility,
    StepFeasibility,
    feasibility_of_step,
    verify_feasibility,
)
from .handling import (
    ByproductEntry,
    CareLevel,
    Fate,
    HazardFlag,
    RouteHandling,
    StepHandling,
    handling_of_dag,
    handling_of_step,
    verify_handling,
)
from .kinetics import (
    RateGrade,
    RateRegime,
    RouteKinetics,
    StepKinetics,
    kinetics_of_step,
    reaction_evidence_key,
    reaction_key_of,
    record_evidence_key,
    verify_kinetics,
    worst_regime,
)
from .routes import (
    DAGSearchReceipt,
    DAGSearchResult,
    RouteSearchReceipt,
    RouteSearchResult,
    SearchStatus,
    enumerate_dags,
    enumerate_routes,
    search_dags,
    search_routes,
)
from .selectivity import (
    RouteSelectivity,
    SelectivityRecord,
    SelectivityStatus,
    SelectivityTable,
    StepSelectivity,
    selectivity_of_step,
    verify_selectivity,
)
from .sourcing import (
    QuantityCoverage,
    RequirementSourcing,
    SourcingPlan,
    plan_sourcing,
)
from .step import ExperimentRoute, ExperimentStep, StepError
from .stock import (
    CostObservation,
    FitnessVerdict,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
    stock_material_from_commodity,
)

__all__ = [
    "Bucket",
    "Quantity",
    "unknown",
    "ExperimentStep",
    "ExperimentRoute",
    "StepError",
    "StockMaterial",
    "MaterialComponent",
    "StockQuantity",
    "CostObservation",
    "stock_material_from_commodity",
    "Phase",
    "FitnessVerdict",
    "DAGShoppingRequirement",
    "ShoppingUnderdeterminedError",
    "dag_shopping_requirement",
    "SourcingPlan",
    "RequirementSourcing",
    "QuantityCoverage",
    "plan_sourcing",
    "Transition",
    "TransitionStatus",
    "Composability",
    "verify_composability",
    "StoichiometricCeiling",
    "RouteCeiling",
    "CeilingError",
    "stoichiometric_ceiling",
    "route_ceiling",
    "StepAccounting",
    "PhysicalAccounting",
    "account_step",
    "account_route",
    "EquipmentItem",
    "EquipmentKind",
    "equipment_for_envelope",
    "equipment_for_step",
    "ConstraintBox",
    "RouteFit",
    "RouteFitStatus",
    "DraftedProcedure",
    "RouteDossier",
    "ProcedureReadiness",
    "fit_route",
    "fit_routes",
    "rank_routes",
    "draft_procedure",
    "draft_route_dossier",
    "enumerate_routes",
    "enumerate_dags",
    "search_routes",
    "search_dags",
    "SearchStatus",
    "RouteSearchReceipt",
    "RouteSearchResult",
    "DAGSearchReceipt",
    "DAGSearchResult",
    "SelectivityStatus",
    "SelectivityRecord",
    "SelectivityTable",
    "StepSelectivity",
    "RouteSelectivity",
    "selectivity_of_step",
    "verify_selectivity",
    "FeasibilityDirection",
    "FeasibilityGrade",
    "StepFeasibility",
    "RouteFeasibility",
    "feasibility_of_step",
    "verify_feasibility",
    "EquilibriumExtent",
    "StepEquilibrium",
    "RouteEquilibrium",
    "equilibrium_of_step",
    "verify_equilibrium",
    "RateRegime",
    "RateGrade",
    "StepKinetics",
    "RouteKinetics",
    "kinetics_of_step",
    "verify_kinetics",
    "reaction_key_of",
    "reaction_evidence_key",
    "record_evidence_key",
    "worst_regime",
    "RouteEyring",
    "StepEyring",
    "eyring_of_step",
    "verify_eyring",
    "rate_agreement",
    "Fate",
    "CareLevel",
    "ByproductEntry",
    "HazardFlag",
    "StepHandling",
    "RouteHandling",
    "handling_of_step",
    "handling_of_dag",
    "verify_handling",
    "SynthesisDAG",
    "DAGCeiling",
    "DAGComposability",
    "DAGVerification",
    "DAGThermoRollup",
    "DAGError",
    "DAGFlow",
    "dag_ceiling",
    "dag_composability",
    "verify_dag",
    "dag_thermo_rollup",
    "Grade",
    "UnifiedVerdict",
    "classify",
    "classify_step",
    "classify_reaction",
    "classify_route",
    "classify_dag",
    "CompiledSynthesis",
    "compile_synthesis",
    "DerivedFormation",
    "formation_enthalpy_0k",
    "SynthesisAssemblyError",
    "assemble_synthesis",
    "find_scission",
    "steps_from_scissions",
]
