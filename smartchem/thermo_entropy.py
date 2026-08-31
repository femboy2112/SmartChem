"""Ideal-gas standard molar entropy S deg(T) DERIVED from molecular structure -- the first rung of the
derivation layer.

The doctrine (``known-physics-not-new-physics``, sharpened 2026-08-31): when a physical value has no
direct source, DERIVE it from established physics and LABEL the derivation honestly -- do not dump it
to ``UNKNOWN``.  A standard molar entropy is a textbook derivation: statistical thermodynamics gives
S deg(T) of an ideal gas from the molecule's mass, its geometry (moments of inertia), its vibrational
frequencies, and its ground-state electronic degeneracy, under the rigid-rotor / harmonic-oscillator
(RRHO) approximation.  Every ingredient is known physics on sourced inputs; the result is a DERIVED
number with a stated method and uncertainty band, never an invented one.

This is EXACTLY the pattern the oracle already uses (calibrate on known cases, state the envelope,
carry the error): the RRHO *formula* is calibrated by reproducing measured standard entropies of
molecules whose frequencies and geometry are independently sourced (see ``tests/test_thermo_entropy``
and ``experiments/``).  The formula is separable from its inputs -- feed it experimental frequencies
and it reproduces experiment; feed it PySCF-computed harmonic frequencies (``geometry.harmonic_analysis``)
and it carries the known +9.1% harmonic bias forward as a propagated uncertainty.

WHAT THIS IS AND IS NOT
-----------------------
* IS: the standard molar entropy of the IDEAL GAS at temperature ``T`` and standard pressure ``p deg``
  (default 1 bar), under RRHO.  DERIVED in the classical/ideal regime, PREDICTED when extrapolated
  outside it.
* IS NOT: a condensed-phase entropy.  S deg(crystal) or S deg(liquid) differ from S deg(gas) by an
  entropy of sublimation/vaporisation, which is a SEPARATE derivation (or a sourced value).  This
  module computes S deg(gas) and says so; it never silently claims to have reached a crystal.

Formulae (standard statistical thermodynamics; e.g. McQuarrie, *Statistical Mechanics*):
  translational (Sackur-Tetrode):  S_tr = R[ ln( (2*pi*m*kB*T/h^2)^(3/2) * kB*T/p ) + 5/2 ]
  rotational, linear:              S_rot = R[ ln( 8*pi^2*I*kB*T / (sigma*h^2) ) + 1 ]
  rotational, non-linear:          S_rot = R[ ln( (sqrt(pi)/sigma) * (8*pi^2*kB*T/h^2)^(3/2)
                                                  * sqrt(Ia*Ib*Ic) ) + 3/2 ]
  vibrational (per real mode, x = h*c*nu~/(kB*T)):  S_vib = R * sum[ x/(e^x-1) - ln(1-e^-x) ]
  electronic:                      S_el = R * ln(g0)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .data.periodic_table import ATOMIC_MASS_CONSTANT_KG, mass_kg_per_molecule, standard_atomic_weight

__all__ = [
    "StandardMolarEntropy",
    "STANDARD_PRESSURE_PA",
    "ideal_gas_entropy",
    "diatomic_entropy",
    "principal_moments_of_inertia",
]

# --- constants -------------------------------------------------------------------------------------
# SI-2019 exact-by-definition (kB, h, NA, c) -- definitional, not measured, so not a recalled-physics
# hazard; identical to the values in smartchem.experiment.eyring/kinetics by definition.  m_u is the
# CODATA 2018 atomic-mass constant (measured), sourced in smartchem.data.periodic_table.
_KB = 1.380649e-23           # Boltzmann constant, J/K
_H = 6.62607015e-34          # Planck constant, J*s
_NA = 6.02214076e23          # Avogadro constant, 1/mol
_R = _KB * _NA               # molar gas constant, J/mol/K (= 8.314462618...)
_C_CM_PER_S = 2.99792458e10  # speed of light, cm/s (so h*c*nu~ with nu~ in cm^-1 is an energy in J)

#: The modern IUPAC standard-state pressure, 1 bar = 100000 Pa (the basis of NIST-JANAF / CODATA
#: standard entropies since 1982).  Pass ``pressure_pa=101325.0`` for the older 1 atm convention;
#: the two differ in S_tr by R*ln(101325/100000) ~ 0.109 J/mol/K.
STANDARD_PRESSURE_PA = 100000.0

#: Regime in which ideal-gas RRHO is graded DERIVED (interpolation within a validated model).  Outside
#: it the result is graded PREDICTED (extrapolation, flagged) -- e.g. very high T where anharmonicity
#: and electronic excitation grow, or very low T where the classical rigid-rotor partition function
#: (valid for T >> rotational temperature) breaks down.
_DERIVED_T_MIN_K = 50.0
_DERIVED_T_MAX_K = 2500.0

#: Nominal model-floor uncertainty (J/mol/K) of ideal-gas RRHO with EXPERIMENTAL frequencies near
#: standard temperature: the residual approximation error (anharmonicity, centrifugal distortion,
#: rovibrational coupling).  PINNED from the calibration in tests/test_thermo_entropy.py, where the
#: derived S deg reproduces sourced experimental standard entropies of N2/CO/HCl to well inside this
#: band -- the same "measure it, then pin it" discipline as the Eyring cross-check tolerance.
_RRHO_MODEL_FLOOR_J_PER_MOL_K = 2.0


@dataclass(frozen=True)
class StandardMolarEntropy:
    """A DERIVED ideal-gas standard molar entropy, with its component breakdown, grade, and band."""

    value_j_per_mol_k: float
    translational: float
    rotational: float
    vibrational: float
    electronic: float
    temperature_k: float
    pressure_pa: float
    linear: bool
    grade: str                       # "DERIVED" (in regime) or "PREDICTED" (extrapolated)
    uncertainty_j_per_mol_k: float
    method: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def render(self) -> str:
        pbar = self.pressure_pa / 100000.0
        return (
            f"S deg(gas) = {self.value_j_per_mol_k:.2f} +/- {self.uncertainty_j_per_mol_k:.2f} J/mol/K "
            f"[{self.grade}] at {self.temperature_k:.2f} K, {pbar:.4g} bar "
            f"(trans {self.translational:.2f} + rot {self.rotational:.2f} + vib {self.vibrational:.2f}"
            f" + elec {self.electronic:.2f}; {self.method})"
        )


def _translational_entropy(molar_mass_u: float, temperature_k: float, pressure_pa: float) -> float:
    m = mass_kg_per_molecule(molar_mass_u)                       # mass of one molecule, kg
    q_over_v = (2.0 * math.pi * m * _KB * temperature_k / _H**2) ** 1.5   # translational q per volume
    volume_per_molecule = _KB * temperature_k / pressure_pa
    return _R * (math.log(q_over_v * volume_per_molecule) + 2.5)


def _rotational_entropy_linear(moment_kg_m2: float, symmetry_number: int,
                               temperature_k: float) -> float:
    q_rot = (8.0 * math.pi**2 * moment_kg_m2 * _KB * temperature_k) / (symmetry_number * _H**2)
    return _R * (math.log(q_rot) + 1.0)


def _rotational_entropy_nonlinear(moments_kg_m2: Sequence[float], symmetry_number: int,
                                  temperature_k: float) -> float:
    ia, ib, ic = moments_kg_m2
    prefactor = (8.0 * math.pi**2 * _KB * temperature_k / _H**2) ** 1.5
    q_rot = (math.sqrt(math.pi) / symmetry_number) * prefactor * math.sqrt(ia * ib * ic)
    return _R * (math.log(q_rot) + 1.5)


def _vibrational_entropy(frequencies_cm: Sequence[float], temperature_k: float) -> float:
    total = 0.0
    for nu in frequencies_cm:
        if nu <= 0.0:            # imaginary/near-zero (external) modes contribute nothing real here
            continue
        x = _H * _C_CM_PER_S * nu / (_KB * temperature_k)
        if x > 700.0:
            # a mode that stiff (h*nu >> kB*T) has vanishing entropy; both terms -> 0.  Handling it
            # explicitly avoids an OverflowError in expm1(x) for a physically-legitimate large finite x.
            continue
        total += x / math.expm1(x) - math.log1p(-math.exp(-x))
    return _R * total


def _electronic_entropy(degeneracy: int) -> float:
    return _R * math.log(degeneracy)


def _reduced_mass_kg(mass_a_u: float, mass_b_u: float) -> float:
    return (mass_a_u * mass_b_u) / (mass_a_u + mass_b_u) * ATOMIC_MASS_CONSTANT_KG


def principal_moments_of_inertia(
    masses_u: Sequence[float], coordinates_angstrom: np.ndarray
) -> tuple[np.ndarray, bool]:
    """Principal moments of inertia (kg*m^2, ascending) and whether the molecule is linear.

    ``coordinates_angstrom`` has shape ``(n_atoms, 3)``.  Linear is detected when the smallest
    principal moment is negligible against the largest (a true linear molecule has one zero moment).
    """
    masses = np.asarray(masses_u, dtype=float)
    coords = np.asarray(coordinates_angstrom, dtype=float) * 1e-10          # Angstrom -> m
    masses_kg = masses * ATOMIC_MASS_CONSTANT_KG
    centre = (masses_kg[:, None] * coords).sum(axis=0) / masses_kg.sum()
    rel = coords - centre
    inertia = np.zeros((3, 3))
    for m, r in zip(masses_kg, rel):
        inertia += m * (np.dot(r, r) * np.eye(3) - np.outer(r, r))
    moments = np.linalg.eigvalsh(inertia)                                   # ascending, real symmetric
    moments = np.clip(moments, 0.0, None)
    largest = moments[-1]
    linear = largest > 0 and moments[0] < 1e-6 * largest
    return moments, bool(linear)


def _grade_and_band(
    temperature_k: float, vibrational: float, frequency_bias_fraction: float,
    frequencies_cm: Sequence[float] | None,
) -> tuple[str, float, tuple[str, ...]]:
    """Grade the result and size its uncertainty band.

    Band = the RRHO model floor combined in quadrature with the propagated effect of a biased
    frequency source (when ``frequency_bias_fraction`` > 0, i.e. computed rather than experimental
    frequencies -- e.g. the known +9.1% PySCF harmonic bias).
    """
    notes: list[str] = []
    in_regime = _DERIVED_T_MIN_K <= temperature_k <= _DERIVED_T_MAX_K
    grade = "DERIVED" if in_regime else "PREDICTED"
    if not in_regime:
        notes.append(
            f"T={temperature_k:.1f} K is outside the DERIVED regime "
            f"[{_DERIVED_T_MIN_K:.0f},{_DERIVED_T_MAX_K:.0f}] K -> PREDICTED (extrapolated)"
        )
    band = _RRHO_MODEL_FLOOR_J_PER_MOL_K
    if frequency_bias_fraction and frequencies_cm is not None:
        scaled = [nu * (1.0 + frequency_bias_fraction) for nu in frequencies_cm]
        dvib = abs(_vibrational_entropy(scaled, temperature_k) - vibrational)
        band = math.hypot(band, dvib)
        notes.append(
            f"frequency source carries a {frequency_bias_fraction:+.1%} bias -> "
            f"+/-{dvib:.2f} J/mol/K propagated into S_vib"
        )
    return grade, band, tuple(notes)


def ideal_gas_entropy(
    *,
    molar_mass_u: float,
    frequencies_cm: Sequence[float],
    moments_of_inertia_kg_m2: Sequence[float],
    linear: bool,
    symmetry_number: int,
    electronic_degeneracy: int = 1,
    temperature_k: float = 298.15,
    pressure_pa: float = STANDARD_PRESSURE_PA,
    frequency_bias_fraction: float = 0.0,
) -> StandardMolarEntropy:
    """DERIVE the ideal-gas standard molar entropy S deg(T) from molecular structure via RRHO.

    ``moments_of_inertia_kg_m2`` is a 1-sequence (linear) or 3-sequence (non-linear) of principal
    moments; ``linear`` says which.  ``symmetry_number`` is the rotational symmetry number
    (1 for a heteronuclear diatomic / asymmetric top, 2 for a homonuclear diatomic, 12 for methane, ...).
    ``electronic_degeneracy`` is the ground-state electronic degeneracy g0 (2S+1 for a spin-only
    ground term; e.g. 3 for O2's triplet).  ``frequency_bias_fraction`` (default 0, experimental
    frequencies) propagates a known bias in a COMPUTED frequency source into the uncertainty band.
    """
    # every numeric input must be a FINITE positive number -- a NaN/inf must raise a clean ValueError here,
    # never leak into the RRHO arithmetic and surface as a NaN/inf S deg dressed as a confident DERIVED value.
    if not (isinstance(temperature_k, (int, float)) and math.isfinite(temperature_k) and temperature_k > 0):
        raise ValueError("temperature_k must be a finite positive absolute temperature (K)")
    if not (isinstance(pressure_pa, (int, float)) and math.isfinite(pressure_pa) and pressure_pa > 0):
        raise ValueError("pressure_pa must be a finite positive pressure (Pa)")
    if not (isinstance(symmetry_number, int) and not isinstance(symmetry_number, bool)
            and symmetry_number >= 1):
        raise ValueError("symmetry_number must be a positive integer")
    if not (isinstance(electronic_degeneracy, int) and not isinstance(electronic_degeneracy, bool)
            and electronic_degeneracy >= 1):
        raise ValueError("electronic_degeneracy must be a positive integer")
    if not (isinstance(molar_mass_u, (int, float)) and math.isfinite(molar_mass_u) and molar_mass_u > 0):
        raise ValueError("molar_mass_u must be a finite positive mass (u)")
    if any(not math.isfinite(f) for f in frequencies_cm):
        raise ValueError("every frequency must be finite (a NaN/inf frequency is not a real mode)")
    if any((not math.isfinite(m)) or m <= 0 for m in moments_of_inertia_kg_m2):
        raise ValueError("every moment of inertia must be a finite positive number")

    s_tr = _translational_entropy(molar_mass_u, temperature_k, pressure_pa)
    moments = list(moments_of_inertia_kg_m2)
    if linear:
        if len(moments) == 3:                       # accept a 3-vector with one ~zero moment
            moments = [max(moments)]
        if len(moments) != 1 or moments[0] <= 0:
            raise ValueError("a linear molecule needs one positive moment of inertia")
        s_rot = _rotational_entropy_linear(moments[0], symmetry_number, temperature_k)
    else:
        if len(moments) != 3 or any(m <= 0 for m in moments):
            raise ValueError("a non-linear molecule needs three positive moments of inertia")
        s_rot = _rotational_entropy_nonlinear(moments, symmetry_number, temperature_k)
    s_vib = _vibrational_entropy(frequencies_cm, temperature_k)
    s_el = _electronic_entropy(electronic_degeneracy)
    total = s_tr + s_rot + s_vib + s_el
    if not math.isfinite(total):  # backstop: never report a NaN/inf as a confident value
        raise ValueError("computed standard entropy is non-finite; refusing to report it")

    grade, band, notes = _grade_and_band(temperature_k, s_vib, frequency_bias_fraction, frequencies_cm)
    method = (
        "ideal-gas RRHO (Sackur-Tetrode translation + rigid rotor + harmonic oscillator + electronic), "
        "known statistical thermodynamics on sourced structural inputs"
    )
    return StandardMolarEntropy(
        value_j_per_mol_k=total, translational=s_tr, rotational=s_rot, vibrational=s_vib,
        electronic=s_el, temperature_k=temperature_k, pressure_pa=pressure_pa, linear=bool(linear),
        grade=grade, uncertainty_j_per_mol_k=band, method=method, notes=notes,
    )


def diatomic_entropy(
    symbol_a: str,
    symbol_b: str,
    *,
    bond_length_angstrom: float,
    frequency_cm: float,
    symmetry_number: int,
    electronic_degeneracy: int = 1,
    temperature_k: float = 298.15,
    pressure_pa: float = STANDARD_PRESSURE_PA,
    frequency_bias_fraction: float = 0.0,
) -> StandardMolarEntropy:
    """DERIVE S deg(gas) for a diatomic from sourced atomic masses + a bond length + a frequency.

    Masses come from the sourced periodic table.  The moment of inertia is I = mu * r_e^2 with mu the
    reduced mass.  ``symmetry_number`` is 2 for a homonuclear diatomic (A2) and 1 for a heteronuclear
    one (AB).  This is the calibration path: with experimental ``bond_length_angstrom`` and
    ``frequency_cm`` (e.g. from ``smartchem.data.reference.GEOMETRY``) it reproduces measured standard
    entropies.
    """
    if bond_length_angstrom <= 0 or frequency_cm <= 0:
        raise ValueError("bond length and frequency must be positive")
    mass_a = standard_atomic_weight(symbol_a)
    mass_b = standard_atomic_weight(symbol_b)
    mu_kg = _reduced_mass_kg(mass_a, mass_b)
    r_m = bond_length_angstrom * 1e-10
    moment = mu_kg * r_m**2
    return ideal_gas_entropy(
        molar_mass_u=mass_a + mass_b,
        frequencies_cm=[frequency_cm],
        moments_of_inertia_kg_m2=[moment],
        linear=True,
        symmetry_number=symmetry_number,
        electronic_degeneracy=electronic_degeneracy,
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
        frequency_bias_fraction=frequency_bias_fraction,
    )
