"""POOR-MAN-SYMMETRIC-WHITELIST-PHASE05-01 (R54, Phase 0.5): the base-rate/vacuity gate on the escape all
FOUR prior defers (R49/R50/R52/R53) converged on -- a SYMMETRIC POSITIVE safe-set whitelist on BOTH reaction
centers.

Background (the escape, named by DEFER #4).  A blacklist-style fail-closed guard cannot reach zero false-VOUCH
because the hazard space is unbounded ([[a-fail-closed-guard-is-a-blacklist-of-an-unbounded-hazard-space]]):
patch phenol, the sulfur/beta-keto/furfuryl leaks open one step out.  The R51 discipline
([[a-declared-unrecognized-input-must-block]]) inverts the polarity: recognize the SAFE set POSITIVELY and
decline everything else.  R53 applied it to ONE side (the element whitelist); the escape is to apply it
SYMMETRICALLY to EVERY reaction center -- confidently FEASIBLE only when the carbinol neighbourhood AND the
acyl neighbourhood are BOTH positively recognized-inert, UNKNOWN otherwise.  Such a whitelist is SOUND BY
CONSTRUCTION: it never emits a confident FEASIBLE on a scaffold it does not positively recognize, so a hazard
it has never heard of yields UNKNOWN, not a false-VOUCH.

But soundness-by-construction is cheap; the whole question DEFER #4 handed forward is the one R52 raised and
no round has answered ([[base-rate-dependent-fail-closed-polarity]]):

    Does the FEASIBLE (VOUCH) set SURVIVE the whitelist, or does the whitelist swallow the deployment
    population -- i.e. is the reward VACUOUS (blesses ~nothing) or, worse, ANTI-TELOS (blesses only the
    conventional and declines exactly the clever unconventional-but-sound routes the arch exists to surface)?

This probe BUILDS the symmetric positive whitelist and MEASURES it, then a FIVE-BEARING adversarial design gate
(dalembert / evil-morty / daniel / birdperson / butter-robot) attacked it.  Every load-bearing claim below was
independently reproduced by the author against this frozen file.

=============================================================================================================
GATE OUTCOME (R54, Phase-0.5, five-bearing gate at HEAD 8678ad3): **DEFER #5** -- the FIFTH verified defer of
the ingenuity reward, and the one that KILLS the escape all four prior defers named.  The instrument's OWN core
battery reads clean (false_vouch=0 on 25 cases; it CLOSES the entire R53 kill -- beta-keto, alpha-thioether,
furfuryl, tert, sec-benzylic all correctly declined -- and blesses 5/7 of my "unconventional" reals).  But that
`sound=True` is a CHECK-DERIVED-FROM-ITS-OWN-SUBJECT: I designed the radius-2 pure-hydrocarbon recognizer
KNOWING the R53 kill set, then tested on it.  The gate broke the FEASIBLE set on THREE independent axes the
positive recognizer can neither read nor decline:

  * dalembert + evil-morty (the clean tombstone): the WHOLE alpha,beta-UNSATURATED ACID class VOUCHes and is
    kitchen-infeasible -- acrylic (C=CC(=O)O), methacrylic (CC(=C)C(=O)O), propiolic (C#CC(=O)O), plus
    crotonic/sorbic/maleic/fumaric/cinnamic/itaconic.  Acrylates/methacrylates POLYMERIZE under hot protic acid
    (their real esterification NEEDS a radical inhibitor -- MEHQ/hydroquinone -- absent from any kitchen);
    propiolic oxa-Michael-adds the alcohol.  The recognizer's `_neighbourhood_is_pure_hydrocarbon` reads ELEMENT
    identity (C/H), never BOND ORDER, so a C=C/C#C conjugated to the carbonyl is invisible.  "Pure hydrocarbon"
    is NOT "inert".
  * evil-morty (a REGRESSION vs R53): remote acid-labile groups PAST radius 2 -- a remote epoxide (OCCCC1CO1)
    or acetal (OCCCC(OC)OC) alcohol -- VOUCH, while the R53 estimator DECLINED them via a molecule-wide
    `_has_remote_acid_labile` guard this positive recognizer DROPPED.  The radius-2 scan sees nothing; glycidol
    declines only by the ACCIDENT of its oxygen sitting inside radius 2.
  * evil-morty (guard vacuity): the ring-heteroatom decline keys on `6 in sizes` (benzene only), so 5-membered
    heteroaromatic acids bypass it -- pyrrole-2-carboxylic (CO + OC(=O)c1ccc[nH]1) VOUCHes and resinifies under
    strong acid.  (And a code quirk: the "ipso" test at recognize_inert_acyl matches ANY carbon double-bonded to
    carbon -- a vinyl, not just an aromatic -- routing every acyclic unsaturated acid into the benzoic branch
    whose ring loop is then vacuously empty.  Fixing it does NOT stop the leak: the aliphatic branch VOUCHes
    acrylic anyway.)

THE THEOREM (why this is defer #5, not a bug list): inverting a fail-closed BLACKLIST (R53) to a POSITIVE
whitelist does NOT reach zero false-VOUCH if "recognized-inert" is defined by an ELEMENT census over a bounded
radius, because reactivity lives in bond order + conjugation + remote groups the census cannot read.  The
R49/R50/R52/R53 collision did not close -- it MOVED from the blacklist guard into the DEFINITION of
"recognized-inert", which now must enumerate reactive-but-pure-hydrocarbon motifs (vinyl/alkynyl/dienes/
cumulenes/extended-aryl-conjugation) over an UNBOUNDED space: the R53 theorem verbatim, one alphabet in (pi
bonds instead of heteroatoms) [[a-fail-closed-guard-is-a-blacklist-of-an-unbounded-hazard-space]].  And the
"patch" is proven un-clean (`run_patch_collision` below): declining alpha,beta-unsaturation to close acrylic
ALSO false-EXCLUDEs crotonic/cinnamic/sorbic (real feasible esters) -- the R52 base-rate/vacuity scissors, live
[[base-rate-dependent-fail-closed-polarity]].

THE DUAL FAILURE (base rate): the soundness the whitelist attempts is bought by declining the polyfunctional
feasible population.  daniel drew an independent 47-row deployment battery (all truth-feasible): feasible_recall
fell from my friendly-subset 0.875 to **0.574** (polyfunctional-only subset 0.444) -- amino-, halo-, hydroxy-,
polyol-acids all near 0% recall.  Simultaneously UNSOUND (blesses infeasible acrylates) AND anti-telos (declines
feasible oil-of-wintergreen).  ZERO live consumer: a fresh full-registry sweep (all 45 targets) found the
whitelist VOUCHes exactly ONE Fischer target (isopentyl acetate -- whose only registry route is a
chemically-BOGUS transesterification-shaped graph-surgery, real precursor sourced-INDUSTRIAL) and DECLINES the
four genuinely-feasible aromatic ones (aspirin/paracetamol/methyl salicylate/4-aminophenyl acetate), so the only
non-trivial wiring (UNKNOWN-as-blocker) would SINK four correct rankings.

WHAT IS BANKED: the escape's PRINCIPLE (symmetric positive recognition) remains right; the carbinol-side core
(degree + cation score + out-of-center nucleophile, from the R53 alcohol-side work) is the one place all five
bearings agree reads a real reaction-center determinant and is SOUND.  The next escape must recognize inert
SCAFFOLDS BY NAME (n-alkyl, non-benzylic sec-alkyl, bare/ortho-mono benzoic) with a saturation-state clause AND
a proven live consumer -- not an element census; that is a genuinely bigger model, now with the failure mode of
the naive version proven.

This probe is the DEFER ARTIFACT: it FREEZES the positive result (the clean friendly-subset battery) AND the
kill (the surviving false-VOUCHes across three independent axes, the patch-collision, the base-rate note).  The
recognizers are LEFT AS-IS with the leaks visible ON PURPOSE (R52/R53 discipline) -- patching any one only proves
the unbounded theorem again one step out (see `run_patch_collision`).
=============================================================================================================

RDKit-free; runs the REAL production parser and reuses the R53 probe's VERIFIED feature extractors so the
degree/cation/acyl facts are the SAME functions (no re-derivation drift).  Kitchen-truth labels are
textbook-ASSERTED with a phys-org citation per row, same discipline as R50/R52/R53.
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
from experiments.poor_man_reactivity_estimator_phase0_probe import (
    _carbinol_carbon,
    _acyl_carbon,
    _acyl_ortho_disubstituted,
    cation_stability_score,
    _ring_membership,
)

#: Frozen fingerprint of :func:`_payload`.  Breaks loudly if the DEFER #5 verdict, the recognizers, the battery,
#: or any adversarial kill row moves against live code.
FROZEN_HASH = "931976834fb7074e1dc8cd3ab38ca82252995b6fca771ed9926faf3b7d887572"

FEASIBLE = "FEASIBLE"
UNKNOWN = "UNKNOWN"

#: Recognized-inert element whitelist AT A REACTION CENTER's local neighbourhood.  Note S is DELIBERATELY absent
#: from the *neighbourhood* scan (unlike R53's molecule-wide _SAFE_ELEMENTS): an alpha-thioether must be DECLINED
#: (the R53 evil-morty thionium leak), and a positive recognizer achieves that by only ever recognizing pure
#: C/H(/the reacting O) local scaffolds -- S in the neighbourhood is simply "not recognized-inert".
_INERT_NEIGHBOURHOOD_ELEMENTS = {"C", "H"}


# --------------------------------------------------------------------------------------------------------------
# radius-bounded neighbourhood scan (the positive recognizer's core primitive)
# --------------------------------------------------------------------------------------------------------------

def _atoms_within_radius(mol, center: int, radius: int, exclude: "set[int]") -> "set[int]":
    """The set of atom indices within graph distance ``radius`` of ``center`` (inclusive), not crossing into
    ``exclude`` (used to pin the reacting O so the -OH/-COOH oxygens are not mistaken for a hazard heteroatom)."""
    adj = _adjacency(mol)
    seen = {center}
    frontier = {center}
    for _ in range(radius):
        nxt: "set[int]" = set()
        for a in frontier:
            for n, _o in adj.get(a, ()):
                if n in exclude or n in seen:
                    continue
                nxt.add(n)
        seen |= nxt
        frontier = nxt
    return seen


def _neighbourhood_is_pure_hydrocarbon(mol, center: int, radius: int, exclude: "set[int]") -> bool:
    """True iff every atom within ``radius`` of ``center`` (excluding the pinned reacting oxygens) is C or H.
    This POSITIVELY recognizes an inert hydrocarbon environment; ANY heteroatom (O/N/S/halogen/...) in range
    means 'not recognized-inert' -> decline.  Aromatic all-carbon rings pass (benzylic/benzoic are inert)."""
    idxs = _atoms_within_radius(mol, center, radius, exclude)
    return all(mol.atoms[i] in _INERT_NEIGHBOURHOOD_ELEMENTS for i in idxs)


def _has_small_ring_in(mol, idxs: "set[int]") -> bool:
    """True if any atom in ``idxs`` sits in a ring smaller than 6 (strained cyclopropyl/cyclobutyl -> cation
    sigma-conjugation / rearrangement).  A 6-ring (benzene) is inert and does NOT trip this."""
    sizes = _ring_membership(mol)
    return any(any(s < 6 for s in sizes.get(i, set())) for i in idxs)


def _carbon_bears_double_bond_o(mol, c: int) -> bool:
    adj = _adjacency(mol)
    return any(order >= 2 and mol.atoms[n] == "O" for n, order in adj.get(c, ()))


# --------------------------------------------------------------------------------------------------------------
# the symmetric POSITIVE recognizers (recognize INERT; decline everything else)
# --------------------------------------------------------------------------------------------------------------

def recognize_inert_carbinol(alcohol) -> bool:
    """POSITIVELY recognize an inert sp3 carbinol scaffold that esterifies cleanly (no E1/SN1 diversion, no
    cation over-stabilization, no acid-labile neighbour).  Recognized iff ALL hold:
      * a reacting sp3 carbinol carbon exists (not a phenol/enol),
      * it is primary or secondary (degree <= 2) with cation-stability score <= 2 (closes tert + sec-benzylic),
      * its radius-2 neighbourhood is PURE HYDROCARBON (no alpha/beta O/N/S -> closes alpha-heteroatom,
        thioether thionium, furfuryl ring-O, aminoalcohol),
      * no ring smaller than 6 in that neighbourhood (closes cyclopropylcarbinyl sigma-conjugation),
      * no competing out-of-center nucleophile anywhere (R52 blade).
    Everything not matching every clause is DECLINED (not recognized-inert), never a false-VOUCH."""
    atoms = alcohol.atoms
    adj = _adjacency(alcohol)
    o = _reacting_hydroxyl_o(atoms, adj)
    c = _carbinol_carbon(alcohol)
    if o is None or c is None:
        return False
    if any(order >= 2 for _n, order in adj.get(c, ())):     # sp2 carbinol (phenol/enol) -> not this domain
        return False
    deg = _carbinol_degree(alcohol)
    if deg < 0 or deg > 2:                                   # tertiary -> E1
        return False
    if cation_stability_score(alcohol) > 2:                 # sec-benzylic etc. -> SN1
        return False
    idxs = _atoms_within_radius(alcohol, c, 2, exclude={o})
    if not _neighbourhood_is_pure_hydrocarbon(alcohol, c, 2, exclude={o}):
        return False
    if _has_small_ring_in(alcohol, idxs):
        return False
    if out_of_center_nucleophiles(alcohol):
        return False
    return True


def recognize_inert_acyl(acid) -> bool:
    """POSITIVELY recognize an inert carboxylic-acid scaffold that esterifies cleanly under Fischer.  Recognized
    iff a carboxyl carbon exists AND its acyl R is one of two positively-recognized inert shapes:
      * ALIPHATIC-inert: the radius-2 neighbourhood of the carboxyl carbon (excluding its own two O's) is pure
        hydrocarbon AND no carbon within radius 2 bears a C=O (closes beta-keto decarboxylation; also declines
        alpha-keto and di-acids -- a tolerated coverage loss, never a false-VOUCH), OR
      * simple AROMATIC (benzoic): the R is an aromatic carbon, NOT ortho-di-substituted (closes mesitoic steric),
        and the ring carbons carry no non-aromatic-carbon substituent within radius 2 of the ipso other than the
        acyl itself (a positively-recognized bare/ortho-mono benzoic; anything fancier is declined).
    Everything else is DECLINED."""
    atoms = acid.atoms
    adj = _adjacency(acid)
    c = _acyl_carbon(acid)
    if c is None:
        return False
    # pin the carboxyl's own two oxygens so they are not read as hazard heteroatoms
    carboxyl_os = {n for n, _o in adj.get(c, ()) if atoms[n] == "O"}

    # is R aromatic (an ipso aromatic carbon attached to the carboxyl)?
    ipso = None
    for n, _o in adj.get(c, ()):
        if atoms[n] == "C" and any(o2 >= 2 and atoms[m] == "C" for m, o2 in adj.get(n, ())):
            ipso = n
            break

    if ipso is None:
        # ALIPHATIC-inert branch
        idxs = _atoms_within_radius(acid, c, 2, exclude=carboxyl_os)
        idxs.discard(c)
        if not all(atoms[i] in _INERT_NEIGHBOURHOOD_ELEMENTS for i in idxs):
            return False
        # no carbon in the radius-2 neighbourhood bears a carbonyl (beta-keto / di-acid) -- radius-2 catches
        # the beta position; alpha (radius-1) is covered too.
        if any(atoms[i] == "C" and _carbon_bears_double_bond_o(acid, i) for i in idxs):
            return False
        if _has_small_ring_in(acid, idxs):
            return False
        return True

    # AROMATIC (benzoic) branch
    if _acyl_ortho_disubstituted(acid):
        return False                                        # mesitoic-type ortho steric inhibition
    # every substituent on the ring within radius 2 of the ipso must be an aromatic C or H (bare/ortho-mono-C
    # benzoic); a heteroatom substituent (o-OH salicylic, o-NH2 anthranilic, nitro, halogen) is NOT recognized
    # -> declined.  (salicylic IS a real Fischer acid -> this is a deliberate coverage loss, measured below.)
    sizes = _ring_membership(acid)
    ring_atoms = {i for i in range(len(atoms)) if 6 in sizes.get(i, set())}
    for i in ring_atoms:
        for n, _o in adj.get(i, ()):
            if n == c or n in ring_atoms:
                continue
            if atoms[n] not in _INERT_NEIGHBOURHOOD_ELEMENTS:
                return False                                # heteroatom ring substituent -> not recognized
    return True


def symmetric_whitelist_verdict(alcohol, acid) -> str:
    """FEASIBLE iff BOTH reaction centers are positively recognized-inert; UNKNOWN otherwise.  Never NOT_FEASIBLE
    and never a confident FEASIBLE on an unrecognized scaffold -> sound-by-construction (zero false-VOUCH)."""
    if recognize_inert_carbinol(alcohol) and recognize_inert_acyl(acid):
        return FEASIBLE
    return UNKNOWN


# --------------------------------------------------------------------------------------------------------------
# the DEPLOYMENT-REPRESENTATIVE battery (NOT a friendly subset): feasible reals across the population + the kill.
# conv = "conventional" (a textbook-obvious esterification) | "unconv" = an unconventional-but-SOUND route (the
# ingenuity target the arch exists to surface).  truth = kitchen-feasible.
# --------------------------------------------------------------------------------------------------------------
#: (label, alcohol SMILES, acid SMILES, truth, kind, citation)
_BATTERY = (
    # ---- feasible, CONVENTIONAL: the plain aliphatic bulk (the deployment base rate) ----
    ("methanol + acetic", "CO", "CC(=O)O", True, "conv", "methyl acetate, textbook Fischer"),
    ("ethanol + acetic", "CCO", "CC(=O)O", True, "conv", "ethyl acetate, the archetypal Fischer ester"),
    ("propan-1-ol + acetic", "CCCO", "CC(=O)O", True, "conv", "n-propyl acetate"),
    ("isopropanol + acetic", "CC(C)O", "CC(=O)O", True, "conv", "isopropyl acetate, 2deg clean Fischer"),
    ("butan-1-ol + acetic", "CCCCO", "CC(=O)O", True, "conv", "n-butyl acetate, industrial solvent ester"),
    ("pentan-1-ol + acetic", "CCCCCO", "CC(=O)O", True, "conv", "pentyl acetate"),
    ("ethanol + propanoic", "CCO", "CCC(=O)O", True, "conv", "ethyl propanoate"),
    ("ethanol + butanoic", "CCO", "CCCC(=O)O", True, "conv", "ethyl butyrate, pineapple ester"),
    ("methanol + formic", "CO", "OC=O", True, "conv", "methyl formate"),
    # ---- feasible, UNCONVENTIONAL-but-sound (the ingenuity target: clever/nonobvious yet real) ----
    ("isopentyl + acetic (banana oil)", "CC(C)CCO", "CC(=O)O", True, "unconv",
     "isopentyl acetate: the classic 'banana oil' -- a poor-man flavour ester from a branched fusel alcohol"),
    ("benzyl + acetic", "OCc1ccccc1", "CC(=O)O", True, "unconv",
     "benzyl acetate: 1deg-benzylic, feasible; a fragrance ester the naive 'no aryl' rule would fear"),
    ("allyl + acetic", "OCC=C", "CC(=O)O", True, "unconv",
     "allyl acetate: 1deg-allylic, industrial; feasible despite the adjacent pi"),
    ("pentanol + benzoic", "CCCCCO", "OC(=O)c1ccccc1", True, "unconv",
     "pentyl benzoate: an aromatic ACID esterifies cleanly -- nonobvious to a 'keep it aliphatic' heuristic"),
    ("methanol + salicylic (wintergreen)", "CO", "O=C(O)c1ccccc1O", True, "unconv",
     "methyl salicylate (oil of wintergreen): salicylic acid + MeOH + H2SO4 IS the real Fischer prep; the "
     "ortho-OH is a spectator on the acyl side"),
    ("ethanol + levulinic (gamma-keto)", "CCO", "CC(=O)CCC(=O)O", True, "unconv",
     "ethyl levulinate: a gamma-keto acid esterifies cleanly (keto too remote to decarboxylate) -- a real "
     "bio-derived fuel-additive ester"),
    ("ethanol + pyruvic (alpha-keto)", "CCO", "CC(=O)C(=O)O", True, "unconv",
     "ethyl pyruvate: an alpha-keto acid DOES Fischer-esterify (real commercial ester)"),
    # ---- INFEASIBLE (the kill set -- must all be DECLINED; a VOUCH here is the fatal false-VOUCH) ----
    ("tert-butanol + acetic", "CC(C)(C)O", "CC(=O)O", False, "kill",
     "3deg alcohol dehydrates via E1; tert-butyl esters need non-Fischer routes"),
    ("1-phenylethanol + acetic", "CC(O)c1ccccc1", "CC(=O)O", False, "kill",
     "2deg benzylic: resonance cation -> SN1/dehydration to styrene competes"),
    ("ethanol + acetoacetic (beta-keto)", "CCO", "CC(=O)CC(=O)O", False, "kill",
     "beta-keto acid decarboxylates (acetone + CO2) under Fischer acid/heat -- dalembert's R53 kill"),
    ("1-(ethylthio)ethanol + acetic", "OC(C)SCC", "CC(=O)O", False, "kill",
     "alpha-thioether ionizes to a thionium ion -> SN1 -- evil-morty's R53 S-gap leak"),
    ("furfuryl + acetic", "OCc1ccco1", "CC(=O)O", False, "kill",
     "2-furylmethyl cation (ring-O donation) -> acid resinification -- evil-morty/daniel's R53 leak"),
    ("cyclopropylcarbinol + acetic", "OCC1CC1", "CC(=O)O", False, "kill",
     "cyclopropylcarbinyl sigma-conjugation rearranges under acid"),
    ("glycidol + acetic", "OCC1CO1", "CC(=O)O", False, "kill",
     "an epoxide is opened by Fischer's acid"),
    ("5-aminopentanol + acetic", "NCCCCCO", "CC(=O)O", False, "kill",
     "free primary amine outcompetes the -OH -> amide (wrong product class)"),
    ("pentanol + mesitoic", "CCCCCO", "Cc1cc(C)c(C(=O)O)c(C)c1", False, "kill",
     "2,4,6-trimethylbenzoic: ortho di-substitution sterically inhibits Fischer"),
)


def run_battery() -> "list[dict]":
    rows = []
    for label, alc_s, acid_s, truth, kind, _cite in _BATTERY:
        alc, acid = parse_smiles(alc_s), parse_smiles(acid_s)
        verdict = symmetric_whitelist_verdict(alc, acid)
        if verdict == FEASIBLE and truth:
            outcome = "true_vouch"
        elif verdict == FEASIBLE and not truth:
            outcome = "FALSE_VOUCH"            # fatal (R49/R51)
        elif verdict == UNKNOWN and not truth:
            outcome = "true_decline"           # correctly declined an infeasible route
        else:                                  # UNKNOWN and truth
            outcome = "false_exclude"          # base-rate coverage loss (tolerable, but the vacuity cost)
        rows.append({
            "label": label, "truth": "feasible" if truth else "infeasible",
            "kind": kind, "verdict": verdict, "outcome": outcome,
        })
    return rows


# --------------------------------------------------------------------------------------------------------------
# THE KILL, frozen (R52/R53 discipline: prove the kill, don't hide it).  The five-bearing gate's surviving
# false-VOUCHes -- kitchen-INfeasible routes the whitelist confidently calls FEASIBLE, on axes the positive
# radius-2 element census cannot read.  Every row VERIFIED by the author against this file.  Left UNPATCHED on
# purpose: each is the R53 unbounded-hazard theorem one alphabet in (see run_patch_collision).
# (label, alcohol SMILES, acid SMILES, axis, finder, why-not-kitchen)
_ADVERSARIAL_FALSE_VOUCHES = (
    ("ethanol + acrylic acid", "CCO", "C=CC(=O)O", "alpha,beta-unsaturation (polymerizes)", "dalembert/evil-morty",
     "acrylic acid + its ester polymerize under hot protic acid; real esterification needs a radical inhibitor "
     "(MEHQ/hydroquinone), absent from any kitchen -> the pot gels, no clean ester"),
    ("ethanol + methacrylic acid", "CCO", "CC(=C)C(=O)O", "alpha,beta-unsaturation (polymerizes)", "dalembert/evil-morty",
     "methacrylate polymerizes (PMMA monomer) under naive Fischer conditions"),
    ("ethanol + propiolic acid", "CCO", "C#CC(=O)O", "alpha,beta-alkyne (oxa-Michael)", "dalembert/evil-morty",
     "the activated C#C undergoes oxa-Michael addition of the alcohol (-> ethyl 3-ethoxyacrylate) + polymerization; "
     "the naive product is the conjugate adduct, not ethyl propiolate"),
    ("remote-epoxide alcohol + AcOH", "OCCCC1CO1", "CC(=O)O", "acid-labile group past radius 2 (R53 REGRESSION)", "evil-morty",
     "Fischer's H2SO4/H2O opens the epoxide; the substrate does not survive.  R53's molecule-wide "
     "_has_remote_acid_labile guard declined this (R53=UNKNOWN); the radius-2 positive scan DROPPED it"),
    ("remote-acetal alcohol + AcOH", "OCCCC(OC)OC", "CC(=O)O", "acid-labile group past radius 2 (R53 REGRESSION)", "evil-morty",
     "Fischer's acid hydrolyzes the acetal; R53 declined it, the radius-2 scan cannot see it"),
    ("methanol + pyrrole-2-carboxylic", "CO", "OC(=O)c1ccc[nH]1", "5-membered heteroaromatic (guard vacuity)", "evil-morty",
     "pyrrole resinifies/polymerizes under strong protic acid; the ring-heteroatom decline keys on 6-membered "
     "rings (`6 in sizes`), so a 5-ring heteroaromatic bypasses the guard entirely"),
)


def _mol_pair(alc_smiles: str, acid_smiles: str):
    return parse_smiles(alc_smiles), parse_smiles(acid_smiles)


def run_adversarial() -> "list[dict]":
    """The gate's surviving false-VOUCHes.  Kitchen-truth is NOT-feasible for all; a row is a surviving
    false-VOUCH iff the whitelist returns FEASIBLE (it does, for all of them -- that is the defer)."""
    rows = []
    for label, alc_s, acid_s, axis, finder, _why in _ADVERSARIAL_FALSE_VOUCHES:
        verdict = symmetric_whitelist_verdict(*_mol_pair(alc_s, acid_s))
        rows.append({"label": label, "axis": axis, "finder": finder, "verdict": verdict,
                     "is_false_vouch": verdict == FEASIBLE})
    return rows


def _acyl_alpha_beta_unsaturated(acid) -> bool:
    """The would-be PATCH: decline an acyl whose alpha carbon bears a C=C/C#C to a beta carbon (conjugated to the
    carbonyl).  Present ONLY to PROVE it cannot separate the polymerizers from the feasibles (run_patch_collision)."""
    from experiments.poor_man_out_of_center_recognizer_defer_probe import _adjacency
    atoms = acid.atoms
    adj = _adjacency(acid)
    c = _acyl_carbon(acid)
    if c is None:
        return False
    for a, _o in adj.get(c, ()):
        if atoms[a] != "C":
            continue
        for m, o2 in adj.get(a, ()):
            if m != c and atoms[m] == "C" and o2 >= 2:
                return True
    return False


#: The proof the alpha,beta-unsaturation leak is NOT patchable within the positive frame: the same bounded
#: structural feature that would decline the infeasible polymerizers ALSO declines feasible conjugated esters --
#: the distinguishing determinant (polymerization propensity) is a magnitude the bounded recognizer cannot read.
#: (label, acid SMILES, kitchen_feasible_truth)
_PATCH_CANNOT_SEPARATE = (
    ("acrylic", "C=CC(=O)O", False), ("methacrylic", "CC(=C)C(=O)O", False), ("propiolic", "C#CC(=O)O", False),
    ("crotonic", "C/C=C/C(=O)O", True), ("cinnamic", "OC(=O)/C=C/c1ccccc1", True), ("sorbic", "CC=CC=CC(=O)O", True),
)


def run_patch_collision() -> dict:
    """Does the alpha,beta-unsaturation patch SEPARATE infeasible polymerizers from feasible conjugated esters?
    No -- it declines BOTH.  Reported as the count of feasible esters the patch would newly false-EXCLUDE."""
    declined_infeasible = declined_feasible = 0
    for _label, smi, truth in _PATCH_CANNOT_SEPARATE:
        if _acyl_alpha_beta_unsaturated(parse_smiles(smi)):
            if truth:
                declined_feasible += 1
            else:
                declined_infeasible += 1
    return {"declined_infeasible": declined_infeasible, "declined_feasible": declined_feasible,
            "separates": declined_feasible == 0 and declined_infeasible > 0}


#: The base-rate cost, in-probe: real, common, feasible esters the whitelist DECLINES (false-EXCLUDE).  A small
#: reproducible sample of daniel's 47-row deployment finding (recall 0.875 -> 0.574 off the friendly subset).
#: (label, alcohol SMILES, acid SMILES)
_DEPLOYMENT_FALSE_EXCLUDES = (
    ("diethyl malonate (ethanol + malonic)", "CCO", "OC(=O)CC(=O)O"),
    ("methyl salicylate / oil of wintergreen (methanol + salicylic)", "CO", "O=C(O)c1ccccc1O"),
    ("ethyl paraben (ethanol + 4-hydroxybenzoic)", "CCO", "OC(=O)c1ccc(O)cc1"),
    ("ethyl lactate (ethanol + lactic)", "CCO", "CC(O)C(=O)O"),
    ("ethyl glycolate (ethanol + glycolic)", "CCO", "OCC(=O)O"),
    ("ethyl pyruvate (ethanol + pyruvic)", "CCO", "CC(=O)C(=O)O"),
)


def run_deployment_false_excludes() -> "list[dict]":
    """Real feasible esters the whitelist declines -> the base-rate cost of the positive frame."""
    rows = []
    for label, alc_s, acid_s in _DEPLOYMENT_FALSE_EXCLUDES:
        v = symmetric_whitelist_verdict(*_mol_pair(alc_s, acid_s))
        rows.append({"label": label, "verdict": v, "is_false_exclude": v == UNKNOWN})
    return rows


def _payload() -> dict:
    rows = run_battery()
    feasible = [r for r in rows if r["truth"] == "feasible"]
    infeasible = [r for r in rows if r["truth"] == "infeasible"]
    conv = [r for r in feasible if r["kind"] == "conv"]
    unconv = [r for r in feasible if r["kind"] == "unconv"]

    n_false_vouch = sum(1 for r in rows if r["outcome"] == "FALSE_VOUCH")
    n_true_vouch = sum(1 for r in rows if r["outcome"] == "true_vouch")
    n_true_decline = sum(1 for r in rows if r["outcome"] == "true_decline")
    n_false_exclude = sum(1 for r in rows if r["outcome"] == "false_exclude")

    conv_vouched = sum(1 for r in conv if r["verdict"] == FEASIBLE)
    unconv_vouched = sum(1 for r in unconv if r["verdict"] == FEASIBLE)

    # BATTERY-sound: zero false-VOUCH on the FRIENDLY-SUBSET battery AND every battery kill-row declined.  This
    # is the POSITIVE result -- and, per the gate, a check-derived-from-its-own-subject (the battery omits the
    # axes the gate's kill lives on), which is exactly why it is NOT soundness.
    battery_sound = (n_false_vouch == 0) and all(r["verdict"] == UNKNOWN for r in infeasible)
    feasible_recall = n_true_vouch / len(feasible) if feasible else 0.0

    adv = run_adversarial()
    adv_vouches = sum(1 for r in adv if r["is_false_vouch"])
    adv_axes = sorted({r["axis"] for r in adv if r["is_false_vouch"]})
    patch = run_patch_collision()
    dfe = run_deployment_false_excludes()
    n_deploy_excl = sum(1 for r in dfe if r["is_false_exclude"])

    return {
        "schema": "poor-man-symmetric-whitelist-phase05-01",
        "round": 54, "phase": 0.5,
        "battery": rows,
        "counts": {
            "total": len(rows),
            "feasible": len(feasible), "infeasible": len(infeasible),
            "battery_false_vouch": n_false_vouch,   # 0 on the friendly subset (the positive result)
            "true_vouch": n_true_vouch,
            "true_decline": n_true_decline,
            "false_exclude": n_false_exclude,
            "conv_total": len(conv), "conv_vouched": conv_vouched,
            "unconv_total": len(unconv), "unconv_vouched": unconv_vouched,
            "adversarial_false_vouches": adv_vouches,   # >0: the KILL -- off-battery axes the census can't read
            "adversarial_axes": len(adv_axes),
            "deployment_false_excludes": n_deploy_excl,  # the base-rate cost, sampled in-probe
        },
        "battery_sound": battery_sound,
        "feasible_recall_friendly_subset": round(feasible_recall, 3),
        "conventional_recall": round(conv_vouched / len(conv), 3) if conv else 0.0,
        "unconventional_recall": round(unconv_vouched / len(unconv), 3) if unconv else 0.0,
        "adversarial_false_vouches": adv,
        "adversarial_axis_list": adv_axes,
        "patch_collision": patch,                     # separates=False: closing acrylic false-EXCLUDEs feasibles
        "deployment_false_excludes": dfe,
        "daniel_deployment_recall": 0.574,            # daniel's independent 47-row battery (vs 0.875 friendly)
        # THE VERDICT: DEFER #5.  The friendly battery is clean, but the gate produced surviving false-VOUCHes on
        # >=3 independent axes the positive radius-2 element census cannot read, the acrylic patch cannot separate
        # infeasible from feasible (the R52 scissors), and the base rate declines the polyfunctional feasibles.
        # Inverting the R53 blacklist to a positive whitelist MOVED the collision into the definition of
        # "recognized-inert"; it did not close it.
        "defer_verdict": (
            battery_sound
            and adv_vouches >= 1
            and len(adv_axes) >= 2
            and patch["separates"] is False
            and n_deploy_excl > 0
        ),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the Phase-0.5 DEFER #5 result holds against live code: the friendly battery is clean, BUT the
    gate's surviving false-VOUCHes still reproduce on multiple independent axes, the acrylic patch still cannot
    separate feasible from infeasible, and the base-rate false-EXCLUDEs still fire."""
    p = _payload()
    c = p["counts"]
    # the POSITIVE result: the friendly-subset battery is clean and non-vacuous
    assert c["battery_false_vouch"] == 0, f"friendly battery not clean: {[r for r in p['battery'] if r['outcome']=='FALSE_VOUCH']}"
    assert p["battery_sound"], f"battery kill set not fully declined: {c}"
    assert c["true_vouch"] > 0, "vacuous FEASIBLE set on the friendly battery"
    # the KILL (the defer's evidence): surviving false-VOUCHes on >=2 independent axes the census can't read
    assert all(r["is_false_vouch"] for r in p["adversarial_false_vouches"]), \
        f"an adversarial case stopped false-VOUCHing (recognizer changed under it?): {p['adversarial_false_vouches']}"
    assert c["adversarial_false_vouches"] >= 1, "the defer's evidence vanished: no surviving false-VOUCH"
    assert c["adversarial_axes"] >= 2, f"the kill must span independent axes: {p['adversarial_axis_list']}"
    # the patch cannot separate (the R52 scissors) and the base-rate cost is real
    assert p["patch_collision"]["separates"] is False, "the alpha,beta-unsaturation patch now separates -- re-check"
    assert c["deployment_false_excludes"] > 0, "the base-rate false-EXCLUDEs vanished"
    assert p["defer_verdict"], f"DEFER #5 verdict does not hold: {c}"
    return True


if __name__ == "__main__":  # pragma: no cover
    import pprint
    print("validate() ->", validate())
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    pprint.pprint(_payload())
