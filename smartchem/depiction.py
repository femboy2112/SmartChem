"""DEPICTION-01: optional 2D structure depiction via RDKit -- a DEV/EXTRA backend, never required.

A SmartChem :class:`~smartchem.category.Molecule` is a pure atom/bond graph and the engine has NO
SMILES writer, so a diagram cannot draw a *constitution* without a depiction backend.  This module
bridges a Molecule straight to an RDKit ``RWMol`` -- built from its ``atoms`` and ``bonds``, NOT from
a SMILES round-trip -- and renders a 2D skeletal-formula SVG.

RDKit is OPTIONAL and dev-only: the committed baseline uninstalls it exactly like every other
rdkit-oracle test, and then :func:`depict_svg` returns ``None`` and every caller degrades to a text /
formula label.  A drawing asserts NO chemistry the engine did not already hold -- it is a picture of
the same graph, nothing more.  Anything that will not sanitize as a closed-shell valence structure
(a radical scission fragment, an unplaced formal charge) returns ``None`` rather than a wrong picture.
"""
from __future__ import annotations

_BACKEND: object | None = None
_TRIED = False


def _backend():
    """Return ``(Chem, rdMolDraw2D, rdDepictor, BondType)`` or ``None`` if RDKit is absent."""
    global _BACKEND, _TRIED
    if not _TRIED:
        _TRIED = True
        try:
            from rdkit import Chem
            from rdkit.Chem import rdDepictor
            from rdkit.Chem.Draw import rdMolDraw2D
            from rdkit.Chem.rdchem import BondType
            _BACKEND = (Chem, rdMolDraw2D, rdDepictor, BondType)
        except Exception:
            _BACKEND = None
    return _BACKEND


def depiction_available() -> bool:
    """True iff the optional RDKit depiction backend is importable in this environment."""
    return _backend() is not None


def molecule_to_rdkit(molecule):
    """Build a SANITIZED RDKit ``Mol`` from a Molecule's atoms+bonds, or ``None``.

    Uses the engine's own graph (element symbols + ``Bond(i, j, order)``); no SMILES is involved.
    Returns ``None`` when RDKit is absent, a bond order is out of the single/double/triple range, or
    the result will not sanitize as a valence-legal structure (so a radical/odd-valence fragment
    degrades to a label instead of a misleading drawing).
    """
    backend = _backend()
    if backend is None:
        return None
    Chem, _draw, _dep, BondType = backend
    order_map = {1: BondType.SINGLE, 2: BondType.DOUBLE, 3: BondType.TRIPLE}
    rw = Chem.RWMol()
    index: list[int] = []
    for symbol in molecule.atoms:
        index.append(rw.AddAtom(Chem.Atom(symbol)))
    for bond in molecule.bonds:
        bond_type = order_map.get(bond.order)
        if bond_type is None:
            return None
        rw.AddBond(index[bond.i], index[bond.j], bond_type)
    mol = rw.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        return None
    return mol


def depict_svg(molecule, *, width: int = 240, height: int = 180) -> str | None:
    """Render ``molecule`` as a 2D skeletal SVG fragment, or ``None`` when it cannot be drawn.

    The returned string is a standalone ``<svg>...</svg>`` (RDKit's own output, XML prolog stripped
    so it inlines in HTML).  ``None`` means "no structure picture available" -- the caller shows the
    chemist label / formula instead.  Explicit hydrogens are collapsed to the usual implicit-H
    skeletal depiction.
    """
    backend = _backend()
    if backend is None:
        return None
    Chem, rdMolDraw2D, rdDepictor, _bt = backend
    mol = molecule_to_rdkit(molecule)
    if mol is None:
        return None
    try:
        mol = Chem.RemoveHs(mol)
        rdDepictor.Compute2DCoords(mol)
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        options = drawer.drawOptions()
        options.padding = 0.08
        options.clearBackground = False
        rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
    except Exception:
        return None
    # Strip an XML declaration / doctype prolog so the <svg> inlines cleanly inside HTML.
    marker = svg.find("<svg")
    return svg[marker:] if marker != -1 else svg


def depict_reaction_svg(reactants, products, *, agents=(), width: int = 900,
                        height: int = 260) -> str | None:
    """Render a single ``reactants (+ agents) -> products`` reaction SCHEME as one SVG, or ``None``.

    A standalone static picture of ONE step -- the "A + B --> C" a chemist draws -- built from the
    engine's own Molecule graphs (no SMILES).  ``None`` when RDKit is absent or any species will not
    sanitise.  Like :func:`depict_svg` this draws only what the engine already holds; it asserts no
    reaction conditions, direction of favourability, or feasibility.
    """
    backend = _backend()
    if backend is None:
        return None
    Chem, rdMolDraw2D, rdDepictor, _bt = backend
    from rdkit.Chem import rdChemReactions

    def prepared(mol):
        rk = molecule_to_rdkit(mol)
        if rk is None:
            return None
        return Chem.RemoveHs(rk)

    reaction = rdChemReactions.ChemicalReaction()
    for group, add in ((reactants, reaction.AddReactantTemplate),
                       (agents, reaction.AddAgentTemplate),
                       (products, reaction.AddProductTemplate)):
        for mol in group:
            prep = prepared(mol)
            if prep is None:
                return None
            add(prep)
    try:
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        drawer.DrawReaction(reaction)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
    except Exception:
        return None
    marker = svg.find("<svg")
    return svg[marker:] if marker != -1 else svg
