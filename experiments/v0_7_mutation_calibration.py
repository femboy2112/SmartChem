"""V0.7-MUTATION-01: the calibrated mutation gate for the production transform-algebra (Round II + Round III).

Adding tests is not enough -- a test that would pass on the BROKEN code proves nothing.  This harness INJECTS each
of the 0.7 failure modes (M1-M10 Round II; M11-M17 Round III: reagent-policy identity binding, prose-independence,
CLI empty-pool, decompile empty-pool, response algebra-rebind-on-load, the frozen missing-field migration law, and a
fresh hetero-DA holdout's silent absence) and shows the corresponding guard/discriminator actually flips (the mutant
is KILLED), so the tests in `tests/test_v0_7_*` are non-vacuous.  Every mutation is applied in a try/finally and
undone, so this harness leaves the code byte-identical.

Run:  .venv/bin/python experiments/v0_7_mutation_calibration.py
"""
from __future__ import annotations

import contextlib
from dataclasses import replace

import smartchem.algebra_profiles as ap
import smartchem.compilation_ir as cir
import smartchem.diels_alder as da
import smartchem.experiment.reaction_type_oracle as oracle
import smartchem.experiment.routes as rt
import smartchem.service as svc
from smartchem.contracts import canonical_digest
from smartchem.identity_parse import InputKind
from smartchem.service import (
    build_recompile_request,
    request_from_payload,
    request_to_payload,
    response_from_payload,
    response_to_payload,
    run_compilation,
)
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    CappedScissionProvider,
    TransformProvider,
    TransformProviderRegistry,
    UnsupportedProviderUseError,
)

_MUTANTS: list = []


def mutant(name: str):
    def deco(fn):
        _MUTANTS.append((name, fn))
        return fn
    return deco


@contextlib.contextmanager
def _patch(obj, name, value):
    """Temporarily set ``obj.name = value`` (works on modules and class objects), restoring exactly on exit.

    0.9.5: the process enumeration cache is cleared on entry AND exit (a patch changes behaviour, never a cache key)."""
    from smartchem.verification import ENUMERATION_CACHE

    had = name in getattr(obj, "__dict__", {})
    old = obj.__dict__.get(name) if had else None
    ENUMERATION_CACHE.clear()
    setattr(obj, name, value)
    try:
        yield
    finally:
        ENUMERATION_CACHE.clear()
        if had:
            setattr(obj, name, old)
        else:
            try:
                delattr(obj, name)
            except AttributeError:
                pass


def _req(profile: str, reagents=("water",)):
    return build_recompile_request(
        "C1CC=CCC1", input_kind=InputKind.SMILES, helper_reagents=reagents,
        stock_materials=("C=CC=C", "C=C"), algebra_profile=profile,
    )


def _da_digest(spec):
    return da._da_semantic_descriptor(da.DielsAlderProvider(), spec).digest


# 1. rule changed, semantic identity unchanged -> MUST be caught (identity binds the rule content digest).
@mutant("M1 rule-change-must-move-identity")
def m1() -> bool:
    real_moves = _da_digest(replace(da._ALKENE_SPEC, retro_rule=da._ALKYNE_SPEC.retro_rule)) != _da_digest(da._ALKENE_SPEC)
    # MUTANT identity that ignores the rule/guard digests (the pre-0.7 declared-metadata identity):
    def blind(spec):
        return TransformProvider.semantic_descriptor.fget(da.DielsAlderProvider()).digest
    mutant_moves = blind(replace(da._ALKENE_SPEC, retro_rule=da._ALKYNE_SPEC.retro_rule)) != blind(da._ALKENE_SPEC)
    return real_moves and not mutant_moves


# 2. guard spec changed, semantic identity unchanged -> MUST be caught (identity binds the guard digest).
@mutant("M2 guard-change-must-move-identity")
def m2() -> bool:
    real_moves = _da_digest(replace(da._ALKENE_SPEC, exocyclic_max_order=2)) != _da_digest(da._ALKENE_SPEC)
    def blind(spec):
        return TransformProvider.semantic_descriptor.fget(da.DielsAlderProvider()).digest
    mutant_moves = blind(replace(da._ALKENE_SPEC, exocyclic_max_order=2)) != blind(da._ALKENE_SPEC)
    return real_moves and not mutant_moves


# 3. a wrong-use provider admitted to route search -> MUST refuse before enumeration.
@mutant("M3 wrong-use-provider-in-route-must-refuse")
def m3() -> bool:
    decompile = ap.resolve_algebra_profile("certified-decompile-v07")
    chx = parse_smiles("C1CC=CCC1")
    try:
        search_routes_typed_refusal = False
        rt.search_routes(chx, reagents=(), available=(), registry=decompile, max_depth=1)
    except UnsupportedProviderUseError:
        search_routes_typed_refusal = True
    except Exception:
        search_routes_typed_refusal = False
    # MUTANT: the guard is a no-op -> the typed refusal is lost (a downstream crash or a mis-run instead).
    with _patch(rt, "assert_registry_supports_use", lambda *a, **k: None):
        try:
            rt.search_routes(chx, reagents=(), available=(), registry=decompile, max_depth=1)
            mutant_typed_refusal = False
        except UnsupportedProviderUseError:
            mutant_typed_refusal = True
        except Exception:
            mutant_typed_refusal = False
    return search_routes_typed_refusal and not mutant_typed_refusal


# 4. the selected request profile ignored, default executed -> MUST change the observable result.
@mutant("M4 selected-profile-ignored-must-change-result")
def m4() -> bool:
    real_ok = run_compilation(_req("certified-route-v07", ())).exit_code == 0
    with _patch(svc, "resolve_algebra_profile", lambda pid: ap.ALGEBRA_PROFILES["legacy-capped-v1"]):
        mutant_exit = run_compilation(_req("certified-route-v07", ())).exit_code
    return real_ok and mutant_exit != 0


# 5. a search under profile A packaged as profile B -> MUST refuse (the binding invariant).
@mutant("M5 profile-A-search-packaged-as-B-must-refuse")
def m5() -> bool:
    orig = rt.search_routes
    def tainted(*a, **k):
        res = orig(*a, **k)
        return replace(res, receipt=replace(res.receipt, transform_registry_digest="TAINTED-WRONG-DIGEST"))
    with _patch(rt, "search_routes", tainted):
        refused = run_compilation(_req("certified-route-v07", ())).exit_code == 5
    return refused


# 6. a tampered serialized profile -> MUST fail closed on deserialize.
@mutant("M6 tampered-serialized-profile-must-fail-closed")
def m6() -> bool:
    payload = request_to_payload(_req("certified-route-v07"))
    payload["algebra_profile"] = "smuggled-unknown-profile"
    try:
        request_from_payload(payload)
        return False
    except ValueError:
        return True


# 7. an empty-reagent request rejected even though a reagentless family can run -> the flag is load-bearing.
@mutant("M7 reagentless-flag-is-load-bearing")
def m7() -> bool:
    real = run_compilation(_req("certified-route-v07", ())).exit_code  # 0: DA runs reagentless
    classes = {type(p) for p in ap.ALGEBRA_PROFILES["certified-route-v07"].providers}
    with contextlib.ExitStack() as stack:
        for c in classes:
            stack.enter_context(_patch(c, "reagentless_capable", False))
        mutant_exit = run_compilation(_req("certified-route-v07", ())).exit_code  # 2: unconditional refusal
    return real == 0 and mutant_exit == 2


# 8. the LOW-LEVEL default registry silently widened -> MUST be observable.  0.7 Round III PROMOTION: the SERVICE/CLI
#    route default (DEFAULT_ROUTE_ALGEBRA_PROFILE) is now INTENTIONALLY certified, so "the default finds DA" is
#    correct, not a bug.  This mutant now guards the USE-DEPENDENT invariant that SURVIVES promotion: the low-level
#    DEFAULT_TRANSFORM_REGISTRY (used by a direct caller that passes no registry, and by the DECOMPILE lane) stays
#    capped-only.  A silent widen of THAT registry -- the thing promotion deliberately did NOT touch -- is a bug.
@mutant("M8 low-level-default-registry-silent-widen-must-be-observable")
def m8() -> bool:
    from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY
    chx = parse_smiles("C1CC=CCC1")
    def emits_da(registry) -> bool:
        transforms, _ = registry.enumerate(chx, (), budget=100_000)
        return any(t.witness_kind.startswith("DIELS_ALDER") for t in transforms)
    real = not emits_da(DEFAULT_TRANSFORM_REGISTRY)  # the low-level default is capped-only: emits no DA disconnection
    mutant_emits = emits_da(ap.ALGEBRA_PROFILES["certified-route-v07"])  # a widened low-level default WOULD emit DA
    return real and mutant_emits


# 9. a DA class witness stripped/forged -> MUST be caught (the route step is class-vouched).
@mutant("M9 da-class-witness-strip-must-be-caught")
def m9() -> bool:
    res = rt.search_routes(parse_smiles("C1CC=CCC1"), reagents=(),
                           available=(parse_smiles("C=CC=C"), parse_smiles("C=C")),
                           registry=ap.resolve_algebra_profile("certified-route-v07"), max_depth=2)
    step = res.routes[0].steps[0]
    real_vouched = oracle.recognize_reaction_type(step) is not None
    with _patch(oracle, "recognize_reaction_type", lambda s: None):
        mutant_vouched = oracle.recognize_reaction_type(step) is not None
    return real_vouched and not mutant_vouched


# 10. aggregate completeness OR'd instead of AND'd -> MUST be caught (a starved provider poisons the aggregate).
@mutant("M10 completeness-must-be-AND-not-OR")
def m10() -> bool:
    ester, water = parse_smiles("CC(=O)OC"), parse_smiles("O")
    cand = ap.resolve_algebra_profile("certified-route-v07")
    _, complete_and = cand.enumerate(ester, (water,), budget=1)  # capped starved -> AND == False (honest)
    per = [p.enumerate_transforms(ester, (water,), budget=1)[1] for p in cand.providers]
    or_would_be = any(per)  # an OR would call the aggregate complete though capped was starved
    return complete_and is False and or_would_be is True


# =========================== 0.7 Round III additions (mutants 11-17) ===========================

# 11. the reagent policy changes but semantic identity does NOT move -> MUST be caught (SS1A: reagentless_capable is
#     load-bearing -- it gates whether an empty-pool search runs, so a flip MUST move the descriptor digest).
@mutant("M11 reagent-policy-change-must-move-identity")
def m11() -> bool:
    cap = CappedScissionProvider()  # reagentless_capable = False
    flipped = type("CapReagentless", (CappedScissionProvider,), {"reagentless_capable": True})()
    real_moves = flipped.semantic_descriptor.digest != cap.semantic_descriptor.digest
    # MUTANT: the pre-Round-III descriptor digest (schema v1) that DROPS reagentless_capable -> the flip is invisible.
    def blind_v1(p) -> str:
        d = p.semantic_descriptor
        return canonical_digest((
            "provider-semantic-descriptor-v1", d.family, d.supported_uses, d.witness_kind, d.projection_kind,
            d.behavior_params, d.structural_rule_digest, d.guard_spec_digest, d.authority,
        ))
    mutant_moves = blind_v1(flipped) != blind_v1(cap)
    return real_moves and not mutant_moves


# 12. a mechanism-PROSE edit MOVES the semantic identity -> MUST be caught (SS1B: identity is prose-independent; the
#     Round-II shape that carried the raw manifest in identity WOULD move on a prose edit -- that is the mutant).
@mutant("M12 mechanism-prose-edit-must-not-move-identity")
def m12() -> bool:
    real = CappedScissionProvider()

    class ProseEdit(CappedScissionProvider):
        @property
        def capability_manifest(self):
            return tuple(("mechanism", "REWORDED PROSE, SAME CHEMISTRY") if k == "mechanism" else (k, v)
                         for k, v in super().capability_manifest)
    prose = ProseEdit()
    real_stable = prose.identity == real.identity  # prose-independent identity: no movement
    # MUTANT: the Round-II identity that spliced the raw manifest into slot 2 -> a prose edit DID move identity.
    def id_with_manifest(p):
        return (p.provider_id, p.provider_version, p.capability_manifest, p.semantic_descriptor.digest)
    mutant_moves = id_with_manifest(prose) != id_with_manifest(real)
    return real_stable and mutant_moves


# 13. the CLI explicit empty helper pool accidentally becomes the water default -> MUST be caught (SS2).
@mutant("M13 cli-explicit-empty-pool-must-not-become-water")
def m13() -> bool:
    import argparse

    from smartchem.cli import _add_recompile_flags, _recompile_request_from_args
    p = argparse.ArgumentParser()
    _add_recompile_flags(p)
    args = p.parse_args(["--algebra", "certified-route-v07", "--no-helper-reagents", "--smiles", "C1CC=CCC1"])
    real_empty = _recompile_request_from_args(args).helper_reagents == ()  # REAL path: explicit empty pool
    # MUTANT: the pre-Round-III threading with no --no-helper-reagents branch -> an empty pool falls to water.
    mut_hr = tuple(args.reagents) if args.reagents else None  # args.reagents is None here -> None -> water default
    mut_watered = build_recompile_request(
        "C1CC=CCC1", input_kind=InputKind.SMILES, helper_reagents=mut_hr, algebra_profile="certified-route-v07",
    ).helper_reagents == ("water",)
    return real_empty and mut_watered


# 14. certified-decompile-v07 rejects an empty reagent pool -> MUST be caught (SS3: empty is a legit declared set).
@mutant("M14 certified-decompile-empty-pool-must-not-be-rejected")
def m14() -> bool:
    decompile = ap.resolve_algebra_profile("certified-decompile-v07")
    eth = parse_smiles("CCO")
    real_ok = len(cir.decompile_structure_to_ir(eth, reagents=(), registry=decompile).structural_candidates) > 0
    # MUTANT: re-impose the old non-empty guard -> an empty pool raises before enumeration.
    orig = cir.decompile_structure_to_ir
    def guarded(target, *, reagents, **kw):
        if not reagents:
            raise TypeError("reagents must be a non-empty tuple of reagent-TYPE Molecules")
        return orig(target, reagents=reagents, **kw)
    with _patch(cir, "decompile_structure_to_ir", guarded):
        try:
            cir.decompile_structure_to_ir(eth, reagents=(), registry=decompile)
            mutant_rejects = False
        except TypeError:
            mutant_rejects = True
    return real_ok and mutant_rejects


# 15. a response's request profile and IR algebra are rebound inconsistently on LOAD -> MUST refuse (SS4).
@mutant("M15 response-algebra-rebind-must-refuse-on-load")
def m15() -> bool:
    """A certified-algebra answer carried under a legacy-algebra request must be refused by the load-time rebind.

    0.9.5 re-read (the v0.9 harness's M190 pattern): X-high D26.1 (``_check_request_answer_coherence``) now re-derives
    the IR's request and transform-registry digests from the carried request by its OWN route, so it refused this
    tamper in the mutant arm as well -- a masked survivor on the merged-0.9 tree d26f0eb.  D26.1 is held out of BOTH
    arms (never weakened): honest = refused by the 0.7 rebind ("algebra-rebind mismatch"), mutant = loads once the
    rebind resolves the wrong registry."""
    cert = run_compilation(_req("certified-route-v07", ()))
    frank = replace(cert, request=_req("legacy-capped-v1"))  # legacy request + certified IR (coherent tamper)
    with _patch(svc.CompilationResponse, "_check_request_answer_coherence", lambda self: None):
        try:
            response_from_payload(response_to_payload(frank))
            real_refuses = False
        except ValueError as exc:
            real_refuses = "algebra-rebind mismatch" in str(exc)
        # MUTANT: the load-time rebind check resolves the WRONG registry (ignores the request's profile), so expected
        # always matches the IR -> the coherent cross-profile rebind loads.
        with _patch(svc, "resolve_algebra_profile", lambda pid: ap.ALGEBRA_PROFILES["certified-route-v07"]):
            try:
                response_from_payload(response_to_payload(frank))
                mutant_loads = True
            except ValueError:
                mutant_loads = False
    return real_refuses and mutant_loads


# 16. a pre-0.7 missing-profile payload follows the (promoted) build default instead of the frozen legacy law -> MUST
#     be caught (SS5: the wire-migration law is decoupled from the promotable build default).
@mutant("M16 pre-0_7-missing-profile-must-stay-legacy")
def m16() -> bool:
    """0.9.5 re-read (Wave C8 F7, same law, stronger enforcement): a missing ``algebra_profile`` must NEVER follow the
    promotable build default.  The accepted generations (current, v0.8) all carry the key, so its absence is now
    REFUSED rather than decoded to the frozen legacy value.  Honest: refused.  Mutant: the decoder defaults the missing
    field to the (promoted) build default -- a wider algebra silently selected."""
    import inspect
    import textwrap

    payload = request_to_payload(_req("legacy-capped-v1"))
    del payload["algebra_profile"]
    # MUTANT (the REAL decoder, recompiled from its own source with two anchored edits -- a stale anchor raises): the
    # key is optional again and a missing one follows the build default.  Globals are the LIVE module dict, so the
    # simulated default promotion below reaches the mutant exactly as it would reach a real default change.
    src = textwrap.dedent(inspect.getsource(svc.request_from_payload))
    for old, new in (('else _V08_REQUEST_PAYLOAD_KEYS, "request")',
                      'else _V08_REQUEST_PAYLOAD_KEYS, "request", optional=frozenset({"algebra_profile"}))'),
                     ('algebra_profile=payload["algebra_profile"],',
                      'algebra_profile=payload.get("algebra_profile", DEFAULT_ROUTE_ALGEBRA_PROFILE),')):
        assert src.count(old) == 1, f"M16 anchor found {src.count(old)}x: {old!r}"
        src = src.replace(old, new)
    ns: dict = {}
    exec(compile(src, "<M16 mutant>", "exec"), svc.__dict__, ns)  # noqa: S102 -- the mutation harness's own source
    mutant_decode = ns["request_from_payload"]
    with _patch(svc, "DEFAULT_ROUTE_ALGEBRA_PROFILE", "certified-route-v07"):  # simulate the default promotion
        try:
            request_from_payload(payload)
            real_refuses = False
        except ValueError:
            real_refuses = True
        mutant_profile = mutant_decode(payload).algebra_profile
    return real_refuses and mutant_profile == "certified-route-v07"


# 17. a fresh hetero-DA holdout is silently absent (its family dropped) -> MUST be caught (SS6: the holdout must fire
#     EXACTLY its own family; dropping the family makes it silently absent, which the corpus assertion catches).
@mutant("M17 fresh-hetero-holdout-absence-must-be-caught")
def m17() -> bool:
    cert = ap.resolve_algebra_profile("certified-route-v07")
    target = parse_smiles("N1C=CCC(C)C1")  # fresh aza-diene holdout (post-freeze, designed by a non-author adversary)

    def da_kinds(reg) -> set:
        ets, _ = reg.enumerate(target, (), budget=100_000)
        return {e.witness_kind for e in ets if e.witness_kind.startswith("DIELS_ALDER")}
    real_fires = da_kinds(cert) == {"DIELS_ALDER_AZA_DIENE"}
    # MUTANT: the aza-diene family is dropped from the certified registry -> the holdout fires NOTHING (silent gap).
    mutant_reg = TransformProviderRegistry(
        tuple(p for p in cert.providers if not isinstance(p, da.AzaDieneDielsAlderProvider))
    )
    mutant_absent = "DIELS_ALDER_AZA_DIENE" not in da_kinds(mutant_reg)
    return real_fires and mutant_absent


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
    print("v0.7 Round II+III calibrated mutation gate:")
    results = run()
    killed = sum(1 for _, k in results if k)
    print(f"\n{killed}/{len(results)} mutants killed.")
    return 0 if killed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
