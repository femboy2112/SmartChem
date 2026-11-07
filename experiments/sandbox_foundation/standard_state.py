"""OPERATION XXIV-2B -- the molal <-> molar standard-state transformation of an equilibrium constant.

THE PROBLEM.  PHREEQC-class databases tabulate log K on the MOLALITY basis (standard state m° = 1 mol per kg of
water, hypothetical ideal 1 m solution).  The sandbox's activity laws build activities from MOLAR concentrations
(c° = 1 mol per L of solution).  Feeding a molal-basis K into a molar activity product uses one dimensionless number on
two incompatible standard states.  The error is small in dilute water, but it is a systematic bias, not noise.

DERIVATION (one solute i, then the whole reaction).  The chemical potential is basis-independent:
    mu_i = mu_i°(m) + RT ln(gamma_i^(m) m_i / m°) = mu_i°(c) + RT ln(gamma_i^(c) c_i / c°).
In the ideal-dilute limit both gammas -> 1 and c_i / m_i -> rho_w* (the PURE-solvent density, kg/L), so
    mu_i°(c) - mu_i°(m) = RT ln( (m_i/m°) / (c_i/c°) ) -> -RT ln(rho_w* m° / c°).
For a reaction sum_i nu_i A_i = 0, dG° = -RT ln K:
    ln K^(c) = ln K^(m) + (sum over AQUEOUS SOLUTES of nu_i) * ln(rho_w* m° / c°)
Pure phases (solids, the solvent) have activity 1 on both bases and do not enter the exponent.  The WHOLE activity
product is transported, not one ion's concentration.  At finite concentration the activity COEFFICIENTS differ too:
    gamma_i^(c) = gamma_i^(m) * (m_i rho_w* / c_i),
which matters only beyond the dilute range the Davies-domain worlds are confined to (I <= 0.1).

DIMENSIONAL CHECK.  rho_w* m° / c° = (kg/L)(mol/kg)/(mol/L): dimensionless, as a factor inside ln must be.

This is a STANDARD-STATE identity, not a fit: no constant is adjusted to agree with anything.  Applying it makes a
molar-basis model and a molal-basis reference describe the same state.  It is NOT evidence that either matches
nature: that needs an independent measurement.
"""
from __future__ import annotations

import math

RHO_W_25C_KG_PER_L = 0.997047          # pure water density at 25 °C (CRC/IAPWS-95: 997.047 kg m^-3 at 0.1 MPa)
M_STANDARD = 1.0                       # mol/kg
C_STANDARD = 1.0                       # mol/L


def aqueous_nu(stoich, unit_activity=()) -> int:
    """Sum of stoichiometric coefficients of the AQUEOUS solutes (products +, reactants -).  Solids and declared
    unit-activity species (the solvent) are excluded."""
    from experiments.sandbox_foundation.general_kernel import Phase
    return sum(int(c) for sp, c in stoich if sp.phase is Phase.AQUEOUS and sp not in tuple(unit_activity))


def molal_to_molar_logK(logK_molal: float, nu_aq: int, rho_w: float = RHO_W_25C_KG_PER_L) -> float:
    """log10 K^(c) from log10 K^(m) for a reaction whose aqueous solutes have net coefficient ``nu_aq``."""
    if not (math.isfinite(logK_molal) and math.isfinite(rho_w) and rho_w > 0):
        raise ValueError("logK and rho_w must be finite (rho_w > 0)")
    return float(logK_molal) + int(nu_aq) * math.log10(rho_w * M_STANDARD / C_STANDARD)


def molar_to_molal_logK(logK_molar: float, nu_aq: int, rho_w: float = RHO_W_25C_KG_PER_L) -> float:
    return float(logK_molar) - int(nu_aq) * math.log10(rho_w * M_STANDARD / C_STANDARD)
