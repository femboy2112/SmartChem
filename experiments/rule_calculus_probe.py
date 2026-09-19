"""Reproducible structural course-correction probe; --integration needs the full repo.

No bench recipe or default registry mutation. JSON is a receipt, not an authority
signature. The finite examples do not establish general chemical coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform

from smartchem.rule_calculus import BondGraph, BondRule, Edge, apply, verify, bounded_closure, independent
from smartchem.rule_semantics import (
    FiniteRelation, PotentialKey, PotentialBalance, QuantityInterval,
    fibre_collisions, capability_verdict,
)

BASE = "8810a45cd508c250919e9d7f7127133a74ae0c2d"
ROOT = Path(__file__).resolve().parents[1]


def run(integration=False):
    left = BondGraph(tuple("XXXX"), frozenset((Edge(0, 1), Edge(2, 3))))
    right = BondGraph(tuple("XXXX"), frozenset((Edge(0, 2), Edge(1, 3))))
    rule = BondRule("formal-switch-no-chemistry-authority", left, right)
    witness = apply(rule, left, (0, 1, 2, 3))
    full = bounded_closure(left, (rule,), depth=3)
    partial = bounded_closure(left, (rule,), depth=3, match_budget=0)
    host = left.tensor(left)
    a = apply(rule, host, (0, 1, 2, 3))
    b = apply(rule, host, (4, 5, 6, 7))
    context = frozenset(("wet", "dry"))
    first = FiniteRelation(frozenset(("input",)), context, frozenset((("input", "wet"),)))
    second = FiniteRelation(context, frozenset(("output",)), frozenset((("dry", "output"),)))
    pa, pi, pb = (PotentialKey(x, "fixed-phase", "fixed-environment", "declared-model") for x in ("A", "I", "B"))
    f, g = PotentialBalance(((pa, -1), (pi, 1))), PotentialBalance(((pi, -1), (pb, 1)))
    values = {pa: QuantityInterval("kJ/mol", 10, 11), pb: QuantityInterval("kJ/mol", 3, 4)}
    net = (f + g).evaluate(values, unit="kJ/mol")
    checks = {
        "independent_replay": verify(witness),
        "formal_inverse": apply(rule.reverse(), witness.target, witness.match).target == left,
        "complete_raw_state_count": len(full.states),
        "complete_status": full.status,
        "budget_refusal_status": partial.status,
        "independence_test": independent(a, b),
        "commuting_square": apply(rule, a.target, b.match).target == apply(rule, b.target, a.match).target,
        "separately_nonempty_contexts": bool(first.pairs and second.pairs),
        "composition_context_empty": not first.then(second).pairs,
        "local_observation_collision_count": len(fibre_collisions((("a", "same", "yes"), ("b", "same", "no")))),
        "individual_potential_steps_unknown": f.evaluate(values, unit="kJ/mol") is None and g.evaluate(values, unit="kJ/mol") is None,
        "net_after_symbolic_cancellation": [str(net.lower), str(net.upper)],
        "empty_capability_evidence": capability_verdict({}),
        "scalar_duration_interchange_counterexample": [max(10 + 0, 0 + 10), max(10, 0) + max(0, 10)],
    }
    expected = {"independent_replay": True, "formal_inverse": True, "complete_raw_state_count": 3,
                "complete_status": "COMPLETE_TO_DEPTH", "budget_refusal_status": "INCOMPLETE_MATCH_BUDGET",
                "independence_test": True, "commuting_square": True, "separately_nonempty_contexts": True,
                "composition_context_empty": True, "local_observation_collision_count": 1,
                "individual_potential_steps_unknown": True, "net_after_symbolic_cancellation": ["-8", "-6"],
                "empty_capability_evidence": "UNKNOWN", "scalar_duration_interchange_counterexample": [10, 20]}
    if checks != expected:
        raise RuntimeError(f"probe verdict changed: {checks}")
    integration_result = {"status": "NOT_RUN", "reason": "request --integration in a complete checkout"}
    if integration:
        from smartchem.rule_calculus_bridge import AuditedCappedScissionProvider
        from smartchem.experiment.step import ExperimentStep
        from smartchem.smiles import parse_smiles
        rows = []
        for smi in ("CC(=O)OC", "CCOCC", "CCN"):
            audits, complete = AuditedCappedScissionProvider().enumerate_audited(
                parse_smiles(smi), (parse_smiles("O"),), budget=50000
            )
            if not complete or not audits:
                raise RuntimeError("integration example did not exhaust its declared space")
            for audit in audits:
                if audit.open().close() != ExperimentStep.from_transform(audit.transform).open().close():
                    raise RuntimeError("open-diagram endpoint projection changed")
            rows.append({"target_smiles": smi, "audited_transforms": len(audits),
                         "recognized_classes": sorted({a.recognized_class for a in audits if a.recognized_class})})
        integration_result = {"status": "OBSERVED", "cases": rows}
    source_hashes = {}
    for name in ("smartchem/rule_calculus.py", "smartchem/rule_semantics.py", "smartchem/rule_calculus_bridge.py",
                 "tests/test_rule_calculus.py", "tests/test_rule_semantics.py", "tests/test_rule_calculus_bridge.py",
                 "experiments/rule_calculus_probe.py", "experiments/rule_calculus_mutations.py"):
        source_hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    return {"schema": "smartchem.rule-calculus-probe/v1", "audited_base": BASE,
            "python": platform.python_version(), "checks": checks, "integration": integration_result,
            "source_sha256": source_hashes,
            "scope": "formal fixed-vertex graphs and declared finite models; no physical validation or production-suite claim"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.integration), indent=2, sort_keys=True))
