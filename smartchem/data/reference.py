"""
Experimental reference data. This is the ground truth every oracle is measured against.

Sources
-------
BDE    : CRC Handbook of Chemistry and Physics, 104th ed., Section 9 "Bond Dissociation
         Energies"; NIST Chemistry WebBook (webbook.nist.gov), gas-phase diatomic D0.
GAP    : CRC Handbook Section 12 "Properties of Semiconductors"; Kittel, Introduction to
         Solid State Physics, 8th ed., Table 2 (300 K values).

Conventions
-----------
* All energies in eV. 1 eV = 96.485 kJ/mol = 23.0605 kcal/mol.
* Diatomic values are intended to represent D0 (dissociation from the vibrational ground
  state), but the compact source labels do not independently establish the D0/D298
  convention for every row. Converting D298 to D0 requires species-specific thermal
  enthalpy increments; it is not a generic kT or zero-point correction. The tabulated
  `uncertainty_ev` does not silently absorb a convention mismatch. Verify the quantity in
  the primary source before adding a row or using one as a high-precision standard.
* `split` is declared explicitly rather than drawn at random so comparisons are
  reproducible and auditable. Historical `test` entries were inspected during the 2026
  tier/uncertainty audit, so that partition is no longer a pristine holdout and must not be
  advertised as one. Future fitting/model selection needs a newly locked external set. The
  existing partition remains useful for regression reporting only.

Honesty note
------------
A benchmark is only as good as its coverage. `coverage_report()` states which reference
species the current periodic table can even attempt, so a good MAE over a tiny subset
cannot masquerade as a good MAE overall.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Mapping

Split = Literal["train", "test"]


@dataclass(frozen=True)
class BondRef:
    """An experimental diatomic bond dissociation energy."""
    formula: str
    atoms: tuple[str, ...]      # element symbols, one per atom
    d0_ev: float                # dissociation energy, eV (positive = bound)
    uncertainty_ev: float       # source/curation scale; not a calibrated coverage claim
    split: Split
    kind: str                   # homonuclear | polar-covalent | ionic | multiple-bond
    source: str
    # Conventional molecular-graph order. This identifies the benchmark species; it is
    # not a claim that a single integer captures its full electronic bond-order observable.
    bond_order: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.atoms, tuple) or len(self.atoms) != 2:
            raise ValueError("a diatomic reference must contain exactly two atoms")
        if any(not isinstance(symbol, str) or not symbol for symbol in self.atoms):
            raise ValueError("reference atom symbols must be non-empty strings")
        if type(self.bond_order) is not int:
            raise TypeError("bond_order must be an integer")
        if self.bond_order < 1:
            raise ValueError("bond_order must be at least one")


@dataclass(frozen=True)
class GapRef:
    """An experimental electronic band gap for an elemental crystal."""
    symbol: str
    coordination: int
    gap_ev: float
    uncertainty_ev: float
    split: Split
    phase: str                  # metal | semiconductor | insulator
    source: str


# --------------------------------------------------------------------------------------
# Diatomic bond dissociation energies
# --------------------------------------------------------------------------------------
BOND_REFS: tuple[BondRef, ...] = (
    # --- homonuclear: the class the current charge-transfer model cannot describe at all,
    #     because chi_A - chi_B is identically zero for A-A pairs.
    BondRef("H2",   ("H", "H"),   4.478, 0.001, "train", "homonuclear",    "NIST WebBook", 1),
    BondRef("N2",   ("N", "N"),   9.754, 0.005, "test",  "multiple-bond",  "NIST WebBook", 3),
    BondRef("O2",   ("O", "O"),   5.116, 0.003, "train", "multiple-bond",  "NIST WebBook", 2),
    BondRef("F2",   ("F", "F"),   1.602, 0.005, "train", "homonuclear",    "CRC 104th, 9-73", 1),
    BondRef("Cl2",  ("Cl", "Cl"), 2.479, 0.005, "train", "homonuclear",    "NIST WebBook (D0)", 1),
    BondRef("I2",   ("I", "I"),   1.542, 0.003, "test",  "homonuclear",    "NIST WebBook", 1),
    BondRef("P2",   ("P", "P"),   5.069, 0.020, "test",  "multiple-bond",  "CRC 104th, 9-73", 3),
    BondRef("S2",   ("S", "S"),   4.371, 0.020, "train", "multiple-bond",  "CRC 104th, 9-73", 2),
    BondRef("C2",   ("C", "C"),   6.213, 0.030, "train", "multiple-bond",  "NIST WebBook", 2),
    BondRef("Si2",  ("Si", "Si"), 3.210, 0.050, "test",  "homonuclear",    "CRC 104th, 9-73", 2),
    BondRef("Na2",  ("Na", "Na"), 0.720, 0.010, "train", "homonuclear",    "NIST WebBook", 1),
    BondRef("K2",   ("K", "K"),   0.514, 0.010, "test",  "homonuclear",    "NIST WebBook", 1),

    # --- polar covalent
    BondRef("HF",   ("H", "F"),   5.869, 0.003, "train", "polar-covalent", "NIST WebBook", 1),
    BondRef("HCl",  ("H", "Cl"),  4.434, 0.003, "test",  "polar-covalent", "NIST WebBook", 1),
    BondRef("HI",   ("H", "I"),   3.054, 0.005, "train", "polar-covalent", "NIST WebBook", 1),
    BondRef("OH",   ("O", "H"),   4.392, 0.004, "train", "polar-covalent", "NIST WebBook", 1),
    BondRef("CH",   ("C", "H"),   3.465, 0.010, "test",  "polar-covalent", "NIST WebBook", 1),
    BondRef("NH",   ("N", "H"),   3.400, 0.020, "train", "polar-covalent", "CRC 104th, 9-73", 1),
    BondRef("SiO",  ("Si", "O"),  8.263, 0.020, "test",  "multiple-bond",  "CRC 104th, 9-73", 2),
    BondRef("CS",   ("C", "S"),   7.355, 0.030, "train", "multiple-bond",  "CRC 104th, 9-73", 3),

    # --- strong multiple bonds: CO is the strongest known diatomic bond and the current
    #     engine refuses to form it at all.
    BondRef("CO",   ("C", "O"),  11.157, 0.005, "test",  "multiple-bond",  "NIST WebBook", 3),
    BondRef("NO",   ("N", "O"),   6.496, 0.005, "train", "multiple-bond",  "NIST WebBook", 2),
    BondRef("CN",   ("C", "N"),   7.738, 0.030, "train", "multiple-bond",  "CRC 104th, 9-73", 3),

    # --- ionic: the class the current model overshoots by ~3x
    BondRef("NaCl", ("Na", "Cl"), 4.234, 0.010, "train", "ionic",          "NIST WebBook", 1),
    BondRef("KCl",  ("K", "Cl"),  4.420, 0.020, "test",  "ionic",          "CRC 104th, 9-73", 1),
    BondRef("NaF",  ("Na", "F"),  4.945, 0.020, "train", "ionic",          "CRC 104th, 9-73", 1),
    BondRef("MgO",  ("Mg", "O"),  3.673, 0.070, "test",  "ionic",          "CRC 104th, 9-73", 1),

    # --- interhalogen
    BondRef("ICl",  ("I", "Cl"),  2.152, 0.010, "train", "polar-covalent", "NIST WebBook", 1),
)


# --------------------------------------------------------------------------------------
# Elemental crystal band gaps
# --------------------------------------------------------------------------------------
GAP_REFS: tuple[GapRef, ...] = (
    GapRef("C",  4,  5.470, 0.030, "train", "insulator",     "CRC 104th, 12-80 (diamond)"),
    GapRef("Si", 4,  1.120, 0.010, "test",  "semiconductor", "CRC 104th, 12-80 (300 K)"),
    # Metals: gap is identically zero. Easy to get right, so they are reported separately
    # and never allowed to flatter an aggregate MAE.
    GapRef("Na", 8,  0.0,   0.0,   "train", "metal",         "Kittel 8th ed., ch. 6"),
    GapRef("K",  8,  0.0,   0.0,   "train", "metal",         "Kittel 8th ed., ch. 6"),
    GapRef("Fe", 8,  0.0,   0.0,   "train", "metal",         "Kittel 8th ed., ch. 6"),
    GapRef("Cu", 12, 0.0,   0.0,   "test",  "metal",         "Kittel 8th ed., ch. 6"),
    GapRef("Zn", 12, 0.0,   0.0,   "train", "metal",         "Kittel 8th ed., ch. 6"),
    GapRef("Pb", 12, 0.0,   0.0,   "test",  "metal",         "Kittel 8th ed., ch. 6"),
    GapRef("Mo", 8,  0.0,   0.0,   "train", "metal",         "Kittel 8th ed., ch. 6"),
    GapRef("Pt", 12, 0.0,   0.0,   "test",  "metal",         "Kittel 8th ed., ch. 6"),
)


# --------------------------------------------------------------------------------------
# Accessors
# --------------------------------------------------------------------------------------
def bonds(split: Split | None = None) -> tuple[BondRef, ...]:
    """Reference bonds, optionally restricted to one split."""
    if split is None:
        return BOND_REFS
    return tuple(b for b in BOND_REFS if b.split == split)


def gaps(split: Split | None = None) -> tuple[GapRef, ...]:
    """Reference band gaps, optionally restricted to one split."""
    if split is None:
        return GAP_REFS
    return tuple(g for g in GAP_REFS if g.split == split)


def required_elements() -> frozenset[str]:
    """Every element symbol the reference set mentions."""
    syms: set[str] = set()
    for b in BOND_REFS:
        syms.update(b.atoms)
    for g in GAP_REFS:
        syms.add(g.symbol)
    return frozenset(syms)


def coverage_report(available: frozenset[str]) -> dict[str, object]:
    """
    State plainly which references the current periodic table can attempt.

    A high score over a small subset is not a high score. Any benchmark output that
    quotes an MAE must quote this alongside it.
    """
    needed = required_elements()
    missing = needed - available
    attemptable_bonds = tuple(b for b in BOND_REFS if set(b.atoms) <= available)
    attemptable_gaps = tuple(g for g in GAP_REFS if g.symbol in available)
    return {
        "elements_required": len(needed),
        "elements_available": len(needed & available),
        "elements_missing": tuple(sorted(missing)),
        "bonds_total": len(BOND_REFS),
        "bonds_attemptable": len(attemptable_bonds),
        "bonds_skipped": tuple(
            b.formula for b in BOND_REFS if not set(b.atoms) <= available
        ),
        "gaps_total": len(GAP_REFS),
        "gaps_attemptable": len(attemptable_gaps),
    }


# --------------------------------------------------------------------------------------
# Structural INPUT data -- not reference answers
# --------------------------------------------------------------------------------------
# Equilibrium bond lengths and harmonic frequencies. These are *inputs* to an electronic
# structure calculation, not the quantity being predicted, and keeping them in a clearly
# separate block is deliberate so the distinction cannot blur.
#
# The protocol this supports is the standard one for benchmarking an electronic method:
#
#     INPUT     : r_e (experimental geometry), omega_e (experimental, for the ZPE)
#     PREDICTED : D_e, the electronic dissociation energy
#     REPORTED  : D_0 = D_e - ZPE,  ZPE ~ 0.5 * omega_e
#
# A fully predictive calculation would optimise the geometry and compute the harmonic
# frequency on the resulting surface. ``PySCFOracle(optimize_geometry=True)`` was never
# that protocol -- its bond-length refinement was truth-centered on the r_e tabulated here
# and it kept using this tabulated frequency -- so it is not assigned the fixed-geometry
# benchmark MAE, and its diatomic path now declines outright rather than returning an
# unvalidated number. The flag is off by default so the benchmark isolates the
# *electronic* method.
#
# Sources: NIST Diatomic Spectral Database; Huber & Herzberg, Constants of Diatomic
# Molecules (1979).
#
#   formula -> (r_e in Angstrom, omega_e in cm^-1, molecular spin 2S)
GEOMETRY: Mapping[str, tuple[float, float, int]] = MappingProxyType({
    "H2":   (0.74144, 4401.2, 0),
    "N2":   (1.09768, 2358.6, 0),
    "O2":   (1.20752, 1580.2, 2),   # triplet ground state
    "F2":   (1.41193,  916.6, 0),
    "Cl2":  (1.98790,  559.7, 0),
    "I2":   (2.66600,  214.5, 0),
    "P2":   (1.89340,  780.8, 0),
    "S2":   (1.88920,  725.7, 2),   # triplet
    "C2":   (1.24250, 1855.0, 0),
    "Si2":  (2.24600,  510.9, 2),   # triplet
    "Na2":  (3.07890,  159.1, 0),
    "K2":   (3.90510,   92.4, 0),
    "HF":   (0.91680, 4138.3, 0),
    "HCl":  (1.27460, 2990.9, 0),
    "HI":   (1.60920, 2309.0, 0),
    "OH":   (0.96966, 3737.8, 1),   # doublet
    "CH":   (1.11990, 2858.5, 1),   # doublet
    "NH":   (1.03620, 3282.3, 2),   # triplet
    "SiO":  (1.50974, 1241.5, 0),
    "CS":   (1.53490, 1285.1, 0),
    "CO":   (1.12832, 2169.8, 0),
    "NO":   (1.15077, 1904.2, 1),   # doublet
    "CN":   (1.17180, 2068.6, 1),   # doublet
    "NaCl": (2.36085,  366.0, 0),
    "KCl":  (2.66665,  281.0, 0),
    "NaF":  (1.92595,  536.1, 0),
    "MgO":  (1.74900,  785.1, 0),
    "ICl":  (2.32090,  384.3, 0),
})

# Ground-state PySCF spin inputs: spin = N_alpha - N_beta = 2S. This is NOT the
# multiplicity, which is 2S + 1. Needed to compute the correct dissociation limit: a BDE
# is E(atoms) - E(molecule), and getting the atomic spin state wrong corrupts the
# reference point.
# Source: NIST Atomic Spectra Database ground-state term symbols.
ATOM_SPIN: Mapping[str, int] = MappingProxyType({
    "H": 1, "He": 0, "Li": 1, "Be": 0, "B": 1, "C": 2, "N": 3, "O": 2, "F": 1, "Ne": 0,
    "Na": 1, "Mg": 0, "Al": 1, "Si": 2, "P": 3, "S": 2, "Cl": 1, "Ar": 0,
    "K": 1, "Ca": 0, "Fe": 4, "Cu": 1, "Zn": 0, "Br": 1, "I": 1,
})

CM_TO_EV = 1.23984198e-4


def zero_point_energy_ev(formula: str) -> float | None:
    """Harmonic ZPE = 0.5 * omega_e, in eV. None if the frequency is not tabulated."""
    entry = GEOMETRY.get(formula)
    if entry is None:
        return None
    return 0.5 * entry[1] * CM_TO_EV


# --------------------------------------------------------------------------------------
# Polyatomic thermochemistry
# --------------------------------------------------------------------------------------
# WHAT IS STORED, AND WHY IT IS NOT THE ATOMIZATION ENERGY
#
# The quantity every polyatomic accuracy claim wants is the atomization energy. It is NOT
# stored here. What is stored is the enthalpy of formation at 0 K -- the quantity that was
# actually measured -- and `atomization_energy_ev` derives the rest:
#
#     D0(molecule) = sum_atoms n_i * dfH(atom_i, 0 K)  -  dfH(molecule, 0 K)
#
# Storing the derived number would have hidden the derivation, and the derivation is where
# a mistake would be invisible. It is also the difference between a reference value and a
# reference *calculation*: this way every number here traces to a measurement.
#
# THE NEAR-MISS THAT SET THIS POLICY
#
# Ethanol's atomization energy was, from memory, "32.72 eV". The derived value is 32.982.
# The recalled figure turned out to equal the bond-additivity estimate
# (C2H6 + CH3OH - CH4) to three decimals -- i.e. it was a reconstruction that silently
# assumed the isodesmic reaction C2H6 + CH3OH -> C2H5OH + CH4 is thermoneutral. It is not:
# it is -0.261 eV (-6.0 kcal/mol). Writing that from memory would have baked the very
# hypothesis `is_isodesmic` exists to test into the ground truth used to test it.
#
# ZERO-POINT ENERGY: WHOSE JOB IT IS
#
# These are D0 values -- dissociation from the vibrational ground state, which is what
# thermochemistry measures. An electronic-structure oracle computes De, the depth of the
# Born-Oppenheimer well. They differ by the molecule's zero-point energy:
#
#     De = D0 + ZPE(molecule)          (atoms have no vibrations, so no atomic term)
#
# The ZPE is NOT tabulated here on purpose. `smartchem.geometry.harmonic_analysis`
# computes it from a Hessian this system takes itself, and it carries a known +9.1%
# harmonic bias recorded in the signed `systematic_ev` channel. Tabulating a ZPE would
# replace an owned, error-barred quantity with a borrowed one.
#
# UNCERTAINTIES
#
# CCCBDB quotes dfH(0 K) to 0.1 kJ/mol without publishing an error bar. For those rows,
# `uncertainty_ev` is a curation scale based on the reported precision and atomic
# references, not a source-published or statistically calibrated interval with guaranteed
# coverage. ATcT is uncertainty-bearing, but this compact table still does not retain
# enough provenance to assign one uniform confidence level to every row. The atomic values
# are also COMMON across species: dfH(C, 0 K) enters every carbon compound with the same
# sign, so its error is systematic across this table, not random -- it does not average
# out over the set, and a mean absolute error computed here inherits it.
#
# Sources
# -------
# CCCBDB : NIST Computational Chemistry Comparison and Benchmark Database, Release 22,
#          "Experimental enthalpy of formation at 0 K" (cccbdb.nist.gov/hf0kx.asp).
# Check   : two values were reproduced from an independent literature compilation of
#          experimental atomization energies -- CH4 17.018 eV and C2H6 28.885 eV -- against
#          17.016 and 28.883 derived here. Agreement to 0.002 eV, ~20x inside chemical
#          accuracy. `test_derivation_reproduces_independent_literature_values` pins it.

#: dfH(0 K) of the gas-phase atoms, kJ/mol. Load-bearing: each enters multiplied by its
#: atom count, so an error here scales with molecule size. CCCBDB Release 22.
ATOM_FORMATION_KJ: Mapping[str, float] = MappingProxyType({
    "H": 216.0,
    "C": 711.2,
    "N": 470.8,
    "O": 246.8,
})

KJ_PER_EV = 96.485


@dataclass(frozen=True)
class PolyatomicRef:
    """An experimental enthalpy of formation at 0 K for a polyatomic molecule."""
    formula: str
    composition: Mapping[str, int]  # immutable element symbol -> positive count
    dfh_0k_kj: float                # enthalpy of formation at 0 K, kJ/mol
    uncertainty_ev: float           # reference scale; not a calibrated coverage claim
    split: Split
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.composition, MappingABC):
            raise TypeError("composition must be a mapping of element symbols to counts")
        if not self.composition:
            raise ValueError("composition must contain at least one element")

        copied: dict[str, int] = {}
        for symbol, count in self.composition.items():
            if not isinstance(symbol, str) or not symbol:
                raise ValueError("composition symbols must be non-empty strings")
            if type(count) is not int:
                raise TypeError("composition counts must be integers")
            if count < 1:
                raise ValueError("composition counts must be positive")
            copied[symbol] = count

        # Copy before wrapping so later mutation of the caller's dictionary cannot change
        # a supposedly frozen reference object. Sorting keeps representation deterministic.
        object.__setattr__(
            self,
            "composition",
            MappingProxyType(dict(sorted(copied.items()))),
        )


POLYATOMIC_REFS: tuple[PolyatomicRef, ...] = (
    PolyatomicRef("H2O",    {"H": 2, "O": 1},          -238.9, 0.004, "train", "CCCBDB R22"),
    PolyatomicRef("NH3",    {"N": 1, "H": 3},           -38.9, 0.006, "train", "CCCBDB R22"),
    PolyatomicRef("CH4",    {"C": 1, "H": 4},           -66.6, 0.008, "train", "CCCBDB R22"),
    PolyatomicRef("CO2",    {"C": 1, "O": 2},          -393.1, 0.008, "test",  "CCCBDB R22"),
    PolyatomicRef("H2O2",   {"H": 2, "O": 2},          -129.7, 0.010, "test",  "CCCBDB R22"),
    PolyatomicRef("N2H4",   {"N": 2, "H": 4},           109.3, 0.012, "test",  "CCCBDB R22"),
    PolyatomicRef("CH3OH",  {"C": 1, "H": 4, "O": 1},  -190.1, 0.008, "train", "CCCBDB R22"),
    PolyatomicRef("C2H6",   {"C": 2, "H": 6},           -68.4, 0.012, "train", "CCCBDB R22"),
    PolyatomicRef("C2H5OH", {"C": 2, "H": 6, "O": 1},  -217.1, 0.014, "test",  "CCCBDB R22"),
    # Added to give the isodesmic class more than one member -- see `is_isodesmic`.
    # Over the nine species above, exactly ONE strictly isodesmic reaction exists
    # (C2H6 + CH3OH -> C2H5OH + CH4), and n=1 cannot measure a predicate. These four
    # were chosen because they are cheap to canonicalise and each unlocks a reaction
    # whose bond signature is preserved exactly.
    PolyatomicRef("CH2O",    {"C": 1, "H": 2, "O": 1},         -104.9, 0.006, "train", "CCCBDB R22"),
    PolyatomicRef("HCOOH",   {"C": 1, "H": 2, "O": 2},         -371.5, 0.008, "test",  "CCCBDB R22"),
    PolyatomicRef("CH3OCH3", {"C": 2, "H": 6, "O": 1},         -166.6, 0.014, "train", "CCCBDB R22"),
    PolyatomicRef("CH3NH2",  {"C": 1, "N": 1, "H": 5},           -7.8, 0.010, "test",  "CCCBDB R22"),

    # -- C3, added for #17, and sourced from ATcT rather than CCCBDB. See the note below
    # on why the source changed for these three and not for the thirteen above.
    PolyatomicRef("C3H8",     {"C": 3, "H": 8},          -82.71, 0.016, "test",  "ATcT 1.202"),
    PolyatomicRef("CH3OC2H5", {"C": 3, "H": 8, "O": 1}, -194.27, 0.018, "train", "ATcT 1.202"),
    PolyatomicRef("C3H7OH",   {"C": 3, "H": 8, "O": 1}, -231.13, 0.018, "test",  "ATcT 1.202"),
)

# Why the last three came from a different source
# -----------------------------------------------
# The thirteen above are CCCBDB, which for 0 K publishes values DERIVED from 298 K
# measurements via TRC heat-content functions -- and publishes no uncertainties at all.
# That derivation has a documented failure: Karton et al. (arXiv:0905.3271) attribute a
# 1.1 kcal/mol (4.6 kJ/mol) error in the CCCBDB 0 K value for neopentane to an erroneous
# heat-content function. So the class of data is not uncertainty-bearing, whatever any
# individual entry happens to be worth.
#
# The Active Thermochemical Tables solve a whole thermochemical network at once and do
# publish 0 K values with uncertainties, so the C3 species take theirs from ATcT v1.202.
# All three were cross-checked and every CCCBDB value agrees within 0.67 kJ/mol; the
# switch was made to retain source-published uncertainty information, not because the
# central CCCBDB values were shown wrong.
#
# Mixing sources inside one table is a real hazard and is tolerated here for a measured
# reason: the largest disagreement between the two sources anywhere in this table is
# 0.67 kJ/mol = 0.007 eV, against Hartree-Fock reaction errors of 0.1-0.3 eV. It
# contributes under 5% of the smallest effect being measured. Re-sourcing the other
# thirteen is worth doing and is not worth blocking on.
#
# One more caution, learned the expensive way. A scrape of the CCCBDB 0 K table returned
# propane = -98.5 kJ/mol carrying the formula string CH3CH2CH2CH3 -- that is BUTANE's row.
# A second, narrower fetch of the identical URL returned the correct C3H8 | -82.4. Nothing
# in the wrong answer looked wrong: right magnitude, right sign, plausible for an alkane.
# This is the same failure mode as the ethanol near-miss documented above, arriving by a
# different route, and the same rule kills both: a reference value is not usable until a
# SECOND, INDEPENDENT source agrees with it.


def atomization_energy_ev(formula: str) -> float | None:
    """
    Experimental atomization energy D0 at 0 K, in eV. None if the species is not tabulated.

    Derived, not stored -- see the module note above. Positive means bound: the energy
    required to pull the molecule apart into ground-state neutral atoms.

    To compare against an electronic-structure result, add the molecule's zero-point
    energy: ``De = D0 + ZPE``. This module deliberately does not supply that ZPE.
    """
    ref = polyatomic(formula)
    if ref is None:
        return None
    atoms_kj = sum(n * ATOM_FORMATION_KJ[s] for s, n in ref.composition.items())
    return (atoms_kj - ref.dfh_0k_kj) / KJ_PER_EV


def polyatomic(formula: str) -> PolyatomicRef | None:
    """Look up one polyatomic reference by formula."""
    for ref in POLYATOMIC_REFS:
        if ref.formula == formula:
            return ref
    return None


def polyatomics(split: Split | None = None) -> tuple[PolyatomicRef, ...]:
    """Polyatomic references, optionally restricted to one split."""
    if split is None:
        return POLYATOMIC_REFS
    return tuple(r for r in POLYATOMIC_REFS if r.split == split)


def reaction_energy_ev(left: Mapping[str, int], right: Mapping[str, int]) -> float | None:
    """
    Experimental reaction energy at 0 K in eV, from formula -> positive integer
    stoichiometric coefficient on each side. Negative means exothermic. None if any
    species is missing.

    Computed from enthalpies of formation directly rather than by differencing atomization
    energies. Both routes are algebraically identical only when the atomic terms cancel,
    so this public reference helper validates elemental balance before publishing a number.
    Open reactions require explicit reservoirs/chemical potentials, which this helper does
    not accept; an unbalanced pseudo-reaction raises instead of acquiring an arbitrary
    reference-dependent value.
    """
    resolved: list[tuple[float, ...]] = []
    inventories: list[Counter[str]] = []
    for side_name, side in (("left", left), ("right", right)):
        if not isinstance(side, MappingABC):
            raise TypeError(f"{side_name} side must be a formula-to-coefficient mapping")
        if not side:
            raise ValueError(f"{side_name} side must contain at least one species")

        # Validate the complete mapping before looking up any formula, so an unknown first
        # row cannot hide malformed stoichiometry later in the same input.
        for formula, coefficient in side.items():
            if not isinstance(formula, str) or not formula:
                raise ValueError("reaction formulas must be non-empty strings")
            if type(coefficient) is not int:
                raise TypeError("stoichiometric coefficients must be integers")
            if coefficient <= 0:
                raise ValueError("stoichiometric coefficients must be positive")

        side_rows: list[float] = []
        inventory: Counter[str] = Counter()
        for formula, coefficient in side.items():
            reference = polyatomic(formula)
            if reference is None:
                return None
            composition = tuple(reference.composition.items())
            side_rows.append(coefficient * reference.dfh_0k_kj)
            for symbol, count in composition:
                inventory[symbol] += coefficient * count
        resolved.append(tuple(side_rows))
        inventories.append(inventory)

    if inventories[0] != inventories[1]:
        raise ValueError(
            "reaction must conserve elemental composition; explicit reservoirs are not "
            "supported by reaction_energy_ev"
        )

    total = 0.0
    for side_rows, sign in ((resolved[1], 1.0), (resolved[0], -1.0)):
        total += sign * sum(side_rows)
    return total / KJ_PER_EV


# Accuracy thresholds, stated once so no module invents its own.
KCAL_PER_EV = 23.0605
CHEMICAL_ACCURACY_EV = 1.0 / KCAL_PER_EV  # exactly 1 kcal/mol under this conversion
GOOD_SEMIEMPIRICAL_EV = 0.30   # a genuinely good fast method
USABLE_SCREENING_EV = 1.00     # useful for ranking, not for quoting
