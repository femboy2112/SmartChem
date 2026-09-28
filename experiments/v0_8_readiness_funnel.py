"""V0.8-FUNNEL-01: the permanent 1.0 readiness funnel over the forcing corpus (plan Sec 9/10.2).

The stage law (Sec 4, cumulative): `formal route candidate -> every step reaction-vouched -> every step
conditions-supported -> every step process-specified`. This is a WEAKEST-LINK funnel: a route only survives a
stage if EVERY one of its steps clears that stage (never an "any step is enough" OR -- Sec 4's
`min_tier`/`route_reaction_type_blockers` law). Per-step and per-route denominators are kept SEPARATE and
BOTH reported, because they answer different questions ("how many individual obligations are discharged"
vs "how many complete routes clear the bar").

A shrinking denominator downstream is the EXPECTED, HONEST shape of this funnel -- it measures evidence
coverage, not a target to hit 100% on. As of Round II, `process-specified` is no longer universally dark:
`procedure_representation_is_complete` (renamed from the old `process_representation_is_complete`, and now
reading `step.envelope.procedure` -- a typed `ProcedureEvidence`, not the legacy `process`) is honestly
satisfiable, and the isopentyl-acetate route (full sourced preparative procedure) is expected to light it
up. So this harness no longer pins that stage at zero -- it asserts the honestly-measured floor (>= 1) and
lets the real count speak, still monotone-checked against the stages above it.

Run:  .venv/bin/python experiments/v0_8_readiness_funnel.py
"""
from __future__ import annotations

from pathlib import Path

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.experiment.readiness import (
    CONDITIONS_SUPPORTED,
    FORMAL_CANDIDATE,
    PROCESS_SPECIFIED,
    REACTION_VOUCHED,
    ObligationStatus,
    evaluate_route,
)
from smartchem.experiment.routes import search_routes
from smartchem.identity_parse import InputKind
from smartchem.service import build_recompile_request, run_compilation
from smartchem.smiles import parse_smiles

_ARTIFACT = Path(__file__).with_name("RESULTS_v0_8_readiness_funnel.md")

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

#: the funnel's four cumulative stages, in order (Sec 4's total order -- FORMAL_CANDIDATE always clears, so
#: it is the funnel's top rather than a filtered stage).
_STAGES = (FORMAL_CANDIDATE, REACTION_VOUCHED, CONDITIONS_SUPPORTED, PROCESS_SPECIFIED)


def _corpus_readinesses() -> list:
    """Every `RouteReadiness` across the Sec 9 forcing corpus, through the promoted default algebra (the
    service front door for named targets; direct `search_routes` for the bare-SMILES retro-DA row)."""
    readinesses = []

    da_result = search_routes(
        parse_smiles("C1CC=CCC1"), reagents=(),
        available=(parse_smiles("C=CC=C"), parse_smiles("C=C")), max_depth=2, registry=_CERTIFIED,
    )
    readinesses += [evaluate_route(route) for route in da_result.routes]

    named = (
        ("paracetamol", ("water", "acetic acid"), ("4-aminophenol",), 2),
        ("aspirin", ("water", "acetic acid"), ("salicylic acid",), 2),
        ("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3),
        ("methyl salicylate", ("water", "methanol"), ("salicylic acid",), 1),
        ("4-aminophenyl acetate", ("water", "acetic acid"), ("4-aminophenol",), 2),
    )
    for target, reagents, have, depth in named:
        req = build_recompile_request(
            target, input_kind=InputKind.NAME, helper_reagents=reagents, stock_materials=have, max_depth=depth,
        )
        resp = run_compilation(req)
        readinesses += [s.readiness for s in resp.ranked_route_dossiers]

    # row 6: aspirin, build-default helper reagent (omit helper_reagents -> service default "water" only).
    req = build_recompile_request(
        "aspirin", input_kind=InputKind.NAME, stock_materials=("salicylic acid",), max_depth=2,
    )
    resp = run_compilation(req)
    readinesses += [s.readiness for s in resp.ranked_route_dossiers]

    return readinesses


def _step_clears(step_readiness, stage: str) -> bool:
    """Whether ONE step clears `stage` -- reading the same cumulative obligations `StepReadiness.tier` does,
    without calling `.tier` itself (so this funnel is an independent re-check of the same law, not a second
    copy of it dressed up as a check)."""
    if stage == FORMAL_CANDIDATE:
        return step_readiness.formal_candidate is ObligationStatus.SATISFIED
    if stage == REACTION_VOUCHED:
        return step_readiness.reaction_type is ObligationStatus.SATISFIED
    if stage == CONDITIONS_SUPPORTED:
        return step_readiness.reaction_type is ObligationStatus.SATISFIED and (
            step_readiness.conditions is ObligationStatus.SATISFIED
        )
    if stage == PROCESS_SPECIFIED:
        return (
            step_readiness.reaction_type is ObligationStatus.SATISFIED
            and step_readiness.conditions is ObligationStatus.SATISFIED
            and step_readiness.process is ObligationStatus.SATISFIED
            and step_readiness.workup_isolation in (
                ObligationStatus.SATISFIED, ObligationStatus.NOT_APPLICABLE,
            )
        )
    raise ValueError(f"unknown stage {stage!r}")


def _route_clears(route_readiness, stage: str) -> bool:
    """A route clears `stage` iff EVERY step does -- weakest-link, never an any-step OR."""
    return all(_step_clears(sr, stage) for sr in route_readiness.per_step)


def compute_funnel(readinesses: list) -> dict:
    per_route = {}
    per_step = {}
    total_routes = len(readinesses)
    total_steps = sum(len(rr.per_step) for rr in readinesses)
    for stage in _STAGES:
        per_route[stage] = sum(1 for rr in readinesses if _route_clears(rr, stage))
        per_step[stage] = sum(1 for rr in readinesses for sr in rr.per_step if _step_clears(sr, stage))
    return {"total_routes": total_routes, "total_steps": total_steps, "per_route": per_route, "per_step": per_step}


def check(results: list, name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def run() -> tuple[list, dict]:
    readinesses = _corpus_readinesses()
    funnel = compute_funnel(readinesses)
    r: list = []

    check(
        r, "corpus non-empty", funnel["total_routes"] > 0 and funnel["total_steps"] > 0,
        f"{funnel['total_routes']} routes, {funnel['total_steps']} steps",
    )
    # Stage 1 (FORMAL_CANDIDATE) is the funnel's ceiling: every constructed route/step clears it (a built
    # ExperimentStep already passed its conservation cert -- Sec 4).
    check(
        r, "every route is a formal candidate",
        funnel["per_route"][FORMAL_CANDIDATE] == funnel["total_routes"],
        f"{funnel['per_route'][FORMAL_CANDIDATE]}/{funnel['total_routes']} routes",
    )
    check(
        r, "every step is a formal candidate",
        funnel["per_step"][FORMAL_CANDIDATE] == funnel["total_steps"],
        f"{funnel['per_step'][FORMAL_CANDIDATE]}/{funnel['total_steps']} steps",
    )
    # Monotone non-increasing down the funnel, both denominators: stage[i] (weaker) >= stage[i+1] (stronger).
    for weaker, stronger in zip(_STAGES[:-1], _STAGES[1:]):
        check(
            r, f"per-route funnel monotone: {weaker} >= {stronger}",
            funnel["per_route"][weaker] >= funnel["per_route"][stronger],
            f"{weaker}={funnel['per_route'][weaker]}, {stronger}={funnel['per_route'][stronger]}",
        )
        check(
            r, f"per-step funnel monotone: {weaker} >= {stronger}",
            funnel["per_step"][weaker] >= funnel["per_step"][stronger],
            f"{weaker}={funnel['per_step'][weaker]}, {stronger}={funnel['per_step'][stronger]}",
        )
    # The corpus is FORCED to actually populate the middle two stages (not a vacuous 0/0/0/0 funnel).
    check(
        r, "reaction-vouched stage is populated (corpus forces it)",
        funnel["per_route"][REACTION_VOUCHED] > 0,
        f"{funnel['per_route'][REACTION_VOUCHED]} routes reaction-vouched",
    )
    check(
        r, "conditions-supported stage is populated (corpus forces it)",
        funnel["per_route"][CONDITIONS_SUPPORTED] > 0,
        f"{funnel['per_route'][CONDITIONS_SUPPORTED]} routes conditions-supported",
    )
    # PROCESS_SPECIFIED is now REACHABLE (Round II): at least one route (isopentyl acetate's full sourced
    # preparative procedure) is expected to honestly light it up -- this is the measured floor, not a
    # ceiling; it must never be gamed back down to a hardcoded number.
    check(
        r, "process-specified stage is reachable (Round II: >= 1, no longer pinned dark)",
        funnel["per_route"][PROCESS_SPECIFIED] >= 1 and funnel["per_step"][PROCESS_SPECIFIED] >= 1,
        f"routes={funnel['per_route'][PROCESS_SPECIFIED]}, steps={funnel['per_step'][PROCESS_SPECIFIED]}",
    )
    return r, funnel


def render_markdown(results: list, funnel: dict) -> str:
    lines = [
        "# v0.8 readiness funnel -- the permanent 1.0 stage counts over the forcing corpus",
        "",
        "Generated by `experiments/v0_8_readiness_funnel.py`. Stage law (cumulative, weakest-link over a "
        "route's steps): `formal candidate -> every step reaction-vouched -> every step conditions-supported "
        "-> every step process-specified`. Per-step and per-route denominators are reported SEPARATELY. A "
        "shrinking downstream count is EXPECTED -- this measures evidence coverage, not a target.",
        "",
        "| stage | routes (of {0}) | steps (of {1}) |".format(funnel["total_routes"], funnel["total_steps"]),
        "|---|---|---|",
    ]
    for stage in _STAGES:
        note = " *(reachable, Round II)*" if stage == PROCESS_SPECIFIED else ""
        lines.append(f"| {stage}{note} | {funnel['per_route'][stage]} | {funnel['per_step'][stage]} |")
    lines += [
        "",
        "| property | verdict | detail |",
        "|---|---|---|",
    ]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    passed = sum(1 for _, ok, _ in results if ok)
    lines += [
        "",
        f"**{passed}/{len(results)} properties hold.** "
        + (
            "The funnel is monotone non-increasing on both denominators, the middle stages are genuinely "
            "populated by the forcing corpus (not vacuous), and PROCESS_SPECIFIED is honestly reachable "
            "(>= 1, Round II)."
            if passed == len(results)
            else "A property FAILED -- the funnel is not sound as stated."
        ),
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("v0.8 readiness funnel -- forcing corpus, promoted default algebra:")
    results, funnel = run()
    md = render_markdown(results, funnel)
    _ARTIFACT.write_text(md, encoding="utf-8")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} properties hold. [wrote {_ARTIFACT}]")
    if passed != len(results):
        print("FUNNEL FAILED.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
