"""The periodic table SmartChem never actually had: complete, SOURCED standard atomic weights.

For most of this project's life ``smartchem.atoms`` carried a hand-maintained registry of ~29
elements in which ``Atom.mass_amu`` defaulted to ``0.0`` and was filled for only three of them
(H, K, I).  A chemistry engine whose carbon has no mass is not standing on a periodic table; it is
standing on a rumour.  This module is the fix: one authoritative table of the relative atomic mass
of every element, keyed by symbol, that the rest of the system resolves masses from.

PROVENANCE (why these numbers are allowed to be here)
-----------------------------------------------------
Every value is FETCHED from an authority and cross-checked, never recalled -- the repo's documented
memory-recall-poisoning history (see the near-miss recorded in ``data/reference.py``) is exactly why.

* Stable elements (Z = 1-92, excluding the eight naturally radioactive ones below): the IUPAC/CIAAW
  **abridged standard atomic weights**, from *Standard Atomic Weights of the Elements 2021 (IUPAC
  Technical Report)*, Prohaska, Irrgeher, Benefield, et al., Pure Appl. Chem. 2022, 94(5), 573-600,
  as published on the CIAAW abridged table (https://ciaaw.org/abridged-atomic-weights.htm) with the
  CIAAW 2024 revisions to Gd, Lu, and Zr included.  An "abridged" value is the conventional
  single-number representative of the interval that IUPAC assigns to elements whose isotopic
  composition varies in nature; 4-5 significant figures, which is far more than a molar mass or an
  ideal-gas entropy needs.
* The naturally radioactive elements with NO standard atomic weight (Tc, Pm, Po, At, Rn, Fr, Ra, Ac)
  and the synthetic elements (Z = 93-118): the mass number of the most stable / longest-lived known
  isotope.  These are NOT standard atomic weights -- no such quantity exists for these elements -- and
  ``has_standard_atomic_weight`` returns ``False`` for them so a caller can tell the difference.  The
  values are the ones the same IUPAC-sourced lists tabulate in brackets.

CROSS-CHECK (the two-blind-paths discipline, applied to a canonical table)
--------------------------------------------------------------------------
The CIAAW abridged table was cross-checked element-by-element against the IUPAC-attributed list at
https://en.wikipedia.org/wiki/List_of_chemical_elements .  For Z = 1-92 the two agreed to the abridged
digit on 91 of 92 stable elements; the single difference was zirconium (CIAAW 91.222 vs the older
91.224), which is the documented CIAAW **2024** revision -- so the newer 91.222 is used here.  A
disagreement that resolves to a dated revision is a passed audit, not a coin toss.

UNITS: unified atomic mass units (u, a.k.a. daltons; g/mol numerically).  ``mass_kg_per_molecule``
converts to SI kilograms via the CODATA atomic-mass constant.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

__all__ = [
    "STANDARD_ATOMIC_WEIGHT",
    "ATOMIC_NUMBER",
    "SYMBOL_OF_Z",
    "ATOMIC_MASS_CONSTANT_KG",
    "standard_atomic_weight",
    "has_standard_atomic_weight",
    "mass_kg_per_molecule",
]

#: The CODATA 2018 unified atomic-mass constant m_u = 1 u in kilograms (a MEASURED constant, so it
#: carries a source rather than being SI-exact).  Source: CODATA 2018,
#: https://physics.nist.gov/cgi-bin/cuu/Value?tukg .
ATOMIC_MASS_CONSTANT_KG = 1.66053906660e-27

# (Z, symbol, value).  Ordered by atomic number.  Values are abridged standard atomic weights
# (stable elements) or most-stable-isotope mass numbers (the radioactive/synthetic elements in
# ``_MASS_NUMBER_ONLY``).  See the module docstring for provenance and the cross-check.
_TABLE: tuple[tuple[int, str, float], ...] = (
    (1, "H", 1.0080), (2, "He", 4.0026), (3, "Li", 6.94), (4, "Be", 9.0122),
    (5, "B", 10.81), (6, "C", 12.011), (7, "N", 14.007), (8, "O", 15.999),
    (9, "F", 18.998), (10, "Ne", 20.180), (11, "Na", 22.990), (12, "Mg", 24.305),
    (13, "Al", 26.982), (14, "Si", 28.085), (15, "P", 30.974), (16, "S", 32.06),
    (17, "Cl", 35.45), (18, "Ar", 39.95), (19, "K", 39.098), (20, "Ca", 40.078),
    (21, "Sc", 44.956), (22, "Ti", 47.867), (23, "V", 50.942), (24, "Cr", 51.996),
    (25, "Mn", 54.938), (26, "Fe", 55.845), (27, "Co", 58.933), (28, "Ni", 58.693),
    (29, "Cu", 63.546), (30, "Zn", 65.38), (31, "Ga", 69.723), (32, "Ge", 72.630),
    (33, "As", 74.922), (34, "Se", 78.971), (35, "Br", 79.904), (36, "Kr", 83.798),
    (37, "Rb", 85.468), (38, "Sr", 87.62), (39, "Y", 88.906), (40, "Zr", 91.222),
    (41, "Nb", 92.906), (42, "Mo", 95.95), (43, "Tc", 97.0), (44, "Ru", 101.07),
    (45, "Rh", 102.91), (46, "Pd", 106.42), (47, "Ag", 107.87), (48, "Cd", 112.41),
    (49, "In", 114.82), (50, "Sn", 118.71), (51, "Sb", 121.76), (52, "Te", 127.60),
    (53, "I", 126.90), (54, "Xe", 131.29), (55, "Cs", 132.91), (56, "Ba", 137.33),
    (57, "La", 138.91), (58, "Ce", 140.12), (59, "Pr", 140.91), (60, "Nd", 144.24),
    (61, "Pm", 145.0), (62, "Sm", 150.36), (63, "Eu", 151.96), (64, "Gd", 157.25),
    (65, "Tb", 158.93), (66, "Dy", 162.50), (67, "Ho", 164.93), (68, "Er", 167.26),
    (69, "Tm", 168.93), (70, "Yb", 173.05), (71, "Lu", 174.97), (72, "Hf", 178.49),
    (73, "Ta", 180.95), (74, "W", 183.84), (75, "Re", 186.21), (76, "Os", 190.23),
    (77, "Ir", 192.22), (78, "Pt", 195.08), (79, "Au", 196.97), (80, "Hg", 200.59),
    (81, "Tl", 204.38), (82, "Pb", 207.2), (83, "Bi", 208.98), (84, "Po", 209.0),
    (85, "At", 210.0), (86, "Rn", 222.0), (87, "Fr", 223.0), (88, "Ra", 226.0),
    (89, "Ac", 227.0), (90, "Th", 232.04), (91, "Pa", 231.04), (92, "U", 238.03),
    (93, "Np", 237.0), (94, "Pu", 244.0), (95, "Am", 243.0), (96, "Cm", 247.0),
    (97, "Bk", 247.0), (98, "Cf", 251.0), (99, "Es", 252.0), (100, "Fm", 257.0),
    (101, "Md", 258.0), (102, "No", 259.0), (103, "Lr", 266.0), (104, "Rf", 267.0),
    (105, "Db", 268.0), (106, "Sg", 267.0), (107, "Bh", 270.0), (108, "Hs", 271.0),
    (109, "Mt", 278.0), (110, "Ds", 281.0), (111, "Rg", 282.0), (112, "Cn", 285.0),
    (113, "Nh", 286.0), (114, "Fl", 289.0), (115, "Mc", 290.0), (116, "Lv", 293.0),
    (117, "Ts", 294.0), (118, "Og", 294.0),
)

#: Elements whose tabulated value is a most-stable-isotope MASS NUMBER, not a standard atomic weight
#: (no standard atomic weight exists for them).  ``has_standard_atomic_weight`` consults this set.
_MASS_NUMBER_ONLY: frozenset[str] = frozenset(
    {"Tc", "Pm", "Po", "At", "Rn", "Fr", "Ra", "Ac"}
    | {sym for z, sym, _ in _TABLE if z >= 93}
)

#: symbol -> abridged standard atomic weight (or most-stable mass number; see ``_MASS_NUMBER_ONLY``).
STANDARD_ATOMIC_WEIGHT: Mapping[str, float] = MappingProxyType(
    {sym: value for _, sym, value in _TABLE}
)
#: symbol -> atomic number.
ATOMIC_NUMBER: Mapping[str, int] = MappingProxyType({sym: z for z, sym, _ in _TABLE})
#: atomic number -> symbol.
SYMBOL_OF_Z: Mapping[int, str] = MappingProxyType({z: sym for z, sym, _ in _TABLE})


def standard_atomic_weight(symbol: str) -> float:
    """The relative atomic mass of ``symbol`` in unified atomic mass units (u).

    Raises ``KeyError`` for an unknown symbol -- LOUD, never a silent ``0.0`` (a zero mass would
    corrupt every downstream reduced mass, moment of inertia, and Sackur-Tetrode term without a
    trace).  For a naturally radioactive or synthetic element the returned value is the mass number
    of the most stable isotope, not a true standard atomic weight; ``has_standard_atomic_weight``
    distinguishes the two.
    """
    try:
        return STANDARD_ATOMIC_WEIGHT[symbol]
    except KeyError:
        raise KeyError(
            f"no atomic weight for element symbol {symbol!r}; known symbols are H..Og (Z 1-118)"
        ) from None


def has_standard_atomic_weight(symbol: str) -> bool:
    """True iff ``symbol`` has a real IUPAC standard atomic weight (False for the radioactive/
    synthetic elements whose stored value is only a most-stable-isotope mass number)."""
    if symbol not in STANDARD_ATOMIC_WEIGHT:
        return False
    return symbol not in _MASS_NUMBER_ONLY


def mass_kg_per_molecule(molar_mass_u: float) -> float:
    """Convert a relative molecular mass (u, = g/mol numerically) to the mass of ONE molecule in kg."""
    return molar_mass_u * ATOMIC_MASS_CONSTANT_KG
