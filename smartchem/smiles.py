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
from fractions import Fraction
from functools import cmp_to_key, lru_cache

from .atoms import PT
from .category import Bond, Molecule, _wl_colours
from .contracts import canonical_digest
from .data.periodic_table import ATOMIC_NUMBER, has_standard_atomic_weight, standard_atomic_weight

__all__ = [
    "SmilesError",
    "SmilesFeatures",
    "parse_smiles",
    "parse_smiles_features",
    "isotope_refined_key",
    "configuration_key",
    "cip_labels",
    "resonance_canonical",
    "resonance_identity",
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
    configuration_digest: "str | None" = None  # canonical chirality-parity-refined key, or None if no perceivable stereocentre (ID-STEREO-01)
    configuration_complete: bool = False  # ID-STEREO-02: True iff the molecule's configuration is FULLY perceived (no
    # marked centre scoped out AND no double-bond stereo) -- the fail-closed signal that CONFIGURATION reduces soundly
    # to a match layer; when False some real stereo is unperceived, so CONFIGURATION stays UNKNOWN (never a false merge)
    cip_labels: tuple[str, ...] = ()  # the sorted CIP R/S names of the SOUNDLY-nameable stereocentres via the general
    # Rule-1a breadth-first digraph (ROUND 20 -- see :func:`cip_labels`); () when none are nameable (achiral, or every
    # marked centre is a Rule-1b/2/4/5-tie / ring / non-4-coordinate deferral).  PERCEPTION ONLY: the constitution
    # Molecule is achiral, so this is never a search-identity term -- it exists so a dossier can SHOW the R/S to a chemist.
    stereocentres_marked: int = 0  # how many tetrahedral centres the SMILES marked (@/@@).  The DENOMINATOR the dossier
    # discloses against: len(cip_labels) of these are soundly named, the rest are named DEFERRALS -- so a target with a
    # nameable centre AND a deferred one never hides the deferred count behind the named one (STEREO-DOSSIER-01 fold).

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
        chirality: int = 0,
    ):
        self.element = element
        self.aromatic = aromatic
        self.charge = charge
        self.h_explicit = h_explicit          # None => fill implicitly; int => bracket, exact
        self.isotope = isotope                # 0 => unspecified; else the mass number (ID-STEREO-01 capture)
        self.chirality = chirality            # tetrahedral SENSE: 0 none, 1 '@' (anticlockwise), 2 '@@' (clockwise)


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
    # chirality markers @ / @@: CAPTURED LOSSLESSLY as the tetrahedral SENSE (ID-STEREO-01): 0 = none, 1 = '@'
    # (TH1, anticlockwise from the first neighbour), 2 = '@@' (TH2, clockwise).  ROUND-12 widened this from a bare
    # boolean -- the sense is what a chirality PARITY descriptor needs; it is still dropped from the constitution
    # GRAPH (W3), but no longer discarded (the recon's "one-field-behind" hazard: the CIP path must read THIS, not a
    # boolean).  ``tetrahedral_stereo`` (a bool) stays derivable as ``bool(chirality)``.
    chirality = 0
    while i < len(body) and body[i] == "@":
        chirality += 1
        i += 1
    if chirality > 2:
        raise SmilesError(f"bracket atom {text[start:end + 1]!r} has more than two '@' chirality marks")
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

# CANON-KEKULE-01 identity path (resonance_canonical): ``_ident`` is the search HOT PATH, and each Kekulé placement
# costs a full canonicalization, so a highly-conjugated fragment could grind (a submittable 122-atom oligophenylene
# enumerated ~4000 placements ~= 18 s -- the evil-morty DoS fold).  Two O(1) guards keep ``_ident`` bounded: skip
# resonance for a molecule over ``_RESONANCE_MAX_HEAVY`` heavy atoms, and cap the placement enumeration at
# ``_RESONANCE_MAX_MATCHINGS``.  Above either, the fragment falls back to the plain literal-bond-order identity (no
# worse than pre-fix -- it just won't unify across Kekulé spellings, a non-issue for a system this large under the
# current bounded targets).  Real drug-like targets (a handful of small aromatic rings, a few dozen placements) are
# comfortably under both.  These are DISTINCT from the parser's 5000 cap, which stays unchanged.  ROUND-14 measured an
# ACTUAL-work meter as the named next-step to lifting these (tests/test_resonance_actual_work.py): it is a sound TIME
# bound (fixes ROUND-13's nominal-cost over-charge) but NOT a malice filter -- a LEGIT PAH out-costs a crafted grind,
# so no work budget separates them, and the caps stay a size proxy for a limit no real (<=24-heavy) target approaches.
_RESONANCE_MAX_HEAVY = 64
_RESONANCE_MAX_MATCHINGS = 128


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
    atoms: list[_Atom], bonds: list[list[int]], charge: int, max_matchings: int = _MAX_KEKULE_MATCHINGS
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
        if count[0] > max_matchings:
            raise SmilesError(
                f"structure has more than {max_matchings} resonance placements; a resonance-canonical "
                "identity for it is out of scope (give an aromatic-lowercase SMILES for the aromatic ring)"
            )
        for k in range(len(bonds)):
            bonds[k][2] = 1 + extra[k]
        out_atoms, out_bonds = _fill_hydrogens(atoms, bonds)
        key = canonical_digest(Molecule(tuple(out_atoms), frozenset(out_bonds), charge).canonical())
        if best[1] is None or key < best[1]:
            best[0], best[1] = tuple(1 + e for e in extra), key

    def _atom_distributions(a: int) -> list[list[tuple[int, int]]]:
        """Every way to meet ``remaining[a]`` over a's forward bonds, as lists of ``(bond, extra_order)`` with
        extra_order > 0.  Recurses only over a's OWN bonds (a handful), never over the molecule -- so this stays
        shallow whatever the molecule's size (the atom-walk below is iterative, not recursive)."""
        forward = [bi for bi in incident[a] if _other(bi, a) > a]  # bonds to not-yet-fixed atoms
        out: list[list[tuple[int, int]]] = []

        def _go(idx: int, left: int, acc: list[tuple[int, int]]) -> None:
            if left == 0:
                out.append(list(acc))
                return
            if idx >= len(forward):
                return  # a's demand cannot be met from here -- a dead branch, not a placement
            bi = forward[idx]
            b = _other(bi, a)
            cap = min(left, remaining[b], 2 - extra[bi])  # a bond order never exceeds 3 (extra <= 2)
            for add in range(cap, -1, -1):
                if add:
                    acc.append((bi, add))
                _go(idx + 1, left - add, acc)
                if add:
                    acc.pop()

        _go(0, remaining[a], [])
        return out

    def _next_pi(a: int) -> int:
        while a < n and remaining[a] == 0:
            a += 1
        return a

    def _apply(a: int, dist: list[tuple[int, int]], sign: int) -> None:
        for bi, add in dist:
            extra[bi] += sign * add
            remaining[a] -= sign * add
            remaining[_other(bi, a)] -= sign * add

    # Iterative DFS over the pi-atoms (an explicit list stack, so a large pinned/conjugated system -- which the
    # atom-walk descends one frame per pi-atom -- never blows the Python recursion limit; the earlier recursive
    # walk crashed with an uncaught RecursionError on a ~330-atom cumulene, the red-team fold).
    start = _next_pi(0)
    if start == n:
        _consider()  # no multiple bond at all: the single all-single placement (a saturated molecule)
    else:
        stack: list[dict] = [{"atom": start, "dists": _atom_distributions(start), "idx": -1, "applied": None}]
        while stack:
            top = stack[-1]
            if top["applied"] is not None:                 # backtrack: undo the distribution we had applied
                _apply(top["atom"], top["applied"], -1)
                top["applied"] = None
            top["idx"] += 1
            if top["idx"] >= len(top["dists"]):
                stack.pop()
                continue
            dist = top["dists"][top["idx"]]
            _apply(top["atom"], dist, +1)
            top["applied"] = dist
            nxt = _next_pi(top["atom"] + 1)
            if nxt == n:
                _consider()                                # a complete placement (every pi-demand met)
            else:
                stack.append({"atom": nxt, "dists": _atom_distributions(nxt), "idx": -1, "applied": None})

    if best[0] is None:  # pragma: no cover -- the drawn structure is always a valid placement
        raise SmilesError("could not assign a valid multiple-bond placement to the structure")
    return best[0]


@lru_cache(maxsize=8192)
def resonance_canonical(molecule: Molecule) -> Molecule:
    """The resonance-canonical representative of ``molecule`` (CANON-KEKULE-01, generalised off the SMILES parser).

    ``parse_smiles`` already resonance-canonicalises everything it parses (via :func:`_min_constitution_placement` /
    :func:`_aromatic_matchings`), so two SMILES spellings of one molecule share an identity.  A ``Molecule`` built by
    FRAGMENT SURGERY -- every scission/redox/heterolytic producer in ``structure_descent`` slices an existing graph and
    NEVER re-parses -- skips that path, so an explicit-Kekulé fragment (e.g. an ORTHO-disubstituted salicylate cut out
    of aspirin) can carry a different ring bond-order pattern than the SAME species parsed from SMILES, and
    ``Molecule.canonical()`` -- which has no resonance notion, only literal bond orders -- then calls them distinct.
    That is the aspirin NO_ROUTE bug: a real disconnection is emitted but its fragment fails to match its registered
    stock.  This applies the identical minimal-constitution placement to an arbitrary ``Molecule``, so a fragment
    unifies with its parsed form.

    It is SOUND (never over-unifies): the placement fixes each atom's pi-demand ``need[a] = sum(order-1)`` from the
    drawn bonds and only re-distributes multiple-bond orders that satisfy the SAME per-atom demand -- a genuine
    resonance form of the SAME constitution.  Two molecules with different constitution or different pi-demand (a real
    double-bond-position tautomer: 1-butene vs 2-butene) keep DISTINCT identities.  It is idempotent on an
    already-parsed (already resonance-canonical) molecule, so wiring it into an identity comparison changes ONLY the
    fragments that were previously mis-split -- no parsed molecule's digest moves.  A molecule whose Kekulé placements
    exceed the enumeration bound raises (never truncates to a non-deterministic minimum), exactly as the parser does.
    """
    atoms, bonds = molecule.atoms, molecule.bonds
    if len(atoms) <= 1:
        return molecule.canonical()
    heavy = [i for i, s in enumerate(atoms) if s != "H"]
    if not heavy or len(heavy) > _RESONANCE_MAX_HEAVY:
        # O(1) DoS guard: a molecule too large to canonicalise per-placement cheaply keeps its literal identity
        # (no worse than pre-fix -- it simply won't unify across Kekulé spellings; see the cap note above).
        return molecule.canonical()
    old_to_new = {old: new for new, old in enumerate(heavy)}
    h_count = [0] * len(heavy)
    heavy_bonds: list[list[int]] = []
    for b in bonds:
        i_is_h, j_is_h = atoms[b.i] == "H", atoms[b.j] == "H"
        if i_is_h and j_is_h:
            continue  # an H2 fragment carries no pi-system; the heavy walk ignores it
        if i_is_h or j_is_h:
            h_count[old_to_new[b.j if i_is_h else b.i]] += 1  # tally each heavy atom's explicit H neighbours
        else:
            heavy_bonds.append([old_to_new[b.i], old_to_new[b.j], b.order])
    # Rebuild the heavy skeleton as parser-shaped atoms whose H is pinned EXACTLY (never implicitly refilled), so the
    # placement re-materialises the identical hydrogen envelope and the digest it minimises is this molecule's own.
    heavy_atoms = [_Atom(atoms[old], False, 0, h_count[new]) for new, old in enumerate(heavy)]
    orders = _min_constitution_placement(heavy_atoms, heavy_bonds, molecule.charge,
                                         max_matchings=_RESONANCE_MAX_MATCHINGS)
    for k in range(len(heavy_bonds)):
        heavy_bonds[k][2] = orders[k]
    out_atoms, out_bonds = _fill_hydrogens(heavy_atoms, heavy_bonds)
    return Molecule(tuple(out_atoms), frozenset(out_bonds), molecule.charge, molecule.state).canonical()


def resonance_identity(molecule: Molecule) -> str:
    """The resonance-canonical identity string shared by route search (``_ident``) and the structural IR
    (``_structure_ident``), so both key on the SAME identity a fragment and its parsed form now agree on.

    Falls back to the literal canonical digest when the canonicaliser refuses the graph (``NotImplementedError`` ->
    the ``asgiven:`` sentinel, unchanged) or when the resonance enumeration is out of scope for a huge fused system
    (``SmilesError`` -> the plain ``canonical()`` digest); in that last case the fragment simply won't unify across
    Kekulé spellings, which is exactly the pre-fix behaviour, never worse.
    """
    try:
        return canonical_digest(resonance_canonical(molecule))
    except NotImplementedError:
        return "asgiven:" + canonical_digest(molecule)
    except SmilesError:
        try:
            return canonical_digest(molecule.canonical())
        except NotImplementedError:
            return "asgiven:" + canonical_digest(molecule)


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


def _perm_parity(seq: "list[int]") -> int:
    """Parity (0 even / 1 odd) of the permutation that sorts ``seq`` -- its inversion count mod 2."""
    inv = 0
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            if seq[i] > seq[j]:
                inv ^= 1
    return inv


def _kekulize_in_place(atoms: list[_Atom], work: list[list[int]], charge: int) -> None:
    """Assign a CONSTITUTION-canonical Kekulé structure to ``work`` (order column) IN PLACE, preserving the caller's
    heavy-atom indices -- the same index-stable canonicalisation :func:`_isotopic_identity` uses, so a chirality key
    keyed on the resulting WL colours is spelling-invariant and refines the constitution the parser commits to."""
    arom_bonds, matchings = _aromatic_matchings(atoms, work)
    if not matchings:
        orders = _min_constitution_placement(atoms, [list(b) for b in work], charge)
        for k in range(len(work)):
            work[k][2] = orders[k]
        return
    best_constitution, best_matching = None, matchings[0]
    for doubles in matchings:
        for k in arom_bonds:
            work[k][2] = 2 if k in doubles else 1
        out_atoms, out_bonds = _fill_hydrogens(atoms, work)
        constitution = canonical_digest(Molecule(tuple(out_atoms), frozenset(out_bonds), charge).canonical())
        if best_constitution is None or constitution < best_constitution:
            best_constitution, best_matching = constitution, doubles
    for k in arom_bonds:
        work[k][2] = 2 if k in best_matching else 1


def _on_cycle(a: int, neighbours: "dict[int, list[int]]", n_atoms: int) -> bool:
    """True iff atom ``a`` lies ON a ring (a cycle passes through it): two of its neighbours stay connected in the
    graph with ``a`` removed.  A ring stereocentre is scoped OUT of chirality perception (its written neighbour order
    depends on the ring-closure DIGIT position, which the bond list does not preserve) -- this is the check that makes
    the docstring's "a ring centre contributes nothing" TRUE, not just claimed.  A ring SUBSTITUENT (e.g. a phenyl arm
    on an acyclic centre) does NOT put the centre on a cycle, so such centres stay perceivable."""
    nbrs = neighbours[a]
    if len(nbrs) < 2:
        return False
    component: dict[int, int] = {}
    cid = 0
    for start in range(n_atoms):
        if start == a or start in component:
            continue
        cid += 1
        stack = [start]
        component[start] = cid
        while stack:
            x = stack.pop()
            for y in neighbours[x]:
                if y != a and y not in component:
                    component[y] = cid
                    stack.append(y)
    seen: set[int] = set()
    for nb in nbrs:
        c = component.get(nb)
        if c in seen:
            return True                                   # two neighbours share a component sans a -> a is on a cycle
        seen.add(c)
    return False


def _perceive_configuration(
    atoms: list[_Atom], bonds: list[list[int]], charge: int
) -> "tuple[str | None, bool]":
    """The chirality-parity perception, returning ``(CONFIGURATION digest or None, perception_complete)``.

    Graph canonicalisation genuinely CANNOT see chirality -- two enantiomers are the SAME graph -- so the extra
    handedness bit is captured EXPLICITLY: for each declared stereocentre, the parity of its four neighbours' WRITTEN
    order relative to their canonical (1-WL colour) order, XORed with the ``@``/``@@`` sense.  A neighbour transposition
    flips the SMILES sense, so ``parity XOR sense`` is invariant across spellings of one enantiomer and OPPOSITE for its
    mirror image (swap-flips-sense pairs agree, enantiomers differ; meso equals its own mirror, (R,R) != (S,S)).

    The digest REFINES constitution -- ``canonical_digest((constitution, sorted (WL-colour, handedness) per centre))``
    -- so equal configuration implies equal constitution; an achiral molecule is ``None`` (left to match at
    CONSTITUTION, never silently split).  Scope is the SOUNDLY perceivable subset: an ACYCLIC tetrahedral centre with
    four neighbours (implicit H per OpenSMILES) whose four 1-WL colours are DISTINCT.  A centre WL cannot separate, or a
    RING centre, contributes NOTHING -- an honest gap, never a guessed parity.

    ``perception_complete`` is the FAIL-CLOSED signal a MATCH-LAYER consumer needs (ID-STEREO-02): ``True`` iff EVERY
    marked centre yielded a descriptor -- i.e. NONE was scoped out.  A scoped-out marked centre is a real stereocentre
    we cannot perceive, so treating configuration as fully determined would FALSELY MERGE two enantiomers differing only
    there; when perception is incomplete the caller must leave CONFIGURATION UNKNOWN, never reduce it to constitution.
    An achiral molecule (no marked centre) is trivially complete.  A marked-but-provably-false centre (two identical
    substituents) also scopes out and conservatively counts as INCOMPLETE -- fail-closed (an honest UNKNOWN at
    CONFIGURATION), never a false merge.  (E/Z and CIP R/S *naming* are the remaining ID-STEREO-01 deferrals; identity
    -- are two species the same stereoisomer? -- does not need the R/S label.)
    """
    marked = [a for a in range(len(atoms)) if atoms[a].chirality]
    if not marked:
        return None, True                                        # achiral: trivially complete, reduces to constitution
    work = [list(b) for b in bonds]
    _kekulize_in_place(atoms, work, charge)
    filled_atoms, filled_bonds = _fill_hydrogens(atoms, work)     # heavy indices 0..n-1 preserved; H appended after
    wl = _wl_colours(tuple(filled_atoms), frozenset(filled_bonds))
    n = len(atoms)
    neighbours: dict[int, list[int]] = {i: [] for i in range(len(filled_atoms))}
    for b in filled_bonds:
        neighbours[b.i].append(b.j)
        neighbours[b.j].append(b.i)
    descriptors: list[tuple[int, int]] = []
    for a in marked:
        if _on_cycle(a, neighbours, len(filled_atoms)):
            continue                                             # RING stereocentre: out of the acyclic scope ->
            # honest gap (its written neighbour order depends on the ring-closure DIGIT position, which the bond
            # list does not preserve -- reconstructing it, and E/Z + CIP R/S, are the named ID-STEREO-01 deferrals).
        incoming = [bd[0] for bd in bonds if bd[1] == a]          # the preceding atom (a is the bond's 2nd endpoint)
        outgoing = [bd[1] for bd in bonds if bd[0] == a]          # branch/chain children, in written order
        h_neighbours = [j for j in neighbours[a] if j >= n and filled_atoms[j] == "H"]   # a's implicit/explicit H
        if len(incoming) > 1:
            continue                                             # defensive: any residual multi-incoming -> skip
        written = ([incoming[0]] if incoming else []) + h_neighbours + outgoing
        if len(written) != 4:
            continue                                             # not a four-coordinate centre in scope
        colours = [wl[x] for x in written]
        if len(set(colours)) != 4:
            continue                                             # WL cannot separate the four -> not perceivable here
        handedness = _perm_parity(colours) ^ (0 if atoms[a].chirality == 1 else 1)
        descriptors.append((wl[a], handedness))
    complete = len(descriptors) == len(marked)                   # every marked centre perceived -> nothing scoped out
    if not descriptors:
        return None, complete
    constitution = canonical_digest(Molecule(tuple(filled_atoms), frozenset(filled_bonds), charge).canonical())
    return canonical_digest((constitution, tuple(sorted(descriptors)))), complete


def _configuration_identity(atoms: list[_Atom], bonds: list[list[int]], charge: int) -> "str | None":
    """The canonical CONFIGURATION key (the digest half of :func:`_perceive_configuration`), or ``None`` when the input
    declares no PERCEIVABLE stereocentre.  See :func:`_perceive_configuration` for the parity method and its scope."""
    return _perceive_configuration(atoms, bonds, charge)[0]


def configuration_key(text: str) -> str:
    """The canonical CONFIGURATION-refined key of ``text`` (ID-STEREO-01), a string for ANY input.

    For an achiral molecule (or one whose stereocentres are not soundly perceivable) this is a constitution-equivalent
    key -- two same-constitution spellings share it; a perceivable stereocentre makes it finer.  So
    ``configuration_key(a) == configuration_key(b)`` iff ``a`` and ``b`` are the same species at the
    CONFIGURATION-refined-constitution level for the perceivable subset (:func:`_configuration_identity`): enantiomers
    differ, a meso form matches its mirror, and every non-chiral pair reduces to constitution.  Raises
    :class:`SmilesError` on a malformed/out-of-scope SMILES, like the parser."""
    if not isinstance(text, str):
        raise SmilesError("SMILES input must be a string")
    stripped = text.strip()
    if not stripped:
        raise SmilesError("empty SMILES")
    atoms, bonds = _parse_skeleton(stripped)
    charge = sum(a.charge for a in atoms)
    configuration = _configuration_identity(atoms, bonds, charge)
    return configuration if configuration is not None else resonance_identity(_build_molecule(atoms, bonds, charge))


# --- ROUND 20 (ID-STEREO-CIP-NAMER): the general CIP Rule-1a breadth-first hierarchical-digraph ranker ---
#
# CIP priority ranking is the HARD half of R/S naming and the wall the distinct-Z slice punts on.  Two prior
# attempts died (ROUND 13/14) to a DEPTH-first tie-break (a nested-tuple lexicographic key), which descends the
# first branch to its leaves before ever comparing the second branch's near sphere -- wrong for the common
# branch-vs-chain motif (``C[C@H](CCC)C(C)C``: isopropyl's first carbon (C,C,H) outranks n-propyl's (C,H,H) AT
# the sphere, a decision DFS defers past).  The correct rule is BREADTH-first, branch-by-branch (Hanson,
# Musacchio, Mayfield, Vainio, Yerin, Redkin, *J. Chem. Inf. Model.* 2018, 58(9), 1755): compare a whole sphere
# of children atomic numbers before descending, then resolve the highest-ranked branch pair fully before the
# next (need-to-know).  Multiple bonds and ring closures become duplicate/phantom leaf atoms (real atomic
# number, no substituents).  ROUND 28 adds CIP **Rule 2** (mass number) as its own full pass at the Rule-1a tie
# hand-off (:func:`_cip_compare_rule2`): where Rule 1a leaves a same-Z tie, the isotope mass breaks it in the
# Rule-1a-established order (so ``F[C@@](Cl)([2H])[3H]`` now NAMES).  Still SOUND, not complete: a tie needing an
# UNBUILT rule (1b/3/4/5), one with an ambiguous Rule-2 pairing (Rule-1a-tied siblings), or an unknown mass, is a
# NAMED DEFERRAL -- a wrong R/S is worse than none.  Validated against the R19 geometric oracle and hand/PubChem
# textbook absolutes (incl. the L-serine=S / L-cysteine=R flip, and the ROUND-28 Rule-2 cases) in
# ``experiments/cip_namer_probe.py``.

_CIP_PHANTOM = (0, 0, ())            #: the phantom (atomic-number-0, mass-0) leaf a missing branch slot pads with
_CIP_AROMATIC = object()             #: sentinel children of an AROMATIC atom: z is known, onward connectivity is withheld
_CIP_NODE_BUDGET = 60000             #: digraph-construction cap; a pathological giant fails CLOSED (defer, never guess)
_CIP_COMPARE_BUDGET = 400000         #: pairwise-comparison cap; likewise fail-closed
_CIP_MANCUDE_MAX_ATOMS = 30          #: per ring system, independent of the parser's identity budget
_CIP_MANCUDE_MAX_MATCHINGS = 128
_CIP_MANCUDE_WORK_BUDGET = 10000


def _cip_mass(element: str, isotope: int) -> "float | None":
    """The CIP **Rule 2** mass of an atom (ROUND 28), in unified atomic mass units.

    A SPECIFIED isotope (``[2H]``, ``[13C]``) carries its exact mass NUMBER (2013 IUPAC Rule 2); an
    unspecified atom carries the SOURCED IUPAC/CIAAW standard atomic weight (``smartchem.data.periodic_table``),
    so the natural-abundance average sits BETWEEN the light and heavy isotopes: ``[1H] (1) < H (1.008) < [2H]
    (2) < [3H] (3)`` and ``[12C] (12) < C (12.011) < [13C] (13)``.  ``None`` when no true standard atomic weight
    exists (a naturally-radioactive or synthetic element -- ``has_standard_atomic_weight`` is ``False``) AND no
    isotope was specified: Rule 2 then DEFERS rather than fabricate a weight from a most-stable-isotope mass
    number (``known-physics-not-new-physics``; those elements are bracket-reachable and NOT filtered by the
    stereocentre scope, so this guard is load-bearing, not defensive garnish)."""
    if isotope:
        return float(isotope)
    if has_standard_atomic_weight(element):
        return standard_atomic_weight(element)
    return None


def _cip_ring_edges(n, bonds) -> frozenset[int]:
    """Ring edges are exactly the non-bridges of the undirected sigma graph (iterative Tarjan DFS)."""
    adj = [[] for _ in range(n)]
    for bi, (a, b, _order) in enumerate(bonds):
        adj[a].append((b, bi))
        adj[b].append((a, bi))
    entered, low, parent = {}, {}, {}
    bridges = set()
    for root in range(n):
        if root in entered:
            continue
        entered[root] = low[root] = len(entered)
        parent[root] = (-1, -1)
        stack = [(root, iter(adj[root]))]
        while stack:
            a, walk = stack[-1]
            step = next(walk, None)
            if step is None:
                stack.pop()
                p, edge = parent[a]
                if p != -1:
                    low[p] = min(low[p], low[a])
                    if low[a] > entered[p]:
                        bridges.add(edge)
                continue
            b, bi = step
            if bi == parent[a][1]:
                continue
            if b in entered:
                low[a] = min(low[a], entered[b])
            else:
                parent[b] = (a, bi)
                entered[b] = low[b] = len(entered)
                stack.append((b, iter(adj[b])))
    return frozenset(set(range(len(bonds))) - bridges)


def _cip_mancude(atoms, bonds, adj) -> "tuple[frozenset[int], dict[int, Fraction], frozenset[int]]":
    """``(blocked, averages, released)`` for the ring systems of the molecule (ROUND 22 mancude + ROUND 33
    localized rings): the Kekule-dependent BOUNDARY atoms, the exact duplicate-Z averages for delocalized
    (>=2-Kekule) mancude systems, and the atoms of LOCALIZED (unique-Kekule) rings released to the ordinary digraph.

    IUPAC P-92.1.4.4 averages over the POSSIBLE PARTNER POSITIONS, not over whole Kekule structures
    with their unequal partner frequencies.  Enumerate perfect matchings only to establish which partners
    are possible; average each distinct partner once.  The supported valences have one ring double per
    neutral C / pyridine-N acceptor and none per fixed pyrrole-N / O / S donor.  A saturated sp3 ring carbon
    (all bonds order 1) is admitted as a pass-through SPECTATOR (ROUND 33) so a partially-unsaturated ring
    reaches the matching enumeration.  A component with a UNIQUE perfect matching (matching_count==1) is a
    single Kekule structure -- NOT a superposition -- and is RELEASED to the ordinary digraph (real z, real
    mass; recorded in ``released``), exactly as an acyclic double bond is handled; a delocalized component
    (>=2 matchings, no spectator) is AVERAGED as before (every real atom and ring-closure duplicate keeps its
    integer Z; only multiple-bond duplicates get the average).

    Detection uses ring topology and filled valence, never lowercase flags as an admission shortcut: an
    explicit Kekule spelling receives the same treatment. Charged, exocyclic-multiple, and mixed
    partially-saturated-fused (>=2 matchings WITH a spectator, e.g. indene/tetralin) systems remain lazy
    boundaries; over-budget matchings fail closed (stay blocked). Saturated rings keep their existing ordinary
    digraph. This is a bounded Rule-1a extension, not general aromaticity perception.
    """
    ring_edges = _cip_ring_edges(len(atoms), bonds)
    ring_adj = {}
    for bi in ring_edges:
        a, b, _order = bonds[bi]
        ring_adj.setdefault(a, set()).add(b)
        ring_adj.setdefault(b, set()).add(a)
    blocked = {i for i, atom in enumerate(atoms) if atom.aromatic}
    averages = {}
    released = set()                                     # ROUND 33: atoms in localized (unique-Kekule) rings released
    seen = set()
    for start in ring_adj:
        if start in seen:
            continue
        component, todo = set(), [start]
        while todo:
            a = todo.pop()
            if a in component:
                continue
            component.add(a)
            todo.extend(ring_adj[a] - component)
        seen.update(component)
        if not any(atoms[a].aromatic or any(o > 1 for _b, o in adj[a]) for a in component):
            continue
        blocked.update(component)
        if len(component) > _CIP_MANCUDE_MAX_ATOMS:
            continue
        acceptors = set()
        valid = True
        spectator_present = False
        for a in component:
            atom = atoms[a]
            orders = sorted(o for _b, o in adj[a])
            ring_doubles = sum(o == 2 and b in ring_adj[a] for b, o in adj[a])
            if atom.charge:
                valid = False
            elif atom.element == "C" and orders == [1, 1, 2] and ring_doubles == 1:
                acceptors.add(a)
            elif atom.element == "N" and orders == [1, 2] and ring_doubles == 1:
                acceptors.add(a)
            elif atom.element == "N" and orders == [1, 1, 1]:
                pass
            elif atom.element in ("O", "S") and orders == [1, 1]:
                pass
            elif atom.element == "C" and orders == [1, 1, 1, 1]:
                spectator_present = True                 # a saturated sp3 ring carbon: ALL bonds order 1 (no ring
                # AND no exocyclic double -- the all-single pattern guarantees both), so it is a LOCALIZED-ring
                # pass-through, not a pi-participant.  Admitting it (rather than the old blanket ``else: valid=False``)
                # lets a partially-unsaturated ring -- cyclopropene, cyclohexene, cyclopentadiene, a cyclic enol
                # ether -- reach the matching enumeration below; on a UNIQUE matching the ring is released to the
                # ordinary digraph (localized double bonds, exactly as acyclic doubles are handled).
            else:
                valid = False
        if not valid or not acceptors:
            continue
        partners = {a: set() for a in acceptors}
        matching_count, work = 0, _CIP_MANCUDE_WORK_BUDGET

        def visit(left, chosen):
            nonlocal matching_count, work
            work -= 1
            if work < 0:
                raise _CipTooBig
            if not left:
                matching_count += 1
                if matching_count > _CIP_MANCUDE_MAX_MATCHINGS:
                    raise _CipTooBig
                for a, b in chosen:
                    partners[a].add(b)
                    partners[b].add(a)
                return
            a = min(left)
            for b in sorted(ring_adj[a] & left):
                visit(left - {a, b}, chosen + ((a, b),))

        try:
            visit(acceptors, ())
        except _CipTooBig:
            continue                       # never publish a truncated matching/partner set
        if not matching_count:
            continue
        # THREE-WAY release (the soundness split birdperson's review pinned):
        #   (1) matching_count == 1 -> the double-bond positions are FORCED (a SINGLE valid Kekule structure), NOT
        #       a superposition.  Release to the ordinary ``_cip_digraph`` with REAL atomic number AND REAL mass --
        #       by leaving these atoms OUT of both ``blocked`` and the ``averages`` (mancude) dict, so the digraph's
        #       ``else`` branch (real z, real mass) and real integer-Z closure leaves fire.  This is exactly the
        #       treatment an ACYCLIC double bond already receives soundly, so Rule 1a AND Rule 2 both decide.  It
        #       names the localized ring class (cyclopropene ... cyclohexadiene, cyclic enol ethers, localized fused
        #       bicyclics) and reroutes a UNIQUE-matching aromatic heterocycle (furan/pyrrole/thiophene) from a
        #       spurious Rule-2 defer (mass=None) to its real mass -- Rule 1a stays BYTE-IDENTICAL because the
        #       average of a single partner IS the real Z (Fraction(z,1) == z under every comparison here).
        #   (2) matching_count >= 2 with NO admitted spectator -> the clean, fully-conjugated mancude system
        #       (benzene, pyridine, di-2-pyridyl): today's exact partner-Z averaging, BYTE-IDENTICAL (no component
        #       that reaches averaging today has an sp3 spectator, so this branch reproduces the prior code exactly).
        #   (3) matching_count >= 2 WITH a spectator -> a mixed partially-saturated fused system (indene, tetralin):
        #       extending the AVERAGING claim (validated only for clean rings) to this new topology is unproven, so
        #       DEFER (leave the component blocked) rather than risk a mislabel.  A distinct, characterised next gap
        #       (aromatic-fused-to-saturated ring substituents), not this round's localized-ring target.
        if matching_count == 1:
            blocked.difference_update(component)
            released.update(component)                   # ROUND 33: this component is a LOCALIZED ring released to
            # the ordinary digraph (real z/mass).  Recorded so a ranking that would pit a released localized ring
            # against a mancude-AVERAGED ligand can fail closed: that cross-comparison rests on the pre-existing
            # partner-Z averaging (R22), which is not oracle-clean for complex conjugation (dalembert flagged it
            # orthogonal), so it must DEFER rather than risk a mislabel.  Saturated rings are never in this set
            # (they are skipped before the classifier), so the guard cannot regress them.
        elif not spectator_present:
            averages.update({a: Fraction(sum(ATOMIC_NUMBER[atoms[b].element] for b in choices), len(choices))
                             for a, choices in partners.items()})
            blocked.difference_update(component)
        # else (matching_count >= 2 with a spectator): leave the component blocked -> the centre defers.
    return frozenset(blocked), averages, frozenset(released)


class _CipTooBig(Exception):
    """The digraph/comparison budget was exhausted -> fail-closed DEFERRAL (never a guessed label)."""


class _CipAromatic(Exception):
    """A comparison needed onward connectivity of an unsupported/over-budget unsaturated ring.

    A known atomic number can still decide before this lazy boundary is inspected. Supported neutral mancude
    systems use exact duplicate-Z averaging; charged resonance and other unsupported systems do not guess.
    """


class _CipAmbiguous(Exception):
    """A later-rule (Rule 2) comparison could not be made without an ARBITRARY choice -> fail-closed DEFERRAL.

    Raised by :func:`_cip_compare_rule2` on an unknown mass (a mancude-superposition duplicate, or a
    radioactive/synthetic element with no true standard weight and no specified isotope) OR a Rule-1a-tied
    sibling set whose Rule-2 pairing is arbitrary.  A guessed pairing could yield a WRONG R/S label, so the
    centre DEFERS instead (the ROUND-28 soundness discipline; a wrong label is worse than no label)."""


def _cip_digraph(atom_idx, parent_idx, path, adj, elems, mass, aromatic, budget, mancude=None):
    """One node of the CIP hierarchical digraph, ``(atomic_number, mass, children)`` (ROUND 28 enriched the
    former ``(atomic_number, children)`` 2-tuple with a ``mass`` slot at index 1 for CIP Rule 2; children move
    to index 2).  ``mass`` is a parallel array keyed by atom index (:func:`_cip_mass`), threaded in rather than
    perturbing the element-string canonicalisation ``_kekulize_in_place``/``_wl_colours`` rely on; ``None`` where
    no true standard weight exists (see :func:`_cip_mass`).

    A multiple bond of order ``o`` contributes ``o - 1`` duplicate leaves of the bonded partner on each side;
    a ring-closure bond (a neighbour already on the root->here path) is NOT traversed and contributes one
    integer-Z closure leaf plus the usual ``o - 1`` multiple-bond duplicates -- so every root-to-leaf path
    visits each real atom at most once and the digraph is FINITE (depth bounded by the atom count).  A
    duplicate/phantom leaf carries the real atomic number of the atom it duplicates but no substituents (its
    own children are the atomic-number-0 phantoms, which the padded comparison in :func:`_cip_compare` treats
    identically to an empty child list); a ring-closure or ordinary multiple-bond duplicate carries the MASS of
    the real atom it duplicates.  Mancude multiple-bond duplicates instead carry the OWNER's exact partner-Z
    average -- a Kekule/partner SUPERPOSITION, not one atom -- so their ``mass`` is ``None`` (no single-atom
    referent; Rule 2 DEFERS on them rather than fabricate, the di-2-pyridyl pin defers either way); a ring-
    closure's own closure leaf stays integer-Z with the duplicated atom's real mass.
    An unsupported unsaturated ring atom is a BOUNDARY
    node ``(z, mass, _CIP_AROMATIC)``: its atomic number AND its own (Kekule-independent) mass are known (so a
    ranking can still decide ON it), but its onward connectivity is withheld because it is Kekule-dependent -- a
    comparison that tries to descend past it raises :class:`_CipAromatic` and the centre defers (its phantom
    DUPLICATES, being z-only leaves, are always safe)."""
    z = ATOMIC_NUMBER.get(elems[atom_idx], 0)
    if atom_idx in aromatic:
        return (z, mass[atom_idx], _CIP_AROMATIC)               # boundary: known z+mass, Kekule-dependent onward -> lazy defer
    budget[0] -= 1
    if budget[0] < 0:
        raise _CipTooBig
    children: list = []
    for nb, order in adj[atom_idx]:
        znb = ATOMIC_NUMBER.get(elems[nb], 0)
        if nb != parent_idx and nb in path:
            children.append((znb, mass[nb], ()))               # ring closure is an integer-Z duplicate (real atom's mass)
        elif nb != parent_idx:
            if nb in aromatic and order > 1:
                raise _CipAromatic                              # exocyclic multiple bond INTO an aromatic atom: the
                # duplicate COUNT (order-1) is Kekule-dependent, generated here at the non-aromatic side before the
                # boundary is consulted -- so defer rather than emit a Kekule-dependent phantom multiset (evil-morty
                # residual A; unproven-reachable but discharged, not left to chance).
            children.append(_cip_digraph(nb, atom_idx, path | {nb}, adj, elems, mass, aromatic, budget, mancude))
        # A mancude multiple-bond duplicate carries the owner's averaged Z (a superposition) -> mass has no
        # single-atom referent -> None (DEFER under Rule 2, never fabricate).  An ordinary duplicate carries
        # the real partner atom's mass.
        if mancude is not None and atom_idx in mancude:
            duplicate_z, dup_mass = mancude[atom_idx], None
        else:
            duplicate_z, dup_mass = znb, mass[nb]
        for _ in range(order - 1):
            children.append((duplicate_z, dup_mass, ()))
    return (z, mass[atom_idx], tuple(children))


def _cip_sorted_children(node, ctx) -> tuple:
    """``node``'s children ranked by CIP priority, highest first; memoised per node in ``ctx['sc']`` so a
    repeated subtree (e.g. every residue of a peptide backbone) is ranked once, not re-sorted on each visit.
    An AROMATIC boundary node has no available children -- inspecting them would depend on the Kekule structure --
    so this raises :class:`_CipAromatic`, deferring the centre (reached only when a tie forces a descent past it)."""
    if node[2] is _CIP_AROMATIC:
        raise _CipAromatic
    sc = ctx["sc"]
    cached = sc.get(node)
    if cached is None:
        cached = tuple(sorted(node[2], key=cmp_to_key(lambda x, y: _cip_compare(x, y, ctx)), reverse=True))
        sc[node] = cached
    return cached


def _cip_compare(a, b, ctx) -> int:
    """Rank two digraph nodes by CIP Rule 1a: ``+1`` if ``a`` outranks ``b``, ``-1`` if ``b``, ``0`` if tied.

    Breadth-first, branch-by-branch (Hanson et al. 2018): equal atomic number -> rank each node's children and
    compare the WHOLE immediate sphere of their atomic numbers before descending (the step a depth-first
    nested-tuple key skips -- the ROUND-14 bug), and only if the entire sphere ties resolve the highest-ranked
    branch pair fully before the next.  A duplicate leaf competes at its own sphere on its REAL atomic number
    and only loses to a real atom of the same number ONE sphere later (its children are phantom-0), so the
    naive "a real atom always beats a duplicate" shortcut -- which mislabels -- is deliberately NOT taken.  A
    ``0`` is a genuine Rule-1a indistinguishability; the caller DEFERS rather than guess.

    Step 3 (the immediate sphere) compares the children's ATOMIC NUMBERS directly -- each child's z is known even
    for an aromatic child, and the ordering of same-z children does not change the z-sequence -- so a decision at
    the sphere never ranks (never descends into) a child, and an aromatic ring in a branch the sphere already
    decides is never consulted.  Only if the whole sphere ties does step 4 fully rank the children (which may then
    descend past an aromatic boundary and raise :class:`_CipAromatic`).  Memoised in ``ctx['cmp']`` (nodes are
    immutable tuples); the cheap unequal-atomic-number case short-circuits before the cache/budget.  ``ctx['budget']``
    bounds the recursion fail-closed (raise -> DEFER) against a pathological digraph."""
    if a[0] != b[0]:
        return 1 if a[0] > b[0] else -1                        # cheap, exact, no memo/budget needed
    cache = ctx["cmp"]
    key = (a, b)
    hit = cache.get(key)
    if hit is not None:
        return hit
    ctx["budget"][0] -= 1
    if ctx["budget"][0] < 0:
        raise _CipTooBig
    za = _cip_child_zs(a)                                       # step 3: the immediate sphere by atomic number ALONE --
    zb = _cip_child_zs(b)                                       # no ranking, so a same-z aromatic grandchild is never consulted
    m = max(len(za), len(zb))
    r = 0
    for k in range(m):
        xa = za[k] if k < len(za) else 0
        xb = zb[k] if k < len(zb) else 0
        if xa != xb:
            r = 1 if xa > xb else -1
            break
    if r == 0:
        ca = _cip_sorted_children(a, ctx)                      # step 4: the sphere ties -> now fully rank the children
        cb = _cip_sorted_children(b, ctx)                      # (may descend past an aromatic boundary -> _CipAromatic)
        for k in range(max(len(ca), len(cb))):                 # resolve the top branch pair before the next (need-to-know)
            na = ca[k] if k < len(ca) else _CIP_PHANTOM
            nb = cb[k] if k < len(cb) else _CIP_PHANTOM
            c = _cip_compare(na, nb, ctx)
            if c != 0:
                r = c
                break
    cache[key] = r
    cache[(b, a)] = -r
    return r


def _cip_compare_rule2(a, b, ctx) -> int:
    """Rank two Rule-1a-EQUAL digraph nodes by CIP **Rule 2** (mass number); ``+1``/``-1``/``0`` (ROUND 28).

    Called ONLY on nodes :func:`_cip_compare` returned ``0`` for (Rule 1a exhausted over the whole digraph
    first -- CIP hierarchy).  It MIRRORS ``_cip_compare``'s validated breadth-first, branch-by-branch shape but
    on the ``mass`` slot: this node's own mass -> the immediate sphere of the children's masses (in the
    Rule-1a-established order) -> only if the whole sphere ties, descend the ranked branch pairs (need-to-know).
    That breadth-first-then-descend order is the SAME shape the ``_DIV_A``/``_DIV_B`` proof pins for Rule 1a
    (NOT a depth-first dive into the top branch, which would be the ROUND-14 bug reincarnated for mass).

    SOUND, not complete -- it fail-closes to a DEFERRAL (raises :class:`_CipAmbiguous`) rather than ever guess a
    label, in three cases: (1) an unknown mass (``None``: a mancude superposition duplicate, or a radioactive/
    synthetic element with no true standard weight and no specified isotope); (2) a Rule-1a-tie among SIBLINGS
    (checked ALL-PAIRS, not adjacent-only -- ``_cip_compare`` is not proven transitive, so an adjacent-only scan
    of a sorted sequence could miss a hidden non-adjacent tie), which makes the child pairing arbitrary; (3) a
    paired-child Rule-1a MISMATCH (the recursion's own precondition, enforced not assumed -- if a non-transitive
    mis-sort ever mispairs, this fails closed instead of mislabelling).  Only where the pairing is FORCED and
    every mass is known does it return a verdict.  Higher-rule ties (1b/3/4/5) it leaves as ``0`` (the caller
    DEFERS)."""
    if a[1] is None or b[1] is None:
        raise _CipAmbiguous                                    # unknown mass -> DEFER, never a bogus None comparison
    if a[1] != b[1]:
        return 1 if a[1] > b[1] else -1                        # this node's own mass decides
    ca = _cip_sorted_children(a, ctx)                          # Rule-1a order (may raise _CipAromatic)
    cb = _cip_sorted_children(b, ctx)
    for seq in (ca, cb):                                       # (2) ALL-PAIRS sibling-tie guard: transitivity-free
        for i in range(len(seq)):
            for j in range(i + 1, len(seq)):
                if _cip_compare(seq[i], seq[j], ctx) == 0:
                    raise _CipAmbiguous                        # ambiguous pairing -> DEFER
    paired = []
    for k in range(max(len(ca), len(cb))):
        na = ca[k] if k < len(ca) else _CIP_PHANTOM
        nb = cb[k] if k < len(cb) else _CIP_PHANTOM
        if _cip_compare(na, nb, ctx) != 0:                     # (3) enforce the Rule-1a-equal pairing precondition
            raise _CipAmbiguous                                # a mispair (only under non-transitivity) -> DEFER
        paired.append((na, nb))
    for na, nb in paired:                                      # step 3: the sphere of child masses (breadth), Rule-1a order
        if na[1] is None or nb[1] is None:
            raise _CipAmbiguous
        if na[1] != nb[1]:
            return 1 if na[1] > nb[1] else -1
    for na, nb in paired:                                      # step 4: sphere of masses tied -> descend ranked pairs
        c = _cip_compare_rule2(na, nb, ctx)
        if c != 0:
            return c
    return 0


def _cip_rank_compare(a, b, ctx, both_acyclic=True) -> int:
    """The CIP hierarchical rank of two ligand digraphs (ROUND 28): Rule 1a exhausted over the WHOLE digraph
    FIRST, then -- ONLY on a genuine Rule-1a tie -- Rule 2 (mass number) as its own full pass.  ``+1``/``-1``/
    ``0``; a ``0`` is a tie no BUILT rule breaks, so the caller DEFERS.  Rule 2 may raise :class:`_CipAmbiguous`
    or :class:`_CipAromatic` (both -> DEFER).  Rules 1b/3/4/5 are NOT built, so a Rule-1a+Rule-2 tie stays ``0``
    (a NAMED deferral).  Keeping Rule 2 a separate pass entered only at the ``_cip_compare == 0`` hand-off is
    soundness-required: folding mass into ``_cip_compare``'s per-leaf tuple would let a shallow mass tie override
    a deeper Rule-1a atomic-number difference -- an inversion of CIP precedence.

    ``both_acyclic`` GATES the Rule-1a -> Rule-2 leapfrog past the UNBUILT Rule 1b (ROUND 33, the localized-ring
    release).  R32 proved Rule 1b is inert on TREES (an acyclic Rule-1a tie <=> identical constitution, so 1b --
    a constitutional rule -- cannot act), which is what licenses skipping straight to Rule 2 for acyclic ligands.
    But Rule 1b BITES with ring closures (Hanson 2018): two ligands CONTAINING RINGS can tie under Rule 1a while
    being constitutionally distinct (ring reconvergence), where Rule 1b would decide -- and letting Rule 2 (an
    isotope asymmetry) break that tie the other way would MISLABEL.  So when either tied ligand contains a ring
    closure (``both_acyclic`` False), a Rule-1a tie DEFERS (returns ``0``) instead of consulting Rule 2 -- the
    sound fail-closed into Rule-1b territory.  Costs only the exotic isotope-on-a-ring corner; a ring vs a
    Rule-1a-DISTINCT ligand (the common localized-ring case) is decided by Rule 1a and never reaches here."""
    c = _cip_compare(a, b, ctx)
    if c != 0:
        return c
    if not both_acyclic:
        return 0                    # Rule-1a tie on a ring-bearing ligand -> Rule 1b territory (unbuilt) -> DEFER
    return _cip_compare_rule2(a, b, ctx)


def _ligand_atoms(w: int, centre: int, adj: "dict[int, list[tuple[int, int]]]") -> "tuple[bool, set[int]]":
    """``(has_ring, atom_set)`` for the ligand rooted at written-neighbour ``w`` (the substituent reached from
    ``centre`` through ``w``).  An off-ring centre (the only scope here) splits the molecule minus ``centre`` into
    disjoint ligand components, so this explores ``w``'s component (never crossing back through ``centre``).
    ``has_ring`` is True iff that component has a cycle (edge count >= node count; a tree has ``nodes - 1`` edges;
    multiplicity is irrelevant -- a double bond is one edge -- so it is the sigma-ring, exactly): its CIP digraph
    will hold ring-closure duplicate atoms, which gates the Rule-2 leapfrog past the unbuilt Rule 1b (inert on
    trees, not on rings -- see :func:`_cip_rank_compare`).  ``atom_set`` is the ligand's atoms, used to detect
    whether a ligand touches a mancude-averaged atom or an R33-released localized-ring atom (the fail-closed guard
    in :func:`_cip_ranks`)."""
    seen = {w}
    stack = [w]
    directed_edges = 0
    while stack:
        node = stack.pop()
        for nb, _order in adj[node]:
            if nb == centre:
                continue
            directed_edges += 1                       # each undirected edge is seen once from each endpoint
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return directed_edges // 2 >= len(seen), seen     # tree: edges == nodes - 1; ring: edges >= nodes


def _cip_child_zs(node) -> tuple:
    """The descending atomic numbers of ``node``'s children -- the immediate sphere, WITHOUT ranking them (so a
    Kekule-dependent aromatic grandchild is never consulted, only its known atomic number counts).  An aromatic
    BOUNDARY node has no available children, so this raises :class:`_CipAromatic` (its own z was already used by
    the caller's atomic-number check; it is only the onward structure that is withheld)."""
    if node[2] is _CIP_AROMATIC:
        raise _CipAromatic
    return tuple(sorted((c[0] for c in node[2]), reverse=True))


def _cip_ranks(written, centre, adj, elems, mass, aromatic, mancude=None, released=frozenset()) -> "list[int] | None":
    """The CIP priority rank (``0`` = highest) of each of the four WRITTEN neighbours of ``centre`` via the
    hierarchical digraph, or ``None`` when the BUILT rules do NOT fully order them (a genuine tie still needing
    Rule 1b/3/4/5, a ranking whose decision depends on an unsupported ring's substituents, an ambiguous Rule-2
    pairing, or an over-budget digraph) -- then the centre is a NAMED DEFERRAL, never a guessed label.

    Ranking is by :func:`_cip_rank_compare`: Rule 1a exhausted over the whole digraph, then (only on a genuine
    Rule-1a tie) Rule 2 (mass number, ROUND 28) as its own full pass.  ``mass`` is the per-atom-index mass array
    (:func:`_cip_mass`) threaded into the digraph.  Byte-identical to the old ``sorted(z, reverse=True)`` ranks on
    the distinct-atomic-number slice (there Rule 1a decides at sphere 0, so Rule 2 never runs), so it strictly
    EXTENDS the shipped naming without changing it -- a distinct-Z centre with an aromatic arm still names (the
    aromatic node's z decides before its withheld substituents are ever needed)."""
    try:
        roots = [_cip_digraph(w, centre, frozenset((centre, w)), adj, elems, mass, aromatic, [_CIP_NODE_BUDGET], mancude)
                 for w in written]
    except (_CipTooBig, _CipAromatic):                          # build only raises _CipAromatic for the exocyclic guard
        return None
    profiles = [_ligand_atoms(w, centre, adj) for w in written]     # ROUND 33
    has_ring = [p[0] for p in profiles]                             # gate the Rule-2 leapfrog past Rule 1b
    touches_released = [bool(p[1] & released) for p in profiles]    # a ligand holding an R33-released localized ring
    if any(touches_released) and sum(has_ring) >= 2:
        return None                                             # a released localized ring would be ranked against
        # ANOTHER ring ligand (saturated, unsaturated, or mancude-aromatic).  Ring-vs-ring CIP ranking descends into
        # competing ring-closure / double-bond duplicate structures -- Rule-1b territory (R32: Rule 1b bites with
        # ring closures) and, for an aromatic co-ligand, the pre-existing partner-Z averaging (R22) -- neither of
        # which the built Rule 1a resolves reliably.  Fail closed to a NAMED DEFERRAL (a wrong R/S is worse than
        # none).  The cited localized-ring gap bears ACYCLIC co-ligands (spectators C/F/Cl/O), so the released ring
        # is the ONLY ring on the centre and it NAMES; two SATURATED rings (never released) are unaffected.
    ctx = {"cmp": {}, "sc": {}, "budget": [_CIP_COMPARE_BUDGET]}  # caches shared across all six pairwise compares
    try:
        ranks: list[int] = []
        for k in range(4):
            higher = 0
            for j in range(4):
                if j == k:
                    continue
                # Rule 2 may break a Rule-1a tie ONLY when both ligands are trees (R32: Rule 1b inert on trees);
                # if either contains a ring closure, a Rule-1a tie defers into unbuilt Rule-1b territory (dalembert).
                c = _cip_rank_compare(roots[j], roots[k], ctx, both_acyclic=not (has_ring[j] or has_ring[k]))
                if c == 0:
                    return None                                 # tie no BUILT rule breaks (Rule 1a+2, or 1b territory) -> DEFER
                if c > 0:
                    higher += 1
            ranks.append(higher)
    except (_CipTooBig, _CipAromatic, _CipAmbiguous):
        return None
    if sorted(ranks) != [0, 1, 2, 3]:
        return None                                             # defensive: not a strict total order -> DEFER
    return ranks


def _cip_labels(atoms: list[_Atom], bonds: list[list[int]], charge: int) -> tuple[str, ...]:
    """CIP R/S NAMES for the SOUNDLY-nameable acyclic stereocentres, sorted; ``()`` if none.

    Priority is computed by the general CIP **Rule 1a** hierarchical digraph (:func:`_cip_ranks`, ROUND 20): a
    breadth-first, branch-by-branch ranking with duplicate/phantom atoms for multiple bonds and ring closures.
    This NAMES the common case the earlier distinct-atomic-number slice deferred -- amino acids, sugars, any
    secondary/tertiary carbon whose ties break one or more spheres out (L-alanine (S), L-serine (S) and its
    cysteine flip (R), the branch-vs-chain motif ``C[C@H](CCC)C(C)C`` (R) that killed the ROUND-14 depth-first
    attempt).  ROUND 28 adds CIP **Rule 2** (mass number) as its own full pass at the Rule-1a tie hand-off
    (:func:`_cip_rank_compare`), so a same-Z tie the isotope mass separates now NAMES too (``F[C@@](Cl)([2H])[3H]``
    -> R).  It stays SOUND: a centre whose four ligands are NOT separated by a BUILT rule -- a tie needing Rule
    1b/3/4/5, a Rule-2 pairing made ambiguous by Rule-1a-tied siblings or an unknown mass, or a true constitutional
    duplicate (a false centre) -- is a NAMED DEFERRAL and gets NO label, because a guessed R/S is worse than
    none. Bounded neutral C/N/O/S mancude rings (>=2 Kekule structures: benzene, pyridine) use exact atomic-number
    averaging of multiple-bond duplicates (:func:`_cip_mancude`), equally for aromatic and explicit Kekule
    spellings; a LOCALIZED unsaturated ring (a UNIQUE Kekule structure -- cyclopropene, cyclohexene,
    cyclopentadiene, a cyclic enol ether, a localized fused bicyclic) is RELEASED to the ordinary digraph and
    NAMES (ROUND 33), when it is the ONLY ring on the centre.  Charged, exocyclic-multiple, and mixed
    partially-saturated-fused ring systems retain a lazy deferral boundary; a released ring ranked against
    ANOTHER ring, or an isotope-labelled ring tied under Rule 1a, DEFERS (Rule-1b / clean-mancude territory);
    a ranking decided by atomic number before reaching a boundary still names. A ring
    stereocentre (``_on_cycle``) and a non-four-coordinate marked centre also defer, as before.
    On the distinct-atomic-number slice the digraph decides at sphere 0, so this is byte-identical to the prior
    ``sorted(z, reverse=True)`` ranks there -- a strict extension, never a change.

    The parity -> R/S sign convention is ANCHORED to a known truth, not memory: L-alanine (textbook (S)) has
    neighbour order [N, H, CH3, COOH] with CIP ranks [1,4,3,2] and ``@@`` (sense bit 1), so
    ``perm_parity([1,4,3,2]) ^ 1 == 0`` -- hence handedness 0 -> S, 1 -> R.  Cross-checked: ``[C@H](F)(Cl)Br``
    computes handedness 0 -> S.  (This is the SAME ``perm_parity ^ sense`` handedness :func:`_perceive_configuration`
    uses for IDENTITY, only with the ordering key swapped from 1-WL colour to CIP atomic-number priority.)
    """
    marked = [a for a in range(len(atoms)) if atoms[a].chirality]
    if not marked:
        return ()
    work = [list(b) for b in bonds]
    _kekulize_in_place(atoms, work, charge)
    filled_atoms, filled_bonds = _fill_hydrogens(atoms, work)     # heavy indices 0..n-1 preserved; H appended after
    n = len(atoms)
    # CIP Rule-2 mass, keyed by filled-atom index (ROUND 28): heavy atoms 0..n-1 carry their parsed isotope (0 =
    # unspecified -> the standard weight); the implicit H's appended after n are unspecified natural H.
    mass = [_cip_mass(filled_atoms[i], atoms[i].isotope if i < n else 0) for i in range(len(filled_atoms))]
    neighbours: dict[int, list[int]] = {i: [] for i in range(len(filled_atoms))}
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(filled_atoms))}
    for b in filled_bonds:
        neighbours[b.i].append(b.j)
        neighbours[b.j].append(b.i)
        adj[b.i].append((b.j, b.order))                          # ordered adjacency for the CIP digraph (phantom counts)
        adj[b.j].append((b.i, b.order))
    aromatic, mancude, released = _cip_mancude(atoms, work, adj)
    labels: list[str] = []
    for a in marked:                                             # SAME scope as _perceive_configuration (acyclic, 4-coord)
        if _on_cycle(a, neighbours, len(filled_atoms)):
            continue
        incoming = [bd[0] for bd in bonds if bd[1] == a]
        outgoing = [bd[1] for bd in bonds if bd[0] == a]
        h_neighbours = [j for j in neighbours[a] if j >= n and filled_atoms[j] == "H"]
        if len(incoming) > 1:
            continue
        written = ([incoming[0]] if incoming else []) + h_neighbours + outgoing
        if len(written) != 4:
            continue
        if any(ATOMIC_NUMBER.get(filled_atoms[x]) is None for x in written):
            continue                                             # a non-periodic-table element -> out of scope
        ranks = _cip_ranks(written, a, adj, filled_atoms, mass, aromatic, mancude, released)
        if ranks is None:
            continue                                             # Rule 1a+2 leave a genuine tie -> NAMED DEFERRAL (never guess)
        handedness = _perm_parity(ranks) ^ (0 if atoms[a].chirality == 1 else 1)
        labels.append("S" if handedness == 0 else "R")          # anchored to L-alanine = S (see docstring)
    return tuple(sorted(labels))


def cip_labels(text: str) -> tuple[str, ...]:
    """The CIP R/S names of ``text``'s soundly-nameable acyclic stereocentres, sorted; ``()`` if none.

    Priority comes from the general CIP **Rule 1a** hierarchical digraph -- breadth-first, branch-by-branch, with
    duplicate/phantom atoms for multiple bonds and ring closures (ROUND 20) -- plus CIP **Rule 2** (mass number,
    ROUND 28) as its own pass at the Rule-1a tie hand-off, so the common same-element case (amino acids, sugars,
    secondary/tertiary carbons) AND a same-Z isotope tie are now NAMED, not deferred.  A LOCALIZED unsaturated
    ring substituent (a unique Kekule structure -- cyclopropene, cyclohexene, cyclopentadiene, a cyclic enol
    ether, a localized fused bicyclic) is also NAMED (ROUND 33) when it is the only ring on the centre.  A centre
    the BUILT rules (1a, 2) cannot fully order (a tie needing Rule 1b/3/4/5, a Rule-2 pairing made ambiguous by
    Rule-1a-tied siblings or an unknown mass), one whose ranking depends on an unsupported/delocalized ring, a
    released ring ranked against ANOTHER ring or an isotope-labelled ring tied under Rule 1a (Rule-1b territory),
    an exocyclic-double or aromatic-fused-to-saturated ring, a ring stereocentre, or a non-four-coordinate marked
    centre contributes NO name -- a named deferral, never a guessed/unsound label.  Raises
    :class:`SmilesError` on a malformed/out-of-scope SMILES, like the parser.  See :func:`_cip_labels` for the
    method and its L-alanine = S sign-convention anchor."""
    if not isinstance(text, str):
        raise SmilesError("SMILES input must be a string")
    stripped = text.strip()
    if not stripped:
        raise SmilesError("empty SMILES")
    atoms, bonds = _parse_skeleton(stripped)
    charge = sum(a.charge for a in atoms)
    return _cip_labels(atoms, bonds, charge)


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
    # Chirality PERCEPTION (ID-STEREO-01), the isotope work's named deferral: a canonical parity descriptor for the
    # perceivable acyclic tetrahedral centres (None when none), computed BEFORE _build_molecule mutates bond orders.
    # perception_complete (ID-STEREO-02) is True iff NO marked centre was scoped out -- the fail-closed match-layer signal.
    configuration_digest, perception_complete = _perceive_configuration(atoms, bonds, charge)
    # CIP R/S NAMES (ID-STEREO-01) for the soundly-nameable centres -- computed on the SAME pristine atoms/bonds, BEFORE
    # _build_molecule mutates bond orders (``_cip_labels`` copies ``bonds`` internally, so the caller's list is untouched).
    cip = _cip_labels(atoms, bonds, charge)
    double_bond_stereo = ("/" in stripped or "\\" in stripped)
    molecule = _build_molecule(atoms, bonds, charge)
    features = SmilesFeatures(
        isotopes=tuple(sorted({a.isotope for a in atoms if a.isotope})),
        tetrahedral_stereo=any(a.chirality for a in atoms),
        double_bond_stereo=double_bond_stereo,
        charged_atoms=sum(1 for a in atoms if a.charge != 0),
        net_charge=charge,
        isotopic_digest=isotopic_digest,
        configuration_digest=configuration_digest,
        # CONFIGURATION is fully perceived only when EVERY marked tetrahedral centre yielded a descriptor AND there is
        # no unperceived double-bond (E/Z) stereo; otherwise some real configuration is unknown, so it must not reduce
        # to a match layer (ID-STEREO-02 fail-closed).
        configuration_complete=perception_complete and not double_bond_stereo,
        cip_labels=cip,
        stereocentres_marked=sum(1 for a in atoms if a.chirality),
    )
    return molecule, features
