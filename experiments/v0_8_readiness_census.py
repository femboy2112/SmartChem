"""V0.8-CENSUS-01: per-step, per-route readiness census over the forcing corpus (plan Sec 9).

This is the "what does the ladder actually SHOW on real routes" instrument. It runs every corpus member
through the real service (`build_recompile_request` -> `run_compilation`), which computes each
`RankedRouteSummary.readiness` via the SAME `smartchem.experiment.readiness.evaluate_route` the
service/dossier consume (Sec 8's "one evaluator" law -- this harness never re-derives its own copy of the
readiness logic, it just reads off the real answer), and reports, per step: is it a formal candidate (always
yes -- a built step already passed its conservation cert), is the reaction type recognized (and by which
class name), is a condition envelope declared/sourced/accepted, is a typed `ProcedureEvidence` attached and
does it clear `process`/`workup_isolation` (complete + sourced, Round II) -- PLUS four pure OBSERVATIONS
that are NOT readiness requirements and never gate a tier:
`handling` (an attention/agitation/equipment note declared on the step's process -- read off the SAME
`process_requirements` tuple the response already carries), and the route-level `selectivity` / `thermo`
(feasibility) / `kinetics` verdict strings the response exposes for ranking ONLY (Sec 2: `fit_status`-adjacent
verdicts, never a readiness grade -- labeled here so nobody mistakes "we noticed a verdict" for "the ladder
needed it").

Ugh, the annoying-but-important part: paracetamol's anhydride step is the best-SOURCED record in the whole
corpus and the WORST-recognized reaction (Sec 4.1's non-monotonicity finding). If this harness ever "fixes"
that by making conditions track the coarse tier, that's not a bugfix, that's M11 -- go read the mutation
harness before touching this one.

Run:  .venv/bin/python experiments/v0_8_readiness_census.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.experiment.readiness import ObligationStatus, RouteReadiness, evaluate_route
from smartchem.experiment.routes import search_routes
from smartchem.identity_parse import InputKind
from smartchem.service import build_recompile_request, run_compilation
from smartchem.smiles import parse_smiles

_ARTIFACT = Path(__file__).with_name("RESULTS_v0_8_readiness_census.md")

#: the promoted default route algebra (capped-scission + the 8 certified DA families) -- NEVER the raw
#: capped-only DEFAULT_TRANSFORM_REGISTRY, which would silently zero out every reaction-vouched row (the
#: parent's verified registry fact).
_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)

_STATUS_ABBR = {
    ObligationStatus.SATISFIED: "SATISFIED", ObligationStatus.UNSATISFIED: "UNSATISFIED",
    ObligationStatus.UNKNOWN: "UNKNOWN", ObligationStatus.NOT_APPLICABLE: "N/A",
}


@dataclass(frozen=True)
class _RouteRow:
    """One route's readiness, plus the four route-level OBSERVATION facts. `process_present` mirrors
    `process_requirements` (one entry per step) so the `handling` observation can be read per step without
    ever touching the DA-owned readiness obligations."""

    readiness: RouteReadiness
    process_requirements: tuple  # tuple[ProcessRequirements | None, ...], one per step, in order
    selectivity_verdict: str
    feasibility_verdict: str
    kinetics_verdict: str


@dataclass(frozen=True)
class Case:
    name: str
    row: int
    description: str
    routes: tuple  # tuple[_RouteRow, ...]


def _procedure_present(sr) -> str:
    """Whether a typed `ProcedureEvidence` is attached to this step's envelope at all -- read off the SAME
    `process`/`workup_isolation` obligation axes the ladder already computes, not a second lookup: per
    `_process_and_workup_obligations`, `process` (and `workup_isolation`) can ONLY be `UNKNOWN` when
    `step.envelope.procedure is None` (every other branch resolves to SATISFIED/UNSATISFIED/NOT_APPLICABLE),
    so `process is UNKNOWN` <=> "no procedure evidence declared" -- a clean, already-derived presence marker,
    not a new axis competing with the readiness gate."""
    if sr.process is ObligationStatus.UNKNOWN and sr.workup_isolation is ObligationStatus.UNKNOWN:
        return "absent"
    return "present"


def _handling_observed(process) -> str:
    """`attached` iff the step's process declares an attention/agitation/equipment note -- an OBSERVATION of
    bench-handling detail, never a readiness obligation (that is `process`/`workup_isolation` on the typed
    ladder, gated on §5's representation-completeness predicate instead)."""
    if process is None:
        return "absent"
    if process.attention is not None or process.agitation is not None or process.equipment:
        return "attached"
    return "absent"


def _row_from_summary(summary) -> _RouteRow:
    return _RouteRow(
        readiness=summary.readiness,
        process_requirements=summary.process_requirements,
        selectivity_verdict=summary.selectivity_verdict,
        feasibility_verdict=summary.feasibility_verdict,
        kinetics_verdict=summary.kinetics_verdict,
    )


def _service_route_rows(target: str, *, reagents: "tuple | None", have: tuple, max_depth: int) -> tuple:
    """Every route the real service returns for one named target, through the PROMOTED default algebra
    (`build_recompile_request` defaults `algebra_profile=DEFAULT_ROUTE_ALGEBRA_PROFILE` -- Sec 9's corpus
    rows 2-8 are all reachable this way; the bare-SMILES retro-DA row below can't go through a name lookup,
    so it uses `search_routes` directly instead).

    ``reagents=None`` means "omit the kwarg" -- ``build_recompile_request``'s OWN default
    (``helper_reagents=("water",)``) then applies, which is exactly what row 6's "default reagent" case needs
    to exercise. Passing ``()`` explicitly (as opposed to omitting it) would mean "no helper reagent at all",
    a materially different request -- never conflate the two."""
    kwargs = {} if reagents is None else {"helper_reagents": reagents}
    req = build_recompile_request(
        target, input_kind=InputKind.NAME, stock_materials=have, max_depth=max_depth, **kwargs,
    )
    resp = run_compilation(req)
    return tuple(_row_from_summary(s) for s in resp.ranked_route_dossiers)


def _da_route_rows() -> tuple:
    """Row 1: retro-Diels-Alder, direct through `search_routes` under the certified registry. No service verdict
    strings exist off this direct path, so the three route-level verdict observations report `(n/a: direct
    search_routes call, no RankedRouteSummary)` honestly rather than fabricating a value."""
    result = search_routes(
        parse_smiles("C1CC=CCC1"), reagents=(),
        available=(parse_smiles("C=CC=C"), parse_smiles("C=C")), max_depth=2, registry=_CERTIFIED,
    )
    return tuple(
        _RouteRow(
            readiness=evaluate_route(route), process_requirements=tuple(s.envelope.process for s in route.steps),
            selectivity_verdict="(n/a: direct search_routes call)",
            feasibility_verdict="(n/a: direct search_routes call)",
            kinetics_verdict="(n/a: direct search_routes call)",
        )
        for route in result.routes
    )


def build_cases() -> list[Case]:
    return [
        Case(
            "retro-DA cyclohexene", 1,
            "cyclohexene <- butadiene + ethylene (retro-[4+2]); no stock reagents -- REACTION_VOUCHED expected, "
            "conditions UNKNOWN (no SEED_CONDITIONS record for a bare DA adduct)",
            _da_route_rows(),
        ),
        Case(
            "paracetamol", 2,
            "4-aminophenol + (water, acetic acid), depth 2 -- the non-monotonic exemplar: the anhydride step "
            "is sourced + workup-described while its reaction type is unrecognized",
            _service_route_rows(
                "paracetamol", reagents=("water", "acetic acid"), have=("4-aminophenol",), max_depth=2,
            ),
        ),
        Case(
            "aspirin", 3,
            "salicylic acid + (water, acetic acid), depth 2 -- same acyl-anhydride shape as paracetamol: "
            "sourced + workup, reaction type unrecognized",
            _service_route_rows("aspirin", reagents=("water", "acetic acid"), have=("salicylic acid",), max_depth=2),
        ),
        Case(
            "isopentyl acetate", 4,
            "isopentyl alcohol + (water, acetic acid) -- recognized (Fischer esterification) + sourced + "
            "workup -> CONDITIONS_SUPPORTED",
            _service_route_rows(
                "isopentyl acetate", reagents=("water", "acetic acid"), have=("isopentyl alcohol",), max_depth=3,
            ),
        ),
        Case(
            "methyl salicylate", 5,
            "salicylic acid + (water, methanol) -- recognized + sourced, workup_included=False -> the clean "
            "CONDITIONS_SUPPORTED ceiling (process/workup both visible-but-open)",
            _service_route_rows(
                "methyl salicylate", reagents=("water", "methanol"), have=("salicylic acid",), max_depth=1,
            ),
        ),
        Case(
            "aspirin, default reagent (no acetic acid)", 6,
            "salicylic acid + the BUILD-DEFAULT helper reagent (water only, no explicit acetic acid) -- "
            "recognized reaction, but the SEED_CONDITIONS name-guard needs acetic acid present, so conditions "
            "stays UNKNOWN (not even declared): the formal-vouched-vs-fake-sourced contrast",
            _service_route_rows("aspirin", reagents=None, have=("salicylic acid",), max_depth=2),
        ),
        Case(
            "4-aminophenyl acetate isomer (negative control)", 7,
            "the O-acetyl C8H9NO2 isomer of paracetamol, same reagents (water, acetic acid) -- structurally "
            "emits the same product pair, but the name-guard fails so it must NOT borrow paracetamol's sourced "
            "envelope (conditions stays UNKNOWN, never SATISFIED)",
            _service_route_rows(
                "4-aminophenyl acetate", reagents=("water", "acetic acid"), have=("4-aminophenol",), max_depth=2,
            ),
        ),
    ]


def render_markdown(cases: list[Case]) -> str:
    lines = [
        "# v0.8 readiness census -- per-step obligation readout over the forcing corpus",
        "",
        "Generated by `experiments/v0_8_readiness_census.py`, through the real service, whose "
        "`RankedRouteSummary.readiness` is computed by the SAME `smartchem.experiment.readiness.evaluate_route` "
        "the dossier consumes, over the PROMOTED default route algebra (`certified-route-v07`) -- the raw "
        "capped-only `DEFAULT_TRANSFORM_REGISTRY` is never used here (it would silently zero out every "
        "reaction-vouched row). `handling` / `selectivity` / `thermo` / `kinetics` are pure OBSERVATIONS, not "
        "readiness obligations -- they never move `tier`.",
        "",
    ]
    tier_counts: dict[str, int] = {}
    axis_counts = {
        axis: {"SATISFIED": 0, "UNSATISFIED": 0, "UNKNOWN": 0, "N/A": 0}
        for axis in ("reaction_type", "conditions", "process", "workup_isolation")
    }
    handling_counts = {"attached": 0, "absent": 0}
    procedure_counts = {"present": 0, "absent": 0}
    n_routes = n_steps = 0

    for case in cases:
        lines += [f"## Row {case.row}: {case.name}", "", case.description, ""]
        if not case.routes:
            lines += ["_no routes returned for this target under the promoted default algebra._", ""]
            continue
        lines += [
            "| route | step | formal | reaction_type | class | conditions | process | workup | procedure | "
            "provenance | step tier | *handling* |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r_idx, row in enumerate(case.routes):
            n_routes += 1
            tier_counts[row.readiness.tier] = tier_counts.get(row.readiness.tier, 0) + 1
            for s_idx, sr in enumerate(row.readiness.per_step):
                n_steps += 1
                for axis in axis_counts:
                    axis_counts[axis][_STATUS_ABBR[getattr(sr, axis)]] += 1
                process = (
                    row.process_requirements[s_idx] if s_idx < len(row.process_requirements) else None
                )
                handling = _handling_observed(process)
                handling_counts[handling] += 1
                procedure_present = _procedure_present(sr)
                procedure_counts[procedure_present] += 1
                prov = ", ".join(sr.provenance) if sr.provenance else "(none)"
                lines.append(
                    f"| {r_idx} | {s_idx} | {_STATUS_ABBR[sr.formal_candidate]} | "
                    f"{_STATUS_ABBR[sr.reaction_type]} | {sr.reaction_class_name or '(unrecognized)'} | "
                    f"{_STATUS_ABBR[sr.conditions]} | {_STATUS_ABBR[sr.process]} | "
                    f"{_STATUS_ABBR[sr.workup_isolation]} | {procedure_present} | {prov} | {sr.tier} | "
                    f"{handling} |"
                )
            lines.append(
                f"| {r_idx} | | | | | | | | | | **route tier: {row.readiness.tier}** | "
                f"*route verdicts -- selectivity={row.selectivity_verdict}, thermo={row.feasibility_verdict}, "
                f"kinetics={row.kinetics_verdict}* |"
            )
        lines.append("")

    lines += [
        "## Aggregate",
        "",
        f"- routes examined: {n_routes}",
        f"- steps examined: {n_steps}",
        "- route coarse-tier distribution: "
        + (", ".join(f"{t}={n}" for t, n in sorted(tier_counts.items())) if tier_counts else "(none)"),
        "",
        "| readiness axis | SATISFIED | UNSATISFIED | UNKNOWN | N/A |",
        "|---|---|---|---|---|",
    ]
    for axis, counts in axis_counts.items():
        lines.append(
            f"| {axis} | {counts['SATISFIED']} | {counts['UNSATISFIED']} | {counts['UNKNOWN']} | {counts['N/A']} |"
        )
    lines += [
        "",
        f"- steps with a typed `ProcedureEvidence` attached at all (`procedure`, presence only -- NOT the same "
        f"as `process`=SATISFIED, which additionally requires completeness + sourcing): "
        f"present={procedure_counts['present']}, absent={procedure_counts['absent']}",
        "",
        "**Observations (never a readiness obligation, never gate a tier):**",
        "",
        f"- `handling` (per step, attention/agitation/equipment declared on the process): "
        f"attached={handling_counts['attached']}, absent={handling_counts['absent']}",
        "- `selectivity` / `thermo` (feasibility) / `kinetics` are route-level RANKING verdict strings already "
        "carried by `RankedRouteSummary` -- see the *route verdicts* line under each route above (the "
        "SMILES-only retro-DA row has no `RankedRouteSummary`, so it reports `(n/a: direct search_routes call)`).",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("v0.8 readiness census -- per-step obligation readout over the forcing corpus:")
    cases = build_cases()
    n_routes = sum(len(c.routes) for c in cases)
    n_steps = sum(len(row.readiness.per_step) for c in cases for row in c.routes)
    print(f"  routes examined: {n_routes}, steps examined: {n_steps}")
    for case in cases:
        for row in case.routes:
            print(f"  [{case.name}] route tier={row.readiness.tier}")
    md = render_markdown(cases)
    _ARTIFACT.write_text(md, encoding="utf-8")
    print(f"[wrote {_ARTIFACT}]")
    if n_routes == 0 or n_steps == 0:
        print("CENSUS FAILED -- no routes/steps examined.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
