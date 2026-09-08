"""Move 6 -- conditions distribute through a route's CAUSAL order, not an incidental linearization.

THE_ORBITAL.md §IX withdrew the distributive law ``λ : T∘W ⇒ W∘T`` (an environment comonad over an effect monad),
never constructed or checked.  Re-aimed at the live route pipeline, its content is a coherence LAW:

    LINEAR-EXTENSION INVARIANCE -- the whole-DAG composability / duration-survival verdict, and the machine-readable
    holds it discloses, are INVARIANT under every linear extension of the DAG's causal partial order.

Before this round the verdict was NOT invariant: the duration gate charged an intermediate the serial hold of the
sibling steps that fell "between" its producer and consumer in ONE arbitrary ``_topological_order`` (Kahn, step-index
tie-break), and R23's gate lets that hold flip the verdict to DEGENERATE.  So permuting the listing order of two
CAUSALLY INDEPENDENT branches -- a chemically inert choice -- flipped DEGENERATE <-> UNKNOWN.  These tests pin the
fix: the gate now charges only the FORCED-BETWEEN (unavoidable-in-every-schedule) hold, so the verdict is a function
of the causal partial order alone.

The law proven here is INVARIANCE, not schedulability: a route dead in every schedule may still read UNKNOWN (the
makespan question is out of scope; see ``_apply_duration_gate``'s docstring).  These tests never assert feasibility.
"""
from __future__ import annotations

from itertools import permutations

import pytest

from smartchem.contracts import EvidenceStatus
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.process_constraints import Agitation, ProcessRequirements
from smartchem.experiment.dag import (
    SynthesisDAG, dag_composability, _hold_segments, _serial_hold_minutes, _forward_reach,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.kinetics import DEFAULT_KINETICS, KineticRef
from smartchem.smiles import parse_smiles


def _reqs(minutes: float) -> ProcessRequirements:
    return ProcessRequirements(
        elapsed_minutes=Interval(minutes, minutes, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True,
        provenance="synthetic process control; no experimental claim",
    )


def _step(target, reactants, products, minutes: float = 40.0):
    env = ConditionEnvelope(
        temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
        provenance="synthetic process control; no experimental claim", process=_reqs(minutes),
    )
    return ExperimentStep.assembling(target, reactants, products, envelope=env)


def _rate(reactant_smiles: str, products: tuple[tuple[str, int], ...]):
    """A transparently SYNTHETIC fast first-order decomposition (k ~ 1e6 /s -> destroyed over any real hold) --
    a TEST lever for the duration wire-in, never a measurement."""
    return DEFAULT_KINETICS.with_records(KineticRef(
        reactant_smiles=((reactant_smiles, 1),), product_smiles=products,
        name=f"{reactant_smiles} decomposition (SYNTHETIC TEST rate)", ea_kj_per_mol=0.0, log10_a=6.0,
        a_units="s^-1", temperature_range_k=(1.0, 1000.0),
        provenance="SYNTHETIC TEST rate; exercises the DAG duration wire-in only -- not a measurement",
    ))


# -- the DAG families (built as a set of steps; every listing permutation is the SAME causal DAG) ---------------

def _convergent_join_steps():
    """Two independent 40-min branches (acetic acid, ethanol) join at a third step.  Neither branch is causally
    forced through the other -- forced-between is EMPTY for both edges."""
    acoh, etoh, ea, water, ald, ethene, o2 = (parse_smiles(s) for s in
        ("CC(=O)O", "CCO", "CC(=O)OCC", "O", "CC=O", "C=C", "O=O"))
    return (
        _step(acoh, (ald, ald, o2), (acoh, acoh)),
        _step(etoh, (ethene, water), (etoh,)),
        _step(ea, (acoh, etoh), (ea, water)),
    )


def _forced_between_steps():
    """A genuine shortcut/diamond: formaldehyde (P) is consumed by BOTH step 1 and step 2, and step 1
    (formaldehyde -> methanol) is UNAVOIDABLY between the producer of P and its other consumer in every schedule
    -- forced-between(producer, join) = {the methanol step}."""
    glycolald, form, meoh, h2, egly = (parse_smiles(s) for s in ("OCC=O", "C=O", "CO", "[H][H]", "OCCO"))
    return (
        _step(form, (glycolald,), (form, form)),   # glycolaldehyde -> 2 formaldehyde   (C2H4O2 = 2 CH2O)
        _step(meoh, (form, h2), (meoh,)),           # formaldehyde + H2 -> methanol      (CH2O + H2 = CH4O)
        _step(egly, (form, meoh), (egly,)),         # formaldehyde + methanol -> ethylene glycol (no byproduct)
    )


def _verdict_and_holds(steps):
    dag = SynthesisDAG.of(*steps)
    comp = dag_composability(dag)
    # The step INDICES permute with the listing, so the (i, j) hold labels are NOT invariant by construction; the
    # invariant the law is about is the VERDICT plus the MULTISET of hold minutes (how long intermediates are held)
    # and the route survival -- never which arbitrary index a step landed on.
    minutes = tuple(sorted(m for m in _serial_hold_minutes(dag).values() if m > 0))
    return comp.verdict, minutes, comp.route_surviving_fraction


# -- the law: verdict + disclosure invariant under every listing permutation ------------------------------------

@pytest.mark.parametrize("family", ["convergent_join", "forced_between"])
def test_verdict_is_invariant_under_branch_listing_permutation(family):
    """THE Move-6 law: permuting the order independent branches are LISTED in (a chemically inert choice) never
    changes the whole-DAG verdict or the disclosed holds -- the verdict is a function of the causal partial order,
    not of the incidental Kahn linearization.  This test FAILS on the pre-Move-6 code (DEGENERATE vs UNKNOWN on the
    convergent join under an injected rate), so it is a real regression test, not a self-verifying mirror."""
    builder = {
        "convergent_join": _convergent_join_steps,
        "forced_between": _forced_between_steps,
    }[family]
    baseline = _verdict_and_holds(builder())
    for perm in permutations(range(len(builder()))):
        steps = builder()
        permuted = tuple(steps[i] for i in perm)
        assert _verdict_and_holds(permuted) == baseline, f"{family}: listing order {perm} changed the verdict/holds"


def test_convergent_join_does_not_flip_even_with_an_injected_rate():
    """The specific bug: a convergent join with a fast-decomposing branch used to flip DEGENERATE depending on
    listing order.  Now forced-between is EMPTY (neither independent branch is forced through the other), so the
    gate never fires -- UNKNOWN in EVERY listing, because a viable schedule (make the fast branch last) exists."""
    steps = _convergent_join_steps()
    rate = _rate("CC(=O)O", (("C", 1), ("O=C=O", 1)))  # fast acetic-acid decay
    for perm in permutations(range(len(steps))):
        dag = SynthesisDAG.of(*(steps[i] for i in perm))
        # forced-between empty for every edge -> no gate hold
        assert all(segs == () for segs in _hold_segments(dag, unavoidable=True).values())
        assert dag_composability(dag, kinetics=rate).verdict != "DEGENERATE"


def test_forced_between_hold_still_flips_degenerate_order_invariantly():
    """Non-vacuity (birdperson #2): the gate is NARROWED, not neutered.  A genuine UNAVOIDABLE hold -- formaldehyde
    forced through the methanol step in every schedule -- still flips DEGENERATE under the injected rate, and does
    so identically in every listing permutation.  A bare convergent join would wrongly show the gate 'dead'; this
    shortcut is where an unavoidable hold actually lives."""
    steps = _forced_between_steps()
    rate = _rate("C=O", (("[H][H]", 1), ("[C-]#[O+]", 1)))  # fast formaldehyde decay
    seen = set()
    for perm in permutations(range(len(steps))):
        dag = SynthesisDAG.of(*(steps[i] for i in perm))
        forced = _hold_segments(dag, unavoidable=True)
        assert any(segs for segs in forced.values()), "the forced-between hold must be non-empty (else vacuous)"
        seen.add(dag_composability(dag, kinetics=rate).verdict)
    assert seen == {"DEGENERATE"}


def test_possibly_between_discloses_both_branches_order_invariantly():
    """The disclosure (possibly-between) is order-independent AND non-vacuous: on the convergent join BOTH branches'
    intermediates could idle ~40 min in some valid schedule, so both edges are disclosed (the pre-Move-6 code
    reported only one, arbitrarily).  Disclosure never flips a verdict."""
    steps = _convergent_join_steps()
    for perm in permutations(range(len(steps))):
        dag = SynthesisDAG.of(*(steps[i] for i in perm))
        minutes = tuple(sorted(m for m in _serial_hold_minutes(dag).values() if m > 0))
        # BOTH producer->join branches disclose a 40-min schedule-relative hold, and the multiset is invariant
        # across every listing (the pre-Move-6 code reported only ONE, arbitrarily, under one Kahn order).
        assert minutes == (40.0, 40.0)


def test_forward_reach_is_the_causal_transitive_closure():
    """_forward_reach(i) = {k : i ->* k}, i included -- a small direct check the closure the law rests on is right."""
    # edges 0->1, 0->2, 1->2 (the forced-between shortcut shape)
    steps = _forced_between_steps()
    dag = SynthesisDAG.of(*steps)
    reach = _forward_reach(len(dag.steps), dag.edges)
    # step 0 (produces formaldehyde) reaches everything; the sink reaches only itself
    assert reach[0] == {0, 1, 2}
    assert reach[2] == {2}
