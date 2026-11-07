"""OPERATION XXIII -- the versioned 2.0 simulation-API CANDIDATE (RESEARCH-ONLY).

    API_VERSION = "smartchem-sim-2.0a0-research"

READ THIS FIRST, PLAINLY: this module is NOT a stable API.  It is NOT in the wheel (it lives under ``experiments/``),
it is NOT covered by COMPATIBILITY.md, and any name, field or wire shape here may change or vanish without notice.
It is a research candidate for the OPERATION XXII §9 consumer surface (docs/research/OPERATION_XXII_2_0_API_GATE.md),
built ON TOP of the public behaviour of ``unified_chemical_world`` (build_unified_world, model_identity,
evidence_identity, the XX-4 restitch) and ``general_coupled`` (CoupledWorld.integrate + CoupledReceipt).  It does not
modify either.  (Ugh, yes, the disclaimer is long.  It's supposed to be.  Nobody gets to pip-install this by accident.)

THE SURFACE (the 9-point gate, research edition):
    SimulationSpec  = ModelSpec (world builder + UnifiedParams)
                    + initial inventories (one SpeciesInventory per (compartment, species), PHASE EXPLICIT per species)
                    + BoundarySchedule (ordered BoundaryPhase: duration_s, n_steps, transport_mode, vented|sealed)
                    + SolverOptions (scheme / rtol / atol / n_samples)
                    + Provenance (every constant/parameter: value, unit, source, tier SOURCED|DERIVED|ASSUMED) --
                      DERIVED by the spec from the params, never accepted from the caller (a label is not a binding).
    run(spec) -> SimulationResult  = immutable sampled Frames + per-phase PhaseReceipts + StitchEvents + identities.

THE FIVE LAYERS -- kept SEPARATE on purpose, because every one of them is a different kind of claim:
    1. EXACT CONSERVATION     -- a STRUCTURAL LAW: E.N = 0 holds for every declared reaction at construction, in exact
                                 integer arithmetic.  ``structural_conservation_check`` re-derives it here, from the
                                 built world's own species compositions.  It is a theorem about the declaration, not
                                 a property of any trajectory.
    2. NUMERICAL CONSERVATION -- ERROR-BOUNDED RECEIPT VERDICTS (per-component VERIFIED_WITHIN_RESOLUTION / VIOLATED /
                                 NUMERICALLY_UNRESOLVED_AT_REQUESTED_SCALE), measured by the integrator over every
                                 accepted step.  A verdict about a computation, not about chemistry.
    3. RATE-LAW IDENTITY      -- certified ONLY relative to the audited authority (general_kernel's closed audit
                                 table); we surface ``execution_identity_basis`` verbatim and never upgrade it.
    4. CALIBRATION            -- an EMPIRICAL claim.  Nothing here is calibrated: k_diss / kLa / k_export / k_valve are
                                 ASSUMED and the dynamic claim tier is capped accordingly.
    5. VISUAL OUTPUT          -- a PROJECTION of these frames.  Never evidence.  Nothing a renderer draws can flow
                                 back into a Frame, a receipt or an identity (frames are frozen; there is no write
                                 path).

COMPOSITION LAWS (what holds and what does NOT -- tested in tests/test_sim_api_v2alpha.py):
    (a) PHASE CONCATENATION holds: run([p1, p2]) == run([p1]) then run([p2]) from p1's STITCHED final state, up to
        (and including) the recorded stitch events.  The integrator is deterministic and re-projects its initial
        state, so the equality is bitwise.
    (b) TIME-SPLITTING is NOT a monoid homomorphism in general.  Cutting [0, T] into two phases is exact only up to the
        re-projection roundoff when the cut lands on the macro-step grid at an unchanged dt; when the pieces carry
        their own n_steps (so dt changes) the results differ by the O(dt) operator-splitting error, which SHRINKS
        under refinement but is NOT zero.  We do NOT claim a functor for numerical dynamics.
    (c) OBSERVER INVARIANCE holds: n_samples (frame cadence) changes neither the final state nor any receipt verdict
        (XX-3: verification cadence is split from sampling cadence).  The RUN identity therefore excludes n_samples;
        the cadence lives in a separate OBSERVATION identity.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType

from experiments.sandbox_foundation.carbonate_equilibrium import KH_CO2_25C, R_GAS_L_ATM
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER, weakest
from experiments.sandbox_foundation.coupled_equilibrium import (
    K1_CARBONIC_25C,
    K2_CARBONIC_25C,
    KA_ACETIC_25C,
    KW_25C,
)
from experiments.sandbox_foundation.general_coupled import _canon_num, _species_key
from experiments.sandbox_foundation.solid_bicarbonate import KSP_NAHCO3_25C
from experiments.sandbox_foundation.unified_chemical_world import (
    Phase_,
    UnifiedParams,
    _build_species,
    _component_totals,
    _require_params,
    _restitch,
    build_unified_world,
    evidence_identity,
    model_identity,
)

API_VERSION = "smartchem-sim-2.0a0-research"

#: provenance tiers (the spec-level vocabulary; DISTINCT from the claim_tiers ladder, which grades RESULTS)
PROVENANCE_TIERS = ("SOURCED", "DERIVED", "ASSUMED")
TRANSPORT_MODES = ("closed", "membrane", "bulk")
SCHEMES = ("lie", "strang")

LAYERS = MappingProxyType({
    "exact_conservation": "STRUCTURAL LAW: E.N = 0 per declared reaction, exact integers, at construction",
    "numerical_conservation": "ERROR-BOUNDED RECEIPT VERDICTS per component, measured over every accepted step",
    "rate_law_identity": "CERTIFIED ONLY RELATIVE TO THE AUDITED AUTHORITY (execution_identity_basis, verbatim)",
    "calibration": "EMPIRICAL CLAIM -- none made here: every dynamic coefficient is ASSUMED",
    "visual_output": "PROJECTION of frames -- never evidence; no write path back into the model",
})


class SimulationSpecError(ValueError):
    """A SimulationSpec that cannot be run as declared.  Raised at construction, never silently defaulted."""


# ============================================================ the spec
@dataclass(frozen=True)
class SpeciesInventory:
    """One initial inventory entry.  ``phase`` is EXPLICIT (aqueous | gas | solid | pure_liquid) and must match the
    declared species' phase -- a caller cannot put 'CO2(g)' in a liquid cell or call NaHCO3(s) aqueous."""
    compartment: str
    species: str
    phase: str
    amount_mol: float


@dataclass(frozen=True)
class BoundaryPhase:
    """One phase of the boundary schedule: how long, how finely, and what the boundary IS during it."""
    name: str
    duration_s: float
    n_steps: int
    transport_mode: str = "closed"     # A<->B mechanism: closed | membrane | bulk
    vented: bool = True                # True = open vessel (CO2 export boundary on the gas); False = sealed headspace

    @property
    def sealed(self) -> bool:
        return not self.vented


@dataclass(frozen=True)
class BoundarySchedule:
    phases: tuple                      # (BoundaryPhase, ...), ordered


@dataclass(frozen=True)
class SolverOptions:
    scheme: str = "strang"
    rtol: float = 1e-10
    atol: float = 1e-14
    n_samples: int | None = None       # frames per phase (None = every macro-step).  Observation only (law c).


@dataclass(frozen=True)
class ProvenanceEntry:
    name: str
    value: float
    unit: str
    source: str
    tier: str                          # SOURCED | DERIVED | ASSUMED
    detail: str = ""                   # the underlying SourcedConstant status/caveat, when there is one


@dataclass(frozen=True)
class Provenance:
    entries: tuple                     # (ProvenanceEntry, ...)

    def by_name(self) -> dict:
        return {e.name: e for e in self.entries}

    def assumed(self) -> tuple:
        return tuple(e for e in self.entries if e.tier == "ASSUMED")


@dataclass(frozen=True)
class ModelSpec:
    """The model inputs: WHICH world builder, with WHICH parameters.  One builder is registered today (the unified
    vinegar/bicarbonate world); the registry is the seam where a second chemistry consumer would plug in."""
    world: str = "unified_vinegar_bicarbonate"
    params: UnifiedParams = field(default_factory=UnifiedParams)


def _sc_entry(const, *, name: str) -> ProvenanceEntry:
    status = const.status
    tier = {"SOURCED": "SOURCED", "DERIVED": "DERIVED", "EXACT": "SOURCED"}.get(status, "ASSUMED")
    detail = f"SourcedConstant status={status}" + ("; exact by definition" if status == "EXACT" else "")
    if const.note:
        detail += f"; {const.note}"
    return ProvenanceEntry(name, float(const.value), const.units, const.source, tier, detail)


def derive_provenance(params: UnifiedParams) -> Provenance:
    """Every constant and parameter the unified world actually executes with, tiered.  Derived from the params and
    the sourced-constant objects themselves -- the caller never supplies a tier."""
    assumed = "ASSUMED synthetic coefficient (CALIBRATION_REQUIRED per apparatus) -- unified_chemical_world.UnifiedParams"
    scen = "declared scenario geometry/condition (caller input, not a physical constant)"
    entries = (
        _sc_entry(KA_ACETIC_25C, name="Ka_acetic_25C"),
        _sc_entry(K1_CARBONIC_25C, name="K1_carbonic_25C"),
        _sc_entry(K2_CARBONIC_25C, name="K2_carbonic_25C"),
        _sc_entry(KW_25C, name="Kw_25C"),
        _sc_entry(KH_CO2_25C, name="KH_CO2_25C"),
        _sc_entry(R_GAS_L_ATM, name="R_gas_L_atm"),
        _sc_entry(KSP_NAHCO3_25C, name="Qsp_NaHCO3_empirical"),
        ProvenanceEntry("k_diss", float(params.k_diss_molpLps), "mol/L/s", assumed, "ASSUMED"),
        ProvenanceEntry("kLa", float(params.kLa_per_s), "1/s", assumed, "ASSUMED"),
        ProvenanceEntry("k_export", float(params.k_export_Lps), "L/s", assumed, "ASSUMED"),
        ProvenanceEntry("k_valve", float(params.k_valve_Lps), "L/s", assumed + " (membrane k / bulk Q)", "ASSUMED"),
        ProvenanceEntry("V_A", float(params.V_A_L), "L", scen, "ASSUMED"),
        ProvenanceEntry("V_B", float(params.V_B_L), "L", scen, "ASSUMED"),
        ProvenanceEntry("V_gas", float(params.V_gas_L), "L", scen, "ASSUMED"),
        ProvenanceEntry("temperature", float(params.temperature_K), "K", scen + "; must sit in the 25 C domain",
                        "ASSUMED"),
    )
    for e in entries:
        if e.tier not in PROVENANCE_TIERS:
            raise SimulationSpecError(f"provenance tier {e.tier!r} for {e.name!r} is not one of {PROVENANCE_TIERS}")
    return Provenance(entries)


def _species_catalog() -> dict:
    """{name: kernel Species} for the unified world's shared species objects."""
    sp = _build_species()
    return {s.name: s for s in sp.__dict__.values()}


_WORLD_BUILDERS = {"unified_vinegar_bicarbonate"}


@dataclass(frozen=True)
class SimulationSpec:
    model: ModelSpec
    initial: tuple                         # (SpeciesInventory, ...)
    schedule: BoundarySchedule
    solver: SolverOptions = field(default_factory=SolverOptions)
    provenance: Provenance = field(init=False)   # DERIVED -- never caller-supplied (a label is not a binding)

    def __post_init__(self):
        # fail closed on everything we can check before integrating -- a spec either runs as declared or is refused
        if self.model.world not in _WORLD_BUILDERS:
            raise SimulationSpecError(f"unknown world builder {self.model.world!r}; registered: {sorted(_WORLD_BUILDERS)}")
        try:
            _require_params(self.model.params)
        except ValueError as exc:          # OutOfSourceDomainError is a ValueError too; re-typed, message kept
            raise SimulationSpecError(str(exc)) from exc
        _validate_schedule(self.schedule)
        _validate_solver(self.solver)
        _validate_initial(self.initial)
        object.__setattr__(self, "provenance", derive_provenance(self.model.params))


def _validate_schedule(schedule) -> None:
    if type(schedule) is not BoundarySchedule or not isinstance(schedule.phases, tuple) or not schedule.phases:
        raise SimulationSpecError("schedule must be a BoundarySchedule with a non-empty tuple of BoundaryPhase")
    names = set()
    for p in schedule.phases:
        if type(p) is not BoundaryPhase:
            raise SimulationSpecError(f"every phase must be a BoundaryPhase (got {type(p).__name__})")
        if p.name in names:
            raise SimulationSpecError(f"duplicate phase name {p.name!r}")
        names.add(p.name)
        if isinstance(p.duration_s, bool) or not (isinstance(p.duration_s, (int, float))
                                                  and math.isfinite(p.duration_s) and p.duration_s > 0):
            raise SimulationSpecError(f"phase {p.name!r}: duration_s must be finite and > 0")
        if isinstance(p.n_steps, bool) or not (isinstance(p.n_steps, int) and p.n_steps >= 1):
            raise SimulationSpecError(f"phase {p.name!r}: n_steps must be an int >= 1")
        if p.transport_mode not in TRANSPORT_MODES:
            raise SimulationSpecError(f"phase {p.name!r}: transport_mode must be one of {TRANSPORT_MODES}")
        if type(p.vented) is not bool:
            raise SimulationSpecError(f"phase {p.name!r}: vented must be a bool")


def _validate_solver(s) -> None:
    if type(s) is not SolverOptions:
        raise SimulationSpecError("solver must be a SolverOptions")
    if s.scheme not in SCHEMES:
        raise SimulationSpecError(f"scheme must be one of {SCHEMES} (monolithic is undefined with a projection)")
    for nm in ("rtol", "atol"):
        v = getattr(s, nm)
        if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
            raise SimulationSpecError(f"{nm} must be finite and > 0")
    if s.n_samples is not None and (isinstance(s.n_samples, bool) or not isinstance(s.n_samples, int)
                                    or s.n_samples < 1):
        raise SimulationSpecError("n_samples must be None or an int >= 1")


def _validate_initial(initial) -> None:
    if not isinstance(initial, tuple):
        raise SimulationSpecError("initial must be a tuple of SpeciesInventory")
    cat = _species_catalog()
    allowed = _compartment_species()
    seen = set()
    for inv in initial:
        if type(inv) is not SpeciesInventory:
            raise SimulationSpecError(f"initial entries must be SpeciesInventory (got {type(inv).__name__})")
        if inv.species not in cat:
            raise SimulationSpecError(f"unknown species {inv.species!r}; declared: {sorted(cat)}")
        declared_phase = cat[inv.species].phase.value
        if inv.phase != declared_phase:
            raise SimulationSpecError(f"species {inv.species!r} is declared {declared_phase!r}, not {inv.phase!r} -- "
                                      f"phase is part of chemical identity and is never coerced")
        if inv.compartment not in allowed:
            raise SimulationSpecError(f"unknown compartment {inv.compartment!r}; declared: {sorted(allowed)}")
        if inv.species not in allowed[inv.compartment]:
            raise SimulationSpecError(f"species {inv.species!r} does not live in compartment {inv.compartment!r}")
        key = (inv.compartment, inv.species)
        if key in seen:
            raise SimulationSpecError(f"duplicate initial inventory for {key}")
        seen.add(key)
        v = inv.amount_mol
        if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
            raise SimulationSpecError(f"initial amount for {key} must be a finite mol value >= 0 (got {v!r})")


def _compartment_species() -> dict:
    """{compartment: set(species name)} as the unified world declares them (built once, mode-independent)."""
    b = build_unified_world(UnifiedParams(), _build_species(), sealed=True, transport_mode="closed")
    return {c.name: {s.name for s in c.system.species} for c in b.world.compartments}


# ============================================================ result types (all frozen; no write path)
def _freeze_map(d) -> MappingProxyType:
    return MappingProxyType({k: (_freeze_map(v) if isinstance(v, dict) else v) for k, v in d.items()})


@dataclass(frozen=True)
class Frame:
    """ONE immutable sampled observation.  ``amounts`` maps (compartment, species name) -> mol (the CANONICAL state);
    ``derived`` maps compartment -> the equilibrium solver's AUTHORITATIVE derived scalars (pH_activity, ...) captured
    from the projection that produced this sample.  Read-only by construction (MappingProxyType)."""
    api_version: str
    index: int
    time_s: float                      # global clock
    phase: str
    phase_index: int
    phase_time_s: float                # clock within the phase
    amounts: MappingProxyType
    derived: MappingProxyType

    def amount(self, compartment: str, species: str) -> float:
        return self.amounts[(compartment, species)]


@dataclass(frozen=True)
class PhaseReceipt:
    """The frozen, renderer-neutral projection of one phase's CoupledReceipt (numerical + scientific)."""
    phase: str
    admitted_tier: str
    structural_tier: str
    declared_kinetic_tier: str
    material_balance_closed: bool
    positivity_held: bool
    min_inventory: float
    component_resolution: MappingProxyType
    component_max_residual: MappingProxyType
    component_tolerance: MappingProxyType
    external_flux: MappingProxyType          # {component: integrated E.q_ext over the phase} (the XVIII-3 ledger)
    raw_material_change: MappingProxyType
    reservoir_exchange: MappingProxyType
    charge_balance_claim: str
    execution_identity_certified: bool
    execution_identity_basis: str            # verbatim from the integrator -- never upgraded here
    numerically_unresolved_components: tuple
    caveats: tuple


@dataclass(frozen=True)
class StitchEvent:
    """An explicit numerical adjustment applied when a phase's final state is re-packed (XX-4 restitch): a negative
    inventory within the roundoff budget clamped to 0.  A numerical event -- NOT chemistry, NOT boundary flux."""
    after_phase: str
    time_s: float
    compartment: str
    species: str
    added_mol: float
    budget_mol: float
    element_impact: MappingProxyType
    charge_impact: float


@dataclass(frozen=True)
class SimulationResult:
    api_version: str
    spec: SimulationSpec
    frames: tuple                            # (Frame, ...)
    receipts: tuple                          # (PhaseReceipt, ...), one per phase
    stitch_events: tuple                     # (StitchEvent, ...)
    stitched_final: MappingProxyType         # (compartment, species) -> mol after the LAST phase's restitch
    structural_conservation: MappingProxyType
    admitted_tier: str                       # weakest over the phase receipts
    identities: MappingProxyType             # model / run / evidence / observation (dicts + digests)
    layers: MappingProxyType = LAYERS

    @property
    def final_frame(self) -> Frame:
        return self.frames[-1]


# ============================================================ identities
def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _legacy_phases(schedule: BoundarySchedule) -> tuple:
    """Map onto the flagship Phase_ so model_identity/evidence_identity are REUSED, not re-implemented.  The legacy
    topology encodes only valve_open (membrane) + sealed, so the v2 identity ALSO binds the full transport mode."""
    return tuple(Phase_(p.name, valve_open=(p.transport_mode != "closed"), sealed=p.sealed,
                        duration_s=float(p.duration_s), n_steps=int(p.n_steps)) for p in schedule.phases)


def spec_identities(spec: SimulationSpec) -> dict:
    """MODEL (physics + boundary topology), RUN (model + initial value problem + solver, NOT the frame cadence),
    EVIDENCE (provenance/scope), OBSERVATION (frame cadence only).  All lossless (float.hex) and JSON-canonical."""
    params = spec.model.params
    legacy = _legacy_phases(spec.schedule)
    model = {
        "api_version": API_VERSION,
        "world": spec.model.world,
        "unified_model_identity": model_identity(params, legacy),        # reused verbatim
        "phase_topology_v2": [[p.name, p.transport_mode, bool(p.vented)] for p in spec.schedule.phases],
    }
    cat = _species_catalog()
    run_ = {
        "model": model,
        "initial_inventories": sorted([inv.compartment, list(_species_key(cat[inv.species])), _canon_num(inv.amount_mol)]
                                      for inv in spec.initial),
        "schedule": [[p.name, _canon_num(p.duration_s), int(p.n_steps)] for p in spec.schedule.phases],
        "solver": {"scheme": spec.solver.scheme, "rtol": _canon_num(spec.solver.rtol),
                   "atol": _canon_num(spec.solver.atol)},
    }
    evidence = {
        "unified_evidence_identity": evidence_identity(params),            # reused verbatim
        "provenance": [[e.name, _canon_num(e.value), e.unit, e.tier, e.source] for e in spec.provenance.entries],
    }
    observation = {"run_digest": _digest(run_), "n_samples": spec.solver.n_samples}
    return {
        "model": model, "run": run_, "evidence": evidence, "observation": observation,
        "model_digest": _digest(model), "run_digest": _digest(run_),
        "evidence_digest": _digest(evidence), "observation_digest": _digest(observation),
    }


# ============================================================ layer 1: the structural law, re-derived exactly
def structural_conservation_check(world) -> dict:
    """E.N = 0 for every declared reaction of every compartment, recomputed here in EXACT integer arithmetic from the
    species compositions (the kernel already refuses an unbalanced reaction at ChemicalSystem construction; this is
    the independent re-derivation that the API surfaces, not a trajectory measurement)."""
    out = {}
    for c in world.compartments:
        for r in c.system.reactions:
            bal = {}
            for s, coeff in r.stoich:
                for el, cnt in s.composition:
                    bal[el] = bal.get(el, 0) + coeff * cnt
                bal["charge"] = bal.get("charge", 0) + coeff * s.charge
            out[f"{c.name}:{r.name}"] = all(v == 0 for v in bal.values())
    return {"law": "E.N == 0 (exact integers)", "reactions": out, "holds": all(out.values())}


# ============================================================ run
def _initial_state_dict(spec: SimulationSpec, cat: dict) -> dict:
    state = {"A": {}, "B": {}, "gas": {}}
    for inv in spec.initial:
        state.setdefault(inv.compartment, {})[cat[inv.species]] = float(inv.amount_mol)
    return state


def _phase_receipt(name: str, traj) -> PhaseReceipt:
    rc = traj.receipt
    return PhaseReceipt(
        phase=name, admitted_tier=rc.admitted_tier, structural_tier=rc.structural_tier,
        declared_kinetic_tier=rc.declared_kinetic_tier, material_balance_closed=bool(rc.material_balance_closed),
        positivity_held=bool(rc.positivity_held), min_inventory=float(rc.min_inventory),
        component_resolution=_freeze_map(dict(rc.component_resolution)),
        component_max_residual=_freeze_map({k: float(v) for k, v in rc.component_max_residual.items()}),
        component_tolerance=_freeze_map({k: float(v) for k, v in rc.component_tolerance.items()}),
        external_flux=_freeze_map({k: float(v) for k, v in rc.external_flux.items()}),
        raw_material_change=_freeze_map({k: float(v) for k, v in rc.raw_material_change.items()}),
        reservoir_exchange=_freeze_map({k: float(v) for k, v in rc.reservoir_exchange.items()}),
        charge_balance_claim=rc.charge_balance_claim,
        execution_identity_certified=bool(rc.execution_identity_certified),
        execution_identity_basis=rc.execution_identity_basis,
        numerically_unresolved_components=tuple(rc.numerically_unresolved_components),
        caveats=tuple(traj.caveats))


def build_phase_world(spec: SimulationSpec, phase: BoundaryPhase):
    """The CoupledWorld for one phase (exposed so a consumer can inspect the declared topology)."""
    return build_unified_world(spec.model.params, _build_species(), sealed=phase.sealed,
                               transport_mode=phase.transport_mode).world


def run(spec: SimulationSpec) -> SimulationResult:
    """Integrate the schedule through the ONE generic integrator, stitching each phase's final state into the next
    (bounded roundoff clamps recorded as StitchEvents; a real positivity excursion is refused)."""
    if type(spec) is not SimulationSpec:
        raise SimulationSpecError("run() takes a SimulationSpec")
    cat = _species_catalog()
    sp = _build_species()
    # the build path: _build_species() mints equal-valued Species each call; key on the canonical objects of `sp`
    by_name = {s.name: s for s in sp.__dict__.values()}
    state = {c: {by_name[s.name]: v for s, v in inv.items()} for c, inv in _initial_state_dict(spec, cat).items()}
    params = spec.model.params
    vols = {"A": params.V_A_L, "B": params.V_B_L, "gas": params.V_gas_L}

    frames, receipts, events = [], [], []
    structural = None
    t0 = 0.0
    for k, ph in enumerate(spec.schedule.phases):
        world = build_unified_world(params, sp, sealed=ph.sealed, transport_mode=ph.transport_mode).world
        if structural is None:
            structural = structural_conservation_check(world)
        traj = world.integrate(state, duration=float(ph.duration_s), n_steps=int(ph.n_steps),
                               scheme=spec.solver.scheme, rtol=spec.solver.rtol, atol=spec.solver.atol,
                               n_samples=spec.solver.n_samples)
        for j, t in enumerate(traj.times):
            amounts = {(c, s.name): float(traj.amounts[c][j][s]) for c in traj.compartments for s in traj.amounts[c][j]}
            derived = {c: _freeze_map({kk: vv for kk, vv in traj.equilibrium_derived[c][j].items()
                                       if isinstance(vv, (str, int, float, bool, type(None)))})
                       for c in traj.compartments}
            frames.append(Frame(API_VERSION, len(frames), float(t0 + t), ph.name, k, float(t),
                                MappingProxyType(amounts), MappingProxyType(derived)))
        receipts.append(_phase_receipt(ph.name, traj))
        last = {c: traj.amounts[c][-1] for c in traj.compartments}
        state, _ct, _cm, violations, adj = _restitch(last, vols)       # reused verbatim (XX-4)
        if violations:
            w = min(violations, key=lambda v: v[2])
            raise SimulationSpecError(f"phase {ph.name!r} ended with a REAL positivity excursion "
                                      f"({w[0]}/{w[1]} = {w[2]:.3e} mol > budget {w[3]:.3e}); refused, not clipped")
        for ev in adj:
            events.append(StitchEvent(ph.name, float(t0 + ph.duration_s), ev["compartment"], ev["species"],
                                      float(ev["added_mol"]), float(ev["budget"]),
                                      _freeze_map(dict(ev["element_impact"])), float(ev["charge_impact"])))
        t0 += float(ph.duration_s)

    stitched = MappingProxyType({(c, s.name): float(v) for c, inv in state.items() for s, v in inv.items()})
    ids = spec_identities(spec)
    return SimulationResult(
        api_version=API_VERSION, spec=spec, frames=tuple(frames), receipts=tuple(receipts),
        stitch_events=tuple(events), stitched_final=stitched,
        structural_conservation=_freeze_map(structural),
        admitted_tier=weakest(*[r.admitted_tier for r in receipts]) if receipts else ASSUMED_PARAMETER,
        identities=_freeze_map(ids))


# ============================================================ composition helpers
def continue_from(spec: SimulationSpec, result: SimulationResult, schedule: BoundarySchedule) -> SimulationSpec:
    """A new spec whose initial inventories are ``result``'s STITCHED final state (law a's right-hand side).  Phases
    come from the catalog, so the explicit per-species phase is re-derived, not guessed."""
    cat = _species_catalog()
    initial = tuple(SpeciesInventory(c, s, cat[s].phase.value, float(v))
                    for (c, s), v in sorted(result.stitched_final.items()))
    return SimulationSpec(model=spec.model, initial=initial, schedule=schedule, solver=spec.solver)


def global_totals(frame: Frame) -> dict:
    """E.n over every compartment for one frame (element + charge totals) -- the same map the ledger uses."""
    cat = _species_catalog()
    state = {}
    for (c, s), v in frame.amounts.items():
        state.setdefault(c, {})[cat[s]] = v
    return _component_totals(state)


# ============================================================ wire
def _plain(obj):
    if isinstance(obj, MappingProxyType) or isinstance(obj, dict):
        return {(("/".join(k)) if isinstance(k, tuple) else str(k)): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def frame_to_dict(f: Frame) -> dict:
    return {"api_version": f.api_version, "index": f.index, "time_s": f.time_s, "phase": f.phase,
            "phase_index": f.phase_index, "phase_time_s": f.phase_time_s,
            "amounts_mol": _plain(f.amounts), "derived": _plain(f.derived)}


def receipt_to_dict(r: PhaseReceipt) -> dict:
    return {k: _plain(getattr(r, k)) for k in r.__dataclass_fields__}


def result_to_dict(res: SimulationResult) -> dict:
    """Strict-JSON wire form (allow_nan=False safe).  Stamped with API_VERSION at the top and on every frame."""
    return {
        "api_version": res.api_version,
        "stability": "RESEARCH-ONLY candidate; not stable, not in the wheel, not covered by COMPATIBILITY.md",
        "layers": dict(res.layers),
        "provenance": [e.__dict__ for e in res.spec.provenance.entries],
        "frames": [frame_to_dict(f) for f in res.frames],
        "receipts": [receipt_to_dict(r) for r in res.receipts],
        "stitch_events": [_plain(e.__dict__) for e in res.stitch_events],
        "stitched_final": _plain(res.stitched_final),
        "structural_conservation": _plain(res.structural_conservation),
        "admitted_tier": res.admitted_tier,
        "identities": _plain(res.identities),
    }
