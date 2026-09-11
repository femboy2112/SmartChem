"""MOVE5-SHARED-RANKER-01: Move 5(b) (the CROSS-DOMAIN shared ranker) VERIFIED DEFER + the one sound
INTRA-chemistry consolidation the post-R38 re-recon surfaced.

ROADMAP "Move 5(b)" asks to make the chemistry ``ExperimentStep``/``ExperimentRoute`` parametric over a
"conserved-inventory transition + survival predicate" AND retrofit BOTH domains onto ONE shared ranker.  The
prior scope decision (``MOVE5_DOMAIN_NEUTRAL_PARAMETERIZATION_SCOPE_DECISION_v0.1.md``) deferred it as a
zero-call-sites abstraction, but predated R37/R38 -- which built the circuit ``CircuitRoute`` + the
``select_within_spec`` ranker as a genuine second-domain consumer.  A 4-bearing re-recon (cartography / YAGNI /
consumer-existence / structure-theorem) with the landscape moved concludes: **still DEFER, now proven** -- the
chemistry ranker (:func:`~smartchem.experiment.drafter.rank_routes`) and the circuit ranker
(:func:`~smartchem.open_circuit_pipeline.within_spec` / ``select_within_spec``) do NOT share a domain-neutral law
richer than ``sorted(key=...)``; a forced unification is lossy-or-non-neutral.  Two code-run counterexamples pin
it (dalembert):

* **CE-1 (set-relativity).**  Chemistry's ``front_index`` ranking tier is computed SET-RELATIVELY by
  :func:`~smartchem.experiment.drafter._pareto_front_indices` (a route's Pareto layer depends on its SIBLINGS --
  removing a dominator promotes what it dominated to a shallower layer).  Circuit's ``(resistance, name)`` key is
  strictly per-candidate and set-invariant.  A generic ``key: Callable[[T], K]`` evaluated per-candidate CANNOT
  reproduce ``rank_routes``; the lossless signature is ``Callable[[Sequence[T]], Callable[[T], K]]``, which is
  entirely chemistry's requirement (circuit ignores the outer argument forever) -- an abstraction whose two
  "generalizing" knobs are each pinned by exactly one caller is not a shared law, it is one domain's shape with
  the other folded in as an unused special case.

* **CE-2 (opposite fail-closed polarity).**  The SAME abstract event -- "the ranking quantity is unknown /
  undefined" -- is handled in OPPOSITE directions.  Chemistry floats an INCOMPLETE objective (a ``None`` axis) to
  the TOP layer (0), ABOVE a complete-but-dominated route (neutral-on-ignorance, the M2b fix).  Circuit EJECTS an
  out-of-band OR ``None``-cost candidate to the disclosed-reject channel (fail-closed; ``within_spec`` returns
  ``False`` before it can ever float).  A single primitive with ONE unknown-policy is therefore either unsound for
  circuits (it would float an open/short into the survivors) or wrong for chemistry (it would invert the M2b
  neutral-on-ignorance fix).

The re-recon's ONE constructive finding IS earned and shipped this round (an INTRA-chemistry consolidation, NOT
the cross-domain lift): ``_route_score`` and ``_dag_score`` duplicated the (now 11-)tier score tuple + the M2b gating
verbatim, and ``rank_routes``/``rank_dags`` duplicated the Pareto-product + front + sort wiring, kept in sync only
by a comment that ``drafter.py`` itself feared would drift ("M2b grows BOTH scorers together ... or the divergence
reopens").  Both are multi-objective + neutral-on-unknown, so ONE shared core is sound there with two real call
sites.  ``drafter.py`` now factors :func:`~smartchem.experiment.drafter._score_tuple` (the tiers) and
:func:`~smartchem.experiment.drafter._physics_ranked_order` (the wiring); the two scorers are thin verdict
extractors over the same core, so a future tier grows ONCE and the two rankings cannot diverge by omission.
Byte-identical to the pre-consolidation output.

This probe pins BOTH: the two defer counterexamples (run on the real functions) and the consolidation being live
(both scorers provably route through the one shared core).  RDKit-free; no oracle needed.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.experiment.drafter import (
    RouteFitStatus,
    _dag_score,
    _pareto_front_indices,
    _route_score,
    _score_tuple,
)
from smartchem.experiment.functorial_physics import PhysicsProduct
from smartchem.open_circuit_pipeline import CircuitStage, within_spec

FROZEN_HASH = "998ac97668c2bf85727421896a775cefd494f0ec95d0ef508ab795cc16efaf38"


# --------------------------------------------------------------------------------------------------------------
# CE-1 -- rank_routes' front_index tier is SET-RELATIVE (unrepresentable as a per-candidate key).
# --------------------------------------------------------------------------------------------------------------
def ce1_front_index_is_set_relative() -> dict:
    """P1 dominates P2 dominates P3.  With all three, layers are (0, 1, 2); drop the dominator P1 and P2's layer
    changes 1 -> 0 -- a route's front_index depends on which SIBLINGS are in the set, so no ``key(candidate)``
    evaluated in isolation can reproduce it (circuit's per-candidate key is set-invariant by contrast)."""
    p1 = PhysicsProduct(-10.0, 0.9)
    p2 = PhysicsProduct(-5.0, 0.8)
    p3 = PhysicsProduct(-1.0, 0.7)
    full = _pareto_front_indices((p1, p2, p3))
    without_p1 = _pareto_front_indices((p2, p3))
    return {
        "full": list(full),
        "without_p1": list(without_p1),
        "p2_layer_full": full[1],
        "p2_layer_without_p1": without_p1[0],
        "set_relative": full[1] != without_p1[0],
    }


# --------------------------------------------------------------------------------------------------------------
# CE-2 -- the two domains handle "unknown ranking quantity" in OPPOSITE directions.
# --------------------------------------------------------------------------------------------------------------
def ce2_opposite_failclosed_polarity() -> dict:
    """Chemistry: an incomplete objective (``None`` axis) lands the TOP layer (0), above a complete dominated
    route (layer 1) -- neutral-on-ignorance.  Circuit: an out-of-band candidate is EJECTED (``within_spec`` False);
    a ``None`` apex is a-fortiori rejected by the same guard (``open_circuit_pipeline.py`` ``if resistance is
    None: return False``).  Opposite placements for the same abstract 'unknown' event."""
    good = PhysicsProduct(-10.0, 0.9)  # complete, best
    dominated = PhysicsProduct(-1.0, 0.1)  # complete, dominated by good
    unknown = PhysicsProduct(None, None)  # incomplete -> neutral -> layer 0 (TOP)
    chem_fronts = _pareto_front_indices((good, dominated, unknown))

    r20 = CircuitStage.resistor(20).diagram  # a finite, well-formed 2-terminal resistor: cost = 20 ohms
    circ_in_band = within_spec(r20, 0, 100)  # 20 in [0, 100] -> survives
    circ_out_of_band = within_spec(r20, 0, 10)  # 20 out of [0, 10] -> EJECTED (fail-closed), never floated
    return {
        "chem_fronts": list(chem_fronts),
        "unknown_layer": chem_fronts[2],  # 0 -- an UNKNOWN objective at the TOP tier
        "dominated_layer": chem_fronts[1],  # 1 -- a KNOWN dominated route BELOW the unknown one
        "circuit_in_band": circ_in_band,
        "circuit_out_of_band": circ_out_of_band,
        "opposite_polarity": (chem_fronts[2] < chem_fronts[1]) and (circ_out_of_band is False),
    }


# --------------------------------------------------------------------------------------------------------------
# The intra-chemistry consolidation is LIVE: both scorers route through the ONE shared _score_tuple, so a route
# and a DAG with identical verdicts produce the identical key (they cannot diverge by a forgotten hand-edit).
# --------------------------------------------------------------------------------------------------------------
class _V:
    """A nested verdict holder (a RouteFit's sub-fit exposes ``.verdict``)."""

    __slots__ = ("verdict",)

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict


class _FakeRouteFit:
    """Duck-typed to the attributes ``_route_score`` reads (NESTED sub-fit verdicts)."""

    def __init__(self, status, comp, sel, feas, eq, kin, gaps, exc) -> None:
        self.status = status
        self.composability = _V(comp)
        self.selectivity = _V(sel)
        self.feasibility = _V(feas)
        self.equilibrium = _V(eq)
        self.kinetics = _V(kin)
        self.gaps = tuple(range(gaps))
        self.exclusions = tuple(range(exc))


class _FakeDagFit:
    """Duck-typed to the attributes ``_dag_score`` reads (FLAT rollup verdicts)."""

    def __init__(self, status, comp, sel, feas, eq, kin, gaps, exc) -> None:
        self.status = status
        self.composability = _V(comp)
        self.selectivity_verdict = sel
        self.feasibility_verdict = feas
        self.equilibrium_verdict = eq
        self.kinetics_verdict = kin
        self.gaps = tuple(range(gaps))
        self.exclusions = tuple(range(exc))


# (status, comp, sel, feas, eq, kin, gaps, exclusions, front_index, net_delta_g)
_BATTERY = [
    (RouteFitStatus.FITS, "COMPOSABLE", "FAVORED", "FAVORABLE", "ESSENTIALLY_COMPLETE", "FAST", 0, 0, 0, -12.5),
    (RouteFitStatus.FITS, "COMPOSABLE", "FAVORED", "UNFAVORABLE", "FAVORABLE", "FAST", 0, 0, 0, -12.5),
    (RouteFitStatus.UNKNOWN, "SINGLE_STEP", "UNKNOWN", "BORDERLINE", "BALANCED", "MODERATE", 2, 0, 1, None),
    (RouteFitStatus.EXCLUDED, "DEGENERATE", "DISFAVORED", "UNFAVORABLE", "NEGLIGIBLE", "FROZEN", 3, 4, 2, 3.0),
    (RouteFitStatus.UNCONSTRAINED, "COMPOSABLE", "NOT_APPLICABLE", "FAVORABLE", "LIMITED", "SLOW", 1, 0, 0, -1.0),
    # a verdict that isn't in any tier dict -> the shared .get(default) path must fire identically for both
    (RouteFitStatus.FITS, "WEIRD_UNSEEN", "MYSTERY", "ODD", "STRANGE", "ALIEN", 0, 0, 0, None),
]


def consolidation_live() -> list:
    """For each verdict row, ``_route_score`` (nested) and ``_dag_score`` (flat) must return the IDENTICAL key --
    the only way that holds across the whole battery is if both delegate to the one shared ``_score_tuple``."""
    out = []
    for status, comp, sel, feas, eq, kin, gaps, exc, front, net in _BATTERY:
        rf = _FakeRouteFit(status, comp, sel, feas, eq, kin, gaps, exc)
        df = _FakeDagFit(status, comp, sel, feas, eq, kin, gaps, exc)
        rs = _route_score(rf, front, net)
        ds = _dag_score(df, front, net)
        # cross-check the extractor produced exactly what a direct _score_tuple call would
        direct = _score_tuple(status, comp, sel, feas, eq, kin, gaps, exc, front, net)
        out.append({"route_score": list(rs), "dag_score": list(ds),
                    "equal": rs == ds, "matches_core": rs == direct})
    return out


def _payload() -> dict:
    return {
        "ce1": ce1_front_index_is_set_relative(),
        "ce2": ce2_opposite_failclosed_polarity(),
        "consolidation": consolidation_live(),
    }


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True, default=str).encode()).hexdigest()


def validate() -> bool:
    """RDKit-free self-check: the two defer counterexamples hold on the real functions, and the intra-chemistry
    consolidation is live (both scorers route through the one shared core)."""
    ce1 = ce1_front_index_is_set_relative()
    assert ce1["full"] == [0, 1, 2], ce1
    assert ce1["without_p1"] == [0, 1], ce1
    assert ce1["p2_layer_full"] == 1 and ce1["p2_layer_without_p1"] == 0, ce1  # sibling departure moved P2's layer
    assert ce1["set_relative"] is True, ce1

    ce2 = ce2_opposite_failclosed_polarity()
    assert ce2["chem_fronts"] == [0, 1, 0], ce2
    assert ce2["unknown_layer"] == 0 and ce2["dominated_layer"] == 1, ce2  # UNKNOWN floats ABOVE a known dominated
    assert ce2["circuit_in_band"] is True and ce2["circuit_out_of_band"] is False, ce2  # circuit EJECTS on fail
    assert ce2["opposite_polarity"] is True, ce2

    cons = consolidation_live()
    assert cons, "battery must be non-empty (vacuous-green guard)"
    assert all(row["equal"] for row in cons), cons  # route-score == dag-score on every row -> one shared core
    assert all(row["matches_core"] for row in cons), cons  # ... and both equal a direct _score_tuple call
    return True


if __name__ == "__main__":  # pragma: no cover
    ok = validate()
    print(f"validate() -> {ok}")
    print(f"content_hash() -> {content_hash()}")
