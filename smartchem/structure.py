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

__all__ = [
    "STRUCTURE_SCHEMA",
    "StructureError",
    "NamedStructure",
    "COMPOUND_REGISTRY",
    "known_compounds",
    "resolve_names",
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


def registered_structures() -> tuple[NamedStructure, ...]:
    """Every registered named structure, in registration order."""
    return _REGISTERED
