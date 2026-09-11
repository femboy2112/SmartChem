"""POOR-MAN-INGENUITY-GATE-DEFER-01 (R49, PR-2): the VERIFIED DEFER of the feasibility-layer ingenuity gate.

PR-2's scoped design was a feasibility-layer reaction-class recognizer that would mint a positive
"VOUCHED / reality-respecting / poor-man-reachable" reward from a step's functional-group TOPOLOGY (donor C-O is
an alcohol, a C-heteroatom bond forms, water leaves).  A four-bearing adversarial DESIGN gate (evil-morty +
dalembert with run counterexamples, birdperson scope, butter-robot YAGNI) KILLED it BEFORE it was wired.  This
probe is the committed evidence of that kill and the reason the sound gate is deferred to the enumeration frontier.

THE KILL (fatal, verified here against the REAL feasibility.py):
    A topological recognizer -- even one keyed CORRECTLY on the FORMED C-heteroatom bond (dalembert's KILL-3
    refinement, which does correctly reject Friedel-Crafts C-C alkylation and the acid class) -- carries ZERO
    information about CATALYSIS or KITCHEN-REACHABILITY.  So it VOUCHES reactions that only proceed under
    transition-metal catalysis: theophylline + methanol -> caffeine + water is a borrowing-hydrogen (Ru/Ir)
    N-methylation; aniline + ethanol -> N-ethylaniline + water is a Ru/Ir catalytic amination.  Both read
    VOUCHED under the topological predicate.  The poor-man ingenuity reward would decorate these as
    "reality-respecting, poor-man-reachable" -- a FABRICATED capability claim, the exact rubber stamp the
    directive forbids ("thermo/topology + conservation is a RUBBER STAMP"; [[kitchen-is-the-lab]]).  Worse: the
    caffeine N-methylation was the design's OWN cited non-vacuity example.
    Tombstone: VOUCHED (topological) does NOT imply kitchen-reachable, and does NOT imply proceeds-uncatalyzed;
    the reward gate reads a signal that does not encode the property it rewards.

WHAT SURVIVED (the sound part, kept untouched):
    R48's GUARDED guard (``feasibility.py::_is_intermolecular_acyl_condensation``) -- the aqueous free-acid
    dehydrative-acylation domain guard -- is sound, target-independent, and its single-water locality holds.  It
    correctly FIRES on the paracetamol Fischer route and stays SILENT on the alcohol-donor cases (it is a
    NEGATIVE fail-closed guard, not a positive reward).  The three-way recognizer taxonomy earns NOTHING at the
    feasibility layer beyond this one guard (dalembert's cheaper rival law: "free acid consumed + water out ->
    GUARDED" covers the same firing set), so there is no sound NEW feasibility-layer work to ship.

TWO NON-KILLS, verified so they are not chased:
    * The anhydride "leak" (R48 does not GUARD 2 acetic acid -> acetic anhydride + water) is HARMLESS: the ΔG
      estimator already returns UNKNOWN there (not a fabricated FAVORABLE), so there is no lie to catch and no
      reason to touch R48's conjunction.
    * Friedel-Crafts C-C alkylation (benzene + ethanol -> ethylbenzene + water) is correctly NOT vouched by the
      corrected formed-bond predicate -- KILL-3(i) is recoverable, so it is not the fatal defect (KILL-1 is).

THE REDUX (the sound hunter, PR-2-real, deferred -- see POOR_MAN_INGENUITY_GATE_SCOPE_v0.1.md):
    (1) the recognizer at the ENUMERATION FRONTIER (``routes.py`` where the transform object CappedScission/
        BondOrderEdit still carries the exact local bond edit -> atom-map-sound, immune to KILL-1/KILL-3);
    (2) per-class REAL FEASIBILITY ENVELOPES = the conditions each class needs (activation / catalyst / water
        removal / solvent) as sourced/textbook REALITY (the allowed "ISA of chemistry", never a per-reaction
        lookup); (3) the ingenuity / poor-man reward gated on the KITCHEN CAPABILITY MODEL
        ([[kitchen-is-the-lab]]) checking (2)'s conditions against household + outdoors equipment -- NEVER on
        graph topology or a ΔG proxy.

RDKit-free; imports and runs the REAL production predicate, so the evidence tracks the shipped code.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.bond_enthalpy import _bond_multiset
from smartchem.experiment.feasibility import (
    _acyl_group_counts,
    _is_intermolecular_acyl_condensation,
    _is_water,
    feasibility_of_step,
)
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name

FROZEN_HASH = "d7c613ab53073618dde5963b8d55df9231c83a5ce04cf9a5f5f34a3d8dea64f1"


def _mol(name_or_smiles: str):
    ns = structure_by_name(name_or_smiles)
    if ns is not None and ns.canonical_molecule is not None:
        return ns.canonical_molecule
    return parse_smiles(name_or_smiles)


def _step(reactants, products) -> ExperimentStep:
    R = [x if not isinstance(x, str) else _mol(x) for x in reactants]
    P = [x if not isinstance(x, str) else _mol(x) for x in products]
    return ExperimentStep(
        STEP_SCHEMA, target=P[0], reactants=tuple(R), products=tuple(P),
        reagents=(), envelope=ConditionEnvelope.unknown(),
    )


def _net_formed(step: ExperimentStep) -> Counter:
    r = sum((_bond_multiset(m) for m in step.reactants), Counter())
    p = sum((_bond_multiset(m) for m in step.products), Counter())
    return p - r


def topological_vouched(step: ExperimentStep) -> bool:
    """The proposed PR-2 ``VOUCHED heteroatom dehydrative alkylation`` predicate, modeled at its STRONGEST -- keyed
    on the FORMED C-heteroatom bond (dalembert KILL-3 refinement, so it correctly rejects Friedel-Crafts C-C and
    the acid class), over the elementary intermolecular shape, with no free acid consumed.  This is exactly the
    predicate the design would have shipped.  Its fatal flaw is what it OMITS: any check that the reaction
    proceeds without catalysis / is reachable in a kitchen.  It is pure graph topology."""
    nwr = [m for m in step.reactants if not _is_water(m)]
    nwp = [m for m in step.products if not _is_water(m)]
    if len(nwr) != 2 or len(nwp) != 1:
        return False
    if sum(_is_water(m) for m in step.products) - sum(_is_water(m) for m in step.reactants) <= 0:
        return False
    if _is_intermolecular_acyl_condensation(step):
        return False  # the acid class is R48-GUARDED, never VOUCHED
    r_acid = sum(_acyl_group_counts(m)[0] for m in step.reactants)
    p_acid = sum(_acyl_group_counts(m)[0] for m in step.products)
    if (p_acid - r_acid) != 0:
        return False  # a free acid changed -> not the clean alcohol-alkylation shape
    formed = _net_formed(step)
    return (formed.get(("C", "N", 1), 0) + formed.get(("C", "O", 1), 0)) >= 1


# (label, reactants, products, NEEDS_CATALYSIS_OR_FORCING, EXPECT_TOPOLOGICAL_VOUCHED)
# The chemistry note (needs-catalysis) is REALITY (textbook): borrowing-hydrogen amination of alcohols and
# Friedel-Crafts alkylation do not proceed at kitchen conditions.  The point of the table: the topological
# predicate cannot SEE that column, so it VOUCHES rows that need catalysis (the two amination rows).
_KILL_CASES = [
    ("caffeine_n_methylation_by_methanol", ["theophylline", "methanol"], ["caffeine", "O"], True, True),
    ("aniline_ethanol_n_alkylation", ["Nc1ccccc1", "CCO"], ["CCNc1ccccc1", "O"], True, True),
    ("diethyl_ether_from_ethanol", ["CCO", "CCO"], ["CCOCC", "O"], True, False),
    ("friedel_crafts_c_c", ["c1ccccc1", "CCO"], ["CCc1ccccc1", "O"], True, False),
]

# R48's GUARDED guard stays sound: fires on the acid class, silent on the alcohol/hetero cases.
_GUARD_SOUND_CASES = [
    ("paracetamol_fischer_acid", ["acetic acid", "4-aminophenol"], ["paracetamol", "O"], True),
    ("caffeine_alcohol_donor", ["theophylline", "methanol"], ["caffeine", "O"], False),
    ("aniline_ethanol_alcohol_donor", ["Nc1ccccc1", "CCO"], ["CCNc1ccccc1", "O"], False),
]


def kill_topology_not_reachable() -> dict:
    """KILL-1: the topological VOUCHED predicate fires on catalysis-required reactions -- topology does not
    encode kitchen-reachability, so it cannot gate the poor-man ingenuity reward."""
    out = {}
    vouched_but_needs_catalysis = []
    for label, r, p, needs_cat, expect in _KILL_CASES:
        step = _step(r, p)
        vouched = topological_vouched(step)
        out[label] = {
            "topological_vouched": vouched,
            "needs_catalysis_or_forcing": needs_cat,
            "matches_expected_vouched": vouched == expect,
            "estimator_feasibility": feasibility_of_step(step).direction.value,
        }
        if vouched and needs_cat:
            vouched_but_needs_catalysis.append(label)
    out["_vouched_but_needs_catalysis"] = sorted(vouched_but_needs_catalysis)
    return out


def guard_stays_sound() -> dict:
    """R48's GUARDED guard is unchanged and correct: fires on the free-acid class, silent on alcohol donors."""
    out = {}
    for label, r, p, expect in _GUARD_SOUND_CASES:
        step = _step(r, p)
        fires = _is_intermolecular_acyl_condensation(step)
        out[label] = {"guard_fires": fires, "expected": expect, "ok": fires == expect}
    return out


def non_kills() -> dict:
    """Two observations verified so they are NOT chased: the anhydride 'leak' is harmless (estimator already
    UNKNOWN, no fabricated FAVORABLE), and Friedel-Crafts is correctly not-vouched by the corrected predicate."""
    anhydride = _step(["CC(=O)O", "CC(=O)O"], ["CC(=O)OC(=O)C", "O"])
    fc = _step(["c1ccccc1", "CCO"], ["CCc1ccccc1", "O"])
    return {
        "anhydride_guard_fires": _is_intermolecular_acyl_condensation(anhydride),      # False (a completeness gap)
        "anhydride_estimator_feasibility": feasibility_of_step(anhydride).direction.value,  # UNKNOWN, not FAVORABLE
        "anhydride_leak_is_harmless": feasibility_of_step(anhydride).direction.value != "FAVORABLE",
        "friedel_crafts_topological_vouched": topological_vouched(fc),                 # False (KILL-3 recoverable)
    }


def _payload() -> dict:
    return {
        "kill_topology_not_reachable": kill_topology_not_reachable(),
        "guard_stays_sound": guard_stays_sound(),
        "non_kills": non_kills(),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check pinning the verified defer: (1) the topological VOUCHED predicate fires on
    catalysis-required reactions (KILL-1 is real); (2) R48's guard stays sound; (3) the two non-kills hold."""
    kill = kill_topology_not_reachable()
    assert kill, "kill cases must be non-empty (vacuous-green guard)"
    assert all(row["matches_expected_vouched"] for k, row in kill.items() if not k.startswith("_")), kill
    # THE fatal kill: at least one catalysis-required reaction is VOUCHED by topology (both aminations, in fact).
    assert kill["_vouched_but_needs_catalysis"] == [
        "aniline_ethanol_n_alkylation", "caffeine_n_methylation_by_methanol",
    ], kill["_vouched_but_needs_catalysis"]

    g = guard_stays_sound()
    assert all(row["ok"] for row in g.values()), g
    assert g["paracetamol_fischer_acid"]["guard_fires"] is True, g
    assert g["caffeine_alcohol_donor"]["guard_fires"] is False, g

    nk = non_kills()
    assert nk["anhydride_leak_is_harmless"] is True, nk           # estimator UNKNOWN, no fabricated FAVORABLE
    assert nk["anhydride_guard_fires"] is False, nk               # the completeness gap, harmless
    assert nk["friedel_crafts_topological_vouched"] is False, nk  # KILL-3(i) recoverable
    return True


if __name__ == "__main__":  # pragma: no cover
    ok = validate()
    print(f"validate() -> {ok}")
    print(f"content_hash() -> {content_hash()}")
