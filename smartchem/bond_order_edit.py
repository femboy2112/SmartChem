"""CHEM-ALG-01: the partial bond-order-edit transform family -- a SECOND, qualitatively distinct transform algebra.

The capped-scission family (:mod:`smartchem.structure_descent`) rewrites WHOLE bonds: it breaks order-1 bonds and
caps the opened ends with reagent fragments.  It explicitly excludes changing an EXISTING bond's ORDER (its own
docstring: "partial bond-order change (addition ACROSS a double bond) ... is not a whole-bond rewrite").  This
module is exactly that excluded family, registered through the TRANSFORM-PROVIDER-01 boundary so it composes
through the UNCHANGED bounded search -- the concrete demonstration that widening the algebra needs no new
search-engine branch (CHEM-ALG-01).

The DECOMPILE reading of a bond-order edit is a **dehydrogenation**: raise one bond's order by one and shed one
hydrogen from each endpoint as H2 --

    reactant  ->  precursor + H2        (e.g.  ethane -> ethene + H2)

Its reverse (the synthesis step the recompiler reads) is a **hydrogenation**: ``precursor + H2 -> reactant``.  The
family is neutral and its products are stable closed molecules (an alkene and H2, not radicals or ions), so it
composes cleanly into a retro route/DAG search that terminates at stock molecules, and it forgets to a plain
composition-level :class:`~smartchem.decompiler.DecompositionEdge` (no reagent consumed).

W3 unchanged: a bond-order edit certifies that such a valence-preserving rewrite EXISTS, never that the
dehydrogenation/hydrogenation runs or under what conditions.  Absent a sourced conditions record it stays a
``FORMAL_CANDIDATE``, gated by the same evidence machinery as every other family (no bespoke path).
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Bond, Molecule
from .contracts import Digestible, canonical_digest
from .decompiler import DecompositionEdge, Formula
from .structure_descent import ScissionError, _fkey
from .transform_provider import TransformProvider

__all__ = [
    "BOND_ORDER_EDIT_SCHEMA",
    "BondOrderEdit",
    "bond_order_edits",
    "BondOrderEditProvider",
]

BOND_ORDER_EDIT_SCHEMA = "smartchem.bond-order-edit/dehydrogenation-v1"

_MAX_BOND_ORDER = 3  # a single may go to double, a double to triple; a triple cannot be raised


def _hydrogen_molecule() -> Molecule:
    """Dihydrogen H2 as a canonical two-atom molecule (the shed pair)."""
    return Molecule(("H", "H"), frozenset({Bond(0, 1, 1)}), 0, "").canonical()


def _h_neighbors(mol: Molecule, atom: int) -> tuple[int, ...]:
    """The hydrogen atoms bonded to ``atom`` by an order-1 bond (the H's a dehydrogenation could shed)."""
    out: list[int] = []
    for b in mol.bonds:
        if b.order != 1:
            continue
        other = b.j if b.i == atom else (b.i if b.j == atom else None)
        if other is not None and mol.atoms[other] == "H":
            out.append(other)
    return tuple(sorted(out))


def _raised_bond(mol: Molecule, i: int, j: int):
    for b in mol.bonds:
        if (b.i, b.j) == (min(i, j), max(i, j)):
            return b
    return None


@dataclass(frozen=True)
class BondOrderEdit(Digestible):
    """One partial bond-order edit: raise the ``(bond_i, bond_j)`` bond by one order, shedding ``h_i`` from
    ``bond_i`` and ``h_j`` from ``bond_j`` as H2.  The constructor is the certificate -- every invariant is
    recomputed from the stored fields, so a hand-built edit that lies about its atoms fails here."""

    schema_version: str
    reactant: Molecule
    bond_i: int
    bond_j: int
    h_i: int
    h_j: int

    def __post_init__(self) -> None:
        if self.schema_version != BOND_ORDER_EDIT_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {BOND_ORDER_EDIT_SCHEMA!r}")
        if type(self.reactant) is not Molecule:
            raise ScissionError("reactant must be a smartchem.category.Molecule")
        if self.reactant.charge != 0:
            raise ScissionError("bond-order edit supports neutral species only")
        for name in ("bond_i", "bond_j", "h_i", "h_j"):
            if type(getattr(self, name)) is not int:
                raise ScissionError(f"{name} must be an int atom index")
        n = len(self.reactant.atoms)
        if not (0 <= self.bond_i < n and 0 <= self.bond_j < n and self.bond_i != self.bond_j):
            raise ScissionError("bond endpoints must be distinct in-range atom indices")
        raised = _raised_bond(self.reactant, self.bond_i, self.bond_j)
        if raised is None:
            raise ScissionError("(bond_i, bond_j) is not a bond of the reactant")
        if raised.order >= _MAX_BOND_ORDER:
            raise ScissionError("the bond is already at maximal order and cannot be raised")
        if self.h_i not in _h_neighbors(self.reactant, self.bond_i):
            raise ScissionError("h_i must be an order-1 hydrogen bonded to bond_i")
        if self.h_j not in _h_neighbors(self.reactant, self.bond_j):
            raise ScissionError("h_j must be an order-1 hydrogen bonded to bond_j")
        if self.h_i == self.h_j:
            raise ScissionError("h_i and h_j must be distinct hydrogens (one shed from each endpoint)")
        # force the products: rebuilding the precursor runs Molecule's own validation, and the DecompositionEdge
        # forget re-checks conservation and W1 descent -- so an edit that would produce an invalid molecule or a
        # non-descending decomposition is refused at construction (the certificate).
        products = self.products
        if len(products) != 2:
            raise ScissionError("a bond-order edit yields exactly the precursor and H2")
        self.forget()

    @property
    def reagents(self) -> tuple:
        """A bond-order edit consumes no reagent -- H2 is a PRODUCT, not a mediator.  The uniform transform
        interface still exposes ``reagents`` (empty here)."""
        return ()

    def _precursor(self) -> Molecule:
        removed = {self.h_i, self.h_j}
        keep = [k for k in range(len(self.reactant.atoms)) if k not in removed]
        remap = {old: new for new, old in enumerate(keep)}
        atoms = tuple(self.reactant.atoms[k] for k in keep)
        bonds = set()
        for b in self.reactant.bonds:
            if b.i in removed or b.j in removed:
                continue  # drop the two shed C-H bonds
            order = b.order + 1 if {b.i, b.j} == {self.bond_i, self.bond_j} else b.order
            a, c = remap[b.i], remap[b.j]
            bonds.add(Bond(min(a, c), max(a, c), order))
        return Molecule(atoms, frozenset(bonds), self.reactant.charge, self.reactant.state).canonical()

    @property
    def products(self) -> tuple[Molecule, ...]:
        """The derived, canonical products: the precursor (bond raised, two H shed) and H2, sorted deterministically."""
        return tuple(
            sorted((self._precursor(), _hydrogen_molecule()), key=lambda m: (len(m.atoms), repr(m)))
        )

    def forget(self) -> DecompositionEdge:
        """The forgetful image: the composition-level :class:`~smartchem.decompiler.DecompositionEdge`
        ``reactant -> precursor + H2`` (no reagent).  Mirrors :meth:`ScissionEdge.forget`'s element-bucket merge
        and canonical sort, so the structural candidate's independent recompute matches it byte-for-byte."""
        merged: dict[Formula, int] = {}
        for m in self.products:
            comp = Formula.of(m.formula, m.charge)
            if comp.is_element:
                (symbol, count), = comp.counts
                bucket = Formula.bucket(symbol)
                merged[bucket] = merged.get(bucket, 0) + count
            else:
                merged[comp] = merged.get(comp, 0) + 1
        products = tuple(sorted(merged.items(), key=lambda pm: (_fkey(pm[0]), pm[1])))
        return DecompositionEdge(Formula.of(self.reactant.formula, self.reactant.charge), 1, products)

    def equation(self) -> str:
        rhs = " + ".join(repr(p) for p in self.products)
        return f"{self.reactant!r} --raise[{self.bond_i}={self.bond_j}]--> {rhs}"

    def __repr__(self) -> str:
        return f"BondOrderEdit({self.equation()})"


def bond_order_edits(
    reactant: Molecule, *, budget: int = 50_000
) -> tuple[tuple[BondOrderEdit, ...], bool]:
    """Enumerate the dehydrogenation bond-order edits of ``reactant`` (raise one bond, shed one H per endpoint).

    Deduplicated by the resulting PRECURSOR (symmetry-equivalent hydrogen choices collapse to one candidate, the
    same way two capped scissions with the same products are one), canonical order.  Returns ``(edits, complete)``;
    ``complete`` is ``False`` iff ``budget`` was hit.  Never raises on a molecule with no raisable bond -- it
    returns ``((), True)`` (exhausted, empty)."""
    if type(reactant) is not Molecule:
        raise TypeError("reactant must be a smartchem.category.Molecule")
    if reactant.charge != 0:
        return (), True
    out: dict[str, BondOrderEdit] = {}
    work = 0
    for b in sorted(reactant.bonds):
        if b.order >= _MAX_BOND_ORDER:
            continue
        h_is = _h_neighbors(reactant, b.i)
        h_js = _h_neighbors(reactant, b.j)
        for h_i in h_is:
            for h_j in h_js:
                if h_i == h_j:
                    continue
                work += 1
                if work > budget:
                    return tuple(sorted(out.values(), key=lambda e: e.digest)), False
                try:
                    edit = BondOrderEdit(BOND_ORDER_EDIT_SCHEMA, reactant, b.i, b.j, h_i, h_j)
                except ScissionError:
                    continue
                # dedup by the produced precursor: equivalent H choices on the same bond are one candidate.
                key = canonical_digest(tuple(canonical_digest(p) for p in edit.products))
                out.setdefault(key, edit)
    return tuple(sorted(out.values(), key=lambda e: e.digest)), True


@dataclass(frozen=True)
class BondOrderEditProvider(TransformProvider):
    """The bond-order-edit family as a typed provider (CHEM-ALG-01).  Consumes no reagent pool -- it ignores the
    reagents argument the boundary passes -- and enumerates dehydrogenation edits behind a stable typed identity."""

    provider_id: str = "bond-order-edit"
    provider_version: str = "v1"
    witness_kind: str = "BOND_ORDER_EDIT"

    @property
    def capability_manifest(self) -> tuple:
        return (
            ("family", "bond-order-edit"),
            ("mechanism", "partial bond-order edit (dehydrogenation), neutral, no reagent consumed"),
            ("witness_kind", self.witness_kind),
            ("projection_kind", "DECOMPOSITION_EDGE"),
            ("max_bond_order", _MAX_BOND_ORDER),
        )

    def enumerate_transforms(self, reactant, reagents, *, budget):
        return bond_order_edits(reactant, budget=budget)
