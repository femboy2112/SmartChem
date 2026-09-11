"""Bond-additivity reaction enthalpy -- a DERIVED estimate of a disconnection's thermodynamic DRIVE, in its domain.

The retrosynthesis engine (capped scission) is valence-preserving but not chemically selective: it OVER-GENERATES,
emitting valence-valid-but-dubious candidates alongside the sound ones (the R45 caffeine finding -- a C-C homologation
``ethanol + theophylline -> caffeine + methanol`` was ranked ABOVE the sound N-methylation ``theophylline + methanol
-> caffeine + water``, because both are thermo-UNKNOWN and the ranker fell through to arbitrary discovery order).

This module supplies the missing signal WITHOUT hard-coding any reaction.  It hard-codes REALITY -- mean bond
enthalpies (measured physical constants keyed by bond TYPE, never by reaction; transferable AVERAGES, so model-laden,
unlike an exact atomic mass) -- and DERIVES a reaction enthalpy from them by Hess's law over the NET bond change::

    ΔH_rxn  ≈  Σ BDE(bonds broken)  −  Σ BDE(bonds formed)

Only the bonds that actually change are consulted (the multiset difference of the reactant vs product bond inventory),
so the unchanged skeleton cancels.  This is the "reproduce known physics to derive an unknown" discipline: the
transform algebra proposes the disconnection; bond additivity grades its drive, labelled DERIVED, never SOURCED.

**What this ranks, precisely.**  The frontier asked to prefer "chemically-sensible disconnections"; what this delivers
is thermodynamic DRIVE (a reaction ΔH sign), which is a *proxy* for sensibility -- they coincide for the caffeine case
and part ways in general (a thermodynamically-favorable disconnection can still be mechanistically absurd).  Every
route stays ``FORMAL_CANDIDATE``; this orders the drive, it does not certify mechanism.

Why it discriminates the caffeine case (the physics, not a rule): the sound methylation forms the very strong O-H
bond of water (463 kJ) -- a thermodynamic sink -- while the C-C homologation breaks a strong C-C bond (347 kJ) and
forms only a weaker C-H (414 kJ), with no comparable sink.  ΔH(sound) ≈ −19 kJ (exergonic), ΔH(dubious) ≈ +19 kJ
(endergonic); the relative separation (≈ +38 kJ, in which the shared N-H/C-N terms cancel) is robust to the exact BDE
values.  Nothing in the table says "methylation good"; Hess's law says water is stable.  This is genuine derivation,
NOT a lookup -- proven not by reverse-antisymmetry (every signed quantity flips on reverse, a lookup included) but by
GENERALIZATION: the ΔH is computed for reactions in NO table (caffeine's methylation is untabulated, R45).

**The domain, and the domain guard (evil-morty / dalembert R47).**  Bond additivity is a sum of LOCALIZED per-bond
terms, so it is BLIND to non-local stabilization -- ring strain and aromatic/ring delocalization -- and INVERTS the
sign there (cyclopropane->propene: est +80, true −33; 1,3-cyclohexadiene->benzene+H2: est +125, true −22).  So
:func:`reaction_delta_h_kj` FAILS CLOSED (returns ``None`` -> BORDERLINE) whenever the ENDOCYCLIC-bond-type multiset
is not preserved across the reaction -- declining exactly the ring-forming/opening/aromatizing regime where additivity
is unsound, and keeping the acyclic-periphery reactions it earns (the caffeine methylation preserves the purine ring).
Residual: linear (non-ring) conjugation changes carry a smaller (~10-20 kJ) non-additive error, bounded by the
dead-band and by this tier being dead-last + subordinate + ranking-only.

**Calibration + the dead-band.**  On seven known-sign reactions the estimator recovers the SIGN of every one,
INCLUDING combustion (whose ~200 kJ MAGNITUDE error -- O2/CO2 resonance -- is why the tier grades sign, never
magnitude); the largest in-domain residual is 14 kJ (CH4+Cl2).  :data:`DERIVED_BORDERLINE_KJ` = 15 is set ABOVE that
so an estimate that clears the band is unlikely to carry the wrong sign from residual error; it is a conservative
floor, not the (much larger, magnitude) accuracy.  See :data:`CALIBRATION` and the committed probe.

**Epistemic status.**  A ranking-only, DERIVED tiebreaker -- strictly subordinate to every sourced tier (it acts only
among routes otherwise tied, where the sourced thermo is UNKNOWN) and NEVER a verdict (it never enters ``fit.status``
or any L2 grade).  Where a sourced ΔG reaches a route, the sourced feasibility tier dominates and this is inert.
Neutral on ignorance: an untabulated bond -- or a ring/aromatic change the guard declines -- -> ``None`` -> the
neutral BORDERLINE rank, never a reward or penalty.
"""
from __future__ import annotations

from collections import Counter

from ..category import Molecule
from .step import ExperimentRoute

__all__ = [
    "MEAN_BOND_ENTHALPY_KJ",
    "DERIVED_BORDERLINE_KJ",
    "BOND_ENTHALPY_PROVENANCE",
    "CALIBRATION",
    "reaction_delta_h_kj",
    "route_delta_h_kj",
    "disconnection_favorability_rank",
]

#: Mean (average) bond enthalpies in kJ/mol, keyed by ``(element_a, element_b, order)`` with the element pair SORTED.
#: These are transferable averages over many molecules -- measured physical constants, a standard tabulation
#: (Atkins & de Paula, *Physical Chemistry*, mean bond enthalpies; consistent with the CRC Handbook).  Transferability
#: is the source of the model's ~10 kJ resolution (calibrated below); the values are the reality this module stands on.
BOND_ENTHALPY_PROVENANCE = (
    "mean bond enthalpies (transferable averages), standard tabulation (Atkins & de Paula, Physical Chemistry; "
    "consistent with the CRC Handbook of Chemistry and Physics)"
)


def _k(a: str, b: str, order: int) -> tuple[str, str, int]:
    x, y = sorted((a, b))
    return (x, y, order)


MEAN_BOND_ENTHALPY_KJ: dict[tuple[str, str, int], float] = {
    _k(*t): v for t, v in {
        # single bonds
        ("C", "H", 1): 414.0, ("C", "C", 1): 347.0, ("C", "N", 1): 305.0, ("C", "O", 1): 358.0,
        ("C", "S", 1): 259.0, ("C", "F", 1): 485.0, ("C", "Cl", 1): 339.0, ("C", "Br", 1): 285.0,
        ("C", "I", 1): 214.0, ("N", "H", 1): 391.0, ("O", "H", 1): 463.0, ("S", "H", 1): 347.0,
        ("N", "N", 1): 163.0, ("N", "O", 1): 201.0, ("O", "O", 1): 146.0, ("H", "H", 1): 436.0,
        ("F", "H", 1): 565.0, ("Cl", "H", 1): 431.0, ("Br", "H", 1): 366.0, ("I", "H", 1): 299.0,
        ("Cl", "Cl", 1): 242.0, ("Br", "Br", 1): 193.0, ("F", "F", 1): 155.0, ("I", "I", 1): 151.0,
        ("N", "F", 1): 272.0, ("N", "Cl", 1): 200.0, ("O", "F", 1): 190.0, ("S", "S", 1): 266.0,
        ("O", "S", 1): 265.0, ("P", "O", 1): 335.0, ("P", "H", 1): 322.0, ("P", "Cl", 1): 326.0,
        # double bonds
        ("C", "C", 2): 614.0, ("C", "N", 2): 615.0, ("C", "O", 2): 745.0, ("C", "S", 2): 477.0,
        ("N", "N", 2): 418.0, ("N", "O", 2): 607.0, ("O", "O", 2): 498.0, ("S", "O", 2): 523.0,
        # triple bonds
        ("C", "C", 3): 839.0, ("C", "N", 3): 891.0, ("N", "N", 3): 945.0, ("C", "O", 3): 1072.0,
    }.items()
}

#: A conservative dead-band: a directional (FAVORABLE/UNFAVORABLE) claim is made only when the derived |ΔH| exceeds
#: it; within it the drive is BORDERLINE (neutral).  It is NOT a claim about the estimator's accuracy (bond additivity
#: can err by ~200 kJ in MAGNITUDE -- see combustion in :data:`CALIBRATION` -- which is precisely why the tier grades
#: SIGN only, never magnitude).  It is set ABOVE the estimator's largest observed residual on in-domain (acyclic,
#: ring-preserving) calibration reactions -- 14 kJ for CH4+Cl2->CH3Cl+HCl -- so an estimate that clears the band is
#: unlikely to carry the wrong sign from residual error alone.  15 > 14, and the motivating caffeine signal (±19 kJ,
#: whose relative separation is a robust +38 kJ) clears it -- the band is a floor above the demonstrated in-domain
#: error, NOT a number tuned to make caffeine pass (any band in (14, 19) works identically for caffeine).
DERIVED_BORDERLINE_KJ = 15.0

#: Known-sign reactions for the instrument rule: ``(name, reactant SMILES, product SMILES, literature ΔH kJ)``.  The
#: estimator must recover the SIGN of every one before its readings on novel disconnections are trusted (see the probe).
CALIBRATION: tuple[tuple[str, tuple[str, ...], tuple[str, ...], float], ...] = (
    ("H2+Cl2->2HCl", ("[H][H]", "ClCl"), ("Cl", "Cl"), -185.0),
    ("N2+3H2->2NH3", ("N#N", "[H][H]", "[H][H]", "[H][H]"), ("N", "N"), -92.0),
    ("2H2O2->2H2O+O2", ("OO", "OO"), ("O", "O", "O=O"), -196.0),
    ("C2H4+H2->C2H6", ("C=C", "[H][H]"), ("CC",), -137.0),
    ("CO+2H2->CH3OH", ("[C-]#[O+]", "[H][H]", "[H][H]"), ("CO",), -128.0),
    ("CH4+Cl2->CH3Cl+HCl", ("C", "ClCl"), ("CCl", "Cl"), -100.0),
    ("CH4+2O2->CO2+2H2O", ("C", "O=O", "O=O"), ("O=C=O", "O", "O"), -890.0),
)


def _bond_multiset(molecule: Molecule) -> Counter:
    counts: Counter = Counter()
    for bond in molecule.bonds:
        counts[_k(molecule.atoms[bond.i], molecule.atoms[bond.j], bond.order)] += 1
    return counts


def _endocyclic_bond_types(molecule: Molecule) -> Counter:
    """The multiset of bond TYPES on ENDOCYCLIC bonds (those lying in a ring).  A bond is endocyclic iff its
    endpoints stay connected after it is removed (it is in a cycle, not a bridge)."""
    bonds = list(molecule.bonds)
    counts: Counter = Counter()
    for skip, bond in enumerate(bonds):
        i, j = bond.i, bond.j
        adjacency: dict[int, list[int]] = {}
        for k, other in enumerate(bonds):
            if k == skip:
                continue
            adjacency.setdefault(other.i, []).append(other.j)
            adjacency.setdefault(other.j, []).append(other.i)
        seen = {i}
        stack = [i]
        in_ring = False
        while stack:
            x = stack.pop()
            if x == j:
                in_ring = True
                break
            for y in adjacency.get(x, []):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        if in_ring:
            counts[_k(molecule.atoms[i], molecule.atoms[j], bond.order)] += 1
    return counts


def reaction_delta_h_kj(
    reactants: "tuple[Molecule, ...]", products: "tuple[Molecule, ...]"
) -> float | None:
    """The DERIVED bond-additivity reaction enthalpy (kJ/mol), or ``None`` if any NET-changed bond type is untabulated.

    ``ΔH = Σ BDE(net bonds broken) − Σ BDE(net bonds formed)``, where the net change is the multiset difference of the
    reactant vs product bond inventories -- so the unchanged skeleton cancels and only the bonds that actually change
    are looked up.  Requires explicit hydrogens on the molecules (so X-H changes are visible); the parser and structure
    descent both supply them.  Returns ``None`` (never a fabricated number) when a changed bond type is not in
    :data:`MEAN_BOND_ENTHALPY_KJ` -- the neutral-on-ignorance discipline.
    """
    # DOMAIN GUARD (evil-morty / dalembert R47): bond additivity is a sum of LOCALIZED, transferable per-bond terms,
    # so it is BLIND to non-local stabilization -- ring strain and aromatic/ring delocalization.  It inverts the sign
    # on ring-strain release (cyclopropane->propene: est +80, true -33) and aromatization (1,3-cyclohexadiene->
    # benzene+H2: est +125, true -22).  Fail CLOSED (return None -> BORDERLINE) whenever the ENDOCYCLIC-bond-type
    # multiset is not preserved across the reaction -- i.e. a ring bond is made, broken, or changes order (ring
    # formation/opening, aromatization, ring-tautomerization).  This declines EXACTLY the regime where additivity is
    # unsound, and keeps the acyclic-periphery reactions it earns (the caffeine N-methylation preserves the purine
    # ring, so its endocyclic multiset is identical on both sides -> the estimate stands).  This is the honest domain
    # of the module's own theorem: "only the changed bonds matter, and localized changes are additive."
    r_endo: Counter = Counter()
    p_endo: Counter = Counter()
    for m in reactants:
        r_endo += _endocyclic_bond_types(m)
    for m in products:
        p_endo += _endocyclic_bond_types(m)
    if r_endo != p_endo:
        return None

    r: Counter = Counter()
    p: Counter = Counter()
    for m in reactants:
        r += _bond_multiset(m)
    for m in products:
        p += _bond_multiset(m)
    broken = r - p
    formed = p - r
    for key in set(broken) | set(formed):
        if key not in MEAN_BOND_ENTHALPY_KJ:
            return None
    return (sum(MEAN_BOND_ENTHALPY_KJ[k] * n for k, n in broken.items())
            - sum(MEAN_BOND_ENTHALPY_KJ[k] * n for k, n in formed.items()))


def route_delta_h_kj(route: "ExperimentRoute") -> float | None:
    """The net DERIVED bond-additivity enthalpy of a route OR a convergent DAG (anything exposing ``.steps``, exactly
    like :func:`~smartchem.experiment.functorial_physics.route_net_delta_g`): the Hess sum over its steps, or ``None``
    if any step is untabulated.  Intermediates cancel across steps (the same additivity), so this is the total drive."""
    total = 0.0
    for step in route.steps:
        dh = reaction_delta_h_kj(tuple(step.reactants), tuple(step.products))
        if dh is None:
            return None
        total += dh
    return total


def disconnection_favorability_rank(route: "ExperimentRoute") -> int:
    """The DERIVED ranking tier for a route (lower = better), NEUTRAL on ignorance:

    * ``0`` FAVORABLE   -- net derived ΔH < −dead-band (exergonic beyond the instrument's resolution)
    * ``1`` BORDERLINE  -- |ΔH| ≤ dead-band, OR untabulated (``None``): the neutral middle, no directional claim
    * ``2`` UNFAVORABLE -- net derived ΔH > +dead-band (endergonic beyond resolution)

    This is the dead-last, strictly-subordinate tiebreaker: it only separates routes that tie on every SOURCED tier.
    """
    dh = route_delta_h_kj(route)
    if dh is None:
        return 1
    if dh < -DERIVED_BORDERLINE_KJ:
        return 0
    if dh > DERIVED_BORDERLINE_KJ:
        return 2
    return 1
