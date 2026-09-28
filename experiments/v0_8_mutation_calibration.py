"""V0.8-MUTATION-01: the calibrated mutation gate for the readiness-obligation ladder (plan Sec 10.1/10.4, M1-M20).

Same discipline as `v0_7_mutation_calibration.py`: adding tests is not enough -- a test that would still pass
on BROKEN code proves nothing. This harness INJECTS each of the 20 failure modes the plan names (M1-M11 from
Round I, M12-M20 added in Round II for typed procedure evidence + canonical transport), on the REAL
`smartchem.experiment.readiness` module (plus, where the failure mode actually lives one layer over in the
upstream isomer guard / the service transport, the real `smartchem.experiment.routes` /
`smartchem.decompiler_conditions` / `smartchem.service` call it's wired through), and shows the corresponding
guard actually flips (the mutant is KILLED). Every mutation is applied via a context-managed monkeypatch and
undone on exit -- this harness never edits a single byte of `smartchem/`, it only pokes at it in memory for
the duration of one check.

Ugh, real talk: M11 is the one that matters most here. Paracetamol's anhydride step is the best-SOURCED
record in the whole corpus (a real DOI) and the worst-recognized reaction (none of the 17 oracle classes
fit an anhydride transacylation) -- so it reports `conditions=SATISFIED` while its coarse `tier` is only
`FORMAL_CANDIDATE`. That is NOT a bug. A "fix" that makes `conditions` agree with the coarse tier is exactly
M11 (deriving obligations FROM the tier instead of the tier FROM the obligations), and this harness pins that
paracetamol's own real corpus record is what M11's mutant breaks.

Round II's M12-M20 harden the typed `ProcedureEvidence`/canonical-transport closure (Wave A Lane F's runnable
repros informed the exact shapes): a canonical above-FORMAL payload with its replay stripped (M12), an
unsourced-but-declared workup (M13), the retired legacy `workup_included` boolean (M14), a silently-skipped
whole-procedure field (M15), free-text prose parsed into structure (M16), the envelope's conditions source
laundering the procedure's own sourcing requirement (M17), the workup gate being droppable from the tier
property -- asserted DIRECTLY on the derivation, never a round-trip, per Wave A Lane E (M18), a same-formula
isomer borrowing procedure evidence through the isomer-blind path (M19), and a bench-fit `FITS` verdict
promoting procedure completeness -- also asserted directly (M20).

Run:  .venv/bin/python experiments/v0_8_mutation_calibration.py
"""
from __future__ import annotations

import contextlib
from dataclasses import replace

import smartchem.decompiler_conditions as dc
import smartchem.experiment.readiness as readiness
import smartchem.experiment.routes as rt
import smartchem.service as svc
from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.conditions import ConditionEnvelope, EvidenceStatus
from smartchem.experiment.readiness import (
    CONDITIONS_SUPPORTED,
    FORMAL_CANDIDATE,
    PROCESS_SPECIFIED,
    REACTION_VOUCHED,
    ObligationStatus,
    RouteReadiness,
    StepReadiness,
    evaluate_route,
    evaluate_step,
    tier_rank,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.process_constraints import ProcessRequirements
from smartchem.procedure_evidence import EvidenceField, EvidenceFieldStatus
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.service import build_recompile_request, response_from_payload, response_to_payload, run_compilation
from smartchem.smiles import parse_smiles

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

_MUTANTS: list = []


def mutant(name: str):
    def deco(fn):
        _MUTANTS.append((name, fn))
        return fn
    return deco


@contextlib.contextmanager
def _patch(obj, name, value):
    """Temporarily set ``obj.name = value`` (works on modules and class objects), restoring exactly on exit."""
    had = name in getattr(obj, "__dict__", {})
    old = obj.__dict__.get(name) if had else None
    setattr(obj, name, value)
    try:
        yield
    finally:
        if had:
            setattr(obj, name, old)
        else:
            try:
                delattr(obj, name)
            except AttributeError:
                pass


# -- fixtures --------------------------------------------------------------------------------------------------


def _identity_step(envelope: "ConditionEnvelope | None" = None) -> ExperimentStep:
    """A trivial CO2 -> CO2 "step" (mass/charge trivially conserved, so it passes the real conservation cert).
    Its whole point is to have NO real reaction centre, so the production oracle honestly reports
    `reaction_type` UNSATISFIED -- an uncontroversial, always-reproducible "not vouched" fixture, with a
    caller-chosen envelope so the conditions/process/workup axes are independently controllable."""
    co2 = parse_smiles("O=C=O")
    return ExperimentStep.assembling(co2, (co2,), (co2,), envelope=envelope)


def _search(target_name: str, reagents: tuple, have: tuple, max_depth: int):
    """Direct `search_routes` under the promoted default algebra (mirrors what the service does internally,
    without importing `drafter.py`), giving raw `ExperimentStep` objects for fixtures that need one."""
    target = resolve_target(target_name, InputKind.NAME).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _isopentyl_step_process_specified() -> ExperimentStep:
    """The real isopentyl-acetate PROCESS_SPECIFIED step (Sec 9 row 4): reaction_type SATISFIED, conditions
    SATISFIED, a COMPLETE + sourced typed `ProcedureEvidence` -- the base fixture every M13-M20 procedure-tamper
    mutant below derives from via `_with_procedure` (`dataclasses.replace` on ONE field of this real, honestly
    PROCESS_SPECIFIED record), never a hand-invented procedure built from scratch. As of Round II this is a
    real, reachable corpus member (the old Round-I fixture-finder here looked for a CONDITIONS_SUPPORTED
    isopentyl step -- Round II's completed procedure means no such step exists in this corpus any more; every
    isopentyl route step is now either FORMAL_CANDIDATE or this honest PROCESS_SPECIFIED one)."""
    result = _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3)
    for route in result.routes:
        rr = evaluate_route(route)
        for step, sr in zip(route.steps, rr.per_step):
            if sr.tier == PROCESS_SPECIFIED:
                return step
    raise AssertionError("expected a real isopentyl acetate PROCESS_SPECIFIED step in the forcing corpus")


def _with_procedure(step: ExperimentStep, **overrides) -> ExperimentStep:
    """A copy of `step` whose `envelope.procedure` is the REAL isopentyl `ProcedureEvidence`
    (:func:`_isopentyl_step_process_specified`) with `overrides` applied via `dataclasses.replace` -- every
    M13-M20 tamper mutates exactly ONE field of a real, honestly-complete procedure, so a fixture bug can never
    make the honest and the mutant path agree for the wrong (both-broken) reason."""
    procedure = replace(step.envelope.procedure, **overrides)
    envelope = replace(step.envelope, procedure=procedure)
    return replace(step, envelope=envelope)


def _isopentyl_step_conditions_supported() -> ExperimentStep:
    """A declared-but-INCOMPLETE isopentyl procedure (Round II's `procedure_representation_is_complete` fails
    because `analytical_verification` is knocked back to genuinely `UNKNOWN_MISSING`, the source's honest
    silence) -- M7's fixture: `process` present-but-not-None must not be conflated with complete."""
    base = _isopentyl_step_process_specified()
    return _with_procedure(base, analytical_verification=EvidenceField.unknown())


def _methyl_salicylate_step_workup_false() -> ExperimentStep:
    """A declared-but-genuinely-SILENT workup axis on the (otherwise real, complete) isopentyl procedure --
    M8's fixture (Round II retired the legacy `process.workup_included=False` boolean this fixture used to read;
    the honest new failure mode is a whole-procedure field left `UNKNOWN_MISSING`, never silently promoted)."""
    base = _isopentyl_step_process_specified()
    return _with_procedure(base, workup_isolation=EvidenceField.unknown())


def _paracetamol_step_recognized_conditions_unknown() -> ExperimentStep:
    """paracetamol's real recognized-but-conditions-unknown step (a plain acyl condensation route the oracle
    DOES recognize, with no attached SEED_CONDITIONS record) -- M2's fixture."""
    result = _search("paracetamol", ("water", "acetic acid"), ("4-aminophenol",), 2)
    for route in result.routes:
        rr = evaluate_route(route)
        for step, sr in zip(route.steps, rr.per_step):
            if sr.reaction_type is ObligationStatus.SATISFIED and sr.conditions is not ObligationStatus.SATISFIED:
                return step
    raise AssertionError("expected a real paracetamol reaction-vouched/conditions-unknown step")


def _paracetamol_step_nonmonotonic():
    """paracetamol's real non-monotonic exemplar (Sec 4.1): the sourced anhydride step, `conditions=SATISFIED`
    while `reaction_type=UNSATISFIED` caps the coarse tier at FORMAL_CANDIDATE. Returns `(step, StepReadiness)`
    -- M11's fixture, and the one the plan explicitly names as what M11 must break."""
    result = _search("paracetamol", ("water", "acetic acid"), ("4-aminophenol",), 2)
    for route in result.routes:
        rr = evaluate_route(route)
        for step, sr in zip(route.steps, rr.per_step):
            if sr.conditions is ObligationStatus.SATISFIED and sr.reaction_type is ObligationStatus.UNSATISFIED:
                return step, sr
    raise AssertionError("expected paracetamol's real non-monotonic (sourced, unrecognized) step")


def _isomer_conditions_axes() -> tuple:
    """The live `conditions` axis for every step of every route the real service returns for the
    4-aminophenyl-acetate isomer, under the SAME reagents paracetamol uses -- M9's honest-vs-mutant probe."""
    req = build_recompile_request(
        "4-aminophenyl acetate", input_kind=InputKind.NAME, helper_reagents=("water", "acetic acid"),
        stock_materials=("4-aminophenol",), max_depth=2,
    )
    resp = run_compilation(req)
    return tuple(sr.conditions for r in resp.ranked_route_dossiers for sr in r.readiness.per_step)


# -- M1-M11 ------------------------------------------------------------------------------------------------------


@mutant("M1 every-formal-route-must-not-auto-become-reaction-vouched")
def m1() -> bool:
    step = _identity_step()
    sr = evaluate_step(step)
    real_ok = sr.tier == FORMAL_CANDIDATE  # honest: unrecognized reaction_type caps the tier here

    def mutant_tier(self) -> str:  # BUG: skips the reaction_type check entirely
        if self.formal_candidate is not ObligationStatus.SATISFIED:
            return FORMAL_CANDIDATE
        if self.conditions is not ObligationStatus.SATISFIED:
            return REACTION_VOUCHED
        if self.process is not ObligationStatus.SATISFIED:
            return CONDITIONS_SUPPORTED
        return PROCESS_SPECIFIED

    with _patch(StepReadiness, "tier", property(mutant_tier)):
        mutant_bad = sr.tier != FORMAL_CANDIDATE
    return real_ok and mutant_bad


@mutant("M2 a-recognized-reaction-must-not-auto-satisfy-conditions")
def m2() -> bool:
    step = _paracetamol_step_recognized_conditions_unknown()
    sr = evaluate_step(step)
    real_ok = sr.tier == REACTION_VOUCHED

    def mutant_tier(self) -> str:  # BUG: skips the conditions check once reaction_type is SATISFIED
        if self.formal_candidate is not ObligationStatus.SATISFIED:
            return FORMAL_CANDIDATE
        if self.reaction_type is not ObligationStatus.SATISFIED:
            return FORMAL_CANDIDATE
        if self.process is not ObligationStatus.SATISFIED:
            return CONDITIONS_SUPPORTED
        return PROCESS_SPECIFIED

    with _patch(StepReadiness, "tier", property(mutant_tier)):
        mutant_bad = sr.tier != REACTION_VOUCHED
    return real_ok and mutant_bad


@mutant("M3 a-declared-but-unsourced-envelope-must-not-count-as-sourced")
def m3() -> bool:
    env = ConditionEnvelope(
        medium="hand-built test medium", status=EvidenceStatus.EXPERIMENTAL,
        provenance="hand-built, declared, deliberately UNSOURCED (no SourceCitation)",
    )
    step = _identity_step(env)
    real_ok = evaluate_step(step).conditions == ObligationStatus.UNSATISFIED

    def mutant_conditions_obligation(step, identity_losses):  # BUG: declared alone counts as sourced
        if step.envelope.is_declared:
            return ObligationStatus.SATISFIED, None, None
        return ObligationStatus.UNKNOWN, None, "conditions: no declared condition envelope (unknown)"

    with _patch(readiness, "_conditions_obligation", mutant_conditions_obligation):
        mutant_bad = evaluate_step(step).conditions == ObligationStatus.SATISFIED
    return real_ok and mutant_bad


@mutant("M4 route-aggregation-must-be-weakest-link-not-any-step")
def m4() -> bool:
    weak = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED, reaction_type=ObligationStatus.UNSATISFIED,
        reaction_class_name=None, conditions=ObligationStatus.UNKNOWN, process=ObligationStatus.UNKNOWN,
        workup_isolation=ObligationStatus.UNKNOWN, provenance=(),
        open_obligations=("reaction_type: not recognized by the production oracle",),
    )
    strong = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED, reaction_type=ObligationStatus.SATISFIED,
        reaction_class_name="hand-built class", conditions=ObligationStatus.SATISFIED,
        process=ObligationStatus.UNSATISFIED, workup_isolation=ObligationStatus.SATISFIED,
        provenance=("https://doi.org/10.1000/hand-built",),
        open_obligations=("process: declared but not a complete bench-procedure representation",),
    )
    route = RouteReadiness(
        per_step=(weak, strong),
        route_open_obligations=tuple(sorted(set(weak.open_obligations + strong.open_obligations))),
    )
    real_ok = route.tier == FORMAL_CANDIDATE  # weakest-link: the unvouched step caps the whole route

    def mutant_route_tier(self) -> str:  # BUG: an accepted source on ONE step promotes the whole route
        return max((step.tier for step in self.per_step), key=tier_rank)

    with _patch(RouteReadiness, "tier", property(mutant_route_tier)):
        mutant_bad = route.tier != FORMAL_CANDIDATE
    return real_ok and mutant_bad


@mutant("M5 favorable-thermo-must-not-substitute-for-reaction-vouch")
def m5() -> bool:
    step = _identity_step()
    object.__setattr__(step, "_favorable_thermo_probe", True)  # an out-of-band hint a naive caller might read
    real_ok = evaluate_step(step).reaction_type == ObligationStatus.UNSATISFIED

    def mutant_reaction_type_obligation(step):  # BUG: a favorable-thermo hint substitutes for the real oracle
        if getattr(step, "_favorable_thermo_probe", False):
            return ObligationStatus.SATISFIED, "favorable-thermo-surrogate (not a real reaction-type vouch)"
        from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
        klass = recognize_reaction_type(step)
        return (ObligationStatus.SATISFIED if klass is not None else ObligationStatus.UNSATISFIED), klass

    with _patch(readiness, "_reaction_type_obligation", mutant_reaction_type_obligation):
        mutant_bad = evaluate_step(step).reaction_type == ObligationStatus.SATISFIED
    return real_ok and mutant_bad


@mutant("M6 a-fits-bench-verdict-must-not-substitute-for-readiness")
def m6() -> bool:
    step = _identity_step()
    object.__setattr__(step, "_fit_status_probe", "FITS")  # a bench-fit verdict readiness must never consult
    real_ok = evaluate_step(step).tier == FORMAL_CANDIDATE
    real_evaluate_step = readiness.evaluate_step

    def mutant_evaluate_step(step, *, identity_losses=()):  # BUG: FITS is read as readiness evidence
        sr = real_evaluate_step(step, identity_losses=identity_losses)
        if getattr(step, "_fit_status_probe", None) == "FITS":
            sr = replace(
                sr, reaction_type=ObligationStatus.SATISFIED, reaction_class_name="fit-status-surrogate",
                conditions=ObligationStatus.SATISFIED,
            )
        return sr

    with _patch(readiness, "evaluate_step", mutant_evaluate_step):
        mutant_bad = readiness.evaluate_step(step).tier != FORMAL_CANDIDATE
    return real_ok and mutant_bad


@mutant("M7 procedure-present-must-not-imply-complete")
def m7() -> bool:
    # Round II renamed `process_representation_is_complete(process)` to
    # `procedure_representation_is_complete(evidence)` (it now reads `step.envelope.procedure`, a typed
    # `ProcedureEvidence`, never the legacy `ProcessRequirements`). This step's real procedure is DECLARED but
    # genuinely INCOMPLETE (Sec 5/D3) -- the exact fixture the presence-alone bug needs.
    step = _isopentyl_step_conditions_supported()
    real_ok = evaluate_step(step).tier == CONDITIONS_SUPPORTED

    def mutant_procedure_complete(evidence) -> bool:  # BUG: mere presence counts as a complete representation
        return evidence is not None

    with _patch(readiness, "procedure_representation_is_complete", mutant_procedure_complete):
        mutant_bad = evaluate_step(step).tier == PROCESS_SPECIFIED
    return real_ok and mutant_bad


@mutant("M8 workup-included-false-must-not-be-ignored")
def m8() -> bool:
    step = _methyl_salicylate_step_workup_false()
    real_ok = evaluate_step(step).workup_isolation == ObligationStatus.UNSATISFIED
    real_process_and_workup = readiness._process_and_workup_obligations

    def mutant_process_and_workup(step):  # BUG: workup_included=False is silently promoted to SATISFIED
        process_status, _workup_status, locator, obligations = real_process_and_workup(step)
        kept = tuple(o for o in obligations if not o.startswith("workup_isolation"))
        return process_status, ObligationStatus.SATISFIED, locator, kept

    with _patch(readiness, "_process_and_workup_obligations", mutant_process_and_workup):
        mutant_bad = evaluate_step(step).workup_isolation == ObligationStatus.SATISFIED
    return real_ok and mutant_bad


@mutant("M9 a-same-formula-isomer-must-not-borrow-condition-evidence")
def m9() -> bool:
    honest = _isomer_conditions_axes()
    real_ok = len(honest) > 0 and all(a is ObligationStatus.UNKNOWN for a in honest)

    def mutant_assembly_conditions(capped, *, losses=()):  # BUG: the target/precursor name-guard is dropped
        from smartchem.identity import is_blocked
        from smartchem.structure import resolve_structure
        if is_blocked(tuple(losses), "conditions"):
            return dc.ConditionEnvelope.unknown()
        record = dc.SEED_CONDITIONS.get(dc._reaction_signature(capped.forget()))
        if record is None or dc.ReactionDirection.ASSEMBLY not in record.directions:
            return dc.ConditionEnvelope.unknown()
        target = resolve_structure(capped.reactant)
        precursors = tuple(resolve_structure(m) for m in capped.products)
        if target is None or any(p is None for p in precursors):
            return dc.ConditionEnvelope.unknown()
        return record.envelope  # the name-guard check that belongs here is simply missing

    with _patch(rt, "assembly_conditions", mutant_assembly_conditions):
        mutated = _isomer_conditions_axes()
    mutant_bad = any(a is ObligationStatus.SATISFIED for a in mutated)
    return real_ok and mutant_bad


@mutant("M10 a-serialized-tier-edited-without-evidence-moving-must-be-refused-on-load")
def m10() -> bool:
    req = build_recompile_request(
        "isopentyl acetate", input_kind=InputKind.NAME, helper_reagents=("water", "acetic acid"),
        stock_materials=("isopentyl alcohol",), max_depth=3,
    )
    resp = run_compilation(req)
    idx = next(
        (i for i, r in enumerate(resp.ranked_route_dossiers) if r.readiness.tier != CONDITIONS_SUPPORTED), None,
    )
    if idx is None:
        raise AssertionError("expected a non-CONDITIONS_SUPPORTED isopentyl acetate route to tamper")
    orig = resp.ranked_route_dossiers[idx]
    # tamper: claim every step's conditions are SATISFIED-with-provenance, WITHOUT touching replay_payload (the
    # evidence that would need to have actually moved).
    tampered_readiness = replace(
        orig.readiness,
        per_step=tuple(
            replace(sr, conditions=ObligationStatus.SATISFIED, provenance=("https://doi.org/10.1000/forged",))
            for sr in orig.readiness.per_step
        ),
    )
    tampered = replace(orig, readiness=tampered_readiness)
    dossiers = list(resp.ranked_route_dossiers)
    dossiers[idx] = tampered
    tampered_resp = replace(resp, ranked_route_dossiers=tuple(dossiers))
    payload = svc.response_to_payload(tampered_resp, include_replay=True)

    real_refuses = False
    try:
        svc.response_from_payload(payload)
    except ValueError:
        real_refuses = True

    with _patch(svc.CompilationResponse, "_check_readiness_coherence", lambda self, **kw: None):
        try:
            svc.response_from_payload(payload)
            mutant_loads = True
        except ValueError:
            mutant_loads = False
    return real_refuses and mutant_loads


@mutant("M11 obligations-must-be-derived-from-the-tier-never-the-reverse")
def m11() -> bool:
    step, real_sr = _paracetamol_step_nonmonotonic()
    real_ok = real_sr.conditions is ObligationStatus.SATISFIED and real_sr.tier == FORMAL_CANDIDATE
    real_evaluate_step = readiness.evaluate_step

    def mutant_evaluate_step(step, *, identity_losses=()):
        # BUG: collapse orthogonality -- force conditions to agree with the coarse tier instead of letting the
        # tier stay a pure PROJECTION of the (already-computed) obligations. This is what breaks paracetamol's
        # visible sourced-but-unrecognized record: its conditions=SATISFIED can no longer survive a coarse tier
        # weaker than CONDITIONS_SUPPORTED.
        sr = real_evaluate_step(step, identity_losses=identity_losses)
        if tier_rank(sr.tier) < tier_rank(CONDITIONS_SUPPORTED) and sr.conditions is ObligationStatus.SATISFIED:
            sr = replace(sr, conditions=ObligationStatus.UNSATISFIED)
        return sr

    with _patch(readiness, "evaluate_step", mutant_evaluate_step):
        mutant_sr = readiness.evaluate_step(step)
    mutant_bad = mutant_sr.conditions is not ObligationStatus.SATISFIED
    return real_ok and mutant_bad


# -- M12-M20 (0.8 Round II) ---------------------------------------------------------------------------------


@mutant("M12 a-canonical-above-formal-payload-with-replay-stripped-must-be-refused")
def m12() -> bool:
    """D5/Blocker A: `transport_mode=CANONICAL_VERIFIED` (the DEFAULT wire, `include_replay=True`) DECLARES its
    above-FORMAL readiness claims re-derivable; a canonical payload whose `replay_payload` is stripped (while
    the declared mode stays CANONICAL_VERIFIED) has nothing left to re-derive FROM and must be refused on
    ordinary load -- this is the mechanism `_check_readiness_coherence`/`response_from_payload` already runs
    unconditionally off the payload's OWN declared mode (not a caller flag), so this mutant proves it is really
    load-bearing, not just present in the source.

    Second, narrower check folded in here (the plan's 'M10-analogue' for procedure evidence specifically): when
    the replay IS present but the replayed step's `envelope.procedure` inside it is stripped, the re-derivation
    disagrees with the carried readiness (a lower tier) and is refused too -- the SAME unconditional mechanism,
    exercised on the procedure axis rather than the whole replay.
    """
    req = build_recompile_request(
        "isopentyl acetate", input_kind=InputKind.NAME, helper_reagents=("water", "acetic acid"),
        stock_materials=("isopentyl alcohol",), max_depth=3,
    )
    resp = run_compilation(req)
    idx = next(
        (i for i, r in enumerate(resp.ranked_route_dossiers) if r.readiness.tier == PROCESS_SPECIFIED), None,
    )
    if idx is None:
        raise AssertionError("expected a real PROCESS_SPECIFIED isopentyl acetate route to tamper")

    # -- part (a): CANONICAL_VERIFIED payload, whole replay stripped ------------------------------------------
    payload_a = response_to_payload(resp, include_replay=True)
    assert payload_a["transport_mode"] == "CANONICAL_VERIFIED"
    payload_a["ranked_route_dossiers"][idx]["replay_payload"] = None  # compare=False -> result_digest unaffected
    real_refuses_a = False
    try:
        response_from_payload(payload_a)
    except ValueError:
        real_refuses_a = True
    with _patch(svc.CompilationResponse, "_check_readiness_coherence", lambda self, **kw: None):
        try:
            response_from_payload(payload_a)
            mutant_loads_a = True
        except ValueError:
            mutant_loads_a = False

    # -- part (b): the carried readiness is FORGED upward on a route whose replay is left UNTOUCHED (so
    # route_digest still matches -- this is the readiness-specific MISMATCH branch of the re-derivation, not
    # the "reconstructs to a different route" digest bind M10 already exercises for a stripped/substituted
    # replay). Pick a real route that is NOT already PROCESS_SPECIFIED and forge every step's per_step
    # obligations (including process/workup_isolation) to SATISFIED -- its actual (unmodified) replayed
    # procedure evidence does not support that claim, so re-derivation disagrees.
    idx_b = next(
        (i for i, r in enumerate(resp.ranked_route_dossiers) if r.readiness.tier != PROCESS_SPECIFIED), None,
    )
    if idx_b is None:
        raise AssertionError("expected a real NON-PROCESS_SPECIFIED isopentyl acetate route to forge upward")
    orig_b = resp.ranked_route_dossiers[idx_b]
    forged_readiness = replace(
        orig_b.readiness,
        per_step=tuple(
            replace(
                sr,
                reaction_type=ObligationStatus.SATISFIED,
                reaction_class_name=sr.reaction_class_name or "forged_class",
                conditions=ObligationStatus.SATISFIED,
                process=ObligationStatus.SATISFIED,
                workup_isolation=ObligationStatus.SATISFIED,
                provenance=("https://doi.org/10.1000/forged-m12",),
                open_obligations=(),
            )
            for sr in orig_b.readiness.per_step
        ),
    )
    forged_b = replace(orig_b, readiness=forged_readiness)
    dossiers_b = list(resp.ranked_route_dossiers)
    dossiers_b[idx_b] = forged_b
    resp_b = replace(resp, ranked_route_dossiers=tuple(dossiers_b))
    payload_b = response_to_payload(resp_b, include_replay=True)
    real_refuses_b = False
    try:
        response_from_payload(payload_b)
    except ValueError:
        real_refuses_b = True
    with _patch(svc.CompilationResponse, "_check_readiness_coherence", lambda self, **kw: None):
        try:
            response_from_payload(payload_b)
            mutant_loads_b = True
        except ValueError:
            mutant_loads_b = False

    return real_refuses_a and mutant_loads_a and real_refuses_b and mutant_loads_b


@mutant("M13 a-declared-unsourced-workup-must-not-count-as-satisfied")
def m13() -> bool:
    """A workup field genuinely PRESENT (the source describes it) but the procedure's own `source` is stripped
    (unsourced) must not count as `workup_isolation=SATISFIED` -- sourcing is a mandatory conjunct on BOTH the
    process and the workup axis (plan D4), never just process."""
    base = _isopentyl_step_process_specified()
    step = _with_procedure(base, source=None)
    real_sr = evaluate_step(step)
    real_ok = (
        real_sr.workup_isolation is ObligationStatus.UNSATISFIED
        and step.envelope.procedure.workup_isolation.status is EvidenceFieldStatus.PRESENT
    )
    real_obligations = readiness._process_and_workup_obligations

    def mutant_obligations(step):  # BUG: workup ignores the sourcing conjunct -- PRESENT alone is SATISFIED
        procedure = step.envelope.procedure
        if procedure is not None and procedure.workup_isolation.status is EvidenceFieldStatus.PRESENT:
            process_status, _workup, locator, obligations = real_obligations(step)
            return process_status, ObligationStatus.SATISFIED, locator, obligations
        return real_obligations(step)

    with _patch(readiness, "_process_and_workup_obligations", mutant_obligations):
        mutant_bad = evaluate_step(step).workup_isolation is ObligationStatus.SATISFIED
    return real_ok and mutant_bad


@mutant("M14 legacy-process-workup-included-bool-must-not-satisfy-workup")
def m14() -> bool:
    """The legacy `ProcessRequirements.workup_included` boolean must NEVER be read as workup evidence -- the
    Round-II axis reads ONLY `envelope.procedure.workup_isolation`. A step with NO procedure at all but a
    legacy `process.workup_included=True` must stay UNKNOWN, never SATISFIED (let alone PROCESS_SPECIFIED)."""
    legacy_process = ProcessRequirements(workup_included=True, provenance="hand-built legacy workup=True probe")
    env = ConditionEnvelope(
        medium="hand-built test medium", status=EvidenceStatus.EXPERIMENTAL,
        provenance="hand-built, declared, sourced envelope with a legacy process block but NO ProcedureEvidence",
        source=SourceCitation("https://doi.org/10.1000/hand-built-m14", SourceReview.ACCEPTED),
        process=legacy_process,
    )
    step = _identity_step(env)
    real_sr = evaluate_step(step)
    real_ok = real_sr.process is ObligationStatus.UNKNOWN and real_sr.workup_isolation is ObligationStatus.UNKNOWN
    real_obligations = readiness._process_and_workup_obligations

    def mutant_obligations(step):  # BUG: legacy process.workup_included=True alone satisfies workup (and process)
        legacy = step.envelope.process
        if step.envelope.procedure is None and legacy is not None and legacy.workup_included:
            return ObligationStatus.SATISFIED, ObligationStatus.SATISFIED, "legacy-workup-included-surrogate", ()
        return real_obligations(step)

    with _patch(readiness, "_process_and_workup_obligations", mutant_obligations):
        mutant_sr = evaluate_step(step)
    mutant_bad = (
        mutant_sr.process is ObligationStatus.SATISFIED and mutant_sr.workup_isolation is ObligationStatus.SATISFIED
    )
    return real_ok and mutant_bad


@mutant("M15 a-missing-whole-procedure-field-must-not-be-silently-complete")
def m15() -> bool:
    """A whole-procedure field left genuinely `UNKNOWN_MISSING` (the source is silent on purification) must
    block completeness -- a predicate that skips checking one field in `WHOLE_PROCEDURE_FIELDS` silently treats
    a real representational gap as complete (plan M15's 'missing operation / gap' failure mode, realized here as
    the field-loop being skipped rather than an ordinal gap, since `ProcedureEvidence.__post_init__` already
    structurally forbids constructing a non-contiguous-ordinal procedure -- the loop-skip is the reachable
    equivalent of that same bug)."""
    base = _isopentyl_step_process_specified()
    step = _with_procedure(base, purification=EvidenceField.unknown())
    real_ok = evaluate_step(step).process is ObligationStatus.UNSATISFIED

    def mutant_complete(evidence) -> bool:  # BUG: skips the "purification" field in the whole-procedure loop
        from smartchem.procedure_evidence import EvidenceFieldStatus as _S
        if evidence is None or evidence.unresolved_omissions or not evidence.operations:
            return False
        for name in readiness.WHOLE_PROCEDURE_FIELDS:
            if name == "purification":
                continue  # the skipped field -- the bug
            if getattr(evidence, name).status is _S.UNKNOWN_MISSING:
                return False
        return True

    with _patch(readiness, "procedure_representation_is_complete", mutant_complete):
        mutant_bad = evaluate_step(step).process is ObligationStatus.SATISFIED
    return real_ok and mutant_bad


@mutant("M16 free-text-provenance-must-not-be-parsed-into-a-structured-operation")
def m16() -> bool:
    """`evidence_scope` (explicitly documented as "NEVER read by the predicate") must stay dead prose even when
    it describes exactly the missing fact -- a mutant that scans it for a keyword and uses that to resolve an
    `UNKNOWN_MISSING` field is inferring structure from free text, which the frozen contract (plan D3) forbids."""
    base = _isopentyl_step_process_specified()
    step = _with_procedure(
        base, quench=EvidenceField.unknown(),
        evidence_scope="quench: not needed -- the acid catalyst is fully consumed/removed downstream",
    )
    real_ok = evaluate_step(step).process is ObligationStatus.UNSATISFIED
    real_complete = readiness.procedure_representation_is_complete

    def mutant_complete(evidence) -> bool:  # BUG: infers "quench" resolved by scanning evidence_scope prose
        if evidence is not None and evidence.quench.status.value == "UNKNOWN_MISSING" and (
            "quench" in evidence.evidence_scope.lower()
        ):
            evidence = replace(
                evidence,
                quench=EvidenceField.not_applicable(evidence.reaction_scope, "inferred from evidence_scope prose"),
            )
        return real_complete(evidence)

    with _patch(readiness, "procedure_representation_is_complete", mutant_complete):
        mutant_bad = evaluate_step(step).process is ObligationStatus.SATISFIED
    return real_ok and mutant_bad


@mutant("M17 the-envelopes-conditions-source-must-not-source-the-procedure")
def m17() -> bool:
    """The isopentyl envelope carries an accepted CONDITIONS source AND the procedure carries its OWN accepted
    source; stripping the procedure's source ALONE (the envelope's stays accepted) must demote `process` --
    the procedure's sourcing is never allowed to piggyback on the enclosing envelope's (plan D4 / Lane F KILL 1)."""
    base = _isopentyl_step_process_specified()
    step = _with_procedure(base, source=None)
    real_ok = (
        step.envelope.is_sourced  # the envelope's OWN conditions source is untouched, still accepted
        and not step.envelope.procedure.is_sourced
        and evaluate_step(step).process is ObligationStatus.UNSATISFIED
    )
    real_obligations = readiness._process_and_workup_obligations

    def mutant_obligations(step):  # BUG: an unsourced procedure borrows the enclosing envelope's source instead
        procedure = step.envelope.procedure
        if procedure is not None and not procedure.is_sourced and step.envelope.is_sourced:
            complete = readiness.procedure_representation_is_complete(procedure)
            if complete:
                locator = step.envelope.source.locator
                return ObligationStatus.SATISFIED, ObligationStatus.SATISFIED, locator, ()
        return real_obligations(step)

    with _patch(readiness, "_process_and_workup_obligations", mutant_obligations):
        mutant_bad = evaluate_step(step).process is ObligationStatus.SATISFIED
    return real_ok and mutant_bad


@mutant("M18 process-specified-must-not-ignore-workup-completeness")
def m18() -> bool:
    """Assert DIRECTLY on `StepReadiness.tier` (Wave A Lane E): `_check_readiness_coherence` re-derives with the
    SAME evaluator, so a systematic tier-property mutation would NOT be caught by any round-trip/byte-equality
    check -- only a direct assertion on the derivation catches it. `process=SATISFIED` + `workup_isolation=
    UNSATISFIED` must stay capped at `CONDITIONS_SUPPORTED`; a tier property that drops the workup gate reaches
    `PROCESS_SPECIFIED` regardless."""
    sr = StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED, reaction_type=ObligationStatus.SATISFIED,
        reaction_class_name="hand-built class", conditions=ObligationStatus.SATISFIED,
        process=ObligationStatus.SATISFIED, workup_isolation=ObligationStatus.UNSATISFIED,
        provenance=("https://doi.org/10.1000/hand-built-m18",),
        open_obligations=("workup_isolation: workup/isolation described but not backed by an accepted source citation",),
    )
    real_ok = sr.tier == CONDITIONS_SUPPORTED

    def mutant_tier(self) -> str:  # BUG: the workup/isolation gate is dropped from the final rung
        if self.reaction_type is not ObligationStatus.SATISFIED:
            return FORMAL_CANDIDATE
        if self.conditions is not ObligationStatus.SATISFIED:
            return REACTION_VOUCHED
        if self.process is not ObligationStatus.SATISFIED:
            return CONDITIONS_SUPPORTED
        return PROCESS_SPECIFIED

    with _patch(StepReadiness, "tier", property(mutant_tier)):
        mutant_bad = sr.tier == PROCESS_SPECIFIED
    return real_ok and mutant_bad


@mutant("M19 a-same-formula-isomer-must-not-borrow-procedure-evidence")
def m19() -> bool:
    """M9's isomer probe, extended to the `process`/`workup_isolation` axes specifically (not just
    `conditions`): the live 4-aminophenyl-acetate negative-control route must show `process`/`workup_isolation`
    UNKNOWN on every step (no procedure attached at all off the structurally-guarded `assembly_conditions`
    path) -- the SAME dropped-name-guard mutant M9 uses (paracetamol's OWN record, envelope AND its attached
    `ProcedureEvidence`, served to the isomer purely because the formula-only `_reaction_signature` collides)
    must leak the procedure axes too, not just conditions."""
    req = build_recompile_request(
        "4-aminophenyl acetate", input_kind=InputKind.NAME, helper_reagents=("water", "acetic acid"),
        stock_materials=("4-aminophenol",), max_depth=2,
    )
    resp = run_compilation(req)
    honest = tuple(
        (sr.process, sr.workup_isolation) for r in resp.ranked_route_dossiers for sr in r.readiness.per_step
    )
    real_ok = len(honest) > 0 and all(
        proc is ObligationStatus.UNKNOWN and workup is ObligationStatus.UNKNOWN for proc, workup in honest
    )

    def mutant_assembly_conditions(capped, *, losses=()):  # BUG: the name-guard is dropped (same as M9)
        from smartchem.identity import is_blocked
        from smartchem.structure import resolve_structure
        if is_blocked(tuple(losses), "conditions"):
            return dc.ConditionEnvelope.unknown()
        record = dc.SEED_CONDITIONS.get(dc._reaction_signature(capped.forget()))
        if record is None or dc.ReactionDirection.ASSEMBLY not in record.directions:
            return dc.ConditionEnvelope.unknown()
        target = resolve_structure(capped.reactant)
        precursors = tuple(resolve_structure(m) for m in capped.products)
        if target is None or any(p is None for p in precursors):
            return dc.ConditionEnvelope.unknown()
        return record.envelope  # the name-guard check that belongs here is simply missing

    with _patch(rt, "assembly_conditions", mutant_assembly_conditions):
        req2 = build_recompile_request(
            "4-aminophenyl acetate", input_kind=InputKind.NAME, helper_reagents=("water", "acetic acid"),
            stock_materials=("4-aminophenol",), max_depth=2,
        )
        resp2 = run_compilation(req2)
        mutated = tuple(
            (sr.process, sr.workup_isolation) for r in resp2.ranked_route_dossiers for sr in r.readiness.per_step
        )
    mutant_bad = any(
        proc is not ObligationStatus.UNKNOWN or workup is not ObligationStatus.UNKNOWN for proc, workup in mutated
    )
    return real_ok and mutant_bad


@mutant("M20 a-fits-process-bench-verdict-must-not-promote-process-completeness")
def m20() -> bool:
    """Assert DIRECTLY on `process`/`tier` (Wave A Lane E, mirroring M18): a `ProcessFitStatus.FITS` bench
    verdict must never substitute for -- or promote -- the SEPARATE literature-procedure completeness axis.
    Fixture: the real declared-but-incomplete isopentyl step (M7's fixture) carries a `FITS` bench-verdict
    probe; the honest evaluator ignores it entirely (`process` stays UNSATISFIED, tier stays capped at
    `CONDITIONS_SUPPORTED`) because readiness never reads `ProcessFitStatus`/`available_equipment`/ΔG at all."""
    step = _isopentyl_step_conditions_supported()  # M7's declared-but-incomplete fixture
    object.__setattr__(step, "_fit_status_probe", "FITS")
    real_sr = evaluate_step(step)
    real_ok = real_sr.process is ObligationStatus.UNSATISFIED and real_sr.tier == CONDITIONS_SUPPORTED
    real_obligations = readiness._process_and_workup_obligations

    def mutant_obligations(step):  # BUG: a FITS bench-verdict probe short-circuits process to SATISFIED
        if getattr(step, "_fit_status_probe", None) == "FITS":
            locator = step.envelope.procedure.source_locator if step.envelope.procedure is not None else None
            return ObligationStatus.SATISFIED, ObligationStatus.SATISFIED, locator, ()
        return real_obligations(step)

    with _patch(readiness, "_process_and_workup_obligations", mutant_obligations):
        mutant_sr = evaluate_step(step)
    mutant_bad = mutant_sr.process is ObligationStatus.SATISFIED and mutant_sr.tier == PROCESS_SPECIFIED
    return real_ok and mutant_bad


def run() -> list:
    results = []
    for name, fn in _MUTANTS:
        try:
            killed = bool(fn())
        except Exception as exc:  # a harness error is a FAILED kill, reported honestly
            killed, name = False, f"{name} [harness-error: {type(exc).__name__}: {exc}]"
        results.append((name, killed))
        print(f"  [{'KILLED' if killed else 'SURVIVED'}] {name}")
    return results


def main() -> int:
    print("v0.8 readiness mutation gate (M1-M20):")
    results = run()
    killed = sum(1 for _, k in results if k)
    print(f"\n{killed}/{len(results)} mutants killed.")
    return 0 if killed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
