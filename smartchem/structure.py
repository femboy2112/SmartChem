"""M-4 v2 (rung 1) -- the structure bridge: resolve a bond-free ``Formula`` to a named compound.

v1's :class:`~smartchem.decompiler.Formula` is a bond-free atom multiset: every structural
isomer of ``C6H7NO`` shares one node.  That is correct for a *stoichiometric* decomposer, but a
chemist cannot act on "``C6H7NO``, some isomer" -- gap #3 of the paracetamol litmus.  This module
closes it by attaching a *specific* molecular structure (a real bond graph) to a formula, so
``C6H7NO`` resolves to **4-aminophenol** and the chemist sees a compound, not a composition.

Relocate, don't reinvent
------------------------
The bond graph is :class:`smartchem.category.Molecule` -- a labelled graph with 1-WL
canonicalization, already in the tree -- not a new type.  The forgetful structure->formula map is
:meth:`Molecule.formula` (atom multiset) piped through :meth:`Formula.of`.  This module is the thin
*registry* over that machinery: a small table of named compounds, each a verified ``Molecule``.

The one law (W3, unchanged from v1)
-----------------------------------
Attaching a structure certifies **connectivity and composition** -- that this formula names a real,
connected molecule with these bonds -- and nothing about thermodynamics, reactivity, or which isomer
a real sample actually is.  A registry entry is a *documented identity claim* (name + structure +
provenance), not a prediction that a decomposition yields this isomer.

The guard that bites -- and exactly how far it bites
----------------------------------------------------
Every registered structure declares its intended ``expected_formula`` and :func:`_check` rejects it
unless the ``Molecule``'s own composition matches -- so a mistyped atom list (build ``C6H8NO`` while
intending ``C6H7NO``) fails loudly at import. That is the conservation guard of
:mod:`smartchem.decompiler` applied to hand-entered graphs, and it catches the common hand-entry
error; ``Molecule.__post_init__`` separately enforces connectivity. What it does **not** verify is
*isomer identity*: a valid but wrong isomer of the right composition (a methyl-formate graph labelled
"acetic acid") passes the composition check. Isomer-correctness of the hand-entered graphs is the
author's responsibility, exercised by the differential identity tests (relabel-invariant and
isomer-separating), not certified by this guard.
"""

from __future__ import annotations

from dataclasses import dataclass

from .category import Bond, Molecule
from .contracts import Digestible, canonical_digest
from .decompiler import Formula
from .smiles import parse_smiles

__all__ = [
    "STRUCTURE_SCHEMA",
    "StructureError",
    "NamedStructure",
    "COMPOUND_REGISTRY",
    "known_compounds",
    "resolve_names",
    "resolve_structure",
    "structure_by_name",
    "registered_structures",
]

STRUCTURE_SCHEMA = "smartchem.structure/named-compound-v2"


class StructureError(ValueError):
    """A named structure's declared formula does not match its own bond graph."""


@dataclass(frozen=True)
class NamedStructure(Digestible):
    """One named compound: a real :class:`~smartchem.category.Molecule` plus its chemist-facing labels.

    ``expected_formula`` is the intended composition as a formula string; it is checked against the
    molecule's own composition at construction (the guard), then the *derived* :attr:`formula` is the
    one used everywhere -- so the two can never silently diverge.
    """

    name: str
    molecule: Molecule
    expected_formula: str
    iupac: str = ""
    cas: str = ""
    synonyms: tuple[str, ...] = ()
    provenance: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise StructureError("name must be a non-empty string")
        if type(self.molecule) is not Molecule:
            raise StructureError("molecule must be a smartchem.category.Molecule")
        if not isinstance(self.synonyms, tuple):
            raise StructureError("synonyms must be a tuple of strings")
        _check(self.molecule, self.expected_formula, self.name)

    @property
    def formula(self) -> Formula:
        """The forgetful structure->formula map: the bond-free v1 node this structure resolves."""
        return Formula.of(self.molecule.formula, self.molecule.charge)

    @property
    def composition(self) -> dict[str, int]:
        return dict(self.molecule.formula)

    @property
    def canonical_molecule(self) -> Molecule | None:
        """The 1-WL canonical form, or ``None`` if canonicalization refused this graph.

        :meth:`Molecule.canonical` raises ``NotImplementedError`` on graphs whose symmetry blows its
        candidate budget (bare vertex-transitive rings). ``None`` is returned rather than swallowed
        so :attr:`canonical_identity_is_invariant` can report the truth.
        """
        try:
            return self.molecule.canonical()
        except NotImplementedError:
            return None

    @property
    def canonical_identity_is_invariant(self) -> bool:
        """True iff this structure has a presentation-invariant identity (canonicalization succeeded)."""
        return self.canonical_molecule is not None

    @property
    def structure_identity(self) -> str:
        """A structural identity digest.

        When canonicalization succeeds the digest is over the canonical form and is
        presentation-invariant (any drawing of this molecule yields the same identity). When it
        refuses, the digest is over the *as-given* graph and is presentation-SENSITIVE -- marked with
        an ``asgiven:`` prefix so the two are never confused.
        """
        canonical = self.canonical_molecule
        if canonical is not None:
            return canonical_digest(canonical)
        return "asgiven:" + canonical_digest(self.molecule)

    @property
    def all_names(self) -> tuple[str, ...]:
        """Common name first, then IUPAC and synonyms (deduplicated, order-stable)."""
        seen: dict[str, None] = {}
        for label in (self.name, self.iupac, *self.synonyms):
            if label:
                seen.setdefault(label, None)
        return tuple(seen)


def _check(molecule: Molecule, expected_formula: str, name: str) -> None:
    """Reject a structure whose bond graph does not carry its declared composition."""
    got = Formula.of(molecule.formula, molecule.charge)
    want = Formula.parse(expected_formula)
    if got != want:
        raise StructureError(
            f"{name!r} declares {expected_formula} ({want!r}) but its bond graph is {got!r}; "
            f"the atom list does not match the intended formula"
        )


# ======================================================================================
# The named-compound bond graphs.  Each is hand-entered and verified by _check at import.
# Aromatic rings are drawn in one Kekule form (alternating bond orders); canonicalization
# treats the graph as given.
# ======================================================================================
def _mol(atoms: tuple[str, ...], bonds: set[Bond]) -> Molecule:
    return Molecule(atoms=atoms, bonds=frozenset(bonds))


# H2O -- O0 with two H
_WATER = _mol(("O", "H", "H"), {Bond(0, 1), Bond(0, 2)})

# --- common small molecules (single dominant isomer each) --------------------------------
# carbon monoxide, C#O
_CARBON_MONOXIDE = _mol(("C", "O"), {Bond(0, 1, 3)})
# carbon dioxide, O=C=O
_CARBON_DIOXIDE = _mol(("C", "O", "O"), {Bond(0, 1, 2), Bond(0, 2, 2)})
# methane, CH4
_METHANE = _mol(("C", "H", "H", "H", "H"), {Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4)})
# ammonia, NH3
_AMMONIA = _mol(("N", "H", "H", "H"), {Bond(0, 1), Bond(0, 2), Bond(0, 3)})
# hydrogen peroxide, H-O-O-H
_HYDROGEN_PEROXIDE = _mol(("O", "O", "H", "H"), {Bond(0, 1), Bond(0, 2), Bond(1, 3)})
# methanol, CH3-OH
_METHANOL = _mol(
    ("C", "O", "H", "H", "H", "H"),
    {Bond(0, 1), Bond(1, 2), Bond(0, 3), Bond(0, 4), Bond(0, 5)},
)
# formaldehyde, H2C=O
_FORMALDEHYDE = _mol(("C", "O", "H", "H"), {Bond(0, 1, 2), Bond(0, 2), Bond(0, 3)})
# formic acid, H-C(=O)-O-H
_FORMIC_ACID = _mol(
    ("C", "O", "O", "H", "H"),
    {Bond(0, 1, 2), Bond(0, 2), Bond(2, 3), Bond(0, 4)},
)

# --- isomer pairs and heteroatom species (the isomer-keyed-evidence subjects) -------------
# ethanol, CH3-CH2-OH  (C2H6O)
_ETHANOL = _mol(
    ("C", "C", "O", "H", "H", "H", "H", "H", "H"),
    {Bond(0, 1), Bond(1, 2), Bond(2, 8), Bond(0, 3), Bond(0, 4), Bond(0, 5), Bond(1, 6), Bond(1, 7)},
)
# dimethyl ether, CH3-O-CH3  (C2H6O -- same formula as ethanol, different structure)
_DIMETHYL_ETHER = _mol(
    ("C", "C", "O", "H", "H", "H", "H", "H", "H"),
    {Bond(0, 2), Bond(1, 2), Bond(0, 3), Bond(0, 4), Bond(0, 5), Bond(1, 6), Bond(1, 7), Bond(1, 8)},
)
# acetone, CH3-C(=O)-CH3  (C3H6O)
_ACETONE = _mol(
    ("C", "C", "C", "O", "H", "H", "H", "H", "H", "H"),
    {Bond(0, 1), Bond(1, 2), Bond(1, 3, 2), Bond(0, 4), Bond(0, 5), Bond(0, 6),
     Bond(2, 7), Bond(2, 8), Bond(2, 9)},
)
# methylamine, CH3-NH2  (CH5N)
_METHYLAMINE = _mol(
    ("C", "N", "H", "H", "H", "H", "H"),
    {Bond(0, 1), Bond(0, 2), Bond(0, 3), Bond(0, 4), Bond(1, 5), Bond(1, 6)},
)
# hydrogen cyanide, H-C#N  (CHN)
_HYDROGEN_CYANIDE = _mol(("C", "N", "H"), {Bond(0, 1, 3), Bond(0, 2)})
# nitric oxide, N=O  (NO)
_NITRIC_OXIDE = _mol(("N", "O"), {Bond(0, 1, 2)})
# nitrogen dioxide, O=N-O  (NO2, one Kekule form)
_NITROGEN_DIOXIDE = _mol(("N", "O", "O"), {Bond(0, 1, 2), Bond(0, 2)})
# sulfur dioxide, O=S=O  (O2S)
_SULFUR_DIOXIDE = _mol(("S", "O", "O"), {Bond(0, 1, 2), Bond(0, 2, 2)})

# 4-aminophenyl acetate -- the O-acetyl (ESTER) isomer of paracetamol, C8H9NO2
# CH3-C(=O)-O-C6H4-NH2: ring C0..C5, amine N6 on C3, ester O7 on C0, carbonyl C8(=O9), methyl C10
_AMINOPHENYL_ACETATE = _mol(
    ("C", "C", "C", "C", "C", "C", "N", "O", "C", "O", "C",
     "H", "H", "H", "H", "H", "H", "H", "H", "H"),
    {
        Bond(0, 1, 2), Bond(1, 2, 1), Bond(2, 3, 2), Bond(3, 4, 1), Bond(4, 5, 2), Bond(5, 0, 1),
        Bond(0, 7), Bond(7, 8),                        # C0-O7-C8  (ester linkage)
        Bond(3, 6), Bond(6, 11), Bond(6, 12),          # C3-N, N-H, N-H  (free amine)
        Bond(8, 9, 2), Bond(8, 10),                    # C8=O9, C8-C10
        Bond(10, 13), Bond(10, 14), Bond(10, 15),      # methyl H
        Bond(1, 16), Bond(2, 17), Bond(4, 18), Bond(5, 19),  # ring H
    },
)

# ketene, CH2=C=O -- C0(H2)=C1=O2
_KETENE = _mol(
    ("C", "C", "O", "H", "H"),
    {Bond(0, 1, 2), Bond(1, 2, 2), Bond(0, 3), Bond(0, 4)},
)

# acetic acid, CH3-C(=O)-OH -- C0 methyl, C1 carbonyl, O2 (=O), O3 (-OH)
_ACETIC_ACID = _mol(
    ("C", "C", "O", "O", "H", "H", "H", "H"),
    {Bond(0, 1), Bond(1, 2, 2), Bond(1, 3), Bond(3, 7), Bond(0, 4), Bond(0, 5), Bond(0, 6)},
)

# acetic anhydride, (CH3CO)2O -- C0(H3)-C1(=O2)-O3-C4(=O5)-C6(H3)
_ACETIC_ANHYDRIDE = _mol(
    ("C", "C", "O", "O", "C", "O", "C", "H", "H", "H", "H", "H", "H"),
    {
        Bond(0, 1), Bond(1, 2, 2), Bond(1, 3), Bond(3, 4), Bond(4, 5, 2), Bond(4, 6),
        Bond(0, 7), Bond(0, 8), Bond(0, 9), Bond(6, 10), Bond(6, 11), Bond(6, 12),
    },
)

# 4-aminophenol, HO-C6H4-NH2 (para) -- ring C0..C5, phenol O7 on C0, amine N6 on C3
_P_AMINOPHENOL = _mol(
    ("C", "C", "C", "C", "C", "C", "N", "O", "H", "H", "H", "H", "H", "H", "H"),
    {
        Bond(0, 1, 2), Bond(1, 2, 1), Bond(2, 3, 2), Bond(3, 4, 1), Bond(4, 5, 2), Bond(5, 0, 1),
        Bond(0, 7), Bond(7, 14),                       # C0-O-H  (phenol)
        Bond(3, 6), Bond(6, 12), Bond(6, 13),          # C3-N, N-H, N-H  (amine)
        Bond(1, 8), Bond(2, 9), Bond(4, 10), Bond(5, 11),  # ring H on C1,C2,C4,C5
    },
)

# paracetamol / acetaminophen, HO-C6H4-NH-C(=O)-CH3 (4-acetamidophenol)
# ring C0..C5, phenol O6 on C0, amide N7 on C3, carbonyl C8(=O9), methyl C10
_PARACETAMOL = _mol(
    ("C", "C", "C", "C", "C", "C", "O", "N", "C", "O", "C",
     "H", "H", "H", "H", "H", "H", "H", "H", "H"),
    {
        Bond(0, 1, 2), Bond(1, 2, 1), Bond(2, 3, 2), Bond(3, 4, 1), Bond(4, 5, 2), Bond(5, 0, 1),
        Bond(0, 6), Bond(6, 11),                       # C0-O-H  (phenol)
        Bond(3, 7), Bond(7, 12), Bond(7, 8),           # C3-N, N-H, N-C(=O)  (amide)
        Bond(8, 9, 2), Bond(8, 10),                    # C8=O9, C8-C10  (carbonyl + methyl)
        Bond(10, 13), Bond(10, 14), Bond(10, 15),      # methyl H
        Bond(1, 16), Bond(2, 17), Bond(4, 18), Bond(5, 19),  # ring H on C1,C2,C4,C5
    },
)


_REGISTERED: tuple[NamedStructure, ...] = (
    NamedStructure(
        "water", _WATER, "H2O", iupac="oxidane", cas="7732-18-5",
        provenance="elementary structure",
    ),
    NamedStructure(
        "carbon monoxide", _CARBON_MONOXIDE, "CO", iupac="carbon monoxide", cas="630-08-0",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "carbon dioxide", _CARBON_DIOXIDE, "CO2", iupac="carbon dioxide", cas="124-38-9",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "methane", _METHANE, "CH4", iupac="methane", cas="74-82-8",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "ammonia", _AMMONIA, "NH3", iupac="azane", cas="7664-41-7",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "hydrogen peroxide", _HYDROGEN_PEROXIDE, "H2O2", iupac="hydrogen peroxide",
        cas="7722-84-1", provenance="std small-molecule structure",
    ),
    NamedStructure(
        "methanol", _METHANOL, "CH4O", iupac="methanol", cas="67-56-1",
        synonyms=("methyl alcohol", "wood alcohol"), provenance="std small-molecule structure",
    ),
    NamedStructure(
        "formaldehyde", _FORMALDEHYDE, "CH2O", iupac="methanal", cas="50-00-0",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "formic acid", _FORMIC_ACID, "CH2O2", iupac="methanoic acid", cas="64-18-6",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "ethanol", _ETHANOL, "C2H6O", iupac="ethanol", cas="64-17-5",
        synonyms=("ethyl alcohol",), provenance="std organic structure; the C2H6O isomer pair",
    ),
    NamedStructure(
        "dimethyl ether", _DIMETHYL_ETHER, "C2H6O", iupac="methoxymethane", cas="115-10-6",
        synonyms=("methyl ether",), provenance="std organic structure; the C2H6O isomer pair",
    ),
    NamedStructure(
        "acetone", _ACETONE, "C3H6O", iupac="propan-2-one", cas="67-64-1",
        synonyms=("propanone", "dimethyl ketone"), provenance="std organic structure",
    ),
    NamedStructure(
        "methylamine", _METHYLAMINE, "CH5N", iupac="methanamine", cas="74-89-5",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "hydrogen cyanide", _HYDROGEN_CYANIDE, "CHN", iupac="formonitrile", cas="74-90-8",
        synonyms=("prussic acid", "hydrocyanic acid"), provenance="std small-molecule structure",
    ),
    NamedStructure(
        "nitric oxide", _NITRIC_OXIDE, "NO", iupac="nitric oxide", cas="10102-43-9",
        synonyms=("nitrogen monoxide",), provenance="std small-molecule structure",
    ),
    NamedStructure(
        "nitrogen dioxide", _NITROGEN_DIOXIDE, "NO2", iupac="nitrogen dioxide", cas="10102-44-0",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "sulfur dioxide", _SULFUR_DIOXIDE, "O2S", iupac="sulfur dioxide", cas="7446-09-5",
        provenance="std small-molecule structure",
    ),
    NamedStructure(
        "4-aminophenyl acetate", _AMINOPHENYL_ACETATE, "C8H9NO2",
        iupac="(4-aminophenyl) acetate", cas="3993-73-1",
        synonyms=("p-aminophenyl acetate",),
        provenance="the O-acetyl (ester) ISOMER of paracetamol; same formula, distinct structure",
    ),
    NamedStructure(
        "ketene", _KETENE, "C2H2O", iupac="ethenone", cas="463-51-4",
        provenance="std organic structure; the reactive acetylating intermediate",
    ),
    NamedStructure(
        "acetic acid", _ACETIC_ACID, "C2H4O2", iupac="acetic acid", cas="64-19-7",
        synonyms=("ethanoic acid",), provenance="std organic structure",
    ),
    NamedStructure(
        "acetic anhydride", _ACETIC_ANHYDRIDE, "C4H6O3", iupac="acetic anhydride",
        cas="108-24-7", synonyms=("ethanoic anhydride",),
        provenance="std organic structure; the classic acetylating reagent",
    ),
    NamedStructure(
        "4-aminophenol", _P_AMINOPHENOL, "C6H7NO", iupac="4-aminophenol", cas="123-30-8",
        synonyms=("p-aminophenol", "para-aminophenol"),
        provenance="std organic structure; the regulated hydrolytic degradant of paracetamol",
    ),
    NamedStructure(
        "paracetamol", _PARACETAMOL, "C8H9NO2", iupac="N-(4-hydroxyphenyl)acetamide",
        cas="103-90-2", synonyms=("acetaminophen", "4-acetamidophenol", "APAP"),
        provenance="std organic structure; the litmus target",
    ),
    # --- G5: common decomposition products, structures parsed from SMILES (G1) so the widened
    #     hazard data has a registered isomer to pin to. Symmetric/mono-substituted aromatics are
    #     Kekulé-invariant, so their canonical identity is stable. ------------------------------
    NamedStructure(
        "benzene", parse_smiles("c1ccccc1"), "C6H6", iupac="benzene", cas="71-43-2",
        provenance="std aromatic parent; SMILES c1ccccc1",
    ),
    NamedStructure(
        "hydrogen sulfide", parse_smiles("S"), "H2S", iupac="sulfane", cas="7783-06-4",
        synonyms=("sulfureted hydrogen",),
        provenance="std inorganic decomposition product; SMILES S",
    ),
    NamedStructure(
        "acetaldehyde", parse_smiles("CC=O"), "C2H4O", iupac="acetaldehyde", cas="75-07-0",
        synonyms=("ethanal",), provenance="std organic oxidation product; SMILES CC=O",
    ),
    NamedStructure(
        "ethylene", parse_smiles("C=C"), "C2H4", iupac="ethene", cas="74-85-1",
        synonyms=("ethene",), provenance="std alkene; SMILES C=C",
    ),
    NamedStructure(
        "acetylene", parse_smiles("C#C"), "C2H2", iupac="ethyne", cas="74-86-2",
        synonyms=("ethyne",), provenance="std alkyne; SMILES C#C",
    ),
    NamedStructure(
        "phenol", parse_smiles("Oc1ccccc1"), "C6H6O", iupac="phenol", cas="108-95-2",
        synonyms=("carbolic acid", "hydroxybenzene"),
        provenance="std aromatic alcohol; SMILES Oc1ccccc1",
    ),
    # --- S2/Mid-1: competing PRODUCT isomers for sourced regiochemical selectivity beyond paracetamol.
    #     Ooh, look at me, two whole isomer PAIRS -- C3H8O splits Markovnikov-wise, C6H4N2O4 splits
    #     ortho/meta/para-wise; can't tell "the major one" apart without a name for each! ------------
    NamedStructure(
        "propan-1-ol", parse_smiles("CCCO"), "C3H8O", iupac="propan-1-ol", cas="71-23-8",
        synonyms=("1-propanol", "n-propanol"),
        provenance="std primary alcohol; SMILES CCCO",
    ),
    NamedStructure(
        "propan-2-ol", parse_smiles("CC(O)C"), "C3H8O", iupac="propan-2-ol", cas="67-63-0",
        synonyms=("2-propanol", "isopropanol", "isopropyl alcohol"),
        provenance="std secondary alcohol; SMILES CC(O)C",
    ),
    NamedStructure(
        "1,3-dinitrobenzene", parse_smiles("[O-][N+](=O)c1cccc([N+](=O)[O-])c1"), "C6H4N2O4",
        iupac="1,3-dinitrobenzene", cas="99-65-0",
        synonyms=("m-dinitrobenzene", "meta-dinitrobenzene"),
        provenance="std meta-nitration product; SMILES [O-][N+](=O)c1cccc([N+](=O)[O-])c1",
    ),
    NamedStructure(
        "1,4-dinitrobenzene", parse_smiles("[O-][N+](=O)c1ccc([N+](=O)[O-])cc1"), "C6H4N2O4",
        iupac="1,4-dinitrobenzene", cas="100-25-4",
        synonyms=("p-dinitrobenzene", "para-dinitrobenzene"),
        provenance="std para-nitration product; SMILES [O-][N+](=O)c1ccc([N+](=O)[O-])cc1",
    ),
    # reactants for the sourced selectivity records, so the S2 reactant-isomer guard can key on them
    NamedStructure(
        "propene", parse_smiles("CC=C"), "C3H6", iupac="prop-1-ene", cas="115-07-1",
        synonyms=("propylene", "1-propene", "methylethylene"),
        provenance="std alkene; the Markovnikov-hydration substrate; SMILES CC=C",
    ),
    NamedStructure(
        "nitrobenzene", parse_smiles("O=[N+]([O-])c1ccccc1"), "C6H5NO2", iupac="nitrobenzene",
        cas="98-95-3", synonyms=("nitrobenzol",),
        provenance="std aromatic; the meta-director nitration substrate; SMILES O=[N+]([O-])c1ccccc1",
    ),
    NamedStructure(
        "nitric acid", parse_smiles("O[N+](=O)[O-]"), "HNO3", iupac="nitric acid", cas="7697-37-2",
        synonyms=("aqua fortis",),
        provenance="std mineral acid; the nitrating agent; SMILES O[N+](=O)[O-]",
    ),
)


def _build_registry() -> dict[Formula, tuple[NamedStructure, ...]]:
    index: dict[Formula, list[NamedStructure]] = {}
    for structure in _REGISTERED:
        index.setdefault(structure.formula, []).append(structure)
    return {formula: tuple(entries) for formula, entries in index.items()}


#: Formula -> the known named compounds of that composition. A formula may map to several isomers;
#: today each litmus formula maps to exactly one, but the tuple shape keeps isomer plurality honest.
COMPOUND_REGISTRY: dict[Formula, tuple[NamedStructure, ...]] = _build_registry()


def known_compounds(formula: "str | dict[str, int] | Formula") -> tuple[NamedStructure, ...]:
    """Every registered named structure whose composition is ``formula`` (empty tuple if none)."""
    key = formula if isinstance(formula, Formula) else (
        Formula.parse(formula) if isinstance(formula, str) else Formula.of(formula)
    )
    return COMPOUND_REGISTRY.get(key, ())


def resolve_names(formula: "str | dict[str, int] | Formula") -> tuple[str, ...]:
    """The common names of the registered compounds for ``formula`` (empty if unregistered)."""
    return tuple(s.name for s in known_compounds(formula))


def resolve_structure(molecule: Molecule) -> "NamedStructure | None":
    """The registered isomer whose bond graph IS ``molecule`` (by canonical identity), or ``None``.

    This is the isomer-resolved lookup that closes the formula-keying gap: given an actual structure
    (a decomposition product, say), it names the *specific* isomer -- ethanol vs dimethyl ether,
    paracetamol vs 4-aminophenyl acetate -- so evidence can be attached by structure, not by an
    ambiguous formula. Returns ``None`` when no registered isomer matches, or when the graph cannot be
    canonicalized (a vertex-transitive ring, per :attr:`NamedStructure.canonical_identity_is_invariant`)
    -- in which case there is no confident structural match to claim.
    """
    if type(molecule) is not Molecule:
        raise StructureError("resolve_structure needs a smartchem.category.Molecule")
    candidates = known_compounds(Formula.of(molecule.formula, molecule.charge))
    if not candidates:
        return None
    try:
        key = canonical_digest(molecule.canonical())
    except NotImplementedError:
        return None
    for structure in candidates:
        if structure.canonical_identity_is_invariant and structure.structure_identity == key:
            return structure
    return None


def structure_by_name(name: str) -> "NamedStructure | None":
    """The registered structure whose common name, IUPAC, or a synonym matches ``name``.

    Case- and surrounding-whitespace-insensitive over :attr:`NamedStructure.all_names`.  This is the
    offline name->structure resolver: it lets a chemist warm the cache or key evidence by a compound's
    NAME without a network round-trip, for any compound the registry carries.  Returns ``None`` on a miss
    (the caller falls back to a live name->structure resolution, or reports a loud skip) -- never a guess.
    """
    if not isinstance(name, str) or not name.strip():
        return None
    needle = name.strip().casefold()
    for structure in _REGISTERED:
        if any(label.casefold() == needle for label in structure.all_names):
            return structure
    return None


def registered_structures() -> tuple[NamedStructure, ...]:
    """Every registered named structure, in registration order."""
    return _REGISTERED
