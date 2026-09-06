"""ROUND-15 item 1 (DAG-HOLD-01): the serial-schedule HOLD disclosure for convergent DAGs.

DAG-BENCH-01 documented -- but did not surface -- a boundary: a convergent DAG's SERIAL schedule holds an early
branch's intermediate through its sibling branches before the join consumes it, and E1 composability is time-blind
(it judges only the adjacent handoff), so that hold's stability is UNVERIFIED.  This makes the boundary LOUD: each
edge whose intermediate waits through intervening sibling steps carries a sourced ``serial-hold-minutes`` DISCLOSURE
(a sound LOWER bound over the DAG's own topological schedule -- the sum of the intervening steps' known-minimum
elapsed, unknown floors counted as 0).  It mirrors the ``_pressure_note`` precedent exactly: an observation-only
FINDING that NEVER degrades the composability verdict (else every convergent DAG with a sibling branch would read
UNKNOWN), which is the load-bearing soundness property pinned below.
"""
from tests.test_process_service import _convergent_40min_dag, requirements

from smartchem.experiment.composability import TransitionStatus, _serial_hold_note
from smartchem.experiment.dag import _serial_hold_minutes, dag_composability


def test_the_serial_hold_is_disclosed_on_the_edge_whose_intermediate_waits_through_a_sibling():
    # two 40-min branches join at a third step; the serial schedule holds the first branch's intermediate through the
    # second branch (40 min) before the join consumes it.
    comp = dag_composability(_convergent_40min_dag())
    notes = comp.serial_hold_notes
    assert len(notes) == 1                                       # exactly one edge carries a real serial hold
    assert ">=40 min" in notes[0]                               # the intervening branch's 40-min floor
    assert "UNVERIFIED" in notes[0] and "time-blind" in notes[0]


def test_the_hold_floor_matches_the_process_gate_known_minimum():
    # the hold is the SUM of intervening steps' known-minimum elapsed (here each step declares elapsed_minutes=[40,40],
    # so the .lo floor is 40) -- the same _known_min floor discipline the process gate uses, a sound LOWER bound.
    holds = _serial_hold_minutes(_convergent_40min_dag())
    assert sorted(holds.values()) == [0.0, 40.0]               # one held edge (40), one adjacent edge (0)


def test_the_disclosure_never_degrades_the_composability_verdict():
    # THE load-bearing soundness property: a COMPOSABLE transition that ALSO carries a hold stays COMPOSABLE -- the
    # hold rides in FINDINGS, never in the verdict-affecting gaps/degenerate_reasons, so it can never flip a pass.
    comp = dag_composability(_convergent_40min_dag())
    held = [t for t in comp.transitions if any(f.label == "serial-hold-minutes" for f in t.findings)]
    assert held and held[0].status is TransitionStatus.COMPOSABLE   # the acetic-acid edge: COMPOSABLE *and* held
    note = comp.serial_hold_notes[0]
    assert note not in comp.gaps                                    # not a gap => cannot turn a FITS into an UNKNOWN
    assert note not in comp.degenerate_reasons                      # not a degeneracy => cannot exclude


def test_the_note_gate_is_silent_below_or_at_zero_minutes_the_linear_and_adjacent_path():
    # the linear route composability path (and any adjacent DAG handoff) passes hold_minutes=None/0 and gets NO note;
    # only a positive hold is disclosed.  This is what keeps a linear route entirely unaffected by DAG-HOLD-01.
    assert _serial_hold_note(None) is None
    assert _serial_hold_note(0) is None and _serial_hold_note(0.0) is None
    q = _serial_hold_note(40.0)
    assert q is not None and q.label == "serial-hold-minutes" and q.value == ">=40" and q.unit == "min"


def test_the_hold_note_surfaces_in_the_human_explain_output():
    text = dag_composability(_convergent_40min_dag()).explain()
    assert "NOTE" in text and "held >=40 min" in text              # a chemist reading the dossier sees the hold


def test_the_serial_hold_is_surfaced_concretely_in_the_dag_bench_note():
    """evil-morty fold (DAG-HOLD-01 Finding 1): the disclosure must reach a REAL product surface, not a dead
    ``explain()`` no product path renders.  ``_dag_bench_note`` is the one human tally DAG mode actually emits, and it
    must carry the CONCRETE hold (a magnitude), not merely the generic boundary sentence it shipped before."""
    from smartchem.service import _dag_bench_note
    from smartchem.experiment.drafter import ConstraintBox
    from smartchem.process_constraints import ProcessBounds
    note = _dag_bench_note([_convergent_40min_dag()], ConstraintBox(process=ProcessBounds(max_total_minutes=600.0)))
    assert note is not None
    assert "DISCLOSED (DAG-HOLD-01)" in note                       # the concrete disclosure fired ...
    assert "up to 40 min" in note                                  # ... with the actual hold magnitude ...
    assert "schedule-relative" in note                             # ... and honest about schedule-dependence


def test_a_no_hold_dag_set_keeps_the_generic_boundary_sentence_unchanged():
    """The concrete clause fires ONLY when there is a real hold; a single-step (or timing-free) DAG set yields the
    byte-identical generic boundary sentence, so DAG-HOLD-01 ripples nothing for the no-hold case (why the paracetamol
    golden did not move)."""
    from smartchem.service import _dag_bench_note
    from smartchem.experiment.dag import SynthesisDAG
    from smartchem.experiment.step import ExperimentStep
    from smartchem.experiment.drafter import ConstraintBox
    from smartchem.conditions import ConditionEnvelope, Interval
    from smartchem.contracts import EvidenceStatus
    from smartchem.process_constraints import ProcessBounds
    from smartchem.smiles import parse_smiles
    acoh, etoh, ea, water = (parse_smiles(s) for s in ("CC(=O)O", "CCO", "CC(=O)OCC", "O"))
    env = ConditionEnvelope(temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
                            provenance="synthetic process control; no experimental claim",
                            process=requirements(elapsed_minutes=Interval(40, 40, "min")))
    single = SynthesisDAG.of(ExperimentStep.assembling(ea, (acoh, etoh), (ea, water), envelope=env))  # no edges -> no hold
    note = _dag_bench_note([single], ConstraintBox(process=ProcessBounds(max_total_minutes=600.0)))
    assert note is not None
    assert "DISCLOSED (DAG-HOLD-01)" not in note                   # no hold => no concrete clause
    assert "serial-hold stability is UNVERIFIED (a strengthening" in note  # the byte-identical generic sentence
