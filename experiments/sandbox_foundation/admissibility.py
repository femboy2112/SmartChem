"""OPERATION XXIV-1B / 1C / 2A -- the PHYSICAL-ADMISSIBILITY contract shared by BOTH execution paths.

The standalone kernel (``ChemicalSystem.integrate``) and the coupled world (``CoupledWorld.integrate``) used to judge
positivity, charge and source domain with different, partly caller-controlled rules.  The probes in
``xxiv_p0_probes.py`` (receipt RED_receipt_7314e2a.json) showed three resulting false admissions.  This module is the
single implementation both paths now call.

1B  POSITIVITY (p6b).  The old floor was ``max(atol*100, 1e-10)`` (coupled) / ``max(atol*10, 1e-12)`` (kernel): the
    caller's SOLVER tolerance set the PHYSICAL admissibility tolerance, so widening atol turned a -0.5 mol inventory of a
    2 mol species into ``positivity_held=True`` + STRUCTURALLY_CONSERVING.  Solver error control and physical
    admissibility are now separate:
        physical floor_j = ABS_FLOOR(path) + POS_REL_FLOOR * scale_j        (caller-INDEPENDENT; scale_j = max_t |n_j|)
        solver band_j    = path_factor * atol + rtol * scale_j               (what the requested numerics can resolve)
    and every slot's deepest dip is classified
        HELD                                  min_j >= 0
        HELD_WITHIN_PHYSICAL_FLOOR            0 > min_j >= -floor_j
        UNRESOLVED_AT_REQUESTED_TOLERANCE     -floor_j > min_j >= -band_j   (the requested numerics cannot resolve the
                                                                              sign: NO positivity claim; tighten atol)
        VIOLATED                              min_j < -max(floor_j, band_j)
    ``positivity_held`` is True only for the first two.  Raw negative minima are PRESERVED in the receipt, never clipped.

1C  CHARGE.  Three DIFFERENT claims, reported separately by a typed ``ChargeValidity``:
      (a) reaction charge conservation   E_q N = 0, proven EXACTLY at system construction (ConservationError otherwise);
      (b) external charge accounting     the charge supplied through boundaries matches the charge row's ledger;
      (c) bulk electroneutrality         whether the solution is physically neutral.
    (a) and (b) can both hold while (c) fails: a bare Na+ feed with no counter-ion, electrode or external circuit is
    mathematically conserved against its ledger and PHYSICALLY UNSUPPORTED.  That is reported as
    UNSUPPORTED_EXTERNAL_NET_CHARGE and floors the ADMITTED tier to REFUSED on both paths; the structural tier keeps
    meaning "the declared mathematics conserved".  Charge SEPARATION by transport (coupled path, XXIII F3) remains a
    structural REFUSAL.  A charged INPUT (declared non-neutral initial state) is reported, not floored -- the run did
    not produce it.

2A  SOURCE-DOMAIN TEMPERATURE.  A law that executes a SourcedConstant sourced at T_src must not execute at a different
    world temperature with that constant unchanged.  No temperature law is validated in this sandbox, so a mismatch
    beyond ``TEMPERATURE_MATCH_TOL_K`` is REFUSED (``SourceDomainError``) on both paths -- no unvalidated extrapolation.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

POS_REL_FLOOR = 1e-9            # a dip nine orders below the species' own peak inventory is not physically significant
POSITIVITY_HELD = "HELD"
POSITIVITY_WITHIN_FLOOR = "HELD_WITHIN_PHYSICAL_FLOOR"
POSITIVITY_UNRESOLVED = "UNRESOLVED_AT_REQUESTED_TOLERANCE"
POSITIVITY_VIOLATED = "VIOLATED"
_POS_RANK = {POSITIVITY_HELD: 0, POSITIVITY_WITHIN_FLOOR: 1, POSITIVITY_UNRESOLVED: 2, POSITIVITY_VIOLATED: 3}

CHARGE_NOT_APPLICABLE = "NOT_APPLICABLE"
CHARGE_NEUTRAL_MAINTAINED = "NEUTRAL_MAINTAINED"
CHARGE_NEUTRALITY_IMPOSED = "NEUTRALITY_IMPOSED_BY_EQUILIBRIUM_OPERATOR"
CHARGE_DECLARED_NON_NEUTRAL = "DECLARED_NON_NEUTRAL_INPUT"
CHARGE_UNSUPPORTED_EXTERNAL = "UNSUPPORTED_EXTERNAL_NET_CHARGE"
CHARGE_SEPARATED = "SEPARATED_BY_TRANSPORT"
REACTION_CHARGE_EXACT = "EXACT_EqN_ZERO"

TEMPERATURE_MATCH_TOL_K = 0.01
SOURCE_DOMAIN_NONE = "NO_SOURCED_CONSTANTS"


@dataclass(frozen=True)
class PositivityAudit:
    verdict: str                 # HELD | HELD_WITHIN_PHYSICAL_FLOOR | UNRESOLVED_AT_REQUESTED_TOLERANCE | VIOLATED
    held: bool                   # verdict in (HELD, HELD_WITHIN_PHYSICAL_FLOOR)
    worst_slot: int              # index of the deepest RELATIVE breach (-1 if none negative)
    negative_minima: dict        # {slot index: raw min (mol)} for every slot that went negative -- never clipped
    floors: dict                 # {slot index: physical floor (mol)} for those slots
    bands: dict                  # {slot index: solver band (mol)} for those slots


def positivity_audit(slot_min, slot_scale, *, abs_floor: float, solver_atol: float, solver_rtol: float,
                     atol_factor: float) -> PositivityAudit:
    worst, worst_j, worst_ratio = POSITIVITY_HELD, -1, -1.0
    neg, floors, bands = {}, {}, {}
    for j, (m, sc) in enumerate(zip(slot_min, slot_scale)):
        m = float(m)
        if not m < 0.0:
            continue
        sc = abs(float(sc))
        floor_j = abs_floor + POS_REL_FLOOR * sc
        band_j = atol_factor * float(solver_atol) + float(solver_rtol) * sc
        neg[j], floors[j], bands[j] = m, floor_j, band_j
        if -m <= floor_j:
            v = POSITIVITY_WITHIN_FLOOR
        elif -m <= band_j:
            v = POSITIVITY_UNRESOLVED
        else:
            v = POSITIVITY_VIOLATED
        ratio = -m / floor_j
        if _POS_RANK[v] > _POS_RANK[worst] or (_POS_RANK[v] == _POS_RANK[worst] and ratio > worst_ratio):
            worst, worst_j, worst_ratio = v, j, ratio
    return PositivityAudit(worst, worst in (POSITIVITY_HELD, POSITIVITY_WITHIN_FLOOR), worst_j, neg, floors, bands)


@dataclass(frozen=True)
class ChargeValidity:
    """XXIV-1C: three distinct charge claims, never collapsed into one 'conserved' word."""
    reaction_charge_conservation: str        # EXACT_EqN_ZERO | NOT_APPLICABLE
    external_charge_supplied_mol: float      # signed charge (mol e) supplied through boundaries over the run
    external_charge_accounted: bool          # the charge ledger closed (the supplied charge is where the ledger says)
    bulk_electroneutrality: str              # see module docstring
    physically_supported: bool               # (c) holds: no net charge without a modeled carrier
    floors_admitted_tier: bool               # True iff this verdict REFUSES the admitted (physical) tier
    explanation: str


def charge_validity(*, charged: bool, supplied: float, accounted: bool, ionic_scale: float, declared_net: float,
                    separated: bool = False, imposed_by_operator: bool = False) -> ChargeValidity:
    """Classify (c) from the measured quantities; ``ionic_scale`` = sum |z_i n_i| that resolves a net charge."""
    if not charged:
        return ChargeValidity(CHARGE_NOT_APPLICABLE, 0.0, True, CHARGE_NOT_APPLICABLE, True, False,
                              "no charged species declared")
    tol = 1e-12 + 1e-6 * max(abs(ionic_scale), abs(supplied))
    if separated:
        return ChargeValidity(REACTION_CHARGE_EXACT, supplied, accounted, CHARGE_SEPARATED, False, True,
                              "transport moved a macroscopic net charge between compartments (an undeclared "
                              "capacitor); the trajectory is not a physical result")
    if abs(supplied) > tol:
        return ChargeValidity(REACTION_CHARGE_EXACT, supplied, accounted, CHARGE_UNSUPPORTED_EXTERNAL, False, True,
                              f"boundaries supplied a net {supplied:+.3e} mol of charge with no modeled counter-ion, "
                              f"electrode or external circuit: conserved against its ledger (claims a and b) but "
                              f"physically unsupported (claim c)")
    if imposed_by_operator:
        return ChargeValidity(REACTION_CHARGE_EXACT, supplied, accounted, CHARGE_NEUTRALITY_IMPOSED, True, False,
                              "electroneutrality is imposed by the fast-equilibrium operator against an implicit "
                              "neutral-solvent reservoir (a labeled approximation, see charge_balance_claim)")
    if abs(declared_net) > tol:
        return ChargeValidity(REACTION_CHARGE_EXACT, supplied, accounted, CHARGE_DECLARED_NON_NEUTRAL, False, False,
                              f"the DECLARED initial state carries a net {declared_net:+.3e} mol of charge; the run "
                              f"conserved it but did not produce it (reported, not floored)")
    return ChargeValidity(REACTION_CHARGE_EXACT, supplied, accounted, CHARGE_NEUTRAL_MAINTAINED, True, False,
                          "neutral input, no net external charge, reactions conserve charge exactly")


def law_source_temperatures(rate_law) -> tuple:
    """((field, T_K), ...) of every SourcedConstant a dataclass rate law carries (the constants it EXECUTES)."""
    from experiments.sandbox_foundation.aqueous_equilibrium import SourcedConstant
    if rate_law is None or not dataclasses.is_dataclass(rate_law):
        return ()
    out = []
    for f in dataclasses.fields(rate_law):
        v = getattr(rate_law, f.name, None)
        if type(v) is SourcedConstant and v.status != "UNKNOWN":
            out.append((f.name, float(v.T_K)))
    return tuple(out)


def temperature_domain_violations(reactions_by_owner, temperature_K: float) -> list:
    """[(owner, reaction, field, T_src)] for every sourced constant whose temperature differs from the execution
    temperature by more than TEMPERATURE_MATCH_TOL_K (no validated temperature law exists in this sandbox)."""
    bad = []
    for owner, rxn in reactions_by_owner:
        for fname, t_src in law_source_temperatures(rxn.rate_law):
            if not (math.isfinite(t_src) and abs(t_src - float(temperature_K)) <= TEMPERATURE_MATCH_TOL_K):
                bad.append((owner, rxn.name, fname, t_src))
    return bad


def source_domain_label(reactions_by_owner, temperature_K: float) -> str:
    temps = sorted({t for _, rxn in reactions_by_owner for _, t in law_source_temperatures(rxn.rate_law)})
    if not temps:
        return SOURCE_DOMAIN_NONE
    return (f"SUPPORTED: every sourced constant executes at its sourced temperature "
            f"({', '.join(f'{t:.2f}' for t in temps)} K vs world {float(temperature_K):.2f} K, tol "
            f"{TEMPERATURE_MATCH_TOL_K} K); within-formula-domain only -- NOT an empirical-validation claim")


# XXIV-2C: the four rungs of a physical claim -- each a DIFFERENT achievement; passing one never implies the next.
NUMERICALLY_EXECUTABLE = "NUMERICALLY_EXECUTABLE"                       # the solver ran and its receipts closed
WITHIN_DECLARED_FORMULA_DOMAIN = "WITHIN_DECLARED_FORMULA_DOMAIN"       # inputs inside the formula's declared limits
COMPARED_TO_REFERENCE_IMPLEMENTATION = "COMPARED_TO_REFERENCE_IMPLEMENTATION"   # agrees with another CODE (model-vs-model)
EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND = "EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND"  # agrees with an independent MEASUREMENT
CLAIM_LADDER = (NUMERICALLY_EXECUTABLE, WITHIN_DECLARED_FORMULA_DOMAIN, COMPARED_TO_REFERENCE_IMPLEMENTATION,
                EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND)
