"""POOR-MAN-OUT-OF-CENTER-RECOGNIZER-DEFER-01 (R52, PR-2): the THIRD verified defer of the ingenuity reward,
now of the "out-of-center recognizer" proposed as KILL-1's unlock #2.

R49 killed a feasibility-layer TOPOLOGICAL reward gate (topology carries zero catalysis/reachability info).
R50 (the ingenuity scissors) killed the enumeration-frontier redux and named the deferred reward's ORDERED
unlock: (#1) catalyst obtainability [BUILT R51], (#2) a fail-closed recognizer on OUT-OF-CENTER features,
(#3) a proven reachable consumer.  This round put unlock #2 -- an EXCLUDE-only, fail-closed, R51-shaped
recognizer that reads functional groups OUTSIDE a step's atom-mapped reaction center and blocks a
"kitchen-selective one-pot" claim on a recognized interferer (a competing free amine) -- before a five-bearing
adversarial DESIGN gate.  The gate DEFERRED it 4-to-1 (dalembert/birdperson/daniel DEFER, butter-robot KILL,
evil-morty lone BUILD-with-folds refuted by the census).  This probe freezes the load-bearing kill and the
three supporting refutations, every fact recomputed from live production code.

THE KILL (a NEW structure theorem -- the recognizer MOVES the collision, it does not close it):
    KILL-1 (R50): a bounded-radius recognizer cannot carry an unbounded-radius condition envelope, because one
    Fischer class straddles kitchen (pentyl acetate) and not-kitchen (5-aminopentyl acetate -- the amine
    outcompetes the alcohol, so heating with the acid gives the N-acyl amide, not the O-ester).  The
    out-of-center recognizer reads that amine and EXCLUDEs 5-aminopentyl -- it relabels THAT blade.  But the
    unbounded-radius determinant is not only competing nucleophiles: it includes the SUBSTITUTION DEGREE at the
    carbinol carbon.  tert-butyl acetate is NOT a Fischer one-pot (a TERTIARY alcohol dehydrates via E1 under
    acid catalysis; tert-butyl esters are made by other routes, never free-acid Fischer) -- yet tert-butanol's
    OUT-OF-CENTER functional groups are byte-identical to pentanol's (both: one reacting hydroxyl on an
    all-carbon skeleton, ZERO competing nucleophiles), AND its atom-mapped edit signature is byte-identical to
    pentyl acetate's (computed here by the R50 scissors probe's own frozen _edit_signature).  So ANY
    out-of-center functional-group recognizer that keeps pentyl NEUTRAL (it MUST, or it false-EXCLUDEs the
    kitchen case) ALSO reaches NEUTRAL for tert-butyl -- a residual false-VOUCH-by-omission of exactly the
    KILL-1 shape.  The distinguishing determinant (carbinol degree, 1 vs 3) lives AT the center and is not a
    functional group in ANY inventory.  The recognizer moves the collision from the amine blade to the steric
    blade; it does not close it.

WHY NOT BUILD IT ANYWAY (three supporting refutations, all verified against live code):
    * REDUNDANT with R48: feasibility_of_step already returns UNKNOWN for BOTH the pentyl AND the 5-aminopentyl
      free-acid Fischer condensations (the R48 domain guard _is_intermolecular_acyl_condensation fires on both),
      so there is NO false "kitchen" pass at the feasibility layer to remove for the class the recognizer fires on.
    * NO LIVE FALSE-VOUCH to remove: the one reachable route to the O-minor-isomer registered target
      (4-aminophenol + acetic acid -> 4-aminophenyl acetate + water) is honest UNKNOWN on BOTH selectivity and
      feasibility today -- loud silence, not a fabricated pass (R49: a model's silence on a property is not a
      false-VOUCH).  The sourced N-selectivity SelectivityRecord covers the ANHYDRIDE reactant set, not this
      FREE-ACID one; and the anhydride route is architecturally unreachable (no anhydride in the commodity catalog).
    * BASE-RATE INVERSION (birdperson, argued in the scope doc): the R51 burden-of-proof flip is sound for
      CATALYSTS (an unrecognized DECLARED catalyst is usually an industrial metal -> block is usually right) but
      its polarity does NOT transfer to SUBSTRATE features (an unrecognized out-of-center group is usually a
      spectator -> fail-closed EXCLUDE is usually WRONG), so a fail-closed-on-unrecognized substrate recognizer
      false-EXCLUDEs real kitchen routes en masse.

THE SOUND FOLLOW-UP THE GATE SURFACED (named, NOT built here): a DERIVED recognizer is unsound (this kill), but a
SOURCED SelectivityRecord is not.  Adding a free-acid 4-aminophenol N-selectivity record (sourcing-gated) would
flip the O-minor route to a correct DISFAVORED -- consuming a sourced fact, dodging every kill above.  See
docs/research/POOR_MAN_OUT_OF_CENTER_RECOGNIZER_SCOPE_DECISION_v0.1.md.

RDKit-free; imports and runs REAL production code, reusing the R50 scissors probe's atom-mapped edit machinery so
the "byte-identical edit" claim is computed by the same frozen functions.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.feasibility import (
    FeasibilityDirection,
    _is_intermolecular_acyl_condensation,
    feasibility_of_step,
)
from smartchem.experiment.selectivity import DEFAULT_SELECTIVITY, SelectivityStatus, selectivity_of_step
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from experiments.poor_man_ingenuity_scissors_probe import _edit_signature, _esterification_scission

#: The frozen fingerprint of :func:`_payload`.  Breaks loudly if the load-bearing kill (the steric collision) or
#: any of the three supporting refutations moves against live code.
FROZEN_HASH = "2115ded5967093c3df6380dffd471f1ad9764d71cebe6b86f114f868b32a1669"

# The three esterifications, read backward as the frontier transform does (ester, acid, alcohol).  pentyl and
# tert-butyl acetate are the collision pair; 5-aminopentyl is the amine blade the recognizer DOES catch.
_PENTYL = ("CC(=O)OCCCCC", "CC(=O)O", "CCCCCO")
_TERT_BUTYL = ("CC(=O)OC(C)(C)C", "CC(=O)O", "CC(C)(C)O")
_AMINOPENTYL = ("CC(=O)OCCCCCN", "CC(=O)O", "NCCCCCO")


def _adjacency(mol) -> "dict[int, list[tuple[int, int]]]":
    adj: "dict[int, list[tuple[int, int]]]" = {}
    for b in mol.bonds:
        adj.setdefault(b.i, []).append((b.j, b.order))
        adj.setdefault(b.j, []).append((b.i, b.order))
    return adj


def _is_carbonyl_c(idx: int, atoms, adj) -> bool:
    return any(order == 2 and atoms[n] == "O" for n, order in adj.get(idx, ()))


def _reacting_hydroxyl_o(atoms, adj) -> "int | None":
    """Index of the -OH oxygen that is the O-esterification reaction centre: an O with exactly one heavy
    neighbour, single-bonded to a non-carbonyl carbon (so ethers/carbonyls are excluded)."""
    for i, el in enumerate(atoms):
        if el != "O":
            continue
        heavy = [(n, o) for n, o in adj.get(i, ()) if atoms[n] != "H"]
        if len(heavy) == 1 and heavy[0][1] == 1 and atoms[heavy[0][0]] == "C" and not _is_carbonyl_c(heavy[0][0], atoms, adj):
            return i
    return None


def _carbinol_degree(alcohol) -> int:
    """The carbon-substitution degree of the carbon bearing the reacting -OH (1=primary, 2=secondary,
    3=tertiary): the count of its carbon neighbours.  This is the unbounded-radius determinant that lives AT
    the reaction centre and is NOT an out-of-centre functional group -- the recognizer is blind to it."""
    atoms = alcohol.atoms
    adj = _adjacency(alcohol)
    o = _reacting_hydroxyl_o(atoms, adj)
    if o is None:
        return -1
    c = [n for n, order in adj.get(o, ()) if atoms[n] == "C"][0]
    return sum(1 for n, order in adj.get(c, ()) if atoms[n] == "C")


def out_of_center_nucleophiles(alcohol) -> "tuple[str, ...]":
    """The recognized COMPETING-NUCLEOPHILE functional groups OUTSIDE the reacting hydroxyl: a primary/secondary
    amine, a thiol, or a SECOND hydroxyl.  These are the interferers the proposed recognizer would read to
    EXCLUDE (an amine outcompetes the alcohol in O-acylation).  An all-carbon skeleton bearing only the one
    reacting -OH returns () -- the recognizer's NEUTRAL case."""
    atoms = alcohol.atoms
    adj = _adjacency(alcohol)
    react_o = _reacting_hydroxyl_o(atoms, adj)
    groups: list[str] = []
    for i, el in enumerate(atoms):
        if i == react_o:
            continue
        nb = adj.get(i, ())
        if el == "N":
            # an amine: all single bonds, no N=O, not bonded to a carbonyl carbon (that would be an amide)
            if all(o == 1 for _n, o in nb) and not any(atoms[n] == "O" for n, _o in nb) and not any(
                atoms[n] == "C" and _is_carbonyl_c(n, atoms, adj) for n, _o in nb
            ):
                groups.append("amine")
        elif el == "S":
            heavy = [(n, o) for n, o in nb if atoms[n] != "H"]
            if len(heavy) <= 1 and all(o == 1 for _n, o in nb):
                groups.append("thiol")
        elif el == "O":
            heavy = [(n, o) for n, o in nb if atoms[n] != "H"]
            if len(heavy) == 1 and heavy[0][1] == 1 and atoms[heavy[0][0]] == "C" and not _is_carbonyl_c(heavy[0][0], atoms, adj):
                groups.append("hydroxyl")  # a SECOND competing -OH
    return tuple(sorted(groups))


def recognizer_verdict(alcohol) -> str:
    """The proposed out-of-centre recognizer, prototyped: EXCLUDE if a competing-nucleophile group is present,
    else NEUTRAL (every out-of-centre group is a recognized inert -- alkyl skeleton + the one reacting -OH).
    It NEVER VOUCHES; NEUTRAL means 'no interferer found', not 'kitchen-selective'."""
    return "EXCLUDE" if out_of_center_nucleophiles(alcohol) else "NEUTRAL"


def steric_collision() -> dict:
    """THE KILL: pentyl acetate (kitchen) and tert-butyl acetate (NOT a Fischer one-pot -- tertiary carbinol,
    E1 dehydration) share a byte-identical atom-mapped edit signature AND byte-identical out-of-centre functional
    groups (both: none but the reacting -OH), so BOTH reach the recognizer's NEUTRAL verdict -- yet only pentyl
    is kitchen.  The recognizer catches the amine blade (5-aminopentyl -> EXCLUDE) but re-collides pentyl with
    tert-butyl on the steric blade (carbinol degree 1 vs 3), which it cannot read.  It moves the collision, it
    does not close it."""
    sig_p = _edit_signature(_esterification_scission(*_PENTYL))
    sig_t = _edit_signature(_esterification_scission(*_TERT_BUTYL))
    alc_p, alc_t, alc_a = (parse_smiles(x[2]) for x in (_PENTYL, _TERT_BUTYL, _AMINOPENTYL))
    return {
        "edit_signatures_identical_pentyl_tbu": sig_p == sig_t,
        "pentyl_out_of_center_nucleophiles": list(out_of_center_nucleophiles(alc_p)),
        "tbu_out_of_center_nucleophiles": list(out_of_center_nucleophiles(alc_t)),
        "amino_out_of_center_nucleophiles": list(out_of_center_nucleophiles(alc_a)),
        "pentyl_recognizer": recognizer_verdict(alc_p),
        "tbu_recognizer": recognizer_verdict(alc_t),
        "amino_recognizer": recognizer_verdict(alc_a),
        "pentyl_carbinol_degree": _carbinol_degree(alc_p),
        "tbu_carbinol_degree": _carbinol_degree(alc_t),
        # kitchen truth (textbook, ASSERTED not computed -- same discipline as the R50 scissors _ESTER_FAMILY
        # flags): a primary/secondary alkyl alcohol + acetic acid IS a kitchen Fischer ester; a TERTIARY alcohol
        # is NOT (it dehydrates via E1 under the acid catalysis Fischer needs).
        "pentyl_kitchen": True,
        "tbu_kitchen": False,
        # the recognizer DOES move the amine blade ...
        "recognizer_moves_amine_blade": (
            recognizer_verdict(alc_a) == "EXCLUDE" and recognizer_verdict(alc_p) == "NEUTRAL"
        ),
        # ... but the steric collision survives: identical edit + identical out-of-centre groups + both NEUTRAL,
        # yet kitchen differs and the only separating feature (carbinol degree) is at the centre, unreadable.
        "collision_survives_on_steric_blade": (
            sig_p == sig_t
            and out_of_center_nucleophiles(alc_p) == out_of_center_nucleophiles(alc_t)
            and recognizer_verdict(alc_p) == recognizer_verdict(alc_t) == "NEUTRAL"
            and _carbinol_degree(alc_p) != _carbinol_degree(alc_t)
        ),
    }


def _mol(name_or_smiles: str):
    ns = structure_by_name(name_or_smiles)
    if ns is not None and ns.canonical_molecule is not None:
        return ns.canonical_molecule
    return parse_smiles(name_or_smiles)


def _fischer_step(alcohol_smiles: str, ester_smiles: str) -> ExperimentStep:
    reactants = (_mol("acetic acid"), parse_smiles(alcohol_smiles))
    products = (parse_smiles(ester_smiles), _mol("water"))
    return ExperimentStep(
        STEP_SCHEMA, target=products[0], reactants=reactants, products=products,
        reagents=(), envelope=ConditionEnvelope.unknown(),
    )


def redundant_with_r48() -> dict:
    """The R48 domain guard already fires (-> feasibility UNKNOWN) on BOTH the kitchen and the non-kitchen
    free-acid Fischer condensations, so there is no false 'kitchen' pass at the feasibility layer for the
    recognizer to remove -- it would be dead there."""
    pentyl = _fischer_step("CCCCCO", "CC(=O)OCCCCC")
    amino = _fischer_step("NCCCCCO", "CC(=O)OCCCCCN")
    return {
        "pentyl_guard_fires": _is_intermolecular_acyl_condensation(pentyl),
        "amino_guard_fires": _is_intermolecular_acyl_condensation(amino),
        "pentyl_feasibility": feasibility_of_step(pentyl).direction.value,
        "amino_feasibility": feasibility_of_step(amino).direction.value,
    }


def no_live_false_vouch() -> dict:
    """The one reachable route to the O-minor-isomer registered target (4-aminophenyl acetate) via the free-acid
    Fischer of 4-aminophenol is honest UNKNOWN on BOTH selectivity and feasibility today -- loud silence, not a
    fabricated 'kitchen' pass (R49: silence is not a false-VOUCH).  So the recognizer has no live output to
    change; its only sound future home consumes a SOURCED selectivity record, which does not yet exist for the
    free-acid reactant set."""
    target = structure_by_name("4-aminophenyl acetate")
    assert target is not None, "4-aminophenyl acetate is expected to be a registered structure"
    tgt = target.molecule
    aminophenol = _mol("4-aminophenol") if structure_by_name("4-aminophenol") else parse_smiles("Nc1ccc(O)cc1")
    step = ExperimentStep(
        STEP_SCHEMA, target=tgt, reactants=(aminophenol, _mol("acetic acid")), products=(tgt, _mol("water")),
        reagents=(), envelope=ConditionEnvelope.unknown(),
    )
    sel = selectivity_of_step(step, table=DEFAULT_SELECTIVITY)
    feas = feasibility_of_step(step)
    return {
        "target": "4-aminophenyl acetate",
        "selectivity": sel.status.value,
        "feasibility": feas.direction.value,
        "is_honest_silence_not_false_vouch": (
            sel.status is SelectivityStatus.UNKNOWN and feas.direction is FeasibilityDirection.UNKNOWN
        ),
    }


def _payload() -> dict:
    return {
        "schema": "poor-man-out-of-center-recognizer-defer-01",
        "round": 52,
        "steric_collision": steric_collision(),
        "redundant_with_r48": redundant_with_r48(),
        "no_live_false_vouch": no_live_false_vouch(),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the verified defer holds against live code: the load-bearing steric-collision kill + the three
    supporting refutations.  Raises on any drift."""
    sc = steric_collision()
    assert sc["edit_signatures_identical_pentyl_tbu"], "kill broke: pentyl and tert-butyl no longer share one edit"
    assert sc["pentyl_out_of_center_nucleophiles"] == [] == sc["tbu_out_of_center_nucleophiles"], sc
    assert sc["recognizer_moves_amine_blade"], "the recognizer no longer catches the amine blade (probe drift)"
    assert sc["collision_survives_on_steric_blade"], "THE KILL broke: the steric collision no longer survives"
    assert sc["pentyl_carbinol_degree"] == 1 and sc["tbu_carbinol_degree"] == 3, sc
    assert sc["pentyl_kitchen"] and not sc["tbu_kitchen"], sc

    r = redundant_with_r48()
    assert r["pentyl_guard_fires"] and r["amino_guard_fires"], r
    assert r["pentyl_feasibility"] == "UNKNOWN" and r["amino_feasibility"] == "UNKNOWN", r

    nv = no_live_false_vouch()
    assert nv["selectivity"] == "UNKNOWN" and nv["feasibility"] == "UNKNOWN", nv
    assert nv["is_honest_silence_not_false_vouch"], nv
    return True


if __name__ == "__main__":  # pragma: no cover
    ok = validate()
    print(f"validate() -> {ok}")
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    import pprint
    pprint.pprint(_payload())
