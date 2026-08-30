"""Phase-at-(T, P) from sourced data via the Clausius-Clapeyron relation -- an established-model estimate.

E1's pressure depth needs to know whether an intermediate is a gas or a condensed phase at a step's declared
temperature AND pressure.  The gas/liquid boundary moves with pressure, and the established textbook model
for that is the integrated Clausius-Clapeyron equation::

    ln(P2 / P1) = -(dHvap / R) * (1/T2 - 1/T1)

Given the NORMAL boiling point (T1 at P1 = 1 atm) and a sourced enthalpy of vaporisation ``dHvap``, this
solves for the boiling point ``T2`` at another pressure ``P2``, then places the phase.  It is a KNOWN model
applied to SOURCED inputs (calibrate/state-envelope/refuse, the oracle discipline), NOT a new-physics
prediction: it assumes a constant ``dHvap`` and ideal vapour (stated), and it refuses (returns ``None``)
whenever the sourced inputs it needs are absent.  Melting is treated as pressure-independent (a standard,
stated approximation for the modest pressure ranges a bench spans).
"""
from __future__ import annotations

import math

from ..data.stability import StabilityRef

__all__ = ["GAS_CONSTANT_J", "boiling_point_at_pressure", "estimate_phase"]

#: The molar gas constant, J/(mol*K).
GAS_CONSTANT_J = 8.314462618


def boiling_point_at_pressure(bp_normal_k: float, dhvap_kj_per_mol: float, pressure_atm: float) -> float:
    """The Clausius-Clapeyron boiling point (K) at ``pressure_atm``, from the normal bp + dHvap.

    Below 1 atm the bp drops (a vacuum boils a liquid at a lower temperature); above it, the bp rises.
    Returns ``+inf`` in the degenerate case where the inputs push the reciprocal temperature non-positive
    (an out-of-range extrapolation), so a caller never divides by zero.
    """
    if pressure_atm <= 0:
        return float("inf")
    dhvap_j = dhvap_kj_per_mol * 1000.0
    inv_t = 1.0 / bp_normal_k - (GAS_CONSTANT_J / dhvap_j) * math.log(pressure_atm)
    if inv_t <= 0:
        return float("inf")
    return 1.0 / inv_t


def estimate_phase(rec: StabilityRef, temperature_k: float, pressure_atm: float) -> str | None:
    """Estimate the phase (``"solid"`` / ``"liquid"`` / ``"gas"``) of ``rec`` at (T, P), or ``None``.

    Returns ``None`` when the sourced data cannot place the phase -- specifically when the gas/liquid
    boundary is needed but the record lacks a boiling point and enthalpy of vaporisation.  The gas boundary
    is the Clausius-Clapeyron bp at ``pressure_atm``; the solid boundary is the (pressure-independent)
    melting point.  Never guesses past the sourced inputs.
    """
    if rec.boiling is not None and rec.dhvap_kj_per_mol is not None:
        bp_normal = (rec.boiling.lo + rec.boiling.hi) / 2.0
        bp_at_p = boiling_point_at_pressure(bp_normal, rec.dhvap_kj_per_mol, pressure_atm)
        if temperature_k >= bp_at_p:
            return "gas"
        if rec.melting is not None and temperature_k < rec.melting.lo:
            return "solid"
        return "liquid"
    # without the gas boundary we can at most say "solid" with confidence; otherwise refuse
    if rec.melting is not None and temperature_k < rec.melting.lo:
        return "solid"
    return None
