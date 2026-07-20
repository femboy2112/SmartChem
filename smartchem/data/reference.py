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
* All energies in eV. 1 eV = 96.485 kJ/mol = 23.061 kcal/mol.
* BDE values are D0 (dissociation from the vibrational ground state) where available.
  Some sources tabulate D298; the two differ by roughly kT plus a zero-point correction,
  typically 0.02-0.05 eV for these species. The stated `uncertainty` absorbs that.
* `split` is declared explicitly rather than drawn at random so calibration is reproducible
  and auditable. TEST entries must never be used to fit anything. The split spans
  homonuclear / heteronuclear / ionic / covalent so it is representative, not adversarial.

Honesty note
------------
A benchmark is only as good as its coverage. `coverage_report()` states which reference
species the current periodic table can even attempt, so a good MAE over a tiny subset
cannot masquerade as a good MAE overall.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Split = Literal["train", "test"]


@dataclass(frozen=True)
class BondRef:
    """An experimental diatomic bond dissociation energy."""
    formula: str
    atoms: tuple[str, ...]      # element symbols, one per atom
    d0_ev: float                # dissociation energy, eV (positive = bound)
    uncertainty_ev: float       # honest error bar on the reference value itself
    split: Split
    kind: str                   # homonuclear | polar-covalent | ionic | multiple-bond
    source: str


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
    BondRef("H2",   ("H", "H"),   4.478, 0.001, "train", "homonuclear",    "NIST WebBook"),
    BondRef("N2",   ("N", "N"),   9.754, 0.005, "test",  "multiple-bond",  "NIST WebBook"),
    BondRef("O2",   ("O", "O"),   5.116, 0.003, "train", "multiple-bond",  "NIST WebBook"),
    BondRef("F2",   ("F", "F"),   1.602, 0.005, "train", "homonuclear",    "CRC 104th, 9-73"),
    BondRef("Cl2",  ("Cl", "Cl"), 2.479, 0.005, "train", "homonuclear",    "NIST WebBook (D0)"),
    BondRef("I2",   ("I", "I"),   1.542, 0.003, "test",  "homonuclear",    "NIST WebBook"),
    BondRef("P2",   ("P", "P"),   5.069, 0.020, "test",  "multiple-bond",  "CRC 104th, 9-73"),
    BondRef("S2",   ("S", "S"),   4.371, 0.020, "train", "multiple-bond",  "CRC 104th, 9-73"),
    BondRef("C2",   ("C", "C"),   6.213, 0.030, "train", "multiple-bond",  "NIST WebBook"),
    BondRef("Si2",  ("Si", "Si"), 3.210, 0.050, "test",  "homonuclear",    "CRC 104th, 9-73"),
    BondRef("Na2",  ("Na", "Na"), 0.720, 0.010, "train", "homonuclear",    "NIST WebBook"),
    BondRef("K2",   ("K", "K"),   0.514, 0.010, "test",  "homonuclear",    "NIST WebBook"),

    # --- polar covalent
    BondRef("HF",   ("H", "F"),   5.869, 0.003, "train", "polar-covalent", "NIST WebBook"),
    BondRef("HCl",  ("H", "Cl"),  4.434, 0.003, "test",  "polar-covalent", "NIST WebBook"),
    BondRef("HI",   ("H", "I"),   3.054, 0.005, "train", "polar-covalent", "NIST WebBook"),
    BondRef("OH",   ("O", "H"),   4.392, 0.004, "train", "polar-covalent", "NIST WebBook"),
    BondRef("CH",   ("C", "H"),   3.465, 0.010, "test",  "polar-covalent", "NIST WebBook"),
    BondRef("NH",   ("N", "H"),   3.400, 0.020, "train", "polar-covalent", "CRC 104th, 9-73"),
    BondRef("SiO",  ("Si", "O"),  8.263, 0.020, "test",  "multiple-bond",  "CRC 104th, 9-73"),
    BondRef("CS",   ("C", "S"),   7.355, 0.030, "train", "multiple-bond",  "CRC 104th, 9-73"),

    # --- strong multiple bonds: CO is the strongest known diatomic bond and the current
    #     engine refuses to form it at all.
    BondRef("CO",   ("C", "O"),  11.157, 0.005, "test",  "multiple-bond",  "NIST WebBook"),
    BondRef("NO",   ("N", "O"),   6.496, 0.005, "train", "multiple-bond",  "NIST WebBook"),
    BondRef("CN",   ("C", "N"),   7.738, 0.030, "train", "multiple-bond",  "CRC 104th, 9-73"),

    # --- ionic: the class the current model overshoots by ~3x
    BondRef("NaCl", ("Na", "Cl"), 4.234, 0.010, "train", "ionic",          "NIST WebBook"),
    BondRef("KCl",  ("K", "Cl"),  4.420, 0.020, "test",  "ionic",          "CRC 104th, 9-73"),
    BondRef("NaF",  ("Na", "F"),  4.945, 0.020, "train", "ionic",          "CRC 104th, 9-73"),
    BondRef("MgO",  ("Mg", "O"),  3.673, 0.070, "test",  "ionic",          "CRC 104th, 9-73"),

    # --- interhalogen
    BondRef("ICl",  ("I", "Cl"),  2.152, 0.010, "train", "polar-covalent", "NIST WebBook"),
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


# Accuracy thresholds, stated once so no module invents its own.
CHEMICAL_ACCURACY_EV = 0.043   # 1 kcal/mol. Reachable only by CCSD(T)/CBS-class methods.
GOOD_SEMIEMPIRICAL_EV = 0.30   # a genuinely good fast method
USABLE_SCREENING_EV = 1.00     # useful for ranking, not for quoting
