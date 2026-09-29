"""ONLOAD-REDERIVE (ROADMAP queue item 2): on-load re-derivation of the composability + physical + ranking axes.

Closes the free-text trust boundary the process-only re-derivation (PROCESS-ADMIT-01) left open: a route that is
non-FITS for a composability or physical reason (or with fabricated ranking verdicts) could be bare-relabeled to FITS
and admitted on load.  A verified-admission consumer now RECONSTRUCTS the exact route/DAG from a thick replay payload,
binds it to route_digest, and re-derives the whole combined verdict + ranking + projections -- structurally, no key.

Design + the two holes this round closes (coherence-is-not-binding; the deletion door) are in
docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.2.md.
"""
import json
from dataclasses import replace

import pytest

from smartchem.category import Molecule
from smartchem.conditions import ConditionEnvelope, EvidenceStatus, Interval
from smartchem.experiment import routes
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.process_constraints import Agitation, Attention, ProcessBounds, ProcessRequirements
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.service import (
    TransformGrammar,
    _condition_envelope_from_payload,
    _condition_envelope_to_payload,
    _molecule_from_payload,
    _molecule_to_payload,
    _reconstruct_dag,
    _reconstruct_route,
    _step_from_payload,
    _step_to_payload,
    _steps_to_replay_payload,
    build_recompile_request,
    deserialize_response,
    ranked_dag_summary_from_payload,
    ranked_dag_summary_to_payload,
    run_compilation,
    serialize_response,
)
from smartchem.smiles import parse_smiles


def _jrt(payload):
    """JSON round trip -- exactly what serialize/deserialize does to the payload."""
    return json.loads(json.dumps(payload))


# ======================================================================================================================
# Layer 1 -- the digest-STABLE round trip (the binding rests on reconstruct(payload).digest == route_digest)
# ======================================================================================================================

def test_molecule_codec_round_trips_positionally():
    for mol in (parse_smiles("O"), parse_smiles("CC(=O)O"), Molecule(("Na",), frozenset(), 1, ""),
                Molecule(("Na",), frozenset(), 0, "*"), Molecule.carrier("e-", -1)):
        assert _molecule_from_payload(_jrt(_molecule_to_payload(mol))) == mol


def test_condition_envelope_codec_round_trips_all_ten_fields():
    env = ConditionEnvelope(
        temperature=Interval(300, 340, "K"), pressure=Interval(1.0, 2.5, "atm"),
        duration=Interval(30, 90, "min"), medium="toluene", catalysts=("DMAP", "H2SO4"),
        applied_field="none", status=EvidenceStatus.EXPERIMENTAL, provenance="declared for the test",
        source=SourceCitation("doi:10.0000/test", SourceReview.UNREVIEWED),
        process=ProcessRequirements(elapsed_minutes=Interval(40, 40, "min"), equipment=("flask",),
                                    workup_included=True, provenance="declared", peak_temperature_k=345.0),
    )
    assert _condition_envelope_from_payload(_jrt(_condition_envelope_to_payload(env))).digest == env.digest
    unknown = ConditionEnvelope.unknown()
    assert _condition_envelope_from_payload(_jrt(_condition_envelope_to_payload(unknown))).digest == unknown.digest


def _rich_step():
    water = parse_smiles("O")
    env = ConditionEnvelope(temperature=Interval(300, 340, "K"), status=EvidenceStatus.EXPERIMENTAL,
                            provenance="declared", process=ProcessRequirements(
                                elapsed_minutes=Interval(40, 40, "min"), provenance="declared"))
    return ExperimentStep.assembling(water, (water,), (water,), envelope=env)


def _convergent_dag():
    acoh, etoh, ea, water, ald, ethene, o2 = (parse_smiles(s) for s in
        ("CC(=O)O", "CCO", "CC(=O)OCC", "O", "CC=O", "C=C", "O=O"))

    def step(target, reactants, products):
        env = ConditionEnvelope(temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
                                provenance="synthetic", process=ProcessRequirements(
                                    elapsed_minutes=Interval(40, 40, "min"), provenance="declared"))
        return ExperimentStep.assembling(target, reactants, products, envelope=env)

    return SynthesisDAG.of(
        step(acoh, (ald, ald, o2), (acoh, acoh)),
        step(etoh, (ethene, water), (etoh,)),
        step(ea, (acoh, etoh), (ea, water)),
    )


def test_step_reconstruction_re_runs_the_conservation_certificate():
    step = _rich_step()
    assert _step_from_payload(_jrt(_step_to_payload(step))).digest == step.digest


def test_route_reconstruct_digest_equals_route_digest():
    route = ExperimentRoute.of(_rich_step())
    assert _reconstruct_route(_jrt(_steps_to_replay_payload(route.steps))).digest == route.digest


def test_dag_reconstruct_digest_equals_dag_digest():
    dag = _convergent_dag()
    back = _reconstruct_dag(_jrt(_steps_to_replay_payload(dag.steps)))
    assert back.digest == dag.digest
    assert [(i, j) for i, j, _ in back.edges] == [(i, j) for i, j, _ in dag.edges]


def test_non_conserving_forged_step_is_refused_at_reconstruction():
    dag = _convergent_dag()
    tp = _steps_to_replay_payload(dag.steps)
    tp[0]["reactants"] = tp[0]["reactants"][:-1]           # drop an O2 -> no longer balanced
    with pytest.raises(Exception):
        _reconstruct_dag(_jrt(tp))


def test_tampered_envelope_breaks_the_route_binding():
    route = ExperimentRoute.of(_rich_step())
    tp = _steps_to_replay_payload(route.steps)
    tp[0]["envelope"]["temperature"] = {"lo": 999.0, "hi": 999.0, "unit": "K"}
    assert _reconstruct_route(_jrt(tp)).digest != route.digest


# ======================================================================================================================
# Layer 2 -- the LINEAR verified-admission policy on a REAL FITS response
# ======================================================================================================================

def _requirements(**changes):
    return replace(ProcessRequirements(
        elapsed_minutes=Interval(10, 20, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True,
        provenance="synthetic software control; no experimental claim"), **changes)


def _fits_response(monkeypatch):
    """A REAL compile whose routes are declared-FITS (the test_process_service synthetic-control pattern)."""
    original = routes._conditions_for
    monkeypatch.setattr(routes, "_conditions_for",
                        lambda t: replace(original(t), process=_requirements()))
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, process=ProcessBounds.quick()))
    assert resp.admissible_route_digests, "setup must yield at least one FITS route"
    return resp


def test_honest_fits_response_survives_verified_admission(monkeypatch):
    """SOUNDNESS: an honest producer response, serialized with the replay payload, passes verified admission with no
    false reject -- the re-projection reproduces every dossier exactly under the response's own pinned eval-context."""
    resp = _fits_response(monkeypatch)
    wire = serialize_response(resp, include_replay=True)
    reloaded = deserialize_response(wire, require_verified_admission=True)
    assert reloaded.admissible_route_digests == resp.admissible_route_digests


def test_verified_admission_is_fail_closed_on_a_missing_payload(monkeypatch):
    """THE DELETION DOOR: the default serialization omits the replay payload (byte-stable).  A verified-admission
    consumer must then REFUSE a FITS route -- it is UNVERIFIED, never admitted, so a stripped payload cannot pass."""
    resp = _fits_response(monkeypatch)
    thin_wire = serialize_response(resp, include_replay=False)                # v0.8 D5: the EXPLICIT lean opt-out
    assert "replay_payload" not in thin_wire                                 # thin: no payload on the wire
    deserialize_response(thin_wire)                                          # default consumer: fine (advisory)
    with pytest.raises(ValueError, match="no replay_payload|UNVERIFIED"):
        deserialize_response(thin_wire, require_verified_admission=True)


def test_bare_relabel_of_a_physical_exclusion_to_fits_is_rejected(monkeypatch):
    """THE HOLE THE ROUND CLOSES: a route EXCLUDED for a PHYSICAL reason (400 K over a 350 K bench cap) whose PROCESS
    axis is FITS.  The process-only re-derivation (PROCESS-ADMIT-01) admits the bare relabel to FITS (the physical
    axis is not re-derived) -- verified admission reconstructs the route, re-derives the physical box, gets EXCLUDED,
    and refuses.  Without a key.  (Mirrors test_process_service.test_non_process_axis_relabel_is_not_yet_authenticated,
    which pins that the DEFAULT unsigned load still accepts it.)"""
    declared = ProcessRequirements(
        elapsed_minutes=Interval(5, 10, "min"), active_minutes=Interval(1, 2, "min"),
        agitation=Agitation.NONE, workup_included=True, provenance="synthetic control; no experimental claim")
    hot = ConditionEnvelope(temperature=Interval(400, 400, "K"), status=EvidenceStatus.EXPERIMENTAL,
                            provenance="synthetic physical control; no experimental claim", process=declared)
    monkeypatch.setattr(routes, "_conditions_for", lambda t: hot)
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, process=ProcessBounds.quick(), max_temperature_k=350))
    victim = resp.ranked_route_dossiers[0]
    assert victim.fit_status == "EXCLUDED" and any("caps at 350" in e for e in victim.exclusions)
    forged = replace(victim, fit_status="FITS", exclusions=(), gaps=())      # physical axis stays process-FITS
    promoted = replace(resp, ranked_route_dossiers=(forged, *resp.ranked_route_dossiers[1:]))
    assert promoted.admissible_route_digests == (victim.route_digest,)        # process-only check still admits it ...
    wire = serialize_response(promoted, include_replay=True)
    with pytest.raises(ValueError, match="re-projects to a DIFFERENT summary"):  # ... verified admission refuses it
        deserialize_response(wire, require_verified_admission=True)


def test_evidence_substitution_across_routes_is_rejected(monkeypatch):
    """HOLE 1 (coherence is not binding): put route A's genuinely-FITS payload under route B's route_digest.  The
    reconstructed route's digest != the claimed route_digest, so the re-projected summary != the claimed one."""
    resp = _fits_response(monkeypatch)
    dossiers = resp.ranked_route_dossiers
    a, b = dossiers[0], next(d for d in dossiers[1:] if d.route_digest != dossiers[0].route_digest)
    swapped = replace(a, replay_payload=b.replay_payload)                    # A's identity, B's evidence
    forged = replace(resp, ranked_route_dossiers=(swapped,) + dossiers[1:])
    wire = serialize_response(forged, include_replay=True)
    with pytest.raises(ValueError, match=r"re-projects to a DIFFERENT summary|refused \(D26\.1\)"):  # D26.1 first
        deserialize_response(wire, require_verified_admission=True)


def test_request_relaxation_is_admitted_unless_the_request_is_pinned(monkeypatch):
    """evil-morty Finding 1 (VERIFIED): the re-derivation trusts the response's OWN request as the bench box.  A
    keyless attacker who RELAXES that request (drops the temperature cap) makes an out-of-bounds route re-derive FITS.
    This pins BOTH directions: WITHOUT a request pin the relaxation is admitted (the honest, documented residual --
    the check authenticates verdict<->route coherence under the STATED context, not the context); WITH the consumer's
    real request pinned via expected_request_digest, it is refused."""
    from dataclasses import replace as _replace

    from smartchem.constraints import PhysicalBounds
    declared = ProcessRequirements(elapsed_minutes=Interval(5, 10, "min"), active_minutes=Interval(1, 2, "min"),
                                   agitation=Agitation.NONE, workup_included=True, provenance="synthetic control")
    hot = ConditionEnvelope(temperature=Interval(400, 400, "K"), status=EvidenceStatus.EXPERIMENTAL,
                            provenance="synthetic physical control", process=declared)
    monkeypatch.setattr(routes, "_conditions_for", lambda t: hot)
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)OC", max_depth=2, process=ProcessBounds.quick(), max_temperature_k=350))
    victim = resp.ranked_route_dossiers[0]
    assert victim.fit_status == "EXCLUDED"
    forged = _replace(victim, fit_status="FITS", exclusions=(), gaps=())
    relaxed_request = _replace(resp.request, constraints=_replace(resp.request.constraints,
                                                                  bounds=PhysicalBounds.of()))  # drop the 350 K cap
    promoted = _replace(resp, request=relaxed_request,
                        ranked_route_dossiers=(forged, *resp.ranked_route_dossiers[1:]))
    wire = serialize_response(promoted, include_replay=True)
    # WITHOUT a request pin: the relaxed box re-derives the 400 K route to FITS -> ADMITTED (documented residual).
    reloaded = deserialize_response(wire, require_verified_admission=True)
    assert forged.route_digest in reloaded.admissible_route_digests
    # WITH the consumer's real (350 K cap) request pinned: the mismatch is refused.
    with pytest.raises(ValueError, match="DIFFERENT request|expected_request_digest"):
        deserialize_response(wire, require_verified_admission=True,
                             expected_request_digest=resp.request.semantic_digest)


def test_serial_holds_are_re_derived_not_trusted():
    """evil-morty Finding 2 fold: serial_holds is compare=False (ignored by ==), so verified admission re-derives it
    explicitly from the reconstructed DAG.  The re-derivation reproduces the TRUE holds and differs from any tampered
    value, so a forged disclosure is refused."""
    from smartchem.constraints import PhysicalBounds
    from smartchem.experiment.drafter import ConstraintBox
    from smartchem.service import RankedDAGSummary
    dag = _convergent_dag()
    box = ConstraintBox.of_bounds(PhysicalBounds.of(), process=ProcessBounds(max_total_minutes=1000))
    summary = RankedDAGSummary.of_dag(dag, box)
    assert summary.serial_holds, "the convergent DAG must expose a serial hold to make this non-vacuous"
    tampered = tuple((i, j, m + 999.0) for i, j, m in summary.serial_holds)
    rederived = RankedDAGSummary.of_dag(_reconstruct_dag(_jrt(_steps_to_replay_payload(dag.steps))), box)
    assert rederived.serial_holds == summary.serial_holds != tampered


def test_the_replay_payload_never_moves_route_identity(monkeypatch):
    """The payload is compare=False: whether or not it rides the wire, result_digest is byte-identical -- route
    identity is preserved, exactly as the scope decision requires (no schema bump, no golden churn)."""
    resp = _fits_response(monkeypatch)
    lean = deserialize_response(serialize_response(resp))                     # no payload
    fat = deserialize_response(serialize_response(resp, include_replay=True)) # payload present
    assert lean.result_digest == resp.result_digest == fat.result_digest


# ======================================================================================================================
# Layer 3 -- the DAG verified-admission policy on a REAL FITS DAG response
# ======================================================================================================================

_PARA_DAG = dict(helper_reagents=("acetic acid",),
                 stock_materials=("4-aminophenol", "acetic anhydride"), max_depth=1)
_PARA_BENCH = ProcessBounds(
    allowed_attention=(Attention.PERIODIC,), allowed_agitation=(Agitation.MANUAL, Agitation.NONE),
    available_equipment=("erlenmeyer flask", "steam bath", "glass rod", "ice bath",
                         "fluted filter paper", "buchner funnel", "water aspirator"),
)


def _fits_dag_response():
    resp = run_compilation(build_recompile_request(
        "smiles:CC(=O)Nc1ccc(O)cc1", grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT,
        process=_PARA_BENCH, **_PARA_DAG))
    assert any(d.fit_status == "FITS" for d in resp.ranked_dag_dossiers), "setup must yield a FITS DAG"
    return resp


def test_honest_fits_dag_survives_verified_admission():
    resp = _fits_dag_response()
    reloaded = deserialize_response(serialize_response(resp, include_replay=True), require_verified_admission=True)
    assert reloaded.admissible_dag_digests == resp.admissible_dag_digests


def test_fits_dag_without_payload_is_fail_closed():
    resp = _fits_dag_response()
    with pytest.raises(ValueError, match="no replay_payload|UNVERIFIED"):
        # v0.8 D5: the replay-less wire is now the EXPLICIT thin opt-out; a verified-admission consumer still refuses it.
        deserialize_response(serialize_response(resp, include_replay=False), require_verified_admission=True)


# ======================================================================================================================
# Layer 4 -- parser hardening: the edges int-coercion trap is closed BEFORE coercion
# ======================================================================================================================

@pytest.mark.parametrize("bad_edge", [[True, 0], [0, 1.9], ["0", 1], [0, "1"]])
def test_dag_edges_reject_non_int_wire_types_before_coercion(bad_edge):
    """A bool/float/string edge index must be REFUSED, not silently coerced (int(True)==1, int(1.9)==1) into a
    legal-looking edge.  Regression against tuple((int(a), int(b)) for a, b in edges) running before the guard."""
    from smartchem.constraints import PhysicalBounds
    from smartchem.experiment.drafter import ConstraintBox
    from smartchem.service import RankedDAGSummary
    summary = RankedDAGSummary.of_dag(_convergent_dag(), ConstraintBox.of_bounds(PhysicalBounds.of()))
    payload = ranked_dag_summary_to_payload(summary)
    assert payload["edges"], "the convergent DAG must expose real edges to corrupt"
    payload["edges"][0] = bad_edge
    with pytest.raises(TypeError):
        ranked_dag_summary_from_payload(payload)
