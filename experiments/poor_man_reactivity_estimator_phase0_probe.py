"""POOR-MAN-REACTIVITY-ESTIMATOR-PHASE0-01 (R53, Phase 0): the DECISIVE kill-or-continue probe for the
ingenuity-reward keystone.  The three prior rounds (R49/R50/R52) each killed a BOOLEAN reaction-classifier:
a bounded-radius LOOKUP key cannot carry the unbounded-radius feasibility envelope, so it collides across the
kitchen boundary and confidently false-VOUCHes a ground-truth-distinct pair.  The plan's ONE unexplored fork
(POOR_MAN_ARCH_COMPLETION_PLAN_v0.1.md sec.3): a CONTINUOUS DERIVED reactivity estimator (bond_enthalpy.py
pattern -- measured constants + calibration + a fail-closed domain guard), which MEASURES the determinants
instead of looking up a class.  This probe answers the fork Bearing A could not close:

    Is the collision recurrence UNBOUNDED (infinite regress -> a sound reward is impossible for Fischer
    esterification as a class -> a FOURTH verified defer, matching R49/R50/R52) or BOUNDED-BUT-LARGE (the
    determinants are a finite set of radius-1/2 graph-local + continuous features that TERMINATE with a
    fail-closed domain guard, exactly as bond_enthalpy.py's additivity terminates outside the ring regime)?

=============================================================================================================
GATE OUTCOME (R53 Phase-0, five-bearing adversarial design gate at HEAD 24afef3): **DEFER #4** -- the FOURTH
verified defer of the ingenuity reward.  The instrument's OWN core battery reads clean (false_vouch=0 on 17
cases, the alcohol-side carbocation core sound AND independently calibration-verified -- daniel: it separates
FRESH score-3 and score-4 alcohols it was never fit on; the Bearing-A benzylic degree-2 collision R52 could
not close IS closed here).  But two INDEPENDENT adversaries broke the FEASIBLE set on axes the battery never
varied, and the break is the SAME shape every prior round hit -- a determinant the bounded feature set can
neither read nor decline:
  * dalembert (structure-theorem): the ACID side is a single flag (ortho-aryl steric).  Any acid that fails
    Fischer for a NON-steric reason is invisible -> confident FEASIBLE.  Proven: beta-keto acids
    (acetoacetic) DECARBOXYLATE under Fischer's acid/heat (acetone + CO2) -- ethyl acetoacetate is made from
    diketene / Claisen, NEVER Fischer of acetoacetic acid.  The keto-position sweep is the theorem: alpha-keto
    (pyruvic) works, beta-keto fails, gamma-keto (levulinic) works -- separating beta needs the keto->carboxyl
    DISTANCE, a radius-2 determinant the feature set has zero acid-side features for.
  * evil-morty (feature-extraction break): sulfur is in _SAFE_ELEMENTS but omitted from _carbinol_alpha_
    heteroatom (O/N only) AND from the thiol detector (thioether = 2 heavy neighbours) -- so an alpha-thioether
    carbinol (thionium-ion SN1) scores FEASIBLE while the byte-identical alpha-O and alpha-N graphs are
    declined.  And the binary conjugation flag is MAGNITUDE-blind: furfuryl alcohol (ring-O-stabilized cation
    -> acid resinification) gets benzyl's exact feature vector -> FEASIBLE.
  * (the P0.3 census earlier found + this round patched the PHENOL hole -- and patching it was met by the S /
    beta-keto / furfuryl leaks: the guard is a HAND-ENUMERATED BLACKLIST of an UNBOUNDED hazard space, so each
    patch is met by a new leak one heteroatom/position/functional-group out.)

THE THEOREM (why this is defer #4, not a bug list): going continuous + three-valued + fail-closed was a REAL
improvement (the alcohol-side cation core is sound and calibrated), but it did NOT reach zero false-VOUCH,
because the DOMAIN GUARD is itself a bounded enumeration of hazard triggers and the hazard space is unbounded.
Making the classifier continuous MOVED the R49/R50/R52 collision from the classifier into the guard; it did not
close it.  The escape all four defers now name: a SYMMETRIC POSITIVE safe-set whitelist on BOTH reaction
centers (R51 "recognize the SAFE set only", applied to substrates) -- confidently FEASIBLE only when both
neighbourhoods are recognized-inert, decline everything else -- which re-raises the R52 base-rate/vacuity
question (does the FEASIBLE set survive the whitelist, or does it swallow the population?) and needs its own
calibration + gate round.  AND: a full-registry sweep (all 45 registered targets) found ZERO consumers -- no
engine-derived route where this estimator changes a ranking today -- so even the bigger model has no live call
site.  P0.1 (sourced constants) fully DELIVERED; the constants are verified (daniel: 6/8 Taft E_s match an
independent compilation exactly; Hammett DOI 10.1021/cr00002a004).

This probe is the DEFER ARTIFACT: it FREEZES both the positive result (the clean core battery) and the KILL
(the surviving false-VOUCHes across independent axes), the R52 discipline of proving the kill rather than
hiding it.  The estimator/guard are LEFT AS-IS with the leaks visible ON PURPOSE -- patching S/beta-keto/
furfuryl would only add three more blacklist entries and prove the theorem again one step out.
=============================================================================================================

THE DECISIVE TEST (the R49/R51 soundness bar, made continuous): a reward is sound iff it produces ZERO
false-VOUCH -- never a confident FEASIBLE on a route whose kitchen-truth is NOT-feasible.  A boolean recognizer
failed this because it had only two states, so a determinant it could not read forced a confident wrong answer.
A THREE-valued estimator (FEASIBLE / NOT_FEASIBLE / UNKNOWN) with a fail-closed guard can decline
(-> UNKNOWN, no reward) exactly the cases whose determinant it cannot measure -- so the question is whether the
FEASIBLE set it DOES claim is collision-free, and whether that set is non-vacuous (avoids the R52 base-rate
trap where fail-closed swallows everything).  false-VOUCH >> false-EXCLUDE >> UNKNOWN (R49/R51).

WHAT THE INSTRUMENT MEASURES (the corrected feature set -- the plan's Conjectured "Taft E_s at the carbinol"
was the wrong physics, corrected here per the plan's own sec.7):
  * ALCOHOL side, the E1/SN1 competition that kills tert-butyl and 1-phenylethanol, is a CARBOCATION-STABILITY
    (electronic) failure, NOT steric.  Cation stability is a RADIUS-1 property: carbinol_degree (hyperconjugation)
    + adjacent-pi (benzylic/allylic/propargylic resonance) + alpha-heteroatom lone-pair donation.  A continuous
    cation-stability SCORE reads what degree-alone (R52's blind spot) could not.
  * ACID side, Taft E_s (the CANONICAL Taft application -- his constants were DEFINED from aliphatic ester
    kinetics) is a continuous RATE/RANKING refinement (pivalic slower than acetic), NOT a feasibility gate
    (pivalic acid DOES esterify via Fischer).  The acid-side FEASIBILITY failure is ortho-aryl steric inhibition
    (mesitoic acid), a radius-2 graph flag that neither E_s (aliphatic) nor Hammett sigma (meta/para) reads.
  * The genuinely UNBOUNDED axis (remote acid-labile groups -- acetals, epoxides, trityl ethers destroyed under
    Fischer's acid; sigma-conjugation / ring-strain cation stabilization a pi-flag misses, e.g. cyclopropyl-
    carbinyl) is NOT enumerated (that is the unbounded regress).  It is DECLINED by a fail-closed domain guard
    (positively recognize a SAFE scaffold, R51 lesson; fail closed outside it, bond_enthalpy.py lesson).

Kitchen-truth labels are textbook-ASSERTED (same discipline as the R50 scissors _ESTER_FAMILY flags and the R52
probe's pentyl/tbu labels), each with its phys-org citation in a comment.  RDKit-free; runs REAL production
parser code and reuses the R52 probe's feature machinery so the degree/nucleophile facts are the same functions.

Sourced constants (P0.1, cleared the DERIVED-table bar):
  * Taft steric parameters E_s (methyl-referenced, Me=0): Taft 1952-56, compiled in standard phys-org texts
    (March, Advanced Organic Chemistry; consistent with HandWiki/Charton tabulations).
  * Hammett sigma / sigma+ : Hansch, Leo & Taft, Chem. Rev. 1991, 91, 165-195, DOI 10.1021/cr00002a004.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.smiles import parse_smiles
from experiments.poor_man_out_of_center_recognizer_defer_probe import (
    _adjacency,
    _carbinol_degree,
    _reacting_hydroxyl_o,
    out_of_center_nucleophiles,
)

#: Frozen fingerprint of :func:`_payload`.  Breaks loudly if the fork verdict, the estimator, or any battery
#: case moves against live code.
FROZEN_HASH = "e12680fcb2341d7477e8d9827e63de2b1ec8127c64ef8c23e99c5412cfc067eb"

# --------------------------------------------------------------------------------------------------------------
# P0.1 -- the sourced DERIVED constant tables (the values the Phase-1 module would hold; here inline for the probe)
# --------------------------------------------------------------------------------------------------------------

#: Taft steric parameter E_s, methyl-referenced (Me = 0.00); more negative = bulkier acyl R -> slower Fischer.
#: A RANKING signal for the acid side (continuous rate), NOT a feasibility gate.  Standard tabulation (Taft
#: 1952-56; March, Advanced Organic Chemistry; consistent with HandWiki/Charton).
TAFT_ES = {
    "H": 1.24, "methyl": 0.00, "ethyl": -0.07, "isopropyl": -0.47, "tert-butyl": -1.54,
    "neopentyl": -1.74, "phenyl": -2.55, "benzyl": -0.38,
}
TAFT_ES_PROVENANCE = (
    "Taft steric parameters E_s, methyl-referenced (Taft 1952-1956; standard phys-org tabulation, March "
    "Advanced Organic Chemistry; consistent with HandWiki/Charton van-der-Waals correlations)"
)
HAMMETT_PROVENANCE = (
    "Hammett sigma/sigma+ substituent constants: Hansch, Leo & Taft, Chem. Rev. 1991, 91, 165-195, "
    "DOI 10.1021/cr00002a004"
)


# --------------------------------------------------------------------------------------------------------------
# Feature extraction (radius-1/2 graph-local, computed from the real production parser)
# --------------------------------------------------------------------------------------------------------------

def _carbinol_carbon(alcohol) -> "int | None":
    """Index of the carbon bearing the reacting -OH, or None."""
    atoms = alcohol.atoms
    adj = _adjacency(alcohol)
    o = _reacting_hydroxyl_o(atoms, adj)
    if o is None:
        return None
    cs = [n for n, order in adj.get(o, ()) if atoms[n] == "C"]
    return cs[0] if cs else None


def _carbinol_conjugation(alcohol) -> int:
    """1 if the carbinol carbon is BENZYLIC / ALLYLIC / PROPARGYLIC -- i.e. a carbon-neighbour participates in a
    C=C or C#C (order>=2 to another carbon) -- else 0.  This adjacent pi system resonance-stabilises the
    incipient carbocation (radius-1 electronic property), the determinant degree-alone (R52) is blind to."""
    atoms = alcohol.atoms
    adj = _adjacency(alcohol)
    c = _carbinol_carbon(alcohol)
    if c is None:
        return 0
    for n, _order in adj.get(c, ()):
        if atoms[n] != "C":
            continue
        if any(o2 >= 2 and atoms[m] == "C" for m, o2 in adj.get(n, ())):
            return 1
    return 0


def _carbinol_is_sp2(alcohol) -> bool:
    """True if the carbon bearing the reacting -OH is itself sp2 (participates in a double/aromatic bond) -- i.e.
    the substrate is a PHENOL or ENOL, not an sp3 carbinol.  The cation-stability carbinol physics is validated
    ONLY for sp3 carbinols (the whole battery); phenol/enol O-acylation is a different mechanism entirely (phenol
    nucleophilicity + the anhydride route), so this is OUT OF DOMAIN -> fail closed to UNKNOWN.

    FOUND BY THE P0.3 CONSUMER CENSUS: forcing the estimator onto salicylic acid (aspirin's live, best-ranked
    Fischer disconnection) exposed that `_carbinol_carbon` returns the AROMATIC ipso carbon for a phenol, and
    cation_stability_score then read degree 2 + conjugation 1 = 3 -> a confident NOT_FEASIBLE via wrong physics.
    The battery had no phenol case, so the friendly-subset calibration missed it (the daniel instrument-rule
    lesson: calibrate across the DEPLOYMENT population, not a subset -- [[a-derived-estimate-must-guard-its-
    domain-of-validity]]).  This guard extends the fail-closed set to close it."""
    adj = _adjacency(alcohol)
    c = _carbinol_carbon(alcohol)
    if c is None:
        return False
    return any(order >= 2 for _n, order in adj.get(c, ()))


def _carbinol_alpha_heteroatom(alcohol) -> bool:
    """True if the carbinol carbon bears a SECOND heteroatom (O/N besides the reacting -OH) -- an alpha-lone-pair
    donor that stabilises the cation off-scale (hemiacetal/aminol carbons).  A domain-guard trigger."""
    atoms = alcohol.atoms
    adj = _adjacency(alcohol)
    o = _reacting_hydroxyl_o(atoms, adj)
    c = _carbinol_carbon(alcohol)
    if c is None:
        return False
    for n, _order in adj.get(c, ()):
        if n != o and atoms[n] in ("O", "N"):
            return True
    return False


def _ring_membership(mol) -> "dict[int, set[int]]":
    """For each atom, the set of ring sizes it belongs to (small rings up to 6), by DFS cycle detection."""
    adj = {i: [] for i in range(len(mol.atoms))}
    for b in mol.bonds:
        adj[b.i].append(b.j)
        adj[b.j].append(b.i)
    sizes: "dict[int, set[int]]" = {i: set() for i in range(len(mol.atoms))}

    # find shortest cycle through each edge (girth-ish) up to size 6
    def shortest_cycle_len(u: int, v: int) -> "int | None":
        # BFS from u to v without using edge (u,v)
        from collections import deque
        dq = deque([(u, 0, -1)])
        seen = {u}
        while dq:
            x, d, prev = dq.popleft()
            if d > 6:
                continue
            for y in adj[x]:
                if x == u and y == v and prev == -1:
                    continue  # skip the direct edge on the first hop
                if y == v and not (x == u):
                    return d + 2
                if y not in seen:
                    seen.add(y)
                    dq.append((y, d + 1, x))
        return None

    for b in mol.bonds:
        # only heavy-atom ring bonds matter
        if mol.atoms[b.i] == "H" or mol.atoms[b.j] == "H":
            continue
        cl = shortest_cycle_len(b.i, b.j)
        if cl is not None and cl <= 6:
            sizes[b.i].add(cl)
            sizes[b.j].add(cl)
    return sizes


def _carbinol_adjacent_strained_ring(alcohol) -> bool:
    """True if the carbinol carbon is bonded to a carbon in a 3-membered ring (cyclopropylcarbinyl): the bent-bond
    sigma-conjugation stabilises the cation and drives rearrangement -- an electronic effect the pi-flag CANNOT
    read (bond_enthalpy.py's ring-strain blindness, recurring).  A domain-guard trigger, NOT a false FEASIBLE."""
    adj = _adjacency(alcohol)
    c = _carbinol_carbon(alcohol)
    if c is None:
        return False
    sizes = _ring_membership(alcohol)
    for n, _o in adj.get(c, ()):
        if alcohol.atoms[n] == "C" and 3 in sizes.get(n, set()):
            return True
    return False


def cation_stability_score(alcohol) -> int:
    """The continuous CARBOCATION-STABILITY score at the carbinol carbon: degree (hyperconjugation) + adjacent-pi
    (benzylic/allylic/propargylic resonance).  Higher = more E1/SN1 side-chemistry under Fischer's acid.
    Empirically (textbook): score<=2 esterifies cleanly (1deg, 2deg, 1deg-benzylic like benzyl acetate,
    1deg-allylic like allyl acetate); score>=3 does not (3deg tert-butyl E1; 2deg-benzylic 1-phenylethanol
    SN1/dehydration).  This is the radius-1 feature that CLOSES Bearing A's isopropanol/1-phenylethanol
    collision, which degree-alone (both degree 2) could not."""
    deg = _carbinol_degree(alcohol)
    if deg < 0:
        return -1
    return deg + _carbinol_conjugation(alcohol)


# acid side -------------------------------------------------------------------------------------------------

def _acyl_carbon(acid) -> "int | None":
    """The carboxyl carbon: a C double-bonded to an O and single-bonded to an -OH oxygen."""
    atoms = acid.atoms
    adj = _adjacency(acid)
    for i, el in enumerate(atoms):
        if el != "C":
            continue
        nbrs = adj.get(i, ())
        has_dbl_o = any(o == 2 and atoms[n] == "O" for n, o in nbrs)
        has_oh = any(o == 1 and atoms[n] == "O"
                     and len([1 for m, _ in adj.get(n, ()) if atoms[m] != "H"]) == 1
                     for n, o in nbrs)
        if has_dbl_o and has_oh:
            return i
    return None


def _acyl_r_is_aromatic(acid) -> bool:
    """True if the acyl carbon's R substituent is an aromatic/sp2 carbon (benzoic-type)."""
    atoms = acid.atoms
    adj = _adjacency(acid)
    c = _acyl_carbon(acid)
    if c is None:
        return False
    for n, _o in adj.get(c, ()):
        if atoms[n] == "C" and any(o2 >= 2 and atoms[m] == "C" for m, o2 in adj.get(n, ())):
            return True
    return False


def _acyl_ortho_disubstituted(acid) -> bool:
    """True if the acyl group is aromatic AND both ring carbons ORTHO to the ipso (attachment) carbon bear a
    non-H, non-ring substituent (mesitoic-type steric inhibition of esterification).  Radius-2 graph flag that
    neither Taft E_s (aliphatic) nor Hammett sigma (meta/para only) can read."""
    atoms = acid.atoms
    adj = _adjacency(acid)
    c = _acyl_carbon(acid)
    if c is None:
        return False
    # ipso = the aromatic carbon attached to the acyl carbon
    ipso = None
    for n, _o in adj.get(c, ()):
        if atoms[n] == "C" and any(o2 >= 2 and atoms[m] == "C" for m, o2 in adj.get(n, ())):
            ipso = n
            break
    if ipso is None:
        return False
    sizes = _ring_membership(acid)
    ortho = [n for n, _o in adj.get(ipso, ())
             if atoms[n] == "C" and 6 in sizes.get(n, set())]
    substituted = 0
    for oc in ortho:
        for n, _o in adj.get(oc, ()):
            if n in (ipso,):
                continue
            # a substituent carbon that is NOT part of the aromatic ring
            if atoms[n] == "C" and 6 not in sizes.get(n, set()):
                substituted += 1
                break
    return substituted >= 2


# --------------------------------------------------------------------------------------------------------------
# The prototype CONTINUOUS estimator (three-valued, fail-closed)
# --------------------------------------------------------------------------------------------------------------

FEASIBLE = "FEASIBLE"
NOT_FEASIBLE = "NOT_FEASIBLE"
UNKNOWN = "UNKNOWN"

#: Recognized-inert element whitelist (the R51 "positively recognize the SAFE set" discipline).  A molecule with
#: any other element is declined (-> UNKNOWN), never confidently FEASIBLE.
_SAFE_ELEMENTS = {"C", "H", "O", "N", "S"}


def _has_remote_acid_labile(mol) -> bool:
    """A coarse detector for the acid-labile groups Fischer's acid destroys: an ACETAL/KETAL carbon (one carbon
    bonded to two single-bonded -O- ethers) or an EPOXIDE (an O in a 3-membered ring).  This is NOT an attempt to
    enumerate the unbounded acid-labile universe -- it is one concrete member, present to show the guard FIRES;
    the Phase-1 guard whitelists inert scaffolds and fails closed on the rest."""
    atoms = mol.atoms
    adj = _adjacency(mol)
    sizes = _ring_membership(mol)
    # epoxide: O in a 3-membered ring
    for i, el in enumerate(atoms):
        if el == "O" and 3 in sizes.get(i, set()):
            return True
    # acetal/ketal: a carbon with two single-bonded ether oxygens (each O bonded to 2 carbons)
    for i, el in enumerate(atoms):
        if el != "C":
            continue
        ether_os = 0
        for n, o in adj.get(i, ()):
            if atoms[n] == "O" and o == 1:
                heavy = [m for m, _ in adj.get(n, ()) if atoms[m] != "H"]
                if len(heavy) == 2 and all(atoms[m] == "C" for m in heavy):
                    ether_os += 1
        if ether_os >= 2:
            return True
    return False


def estimate_fischer_feasibility(alcohol, acid) -> str:
    """The prototype continuous estimator, fail-closed.  Returns FEASIBLE / NOT_FEASIBLE / UNKNOWN.

    Order matters: the DOMAIN GUARD (fail-closed) is consulted FIRST, so a determinant the features cannot
    measure yields UNKNOWN (no reward), never a confident FEASIBLE.  Only inside the guarded domain does the
    estimator make a confident call.
    """
    # ---- DOMAIN GUARD (fail closed; the bounded-vs-unbounded escape) ----
    for mol in (alcohol, acid):
        if any(el not in _SAFE_ELEMENTS for el in mol.atoms):
            return UNKNOWN                                   # unrecognized element scaffold
        if _has_remote_acid_labile(mol):
            return UNKNOWN                                   # acid-labile group -> decline (unbounded axis)
    if _carbinol_carbon(alcohol) is None or _acyl_carbon(acid) is None:
        return UNKNOWN                                       # not the reaction shape we model
    if _carbinol_is_sp2(alcohol):
        return UNKNOWN                                       # PHENOL/ENOL -- out of the sp3-carbinol domain (P0.3 census)
    if _carbinol_alpha_heteroatom(alcohol):
        return UNKNOWN                                       # alpha-heteroatom cation stabilization (off-scale)
    if _carbinol_adjacent_strained_ring(alcohol):
        return UNKNOWN                                       # sigma-conjugation the pi-flag can't read
    if _acyl_r_is_aromatic(acid) and _acyl_ortho_disubstituted(acid):
        # ortho steric inhibition is a CONFIDENT not-feasible, not a decline -- the flag reads it directly
        return NOT_FEASIBLE

    # ---- CONFIDENT calls inside the domain ----
    if out_of_center_nucleophiles(alcohol):
        return NOT_FEASIBLE                                  # competing nucleophile changes the product class
    score = cation_stability_score(alcohol)
    if score < 0:
        return UNKNOWN
    if score >= 3:
        return NOT_FEASIBLE                                  # E1/SN1 dominates (tert / sec-benzylic)
    return FEASIBLE


def acyl_rate_rank(acid_r_group: str) -> "float | None":
    """The continuous acid-side RANKING refinement from Taft E_s (higher E_s -> faster Fischer).  A RANKING term
    for the affordability axis, NOT a feasibility gate -- returned separately to show its distinct role."""
    return TAFT_ES.get(acid_r_group)


# --------------------------------------------------------------------------------------------------------------
# The CORE battery: every determinant + Bearing A's new pairs + guard stress cases, with textbook kitchen-truth.
# This is the CALIBRATION set the estimator was shaped against; it reads clean (false_vouch=0) and shows the
# alcohol-side core is sound.  The KILL lives in _ADVERSARIAL_FALSE_VOUCHES below, found by the design gate on
# axes this set never varied -- the daniel calibration-on-a-subset lesson, live.
# --------------------------------------------------------------------------------------------------------------

#: (label, alcohol SMILES, acid SMILES, acid_r_group_for_Es, kitchen_feasible_truth, citation-comment)
_CORE_BATTERY = (
    # --- alcohol-side: the R52 documented degree collision ---
    ("pentan-1-ol + AcOH", "CCCCCO", "CC(=O)O", "methyl", True,
     "primary alkyl Fischer -> pentyl acetate, a kitchen ester"),
    ("tert-butanol + AcOH", "CC(C)(C)O", "CC(=O)O", "methyl", False,
     "tertiary alcohol dehydrates via E1 under acid; tert-butyl esters need non-Fischer routes"),
    # --- alcohol-side: Bearing A's NEW collision (degree-2 benzylic vs degree-2 clean) ---
    ("isopropanol + AcOH", "CC(C)O", "CC(=O)O", "methyl", True,
     "secondary alkyl Fischer -> isopropyl acetate, works (slower than 1deg but clean)"),
    ("1-phenylethanol + AcOH", "CC(O)c1ccccc1", "CC(=O)O", "methyl", False,
     "secondary BENZYLIC: resonance-stabilized cation -> SN1/dehydration to styrene competes under acid"),
    # --- alcohol-side: the discriminating controls (benzylic/allylic that DO work at degree 1) ---
    ("benzyl alcohol + AcOH", "OCc1ccccc1", "CC(=O)O", "methyl", True,
     "primary benzylic: benzyl acetate IS a real ester; 1deg benzylic cation not stable enough to divert"),
    ("allyl alcohol + AcOH", "OCC=C", "CC(=O)O", "methyl", True,
     "primary allylic: allyl acetate is industrial; 1deg allylic esterifies cleanly"),
    ("neopentyl alcohol + AcOH", "OCC(C)(C)C", "CC(=O)O", "methyl", True,
     "primary, beta-branched: Fischer O-acylation is fine (SN2 block is irrelevant to esterification)"),
    ("3-buten-2-ol + AcOH", "CC(O)C=C", "CC(=O)O", "methyl", False,
     "secondary allylic: allylic SN1 transposition/rearrangement under acid -> not a clean Fischer"),
    # --- alcohol-side competing nucleophile (R52's amine blade) ---
    ("5-aminopentanol + AcOH", "NCCCCCO", "CC(=O)O", "methyl", False,
     "free primary amine outcompetes the -OH -> N-acyl amide, changes the product class"),
    # --- acid-side: aliphatic sterics (RANKING, not a gate: all esterify) ---
    ("pentan-1-ol + pivalic", "CCCCCO", "CC(C)(C)C(=O)O", "tert-but-carbonyl", True,
     "pivalic acid IS esterifiable via Fischer, just slow (very negative E_s) -> feasible, low rank"),
    ("pentan-1-ol + benzoic", "CCCCCO", "OC(=O)c1ccccc1", "phenyl", True,
     "benzoic acid Fischer -> pentyl benzoate, classic; aromatic acyl esterifies fine"),
    # --- acid-side: the ortho-steric FEASIBILITY failure (mesitoic) ---
    ("pentan-1-ol + mesitoic", "CCCCCO", "Cc1cc(C)c(C(=O)O)c(C)c1", "aryl-ortho", False,
     "2,4,6-trimethylbenzoic (mesitoic): ortho di-substitution sterically inhibits normal Fischer"),
    # --- domain-guard stress cases: determinants the features CANNOT read -> MUST fail closed to UNKNOWN ---
    ("cyclopropylcarbinol + AcOH", "OCC1CC1", "CC(=O)O", "methyl", False,
     "cyclopropylcarbinyl cation (sigma-conjugation) rearranges under acid -> guard must decline (pi-flag blind)"),
    ("solketal-like acetal alcohol + AcOH", "OCC1OCCO1", "CC(=O)O", "methyl", False,
     "a remote 1,3-dioxolane (acetal) is destroyed by Fischer's acid -> guard must decline (unbounded axis)"),
    ("glycidol + AcOH", "OCC1CO1", "CC(=O)O", "methyl", False,
     "an epoxide is opened by Fischer's acid -> guard must decline"),
    # --- PHENOL / ENOL stress cases (the P0.3 census's find -- battery had none; sp3-carbinol physics is
    #     out of domain for a phenolic reacting O, so the guard must DECLINE, not confidently mis-verdict) ---
    ("phenol + AcOH (phenol as nucleophile)", "Oc1ccccc1", "CC(=O)O", "methyl", False,
     "PHENOL O-acylation with free AcOH is impractical (needs anhydride) AND is not an sp3-carbinol E1 problem "
     "-> out of domain -> DECLINE (right answer via right reason = fail-closed, not wrong-physics NOT_FEASIBLE)"),
    ("salicylic acid as nucleophile + AcOH (aspirin route)", "O=C(O)c1ccccc1O", "CC(=O)O", "methyl", False,
     "the P0.3 census's LIVE aspirin pair: salicylic acid's phenol O is the reacting site -> out of the carbinol "
     "domain -> MUST decline to UNKNOWN (was a confident NOT_FEASIBLE via the phenol-misclassification hole)"),
)


#: THE KILL, frozen (R52 discipline: prove the kill, don't hide it).  The surviving false-VOUCHes the five-bearing
#: design gate found on axes the core battery never varied.  Kitchen-truth for EVERY row is NOT-feasible; the
#: estimator returns FEASIBLE for every one -- a confident capability claim on an infeasible route, the exact
#: R49/R51 fatal error.  Left UNPATCHED on purpose: each is a hole in a hand-enumerated guard, and patching them
#: only proves the unbounded-hazard theorem again one step out.
#: (label, alcohol SMILES, acid SMILES, determinant-axis, finder, why-not-kitchen)
_ADVERSARIAL_FALSE_VOUCHES = (
    ("ethanol + acetoacetic acid", "CCO", "CC(=O)CC(=O)O", "acid-side beta-keto decarboxylation", "dalembert",
     "a beta-keto acid decarboxylates (acetone + CO2) under Fischer acid/heat; ethyl acetoacetate is made from "
     "diketene/Claisen, never Fischer of acetoacetic acid -- the acid does not survive the conditions"),
    ("ethanol + 3-oxoglutaric acid", "CCO", "OC(=O)CC(=O)CC(=O)O", "acid-side beta-keto decarboxylation", "dalembert",
     "a doubly-beta-keto (1,3-dicarbonyl) acid decarboxylates readily -- the tropinone-synthesis property"),
    ("1-(ethylthio)ethanol + AcOH", "OC(C)SCC", "CC(=O)O", "alpha-thioether thionium (S guard gap)", "evil-morty",
     "an alpha-alkylthio carbinol ionizes to a sulfur-stabilized thionium ion -> SN1 dominates; S is in "
     "_SAFE_ELEMENTS but omitted from _carbinol_alpha_heteroatom (O/N only) and the thiol detector"),
    ("furfuryl alcohol + AcOH", "OCc1ccco1", "CC(=O)O", "heteroaryl cation magnitude (binary conj flag)", "evil-morty/daniel",
     "the 2-furylmethyl cation is far more stabilized than benzyl (ring-O donation) -> acid-catalyzed "
     "resinification/self-polymerization dominates; the binary conjugation flag gives it benzyl's exact vector"),
)


def _mol_pair(alc_smiles: str, acid_smiles: str):
    return parse_smiles(alc_smiles), parse_smiles(acid_smiles)


def run_adversarial() -> "list[dict]":
    """Run the gate-found KILL cases.  Kitchen-truth is NOT-feasible for all; a row is a surviving false-VOUCH
    iff the estimator returns FEASIBLE (it does, for all of them -- that is the defer)."""
    rows = []
    for label, alc_s, acid_s, axis, finder, _why in _ADVERSARIAL_FALSE_VOUCHES:
        verdict = estimate_fischer_feasibility(*_mol_pair(alc_s, acid_s))
        rows.append({
            "label": label, "axis": axis, "finder": finder, "verdict": verdict,
            "is_false_vouch": verdict == FEASIBLE,
        })
    return rows


def run_battery() -> "list[dict]":
    rows = []
    for label, alc_s, acid_s, r_group, truth, _cite in _CORE_BATTERY:
        alc, acid = _mol_pair(alc_s, acid_s)
        verdict = estimate_fischer_feasibility(alc, acid)
        # classify the outcome against kitchen-truth
        if verdict == UNKNOWN:
            kind = "declined"                                # fail-closed: always safe
        elif verdict == FEASIBLE and truth:
            kind = "true_feasible"
        elif verdict == NOT_FEASIBLE and not truth:
            kind = "true_not_feasible"
        elif verdict == FEASIBLE and not truth:
            kind = "FALSE_VOUCH"                             # the fatal error (R49/R51)
        else:  # NOT_FEASIBLE and truth
            kind = "false_exclude"                           # coverage loss (tolerable)
        rows.append({
            "label": label,
            "kitchen_truth": "feasible" if truth else "not_feasible",
            "verdict": verdict,
            "cation_score": cation_stability_score(alc),
            "outcome": kind,
        })
    return rows


def _documented_pair_separated(rows) -> bool:
    d = {r["label"]: r["verdict"] for r in rows}
    # R52 documented degree pair
    p1 = d["pentan-1-ol + AcOH"] == FEASIBLE and d["tert-butanol + AcOH"] == NOT_FEASIBLE
    return p1


def _bearing_a_pair_separated(rows) -> bool:
    d = {r["label"]: r["verdict"] for r in rows}
    # the NEW degree-2 benzylic collision degree-alone could not separate
    return d["isopropanol + AcOH"] == FEASIBLE and d["1-phenylethanol + AcOH"] == NOT_FEASIBLE


def acid_rate_ranking_demo() -> "list[dict]":
    """Demonstrate the Taft E_s table's DISTINCT role: a continuous acid-side RATE ranking, NOT a feasibility
    gate.  All of these acids esterify (feasible); E_s orders their kitchen rate (acetic fastest, pivalic
    slowest).  This is the signal the affordability Pareto axis would consume, separate from the feasibility
    verdict -- showing why a CONTINUOUS estimator does what a boolean class key never could."""
    demo = []
    for r_group in ("methyl", "ethyl", "isopropyl", "neopentyl", "tert-butyl", "phenyl"):
        demo.append({"acid_r_group": r_group, "taft_es": acyl_rate_rank(r_group)})
    demo.sort(key=lambda d: (d["taft_es"] is None, -(d["taft_es"] or 0.0)))
    return demo


def _payload() -> dict:
    rows = run_battery()
    adv = run_adversarial()
    n_false_vouch = sum(1 for r in rows if r["outcome"] == "FALSE_VOUCH")
    n_true_feasible = sum(1 for r in rows if r["outcome"] == "true_feasible")
    n_true_not = sum(1 for r in rows if r["outcome"] == "true_not_feasible")
    n_false_exclude = sum(1 for r in rows if r["outcome"] == "false_exclude")
    n_declined = sum(1 for r in rows if r["outcome"] == "declined")
    adv_vouches = sum(1 for r in adv if r["is_false_vouch"])
    adv_axes = sorted({r["axis"] for r in adv if r["is_false_vouch"]})
    core_clean = (
        n_false_vouch == 0 and n_true_feasible > 0
        and _documented_pair_separated(rows) and _bearing_a_pair_separated(rows) and n_declined > 0
    )
    return {
        "schema": "poor-man-reactivity-estimator-phase0-defer-01",
        "round": 53,
        "phase": 0,
        "core_battery": rows,
        "adversarial_false_vouches": adv,
        "acid_rate_ranking": acid_rate_ranking_demo(),
        "counts": {
            "core_total": len(rows),
            "core_false_vouch": n_false_vouch,         # 0: the core/calibration set is clean
            "true_feasible": n_true_feasible,          # non-vacuous FEASIBLE set (the alcohol-side core works)
            "true_not_feasible": n_true_not,
            "false_exclude": n_false_exclude,
            "declined_unknown": n_declined,            # guard fires on the enumerated hazards it DOES know
            "adversarial_false_vouches": adv_vouches,  # >0: the KILL -- leaks the guard does NOT enumerate
            "adversarial_axes": len(adv_axes),
        },
        "core_clean": core_clean,                      # the POSITIVE result: alcohol-side core sound + calibrated
        "documented_degree_pair_separated": _documented_pair_separated(rows),
        "bearing_a_benzylic_pair_separated": _bearing_a_pair_separated(rows),
        "adversarial_axis_list": adv_axes,
        # THE VERDICT: DEFER #4.  The core/calibration battery is clean, but INDEPENDENT adversaries produced
        # surviving false-VOUCHes on >=2 distinct determinant axes the bounded feature set + the hand-enumerated
        # guard can neither read nor decline.  Making the classifier continuous MOVED the R49/R50/R52 collision
        # into the guard; it did not close it.  Sound only inside a friendly subset -> NOT shovel-ready.
        "defer_verdict": (
            core_clean
            and adv_vouches >= 1
            and len(adv_axes) >= 2
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the Phase-0 DEFER #4 result holds against live code: the core battery is clean AND the gate's
    surviving false-VOUCHes still reproduce on multiple independent axes."""
    p = _payload()
    c = p["counts"]
    # the POSITIVE result: the alcohol-side core / calibration battery is clean and non-vacuous
    assert c["core_false_vouch"] == 0, f"core battery not clean: {p['core_battery']}"
    assert c["true_feasible"] > 0, f"vacuous FEASIBLE set (R52 base-rate trap): {c}"
    assert c["declined_unknown"] > 0, f"guard never fires on its enumerated hazards: {c}"
    assert p["documented_degree_pair_separated"], "R52 degree collision no longer separated"
    assert p["bearing_a_benzylic_pair_separated"], "Bearing A benzylic collision no longer closed"
    # the KILL (the defer's evidence): surviving false-VOUCHes on >=2 independent axes the guard can't enumerate
    assert all(r["is_false_vouch"] for r in p["adversarial_false_vouches"]), \
        f"an adversarial case stopped false-VOUCHing (guard changed under it?): {p['adversarial_false_vouches']}"
    assert c["adversarial_false_vouches"] >= 1, "the defer's evidence vanished: no surviving false-VOUCH"
    assert c["adversarial_axes"] >= 2, f"the kill must span independent axes: {p['adversarial_axis_list']}"
    assert p["defer_verdict"], f"DEFER #4 verdict does not hold: {p}"
    return True


if __name__ == "__main__":  # pragma: no cover
    ok = validate()
    print(f"validate() -> {ok}")
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    import pprint
    pprint.pprint(_payload())
