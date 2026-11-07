"""Permanent cross-mode control for #109 -- no public consumer vouches a conserved fiction.

The full claim, finding, and the LATENT HOLE record live in experiments/latent_fiction_109.py
(its admission half -- the convergent-DAG path admitting a FITS fiction with the oracle never
consulted -- was closed by DAG-ADMIT-02, 31edffc; the THIN_ADVISORY residue is recorded there). This pins that a conserved fiction is never
REACTION_VOUCHED (linear) nor FITS/admissible (linear OR convergent-DAG), while a genuine
reaction IS vouched -- so the demotion assertion is non-vacuous.

BITES on regression: if a future change (e.g. a generated DAG step gaining declared conditions so
that dag_bench_fit reaches FITS, combined with a regression of the DAG-ADMIT-02 recognition gate)
lets a fiction reach admissible_dag_digests, or a linear fiction reach REACTION_VOUCHED, validate()
returns False here.
"""
from experiments.latent_fiction_109 import validate


def test_no_consumer_vouches_a_conserved_fiction():
    ok, summary = validate()
    assert ok, f"#109 fiction control failed: {summary}"
    assert summary["fiction_never_vouched_or_admitted"] is True
    # non-vacuous: the pipeline genuinely vouches a REAL reaction in linear mode, so the
    # "fiction is never vouched" assertions are discriminating, not trivially true on an empty set.
    assert summary["real_reaction_vouched_in_linear"] >= 1
