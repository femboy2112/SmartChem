"""CATALYST-OBTAIN-01: the poor-man catalyst-obtainability gate.

The committed probe (:mod:`experiments.catalyst_availability_probe`) is the comprehensive frozen evidence; these
are the fast regression pins over the SAME live behavior, kept independent of the probe so a probe refactor cannot
silently drop coverage.  The soundness law: the gate may only EXCLUDE (a catalyst the kitchen cannot get) or stay
NEUTRAL (a positively-recognized kitchen catalyst / an undeclared one) -- it never VOUCHes.  false-VOUCH >>
false-UNRECOGNIZED, so a declared catalyst passes ONLY if positively kitchen-obtainable (the burden-of-proof flip).
"""
from __future__ import annotations

from smartchem.conditions import ConditionEnvelope
from smartchem.contracts import EvidenceStatus
from smartchem.data.reagents import Availability
from smartchem.experiment.catalyst_availability import (
    NON_KITCHEN_METALS, catalyst_availability, is_kitchen_obtainable, route_catalyst_blockers)
from experiments import catalyst_availability_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_kitchen_acids_and_bases_classify_to_a_kitchen_tier():
    assert catalyst_availability("sulfuric acid") is Availability.HARDWARE
    assert catalyst_availability("conc. H2SO4") is Availability.HARDWARE  # a variant declaration, not false-excluded
    assert catalyst_availability("acetic acid") is Availability.GROCERY
    for c in ("sodium hydroxide", "NaOH", "KOH", "hydrochloric acid", "HCl", "muriatic acid"):
        assert is_kitchen_obtainable(catalyst_availability(c)), c


def test_metal_catalysts_classify_industrial_including_the_eponymous_ones():
    for c in ("palladium on carbon", "Pd/C", "PtO2", "Raney nickel", "Grubbs II", "Grubbs",
              "Lindlar catalyst", "Wilkinson's catalyst", "Crabtree's catalyst", "Jacobsen catalyst",
              "RuCl3", "ruthenium trichloride", "TiCl4"):
        assert catalyst_availability(c) is Availability.INDUSTRIAL, c
        assert not is_kitchen_obtainable(catalyst_availability(c)), c


def test_unrecognized_and_empty_names_fail_closed_to_none():
    # None is "unrecognized", NOT "kitchen" -- a declared unrecognized catalyst is BLOCKED by the flip below.
    for c in ("Ru or Ir borrowing-hydrogen catalyst", "p-TsOH", "lipase", "heat", "", "   ",
              "palladium-free conditions"):
        assert catalyst_availability(c) is None, c
    assert catalyst_availability(None) is None  # type: ignore[arg-type]  -- non-string, no crash


def test_no_classifier_miss_is_ever_kitchen_the_no_false_vouch_invariant():
    # the load-bearing polarity: an unrecognized name must never read as kitchen-obtainable.
    for c in ("Ru or Ir borrowing-hydrogen catalyst", "some novel metallaphotoredox catalyst", "", "?!"):
        assert not is_kitchen_obtainable(catalyst_availability(c)), c


class _FakeStep:
    def __init__(self, env): self.envelope = env


class _FakeRoute:
    def __init__(self, envs): self.steps = [_FakeStep(e) for e in envs]


def _declaring(*catalysts: str) -> ConditionEnvelope:
    if not catalysts:
        return ConditionEnvelope.unknown()
    return ConditionEnvelope(catalysts=tuple(catalysts), medium="neat",
                             status=EvidenceStatus.EXPERIMENTAL, provenance="test")


def test_burden_of_proof_flip_declared_and_not_positively_kitchen_blocks():
    # undeclared -> genuine silence -> neutral
    assert route_catalyst_blockers(_FakeRoute([_declaring()])) == ()
    # declared kitchen -> neutral
    assert route_catalyst_blockers(_FakeRoute([_declaring("sulfuric acid")])) == ()
    # declared industrial metal -> BLOCK (with a precise reason)
    metal = route_catalyst_blockers(_FakeRoute([_declaring("palladium on carbon")]))
    assert metal == ("catalyst not kitchen-obtainable: palladium on carbon [industrial]",)
    # declared BUT unrecognized -> BLOCK (uncertainty reason -- never a silent pass; the dalembert KILL-1 fix)
    unk = route_catalyst_blockers(_FakeRoute([_declaring("Ru or Ir borrowing-hydrogen catalyst")]))
    assert len(unk) == 1 and "uncertain obtainability" in unk[0]


def test_transition_metal_guard_includes_d_block_excludes_s_block():
    # periodic-table reality: catalytic transition/platinum/heavy metals are non-kitchen; alkali/alkaline-earth
    # (which make genuine kitchen base catalysts like NaOH/K2CO3) are NOT, so a base salt is never false-excluded.
    assert {"Fe", "Cu", "Ni", "Mn", "Ti", "Pd", "Pt", "Ru", "Rh", "Ir"} <= NON_KITCHEN_METALS
    assert not ({"Li", "Na", "K", "Ca", "Mg"} & NON_KITCHEN_METALS)
