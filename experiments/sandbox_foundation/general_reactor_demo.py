"""OPERATION XXII section 5 -- ONE configurable vinegar/bicarbonate reactor, THREE interchangeable transport laws.

The XXI flagship (unified_chemical_world) coupled an acetic-acid cell A, a sodium-bicarbonate cell B (with undissolved
NaHCO3 and a shared CO2 headspace) through a SELECTIVE membrane that passes only the neutral carriers HAc and CO2(aq).
XXII-5 makes the inter-chamber mechanism a first-class, interchangeable PHYSICAL DECLARATION inside the SAME flagship:

  "closed"    no A<->B transport.
  "membrane"  selective membrane -- neutral HAc + CO2(aq) cross; the IONS (Na+, Ac-, HCO3-, CO3-2) cannot, so the Na
              gradient never relaxes and the two chambers keep distinct ionic strengths.
  "bulk"      ElectroneutralBulkExchange -- equal LIQUID PARCELS carrying the COMPLETE dissolved roster (all 8 aqueous
              species at one Q), so Na, total acetate and total inorganic carbon ALL relax toward a common composition
              and neither chamber is left charged (XXII-1 completeness-gated: a partial/charged subset is refused).

The Henry gas-liquid CO2 transfer (B<->gas) and the optional open-vessel vent are present in every mode.  The SAME
generic CoupledWorld.integrate advances all three -- only the declared transport operator differs, never the integrator.
This is the headline Wave-C deliverable: a reactor where the user chooses an ACTUAL transport law, not an animation.

Run ``python -m experiments.sandbox_foundation.general_reactor_demo`` for the three-mode comparison table.
"""
from __future__ import annotations

from dataclasses import dataclass

from experiments.sandbox_foundation.unified_chemical_world import (
    UnifiedParams,
    _build_species,
    build_unified_world,
    initial_state,
)

MODES = ("closed", "membrane", "bulk")


@dataclass(frozen=True)
class ReactorObservables:
    """The §5 comparison quantities, extracted from ONE mode's trajectory (endpoint unless noted)."""
    mode: str
    pH_A: float | None
    pH_B: float | None
    Na_A: float
    Na_B: float
    na_gradient: float           # |[Na+]_A - [Na+]_B| (mol/L) -- 0 for a fully mixed solution; membrane keeps it
    acetate_A: float             # HAc + Ac- in A
    acetate_B: float             # HAc + Ac- in B (membrane: only neutral HAc crosses; bulk: Ac- too)
    TIC_A: float                 # total inorganic carbon in A (CO2aq + HCO3- + CO3-2)
    TIC_B: float
    solid_B: float               # remaining undissolved NaHCO3(s)
    CO2aq_B: float
    CO2_headspace: float         # gas-phase CO2
    CO2_export_C: float          # net C exported via the open vent (0 when sealed)
    tier: str
    material_balance_closed: bool
    max_step_material_residual: float
    numerically_unresolved: tuple
    charge_A: float
    charge_B: float


def run_reactor(mode: str, params: UnifiedParams | None = None, *, acid_mol: float = 0.10,
                bicarb_solid_mol: float = 0.05, bicarb_dissolved_mol: float = 0.05,
                duration: float = 120.0, n_steps: int = 240, n_samples: int | None = None,
                sealed: bool = True):
    """Build and integrate a single-phase reactor in ``mode`` from the shared initial state.  Returns the trajectory."""
    params = params or UnifiedParams()
    sp = _build_species()
    build = build_unified_world(params, sp, sealed=sealed, transport_mode=mode)
    init = initial_state(sp, acid_mol=acid_mol, bicarb_solid_mol=bicarb_solid_mol,
                         bicarb_dissolved_mol=bicarb_dissolved_mol)
    tr = build.world.integrate(init, duration=duration, n_steps=n_steps, n_samples=n_samples, scheme="strang")
    return tr, sp, params


def _amt(tr, cell, sp_obj):
    return tr.amounts[cell][-1].get(sp_obj, 0.0)


def _cell_charge(tr, sp, cell):
    s = sp
    return sum(obj.charge * tr.amounts[cell][-1].get(obj, 0.0)
               for obj in (s.HAc, s.Ac, s.CO2aq, s.HCO3, s.CO3, s.Hp, s.OHm, s.Nap))


def observe(mode: str, tr, sp, params: UnifiedParams) -> ReactorObservables:
    def ph(cell):
        ds = tr.equilibrium_derived.get(cell, ())
        return ds[-1].get("pH_activity") if ds else None

    na_a, na_b = _amt(tr, "A", sp.Nap), _amt(tr, "B", sp.Nap)

    def tic(cell):   # total inorganic carbon
        return _amt(tr, cell, sp.CO2aq) + _amt(tr, cell, sp.HCO3) + _amt(tr, cell, sp.CO3)

    def acet(cell):  # total acetate (neutral + ionized)
        return _amt(tr, cell, sp.HAc) + _amt(tr, cell, sp.Ac)
    return ReactorObservables(
        mode=mode, pH_A=ph("A"), pH_B=ph("B"), Na_A=na_a, Na_B=na_b,
        na_gradient=abs(na_a / params.V_A_L - na_b / params.V_B_L),
        acetate_A=acet("A"), acetate_B=acet("B"), TIC_A=tic("A"), TIC_B=tic("B"),
        solid_B=_amt(tr, "B", sp.solid), CO2aq_B=_amt(tr, "B", sp.CO2aq),
        CO2_headspace=_amt(tr, "gas", sp.CO2g),
        CO2_export_C=-float(tr.receipt.external_flux.get("C", 0.0)),      # C leaving via the vent (sign: out = +)
        tier=tr.tier, material_balance_closed=tr.receipt.material_balance_closed,
        max_step_material_residual=tr.receipt.max_step_material_residual,
        numerically_unresolved=tr.receipt.numerically_unresolved_components,
        charge_A=_cell_charge(tr, sp, "A"), charge_B=_cell_charge(tr, sp, "B"))


def compare_modes(params: UnifiedParams | None = None, *, sealed: bool = True, **run_kw) -> dict:
    """Run the SAME initial state under closed / membrane / bulk and return {mode: ReactorObservables}."""
    out = {}
    for mode in MODES:
        tr, sp, p = run_reactor(mode, params, sealed=sealed, **run_kw)
        out[mode] = observe(mode, tr, sp, p)
    return out


if __name__ == "__main__":
    obs = compare_modes()
    cols = [("pH_A", "pH_A"), ("pH_B", "pH_B"), ("na_gradient", "Na grad M"), ("acetate_B", "acetate_B"),
            ("TIC_A", "TIC_A"), ("solid_B", "solid_B"), ("CO2_headspace", "CO2(g)"), ("tier", "tier")]
    print(f"{'mode':9s} " + " ".join(f"{label:>11s}" for _, label in cols))
    for mode in MODES:
        o = obs[mode]
        cells = []
        for attr, _ in cols:
            v = getattr(o, attr)
            cells.append(f"{v:>11.4f}" if isinstance(v, float) else f"{str(v):>11s}")
        print(f"{mode:9s} " + " ".join(cells))
    print("\ncharge A/B per mode (must be ~0):")
    for mode in MODES:
        o = obs[mode]
        print(f"  {mode:9s} qA={o.charge_A:+.2e} qB={o.charge_B:+.2e}  closed={o.material_balance_closed} "
              f"resid={o.max_step_material_residual:.2e}")
