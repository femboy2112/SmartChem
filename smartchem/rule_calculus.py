"""Finite, atom-preserving bond-rule calculus; structural evidence, NOT chemistry authority.

This is a guarded simple-graph fragment of double-pushout rewriting: every
vertex survives and K contains exactly the shared edges. No claim is made that
the category of chemically valid graphs is adhesive. Explicit atom labels and
per-vertex bond-order sums are preserved. Labels are opaque; valence validity,
mechanism, kinetics, stereo, phase, safety and affordability are NOT inferred.

The independent verifier uses an adjacency-table interpreter, not apply().
Hashes identify raw presentations, not isomorphism classes or trusted evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable

SCHEMA = "smartchem.bond-rule/fixed-vertices-v1"


class RuleError(ValueError):
    """Malformed or inapplicable formal rewrite."""


def _integer(value: int, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise RuleError(f"expected an integer >= {minimum}")


def _hash(value: object) -> str:
    return sha256(json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True, order=True)
class Edge:
    i: int
    j: int
    order: int = 1

    def __post_init__(self) -> None:
        _integer(self.i)
        _integer(self.j)
        _integer(self.order, 1)
        if self.i == self.j:
            raise RuleError("self bonds are outside this fragment")
        if self.i > self.j:
            i, j = self.j, self.i
            object.__setattr__(self, "i", i)
            object.__setattr__(self, "j", j)

    @property
    def pair(self) -> tuple[int, int]:
        return self.i, self.j


@dataclass(frozen=True)
class BondGraph:
    """A possibly disconnected, finite graph with explicit positional labels."""
    labels: tuple[str, ...]
    edges: frozenset[Edge] = frozenset()

    def __post_init__(self) -> None:
        if type(self.labels) is not tuple or any(type(x) is not str or not x for x in self.labels):
            raise RuleError("labels must be a tuple of nonempty strings")
        if type(self.edges) is not frozenset or any(type(e) is not Edge for e in self.edges):
            raise RuleError("edges must be a frozenset of Edge values")
        if any(e.j >= len(self.labels) for e in self.edges):
            raise RuleError("bond endpoint outside vertex set")
        if len({e.pair for e in self.edges}) != len(self.edges):
            raise RuleError("one bond-order record per atom pair required")

    @property
    def degrees(self) -> tuple[int, ...]:
        out = [0] * len(self.labels)
        for e in self.edges:
            out[e.i] += e.order
            out[e.j] += e.order
        return tuple(out)

    @property
    def digest(self) -> str:
        return _hash((SCHEMA, self.labels, [(e.i, e.j, e.order) for e in sorted(self.edges)]))

    def relabel(self, old_to_new: tuple[int, ...]) -> BondGraph:
        """Transport a presentation by a declared vertex permutation."""
        _match_tuple(old_to_new, len(self.labels), len(self.labels))
        labels = [""] * len(self.labels)
        for old, new in enumerate(old_to_new):
            labels[new] = self.labels[old]
        return BondGraph(tuple(labels), _map_edges(self.edges, old_to_new))

    def tensor(self, other: BondGraph) -> BondGraph:
        offset = len(self.labels)
        return BondGraph(self.labels + other.labels, self.edges | frozenset(
            Edge(e.i + offset, e.j + offset, e.order) for e in other.edges
        ))


def _match_tuple(match: tuple[int, ...], size: int, host_size: int) -> None:
    if type(match) is not tuple or len(match) != size:
        raise RuleError("match must give one host index for each rule vertex")
    for i in match:
        _integer(i)
        if i >= host_size:
            raise RuleError("match outside host")
    if len(set(match)) != size:
        raise RuleError("matches must be injective")


def _map_edges(edges: Iterable[Edge], match: tuple[int, ...]) -> frozenset[Edge]:
    return frozenset(Edge(match[e.i], match[e.j], e.order) for e in edges)


@dataclass(frozen=True)
class BondRule:
    """L <- K -> R with the SAME labelled vertices on all three legs.

    rule_id is a provenance label, not a reaction-class certificate. The
    unchanged-edge interface is computed, never accepted on a caller's word.
    """
    rule_id: str
    left: BondGraph
    right: BondGraph

    def __post_init__(self) -> None:
        if type(self.rule_id) is not str or not self.rule_id:
            raise RuleError("a nonempty rule_id is required")
        if type(self.left) is not BondGraph or type(self.right) is not BondGraph:
            raise RuleError("both rule legs must be BondGraphs")
        if self.left.labels != self.right.labels:
            raise RuleError("this fragment preserves each labelled atom")
        if self.left.degrees != self.right.degrees:
            raise RuleError("per-atom bond-order sums must be preserved")

    @property
    def interface(self) -> BondGraph:
        return BondGraph(self.left.labels, self.left.edges & self.right.edges)

    @property
    def deleted(self) -> frozenset[Edge]:
        return self.left.edges - self.right.edges

    @property
    def added(self) -> frozenset[Edge]:
        return self.right.edges - self.left.edges

    @property
    def digest(self) -> str:
        return _hash((SCHEMA, self.rule_id, self.left.digest, self.right.digest))

    def reverse(self) -> BondRule:
        """Formal reversal only; no claim of physical reversibility."""
        return BondRule(self.rule_id, self.right, self.left)


@dataclass(frozen=True)
class RewriteWitness:
    rule: BondRule
    source: BondGraph
    match: tuple[int, ...]
    target: BondGraph

    @property
    def digest(self) -> str:
        return _hash((SCHEMA, self.rule.digest, self.source.digest, self.match, self.target.digest))


def apply(rule: BondRule, host: BondGraph, match: tuple[int, ...]) -> RewriteWitness:
    """Apply an injective match, refusing edge collisions instead of overwriting."""
    if type(rule) is not BondRule or type(host) is not BondGraph:
        raise RuleError("apply expects a BondRule and BondGraph")
    _match_tuple(match, len(rule.left.labels), len(host.labels))
    if any(host.labels[v] != rule.left.labels[i] for i, v in enumerate(match)):
        raise RuleError("match does not preserve labels")
    if not _map_edges(rule.left.edges, match) <= host.edges:
        raise RuleError("required left-hand bonds are absent or have the wrong order")
    remaining = host.edges - _map_edges(rule.deleted, match)
    new = _map_edges(rule.added, match)
    if {e.pair for e in remaining} & {e.pair for e in new}:
        raise RuleError("new bond collides with surviving context")
    target = BondGraph(host.labels, remaining | new)
    return RewriteWitness(rule, host, match, target)


def verify(witness: RewriteWitness) -> bool:
    """Independently replay into a pair->order table; no call to apply().

    The boundary is data, not malicious in-process Python. This is not a
    cryptographic attestation of who supplied the rule or a chemistry VOUCH.
    """
    try:
        if type(witness) is not RewriteWitness:
            return False
        r, g, h, m = witness.rule, witness.source, witness.target, witness.match
        if type(r) is not BondRule or type(g) is not BondGraph or type(h) is not BondGraph:
            return False
        _match_tuple(m, len(r.left.labels), len(g.labels))
        if g.labels != h.labels or r.left.labels != r.right.labels:
            return False
        if r.left.degrees != r.right.degrees or g.degrees != h.degrees:
            return False
        if any(g.labels[m[i]] != label for i, label in enumerate(r.left.labels)):
            return False
        table = {e.pair: e.order for e in g.edges}
        old = {tuple(sorted((m[e.i], m[e.j]))): e.order for e in r.left.edges}
        new = {tuple(sorted((m[e.i], m[e.j]))): e.order for e in r.right.edges}
        if any(table.get(pair) != order for pair, order in old.items()):
            return False
        for pair, order in old.items():
            if new.get(pair) != order:
                del table[pair]
        for pair, order in new.items():
            if old.get(pair) != order:
                if pair in table:
                    return False
                table[pair] = order
        return table == {e.pair: e.order for e in h.edges}
    except (AttributeError, TypeError, ValueError, KeyError, IndexError):
        return False


@dataclass(frozen=True)
class MatchReceipt:
    witnesses: tuple[RewriteWitness, ...]
    attempts: int
    budget: int
    complete: bool


def enumerate_matches(rule: BondRule, host: BondGraph, *, budget: int = 10000) -> MatchReceipt:
    """Budgeted iterative DFS. Work counts attempted vertex extensions, not hits.

    Complete means every injective label-preserving match was considered;
    canonical-isomorphism deduplication is deliberately NOT performed here.
    """
    _integer(budget)
    if type(rule) is not BondRule or type(host) is not BondGraph:
        raise RuleError("enumeration expects a BondRule and BondGraph")
    candidates = tuple(tuple(j for j, x in enumerate(host.labels) if x == label)
                       for label in rule.left.labels)
    if any(not row for row in candidates):
        return MatchReceipt((), 0, budget, True)
    if not candidates:
        return MatchReceipt((apply(rule, host, ()),), 0, budget, True)
    stack = [((), iter(candidates[0]))]
    out: list[RewriteWitness] = []
    work = 0
    while stack:
        prefix, choices = stack[-1]
        try:
            v = next(choices)
        except StopIteration:
            stack.pop()
            continue
        if work == budget:
            return MatchReceipt(tuple(out), work, budget, False)
        work += 1
        if v in prefix:
            continue
        extended = prefix + (v,)
        k = len(extended)
        if any(Edge(extended[e.i], extended[e.j], e.order) not in host.edges
               for e in rule.left.edges if e.j < k):
            continue
        if k == len(candidates):
            try:
                out.append(apply(rule, host, extended))
            except RuleError:
                pass  # complete match, but its newly formed edge collides with context
        else:
            stack.append((extended, iter(candidates[k])))
    return MatchReceipt(tuple(out), work, budget, True)


def independent(a: RewriteWitness, b: RewriteWitness) -> bool:
    """A sufficient read/write test for commuting applications of THIS fragment.

    Required old bonds and absent new bonds are reads; changed pairs are
    writes. No claim covers unrepresented global chemical application guards.
    """
    if not verify(a) or not verify(b) or a.source != b.source:
        return False

    def footprints(w):
        reads = {e.pair for e in _map_edges(w.rule.left.edges | w.rule.added, w.match)}
        writes = {e.pair for e in _map_edges(w.rule.deleted | w.rule.added, w.match)}
        return reads, writes

    ar, aw = footprints(a)
    br, bw = footprints(b)
    return not (aw & br or bw & ar)


@dataclass(frozen=True)
class ClosureReceipt:
    seed_digest: str
    grammar_digest: str
    depth: int
    states: tuple[BondGraph, ...]
    transitions: tuple[RewriteWitness, ...]
    attempts: int
    status: str
    match_budget: int
    state_budget: int

    @property
    def complete(self) -> bool:
        return self.status == "COMPLETE_TO_DEPTH"


def bounded_closure(seed: BondGraph, rules: tuple[BondRule, ...], *, depth: int,
                    match_budget: int = 100000, state_budget: int = 1000) -> ClosureReceipt:
    """Reachable RAW states within depth, not all paths or physical syntheses.

    BFS deduplication uses full graph values, not digest collision assumptions.
    State-preserving cycles are legal. Neither early exit nor one incomplete
    provider can be called complete. Rule bodies and ordered registry bind scope.
    """
    _integer(depth)
    _integer(match_budget)
    _integer(state_budget, 1)
    if type(seed) is not BondGraph or type(rules) is not tuple:
        raise RuleError("expected a graph and a tuple of rules")
    if any(type(r) is not BondRule for r in rules):
        raise RuleError("registry entries must be BondRules")
    if len({r.rule_id for r in rules}) != len(rules):
        raise RuleError("registry rule IDs must be unique")
    grammar_digest = _hash((SCHEMA, tuple(r.digest for r in rules)))
    states = [seed]
    distances = {seed: 0}
    transitions: list[RewriteWitness] = []
    work = 0

    def result(status):
        return ClosureReceipt(seed.digest, grammar_digest, depth, tuple(states),
                              tuple(transitions), work, status, match_budget, state_budget)

    cursor = 0
    while cursor < len(states):
        g = states[cursor]
        cursor += 1
        if distances[g] >= depth:
            continue
        for rule in rules:
            matches = enumerate_matches(rule, g, budget=match_budget - work)
            work += matches.attempts
            for w in matches.witnesses:
                if w.target not in distances:
                    if len(states) == state_budget:
                        return result("INCOMPLETE_STATE_BUDGET")
                    distances[w.target] = distances[g] + 1
                    states.append(w.target)
                transitions.append(w)
            if not matches.complete:
                return result("INCOMPLETE_MATCH_BUDGET")
    return result("COMPLETE_TO_DEPTH")
