"""#112 -- the SN2 nucleophilic-substitution reaction-TYPE recognizer (sp3 carbon, halide leaving group).

``_sn2_substitution`` vouches the neutral-representable SN2 subset -- a heteroatom (O/N/S) nucleophile
displacing a HALIDE at an sp3, non-tertiary carbon, ``R-X + Nu-M -> R-Nu + M-X`` with the counterion M (metal
of a salt, or H) carried explicitly so the #105 global-charge wall is never touched.  It is locked by the #106
radius-1 sp3/non-tertiary predicate (which excludes the centre-identical SNAr / vinylic / acyl collisions) AND
an independent single-cut re-derivation into the declared precursors, and it is content-deterministic (never
reads ``step.reaction_center``) and fail-closed.

Proof obligations pinned here (the plan's ten): conservation, reproducible rewrite, structural-locality /
applicable-domain witness, independent (forge-proof) recognition, explicit reactant/coproduct accounting, the
no-false-VOUCH adversarial corpus (SNAr / tertiary / vinylic / acyl / non-halide-leaving-group / carbon-
nucleophile), positive+negative+null+mutation controls, route-level (blocker) behaviour, version/compatibility,
and FRESH holdout molecules not used to design the rule.
"""
from __future__ import annotations

import dataclasses
import types

import pytest

from smartchem.experiment.reaction_type_oracle import (
    _RECOGNIZERS,
    _sn2_substitution,
    recognize_reaction_type,
    recognize_reaction_type_outcome,
    route_reaction_type_blockers,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.reaction_center import ReactionCenter
from smartchem.smiles import parse_smiles

_SN2 = "SN2 substitution"


def _step(target_smi: str, rx_smi: str, nu_smi: str, coproduct_smi: str) -> ExperimentStep:
    """R-X + Nu-source -> target(R-Nu) + coproduct.  The ExperimentStep ctor re-checks conservation."""
    target = parse_smiles(target_smi)
    reactants = (parse_smiles(rx_smi), parse_smiles(nu_smi))
    products = (target, parse_smiles(coproduct_smi))
    return ExperimentStep.assembling(target, reactants, products, reagents=())


def _is_sn2(step) -> bool:
    name = recognize_reaction_type(step)
    return name is not None and _SN2 in name


# ====================================================================================================
# POSITIVES -- genuine SN2 at an sp3 carbon, O/N/S nucleophile, halide leaving group
# ====================================================================================================
_POSITIVES = [
    ("Williamson diethyl ether (O, primary, Na salt)", "CCOCC", "CCBr", "CCO[Na]", "[Na]Br"),
    ("ethyl thioether (S, salt)",                      "CCSCC", "CCBr", "CCS[Na]", "[Na]Br"),
    ("N-alkylation EtNHMe (N, neutral amine -> HBr)",  "CCNC",  "CCBr", "CN",      "Br"),
    ("secondary isopropyl methyl ether (O)",           "COC(C)C", "CC(C)Br", "CO[Na]", "[Na]Br"),
    ("benzyl methyl ether (O, benzylic sp3)",          "COCc1ccccc1", "BrCc1ccccc1", "CO[Na]", "[Na]Br"),
]


@pytest.mark.parametrize("label,tgt,rx,nu,cop", _POSITIVES, ids=[c[0] for c in _POSITIVES])
def test_genuine_sn2_is_recognized(label, tgt, rx, nu, cop):
    assert _is_sn2(_step(tgt, rx, nu, cop)), label


# -- FRESH holdouts: propyl / butyl / allyl / iodo -- NOT used to design the rule ----------------------
_HOLDOUTS = [
    ("1-bromopropane + NaOMe -> methyl propyl ether", "CCCOC", "CCCBr", "CO[Na]", "[Na]Br"),
    ("1-bromobutane + NaSEt -> butyl ethyl sulfide",  "CCCCSCC", "CCCCBr", "CCS[Na]", "[Na]Br"),
    ("allyl chloride + NaOMe -> allyl methyl ether",  "C=CCOC", "C=CCCl", "CO[Na]", "[Na]Cl"),
    ("iodoethane + NaOMe -> ethyl methyl ether (I LG)", "CCOC", "CCI", "CO[Na]", "[Na]I"),
    ("propylamine + MeI -> N-methylpropylamine (HI)",  "CCCNC", "CCCN", "CI", "I"),
]


@pytest.mark.parametrize("label,tgt,rx,nu,cop", _HOLDOUTS, ids=[c[0] for c in _HOLDOUTS])
def test_fresh_holdouts_are_recognized(label, tgt, rx, nu, cop):
    assert _is_sn2(_step(tgt, rx, nu, cop)), f"fresh holdout should vouch: {label}"


# ====================================================================================================
# NO-FALSE-VOUCH adversarial corpus -- each MUST NOT vouch as SN2 (the issue's named controls)
# ====================================================================================================
_MUST_NOT_VOUCH = [
    ("MTBE: tert-butyl centre (SN1, not SN2)",  "COC(C)(C)C", "CC(C)(C)Br", "CO[Na]", "[Na]Br"),
    ("SNAr: aryl centre (centre-identical)",     "COc1ccccc1",  "Brc1ccccc1", "CO[Na]", "[Na]Br"),
    ("vinylic substitution (sp2 centre)",        "COC=C",       "BrC=C",      "CO[Na]", "[Na]Br"),
    ("acyl substitution (carbonyl centre)",      "COC(C)=O",    "CC(=O)Br",   "CO[Na]", "[Na]Br"),
    ("non-halide leaving group (hydroxide)",     "CCOCC",       "CCO",        "CCO[Na]", "[Na]O"),
]


@pytest.mark.parametrize("label,tgt,rx,nu,cop", _MUST_NOT_VOUCH, ids=[c[0] for c in _MUST_NOT_VOUCH])
def test_adversarial_corpus_does_not_false_vouch(label, tgt, rx, nu, cop):
    out = recognize_reaction_type_outcome(_step(tgt, rx, nu, cop))
    assert not (out.is_match and _SN2 in str(out.reaction_class)), f"FALSE-VOUCHED SN2: {label}"


def test_carbon_nucleophile_is_deferred_not_vouched():
    # nitrile synthesis EtBr + NaCN -> propionitrile(EtCN) + NaBr: a REAL SN2, but a C-nucleophile -- deferred
    # (it needs its own C-C-coupling lock), so it must ABSTAIN cleanly (honest coverage loss), never vouch here.
    out = recognize_reaction_type_outcome(_step("CCC#N", "CCBr", "[Na]C#N", "[Na]Br"))
    assert not (out.is_match and _SN2 in str(out.reaction_class)), "deferred nitrile must not vouch as SN2"
    assert not out.is_internal_error, f"must be a clean abstain, not an instrument fault: {out.faults}"


def test_cc_coupling_fiction_does_not_vouch():
    # an organometallic C-C coupling fiction EtBr + MeNa -> propane + NaBr forms a C-C bond with the same salt
    # coproduct; the heteroatom-only nucleophile restriction demotes it (no C-{O,N,S} bond forms).
    assert not _is_sn2(_step("CCC", "CCBr", "C[Na]", "[Na]Br"))


# ====================================================================================================
# ADVERSARY KILLS (evil-morty + d'Alembert) -- SN1 oxocarbenium / carbene centres, permanent regressions
# ====================================================================================================
# The recognizer's SN1-exclusion rationale is enforced by the radius-1 gate, NOT by a carbon count: a carbon
# count reads a heteroatom-crowded oxocarbenium as a benign "secondary" centre and false-vouches it.  The gate
# demotes any zero-hydrogen (fully substituted) carbon AND any carbon whose only heteroatom neighbour is not the
# nucleophile (an alpha-O/N/S lone-pair donor -> SN1).
_SN1_CENTRE_KILLS = [
    ("acetone dimethyl ketal (evil-morty KILL-1: 2C+2O, 0 H)", "CC(C)(OC)OC", "CC(C)(Cl)OC", "CO[Na]", "[Na]Cl"),
    ("tetramethyl orthocarbonate (evil-morty KILL-2: 4 O)", "COC(OC)(OC)OC", "COC(OC)(OC)Cl", "CO[Na]", "[Na]Cl"),
    ("methylal / MOM centre (d'Alembert: alpha-O, 2 H)", "COCOC", "ClCOC", "CO[Na]", "[Na]Cl"),
    ("trimethyl orthoformate (d'Alembert: 1 H, 2 alpha-O -- the airtight kill)", "COC(OC)OC", "ClC(OC)OC", "CO[Na]", "[Na]Cl"),
    ("dithioacetal thiocarbenium (d'Alembert: alpha-S)", "CSCSC", "ClCSC", "CS[Na]", "[Na]Cl"),
    ("aminal iminium (d'Alembert: alpha-N)", "CN(C)CN(C)C", "ClCN(C)C", "CNC", "Cl"),
]


@pytest.mark.parametrize("label,tgt,rx,nu,cop", _SN1_CENTRE_KILLS, ids=[c[0] for c in _SN1_CENTRE_KILLS])
def test_alpha_heteroatom_sn1_centres_do_not_vouch(label, tgt, rx, nu, cop):
    assert not _is_sn2(_step(tgt, rx, nu, cop)), f"alpha-heteroatom SN1 oxocarbenium FALSE-VOUCHED: {label}"


def test_carbene_centre_does_not_vouch():
    # d'Alembert KILL-1: is_saturated_carbon is an all-single-bonds test, NOT a valence test, so a DIVALENT
    # carbene passes the sp3 clause; the target fails is_closed_shell_neutral and the carbon is not tetravalent,
    # so the hardened gate demotes it (the is_closed_shell_neutral guard every sibling recognizer already carried).
    assert not _is_sn2(_step("[C](C)OC", "[C](C)Br", "CO[Na]", "[Na]Br"))


# ====================================================================================================
# MUTATION controls -- a genuine SN2 and its minimal near-miss twin, decided oppositely
# ====================================================================================================
def test_mutation_primary_vouches_tertiary_twin_demotes():
    assert _is_sn2(_step("CCOC", "CCBr", "CO[Na]", "[Na]Br"))            # primary: VOUCH
    assert not _is_sn2(_step("COC(C)(C)C", "CC(C)(C)Br", "CO[Na]", "[Na]Br"))  # tertiary twin: DEMOTE


def test_sn2_vouch_is_a_structural_type_claim_not_a_mechanism_or_stereochemistry_claim():
    # OPERATION XII 1B boundary: a graph rewrite cannot establish a MECHANISM. The vouch certifies an SN2-COMPATIBLE
    # sp3 centre (a NECESSARY structural condition), NOT that the substrate proceeds by SN2 over SN1/E2
    # (solvent/kinetics-dependent, unrepresented), and NOT any Walden-inversion stereochemistry (the constitution-only
    # Molecule carries no configuration). A SECONDARY substrate -- where SN1/E2 genuinely compete -- still vouches,
    # because SN2 is a structurally AVAILABLE mechanism there; the existential vouch makes no claim it wins.
    secondary = _step("COC(C)C", "CC(C)Br", "CO[Na]", "[Na]Br")  # isopropyl methyl ether: SN1/E2 compete
    assert _is_sn2(secondary)
    rt = recognize_reaction_type(secondary)
    assert rt is not None and _SN2 in rt
    # the recognized value is a reaction-TYPE label; it asserts no mechanism-resolution or stereochemical outcome
    low = rt.lower()
    for banned in ("inversion", "retention", "concerted", "stereo", "enantio"):
        assert banned not in low


def test_mutation_halide_vouches_hydroxide_twin_demotes():
    assert _is_sn2(_step("CCOC", "CCBr", "CO[Na]", "[Na]Br"))            # halide LG: VOUCH
    assert not _is_sn2(_step("CCOC", "CCO", "CO[Na]", "[Na]O"))          # hydroxide LG twin: DEMOTE


# ====================================================================================================
# CONTENT-DETERMINISM -- a forged/absent centre can neither MINT nor BLOCK a vouch
# ====================================================================================================
_FOREIGN_CENTER = ReactionCenter.of((("C", "C", 1),), (("C", "C", 2),), 1)  # a Diels-Alder-shaped centre


def test_forged_centre_does_not_block_a_genuine_sn2():
    genuine = _step("CCOCC", "CCBr", "CCO[Na]", "[Na]Br")
    forged = dataclasses.replace(genuine, reaction_center=_FOREIGN_CENTER)
    assert _is_sn2(forged), "a borrowed centre must not block a real SN2 (centre is never read)"


def test_forged_centre_does_not_mint_an_sn2_on_a_fiction():
    # an acyl transfer (carbonyl centre, NOT SN2) wearing a borrowed SN2-shaped centre stays unrecognized as SN2.
    fiction = _step("COC(C)=O", "CC(=O)Br", "CO[Na]", "[Na]Br")
    forged = dataclasses.replace(fiction, reaction_center=ReactionCenter.of((("C", "O", 1),), (("Br", "C", 1),), 1))
    assert not _sn2_substitution(forged), "no forged centre buys an SN2 vouch"


def test_absent_centre_still_vouches():
    genuine = _step("CCOCC", "CCBr", "CCO[Na]", "[Na]Br")
    assert genuine.reaction_center is None and _is_sn2(genuine)


# ====================================================================================================
# SHAPE / NULL accounting -- only the elementary 2->2 intermolecular substitution shape
# ====================================================================================================
def test_wrong_shape_abstains():
    target = parse_smiles("CCOCC")
    # a 3-reactant step (a spectator present) is not the elementary SN2 shape -> abstain
    three = ExperimentStep.assembling(
        target, (parse_smiles("CCBr"), parse_smiles("CCO[Na]"), parse_smiles("O")),
        (target, parse_smiles("[Na]Br"), parse_smiles("O")), reagents=(),
    )
    assert not _sn2_substitution(three)


def test_null_identity_step_abstains():
    # a degenerate "reaction" that makes nothing new must not vouch.
    m = parse_smiles("CCBr")
    null = ExperimentStep.assembling(m, (m,), (m,), reagents=())
    out = recognize_reaction_type_outcome(null)
    assert not (out.is_match and _SN2 in str(out.reaction_class))


# ====================================================================================================
# NO CROSS-POACH -- exactly the SN2 recognizer fires on an SN2 step; SN2 fires on none of the others
# ====================================================================================================
def test_exactly_the_sn2_recognizer_fires_on_an_sn2_step():
    step = _step("CCOCC", "CCBr", "CCO[Na]", "[Na]Br")
    fired = []
    for name, pred in _RECOGNIZERS:
        try:
            if pred(step):
                fired.append(name)
        except Exception:
            pass
    assert len(fired) == 1 and _SN2 in fired[0], fired


@pytest.mark.parametrize(
    "label,rs,ps",
    [
        ("acyl condensation", ("CC(=O)O", "CCO"), ("CC(=O)OCC", "O")),
        ("etherification",    ("CCO", "CCO"), ("CCOCC", "O")),
        ("N-alkylation (dehydrative)", ("CN", "CO"), ("CNC", "O")),
    ],
)
def test_sn2_does_not_poach_other_classes(label, rs, ps):
    target = parse_smiles(ps[0])
    step = ExperimentStep.assembling(target, tuple(parse_smiles(s) for s in rs),
                                     tuple(parse_smiles(s) for s in ps), reagents=())
    assert not _sn2_substitution(step), f"SN2 must not poach {label}"


# ====================================================================================================
# ROUTE-LEVEL -- an SN2 step is VOUCHED (no fiction blocker); a fiction step is BLOCKED
# ====================================================================================================
def test_route_with_an_sn2_step_has_no_fiction_blocker():
    step = _step("CCOCC", "CCBr", "CCO[Na]", "[Na]Br")
    route = types.SimpleNamespace(steps=(step,))
    assert route_reaction_type_blockers(route) == ()


def test_route_with_a_fiction_step_is_blocked():
    # a conserved-but-fictional C-C glue (ethane + ethane -> butane + H2; no recognizer vouches it) demotes the route.
    fiction = ExperimentStep.assembling(
        parse_smiles("CCCC"), (parse_smiles("CC"), parse_smiles("CC")),
        (parse_smiles("CCCC"), parse_smiles("[H][H]")), reagents=(),
    )
    route = types.SimpleNamespace(steps=(fiction,))
    assert route_reaction_type_blockers(route) != ()


# ====================================================================================================
# COMPATIBILITY -- the registry grew by exactly one; the recognizer is a total pure boolean
# ====================================================================================================
def test_registry_has_twenty_four_recognizers_including_sn2():
    assert len(_RECOGNIZERS) == 24  # 1.5 consolidation: base 20 + hydrogenation + oxoacid ester + SN2 + imine
    assert any(_SN2 in name for name, _ in _RECOGNIZERS)


def test_recognizer_is_total_on_a_degenerate_step():
    # a 1-reactant / 1-product step is outside the shape; the predicate returns False, never raises.
    m = parse_smiles("CCBr")
    step = ExperimentStep.assembling(m, (m,), (m,), reagents=())
    assert _sn2_substitution(step) is False
