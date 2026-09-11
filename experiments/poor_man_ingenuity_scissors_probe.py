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
sees the whole molecule -- catalysis, chemoselectivity, sterics). Every fact below is recomputed from live
production code; nothing is an agent's story. See docs/research/POOR_MAN_INGENUITY_GATE_SCOPE_v0.1.md and
the R49 sibling experiments/poor_man_ingenuity_gate_defer_probe.py.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.contracts import EvidenceStatus
from smartchem.data.reagents import commodity_for
from smartchem.decompiler_conditions import SEED_CONDITIONS
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.equipment import equipment_for_envelope
from smartchem.experiment.step import _ident
from smartchem.process_constraints import ProcessBounds, evaluate_process
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.structure_descent import _join, capped_scissions

#: The frozen fingerprint of :func:`_payload`.  A live code change that alters any kill (a new catalyst
#: model, a per-class envelope, a SEED record that flips a census target) breaks this loudly -- the tripwire
#: that the defer's premises changed.  Volatile counts (registry size, SEED size) are deliberately NOT hashed.
FROZEN_HASH = "e2189bdc015f9e045b8bb77d61ae4a77c2f51ed7afb6409af22a751dfef5a2f2"

_WATER = parse_smiles("O")

# -- KILL-1: the atom-mapped local edit collides across the kitchen boundary, unboundedly -------------
# Each row is (label, ester SMILES, acid SMILES, alcohol SMILES, kitchen-reachable?).  Every row is the
# SAME reaction class ("primary alcohol + carboxylic acid -> ester + water", Fischer esterification), read
# backward from the ester as the real frontier transform does.  The amino members straddle to NOT-kitchen:
# the amine is the stronger nucleophile, so heating the amino-alcohol with the acid gives the N-acyl amide,
# not the O-ester -- selective O-esterification needs amine protection/deprotection (multi-step), not a
# kitchen one-pot.  Pentyl/heptyl acetate are classic hobby "banana oil" Fischer esters.
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


# -- KILL-2: the "existing capability stack" is structurally blind to catalysis ----------------------
def catalyst_blind_reward():
    """KILL-2: build the caffeine N-methylation envelope the way L2 is *supposed* to be built -- honest and
    complete, the metal catalyst and forcing temperature DECLARED, nothing omitted -- then run the three
    legs the redux names as the kitchen capability model.  Not one returns EXCLUDED, so a reward gated on
    this stack would VOUCH a Ru/Ir-catalyzed reaction as poor-man-reachable (R49's KILL-1, one storey down)."""
    env = ConditionEnvelope(
        temperature=Interval(423.0, 453.0, "K"),  # ~150-180 C
        catalysts=("Ru or Ir borrowing-hydrogen catalyst",),
        medium="neat / solventless",
        status=EvidenceStatus.EXPERIMENTAL,
        provenance="textbook: borrowing-hydrogen N-alkylation of amines/amides with alcohols requires Ru/Ir",
    )
    fits = {name: evaluate_process([env], ProcessBounds.preset(name)).status.value
            for name in ("quick", "low-touch", "unconstrained")}
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
        "fits_statuses": fits,
        "any_leg_excluded": bool(any_excluded),
        "equipment_names_catalyst": equipment_names_catalyst,
        "all_consumed_obtainable": all(v is not None for v in consumed_obtainable.values()),
        "consumed_tiers": consumed_obtainable,
    }


def seed_catalysts_empty():
    """KILL-2b: every sourced SEED_CONDITIONS record has an empty structured ``catalysts`` field -- where a
    catalyst is genuinely required it is buried in free-text ``medium``.  So even the sourced path carries
    zero structured catalyst information, and it is the authoring template a per-class table would copy."""
    envs = [rec.envelope for rec in SEED_CONDITIONS.values()]
    return {
        "all_catalysts_field_empty": all(e.catalysts == () for e in envs),
        "any_catalyst_in_medium_text": any("cataly" in e.medium.lower() or "acid" in e.medium.lower()
                                           for e in envs),
    }


# -- The scissors census: the only sound signal is conventional, not ingenious ----------------------
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
    counts (registry size, SEED size) are excluded so the hash breaks only on a real premise change."""
    return {
        "schema": "poor-man-ingenuity-scissors-01",
        "round": 50,
        "kill_1_radius_collision": radius_collision(),
        "kill_2_catalyst_blind_reward": {
            k: v for k, v in catalyst_blind_reward().items() if k != "consumed_tiers"
        },
        "kill_2b_seed_catalysts_empty": seed_catalysts_empty(),
        "scissors_census": {
            k: v for k, v in sourced_signal_is_conventional().items() if k != "per_target"
        },
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert every kill still holds against live code.  Raises on any drift; returns True when the defer's
    premises are all intact."""
    k1 = radius_collision()
    assert k1["all_edits_identical"], "KILL-1 broke: the Fischer family no longer shares one local edit"
    assert k1["collision_straddles_boundary"], "KILL-1 broke: the identical-edit collision no longer straddles kitchen/not-kitchen"

    k2 = catalyst_blind_reward()
    assert not k2["any_leg_excluded"], "KILL-2 repaired: a leg now EXCLUDES the declared catalyst (a catalyst model may exist)"
    assert not k2["equipment_names_catalyst"], "KILL-2 drift: equipment now names the catalyst"
    assert k2["all_consumed_obtainable"], "KILL-2 drift: a consumed species is no longer obtainable"

    k2b = seed_catalysts_empty()
    assert k2b["all_catalysts_field_empty"], "KILL-2b repaired: a SEED record now populates structured catalysts"

    census = sourced_signal_is_conventional()
    assert census["methyl_salicylate_fully_sourced_kitchen"], "census drift: methyl salicylate is no longer the sourced-kitchen route"
    assert not census["caffeine_sourced"], "census drift: caffeine now has a fully-sourced route"
    assert not census["paracetamol_sourced"], "census drift: paracetamol now has a fully-sourced route"
    return True


if __name__ == "__main__":
    validate()
    print("validate() -> True (all four kills intact)")
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    import pprint
    pprint.pprint(_payload())
