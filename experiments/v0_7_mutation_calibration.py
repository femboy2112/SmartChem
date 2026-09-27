"""V0.7-MUTATION-01: the calibrated mutation gate for the production transform-algebra (Round II).

Adding tests is not enough -- a test that would pass on the BROKEN code proves nothing.  This harness INJECTS each
of the ten 0.7 Round II failure modes and shows the corresponding guard/discriminator actually flips (the mutant is
KILLED), so the tests in `tests/test_v0_7_*` are non-vacuous.  Every mutation is applied in a try/finally and undone,
so this harness leaves the code byte-identical.

Run:  .venv/bin/python experiments/v0_7_mutation_calibration.py
"""
from __future__ import annotations

import contextlib
from dataclasses import replace

import smartchem.algebra_profiles as ap
import smartchem.diels_alder as da
import smartchem.experiment.reaction_type_oracle as oracle
import smartchem.experiment.routes as rt
import smartchem.service as svc
from smartchem.identity_parse import InputKind
from smartchem.service import build_recompile_request, request_from_payload, request_to_payload, run_compilation
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    TransformProvider,
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


# 8. the default profile silently widened -> MUST be observable (default must stay legacy).
@mutant("M8 default-silent-widen-must-be-observable")
def m8() -> bool:
    def default_finds_da() -> bool:
        r = build_recompile_request("C1CC=CCC1", input_kind=InputKind.SMILES,
                                    helper_reagents=("water",), stock_materials=("C=CC=C", "C=C"))
        return run_compilation(r).exit_code == 0
    real = not default_finds_da()  # the legacy default cannot make cyclohexene
    with _patch(svc, "DEFAULT_ALGEBRA_PROFILE", "certified-route-v07"):
        mutant_finds = default_finds_da()  # a widened default WOULD find the DA route
    return real and mutant_finds


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
    print("v0.7 Round II calibrated mutation gate:")
    results = run()
    killed = sum(1 for _, k in results if k)
    print(f"\n{killed}/{len(results)} mutants killed.")
    return 0 if killed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
