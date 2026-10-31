"""Permanent cross-mode control for #109 -- no public consumer vouches a conserved fiction.

The full claim, finding, and the documented LATENT HOLE (the convergent-DAG path is oracle-blind
and a fiction is contained today only by the unrelated "undeclared-conditions => UNKNOWN" wall)
live in experiments/latent_fiction_109.py. This pins that a conserved fiction is never
REACTION_VOUCHED (linear) nor FITS/admissible (linear OR convergent-DAG), while a genuine
reaction IS vouched -- so the demotion assertion is non-vacuous.

BITES on regression: if a future change (e.g. a generated DAG step gaining declared conditions,
which would let dag_bench_fit reach FITS with the oracle never consulted) lets a fiction reach
admissible_dag_digests, or a linear fiction reach REACTION_VOUCHED, validate() returns False here.
"""
from experiments.latent_fiction_109 import validate


def test_no_consumer_vouches_a_conserved_fiction():
    ok, summary = validate()
    assert ok, f"#109 fiction control failed: {summary}"
    assert summary["fiction_never_vouched_or_admitted"] is True
    # non-vacuous: the pipeline genuinely vouches a REAL reaction in linear mode, so the
    # "fiction is never vouched" assertions are discriminating, not trivially true on an empty set.
    assert summary["real_reaction_vouched_in_linear"] >= 1
