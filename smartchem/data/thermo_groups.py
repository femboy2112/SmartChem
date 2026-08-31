"""The DERIVATION engine: Benson group additivity for gas-phase ΔfH°(298) and S°(298).

This is rung 2 of the derivation layer -- the answer to "stop dumping *derivable* physical values to
``UNKNOWN``".  Sourced molecular thermodynamic data (:mod:`smartchem.data.thermo` /
:mod:`.thermo_extended`) covers a few dozen species; ab-initio (PySCF) walls at ~3 heavy atoms.  Group
additivity is the known-physics bridge across that gap: a molecule's ideal-gas standard enthalpy of
formation and standard molar entropy are estimated as the SUM of contributions from each heavy atom's local
bonding environment (its "Benson group"), plus a rotational-symmetry entropy correction.  That is
*reproducing known chemistry* -- the same method used to build every combustion mechanism in the field --
not inventing new physics ([[known-physics-not-new-physics]]).  A value it produces is graded ``DERIVED``
(in-scheme groups) or ``PREDICTED`` (a group assigned by analogy), always WITH AN UNCERTAINTY BAND, never a
bare number pretending to measurement precision.

Two hard boundaries, stated loudly
-----------------------------------
* **Gas phase only.**  Group additivity yields IDEAL-GAS values.  A condensed-phase (liquid/crystal) ΔfH°/S°
  needs a separate sublimation/vaporisation correction (ΔsubH/ΔsubS) -- a different rung.  Every estimate
  here is ``phase="gas"``; feasibility must not silently mix a derived-gas record with a sourced-condensed
  one (the phase trap).  This is exactly why the paracetamol litmus wall -- a missing *crystal* S° -- is not
  fully closed by this module: the gas estimate closes the GAS-phase ΔG, the gas->crystal correction remains
  open.
* **Off-coverage is a loud ``None``, never a guess.**  :func:`estimate_thermo` returns ``None`` (naming the
  exact missing group) when any heavy atom's environment is not in the sourced table.  It never fabricates a
  group value to force an answer.

Provenance discipline (the anti-poisoning rule, [[a-reaction-key-by-formula-borrows-a-rate]])
--------------------------------------------------------------------------------------------
Every group value here was FETCHED from the open, MIT-licensed RMG-database group-additivity tables
(github.com/ReactionMechanismGenerator/RMG-database, ``input/thermo/groups/group.py``) -- the reference
implementation the combustion-kinetics field uses -- with the RMG ``shortDesc`` (its own provenance tag)
carried per record, NOT recalled from training.  The classic ``BENSON``-tagged values (Benson,
*Thermochemical Kinetics*, 1976; Cohen & Benson, *Chem. Rev.* 1993) form the internally-consistent core;
where a group's only value is a later CBS-QB3 quantum refit or an RMG thermo-library fit, it is tiered
``EXPERIMENTAL`` and the mixing is validated by molecular calibration (below).  Units are read per-record
(the source file mixes kcal/mol and kJ/mol) and converted to SI here once.

The instrument rule (this repo's sacred discipline)
---------------------------------------------------
Code that estimates a physical quantity is a scientific instrument; it must recover KNOWN values before its
novel outputs are believed.  :mod:`tests.test_thermo_groups` calibrates this estimator against sourced
gas-phase molecular ΔfH°/S° (ethane, propane, benzene, methanol, ethanol, acetone, ...): the group sum plus
the symmetry correction reproduces e.g. methanol ΔfH° to <1 kJ/mol and S° to <0.5 J/mol/K, and benzene S° to
<0.5 J/mol/K.  A group value that fails calibration is wrong and gets fixed or dropped; the calibration IS
the cross-check that the mixed-provenance ensemble is self-consistent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..category import Molecule

__all__ = [
    "GroupTier",
    "BensonGroup",
    "BENSON_GROUPS",
    "RingTier",
    "RingStrain",
    "RING_STRAIN",
    "GroupThermoEstimate",
    "assign_groups",
    "estimate_thermo",
    "R_J_PER_MOL_K",
]

#: Molar gas constant (J/mol/K) -- the SI-exact value, used for the -R ln(σ) symmetry entropy correction.
R_J_PER_MOL_K = 8.314462618
#: Thermochemical calorie -> joule (exact, by definition), the unit conversion for the kcal/cal source values.
_CAL_TO_J = 4.184


class GroupTier(str, Enum):
    """How a group's value is sourced -- sets its uncertainty band and whether it grades DERIVED or PREDICTED.

    * ``ESTABLISHED`` -- a classic ``BENSON``-tagged additive value, internally consistent and confirmed by
      the molecular calibration suite.
    * ``EXPERIMENTAL`` -- present in RMG but from a later CBS-QB3 quantum refit or a thermo-library fit
      (a single, still-sourced bearing); wider band.
    * ``ASSIGNED`` -- no direct value; taken by analogy from a structurally similar group (RMG's own
      documented "Assigned ..." practice).  An estimate using one grades ``PREDICTED``, not ``DERIVED``.
    """

    ESTABLISHED = "ESTABLISHED"
    EXPERIMENTAL = "EXPERIMENTAL"
    ASSIGNED = "ASSIGNED"


#: Per-tier 1σ uncertainty contribution of ONE group, (ΔfH° kJ/mol, S° J/mol/K), combined in quadrature.
_TIER_BAND: dict[GroupTier, tuple[float, float]] = {
    GroupTier.ESTABLISHED: (4.0, 4.0),
    GroupTier.EXPERIMENTAL: (8.0, 6.0),
    GroupTier.ASSIGNED: (12.0, 10.0),
}


@dataclass(frozen=True)
class BensonGroup:
    """One Benson group's SOURCED ideal-gas contribution: ΔfH°(298) kJ/mol and S°(298) J/mol/K.

    ``label`` is this repo's canonical group name (centre atom type + sorted heavy-ligand types + H count,
    e.g. ``C-(C)(H)3``, ``CB-(O)``, ``N-(CB)(CO)(H)``); :func:`assign_groups` emits exactly these labels.
    ``rmg_label`` is the source key in the RMG database, kept for traceability.
    """

    label: str
    dhf_kj_per_mol: float
    s_j_per_mol_k: float
    tier: GroupTier
    rmg_label: str
    provenance: str
    #: Optional (ΔfH° kJ/mol, S° J/mol/K) uncertainty override, used when a group's real transferability is
    #: worse than its tier implies -- e.g. a group calibrated in one environment that transfers poorly to
    #: another (the branched tertiary-amine N, whose methyl-armed fit is ~19 kJ off for ethyl arms).
    band: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("label must be a non-empty string")
        if isinstance(self.dhf_kj_per_mol, bool) or not isinstance(self.dhf_kj_per_mol, (int, float)):
            raise TypeError("dhf_kj_per_mol must be a real number")
        if isinstance(self.s_j_per_mol_k, bool) or not isinstance(self.s_j_per_mol_k, (int, float)):
            raise TypeError("s_j_per_mol_k must be a real number")
        if not isinstance(self.tier, GroupTier):
            raise TypeError("tier must be a GroupTier")


def _kcal(dhf_kcal: float, s_cal: float) -> tuple[float, float]:
    """Convert a (kcal/mol, cal/mol/K) source pair to SI (kJ/mol, J/mol/K)."""
    return round(dhf_kcal * _CAL_TO_J, 3), round(s_cal * _CAL_TO_J, 3)


# =====================================================================================================
# The sourced group table.  Values FETCHED from RMG-database input/thermo/groups/group.py (MIT licence);
# the RMG source label + its shortDesc tag are recorded per row.  kcal/cal rows are converted via _kcal();
# rows whose RMG value is natively kJ/J are written directly.  A group whose RMG entry carried S298=0 (a
# not-yet-fitted placeholder) is NOT stored as zero -- it is either omitted (a loud gap) or ASSIGNED from a
# real analogue, never given a fabricated zero entropy.
# =====================================================================================================
_E = GroupTier.ESTABLISHED
_X = GroupTier.EXPERIMENTAL
_A = GroupTier.ASSIGNED
_RMG = "RMG-database input/thermo/groups/group.py (MIT); "

BENSON_GROUPS: tuple[BensonGroup, ...] = (
    # -- sp3 carbon (alkane skeleton) -- classic BENSON, kcal/cal ------------------------------------
    BensonGroup("C-(C)(H)3", *_kcal(-10.2, 30.41), _E, "Cs-CsHHH", _RMG + "'Cs-CsHHH BENSON'"),
    BensonGroup("C-(C)2(H)2", *_kcal(-4.93, 9.42), _E, "Cs-CsCsHH", _RMG + "'Cs-CsCsHH BENSON'"),
    BensonGroup("C-(C)3(H)", *_kcal(-1.9, -12.07), _E, "Cs-CsCsCsH", _RMG + "'Cs-CsCsCsH BENSON'"),
    BensonGroup("C-(C)4", *_kcal(0.5, -35.1), _E, "Cs-CsCsCsCs", _RMG + "'Cs-CsCsCsCs BENSON'"),
    # methyl on an aromatic / carbonyl / alkene / oxygen centre.  RMG assigns the aromatic & alkene methyl
    # to the plain Cs-CsHHH value (BENSON practice); the carbonyl- and oxy-methyl carry their own refit.
    BensonGroup("C-(CB)(H)3", *_kcal(-10.2, 30.41), _E, "Cs-CbHHH", _RMG + "'Cs-CbHHH BENSON (Assigned Cs-CsHHH)'"),
    BensonGroup("C-(Cd)(H)3", *_kcal(-10.2, 30.41), _A, "Cs-CsHHH", _RMG + "alkene methyl assigned Cs-CsHHH (BENSON practice)"),
    BensonGroup("C-(CO)(H)3", -42.9, 127.12, _X, "Cs-(Cds-O2d)HHH", _RMG + "'Derived from CBS-QB3' (kJ/J native)"),
    BensonGroup("C-(O)(H)3", -42.9, 127.12, _X, "Cs-OsHHH", _RMG + "'Derived from CBS-QB3' (kJ/J native)"),
    # carbons bearing a single-bonded oxygen (the CH2/CH of primary & secondary alcohols, ethers) --------
    BensonGroup("C-(C)(O)(H)2", -34.3, 37.65, _X, "Cs-CsOsHH", _RMG + "'Derived from CBS-QB3' (kJ/J native)"),
    BensonGroup("C-(C)2(O)(H)", -25.1, -52.05, _X, "Cs-CsCsOsH", _RMG + "'Derived from CBS-QB3' secondary-alcohol CH (kJ/J native)"),
    # -- alkene (sp2) carbon -- classic BENSON --------------------------------------------------------
    BensonGroup("Cd-(H)2", *_kcal(6.26, 27.61), _E, "Cds-CdsHH", _RMG + "'Cd-HH BENSON'"),
    BensonGroup("Cd-(C)(H)", *_kcal(8.59, 7.97), _E, "Cds-CdsCsH", _RMG + "'Cd-CsH BENSON'"),
    BensonGroup("Cd-(C)2", *_kcal(10.34, -12.7), _E, "Cds-CdsCsCs", _RMG + "'Cd-CsCs BENSON'"),
    # -- aromatic (benzene) carbon -- classic BENSON.  The two ring bonds are IMPLICIT in the CB value;
    #    the single listed ligand is the exocyclic substituent (or H). ---------------------------------
    BensonGroup("CB-(H)", *_kcal(3.3, 11.53), _E, "Cb-H", _RMG + "'Cb-H BENSON'"),
    BensonGroup("CB-(C)", *_kcal(5.51, -7.69), _E, "Cb-Cs", _RMG + "'Cb-Cs BENSON'"),
    BensonGroup("CB-(O)", *_kcal(-0.9, -10.2), _E, "Cb-O2s", _RMG + "'Cb-O BENSON'"),
    BensonGroup("CB-(N)", *_kcal(-0.5, -9.69), _X, "Cb-N3s", _RMG + "Cb-N3s (RMG, untagged)"),
    # -- oxygen (hydroxyl / phenol / ether).  Hydroxyl uses the BENSON value (-37.9), NOT RMG's default
    #    CBS-QB3 O2s-CsH (-39.5 kcal) which is inconsistent with the BENSON core -- consistency over the
    #    newer refit, confirmed by the methanol calibration. --------------------------------------------
    BensonGroup("O-(C)(H)", *_kcal(-37.9, 29.1), _E, "O2s-CbH", _RMG + "'O-CbH BENSON (Assigned O-CsH)' (BENSON hydroxyl, not the CBS-QB3 default)"),
    BensonGroup("O-(CB)(H)", *_kcal(-37.9, 29.1), _E, "O2s-CbH", _RMG + "'O-CbH BENSON (Assigned O-CsH)'"),
    BensonGroup("O-(C)2", -98.6, 38.61, _X, "O2s-CsCs", _RMG + "'Derived from CBS-QB3' ether (kJ/J native)"),
    # -- carbonyl carbon (the =O is ABSORBED into the group, Benson convention) ------------------------
    BensonGroup("CO-(H)2", *_kcal(-25.95, 53.68), _E, "Cds-OdHH", _RMG + "'CO-HH BENSON' (formaldehyde)"),
    BensonGroup("CO-(C)(H)", -123.4, 145.46, _X, "Cds-OdCsH", _RMG + "'Derived from CBS-QB3' aldehyde (kJ/J native)"),
    BensonGroup("CO-(C)2", -132.2, 61.78, _X, "Cds-OdCsCs", _RMG + "'Derived from CBS-QB3' ketone (kJ/J native)"),
    BensonGroup("CO-(C)(O)", -222.0, 43.52, _X, "Cds-OdCsOs", _RMG + "'Derived from CBS-QB3' ester/acid carbonyl (kJ/J native)"),
    BensonGroup("CO-(C)(N)", *_kcal(-38.3664, 12.3176), _X, "Cds-OdN3sCs", _RMG + "'Derived from RMG Thermo Libraries' amide carbonyl"),
    # -- nitrogen (amine / amide) ---------------------------------------------------------------------
    BensonGroup("N-(C)(H)2", *_kcal(0.864147, 28.389), _X, "N3s-CsHH", _RMG + "'Derived from RMG Thermo Libraries' primary amine"),
    BensonGroup("N-(CB)(H)2", *_kcal(4.8, 29.71), _X, "N3s-CbHH", _RMG + "N3s-CbHH (RMG) aniline nitrogen"),
    BensonGroup("N-(C)(CO)(H)", *_kcal(-1.80039, 8.54505), _X, "N3s-(CO)CsH", _RMG + "'Derived from RMG Thermo Libraries' aliphatic amide N"),
    # aromatic amide nitrogen: its RMG entry (N3s-(CO)CbH) carries a real ΔfH° (0.4 kcal) but S298=0 (a
    # not-yet-fitted placeholder).  We keep the real ΔfH° and ASSIGN the entropy from the aliphatic amide N
    # -- so paracetamol's amide N resolves as PREDICTED-with-wide-band, never a fabricated zero-entropy.
    BensonGroup("N-(CB)(CO)(H)", *_kcal(0.4, 8.54505), _A, "N3s-(CO)CbH",
                _RMG + "ΔfH° from N3s-(CO)CbH (0.4 kcal); S° ASSIGNED from N-(C)(CO)(H)=8.54505 cal (its RMG S298=0 is a placeholder, refused)"),
    # -- aliphatic amine coverage (rung B): closes ethylamine/propylamine/di-/tri-methylamine; SI values
    #    fetched from RMG group.py and CROSS-CHECKED against sourced gas ΔfH° (n-propylamine residual 0.45 kJ,
    #    trimethylamine 1.3 kJ, dimethylamine 2.1 kJ -- NIST/CCCBDB). ------------------------------------
    BensonGroup("C-(C)(N)(H)2", -10.93, 41.17, _E, "Cs-CsN3sHH", _RMG + "amine CH2; xcheck n-propylamine 0.45 kJ"),
    BensonGroup("C-(N)(H)3", -23.76, 132.15, _E, "Cs-N3sHHH", _RMG + "N-methyl; xcheck trimethylamine 1.3 kJ"),
    BensonGroup("N-(C)2(H)", 30.65, 31.89, _A, "N3s-CsCsH",
                _RMG + "secondary amine N; methyl-armed calibration transfers poorly to non-methyl arms -- PREDICTED, wide band", band=(16.0, 16.0)),
    BensonGroup("N-(C)3", 48.86, -66.58, _A, "N3s-CsCsCs",
                _RMG + "tertiary amine N; methyl-armed fit is ~19 kJ off for ethyl arms (red-team HIGH) -- PREDICTED, wide band", band=(20.0, 18.0)),
    BensonGroup("C-(C)2(N)(H)", 4.88, -51.73, _X, "Cs-CsCsN3sH", _RMG + "amine CH; single-compound fit (n=9, isopropylamine) -- EXPERIMENTAL"),
    # -- carboxylic-acid / ester coverage (rung B): closes acetic/formic acid, methyl/ethyl acetate;
    #    O-(CO)(H) closes acetic acid to 2.9 kJ and formic acid to 1.6 kJ (NIST gas). --------------------
    BensonGroup("O-(CO)(H)", -165.20, 125.32, _E, "O2s-(Cds-O2d)H", _RMG + "acid/ester hydroxyl O; xcheck acetic acid 2.9 kJ"),
    BensonGroup("CO-(O)(H)", -211.80, 124.04, _E, "Cds-OdOsH", _RMG + "carboxyl carbon; xcheck formic acid 1.6 kJ"),
    BensonGroup("O-(C)(CO)", -102.20, 45.71, _E, "O2s-(Cds-O2d)Cs", _RMG + "ester oxygen (canonical C-before-CO order); xcheck methyl acetate 0.0 kJ"),
    BensonGroup("C-(C)(CO)(H)2", -21.50, 40.32, _X, "Cs-Cs(CO)HH", _RMG + "CH2 alpha to carbonyl"),
    # -- amide coverage (rung B): the aliphatic amides beyond the aromatic-amide N already present.
    #    Several are low-n RMG-library fits (EXPERIMENTAL, wide band); none carry a placeholder-zero entropy.
    BensonGroup("CO-(N)(H)", -160.27, 136.98, _X, "Cds-OdN3sH", _RMG + "formamide-type amide carbonyl"),
    BensonGroup("N-(CO)(H)2", -37.06, 110.38, _X, "N3s-(CO)HH", _RMG + "primary-amide N"),
    BensonGroup("N-(CO)2(H)", 1.49, 17.59, _A, "N3s-(CO)(CO)H", _RMG + "imide N; single-point fit (n=1, +-20 kJ) -- ASSIGNED-grade (PREDICTED), too rough for DERIVED"),
    BensonGroup("N-(C)2(CO)", 20.03, -62.90, _A, "N3s-(CO)CsCs", _RMG + "tertiary-amide N; n=2 fit (+-20 kJ) -- ASSIGNED-grade (PREDICTED)"),
    BensonGroup("CO-(N)2", -163.70, 51.22, _X, "CO-N3sN3sOd", _RMG + "urea-type carbonyl (two amide N)"),
)


class RingTier(str, Enum):
    """Whether a ring-strain correction is molecule-calibrated (ESTABLISHED) or only an exact RMG transcription
    with no molecular cross-check available here (EXPERIMENTAL, wider band)."""

    ESTABLISHED = "ESTABLISHED"
    EXPERIMENTAL = "EXPERIMENTAL"


@dataclass(frozen=True)
class RingStrain:
    """One ring's SOURCED strain correction: the ΔfH°/S° a ring adds ON TOP of its atom-centred groups.

    ``key`` is the ring classifier name (:func:`_classify_ring`); ``dhf_kj_per_mol`` / ``s_j_per_mol_k`` are
    the corrections in SI.  Applied as ΔfH° += strain.ΔfH, S° += strain.S (then the usual − R ln σ)."""

    key: str
    dhf_kj_per_mol: float
    s_j_per_mol_k: float
    tier: RingTier
    provenance: str


_RE = RingTier.ESTABLISHED
_RX = RingTier.EXPERIMENTAL
_RRING = "RMG-database input/thermo/groups/ring.py (MIT); "

#: Ring-strain corrections, DERIVED to be CONSISTENT WITH THIS ENGINE'S GROUP BASIS.  An RMG ring correction
#: is fit to RMG's own group values; mixing it with this table's (Benson/CBS-QB3-blended) groups is unsound
#: -- the adversarial red-team proved it: RMG's Tetrahydrofuran ring-S (88.54) with this basis gave S°(THF)
#: 26 J/mol/K too low, outside band (it wrongly put THF's entropy BELOW cyclopentane's).  So each correction
#: here is instead DERIVED as (sourced gas molecular ΔfH°/S°) − (this engine's atom-group sum) [+ R ln σ for
#: S] from the workflow-verified anchors -- reproducing the parent ring EXACTLY and transferring consistently
#: to substituted rings.  ΔfH matches its old RMG value (the C/H groups already agreed); the S° values are the
#: corrected ones (THF 114.73 not 88.54, cyclohexane 82.37 not 75.85, ...).  The three UNSATURATED-ring
#: corrections keep their RMG transcription (no molecular anchor + they need the alkene Cd groups) -> EXPERIMENTAL.
_RDER = _RRING + "ring correction DERIVED from sourced gas molecular ΔfH°/S° minus this engine's group sum"
RING_STRAIN: tuple[RingStrain, ...] = (
    RingStrain("Cyclopropane", 115.18, 134.04, _RE, f"{_RDER}; anchor cyclopropane 53.30/237.38"),
    RingStrain("Cyclobutane", 110.91, 124.04, _RE, f"{_RDER}; anchor cyclobutane 28.40/264.40"),
    RingStrain("Cyclopentane", 26.73, 114.94, _RE, f"{_RDER}; anchor cyclopentane -76.40/292.86"),
    RingStrain("Cyclohexane", 0.66, 82.37, _RE, f"{_RDER}; anchor cyclohexane -123.10/298.19"),
    RingStrain("Ethylene_oxide", 114.57, 134.85, _RE, f"{_RDER}; anchor oxirane -52.63/243.00"),
    RingStrain("Oxetane", 107.29, 123.87, _RE, f"{_RDER}; anchor oxetane -80.54/271.43"),
    RingStrain("Tetrahydrofuran", 24.25, 114.73, _RE, f"{_RDER}; anchor THF -184.20/301.70"),
    RingStrain("Cyclohexene", 4.89, 88.75, _RX, _RRING + "'Cyclohexene ring BENSON'; no molecular anchor here"),
    RingStrain("Cyclopentene", 24.98, 108.07, _RX, _RRING + "'Cyclopentene ring BENSON'; no molecular anchor here"),
    RingStrain("Cyclobutene", 124.85, 124.97, _RX, _RRING + "'Cyclobutene ring BENSON'; no molecular anchor here"),
)

_RING_BY_KEY: dict[str, RingStrain] = {r.key: r for r in RING_STRAIN}

_GROUP_BY_LABEL: dict[str, BensonGroup] = {g.label: g for g in BENSON_GROUPS}

# Priority order for rendering a group's heavy ligands into a canonical label (H is always rendered last).
_LIGAND_PRIORITY: dict[str, int] = {"C": 0, "Cd": 1, "Ct": 2, "CB": 3, "CO": 4, "O": 5, "N": 6}


# =====================================================================================================
# Structural analysis of the bond graph (hydrogens are EXPLICIT atom nodes; see smiles._fill_hydrogens).
# =====================================================================================================
def _neighbours(mol: Molecule) -> list[list[tuple[int, int]]]:
    """Adjacency as ``[(neighbour_index, bond_order), ...]`` per atom position."""
    adj: list[list[tuple[int, int]]] = [[] for _ in mol.atoms]
    for b in mol.bonds:
        adj[b.i].append((b.j, b.order))
        adj[b.j].append((b.i, b.order))
    return adj


def _aromatic_rings(mol: Molecule, adj: list[list[tuple[int, int]]]) -> tuple[frozenset[int], frozenset[frozenset[int]], int]:
    """Detect benzene-type aromatic carbons and their ring bonds from the Kekulé encoding.

    Scope: isolated 6-membered all-carbon rings whose bonds alternate single/double (a Kekulé benzene ring),
    which is the aromatic case in the litmus (benzene, phenol, paracetamol).  Returns the set of aromatic
    carbon indices, the set of aromatic ring bonds (each an unordered ``frozenset{i, j}``), and the number of
    distinct aromatic rings detected.  A carbon in a ring that is NOT a clean alternating 6-carbocycle is left
    non-aromatic -- honest under-detection, never a wrong aromatic label.
    """
    carbons = [i for i, s in enumerate(mol.atoms) if s == "C"]
    cset = set(carbons)
    aromatic: set[int] = set()
    ring_bonds: set[frozenset[int]] = set()
    seen_rings: set[frozenset[int]] = set()

    def dfs(start: int, current: int, path: list[int]) -> None:
        for j, _order in adj[current]:
            if j not in cset:
                continue
            if j == start and len(path) == 6:
                ring = frozenset(path)
                if len(ring) == 6:
                    seen_rings.add(ring)
                continue
            if j in path or len(path) >= 6:
                continue
            path.append(j)
            dfs(start, j, path)
            path.pop()

    for c in carbons:
        dfs(c, c, [c])

    num_rings = 0
    for ring in seen_rings:
        # Kekulé test: within the ring, every carbon has exactly one order-2 ring bond and one order-1.
        ok = True
        this_ring_bonds: set[frozenset[int]] = set()
        for i in ring:
            ring_orders = [o for (j, o) in adj[i] if j in ring]
            if sorted(ring_orders) != [1, 2]:
                ok = False
                break
            for j, _o in adj[i]:
                if j in ring:
                    this_ring_bonds.add(frozenset((i, j)))
        if ok:
            aromatic |= set(ring)
            ring_bonds |= this_ring_bonds
            num_rings += 1
    return frozenset(aromatic), frozenset(ring_bonds), num_rings


def _find_rings(mol: Molecule, adj: list[list[tuple[int, int]]]) -> list[list[int]]:
    """All simple cycles up to length 7 among heavy atoms, deduped by atom-set, returned in cycle order."""
    heavy = [i for i, s in enumerate(mol.atoms) if s != "H"]
    hset = set(heavy)
    seen: set[frozenset[int]] = set()
    rings: list[list[int]] = []

    def dfs(start: int, cur: int, path: list[int]) -> None:
        for j, _o in adj[cur]:
            if j not in hset:
                continue
            if j == start and len(path) >= 3:
                key = frozenset(path)
                if key not in seen:
                    seen.add(key)
                    rings.append(list(path))
                continue
            if j in path or len(path) >= 7 or j <= start:
                continue
            path.append(j)
            dfs(start, j, path)
            path.pop()

    for s in heavy:
        dfs(s, s, [s])
    return rings


def _ring_edges(ring: list[int]) -> frozenset[frozenset[int]]:
    return frozenset(frozenset((ring[k], ring[(k + 1) % len(ring)])) for k in range(len(ring)))


def _select_sssr(rings: list[list[int]], cycle_rank: int) -> list[list[int]] | None:
    """The smallest-set-of-smallest-rings: greedily take smallest rings that each add a new edge until the
    cycle space is spanned.  Returns None if fewer than ``cycle_rank`` independent rings are found (a ring
    larger than the search cap went uncaught -> off-coverage, not silently ignored)."""
    selected: list[list[int]] = []
    covered: set[frozenset[int]] = set()
    for r in sorted(rings, key=len):
        e = _ring_edges(r)
        if not e <= covered:
            selected.append(r)
            covered |= e
        if len(selected) == cycle_rank:
            return selected
    return selected if len(selected) == cycle_rank else None


def _classify_ring(mol: Molecule, adj: list[list[tuple[int, int]]], ring: list[int]) -> str | None:
    """Map a NON-aromatic ring to a RING_STRAIN key (size + element multiset + ring-double-bond count), or
    None if it is a ring type with no sourced strain correction.

    Keys on the RING atoms only, so a SUBSTITUTED ring borrows its parent carbocycle/heterocycle's strain
    correction -- the standard Benson approximation: cyclohexanone/methylcyclohexane use the Cyclohexane
    correction, a γ-lactone the Tetrahydrofuran one (the substituent's and an in-ring carbonyl's effect on
    strain is left to the atom groups + the uncertainty band, which covers it on the tested cases; a ring the
    band could NOT cover would be a real gap to add here).  An in-ring heteroatom pattern with no tabled
    correction (a 6-ring lactone/lactam, 1,4-dioxane, ...) returns None -- off-coverage, not a wrong strain."""
    size = len(ring)
    ringset = set(ring)
    # A ring atom with an EXOCYCLIC double bond (an in-ring carbonyl -> ketone/lactone/lactam ring, or an
    # exocyclic alkene) has a strain the parent carbocycle/heterocycle correction does NOT capture -- for a
    # strained ring the error is huge and sign-flipping (cyclopropanone: parent Cyclopropane strain +115 vs
    # its true ~+191, a 76 kJ/mol confident-wrong-answer, red-team HIGH). Refuse it: off-coverage, not a guess.
    for i in ring:
        for j, o in adj[i]:
            if j not in ringset and o >= 2:
                return None
    elems = "".join(sorted(mol.atoms[i] for i in ring))
    ndouble = 0
    for i in ring:
        for j, o in adj[i]:
            if j in ringset and j > i and o == 2:
                ndouble += 1
    table = {
        (3, "CCC", 0): "Cyclopropane", (3, "CCO", 0): "Ethylene_oxide",
        (4, "CCCC", 0): "Cyclobutane", (4, "CCCC", 1): "Cyclobutene", (4, "CCCO", 0): "Oxetane",
        (5, "CCCCC", 0): "Cyclopentane", (5, "CCCCC", 1): "Cyclopentene", (5, "CCCCO", 0): "Tetrahydrofuran",
        (6, "CCCCCC", 0): "Cyclohexane", (6, "CCCCCC", 1): "Cyclohexene",
    }
    return table.get((size, elems, ndouble))


def _ring_analysis(
    mol: Molecule, adj: list[list[tuple[int, int]]], aromatic: frozenset[int]
) -> tuple[str, ...] | None:
    """The RING_STRAIN keys for a molecule's non-aromatic rings, or None (off-coverage) if any ring is a
    type with no sourced correction, the rings are fused (polycyclic strain not tabulated), or a ring larger
    than the search cap went uncaught.  An acyclic molecule -- or one whose only rings are benzene aromatics
    -- returns ``()`` (no correction, on-coverage)."""
    heavy = [i for i, s in enumerate(mol.atoms) if s != "H"]
    hbonds = sum(1 for b in mol.bonds if mol.atoms[b.i] != "H" and mol.atoms[b.j] != "H")
    cycle_rank = hbonds - len(heavy) + 1
    if cycle_rank <= 0:
        return ()
    sssr = _select_sssr(_find_rings(mol, adj), cycle_rank)
    if sssr is None:
        return None  # a ring bigger than the search cap -> off-coverage
    nonarom = [r for r in sssr if not all(i in aromatic for i in r)]
    # fused rings (any two non-aromatic rings share an atom) -> polycyclic strain not tabulated
    for a in range(len(nonarom)):
        for b in range(a + 1, len(nonarom)):
            if set(nonarom[a]) & set(nonarom[b]):
                return None
    keys: list[str] = []
    for r in nonarom:
        key = _classify_ring(mol, adj, r)
        if key is None or key not in _RING_BY_KEY:
            return None
        keys.append(key)
    return tuple(keys)


def _h_count(adj_i: list[tuple[int, int]], atoms: tuple[str, ...]) -> int:
    return sum(1 for (j, _o) in adj_i if atoms[j] == "H")


def _center_type(mol: Molecule, i: int, adj: list[list[tuple[int, int]]], aromatic: frozenset[int]) -> str | None:
    """The Benson centre-atom type for heavy atom ``i``: C / Cd / Ct / CB / CO / O / N, or ``None`` if the
    atom is an ABSORBED carbonyl oxygen (the ``=O`` of a C=O, folded into the CO group and NOT its own group).

    A non-CHNO element returns its raw symbol (an off-coverage sentinel that :func:`assign_groups` rejects).
    """
    el = mol.atoms[i]
    nbrs = adj[i]
    if el == "C":
        if i in aromatic:
            return "CB"
        if any(atoms_o == 2 and mol.atoms[j] == "O" for (j, atoms_o) in nbrs):
            return "CO"  # carbonyl carbon (=O)
        if any(o == 3 for (_j, o) in nbrs):
            return "Ct"
        if any(o == 2 for (_j, o) in nbrs):
            return "Cd"
        return "C"
    if el == "O":
        # a carbonyl =O has a single neighbour reached by an order-2 bond -> absorbed (no own group).
        heavy = [(j, o) for (j, o) in nbrs if mol.atoms[j] != "H"]
        if len(heavy) == 1 and heavy[0][1] == 2:
            return None
        return "O"
    if el == "N":
        return "N"
    return el  # off-coverage element sentinel


def _group_label(mol: Molecule, i: int, ctype: str, adj: list[list[tuple[int, int]]],
                 center_types: dict[int, str | None], ring_bonds: frozenset[frozenset[int]]) -> str | None:
    """Build atom ``i``'s canonical Benson group label, or ``None`` if a heavy ligand is off-coverage.

    The atom(s) belonging to the centre's IMPLICIT bond are excluded from the ligand list: the two aromatic
    ring bonds for CB, the ``=O`` for CO, the ``=C`` partner for Cd, the ``#C`` partner for Ct.
    """
    nH = _h_count(adj[i], mol.atoms)
    ligand_types: list[str] = []
    for j, order in adj[i]:
        if mol.atoms[j] == "H":
            continue
        jt = center_types[j]
        # skip the centre's implicit-bond partner(s)
        if ctype == "CB" and frozenset((i, j)) in ring_bonds:
            continue
        if ctype == "CO" and mol.atoms[j] == "O" and order == 2:
            continue
        if ctype == "Cd" and order == 2:
            continue
        if ctype == "Ct" and order == 3:
            continue
        if jt is None or jt not in _LIGAND_PRIORITY:
            return None  # a ligand we cannot type -> off-coverage, loud
        ligand_types.append(jt)
    ligand_types.sort(key=lambda t: (_LIGAND_PRIORITY[t], t))
    parts: list[str] = []
    idx = 0
    while idx < len(ligand_types):
        t = ligand_types[idx]
        k = 1
        while idx + k < len(ligand_types) and ligand_types[idx + k] == t:
            k += 1
        parts.append(f"({t})" if k == 1 else f"({t}){k}")
        idx += k
    if nH:
        parts.append("(H)" if nH == 1 else f"(H){nH}")
    return f"{ctype}-{''.join(parts)}"


def assign_groups(molecule: Molecule) -> tuple[str, ...] | None:
    """The multiset of Benson group labels for ``molecule``, or ``None`` if any heavy atom is off-coverage.

    Off-coverage = a non-CHNO element, or a local environment whose ligands cannot be typed.  Hydrogens and
    absorbed carbonyl oxygens contribute no group of their own.  The returned tuple is sorted, so it is a
    stable, comparable signature.
    """
    if type(molecule) is not Molecule:
        raise TypeError("assign_groups takes a Molecule")
    mol = molecule.canonical()
    adj = _neighbours(mol)
    aromatic, ring_bonds, _num_aromatic_rings = _aromatic_rings(mol, adj)
    # Ring-strain guard: Benson additivity needs a strain correction for every non-benzene ring
    # (cyclopropane +115, cyclobutane +110, epoxide +112 kJ/mol, ...).  :func:`_ring_analysis` returns the
    # sourced strain keys for the molecule's non-aromatic rings, or None when a ring has no sourced
    # correction, the rings are fused (polycyclic strain not tabulated), or a ring is larger than the search
    # cap -- in every such case the molecule is OFF-COVERAGE (a loud None), never a strain-blind estimate.
    if _ring_analysis(mol, adj, aromatic) is None:
        return None
    center_types: dict[int, str | None] = {}
    for i, s in enumerate(mol.atoms):
        if s == "H":
            continue
        center_types[i] = _center_type(mol, i, adj, aromatic)
    labels: list[str] = []
    for i, ct in center_types.items():
        if ct is None:
            continue  # absorbed carbonyl oxygen
        if ct not in _LIGAND_PRIORITY and ct != "Ct":
            return None  # off-coverage centre element (e.g. S, Cl, P)
        label = _group_label(mol, i, ct, adj, center_types, ring_bonds)
        if label is None:
            return None
        labels.append(label)
    return tuple(sorted(labels))


# =====================================================================================================
# Rotational-symmetry number for the -R ln(σ) + R ln(n_optical) entropy correction.
# σ = σ_ext × σ_int:  σ_ext = |Aut(heavy graph)| with aromatic ring bonds uniformised (so the Kekulé
# single/double alternation does not spuriously break benzene's ring symmetry); σ_int = 3 per methyl-type
# top.  This reproduces the physical symmetry number for the whole calibration set (ethane/propane/butane
# 18, benzene 12, methanol/ethanol/acetaldehyde/propene 3, acetone/dimethyl-ether 18).
#
# WHERE THE GRAPH AUTOMORPHISM IS NOT THE SYMMETRY NUMBER (and how each case is handled honestly):
# * Improper (mirror) symmetry -- a 2-D graph cannot tell a proper C2 rotation from a mirror, so |Aut|
#   over-counts a *single* equivalent-group swap by a factor 2 (e.g. toluene, isopropanol, and even
#   neopentane where |Aut|=|Td|=24 vs the proper σ_ext=12).  That ≤ R ln 2 ≈ 5.76 J/mol/K residual is
#   always folded into the S° band, and these stay DERIVED.
# * Independent permutation of equivalent tops at DIFFERENT branch points -- the graph lets the methyls on
#   one quaternary/tertiary carbon permute independently of those on another (S3×S3×… ), which NO rigid
#   rotation realizes, so the over-count COMPOUNDS multiplicatively and blows past R ln 2 (2,2,3,3-
#   tetramethylbutane: |Aut|σ=52488 vs true 4374, a factor 12).  A 2-D graph cannot compute the true σ_ext
#   here (it needs 3-D), so :func:`_sigma_multicenter_unreliable` DETECTS the signature (≥2 heavy atoms
#   each bearing ≥2 equivalent methyl tops) and the estimate is graded PREDICTED with its S° band widened to
#   R ln(σ_ext) -- honestly bracketing the over-count instead of asserting a confident (too-low) S°.
#   (Found by adversarial review; the old "≤ R ln 2 always" claim here was false for multi-branch alkanes.)
# n_optical (chirality) is a future rung; held at 1 (its effect is also ≤ R ln 2, in the band).
# =====================================================================================================
_MAX_AUT_ATOMS = 20  # safety valve: above this, skip the search -> σ_ext=1 and the estimate grades PREDICTED


def _heavy_symmetry_graph(mol: Molecule, adj: list[list[tuple[int, int]]],
                          ring_bonds: frozenset[frozenset[int]]) -> tuple[list[int], dict[int, tuple[str, int]], dict[frozenset[int], int]]:
    """Heavy-atom nodes, per-node colour ``(element, H-count)``, and per-edge colour (bond order, aromatic
    ring bonds mapped to the sentinel 0 so benzene reads as a uniform 6-cycle)."""
    heavy = [i for i, s in enumerate(mol.atoms) if s != "H"]
    color = {i: (mol.atoms[i], _h_count(adj[i], mol.atoms)) for i in heavy}
    edges: dict[frozenset[int], int] = {}
    for b in mol.bonds:
        if mol.atoms[b.i] == "H" or mol.atoms[b.j] == "H":
            continue
        key = frozenset((b.i, b.j))
        edges[key] = 0 if key in ring_bonds else b.order
    return heavy, color, edges


def _automorphism_count(heavy: list[int], color: dict[int, tuple[str, int]], edges: dict[frozenset[int], int]) -> int:
    """Order of the automorphism group of the coloured heavy-atom graph (brute force over colour classes)."""
    if len(heavy) > _MAX_AUT_ATOMS:
        return 1
    nbr: dict[int, dict[int, int]] = {i: {} for i in heavy}
    for key, o in edges.items():
        a, b = tuple(key)
        nbr[a][b] = o
        nbr[b][a] = o
    targets_by_color: dict[tuple[str, int], list[int]] = {}
    for i in heavy:
        targets_by_color.setdefault(color[i], []).append(i)
    order = sorted(heavy, key=lambda i: (len(targets_by_color[color[i]]), i))
    count = 0

    def consistent(mapping: dict[int, int], a: int, img: int) -> bool:
        for src, dst in mapping.items():
            if (a in nbr[src]) != (img in nbr[dst]):
                return False
            if a in nbr[src] and nbr[src][a] != nbr[dst][img]:
                return False
        return True

    def backtrack(k: int, mapping: dict[int, int], used: set[int]) -> None:
        nonlocal count
        if k == len(order):
            count += 1
            return
        a = order[k]
        for img in targets_by_color[color[a]]:
            if img in used:
                continue
            if consistent(mapping, a, img):
                mapping[a] = img
                used.add(img)
                backtrack(k + 1, mapping, used)
                del mapping[a]
                used.discard(img)

    backtrack(0, {}, set())
    return max(count, 1)


def _internal_symmetry(mol: Molecule, adj: list[list[tuple[int, int]]]) -> int:
    """Product of internal-rotor top symmetries: 3 for each methyl-type top (a heavy atom bonded to the
    skeleton by exactly one single bond and to exactly three H)."""
    sigma_int = 1
    for i, s in enumerate(mol.atoms):
        if s == "H":
            continue
        heavy = [(j, o) for (j, o) in adj[i] if mol.atoms[j] != "H"]
        nH = _h_count(adj[i], mol.atoms)
        if len(heavy) == 1 and heavy[0][1] == 1 and nH == 3:
            sigma_int *= 3
    return sigma_int


def _methyl_tops_per_atom(mol: Molecule, adj: list[list[tuple[int, int]]]) -> dict[int, int]:
    """For each heavy atom, how many methyl-type tops (a C bonded to it by one single bond and to 3 H) hang
    off it -- the count of independently-permutable equivalent tops at that branch point."""
    counts: dict[int, int] = {}
    for i, s in enumerate(mol.atoms):
        if s == "H":
            continue
        n = 0
        for j, o in adj[i]:
            if o == 1 and mol.atoms[j] == "C":
                jheavy = [(k, oo) for (k, oo) in adj[j] if mol.atoms[k] != "H"]
                jH = _h_count(adj[j], mol.atoms)
                if len(jheavy) == 1 and jH == 3:
                    n += 1
        counts[i] = n
    return counts


def _sigma_multicenter_unreliable(mol: Molecule, adj: list[list[tuple[int, int]]]) -> bool:
    """True when σ_ext = |Aut(heavy graph)| can COMPOUND past the factor-2 mirror residual: the signature is
    two or more distinct branch points that each bear >=2 equivalent methyl tops, which the graph permits to
    permute independently (S3xS3, …) though no rigid rotation does.  A single multi-methyl centre (neopentane,
    isobutane) is only the factor-2 improper case and stays reliable (in-band)."""
    counts = _methyl_tops_per_atom(mol, adj)
    return sum(1 for n in counts.values() if n >= 2) >= 2


def _symmetry_number(mol: Molecule, adj: list[list[tuple[int, int]]],
                     ring_bonds: frozenset[frozenset[int]]) -> tuple[int, int, bool]:
    """The total rotational symmetry number σ, its external part σ_ext, and whether the automorphism search
    was skipped (graph too big -> σ_ext forced to 1)."""
    heavy, color, edges = _heavy_symmetry_graph(mol, adj, ring_bonds)
    skipped = len(heavy) > _MAX_AUT_ATOMS
    sigma_ext = _automorphism_count(heavy, color, edges)
    return sigma_ext * _internal_symmetry(mol, adj), sigma_ext, skipped


@dataclass(frozen=True)
class GroupThermoEstimate:
    """A DERIVED/PREDICTED ideal-gas ΔfH°(298) and S°(298), each with an uncertainty band, from group
    additivity.  ``grade`` is ``PREDICTED`` if any contributing group is ``ASSIGNED`` (by analogy), else
    ``DERIVED``.  Always ``phase == "gas"`` -- a condensed-phase value needs a separate correction."""

    dhf_kj_per_mol: float
    s_j_per_mol_k: float
    dhf_uncertainty_kj: float
    s_uncertainty_j_per_k: float
    grade: str
    symmetry_number: int
    groups: tuple[str, ...]
    provenance: str
    phase: str = "gas"
    _tiers: tuple[GroupTier, ...] = field(default=(), compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.grade not in ("DERIVED", "PREDICTED"):
            raise ValueError("grade must be DERIVED or PREDICTED")
        if self.phase != "gas":
            raise ValueError("group additivity yields gas-phase values only")


def estimate_thermo(molecule: Molecule) -> GroupThermoEstimate | None:
    """Estimate ideal-gas ΔfH°(298) and S°(298) for ``molecule`` by Benson group additivity, or ``None``
    (naming the missing group in no output -- the caller sees ``None``) if any group is off-coverage.

    S° = Σ S°(groups) − R ln(σ) + R ln(n_optical), with n_optical = 1 (chirality is a future rung).  The
    ΔfH° band is the quadrature sum of per-group tier bands; the S° band adds the σ-approximation residual
    (R ln 2).  Grade is ``PREDICTED`` if any group is ``ASSIGNED``, else ``DERIVED``.
    """
    labels = assign_groups(molecule)
    if labels is None:
        return None
    groups = [_GROUP_BY_LABEL.get(lbl) for lbl in labels]
    if any(g is None for g in groups):
        return None  # a real, typed group with no sourced value -> loud gap
    mol = molecule.canonical()
    adj = _neighbours(mol)
    _aromatic, ring_bonds, _n_rings = _aromatic_rings(mol, adj)
    sigma, sigma_ext, skipped = _symmetry_number(mol, adj, ring_bonds)
    multicenter = _sigma_multicenter_unreliable(mol, adj)
    sigma_unreliable = skipped or multicenter

    # ring-strain corrections (rung A): a non-aromatic ring adds ΔfH°/S° on top of its atom-centred groups.
    # assign_groups already guaranteed every ring is sourced (else it returned None), so this is not-None.
    ring_keys = _ring_analysis(mol, adj, _aromatic) or ()
    rings = [_RING_BY_KEY[k] for k in ring_keys]

    dhf = sum(g.dhf_kj_per_mol for g in groups) + sum(r.dhf_kj_per_mol for r in rings)
    s_groups = sum(g.s_j_per_mol_k for g in groups) + sum(r.s_j_per_mol_k for r in rings)
    s_total = s_groups - R_J_PER_MOL_K * math.log(sigma)  # n_optical = 1 -> +R ln 1 = 0

    _ring_band = {RingTier.ESTABLISHED: (4.0, 5.0), RingTier.EXPERIMENTAL: (8.0, 8.0)}
    _gband = [g.band if g.band is not None else _TIER_BAND[g.tier] for g in groups]
    dhf_var = sum(b[0] ** 2 for b in _gband) + sum(_ring_band[r.tier][0] ** 2 for r in rings)
    s_var = sum(b[1] ** 2 for b in _gband) + sum(_ring_band[r.tier][1] ** 2 for r in rings)
    # symmetry-uncertainty band: normally the R ln 2 improper-mirror residual; widened when σ is unreliable.
    if skipped:
        s_sym_residual = R_J_PER_MOL_K * math.log(18.0)   # σ_ext unknown (graph too big) -- a generous floor
    elif multicenter:
        s_sym_residual = R_J_PER_MOL_K * math.log(sigma_ext)  # brackets the compounding branch-permutation over-count
    else:
        s_sym_residual = R_J_PER_MOL_K * math.log(2.0)
    dhf_band = round(math.sqrt(dhf_var), 1)
    s_band = round(math.sqrt(s_var) + s_sym_residual, 1)

    tiers = tuple(g.tier for g in groups)
    grade = (
        "PREDICTED"
        if (any(t is GroupTier.ASSIGNED for t in tiers) or sigma_unreliable)
        else "DERIVED"
    )

    counts: dict[str, int] = {}
    for lbl in labels:
        counts[lbl] = counts.get(lbl, 0) + 1
    group_render = ", ".join(f"{n}x {lbl}" if n > 1 else lbl for lbl, n in sorted(counts.items()))
    sigma_note = "" if not sigma_unreliable else (
        " [σ UNRELIABLE: "
        + ("graph too large, σ_ext skipped" if skipped else
           "multiple equivalent branch tops -- graph over-counts the rotational σ; S° band widened to bracket it")
        + " -> PREDICTED]"
    )
    ring_note = "" if not rings else (
        f"; ring-strain corrections [{', '.join(sorted(r.key for r in rings))}] (RMG ring.py)"
    )
    provenance = (
        f"{grade} ideal-gas (298 K) via Benson group additivity: ΔfH° = Σ groups (+ ring strain), "
        f"S° = Σ groups (+ ring strain) − R·ln(σ={sigma}); groups [{group_render}]{ring_note}; "
        f"sourced RMG-database Benson/CBS-QB3 values (see BENSON_GROUPS provenance); "
        f"gas phase only (condensed-phase needs a separate Δsub correction){sigma_note}"
    )
    return GroupThermoEstimate(
        round(dhf, 2), round(s_total, 2), dhf_band, s_band, grade, sigma, tuple(labels), provenance,
        _tiers=tiers,
    )
