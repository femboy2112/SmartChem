"""POOR-MAN-INGENUITY-SCISSORS-01 (R50, PR-2): why the poor-man *ingenuity* reward is unrealizable
soundly on today's models -- the committed evidence behind the second verified defer.

R49 killed a FEASIBILITY-LAYER ingenuity reward (topology cannot gate a capability reward). The redux
(PR-2-real) moved the reward to the ENUMERATION FRONTIER, keyed on the live transform's atom-mapped local
bond edit, and gated on "the existing capability stack" + a per-CLASS condition envelope. A four-bearing
adversarial DESIGN gate (dalembert + evil-morty soundness, birdperson architecture, a daniel empirical
census) killed *that* too, and together the bearings proved a deeper result than any one of them -- the
**ingenuity scissors**:

  * to be INGENIOUS ("wtf how -- OK it works") a route must be UNCONVENTIONAL -> it has no per-reaction
    sourced record (that is what makes it unconventional);
  * sound reachability for an UNSOURCED route can only come from a DERIVED model (topology -> class ->
    envelope);
  * that derived model is UNSOUND across the kitchen boundary (KILL-1 below): condition determinants
    (chemoselectivity, sterics, remote electronics) are unbounded-radius, so a bounded-radius local-edit
    fingerprint collides -- one CLASS label straddles kitchen and not-kitchen;
  * so the only SOUND, non-vacuous poor-man signal available today (per-reaction-sourced x commodity-tier)
    fires ONLY on already-documented CONVENTIONAL routes (census below: methyl salicylate, 1 of 45 registered
    targets), never the unconventional ones the directive wants.

Therefore the ingenuity reward is deferred until a real substrate-aware feasibility model exists (one that
sees the whole molecule -- catalysis, chemoselectivity, sterics).

R51 UPDATE -- the catalyst-availability half is now BUILT; the defer still stands on KILL-1.
CATALYST-OBTAIN-01 (:mod:`smartchem.experiment.catalyst_availability`) shipped the FIRST increment of that
"real substrate-aware model": a sound catalyst-obtainability gate (grounded classifier + a burden-of-proof
flip -- a DECLARED catalyst passes only if positively kitchen-obtainable, else it BLOCKS).  That deliberately
DISCHARGES two of this probe's SUPPORTING observations -- KILL-2b (a SEED record now carries a structured
catalyst) and the blindness KILL-2 measured (the obtainability model now EXCLUDES a declared Ru/Ir catalyst).
It does NOT reopen the ingenuity reward: the LOAD-BEARING kill is KILL-1 (the enumeration-frontier RECOGNIZER
cannot carry an unbounded-radius envelope on a bounded-radius edit), which is untouched, and Blade 1 (the
census) is untouched.  So the two blades still close and the reward stays deferred; what changed is that the
capability stack is no longer *catalyst-obtainability*-blind.  See
docs/research/CATALYST_OBTAINABILITY_SCOPE_v0.1.md and the R49 sibling
experiments/poor_man_ingenuity_gate_defer_probe.py.  Every fact below is recomputed from live production code.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.reagents import commodity_for
from smartchem.decompiler_conditions import SEED_CONDITIONS
from smartchem.experiment.catalyst_availability import (
    catalyst_availability, is_kitchen_obtainable, route_catalyst_blockers)
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.equipment import equipment_for_envelope
from smartchem.experiment.step import _ident
from smartchem.process_constraints import ProcessBounds, evaluate_process
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.structure_descent import _join, capped_scissions

#: The frozen fingerprint of :func:`_payload`.  A live code change that alters the LOAD-BEARING kill (KILL-1) or
#: the census, or that changes the now-built catalyst-obtainability state, breaks this loudly -- the tripwire that
#: the defer's premises moved.  Volatile counts (registry size, SEED size) are deliberately NOT hashed.  Re-frozen
#: at R51 when CATALYST-OBTAIN-01 discharged KILL-2b + the KILL-2 blindness (deliberately, in the open).
FROZEN_HASH = "56fa061c2b206d95538227fc2d8e46b4adb5678a55cf555df19a490180b3029d"

_WATER = parse_smiles("O")

# -- KILL-1 (LOAD-BEARING, UNTOUCHED): the atom-mapped local edit collides across the kitchen boundary --------
# Each row is (label, ester SMILES, acid SMILES, alcohol SMILES, kitchen-reachable?).  Every row is the
# SAME reaction class ("primary alcohol + carboxylic acid -> ester + water", Fischer esterification), read
# backward from the ester as the real frontier transform does.  The amino members straddle to NOT-kitchen:
# the amine is the stronger nucleophile, so heating the amino-alcohol with the acid gives the N-acyl amide,
# not the O-ester -- selective O-esterification needs amine protection/deprotection (multi-step), not a
# kitchen one-pot.  Pentyl/heptyl acetate are classic hobby "banana oil" Fischer esters.  This is the kill
# the whole DEFER rests on, and CATALYST-OBTAIN-01 does NOT touch it: it is a RECOGNIZER-radius kill, not a
# catalyst-obtainability kill.
_ESTER_FAMILY = (
    ("pentyl acetate", "CC(=O)OCCCCC", "CC(=O)O", "CCCCCO", True),
    ("heptyl acetate", "CC(=O)OCCCCCCC", "CC(=O)O", "CCCCCCCO", True),
    ("5-aminopentyl acetate", "CC(=O)OCCCCCN", "CC(=O)O", "NCCCCCO", False),
    ("7-aminoheptyl acetate", "CC(=O)OCCCCCCCN", "CC(=O)O", "NCCCCCCCO", False),
)


def _edit_signature(cs) -> tuple[tuple, tuple]:
    """The atom-mapped local bond edit a frontier class recognizer would read: the multiset of
    (sorted element pair, bond order) for the broken (``cut``) and formed (``caps``) bonds, in the joined
    reactant+reagents index space (so element labels are real, not positional)."""
    atoms, _bonds, _off = _join(cs.reactant, cs.reagents)
    cut = tuple(sorted(Counter(tuple(sorted((atoms[b.i], atoms[b.j]))) + (b.order,) for b in cs.cut).items()))
    cap = tuple(sorted(Counter(tuple(sorted((atoms[b.i], atoms[b.j]))) + (b.order,) for b in cs.caps).items()))
    return cut, cap


def _esterification_scission(ester_smiles: str, acid_smiles: str, alcohol_smiles: str):
    """Find, among the REAL capped scissions of the ester (water as the mediating reagent), the one whose
    two products are the acid and the alcohol -- i.e. the Fischer esterification read backward."""
    ester = parse_smiles(ester_smiles)
    want = sorted(
        [sorted(Counter(parse_smiles(acid_smiles).canonical().atoms).items()),
         sorted(Counter(parse_smiles(alcohol_smiles).canonical().atoms).items())]
    )
    edges, _complete = capped_scissions(ester, (_WATER,), max_reactant_cuts=1, budget=100_000)
    for cs in edges:
        prods = cs.products
        if len(prods) == 2 and sorted(sorted(Counter(p.atoms).items()) for p in prods) == want:
            return cs
    raise AssertionError(f"no esterification scission found for {ester_smiles!r}")


def radius_collision():
    """KILL-1: every member of the Fischer family has a byte-identical atom-mapped local edit, yet the
    members straddle the kitchen boundary -- so a class keyed on the local edit cannot carry the right
    condition envelope.  The invariance across chain length AND terminal group is the unbounded-radius
    structure theorem made live: no fixed recognizer radius separates the kitchen from the non-kitchen row."""
    sigs = {}
    for label, ester, acid, alc, _kitchen in _ESTER_FAMILY:
        sigs[label] = _edit_signature(_esterification_scission(ester, acid, alc))
    distinct_edits = {s for s in sigs.values()}
    kitchen = sorted(lbl for lbl, _e, _a, _al, k in _ESTER_FAMILY if k)
    not_kitchen = sorted(lbl for lbl, _e, _a, _al, k in _ESTER_FAMILY if not k)
    (only_cut, only_cap), = distinct_edits  # asserts exactly one edit signature across the whole family
    return {
        "all_edits_identical": len(distinct_edits) == 1,
        "cut": list(only_cut),
        "caps": list(only_cap),
        "kitchen_members": kitchen,
        "not_kitchen_members": not_kitchen,
        "collision_straddles_boundary": bool(kitchen) and bool(not_kitchen) and len(distinct_edits) == 1,
    }


# -- KILL-2 (BOUNDARY, R51): the OLD process/equipment/reagent-tier legs stay catalyst-agnostic BY DESIGN ------
def process_equipment_legs_are_catalyst_agnostic():
    """R50 measured that the process/equipment/consumed-reagent legs do NOT EXCLUDE a declared Ru/Ir catalyst.
    That is STILL TRUE and CORRECT: those legs judge time/attention/equipment/consumed-stock, not catalyst
    obtainability -- a different axis.  It is no longer a *kill*, because CATALYST-OBTAIN-01 added the missing
    axis as a SEPARATE leg (see :func:`catalyst_obtainability_gate_blocks`).  This function documents the
    boundary: the honest envelope with the metal catalyst DECLARED still passes these three legs unchanged."""
    env = _metal_catalyst_envelope()
    any_excluded = any(evaluate_process([env], ProcessBounds.preset(name)).exclusions
                       for name in ("quick", "low-touch", "unconstrained"))
    items = equipment_for_envelope(env)
    equipment_names_catalyst = any(
        "cataly" in (it.name + it.reason).lower() or " ru" in (" " + it.name.lower())
        for it in items
    )
    consumed_obtainable = {}
    for nm in ("theophylline", "methanol", "water"):
        c = commodity_for(structure_by_name(nm).molecule)
        consumed_obtainable[nm] = (c.availability.value if c else None)
    return {
        "declared_catalyst": list(env.catalysts),
        "process_legs_exclude": bool(any_excluded),          # False -- process is not the obtainability axis
        "equipment_names_catalyst": equipment_names_catalyst,  # False -- equipment is not the obtainability axis
        "all_consumed_obtainable": all(v is not None for v in consumed_obtainable.values()),
    }


def _metal_catalyst_envelope() -> ConditionEnvelope:
    """The honest, complete borrowing-hydrogen N-alkylation envelope -- metal catalyst and forcing temperature
    DECLARED, nothing omitted -- the exact input the R50 redux would have VOUCHED."""
    return ConditionEnvelope(
        temperature=Interval(423.0, 453.0, "K"),  # ~150-180 C
        catalysts=("Ru or Ir borrowing-hydrogen catalyst",),
        medium="neat / solventless",
        status=EvidenceStatus.EXPERIMENTAL,
        provenance="textbook: borrowing-hydrogen N-alkylation of amines/amides with alcohols requires Ru/Ir",
    )


class _FakeStep:
    def __init__(self, env): self.envelope = env


class _FakeRoute:
    def __init__(self, envs): self.steps = [_FakeStep(e) for e in envs]


def catalyst_obtainability_gate_blocks():
    """R51 DISCHARGE of the KILL-2 blindness: the NEW obtainability leg (CATALYST-OBTAIN-01) now EXCLUDES the
    declared Ru/Ir catalyst the old stack silently VOUCHED.  A DECLARED catalyst the kitchen cannot positively
    obtain (an industrial metal catalyst, or an unrecognized one -- the burden-of-proof flip) produces a hard
    blocker; the sourced kitchen catalyst (isopentyl acetate's H2SO4 -> HARDWARE) does NOT.  So the poor-man
    stack is no longer catalyst-obtainability-blind -- while KILL-1 (the recogniser) keeps the reward deferred."""
    metal_env = _metal_catalyst_envelope()
    metal_blockers = route_catalyst_blockers(_FakeRoute([metal_env]))
    kitchen_env = ConditionEnvelope(
        catalysts=("sulfuric acid",), medium="neat; acid-catalyzed",
        status=EvidenceStatus.EXPERIMENTAL, provenance="Fischer acid catalyst; kitchen-obtainable",
    )
    kitchen_blockers = route_catalyst_blockers(_FakeRoute([kitchen_env]))
    return {
        "metal_catalyst_blocked": bool(metal_blockers),
        "metal_catalyst_tier_not_kitchen": not is_kitchen_obtainable(
            catalyst_availability("Ru or Ir borrowing-hydrogen catalyst")),
        "kitchen_catalyst_not_blocked": kitchen_blockers == (),
    }


def seed_catalyst_now_populated():
    """R51 DISCHARGE of KILL-2b: exactly ONE SEED_CONDITIONS record (isopentyl acetate, the only one whose
    sourced quote names a specific catalyst -- "conc. H2SO4") now carries a STRUCTURED catalyst, and it is
    kitchen-obtainable (sulfuric acid -> HARDWARE), so the sourced path is no longer structurally catalyst-blind.
    The records whose quotes name no specific species stay catalysts=() (naming one would be an inference)."""
    envs = [rec.envelope for rec in SEED_CONDITIONS.values()]
    populated = [e for e in envs if e.catalysts]
    all_populated_kitchen = all(
        all(is_kitchen_obtainable(catalyst_availability(c)) for c in e.catalysts) for e in populated
    )
    return {
        "n_records_with_structured_catalyst": len(populated),
        "all_populated_catalysts_kitchen": bool(populated) and all_populated_kitchen,
    }


# -- The scissors census (Blade 1, UNTOUCHED): the only sound signal is conventional, not ingenious ----------
_CENSUS_TARGETS = ("methyl salicylate", "caffeine", "paracetamol")
_KITCHEN_TIERS = ("grocery", "pharmacy", "hardware", "pool_garden")


def _availability(mol) -> str | None:
    c = commodity_for(mol)
    return c.availability.value if c else None


def sourced_signal_is_conventional():
    """The empirical scissors: of the registered targets, the flagship drug targets (caffeine, paracetamol)
    have NO fully-sourced route, while the one target whose route is both per-reaction-sourced and
    commodity-terminated is a CONVENTIONAL textbook ester (methyl salicylate).  The sound signal is the
    opposite of ingenuity."""
    water = structure_by_name("water").molecule
    out = {}
    for name in _CENSUS_TARGETS:
        target = structure_by_name(name).molecule
        compiled = compile_synthesis(target, reagents=(water,))
        best = None
        for fit in compiled.ranked:
            steps = fit.route.steps
            all_sourced = all(s.envelope.status is EvidenceStatus.EXPERIMENTAL for s in steps)
            made = {_ident(p) for s in steps for p in s.products}
            leaves = [r for s in steps for r in s.reactants if _ident(r) not in made]
            leaf_tiers = [_availability(m) for m in leaves]
            all_kitchen = bool(leaf_tiers) and all(t in _KITCHEN_TIERS for t in leaf_tiers)
            row = {"sourced": all_sourced, "kitchen_leaves": all_kitchen, "n_steps": len(steps)}
            if best is None or (all_sourced and all_kitchen):
                best = row
        out[name] = best if best is not None else {"sourced": False, "kitchen_leaves": False, "n_steps": 0}
    return {
        "methyl_salicylate_fully_sourced_kitchen": (
            out["methyl salicylate"]["sourced"] and out["methyl salicylate"]["kitchen_leaves"]
        ),
        "caffeine_sourced": out["caffeine"]["sourced"],
        "paracetamol_sourced": out["paracetamol"]["sourced"],
        "per_target": out,
    }


def _payload() -> dict:
    """The load-bearing conclusions of the defer, recomputed from live code -- the frozen subject.  Volatile
    counts (registry size, SEED size) are excluded so the hash breaks only on a real premise change.  R51: the
    two catalyst sub-observations are now DISCHARGE records (KILL-2b populated, the KILL-2 blindness repaired at
    the obtainability layer); KILL-1 + the census remain the load-bearing DEFER evidence."""
    return {
        "schema": "poor-man-ingenuity-scissors-01",
        "round": 51,
        "kill_1_radius_collision": radius_collision(),
        "kill_2_process_equipment_legs_agnostic": process_equipment_legs_are_catalyst_agnostic(),
        "r51_catalyst_gate_now_blocks": catalyst_obtainability_gate_blocks(),
        "r51_seed_catalyst_now_populated": seed_catalyst_now_populated(),
        "scissors_census": {
            k: v for k, v in sourced_signal_is_conventional().items() if k != "per_target"
        },
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert the DEFER still holds against live code (KILL-1 + census) AND the R51 discharges are real.
    Raises on any drift; returns True when every premise is intact."""
    # -- the LOAD-BEARING kill (the reward stays deferred on this) --
    k1 = radius_collision()
    assert k1["all_edits_identical"], "KILL-1 broke: the Fischer family no longer shares one local edit"
    assert k1["collision_straddles_boundary"], "KILL-1 broke: the identical-edit collision no longer straddles kitchen/not-kitchen"

    # -- Blade 1: the census (the sound signal is conventional, not ingenious) --
    census = sourced_signal_is_conventional()
    assert census["methyl_salicylate_fully_sourced_kitchen"], "census drift: methyl salicylate is no longer the sourced-kitchen route"
    assert not census["caffeine_sourced"], "census drift: caffeine now has a fully-sourced route"
    assert not census["paracetamol_sourced"], "census drift: paracetamol now has a fully-sourced route"

    # -- R51: the OLD process/equipment/reagent legs stay catalyst-agnostic BY DESIGN (a boundary, not a kill) --
    legs = process_equipment_legs_are_catalyst_agnostic()
    assert not legs["process_legs_exclude"], "boundary drift: the process leg now excludes a catalyst (it is not the obtainability axis)"
    assert not legs["equipment_names_catalyst"], "boundary drift: equipment now names the catalyst"
    assert legs["all_consumed_obtainable"], "drift: a consumed species is no longer obtainable"

    # -- R51 DISCHARGE: the NEW obtainability leg blocks the metal catalyst; the sourced kitchen catalyst passes --
    gate = catalyst_obtainability_gate_blocks()
    assert gate["metal_catalyst_blocked"], "R51 regressed: the obtainability gate no longer blocks the Ru/Ir catalyst"
    assert gate["metal_catalyst_tier_not_kitchen"], "R51 regressed: the metal catalyst is classified kitchen-obtainable"
    assert gate["kitchen_catalyst_not_blocked"], "R51 regressed: the sourced kitchen catalyst (H2SO4) is being blocked (false-EXCLUDE)"

    # -- R51 DISCHARGE: a SEED record now carries a structured, kitchen-obtainable catalyst --
    seed = seed_catalyst_now_populated()
    assert seed["n_records_with_structured_catalyst"] >= 1, "R51 regressed: no SEED record carries a structured catalyst"
    assert seed["all_populated_catalysts_kitchen"], "R51: a populated SEED catalyst is not kitchen-obtainable (would false-EXCLUDE a sourced route)"
    return True


if __name__ == "__main__":
    validate()
    print("validate() -> True (KILL-1 + census hold; R51 catalyst discharges real)")
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    import pprint
    pprint.pprint(_payload())
