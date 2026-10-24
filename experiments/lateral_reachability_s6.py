"""LATERAL-REACHABILITY-S6 -- ONE lateral family reachable via an opt-in state-aware search, now CENTRE-FREE (§6).

The moonshot, scoped honestly.  A [3,3] sigmatropic / electrocyclic rearrangement is RANK-FLAT (an isomerization,
same atom count), so it cannot ride the strict-descent ``search_routes`` recursion (W1).  :mod:`smartchem.lateral_search`
is its SOUND home: a bounded breadth-first closure over isomer states that terminates on its OWN visited-set + depth
+ state budgets (NOT strict rank descent), entirely outside the route search.  :func:`lateral_route_to` already
reconstructs an opt-in, state-aware, bounded route to a goal isomer -- this is the "make ONE lateral family reachable
via opt-in state-aware search" deliverable, demonstrated end-to-end for three families (Cope, Claisen, 6-pi
electrocyclic).

The #132 PAYOFF this round unlocks: the reaction-type oracle now vouches a lateral step by its re-derivation ALONE
(no reaction_center read), so a HAND-ASSEMBLED, CENTRE-LESS lateral route is recognized step-by-step -- previously a
centre-less step was fail-closed demoted by the retired Layer-C gate.  This corpus proves both the centre-carrying
route (via ``from_transform``) and the centre-less re-assembly are vouched (empty reaction-type blockers).

NO HARD BLOCKING THEOREM (recorded, not acted on).  An independent recon established that the stale claim "fusing a
rank-flat provider into search_routes breaks termination" is an OVER-claim: ``search_routes`` terminates on
``max_depth`` (not W1), and since #124 an ancestor precursor not in stock is refused (blocking A<-B<-A phantom
self-supply, with "a future rank-flat provider" named as the intended customer).  So a bounded lateral provider CAN
ride the route lane (a working adapter was prototyped).  The real cost is a FACTORIAL simple-path blow-up on a
rank-flat isomer graph (no global visited-set in search_routes), which a lexicographic (rank, lateral-budget)
well-founded measure would cap.  That FUSION is a separately-gated change to the shared search path (it alters a
default-adjacent code path and wants its own soundness + cost regression gate), so it is the NEXT falsifiable step,
NOT done here; this module uses the already-sound separate lateral search.

Run: ``.venv/bin/python -m experiments.lateral_reachability_s6``
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem.smiles import parse_smiles
from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.step import ExperimentStep
from smartchem.lateral_search import lateral_route_to, lateral_closure
from smartchem.lateral_rewrite import CLAISEN, ELECTRO_6PI, COPE, lateral_rewrites
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type, route_reaction_type_blockers

_ENV = ConditionEnvelope.unknown()


def _cope_goal():
    prods = lateral_rewrites(COPE, parse_smiles("C=CC(C)CC=C"))
    return prods[0] if prods else None


#: (name, family, seed, goal) -- the goal is reached from the seed by a bounded lateral search (retro direction:
#: the closure fires on the carbonyl / ring form, so the seed is the pent-4-enal / 1,3-cyclohexadiene / 1,5-diene).
def _cases():
    return (
        ("Claisen [3,3]", CLAISEN, parse_smiles("O=CCCC=C"), parse_smiles("C=COCC=C")),
        ("6-pi electrocyclic", ELECTRO_6PI, parse_smiles("C1C=CC=CC1"), parse_smiles("C=CC=CC=C")),
        ("Cope [3,3]", COPE, parse_smiles("C=CC(C)CC=C"), _cope_goal()),
    )


def _forward_steps(chain):
    """Rebuild each edge as the FORWARD synthesis step ``from_transform`` orients it (reactant = edge.products[0],
    product = edge.reactant), both centre-carrying and CENTRE-LESS."""
    carried, centreless = [], []
    for e in chain:
        carried.append(ExperimentStep.from_transform(e, envelope=None))
        react, prod = e.products[0], e.reactant   # the forward (synthesis) direction the recognizer expects
        centreless.append(ExperimentStep.assembling(prod, (react,), (prod,), reagents=(), envelope=_ENV,
                                                     reaction_center=None))
    return carried, centreless


def measure() -> dict:
    rows = []
    for name, fam, seed, goal in _cases():
        if goal is None:
            rows.append((name, "no-goal", None, None, None))
            continue
        chain = lateral_route_to(seed, goal, (fam,), depth=4)
        if not chain:
            rc = lateral_closure(seed, (fam,), depth=4)
            rows.append((name, f"unreached ({rc.status}, {len(rc.isomers)} isomers)", None, None, None))
            continue
        carried, centreless = _forward_steps(chain)
        carried_route = SimpleNamespace(steps=tuple(carried))
        centreless_route = SimpleNamespace(steps=tuple(centreless))
        rows.append((
            name, f"route len {len(chain)}",
            [recognize_reaction_type(s) for s in centreless],
            route_reaction_type_blockers(carried_route),
            route_reaction_type_blockers(centreless_route),
        ))
    return {"rows": rows}


def validate() -> bool:
    """Each family's lateral route is reached AND vouched step-by-step BOTH with a carried centre and CENTRE-LESS
    (the #132 payoff): empty reaction-type blockers for both routes, and every centre-less step recognized."""
    for name, status, classes, carried_blk, centreless_blk in measure()["rows"]:
        if classes is None or carried_blk != () or centreless_blk != ():
            return False
        if any(c is None for c in classes):
            return False
    return True


def main() -> None:
    print("LATERAL-REACHABILITY-S6 -- opt-in bounded lateral search, oracle-vouched, centre-free (#132 payoff)\n")
    for name, status, classes, carried_blk, centreless_blk in measure()["rows"]:
        ok = classes is not None and carried_blk == () and centreless_blk == () and all(classes)
        print(f"  {'OK ' if ok else '!! '}{name:22s} {status}")
        if classes is not None:
            print(f"        centre-less step classes : {classes}")
            print(f"        carried-centre blockers  : {carried_blk}")
            print(f"        centre-less blockers     : {centreless_blk}")
    print(f"\n  VERDICT: {'PASS' if validate() else 'FAIL'}")


if __name__ == "__main__":
    main()
