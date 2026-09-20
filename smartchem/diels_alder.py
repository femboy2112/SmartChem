"""Diels-Alder [4+2] retro-disconnection family on the rule_calculus kernel -- structural, opt-in, Problem A only.

This module compiles ONE new benign reaction family (all-carbon Diels-Alder) onto the fixed-vertex
:mod:`smartchem.rule_calculus` kernel.  It enumerates GUARDED retro-DA disconnections of a target bond graph and
derives the class witness FROM THE MATCH (not a self-declared name).  It asserts structural type-validity only: a
witness means "this is a structurally valid [4+2] retro-Diels-Alder disconnection", NEVER that the forward reaction is
feasible, selective, or endo/exo-resolved (Problem B stays with :mod:`smartchem.experiment.feasibility`).

Design + boundaries: ``docs/research/RULE_CALCULUS_DIELS_ALDER_FAMILY_v0.1.md``.  This layer touches no default
provider registry, no production gate, and no existing recognizer.  Everything here fails CLOSED: a match that does not
pass every guard is DROPPED (honest coverage loss), never coerced into a witness.
"""
from __future__ import annotations

from dataclasses import dataclass

from .rule_calculus import BondGraph, BondRule, Edge, RewriteWitness, RuleError, enumerate_matches, verify

# Forward [4+2]: diene C0=C1-C2=C3  +  dienophile C4=C5  ->  cyclohexene ring C0-C1=C2-C3-C4-C5-C0.
# Per-atom bond-order sums are preserved (2,3,3,2,2,2) both sides -- a pericyclic reaction conserves valence, so it
# lives natively in the degree-locked fixed-vertex fragment (proven in the feasibility spike).
_C6 = ("C",) * 6
_FORWARD = BondRule(
    "diels-alder-[4+2]-carbocyclic-v1",
    BondGraph(_C6, frozenset({Edge(0, 1, 2), Edge(1, 2, 1), Edge(2, 3, 2), Edge(4, 5, 2)})),
    BondGraph(_C6, frozenset({Edge(0, 1, 1), Edge(1, 2, 2), Edge(2, 3, 1),
                              Edge(3, 4, 1), Edge(4, 5, 1), Edge(0, 5, 1)})),
)
#: The disconnection direction R -> L: a cyclohexene adduct -> diene + dienophile.
RETRO_DA: BondRule = _FORWARD.reverse()
#: The class label the witness carries.  It is EMITTED only when the match's own net bond change matches this family's
#: signature AND the independent verifier agrees -- it is never asserted from the rule id alone (see :func:`class_witness`).
DA_CLASS = "diels-alder-[4+2]-carbocyclic"

# The diene carbons {0,1,2,3} and dienophile carbons {4,5} in the rule's own vertex numbering.
_DIENE = frozenset({0, 1, 2, 3})
_DIENOPHILE = frozenset({4, 5})


@dataclass(frozen=True)
class DisconnectionAudit:
    """A guard-passed retro-DA disconnection: the kernel witness plus the derived class."""
    witness: RewriteWitness
    reaction_class: str
    diene_vertices: tuple[int, ...]
    dienophile_vertices: tuple[int, ...]


def _induced_edges(graph: BondGraph, vertices) -> frozenset[Edge]:
    """Edges of ``graph`` with BOTH endpoints in ``vertices`` -- the induced subgraph (the locality lock)."""
    vs = set(vertices)
    return frozenset(e for e in graph.edges if e.i in vs and e.j in vs)


def _component_of(graph: BondGraph, seeds) -> frozenset[int]:
    """Connected component(s) of ``graph`` reachable from ``seeds`` (undirected)."""
    adjacent: dict[int, set[int]] = {i: set() for i in range(len(graph.labels))}
    for e in graph.edges:
        adjacent[e.i].add(e.j)
        adjacent[e.j].add(e.i)
    seen: set[int] = set()
    stack = list(seeds)
    while stack:
        i = stack.pop()
        if i not in seen:
            seen.add(i)
            stack.extend(adjacent[i] - seen)
    return frozenset(seen)


def _match_signature(witness: RewriteWitness) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The net bond change of THIS match, read off the witness (not the rule id): (deleted orders, added orders)."""
    rule = witness.rule
    deleted = tuple(sorted(e.order for e in rule.left.edges - rule.right.edges))
    added = tuple(sorted(e.order for e in rule.right.edges - rule.left.edges))
    return deleted, added


# The [4+2] retro signature computed from the family rule itself, so the check tracks the rule, not a hand-typed constant.
_RETRO_SIGNATURE = _match_signature(RewriteWitness(RETRO_DA, RETRO_DA.left, tuple(range(6)), RETRO_DA.right))


def class_witness(witness: RewriteWitness) -> str | None:
    """The reaction CLASS derived from the actual match, or ``None`` (fail-closed) if it is not a [4+2] retro-DA.

    The label is not asserted from the rule id: it is emitted only when the match's OWN net bond-order change equals
    this family's signature.  A mismatch -- a mutated rule, a different net change -- yields ``None``.
    """
    if not verify(witness):
        return None
    if _match_signature(witness) != _RETRO_SIGNATURE:
        return None
    return DA_CLASS


def independently_reconstructs(target: BondGraph, retro_result: BondGraph, match: tuple[int, ...]) -> bool:
    """Independent verifier (separate representation from the enumerator's ``apply``): does re-forming the two cleaved
    sigma bonds and restoring the pi shift on ``retro_result`` reproduce ``target`` EXACTLY, by adjacency multiset?

    This never calls :func:`apply`.  It rebuilds the forward bond delta from the rule geometry and the match, applies
    it to ``retro_result`` as a pair->order table, and compares to ``target``.  A forgery that fools the enumerator
    but not this recomputation is rejected.
    """
    try:
        if target.labels != retro_result.labels:
            return False
        # Forward delta (synthesis L->R) mapped through the match, computed from the rule geometry directly.
        forward = _FORWARD
        deleted = {tuple(sorted((match[e.i], match[e.j]))): e.order for e in forward.left.edges - forward.right.edges}
        added = {tuple(sorted((match[e.i], match[e.j]))): e.order for e in forward.right.edges - forward.left.edges}
        table = {e.pair: e.order for e in retro_result.edges}
        for pair, order in deleted.items():        # bonds the forward reaction consumes must be present to remove
            if table.get(pair) != order:
                return False
            del table[pair]
        for pair, order in added.items():          # bonds the forward reaction forms must not already survive
            if pair in table:
                return False
            table[pair] = order
        return table == {e.pair: e.order for e in target.edges}
    except (AttributeError, TypeError, ValueError, KeyError, IndexError):
        return False


def retro_da_disconnections(target: BondGraph, *, budget: int = 100000) -> tuple[tuple[DisconnectionAudit, ...], bool]:
    """Every GUARDED retro-Diels-Alder disconnection of ``target``, plus an honest completeness flag.

    Guards (each failure DROPS the match -- coverage loss, never a coerced witness), per the design doc s3:
      2. induced-subgraph exactness on the six matched carbons (locality lock: no extra bond forges a fake adduct);
      3. aromatic / polyene exclusion is automatic (the pattern needs exactly one ring C=C among the six);
      5. the retro must GLOBALLY disconnect the target into a diene component and a disjoint dienophile component;
      + the class witness (match signature) and the independent verifier must both agree.
    """
    if type(target) is not BondGraph:
        raise RuleError("retro_da_disconnections expects a BondGraph target")
    receipt = enumerate_matches(RETRO_DA, target, budget=budget)
    audits: list[DisconnectionAudit] = []
    seen_products: set[str] = set()  # collapse symmetric matches that yield the SAME product presentation
    for w in receipt.witnesses:
        m = w.match
        # Guard 2: the six matched carbons induce EXACTLY the ring pattern (no extra bond among them).
        if _induced_edges(target, m) != frozenset(Edge(m[e.i], m[e.j], e.order) for e in RETRO_DA.left.edges):
            continue
        # Class witness derived from the match + kernel verify.
        cls = class_witness(w)
        if cls is None:
            continue
        # Independent verifier: reconstruction reproduces the target exactly.
        if not independently_reconstructs(target, w.target, m):
            continue
        # Guard 5: global two-fragment split -- diene carbons and dienophile carbons land in DISJOINT components.
        diene_seeds = {m[i] for i in _DIENE}
        dienophile_seeds = {m[i] for i in _DIENOPHILE}
        diene_comp = _component_of(w.target, diene_seeds)
        dienophile_comp = _component_of(w.target, dienophile_seeds)
        if diene_comp & dienophile_comp:
            continue  # still connected (fused/bridged through external atoms) -> deferred, dropped
        if not (diene_seeds <= diene_comp and dienophile_seeds <= dienophile_comp):
            continue
        digest = w.target.digest
        if digest in seen_products:
            continue
        seen_products.add(digest)
        audits.append(DisconnectionAudit(
            witness=w, reaction_class=cls,
            diene_vertices=tuple(sorted(diene_seeds)),
            dienophile_vertices=tuple(sorted(dienophile_seeds)),
        ))
    return tuple(audits), receipt.complete
