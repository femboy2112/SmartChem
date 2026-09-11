"""CATALYST-OBTAIN-01: the committed evidence that the poor-man catalyst-obtainability gate is SOUND.

The gap (R50 KILL-2, re-verified): the kitchen capability model was blind to catalysis -- a step's declared
catalyst was gated by nothing, so a route needing an un-buyable metal catalyst read as poor-man-reachable.
:mod:`smartchem.experiment.catalyst_availability` is the missing organ.  This probe freezes the four load-bearing
soundness properties the R50 design gate (dalembert/evil-morty/birdperson/daniel) demanded, each recomputed from
live production code:

1. CLASSIFIER POLARITY -- kitchen acids/bases classify to a kitchen tier; catalytic metals classify INDUSTRIAL;
   an unrecognized name classifies to None (NOT a kitchen tier).  A miss NEVER lands on a kitchen tier.
2. THE BURDEN-OF-PROOF FLIP (dalembert KILL-1) -- a route may pass ONLY if every DECLARED catalyst is positively
   kitchen-obtainable; a declared metal OR a declared-but-unrecognized catalyst BLOCKS (false-VOUCH >>
   false-UNRECOGNIZED).  An undeclared catalyst (catalysts=()) is genuine silence and never blocks.
3. THE TRANSITION-METAL GUARD (dalembert KILL-2) -- the non-kitchen metal set is a periodic-table fact that
   INCLUDES the catalytic transition/platinum/heavy metals and EXCLUDES the s-block, so a kitchen base salt
   (NaOH) is never false-excluded while a d-block metal salt would be.
4. THE NEUTRAL LITMUS (daniel) -- the one live route that exercises the gate end-to-end (isopentyl acetate's
   sourced conc. H2SO4) carries the structured catalyst and is correctly NOT blocked (sulfuric acid -> HARDWARE).

There is NO fuzzy substring/element-token scan (it is negation-blind and substring-catastrophic -- the recurring
keyword-match lesson); coverage of exotic metals is carried by the flip, not by an unsound recogniser.  Honest
boundary: no registered reaction declares a metal catalyst today, so the EXCLUDE path is a GUARD AHEAD OF ITS
DATA -- proven here on constructed routes, benign on every live one.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.conditions import ConditionEnvelope, EvidenceStatus
from smartchem.data.reagents import Availability
from smartchem.experiment.catalyst_availability import (
    NON_KITCHEN_METALS, catalyst_availability, is_kitchen_obtainable, route_catalyst_blockers)
from smartchem.experiment.compile import compile_synthesis
from smartchem.structure import structure_by_name

FROZEN_HASH = "a2a55d3f8ec90055e32579754161f3f506a0196fdc91da25e3aff96f12de5661"

# representative battery: every row's tier is checked against its expectation in :func:`validate`.
_KITCHEN = ("sulfuric acid", "conc. H2SO4", "sodium hydroxide", "NaOH", "KOH", "acetic acid",
            "hydrochloric acid", "HCl", "muriatic acid")
_INDUSTRIAL = ("palladium on carbon", "Pd/C", "PtO2", "Adams' catalyst", "Raney nickel", "Grubbs II",
               "Grubbs", "Lindlar catalyst", "Wilkinson's catalyst", "Crabtree's catalyst",
               "Jacobsen catalyst", "RuCl3", "ruthenium trichloride", "TiCl4")
_UNRECOGNIZED = ("Ru or Ir borrowing-hydrogen catalyst", "p-TsOH", "lipase", "heat",
                 "", "   ", "palladium-free conditions")


class _FakeStep:
    def __init__(self, env): self.envelope = env


class _FakeRoute:
    def __init__(self, envs): self.steps = [_FakeStep(e) for e in envs]


def _env(catalysts: tuple[str, ...]) -> ConditionEnvelope:
    if not catalysts:
        return ConditionEnvelope.unknown()
    return ConditionEnvelope(catalysts=catalysts, medium="neat",
                             status=EvidenceStatus.EXPERIMENTAL, provenance="probe")


def classifier_polarity() -> dict:
    """Every kitchen name -> a kitchen tier; every industrial name -> INDUSTRIAL; every unrecognized name ->
    None.  The load-bearing invariant: a miss NEVER lands on a kitchen tier (that would be a false-VOUCH)."""
    return {
        "kitchen_all_kitchen": all(is_kitchen_obtainable(catalyst_availability(c)) for c in _KITCHEN),
        "industrial_all_industrial": all(
            catalyst_availability(c) is Availability.INDUSTRIAL for c in _INDUSTRIAL),
        "unrecognized_all_none": all(catalyst_availability(c) is None for c in _UNRECOGNIZED),
        "no_miss_is_kitchen": not any(is_kitchen_obtainable(catalyst_availability(c)) for c in _UNRECOGNIZED),
    }


def burden_of_proof_flip() -> dict:
    """A DECLARED metal OR unrecognized catalyst BLOCKS; a DECLARED kitchen catalyst and an UNDECLARED one do not."""
    return {
        "undeclared_neutral": route_catalyst_blockers(_FakeRoute([_env(())])) == (),
        "kitchen_neutral": route_catalyst_blockers(_FakeRoute([_env(("sulfuric acid",))])) == (),
        "metal_blocks": bool(route_catalyst_blockers(_FakeRoute([_env(("palladium on carbon",))]))),
        "unrecognized_blocks": bool(
            route_catalyst_blockers(_FakeRoute([_env(("Ru or Ir borrowing-hydrogen catalyst",))]))),
        "mixed_blocks_only_the_metal": route_catalyst_blockers(
            _FakeRoute([_env(("palladium on carbon",)), _env(("sulfuric acid",))])
        ) == ("catalyst not kitchen-obtainable: palladium on carbon [industrial]",),
    }


def transition_metal_guard() -> dict:
    """The non-kitchen metal set is periodic-table reality: it INCLUDES catalytic transition/platinum/heavy metals
    and EXCLUDES the s-block, so a kitchen base salt (NaOH: Na is s-block) is not false-excluded."""
    d_block_and_pgm = {"Fe", "Cu", "Ni", "Mn", "Ti", "Pd", "Pt", "Ru", "Rh", "Ir", "Os", "Ag", "Au", "Zn"}
    s_block = {"Li", "Na", "K", "Rb", "Cs", "Be", "Mg", "Ca", "Sr", "Ba"}
    return {
        "includes_catalytic_metals": d_block_and_pgm <= NON_KITCHEN_METALS,
        "excludes_s_block": not (s_block & NON_KITCHEN_METALS),
        "naoh_stays_kitchen": is_kitchen_obtainable(catalyst_availability("sodium hydroxide")),
    }


def neutral_litmus() -> dict:
    """The one live end-to-end route: isopentyl acetate carries the sourced structured H2SO4 catalyst, which is
    HARDWARE-tier (kitchen), so the gate correctly does NOT block it -- the mechanism fires, benign, on real data."""
    water = structure_by_name("water").molecule
    compiled = compile_synthesis(structure_by_name("isopentyl acetate").molecule, reagents=(water,))
    carried = False
    any_blocked = False
    for fit in compiled.ranked:
        if any(s.envelope.catalysts for s in fit.route.steps):
            carried = True
        if route_catalyst_blockers(fit.route):
            any_blocked = True
    return {
        "route_carries_structured_catalyst": carried,
        "route_not_blocked": not any_blocked,
        "h2so4_is_hardware": catalyst_availability("sulfuric acid") is Availability.HARDWARE,
    }


def fail_closed() -> dict:
    """Standalone fail-closed: empty/whitespace/non-string names classify to None, never crash, never misfire."""
    return {
        "empty_none": catalyst_availability("") is None,
        "whitespace_none": catalyst_availability("   ") is None,
        "nonstring_none": catalyst_availability(None) is None,  # type: ignore[arg-type]
    }


def _payload() -> dict:
    return {
        "schema": "catalyst-obtain-01",
        "round": 51,
        "classifier_polarity": classifier_polarity(),
        "burden_of_proof_flip": burden_of_proof_flip(),
        "transition_metal_guard": transition_metal_guard(),
        "neutral_litmus": neutral_litmus(),
        "fail_closed": fail_closed(),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> bool:
    """Assert every soundness property holds against live code.  Raises on any drift."""
    p = classifier_polarity()
    assert p["kitchen_all_kitchen"], "a kitchen catalyst no longer classifies to a kitchen tier"
    assert p["industrial_all_industrial"], "an industrial metal catalyst no longer classifies INDUSTRIAL"
    assert p["unrecognized_all_none"], "an unrecognized catalyst no longer classifies None"
    assert p["no_miss_is_kitchen"], "FALSE-VOUCH: a miss now lands on a kitchen tier"

    f = burden_of_proof_flip()
    assert f["undeclared_neutral"], "an undeclared catalyst now blocks (should be genuine silence)"
    assert f["kitchen_neutral"], "FALSE-EXCLUDE: a declared kitchen catalyst now blocks"
    assert f["metal_blocks"], "FALSE-VOUCH: a declared metal catalyst no longer blocks"
    assert f["unrecognized_blocks"], "FALSE-VOUCH: a declared unrecognized catalyst no longer blocks"
    assert f["mixed_blocks_only_the_metal"], "the mixed-route blocker set drifted"

    g = transition_metal_guard()
    assert g["includes_catalytic_metals"], "the non-kitchen metal set dropped a catalytic metal"
    assert g["excludes_s_block"], "the non-kitchen metal set now includes an s-block metal (would false-exclude a base)"
    assert g["naoh_stays_kitchen"], "FALSE-EXCLUDE: NaOH is no longer kitchen-obtainable"

    n = neutral_litmus()
    assert n["route_carries_structured_catalyst"], "the isopentyl route no longer carries the structured catalyst"
    assert n["route_not_blocked"], "FALSE-EXCLUDE: the sourced kitchen H2SO4 route is being blocked"
    assert n["h2so4_is_hardware"], "sulfuric acid no longer classifies HARDWARE"

    c = fail_closed()
    assert all(c.values()), "the classifier is not fail-closed on empty/whitespace/non-string names"
    return True


if __name__ == "__main__":
    validate()
    print("validate() -> True (catalyst-obtainability gate is sound)")
    print("content_hash():", content_hash())
    print("FROZEN_HASH  :", FROZEN_HASH)
    print("match:", content_hash() == FROZEN_HASH)
    import pprint
    pprint.pprint(_payload())
