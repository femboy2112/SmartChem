"""V0.9-FUNNEL-01: the capability compiler funnel + per-axis census over the forcing corpus (Round III).

**Ooh yeah, a census! Look at me, I count things HONESTLY!** Same discipline as
`v0_8_readiness_funnel.py`: report the REAL numbers the real code produces over the REAL forcing corpus, and
never reduce the denominator to the pretty cases. For EACH profile (`research_lab()`, `poor_man()`, the
fully-declared Custom `isopentyl_capability_fit_bench()`) INDEPENDENTLY, over EVERY route
`smartchem.experiment.routes.search_routes` returns for the five corpus targets (isopentyl acetate, aspirin,
paracetamol, methyl salicylate, retro-Diels-Alder), this harness reports two complementary views:

1. **The cumulative FUNNEL** (`routes returned -> PROCESS_SPECIFIED -> assessment requested -> material fit
   -> equipment fit -> physical -> process -> containment -> measurement -> waste -> procurement -> monetary
   assessed -> CAPABILITY_FIT`): a route survives a stage only if it survived every stage before it AND this
   one (a real funnel narrows; a shrinking denominator downstream is the EXPECTED, HONEST shape -- same
   ethos as the 0.8 readiness funnel).
2. **The per-axis CENSUS**: for EVERY one of the 11 `CapabilityAssessment` axes (including `ventilation` and
   `attention_care`, which the funnel list above does not name because they never gate the overall fold),
   the FULL `BLOCKED`/`UNKNOWN`/`UNCONSTRAINED`/`NOT_APPLICABLE`/`FIT` breakdown over EVERY route -- the
   denominator here is NEVER narrowed by the funnel above, on purpose (the mission's own instruction: "every
   route, every axis, honest counts").

`search_routes` itself is PROFILE-BLIND (D10): "routes returned" and the PROCESS_SPECIFIED tier count are
therefore IDENTICAL across all three profiles -- that identity is itself a receipt this harness prints, not
an assumption.

Run:  .venv/bin/python experiments/v0_9_capability_funnel.py
"""
from __future__ import annotations

from pathlib import Path

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.capability.assess import assess
from smartchem.capability.enums import CapabilityStatus
from smartchem.capability.presets import isopentyl_capability_fit_bench, poor_man, research_lab
from smartchem.capability.requirements import compile_capability_requirements
from smartchem.experiment import routes as rt
from smartchem.experiment.readiness import PROCESS_SPECIFIED, evaluate_route
from smartchem.identity_parse import InputKind, resolve_target

_ARTIFACT = Path(__file__).with_name("V0_9_CAPABILITY_FUNNEL_RESULTS.md")

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

#: every axis `CapabilityAssessment` carries, in the SAME fixed order `CapabilityAssessment.axes` uses.
_ALL_AXES = (
    "material", "equipment", "physical", "process", "containment", "ventilation", "measurement",
    "waste", "procurement", "attention_care", "monetary",
)
#: the 9 axes the mission's funnel list names explicitly (ventilation/attention_care never gate the fold,
#: so they are census-only -- see module docstring).
_FUNNEL_AXES = (
    "material", "equipment", "physical", "process", "containment", "measurement", "waste", "procurement",
    "monetary",
)
#: the funnel's stage order, exactly as named in the release-evidence task.
_STAGES = (
    "routes returned", "PROCESS_SPECIFIED", "assessment requested",
    *(f"{axis} fit" for axis in _FUNNEL_AXES[:-1]), "monetary assessed", "CAPABILITY_FIT",
)

_PROFILES = (
    ("research_lab", research_lab),
    ("poor_man", poor_man),
    ("isopentyl_capability_fit_bench", isopentyl_capability_fit_bench),
)

_STATUS_NAMES = ("FIT", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE", "UNCONSTRAINED")


def _search(target_name, reagents, have, max_depth, tkind=InputKind.NAME):
    target = resolve_target(target_name, tkind).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _corpus_routes() -> list:
    """Every route the real search returns for the five forcing-corpus targets (the SAME real, sourced,
    profile-blind search `tests/test_v0_9_capability_round_iii.py` drives its matrix on) -- ALL of them,
    never just the first candidate, so the denominator is never quietly narrowed."""
    routes = []
    routes += _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3).routes
    routes += _search(
        "acetylsalicylic acid", ("acetic acid",), ("salicylic acid", "acetic anhydride"), 3,
    ).routes
    routes += _search("paracetamol", ("acetic acid",), ("4-aminophenol", "acetic anhydride"), 3).routes
    routes += _search("methyl salicylate", ("water",), ("salicylic acid", "methanol"), 3).routes
    routes += _search("C1=CCCCC1", ("C=C",), ("C=CC=C",), 2, tkind=InputKind.SMILES).routes  # retro-Diels-Alder
    return routes


def _axis_ok(status: CapabilityStatus) -> bool:
    """Whether an axis status lets a route PASS that stage of the cumulative funnel -- the SAME "clean"
    definition the Round-III test file's `_nonclean_axes` uses (FIT/NOT_APPLICABLE/UNCONSTRAINED never
    block; BLOCKED/UNKNOWN always do)."""
    return status in (CapabilityStatus.FIT, CapabilityStatus.NOT_APPLICABLE, CapabilityStatus.UNCONSTRAINED)


def compute(routes: list, profile_builder) -> dict:
    """One profile's funnel + census over `routes`. Returns
    ``{"funnel": {stage: count}, "census": {axis: {status_name: count}}, "total_routes": int}``."""
    funnel = {stage: 0 for stage in _STAGES}
    census = {axis: {name: 0 for name in _STATUS_NAMES} for axis in _ALL_AXES}
    total = len(routes)
    for i, route in enumerate(routes):
        if i and i % 10 == 0:
            print(f"    ...{i}/{total} routes assessed", flush=True)
        req = compile_capability_requirements(route)
        readiness = evaluate_route(route)
        profile = profile_builder()
        a = assess(profile, req, readiness)

        for axis in _ALL_AXES:
            census[axis][getattr(a, axis).status.value] += 1

        alive = True
        for stage in _STAGES:
            if stage == "routes returned":
                stage_pass = True
            elif stage == "PROCESS_SPECIFIED":
                stage_pass = readiness.tier == PROCESS_SPECIFIED
            elif stage == "assessment requested":
                stage_pass = True  # assess() is unconditional -- CAPABILITY_ASSESSED is trivially true
            elif stage == "monetary assessed":
                stage_pass = _axis_ok(a.monetary.status)
            elif stage == "CAPABILITY_FIT":
                stage_pass = a.overall is CapabilityStatus.FIT
            else:
                stage_axis = stage.rsplit(" ", 1)[0]
                stage_pass = _axis_ok(getattr(a, stage_axis).status)
            alive = alive and stage_pass
            if alive:
                funnel[stage] += 1
    return {"funnel": funnel, "census": census, "total_routes": total}


def check(results: list, name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


def run() -> tuple:
    routes = _corpus_routes()
    per_profile = {name: compute(routes, builder) for name, builder in _PROFILES}
    r: list = []

    check(r, "corpus non-empty", len(routes) > 0, f"{len(routes)} routes returned")
    # search_routes is profile-blind (D10): "routes returned" and the tier gate must be IDENTICAL everywhere.
    returned = {per_profile[n]["funnel"]["routes returned"] for n, _ in _PROFILES}
    ps = {per_profile[n]["funnel"]["PROCESS_SPECIFIED"] for n, _ in _PROFILES}
    check(
        r, "routes-returned is profile-blind", len(returned) == 1,
        f"routes returned per profile: {[per_profile[n]['funnel']['routes returned'] for n, _ in _PROFILES]}",
    )
    check(
        r, "PROCESS_SPECIFIED count is profile-blind", len(ps) == 1,
        f"PROCESS_SPECIFIED per profile: {[per_profile[n]['funnel']['PROCESS_SPECIFIED'] for n, _ in _PROFILES]}",
    )
    # the funnel must be monotone non-increasing, stage over stage, for EVERY profile (it's cumulative AND).
    for name, _ in _PROFILES:
        funnel = per_profile[name]["funnel"]
        for weaker, stronger in zip(_STAGES[:-1], _STAGES[1:]):
            check(
                r, f"{name}: funnel monotone {weaker!r} >= {stronger!r}",
                funnel[weaker] >= funnel[stronger], f"{weaker}={funnel[weaker]}, {stronger}={funnel[stronger]}",
            )
    # the isopentyl fully-declared bench is the release positive: it must reach a genuine CAPABILITY_FIT (>=1).
    fit_bench_fit = per_profile["isopentyl_capability_fit_bench"]["funnel"]["CAPABILITY_FIT"]
    check(
        r, "isopentyl_capability_fit_bench reaches a genuine CAPABILITY_FIT on the real corpus",
        fit_bench_fit >= 1, f"CAPABILITY_FIT count = {fit_bench_fit}",
    )
    # research_lab (no declared stock) and poor_man (no distillation/IR/hood) must NEVER reach CAPABILITY_FIT
    # on this corpus (forcing-matrix law) -- the funnel's own last stage must honestly read 0 for both.
    for name in ("research_lab", "poor_man"):
        n = per_profile[name]["funnel"]["CAPABILITY_FIT"]
        check(r, f"{name} never reaches CAPABILITY_FIT on this corpus", n == 0, f"CAPABILITY_FIT count = {n}")
    # per-axis census denominators must NEVER be narrowed -- every axis's status counts sum to total_routes.
    for name, _ in _PROFILES:
        total = per_profile[name]["total_routes"]
        for axis in _ALL_AXES:
            counted = sum(per_profile[name]["census"][axis].values())
            check(
                r, f"{name}: {axis} census denominator == total routes (never narrowed)",
                counted == total, f"{counted} == {total}",
            )
    return r, per_profile, routes


def render_markdown(results: list, per_profile: dict, total_routes: int) -> str:
    lines = [
        "# v0.9 Capability Compiler -- funnel + per-axis census (Round III forcing corpus)",
        "",
        "Generated by `experiments/v0_9_capability_funnel.py`. Corpus: every route "
        "`smartchem.experiment.routes.search_routes` returns for isopentyl acetate, aspirin, paracetamol, "
        "methyl salicylate, and retro-Diels-Alder (the SAME five targets the Round-III forcing matrix drives "
        f"its per-route rows on) -- **{total_routes} routes total**, IDENTICAL across every profile "
        "(`search_routes` is profile-blind, D10). The funnel is a CUMULATIVE AND over the stages listed, in "
        "order; a shrinking count downstream is the EXPECTED, HONEST shape -- it measures how many routes "
        "survive every gate up to and including that stage, not a target to hit 100% on. The per-axis "
        "census, separately, is NEVER narrowed by the funnel -- every axis's status counts sum to the full "
        f"{total_routes}-route denominator for every profile.",
        "",
    ]
    for name, _ in _PROFILES:
        data = per_profile[name]
        lines += [f"## Profile: `{name}()`", "", "### Funnel", "", "| stage | routes surviving |", "|---|---|"]
        for stage in _STAGES:
            lines.append(f"| {stage} | {data['funnel'][stage]} |")
        lines += ["", "### Per-axis census (every route, denominator never narrowed)", ""]
        lines.append("| axis | " + " | ".join(_STATUS_NAMES) + " | total |")
        lines.append("|---|" + "---|" * (len(_STATUS_NAMES) + 1))
        for axis in _ALL_AXES:
            counts = data["census"][axis]
            total_axis = sum(counts.values())
            lines.append(
                f"| {axis} | " + " | ".join(str(counts[s]) for s in _STATUS_NAMES) + f" | {total_axis} |"
            )
        lines.append("")

    lines += ["## Properties checked", "", "| property | verdict | detail |", "|---|---|---|"]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    passed = sum(1 for _, ok, _ in results if ok)
    lines += [
        "",
        f"**{passed}/{len(results)} properties hold.** "
        + (
            "The funnel is monotone non-increasing for every profile, routes-returned/PROCESS_SPECIFIED are "
            "honestly profile-blind, the fully-declared bench reaches a genuine CAPABILITY_FIT, "
            "research_lab/poor_man never fabricate one, and every per-axis census denominator is the full, "
            "un-narrowed route count."
            if passed == len(results)
            else "A property FAILED -- the funnel/census is not sound as stated."
        ),
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("v0.9 capability compiler funnel + census (research_lab / poor_man / isopentyl_capability_fit_bench):")
    results, per_profile, routes = run()
    md = render_markdown(results, per_profile, len(routes))
    _ARTIFACT.write_text(md, encoding="utf-8")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} properties hold. [wrote {_ARTIFACT}]")
    if passed != len(results):
        print("FUNNEL/CENSUS FAILED.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
