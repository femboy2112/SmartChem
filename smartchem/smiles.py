"""G1 -- the front door: a hand-rolled SMILES-subset parser to :class:`~smartchem.category.Molecule`.

Until this, every bond graph in the system was hand-entered (23 compounds). "Recompile *any*
chemical" failed at ingestion, not at the descent. This closes that: ``parse_smiles`` turns a SMILES
string into a real, canonicalised ``Molecule``, so the decomposition engine can be pointed at
anything a chemist can name -- no dependency, numpy-free-root-clean, ours to guard and verify.

Why hand-rolled, not RDKit
--------------------------
The ethos is load-bearing math on a self-certifying, dependency-light core. A heavy binary
cheminformatics stack bolted onto that would be the opposite bet. This parser is small, inspectable,
and every molecule it emits is checked (composition parsed == composition built) and canonicalised
(so a wrong bond graph cannot masquerade as a right one). Correctness is proven against the registry:
:mod:`tests.test_smiles` parses each of the 23 registered species and asserts the parsed graph is
**structurally identical** (canonical-equal) to the hand-entered one -- formula AND topology.

Scope (v1), stated as loud walls, never silent
----------------------------------------------
* **Organic-subset atoms** bare (``B C N O P S F Cl Br I``, plus ``H``) and **bracket atoms**
  ``[...]`` with explicit H count and charge (``[NH4+]``, ``[O-]``, ``[Fe+2]``). Bracket elements are
  validated against :data:`~smartchem.atoms.PT`.
* **Bonds** ``-`` ``=`` ``#`` (orders 1/2/3), aromatic (lowercase atoms or ``:``), branches ``( )``,
  ring closures (single digit and ``%nn``).
* **Aromatic Kekulisation** for carbon rings AND the common aromatic heteroatoms -- pyridine-type
  ``n``, pyrrole-type ``[nH]``, furan/thiophene-type ``o``/``s`` (pyridine, pyrrole, furan,
  thiophene, imidazole all parse): a perfect matching over the ring's pi-ACCEPTORS (carbon, and a
  bare/no-H nitrogen with fewer than three sigma bonds) assigns the alternating double bonds, while
  each pi-DONOR (``o``, ``s``, and an ``H``-bearing or already-3-bonded nitrogen) sits out the
  matching entirely and keeps every incident aromatic bond at order 1 -- its lone pair, not a ring
  double bond, is the aromatic contribution. Any OTHER aromatic heteroatom (``p`` and friends) is a
  documented v1 gap and is **refused loudly** -- give an explicit Kekulé SMILES.
* **Constitutional only (W3).** Stereo markers (``/``, backslash, ``@``) carry no cis/trans or R/S
  here -- they are parsed and ignored, exactly as :mod:`smartchem.decompiler_boundary` refuses to
  *claim* stereochemistry. A bond graph is constitution, not configuration.
* **Disconnected SMILES** (``.``) are refused: a ``Molecule`` is one connected species.

Aromatic identity is resonance-canonical (R2): a fused benzenoid such as naphthalene has several
non-isomorphic Kekulé structures, so picking one arbitrarily would give one molecule several
identities (and several decomposition menus). Instead the parser builds the canonical form of EVERY
Kekulé structure and returns the minimal one -- a canonical representative of the resonance orbit --
so any two Kekulé drawings of the same molecule collapse to ONE identity. This holds whether the ring
is drawn AROMATIC (lowercase / ``:``) or as an EXPLICIT Kekulé (uppercase atoms, ``=`` bonds): an
explicit drawing is resonance-canonicalised the same way, over every multiple-bond placement its fixed
sigma-skeleton and per-atom pi-demand allow (:func:`_min_constitution_placement`, CANON-KEKULE-01), so
a fused aromatic never fails to match its own aromatic spelling. A localised double bond is pi-demand-
pinned (1-butene's stays on C1=C2; a tautomer keeps its H-placement), so only genuine resonance
collapses. Symmetric rings (benzene, mono-/para-substituted) already had isomorphic Kekulé forms. The
remaining honest boundary is finer: this fixes the molecule's *identity*, not the aromatic bond model
-- a scission still cuts the specific single/double bonds of the chosen canonical form, so cutting an
aromatic ring bond is reported against that representative rather than a delocalised 1.5-order bond (a
stated resonance boundary, not a silent one). A giant PAH beyond the enumeration bound is refused.
"""

from __future__ import annotations

from dataclasses import dataclass

from .atoms import PT
from .category import Bond, Molecule
from .contracts import canonical_digest

__all__ = [
    "SmilesError",
    "SmilesFeatures",
    "parse_smiles",
    "parse_smiles_features",
    "isotope_refined_key",
]


class SmilesError(ValueError):
    """A SMILES string is malformed or uses a feature outside this parser's declared scope."""


@dataclass(frozen=True)
class SmilesFeatures:
    """The configuration/isotope/local-charge features a SMILES DECLARES that the constitution-only
    :class:`~smartchem.category.Molecule` cannot represent (ID-STEREO-01).

    :func:`parse_smiles` deliberately drops these (a bond graph is constitution, W3), so an enantiomer, an
    isotopologue and a net-neutral zwitterion collapse to the same ``Molecule`` as their flat analogue.  That
    collapse is correct AT the constitution layer, but it must never be SILENT (standard section 5.3): this record
    reports exactly which finer features were seen and dropped, so a caller can record the typed ``IdentityLoss``
    blockers (:func:`smartchem.identity.representation_losses_for`) rather than let the drop pass unremarked.
    """

    isotopes: tuple[int, ...]        # sorted, distinct isotope mass numbers that appeared (e.g. (2, 13))
    tetrahedral_stereo: bool         # any '@' / '@@' tetrahedral chirality marker
    double_bond_stereo: bool         # any '/' or '\\' double-bond configuration marker
    charged_atoms: int               # how many atoms bear a nonzero FORMAL charge (per-atom, pre-summing)
    net_charge: int                  # the molecular total charge (the only charge the Molecule keeps)
    isotopic_digest: "str | None" = None  # the canonical isotope-refined-constitution key (ID-STEREO-01 perception)

    @property
    def has_isotope(self) -> bool:
        return bool(self.isotopes)

    @property
    def has_stereo(self) -> bool:
        return self.tetrahedral_stereo or self.double_bond_stereo

    @property
    def has_local_charge_structure(self) -> bool:
        """True when per-atom formal charge is present but NOT recoverable from the scalar molecular total.

        Fires in two provable cases: (1) a net-NEUTRAL species that still bears formal charge on an atom -- the
        zwitterion/ylide (``[NH3+]CC(=O)[O-]``, net 0), where the single total-charge scalar the ``Molecule`` keeps
        is 0 and thus provably hides the internal ``+``/``-`` separation; (2) TWO OR MORE charged atoms regardless of
        the net, since one scalar cannot encode a multi-site distribution (which atom carries which charge).  A
        single charged atom whose charge IS the net (a simple monopole such as ``[OH-]``, ``[NH4+]``) is recoverable
        from the scalar and is NOT flagged.  Over-flagging here is fail-CLOSED (section 5.3): recording a blocker
        that turns out unnecessary is safe; missing a real charge separation is not.
        """
        return self.charged_atoms >= 1 and (self.net_charge == 0 or self.charged_atoms >= 2)


# organic-subset bare atoms (two-char symbols must be tried before one-char in the tokeniser)
_ORGANIC = {"Cl", "Br", "B", "C", "N", "O", "P", "S", "F", "I"}
_AROMATIC_BARE = {"c", "n", "o", "s", "p"}
# normal valences for implicit-H filling: smallest valence >= used bonds wins (OpenSMILES rule)
_VALENCES: dict[str, tuple[int, ...]] = {
    "B": (3,), "C": (4,), "N": (3, 5), "O": (2,), "P": (3, 5), "S": (2, 4, 6),
    "F": (1,), "Cl": (1,), "Br": (1,), "I": (1,), "H": (1,),
}
_BOND_ORDER = {"-": 1, "=": 2, "#": 3}
_AROMATIC = -1  # sentinel bond order for an as-yet-unkekulised aromatic bond


class _Atom:
    __slots__ = ("element", "aromatic", "charge", "h_explicit", "isotope", "chirality")

    def __init__(
        self,
        element: str,
        aromatic: bool,
        charge: int,
        h_explicit: int | None,
        isotope: int = 0,
        chirality: bool = False,
    ):
        self.element = element
        self.aromatic = aromatic
        self.charge = charge
        self.h_explicit = h_explicit          # None => fill implicitly; int => bracket, exact
        self.isotope = isotope                # 0 => unspecified; else the mass number (ID-STEREO-01 capture)
        self.chirality = chirality            # a tetrahedral '@'/'@@' marker was present (dropped from the graph)


def _parse_bracket(text: str, start: int) -> tuple[_Atom, int]:
    """Parse ``[...]`` starting at the ``[`` (index ``start``); return the atom and the index past ``]``."""
    end = text.find("]", start)
    if end == -1:
        raise SmilesError(f"unclosed bracket atom at position {start}")
    body = text[start + 1:end]
    i = 0
    iso = ""
    while i < len(body) and body[i].isdigit():      # isotope: CAPTURED (ID-STEREO-01), dropped from the graph
        iso += body[i]
        i += 1
    isotope = int(iso) if iso else 0
    if i >= len(body):
        raise SmilesError(f"bracket atom {text[start:end + 1]!r} has no element")
    aromatic = body[i].islower()
    # element symbol: a two-letter element (Upper+lower, e.g. 'Cl', 'Se') when the capitalised
    # pair is a real element, else a single letter. Aromatic atoms are written lowercase.
    if len(body) - i >= 2 and body[i + 1].islower() and body[i:i + 2].capitalize() in PT:
        element, i = body[i:i + 2].capitalize(), i + 2
    elif body[i].upper() in PT or body[i].upper() == "H":
        element, i = body[i].upper(), i + 1
    else:
        raise SmilesError(f"unknown element in bracket atom {text[start:end + 1]!r}")
    # chirality markers @ / @@: CAPTURED (ID-STEREO-01) but dropped from the graph (constitutional only, W3)
    chirality = False
    while i < len(body) and body[i] == "@":
        chirality = True
        i += 1
    h_count = 0
    if i < len(body) and body[i] == "H":
        i += 1
        num = ""
        while i < len(body) and body[i].isdigit():
            num += body[i]
            i += 1
        h_count = int(num) if num else 1
    charge = 0
    while i < len(body) and body[i] in "+-":
        sign = 1 if body[i] == "+" else -1
        i += 1
        num = ""
        while i < len(body) and body[i].isdigit():
            num += body[i]
            i += 1
        if num:
            charge += sign * int(num)
        else:
            charge += sign
            while i < len(body) and body[i] in "+-" and body[i] == ("+" if sign == 1 else "-"):
                charge += sign
                i += 1
    if i != len(body):
        raise SmilesError(f"could not parse bracket atom {text[start:end + 1]!r}")
    return _Atom(element, aromatic, charge, h_count, isotope, chirality), end + 1


def _parse_skeleton(
    text: str,
) -> tuple[list[_Atom], list[list[int]]]:
    """Walk the SMILES, building atoms and explicit bonds ``[i, j, order]`` (order ``_AROMATIC`` pending).

    Standard stack walk: a branch ``(`` saves the current attachment atom, ``)`` restores it; ring-
    closure digits pair a bond between their two occurrences.
    """
    atoms: list[_Atom] = []
    bonds: list[list[int]] = []
    prev: int | None = None
    pending: int | None = None           # explicit bond order awaiting the next atom/ring-closure
    branch_stack: list[int] = []
    ring_open: dict[str, tuple[int, int | None]] = {}   # label -> (atom, pending order)
    i, n = 0, len(text)

    def connect(a: int, b: int, order: int | None, both_aromatic: bool) -> None:
        if a == b:
            raise SmilesError("a bond connects an atom to itself")
        o = order if order is not None else (_AROMATIC if both_aromatic else 1)
        bonds.append([a, b, o])

    while i < n:
        ch = text[i]
        if ch == "(":
            if prev is None:
                raise SmilesError("branch '(' before any atom")
            branch_stack.append(prev)
            i += 1
        elif ch == ")":
            if not branch_stack:
                raise SmilesError("unbalanced ')'")
            prev = branch_stack.pop()
            i += 1
        elif ch in "-=#:/\\":
            pending = _AROMATIC if ch == ":" else _BOND_ORDER.get(ch, 1)
            i += 1
        elif ch == ".":
            raise SmilesError("disconnected SMILES ('.'): a Molecule is one connected species")
        elif ch.isdigit() or ch == "%":
            if prev is None:
                raise SmilesError("ring-closure digit before any atom")
            if ch == "%":
                label = text[i + 1:i + 3]
                i += 3
            else:
                label = ch
                i += 1
            if label in ring_open:
                other, oorder = ring_open.pop(label)
                order = pending if pending is not None else oorder
                connect(other, prev, order, atoms[other].aromatic and atoms[prev].aromatic)
            else:
                ring_open[label] = (prev, pending)
            pending = None
        else:
            if ch == "[":
                atom, i = _parse_bracket(text, i)
            else:
                two = text[i:i + 2]
                if two in _ORGANIC and two in ("Cl", "Br"):
                    element, aromatic, i = two, False, i + 2
                elif ch.upper() in {s for s in _ORGANIC if len(s) == 1} or ch in _AROMATIC_BARE:
                    if ch in _AROMATIC_BARE:
                        element, aromatic = ch.upper(), True
                    elif ch in _ORGANIC:
                        element, aromatic = ch, False
                    else:
                        raise SmilesError(f"unexpected character {ch!r} at position {i}")
                    i += 1
                else:
                    raise SmilesError(f"unexpected character {ch!r} at position {i}")
                atom = _Atom(element, aromatic, 0, None)
            idx = len(atoms)
            atoms.append(atom)
            if prev is not None:
                connect(prev, idx, pending, atoms[prev].aromatic and atom.aromatic)
            pending = None
            prev = idx

    if branch_stack:
        raise SmilesError("unbalanced '(' -- a branch was not closed")
    if ring_open:
        raise SmilesError(f"unclosed ring bond(s): {sorted(ring_open)}")
    if not atoms:
        raise SmilesError("empty SMILES")
    return atoms, bonds


# R2: bound the resonance enumeration. A benzenoid's Kekulé count is small (benzene 2, naphthalene 3,
# anthracene 4, phenanthrene 5, pyrene 6, coronene 20); only a pathological giant PAH exceeds these,
# and it is refused loudly rather than given a Kekulé-arbitrary identity.
_MAX_AROMATIC_CARBONS = 30
_MAX_KEKULE_MATCHINGS = 5000


def _aromatic_matchings(
    atoms: list[_Atom], bonds: list[list[int]]
) -> tuple[list[int], list[frozenset[int]]]:
    """The aromatic bond indices and EVERY perfect matching over the aromatic ring's pi-acceptors.

    Each matching is the set of aromatic bond indices assigned a *double* bond (one Kekulé structure);
    the rest become single. Not every aromatic atom takes a double bond, though: a heteroatom can be a
    pi-DONOR instead (its lone pair, not a ring double bond, supplies the aromatic electron), so the
    matching runs over the pi-ACCEPTOR subset only --

    * **acceptor** (needs exactly one ring double bond, same as an aromatic carbon): element ``C``; or
      a bare/no-H aromatic ``N`` with fewer than three sigma bonds (the pyridine-type nitrogen).
    * **donor** (sits out the matching; every incident aromatic bond defaults to order 1): element
      ``O`` or ``S``; or an aromatic ``N`` carrying an explicit H, OR one already at three sigma bonds
      -- a substituted or bridgehead pyrrole-type nitrogen ([nH], N-substituted pyrrole, indolizine).

    Returns ``([], [])`` when there is no aromatic bond. Refuses any OTHER aromatic heteroatom (a v1
    gap, e.g. aromatic P) and an aromatic system with no perfect matching -- loudly, never a silent
    wrong order.

    Enumerating EVERY matching (not just the first) is what lets :func:`parse_smiles` pick a
    resonance-CANONICAL representative (R2): a fused benzenoid such as naphthalene has several
    non-isomorphic Kekulé structures, and taking the canonical-minimal one collapses them to a single
    identity, so two Kekulé drawings of one molecule no longer decompose to two different menus.
    """
    arom_bonds = [k for k, (_i, _j, o) in enumerate(bonds) if o == _AROMATIC]
    if not arom_bonds:
        return [], []
    arom_atoms = sorted({e for bi in arom_bonds for e in bonds[bi][:2]})

    # Full sigma-bond degree (EVERY bond, not just the aromatic ring ones) is what tells a bare,
    # H-less aromatic N apart: 2 connections and it's pyridine-type (an acceptor); 3 and every seat is
    # already taken, so it's donor-type (a substituted pyrrole N or a bridgehead like indolizine).
    degree: dict[int, int] = {}
    for a, b, _o in bonds:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1

    acceptors: list[int] = []
    for a in arom_atoms:
        element = atoms[a].element
        if element == "C":
            acceptors.append(a)
        elif element == "N":
            h = atoms[a].h_explicit
            if h or degree.get(a, 0) >= 3:
                pass                            # [nH], or no H but already 3 sigma bonds -- a donor
            else:                               # bare, 2-connection N: pyridine-type, takes one double
                acceptors.append(a)
        elif element in ("O", "S"):
            pass                                # a lone-pair donor, never a matching vertex
        else:
            raise SmilesError(
                f"aromatic heteroatom {element!r} is a v1 gap; "
                "give an explicit Kekulé SMILES (e.g. uppercase atoms with '=' bonds)"
            )
    if len(arom_atoms) > _MAX_AROMATIC_CARBONS:
        raise SmilesError(
            f"aromatic system has {len(arom_atoms)} atoms (> {_MAX_AROMATIC_CARBONS}); a "
            "resonance-canonical identity for a ring this large is out of scope (give a Kekulé SMILES)"
        )
    acceptor_set = set(acceptors)
    neighbours: dict[int, list[tuple[int, int]]] = {a: [] for a in acceptors}
    for bi in arom_bonds:
        a, b, _o = bonds[bi]
        if a in acceptor_set and b in acceptor_set:    # a donor-incident bond is never a matching edge
            neighbours[a].append((b, bi))               # -- it stays order 1 by default below, its
            neighbours[b].append((a, bi))                # lone pair never masquerading as a double bond
    matchings: list[frozenset[int]] = []

    def enumerate_from(matched: frozenset[int], chosen: frozenset[int]) -> None:
        if len(matchings) > _MAX_KEKULE_MATCHINGS:
            return
        a = next((x for x in acceptors if x not in matched), None)
        if a is None:                                  # every pi-acceptor paired: a full matching
            matchings.append(chosen)
            return
        for b, bi in neighbours[a]:                    # pair the smallest unmatched atom each step:
            if b not in matched:                       # enumerates every perfect matching exactly once
                enumerate_from(matched | {a, b}, chosen | {bi})

    enumerate_from(frozenset(), frozenset())
    if not matchings:
        raise SmilesError("could not assign a Kekulé structure to the aromatic system")
    if len(matchings) > _MAX_KEKULE_MATCHINGS:
        raise SmilesError(
            f"aromatic system has more than {_MAX_KEKULE_MATCHINGS} Kekulé structures; a "
            "resonance-canonical identity for it is out of scope (give an explicit Kekulé SMILES)"
        )
    return arom_bonds, matchings


def _fill_hydrogens(atoms: list[_Atom], bonds: list[list[int]]) -> tuple[list[str], list[Bond]]:
    """Add implicit hydrogens and materialise the final atom list + Bond set.

    Bracket atoms carry an exact H count; organic-subset atoms fill to the smallest normal valence
    at least as large as their used bond order (the OpenSMILES rule). Charge lives on bracket atoms,
    where H is explicit, so it never interacts with implicit-H filling.
    """
    used = [0] * len(atoms)
    for a, b, o in bonds:
        used[a] += o
        used[b] += o
    out_atoms = [atom.element for atom in atoms]
    out_bonds = [Bond(a, b, o) for a, b, o in bonds]
    for k, atom in enumerate(atoms):
        if atom.h_explicit is not None:
            h_count = atom.h_explicit
        else:
            valset = _VALENCES.get(atom.element)
            if valset is None:
                raise SmilesError(
                    f"{atom.element!r} is not an organic-subset atom; write it in brackets "
                    "with an explicit H count, e.g. [Se H2]"
                )
            target = next((v for v in valset if v >= used[k]), None)
            if target is None:
                raise SmilesError(
                    f"atom {atom.element!r} has bond order {used[k]} exceeding its normal valence "
                    f"{valset}; state hydrogens explicitly in brackets"
                )
            h_count = target - used[k]
        for _ in range(h_count):
            hi = len(out_atoms)
            out_atoms.append("H")
            out_bonds.append(Bond(k, hi, 1))
    return out_atoms, out_bonds


def _min_constitution_placement(
    atoms: list[_Atom], bonds: list[list[int]], charge: int
) -> tuple[int, ...]:
    """The bond-order assignment that minimises the constitution digest over EVERY multiple-bond placement
    consistent with the fixed sigma-skeleton and per-atom pi-demand -- resonance-canonical for an EXPLICIT
    (unflagged) structure (CANON-KEKULE-01).

    The current aromatic path (:func:`_aromatic_matchings`) resonance-canonicalises only bonds the INPUT flagged
    aromatic (lowercase / ``:``); an explicit-Kekulé drawing (uppercase atoms, ``=`` bonds) carries no flags, so a
    fused aromatic written that way kept its authored double bonds and a molecule could fail to match its OWN
    aromatic spelling.  This closes it WITHOUT aromaticity perception: each atom's pi-demand ``need[a] =
    sum(order-1)`` is fixed by the drawn structure (so the input's H-counts pin a LOCALISED double -- 1-butene's
    is forced onto C1=C2, and a tautomer keeps its distinct H-placement), and every placement satisfying that
    demand exactly is a resonance form of the SAME constitutional molecule.  Minimising the constitution digest
    over them is the canonical representative -- the exact R2 move, generalised from aromatic-flagged bonds to the
    pi-system.  A molecule with a UNIQUE placement (every localised/pinned double, i.e. most molecules) returns its
    drawn orders unchanged, so this is byte-identical for everything except a genuinely resonance-degenerate
    unflagged system.  Refuses (never truncates to a non-deterministic minimum) if the placements exceed the bound.
    """
    n = len(atoms)
    need = [0] * n
    for a, b, o in bonds:
        need[a] += o - 1
        need[b] += o - 1
    incident: list[list[int]] = [[] for _ in range(n)]
    for bi, (a, b, _o) in enumerate(bonds):
        incident[a].append(bi)
        incident[b].append(bi)
    remaining = need[:]
    extra = [0] * len(bonds)
    best: list = [None, None]  # [orders_tuple, digest_key]
    count = [0]

    def _other(bi: int, a: int) -> int:
        x, y, _o = bonds[bi]
        return y if x == a else x

    def _consider() -> None:
        count[0] += 1
        if count[0] > _MAX_KEKULE_MATCHINGS:
            raise SmilesError(
                f"structure has more than {_MAX_KEKULE_MATCHINGS} resonance placements; a resonance-canonical "
                "identity for it is out of scope (give an aromatic-lowercase SMILES for the aromatic ring)"
            )
        for k in range(len(bonds)):
            bonds[k][2] = 1 + extra[k]
        out_atoms, out_bonds = _fill_hydrogens(atoms, bonds)
        key = canonical_digest(Molecule(tuple(out_atoms), frozenset(out_bonds), charge).canonical())
        if best[1] is None or key < best[1]:
            best[0], best[1] = tuple(1 + e for e in extra), key

    def _rec(a: int) -> None:
        while a < n and remaining[a] == 0:
            a += 1
        if a == n:
            _consider()
            return
        forward = [bi for bi in incident[a] if _other(bi, a) > a]  # bonds to not-yet-fixed atoms

        def _dist(idx: int, left: int) -> None:
            if left == 0:
                _rec(a + 1)
                return
            if idx >= len(forward):
                return  # atom a's demand cannot be met from here -- a dead branch, not a placement
            bi = forward[idx]
            b = _other(bi, a)
            cap = min(left, remaining[b], 2 - extra[bi])  # a bond order never exceeds 3 (extra <= 2)
            for add in range(cap, -1, -1):
                extra[bi] += add
                remaining[a] -= add
                remaining[b] -= add
                _dist(idx + 1, left - add)
                extra[bi] -= add
                remaining[a] += add
                remaining[b] += add

        _dist(0, remaining[a])

    _rec(0)
    if best[0] is None:  # pragma: no cover -- the drawn structure is always a valid placement
        raise SmilesError("could not assign a valid multiple-bond placement to the structure")
    return best[0]


def _build_molecule(atoms: list[_Atom], bonds: list[list[int]], charge: int) -> Molecule:
    """Kekulise (resonance-canonical, R2) and materialise the canonical constitution-only Molecule.

    Shared by :func:`parse_smiles` and :func:`parse_smiles_features` so the ONE Kekulé/canonicalisation path
    cannot drift between the plain door and the feature-capturing one.
    """
    arom_bonds, matchings = _aromatic_matchings(atoms, bonds)

    if not matchings:                                  # no aromatic-FLAGGED system: resonance-canonicalise the
        orders = _min_constitution_placement(atoms, bonds, charge)  # pi placement so an explicit-Kekulé fused
        for k in range(len(bonds)):                    # aromatic collapses to its aromatic spelling (CANON-KEKULE-01)
            bonds[k][2] = orders[k]
        out_atoms, out_bonds = _fill_hydrogens(atoms, bonds)
        return Molecule(tuple(out_atoms), frozenset(out_bonds), charge).canonical()

    # R2 -- resonance-canonical: build the canonical form of EVERY Kekulé structure and return the
    # minimal one, so any two Kekulé drawings of the same molecule collapse to a single identity (and
    # thus a single decomposition menu). For a symmetric ring (benzene, mono/para-substituted) all
    # Kekulé forms are already isomorphic, so this returns the same identity as before; for a fused
    # benzenoid (naphthalene, anthracene, phenanthrene) it removes the former Kekulé-choice ambiguity.
    best: Molecule | None = None
    best_key: str | None = None
    for doubles in matchings:
        for k in arom_bonds:
            bonds[k][2] = 2 if k in doubles else 1
        out_atoms, out_bonds = _fill_hydrogens(atoms, bonds)
        cand = Molecule(tuple(out_atoms), frozenset(out_bonds), charge).canonical()
        key = canonical_digest(cand)
        if best_key is None or key < best_key:
            best, best_key = cand, key
    assert best is not None                            # matchings is non-empty here
    return best


def _isotopic_identity(atoms: list[_Atom], bonds: list[list[int]], charge: int) -> str:
    """The canonical ISOTOPE-REFINED-CONSTITUTION key: constitution + per-atom isotope labels (ID-STEREO-01).

    Sound stereo/isotope PERCEPTION is the piece the detection arm (``isotope_loss`` etc.) deferred.  This builds
    the isotope half of it, and it does so WITHOUT a bespoke canonicaliser or an atom-coloured ``Molecule``: it runs
    the SAME proven graph canonicaliser the constitution digest uses (:func:`category._canonical_by_individualisation`,
    with its false-twin pruning and pinned relabel-invariance) over an ISOTOPE-COLOURED copy of the graph, so a
    labelled atom seeds a distinct colour class and the canonical form distinguishes isotopologues by PLACEMENT while
    staying invariant under presentation.  Aromatic inputs are handled resonance-canonically (the minimum key over
    every Kekule matching), exactly like :func:`_build_molecule`, so two Kekule drawings of one isotopologue collapse.

    Soundness the tests pin: (1) relabel-invariance -- two SMILES spellings of one isotopologue share the key;
    (2) symmetric-position invariance -- a label on either of two symmetric sites gives ONE key (the canonicaliser
    minimises over the symmetry); (3) positional distinction -- a label at a different site gives a different key;
    (4) it REFINES constitution -- equal key implies equal constitution (stripping the colour prefix leaves the
    identical graph).  BOUNDARY (never faked): this is the isotope refinement of CONSTITUTION, MODULO stereochemistry
    -- it does NOT encode chirality/cis-trans, so two enantiomeric isotopologues share it.  It is therefore NOT the
    MatchLayer ISOTOPIC slot (the lattice puts ISOTOPIC above CONFIGURATION, so that slot additionally needs sound
    stereo perception -- a canonical CIP parity, which graph canonicalisation cannot supply because chirality is a
    reflection); that, and CONFIGURATION, stay the named ID-STEREO-01 deferral.
    """
    from .category import _canonical_by_individualisation

    work = [list(b) for b in bonds]                       # a private copy: never disturb the caller's pending bonds
    arom_bonds, matchings = _aromatic_matchings(atoms, work)

    def colored_key() -> str:
        out_atoms, out_bonds = _fill_hydrogens(atoms, work)
        # colour ONLY the atoms that carried an isotope (k < len(atoms); implicit H are appended after and unlabelled).
        # 'iso:El' can never collide with a bare element symbol, so the colouring is injective over the symbol set.
        colored = tuple(
            f"{atoms[k].isotope}:{out_atoms[k]}" if k < len(atoms) and atoms[k].isotope else out_atoms[k]
            for k in range(len(out_atoms))
        )
        symbols, edges = _canonical_by_individualisation(colored, frozenset(out_bonds))
        return canonical_digest((symbols, edges, charge))

    if not matchings:
        # no aromatic-FLAGGED system: commit to the SAME constitution-minimal pi placement _build_molecule commits
        # to (CANON-KEKULE-01), so the isotope key can never split an explicit-Kekulé fused aromatic from its
        # aromatic spelling -- the isotopic key MUST refine constitution.
        orders = _min_constitution_placement(atoms, work, charge)
        for k in range(len(work)):
            work[k][2] = orders[k]
        return colored_key()
    # Resonance-canonical: commit to the EXACT Kekule structure :func:`_build_molecule` commits to -- the matching
    # that minimises the CONSTITUTION digest ``canonical_digest(Molecule.canonical())``, NOT the coloured key.  This
    # alignment is load-bearing for soundness: whenever the constitution unifies two spellings (an aromatic spelling
    # and an explicit-Kekule spelling of one fused benzenoid), this key MUST unify them too.  Minimising the coloured
    # key instead could pick a different Kekule than the constitution and split ONE species into two identities
    # (red-team ID-STEREO-01-SPLIT-KEKULE: naphthalene aromatic vs explicit-Kekule).  Every matching that ties on the
    # constitution digest is the SAME canonical molecule, so it yields the SAME coloured key -- the tie-break is moot.
    best_matching = matchings[0]
    best_constitution: str | None = None
    for doubles in matchings:
        for k in arom_bonds:
            work[k][2] = 2 if k in doubles else 1
        out_atoms, out_bonds = _fill_hydrogens(atoms, work)
        constitution = canonical_digest(Molecule(tuple(out_atoms), frozenset(out_bonds), charge).canonical())
        if best_constitution is None or constitution < best_constitution:
            best_constitution, best_matching = constitution, doubles
    for k in arom_bonds:
        work[k][2] = 2 if k in best_matching else 1
    return colored_key()


def isotope_refined_key(text: str) -> str:
    """The canonical isotope-refined-constitution key of ``text`` (ID-STEREO-01), a string for ANY input.

    For an unlabelled molecule this is a constitution-equivalent key (two same-constitution spellings share it); a
    label makes it finer.  Use it to tell isotopologues apart soundly: ``isotope_refined_key(a) == isotope_refined_
    key(b)`` iff ``a`` and ``b`` are the same species AT THE ISOTOPE-REFINED-CONSTITUTION level (modulo stereo, see
    :func:`_isotopic_identity`).  Raises :class:`SmilesError` on a malformed/out-of-scope SMILES, like the parser.
    """
    if not isinstance(text, str):
        raise SmilesError("SMILES input must be a string")
    stripped = text.strip()
    if not stripped:
        raise SmilesError("empty SMILES")
    atoms, bonds = _parse_skeleton(stripped)
    charge = sum(a.charge for a in atoms)
    return _isotopic_identity(atoms, bonds, charge)


def parse_smiles(text: str) -> Molecule:
    """Parse a SMILES string into a canonical :class:`~smartchem.category.Molecule`.

    Raises :class:`SmilesError` for a malformed string or an out-of-scope feature (an aromatic
    heteroatom outside {C, N, O, S}, a disconnected ``.``), never returning a wrong graph silently.
    The returned molecule is canonicalised, so two spellings of the same structure compare equal.
    """
    if not isinstance(text, str):
        raise SmilesError("SMILES input must be a string")
    stripped = text.strip()
    if not stripped:
        raise SmilesError("empty SMILES")
    atoms, bonds = _parse_skeleton(stripped)
    charge = sum(a.charge for a in atoms)
    return _build_molecule(atoms, bonds, charge)


def parse_smiles_features(text: str) -> tuple[Molecule, SmilesFeatures]:
    """Parse a SMILES and ALSO report the finer-layer features it declares that the graph cannot keep.

    Identical Molecule to :func:`parse_smiles` (same tokeniser, same Kekulé canonicalisation), plus a
    :class:`SmilesFeatures` naming the isotope labels, tetrahedral/double-bond stereochemistry and net-neutral
    local-charge separation that were parsed and dropped (ID-STEREO-01).  Isotope/chirality/charge are captured per
    atom during the parse.

    ``double_bond_stereo`` is a CONSERVATIVE presence scan: ``'/'``/``'\\'`` appear ONLY as bond-configuration
    tokens in SMILES, so the scan never MISSES a declared marker -- but it does not perceive whether a real
    geometric isomer exists, so a chemically-redundant directional bond (an alkene end bearing two identical
    substituents) is OVER-flagged.  That errs toward recording a stereo blocker (fail-CLOSED, section 5.3) rather
    than dropping a real one; precise perception of whether a stereoisomer actually exists is deferred with the rest
    of stereochemistry perception (never faked here).
    """
    if not isinstance(text, str):
        raise SmilesError("SMILES input must be a string")
    stripped = text.strip()
    if not stripped:
        raise SmilesError("empty SMILES")
    atoms, bonds = _parse_skeleton(stripped)
    charge = sum(a.charge for a in atoms)
    # The isotope-refined key must see the PRISTINE aromatic bonds (_build_molecule mutates them during Kekulisation),
    # so compute it FIRST -- it takes a private copy of `bonds` and leaves the caller's list untouched.
    isotopic_digest = _isotopic_identity(atoms, bonds, charge) if any(a.isotope for a in atoms) else None
    molecule = _build_molecule(atoms, bonds, charge)
    features = SmilesFeatures(
        isotopes=tuple(sorted({a.isotope for a in atoms if a.isotope})),
        tetrahedral_stereo=any(a.chirality for a in atoms),
        double_bond_stereo=("/" in stripped or "\\" in stripped),
        charged_atoms=sum(1 for a in atoms if a.charge != 0),
        net_charge=charge,
        isotopic_digest=isotopic_digest,
    )
    return molecule, features
