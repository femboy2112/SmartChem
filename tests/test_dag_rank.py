"""ROUND-15 item 2 (DAG-RANK-01): convergent DAGs are ranked best-first, closing the "DAG mode ranks nothing" gap.

DAG-BENCH-01 made a convergent DAG a first-class bench citizen (a combined section-11 fit per DAG) but left the
dossiers in raw search-discovery order -- ``service.py`` even said so in a comment ("DAG mode ranks nothing
LINEARLY").  A chemist handed several admissible convergent routes to the same target got NO signal on which is best,
the exact asymmetry the paracetamol litmus cares about.  ``rank_dags``/``_dag_score`` are the DAG analogue of
``rank_routes``/``_route_score``: FITS+COMPOSABLE convergent routes float above UNKNOWN-gap ones above
EXCLUDED/DEGENERATE ones, on exactly what the combined ``DAGBenchFit`` carries (status -> composability -> gap ->
exclusion counts).  The three PER-REACTION thermochemical tiebreakers a linear route gets are a NAMED next-step (a DAG
does not aggregate them yet), so this is a sound COARSE ranking, never a claim of thermochemical discrimination.
"""
from types import SimpleNamespace

from tests.test_process_service import (
    _convergent_40min_dag, requirements, run_compilation, build_recompile_request,
)

from smartchem.contracts import EvidenceStatus
from smartchem.conditions import ConditionEnvelope, Interval
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.drafter import ConstraintBox, RouteFitStatus, DAGBenchFit, _dag_score, rank_dags
from smartchem.experiment.step import ExperimentStep
from smartchem.process_constraints import ProcessBounds
from smartchem.service import TransformGrammar
from smartchem.smiles import parse_smiles

_STATUS_RANK = {"FITS": 0, "UNCONSTRAINED": 0, "UNKNOWN": 1, "EXCLUDED": 2}


def _fit(status, verdict, gaps=(), exclusions=()):
    """A DAGBenchFit with a stubbed composability verdict, to exercise _dag_score's ordering in isolation."""
    return DAGBenchFit(status, exclusions, gaps, SimpleNamespace(verdict=verdict))


def _single_step_fits_dag():
    """A trivial single-step DAG (NO_TRANSITIONS composability): FITS under any generous-enough process budget."""
    acoh, etoh, ea, water = (parse_smiles(s) for s in ("CC(=O)O", "CCO", "CC(=O)OCC", "O"))
    env = ConditionEnvelope(
        temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
        provenance="synthetic process control; no experimental claim",
        process=requirements(elapsed_minutes=Interval(40, 40, "min")),
    )
    return SynthesisDAG.of(ExperimentStep.assembling(ea, (acoh, etoh), (ea, water), envelope=env))


def test_dag_score_orders_fits_composable_first_and_excluded_degenerate_last():
    """The full ordering matrix -- the DAG analogue of _route_score's structural tiers."""
    fits_comp = _fit(RouteFitStatus.FITS, "COMPOSABLE")
    unconstrained = _fit(RouteFitStatus.UNCONSTRAINED, "COMPOSABLE")
    fits_uncomposable = _fit(RouteFitStatus.FITS, "UNKNOWN")
    unknown = _fit(RouteFitStatus.UNKNOWN, "UNKNOWN", gaps=("g",))
    excluded = _fit(RouteFitStatus.EXCLUDED, "DEGENERATE", exclusions=("e",))
    assert _dag_score(fits_comp) == _dag_score(unconstrained)      # UNCONSTRAINED shares the top status tier with FITS
    assert _dag_score(fits_comp) < _dag_score(fits_uncomposable)   # composability breaks a status tie
    assert _dag_score(fits_uncomposable) < _dag_score(unknown)     # an UNKNOWN-fit sinks below a FITS
    assert _dag_score(unknown) < _dag_score(excluded)              # EXCLUDED is worst


def test_dag_score_breaks_ties_on_fewer_gaps_then_fewer_exclusions():
    one_gap = _fit(RouteFitStatus.UNKNOWN, "UNKNOWN", gaps=("a",))
    two_gaps = _fit(RouteFitStatus.UNKNOWN, "UNKNOWN", gaps=("a", "b"))
    assert _dag_score(one_gap) < _dag_score(two_gaps)             # fewer unassessed dimensions ranks better


def test_rank_dags_floats_a_fits_dag_above_an_excluded_one_under_one_bench():
    box70 = ConstraintBox(process=ProcessBounds(max_total_minutes=70.0))
    fits_dag = _single_step_fits_dag()                            # serial 40 <= 70 -> FITS
    excluded_dag = _convergent_40min_dag()                       # critical-path floor 80 > 70 -> EXCLUDED
    ranked = rank_dags([excluded_dag, fits_dag], box70)          # given worst-first, must re-order best-first
    assert ranked[0] is fits_dag and ranked[1] is excluded_dag


def test_rank_dags_is_stable_and_returns_a_tuple_of_dags():
    box = ConstraintBox(process=ProcessBounds(max_total_minutes=90.0))
    d1, d2 = _convergent_40min_dag(), _convergent_40min_dag()    # identical fits -> discovery order preserved (stable)
    ranked = rank_dags([d1, d2], box)
    assert ranked == (d1, d2)
    assert len(rank_dags([d1, d2])) == 2                         # box=None (unconstrained) path also returns all dags


def test_the_service_returns_dag_dossiers_ranked_best_first_non_vacuously():
    """The wired path, asserted NON-VACUOUSLY (evil-morty fold, DAG-RANK-01 Finding 1).

    The earlier assertion was vacuous twice: the paracetamol fixture returns a SINGLETON dossier (``ranks==sorted`` is
    trivially true -- a reversed sort would pass), and every reachable service DAG set carries a CONSTANT ``fit_status``,
    so a status-only check never touches the reorder ``rank_dags`` actually performs (which falls to the secondary
    gap-count key).  This asserts the REAL reorder: ethyl acetate through the convergent grammar yields several UNKNOWN
    dossiers whose GAP COUNTS genuinely vary, and the service must return them with the ``(status, gap-count)`` key
    non-decreasing -- a dropped, reversed, or wrong-key sort now fails."""
    resp = run_compilation(build_recompile_request(
        "smiles:CCOC(=O)C", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=ProcessBounds(max_total_minutes=600.0), max_depth=3))
    dossiers = resp.ranked_dag_dossiers
    assert len(dossiers) >= 2                                   # a real multi-route ranking subject
    keys = [(_STATUS_RANK[d.fit_status], len(d.gaps)) for d in dossiers]
    assert keys == sorted(keys)                                 # best-first: status, then fewer gaps
    assert len({k[1] for k in keys}) >= 2                       # NON-VACUOUS: the gap counts genuinely vary
