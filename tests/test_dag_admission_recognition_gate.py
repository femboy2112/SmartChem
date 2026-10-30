"""DAG-ADMIT-02 -- the convergent-DAG reaction-TYPE admission gate (RED-first regression lock).

The DAG-ADMIT-BYPASS: ``admissible_dag_digests`` gated purely on ``fit_status == "FITS"`` and never consulted the
reaction-type oracle, so a conserved FICTION that physically/process-FITS reached an admissible DAG state while its
chemistry was unrecognized -- the linear path carries recognition on the readiness/frontier axis, but a
``RankedDAGSummary`` carries no such axis.  The repair re-derives recognition from the thick ``replay_payload`` at the
admission point (no stored field, no schema/digest/golden move), admitting a FITS DAG only when every step is a
positively-recognized reaction class, while ``fit_status`` keeps its pure physical/process meaning.

These exercise the REAL ``admissible_dag_digests`` property on responses built through ``run_compilation``, by forcing
a genuine IR-backed DAG candidate to a coherent FITS (the ``test_process_service`` idiom) carrying its own replay.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from smartchem.conditions import Interval
from smartchem.process_constraints import Agitation, ProcessBounds, ProcessRequirements
from smartchem.service import (
    RANKED_DAG_SUMMARY_SCHEMA, RankedDAGSummary, TransformGrammar, _dag_dossier_steps_recognized,
    _reconstruct_dag, build_recompile_request, deserialize_response, response_from_payload, response_to_payload,
    run_compilation, serialize_response,
)
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers

from experiments import dag_admission_recognition_gate_probe as probe


def _requirements():
    return ProcessRequirements(
        elapsed_minutes=Interval(10, 20, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True,
        provenance="synthetic software control; no experimental claim")


def _methyl_acetate_dag_response():
    # a COMPLETE convergent-DAG recompile that returns both a recognized (ester) and an unrecognized (multi-step)
    # real IR candidate -- the reachable production shape the finding named.
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, max_depth=3,
        process=ProcessBounds(max_total_minutes=1000.0)))
    assert resp.ranked_dag_dossiers, "setup must yield DAG dossiers"
    return resp


def _recognized(d) -> bool:
    return not route_reaction_type_blockers(_reconstruct_dag(d.replay_payload))


def _force_fits(d, *, replay=True):
    # a coherent FITS dossier for the SAME IR candidate (one declared step, no edges -> process re-derives FITS),
    # carrying (or not) that candidate's own replay -- so recognition re-derives against the real steps.
    return RankedDAGSummary(
        RANKED_DAG_SUMMARY_SCHEMA, d.route_digest, d.equation or "control step", "FITS", (), (),
        (_requirements(),), (), replay_payload=(d.replay_payload if replay else None))


def _inject(resp, forced):
    # replace the matching dossier (same route_digest) so the set still covers every IR candidate (D24.14).
    return replace(resp, ranked_dag_dossiers=tuple(
        forced if d.route_digest == forced.route_digest else d for d in resp.ranked_dag_dossiers))


def test_probe_validates():
    assert probe.validate() is True, probe.measure()


def test_unrecognized_fits_dag_is_withheld_from_admission():
    """THE BYPASS, CLOSED: a FITS DAG whose steps are unrecognized does NOT enter admissible_dag_digests."""
    resp = _methyl_acetate_dag_response()
    unrec = next((d for d in resp.ranked_dag_dossiers if not _recognized(d)), None)
    assert unrec is not None, "setup must yield an unrecognized DAG candidate"
    forced = _force_fits(unrec)
    injected = _inject(resp, forced)
    # the forced dossier IS FITS (fit_status keeps its pure physical/process meaning) ...
    got = next(d for d in injected.ranked_dag_dossiers if d.route_digest == unrec.route_digest)
    assert got.fit_status == "FITS"
    # ... but it is WITHHELD from admission, because its chemistry is unrecognized (the gate).
    assert unrec.route_digest not in injected.admissible_dag_digests
    # NON-VACUITY: it is FITS and would have been admitted by the old fit_status-only rule.
    assert got.fit_status == "FITS" and not _recognized(unrec)


def test_recognized_fits_dag_is_admitted():
    """NO FALSE-EXCLUDE: a FITS DAG whose steps ARE recognized stays admitted."""
    resp = _methyl_acetate_dag_response()
    rec = next((d for d in resp.ranked_dag_dossiers if _recognized(d)), None)
    assert rec is not None, "setup must yield a recognized DAG candidate"
    injected = _inject(resp, _force_fits(rec))
    assert rec.route_digest in injected.admissible_dag_digests


def test_substituted_replay_cannot_buy_admission():
    """FORGE (identity-bind): a recognized candidate's replay carried under an UNRECOGNIZED candidate's digest does
    not bind (reconstruct(replay).digest != route_digest), so it cannot launder the fiction into admission."""
    resp = _methyl_acetate_dag_response()
    rec = next(d for d in resp.ranked_dag_dossiers if _recognized(d))
    unrec = next(d for d in resp.ranked_dag_dossiers if not _recognized(d))
    forged = RankedDAGSummary(
        RANKED_DAG_SUMMARY_SCHEMA, unrec.route_digest, unrec.equation, "FITS", (), (),
        (_requirements(),), (), replay_payload=rec.replay_payload)          # recognized steps, fiction's digest
    injected = _inject(resp, forged)
    assert unrec.route_digest not in injected.admissible_dag_digests
    assert _dag_dossier_steps_recognized(forged) is False                   # the bind refuses the substitution


def test_missing_replay_is_advisory_on_plain_but_refused_under_verified_admission():
    """MISSING-EVIDENCE: a FITS DAG with no replay stays ADVISORY on a plain load (admitted on fit_status, keeping
    process_selection_status/exit_code transport-invariant), and is REFUSED under verified admission -- fail-closed,
    never relabelled chemically impossible (its fit_status is untouched)."""
    resp = _methyl_acetate_dag_response()
    rec = next(d for d in resp.ranked_dag_dossiers if _recognized(d))
    thin = _force_fits(rec, replay=False)
    injected = _inject(resp, thin)
    # advisory on a plain in-memory response: admitted on fit_status (no replay to disprove recognition) ...
    assert rec.route_digest in injected.admissible_dag_digests
    assert _dag_dossier_steps_recognized(thin) is True                      # advisory, not a false "impossible"
    # ... but a no-replay FITS DAG is REFUSED under verified admission (the strong guarantee).
    payload = response_to_payload(injected, include_replay=False)
    with pytest.raises(ValueError):
        response_from_payload(payload, require_verified_admission=True)


_PARA_DAG = dict(helper_reagents=("acetic acid",),
                 stock_materials=("4-aminophenol", "acetic anhydride"), max_depth=1)


def test_gate_does_not_move_result_digest_or_break_round_trip():
    """The gate adds NO stored field and moves NO identity: a REAL recognized FITS DAG (paracetamol via Ac2O) is
    admitted, and a thick round-trip preserves result_digest and the admissible set
    (process_selection_status/exit_code re-derive byte-identically)."""
    from smartchem.process_constraints import Attention
    bench = ProcessBounds(
        allowed_attention=(Attention.PERIODIC,), allowed_agitation=(Agitation.MANUAL, Agitation.NONE),
        available_equipment=("erlenmeyer flask", "steam bath", "glass rod", "ice bath",
                             "fluted filter paper", "buchner funnel", "water aspirator"))
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Nc1ccc(O)cc1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, process=bench, **_PARA_DAG))
    assert resp.admissible_dag_digests, "the recognized paracetamol DAG must be admitted (no false-exclude)"
    assert all(_recognized(d) for d in resp.ranked_dag_dossiers if d.fit_status == "FITS")
    back = deserialize_response(serialize_response(resp))
    assert back.result_digest == resp.result_digest
    assert back.admissible_dag_digests == resp.admissible_dag_digests
    assert back.process_selection_status == resp.process_selection_status
