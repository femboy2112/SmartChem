"""OPERATION XIII P3 -- the TWO-CELL reactive vinegar/bicarbonate world.

`living_chamber.py` transports neutral acetic acid across a membrane between two acetate/water cells.  This module
is its mixed-chemistry sibling: two liquid cells each carrying the coupled vinegar+carbonate inventory, connected by
a boundary that supports the two physically-honest transport modes section 5 names, with every internal transfer
cancelling in the global conservation ledger.

STATE = THE CONSERVED COMPONENT INVENTORY, NOT FREE SPECIES.  Each cell carries only its analytical totals -- total
acetate, total inorganic carbon, sodium (mol) and liquid volume (L) -- at a declared temperature.  The eight
concentrations ([HAc],[Ac-],[CO2aq],[HCO3-],[CO3],[H+],[OH-],[Na+]) are a pure function E(b) of the totals,
delivered by the coupled closed solver (fast acid-base equilibrium).  Volume/concentration are in LITERS / mol·L^-1
throughout (no mol/m^3 hinge; a single consistent unit system).

TWO TRANSPORT MODES (section 5):

  A. SELECTIVE DIFFUSION of the NEUTRAL carriers only -- neutral acetic acid HAc and dissolved CO2(aq):
        J_HAc = g_HAc * valve * (c_HAc[A] - c_HAc[B])      [mol/s]        (carries TOTAL ACETATE)
        J_CO2 = g_CO2 * valve * (c_CO2aq[A] - c_CO2aq[B])  [mol/s]        (carries TOTAL INORGANIC CARBON)
     Charged species (Na+, Ac-, HCO3-, CO3-2, H+, OH-) are NEVER given independent Fick fluxes while local
     electroneutrality is asserted -- that is the Nernst-Planck obstruction (living_chamber / interface E3).  So
     sodium does not cross a diffusive membrane at all, and the acetate/carbon that cross do so only as their
     neutral forms.  Equal-and-opposite -> global acetate and global carbon are invariant; sodium is per-cell fixed.

  B. BULK LIQUID EXCHANGE / MIXING -- a pairwise swap of equal, locally-electroneutral solution parcels:
     exchange a volume dV = r * valve * dt between the cells, each parcel carrying its donor cell's OWN balanced
     composition (all components in proportion).  A balanced parcel preserves charge WITHOUT solving Nernst-Planck
     (interface E3's admissible route), and the symmetric swap keeps both cell volumes fixed.  Each component:
        dn[A] = dV * (C[B] - C[A]),   dn[B] = -dn[A]      for acetate, carbon AND sodium.

ACCEPTED STEP: read totals -> speciate -> compute the mode's transfer -> apply ONE equal-and-opposite component
pair per quantity -> enforce nonnegative totals and a dt bound (a step that would export more than a donor holds is
REFUSED or SUBSTEPPED, never silently truncated) -> re-equilibrate both cells -> verify global conservation + local
charge closure.  Rendering is a pure read; the trajectory is independent of sampling frequency.

NOT a kinetic reaction rate: HAc<->Ac- / the carbonate speciation are ALGEBRAIC local-equilibrium projections.  The
only time-dependent processes are the declared, passive transport laws.  Exchange coefficients (g_HAc, g_CO2, r) are
PRESCRIBED physical parameters (claim_tiers.ASSUMED_PARAMETER) until calibrated.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.aqueous_equilibrium import InvalidParameterError
from experiments.sandbox_foundation.coupled_gas_equilibrium import MixedGasResult, MixedGasSystem
from experiments.sandbox_foundation.coupled_gas_equilibrium import solve as gas_solve

CONSERVATION_ATOL_MOL = 1e-12
NEGATIVE_ATOL_MOL = 1e-15
AVAILABILITY_RTOL = 1e-9
MAX_SUBSTEPS = 100000


class CoupledTwoCellError(InvalidParameterError):
    """Fail-closed refusal in the two-cell layer (bad geometry, an un-admitted local solve, a non-conservative or
    over-exporting step)."""


@dataclass(frozen=True)
class CoupledCell:
    """A well-mixed liquid cell: conserved totals (mol) + volume (L) + temperature; species are derived, not stored."""
    volume_L: float
    n_acetate_mol: float
    n_carbon_mol: float
    n_sodium_mol: float
    temperature_K: float = 298.15
    activity_model: str = "ideal"

    def __post_init__(self):
        for name in ("volume_L", "n_acetate_mol", "n_carbon_mol", "n_sodium_mol"):
            v = getattr(self, name)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= -NEGATIVE_ATOL_MOL):
                raise CoupledTwoCellError(f"{name}={v!r} must be finite and >= 0")
        if self.volume_L <= 0:
            raise CoupledTwoCellError("volume_L must be > 0")
        if self.activity_model not in ("ideal", "davies"):
            raise CoupledTwoCellError("activity_model must be 'ideal' or 'davies'")

    @property
    def C_Ac(self) -> float:
        return self.n_acetate_mol / self.volume_L

    @property
    def C_C(self) -> float:
        return self.n_carbon_mol / self.volume_L

    @property
    def Na(self) -> float:
        return self.n_sodium_mol / self.volume_L

    def speciate(self) -> MixedGasResult:
        return gas_solve(MixedGasSystem(mode="closed", total_acetate_M=self.C_Ac, total_carbon_M=self.C_C,
                                        sodium_M=self.Na, activity_model=self.activity_model,
                                        temperature_K=self.temperature_K))


@dataclass(frozen=True)
class DiffusiveMembrane:
    """Selective permeabilities (L/s) for the two NEUTRAL carriers, times a valve in [0, 1] (0 = closed)."""
    g_HAc_L_per_s: float = 0.0
    g_CO2_L_per_s: float = 0.0
    valve: float = 1.0

    def __post_init__(self):
        for name in ("g_HAc_L_per_s", "g_CO2_L_per_s"):
            v = getattr(self, name)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
                raise CoupledTwoCellError(f"{name} must be finite and >= 0")
        if not (math.isfinite(self.valve) and 0.0 <= self.valve <= 1.0):
            raise CoupledTwoCellError("valve must be in [0, 1]")


@dataclass(frozen=True)
class StepReport:
    dt_s: float
    substeps: int
    transfers_mol: dict               # {"acetate": ..., "carbon": ..., "sodium": ...} net A->B over the step
    global_residual_mol: dict         # |global total change| per component (should be ~0)
    charge_residual_M: tuple          # (cellA, cellB) local charge-balance residuals after re-equilibration
    verdicts: tuple                   # (cellA.verdict, cellB.verdict)
    claim_tier: str
    refused: bool = False
    note: str = ""


@dataclass(frozen=True)
class CoupledWorld:
    cellA: CoupledCell
    cellB: CoupledCell
    time_s: float = 0.0
    ledger: tuple = field(default_factory=tuple)   # tuple of StepReport

    def global_totals(self) -> dict:
        return {"acetate": self.cellA.n_acetate_mol + self.cellB.n_acetate_mol,
                "carbon": self.cellA.n_carbon_mol + self.cellB.n_carbon_mol,
                "sodium": self.cellA.n_sodium_mol + self.cellB.n_sodium_mol}


def _apply_component_transfer(world: CoupledWorld, d_ac: float, d_c: float, d_na: float) -> CoupledWorld:
    """Move (d_ac, d_c, d_na) mol of each component from A to B (equal and opposite).  Caller guarantees the dt bound
    so no total goes negative beyond roundoff."""
    A, B = world.cellA, world.cellB
    nA = replace(A, n_acetate_mol=max(A.n_acetate_mol - d_ac, 0.0), n_carbon_mol=max(A.n_carbon_mol - d_c, 0.0),
                 n_sodium_mol=max(A.n_sodium_mol - d_na, 0.0))
    nB = replace(B, n_acetate_mol=max(B.n_acetate_mol + d_ac, 0.0), n_carbon_mol=max(B.n_carbon_mol + d_c, 0.0),
                 n_sodium_mol=max(B.n_sodium_mol + d_na, 0.0))
    return replace(world, cellA=nA, cellB=nB)


def _finish_step(world: CoupledWorld, before: dict, d_ac: float, d_c: float, d_na: float, dt: float,
                 substeps: int) -> StepReport:
    after = world.global_totals()
    rA, rB = world.cellA.speciate(), world.cellB.speciate()
    tier = claim_tiers.weakest(
        claim_tiers.NUMERICALLY_VERIFIED if "UNVERIFIED" not in rA.verdict else claim_tiers.UNVERIFIED,
        claim_tiers.NUMERICALLY_VERIFIED if "UNVERIFIED" not in rB.verdict else claim_tiers.UNVERIFIED,
        claim_tiers.ASSUMED_PARAMETER)   # the transport coefficients are prescribed/assumed
    return StepReport(
        dt_s=dt, substeps=substeps,
        transfers_mol={"acetate": d_ac, "carbon": d_c, "sodium": d_na},
        global_residual_mol={k: abs(after[k] - before[k]) for k in before},
        charge_residual_M=(rA.charge_balance_residual, rB.charge_balance_residual),
        verdicts=(rA.verdict, rB.verdict), claim_tier=tier)


def _max_dt_for(rate_A_to_B_mol_per_s: float, avail_A: float, avail_B_for_reverse: float) -> float:
    """The largest dt that does not export more than the donor holds for a single signed component flux."""
    r = rate_A_to_B_mol_per_s
    if r > 0:
        return avail_A / r if r > 0 else math.inf
    if r < 0:
        return avail_B_for_reverse / (-r)
    return math.inf


def step_diffusive(world: CoupledWorld, membrane: DiffusiveMembrane, dt: float) -> CoupledWorld:
    """One accepted selective-diffusion step: neutral HAc and CO2(aq) cross per their gradients; total acetate and
    total carbon move equal-and-opposite; sodium does not cross.  Substeps adaptively so no donor over-exports."""
    if not (math.isfinite(dt) and dt > 0):
        raise CoupledTwoCellError("dt must be finite and > 0")
    before = world.global_totals()
    w = world
    remaining = dt
    total_d_ac = total_d_c = 0.0
    substeps = 0
    while remaining > 0:
        substeps += 1
        if substeps > MAX_SUBSTEPS:
            raise CoupledTwoCellError("too stiff: exceeded the adaptive-substep budget (fail closed)")
        sA, sB = w.cellA.speciate(), w.cellB.speciate()
        v = membrane.valve
        j_hac = membrane.g_HAc_L_per_s * v * (sA.hac_M - sB.hac_M)      # mol/s, A->B
        j_co2 = membrane.g_CO2_L_per_s * v * (sA.co2aq_M - sB.co2aq_M)  # mol/s, A->B
        # dt bound: neither flux may export more acetate/carbon than the donor cell holds.
        lim = remaining
        lim = min(lim, _max_dt_for(j_hac, w.cellA.n_acetate_mol * (1 - AVAILABILITY_RTOL),
                                   w.cellB.n_acetate_mol * (1 - AVAILABILITY_RTOL)))
        lim = min(lim, _max_dt_for(j_co2, w.cellA.n_carbon_mol * (1 - AVAILABILITY_RTOL),
                                   w.cellB.n_carbon_mol * (1 - AVAILABILITY_RTOL)))
        if not math.isfinite(lim) or lim <= 0:
            lim = remaining
        step = min(remaining, lim)
        d_ac, d_c = j_hac * step, j_co2 * step
        w = _apply_component_transfer(w, d_ac, d_c, 0.0)
        total_d_ac += d_ac
        total_d_c += d_c
        remaining -= step
        if abs(j_hac) < 1e-30 and abs(j_co2) < 1e-30:
            break   # at equilibrium across the membrane: nothing more to move this step
    report = _finish_step(w, before, total_d_ac, total_d_c, 0.0, dt, substeps)
    if max(report.global_residual_mol.values()) > CONSERVATION_ATOL_MOL:
        raise CoupledTwoCellError(f"diffusive step broke global conservation: {report.global_residual_mol}")
    return replace(w, time_s=w.time_s + dt, ledger=w.ledger + (report,))


def step_mixing(world: CoupledWorld, exchange_rate_L_per_s: float, dt: float, *, valve: float = 1.0) -> CoupledWorld:
    """One accepted bulk-mixing step: swap equal, electroneutral solution parcels of volume dV = rate*valve*dt (each
    carrying its donor's own balanced composition).  Volumes stay fixed; all components move; charge is preserved by
    construction (balanced parcels).  dV is bounded by the smaller cell volume."""
    if not (math.isfinite(dt) and dt > 0):
        raise CoupledTwoCellError("dt must be finite and > 0")
    if not (math.isfinite(exchange_rate_L_per_s) and exchange_rate_L_per_s >= 0):
        raise CoupledTwoCellError("exchange_rate_L_per_s must be finite and >= 0")
    if not (math.isfinite(valve) and 0.0 <= valve <= 1.0):
        raise CoupledTwoCellError("valve must be in [0, 1]")
    before = world.global_totals()
    A, B = world.cellA, world.cellB
    dV = exchange_rate_L_per_s * valve * dt
    dV = min(dV, A.volume_L, B.volume_L)   # cannot swap more than a cell holds
    # symmetric swap of balanced parcels: dn[A] = dV*(C[B]-C[A]) per component; dn[B] = -dn[A]; volumes unchanged.
    d_ac = dV * (B.C_Ac - A.C_Ac)
    d_c = dV * (B.C_C - A.C_C)
    d_na = dV * (B.Na - A.Na)
    nA = replace(A, n_acetate_mol=max(A.n_acetate_mol + d_ac, 0.0), n_carbon_mol=max(A.n_carbon_mol + d_c, 0.0),
                 n_sodium_mol=max(A.n_sodium_mol + d_na, 0.0))
    nB = replace(B, n_acetate_mol=max(B.n_acetate_mol - d_ac, 0.0), n_carbon_mol=max(B.n_carbon_mol - d_c, 0.0),
                 n_sodium_mol=max(B.n_sodium_mol - d_na, 0.0))
    w = replace(world, cellA=nA, cellB=nB)
    # note: transfer sign convention in the report is "A -> B", so negate (parcel swap moved +d into A).
    report = _finish_step(w, before, -d_ac, -d_c, -d_na, dt, substeps=1)
    if max(report.global_residual_mol.values()) > CONSERVATION_ATOL_MOL:
        raise CoupledTwoCellError(f"mixing step broke global conservation: {report.global_residual_mol}")
    return replace(w, time_s=w.time_s + dt, ledger=w.ledger + (report,))


def simulate_diffusive(world: CoupledWorld, membrane: DiffusiveMembrane, *, duration_s: float, dt: float) -> CoupledWorld:
    """Advance the world by selective diffusion over duration_s in steps of dt (the last step is clipped to land
    exactly on duration_s)."""
    w = world
    t = 0.0
    while t < duration_s - 1e-15:
        step = min(dt, duration_s - t)
        w = step_diffusive(w, membrane, step)
        t += step
    return w
