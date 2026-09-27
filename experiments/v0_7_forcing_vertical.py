"""V0.7-FORCING-VERTICAL-01: one admitted family widens the ALGEBRA through the UNCHANGED search.

The 0.7 thesis is that a certified provider -- not a capped-scission-only default -- is the unit of the
production algebra.  This is the first forcing vertical: take the already-built, already-reviewed, oracle-
recognized, fuzz-covered alkene Diels-Alder family (admission verdict in
`docs/research/V0_7_PRODUCTION_CHEMICAL_ALGEBRA_PLAN_v0.1.md` §2) and prove, through the UNCHANGED
`search_routes` shell, the eight properties the plan requires -- WITHOUT flipping the global default.

The candidate registry is `(CappedScissionProvider(), DielsAlderProvider())`, selected explicitly; the global
`DEFAULT_TRANSFORM_REGISTRY` is never mutated.  Each property prints PASS/FAIL; a single failure exits nonzero.

Run:  .venv/bin/python experiments/v0_7_forcing_vertical.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from smartchem.diels_alder import DielsAlderProvider
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY,
    CappedScissionProvider,
    TransformProviderRegistry,
    search_algebra_digest,
)

_ARTIFACT = Path(__file__).with_name("RESULTS_v0_7_forcing_vertical.md")

CANDIDATE = TransformProviderRegistry((CappedScissionProvider(), DielsAlderProvider()))

# The canonical DA retron: cyclohexene retro-[4+2] -> 1,3-butadiene + ethylene.
CHX = parse_smiles("C1CC=CCC1")
BUTA = parse_smiles("C=CC=C")
ETH = parse_smiles("C=C")


def _route_signature(result) -> tuple:
    """A canonical, comparable signature of a route set: per route, the tuple of step product formulae."""
    return tuple(
        sorted(tuple(repr(m) for m in step.products) for route in result.routes for step in route.steps)
    )


def _da_witnesses(reactant):
    """The DIELS_ALDER EnumeratedTransforms the candidate registry emits for ``reactant`` (reagentless)."""
    ets, complete = CANDIDATE.enumerate(reactant, (), budget=100_000)
    return [e for e in ets if e.witness_kind == "DIELS_ALDER"], complete


def check(results: list, name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def run() -> list:
    r: list = []

    # P1 -- reachability delta: unreachable under capped-scission-only, reachable under the wider algebra.
    with_da = search_routes(CHX, reagents=(), available=(BUTA, ETH), registry=CANDIDATE, max_depth=2)
    without = search_routes(CHX, reagents=(), available=(BUTA, ETH), max_depth=2)  # DEFAULT registry
    check(r, "P1 reachability", len(with_da.routes) >= 1 and len(without.routes) == 0,
          f"candidate routes={len(with_da.routes)}, default routes={len(without.routes)}")

    # P2 -- the generated step is vouched by INDEPENDENT re-derived class evidence (oracle class 4).
    step0 = with_da.routes[0].steps[0] if with_da.routes else None
    cls = recognize_reaction_type(step0) if step0 is not None else None
    das, _ = _da_witnesses(CHX)
    check(r, "P2 class-vouch", cls is not None and "diels" in cls.lower() and len(das) == 1
          and das[0].provider_id == "diels-alder-retro",
          f"oracle class={cls!r}, enumerate DA witnesses={len(das)}")

    # P3 -- no unrelated route changes when the wider family is INAPPLICABLE (a saturated ring has no DA retron).
    inapplicable = parse_smiles("C1CCCCC1")  # cyclohexane: no double bond -> DA emits nothing
    d_sig = _route_signature(search_routes(inapplicable, reagents=(), available=(), max_depth=2))
    c_sig = _route_signature(search_routes(inapplicable, reagents=(), available=(), registry=CANDIDATE, max_depth=2))
    da_here, _ = _da_witnesses(inapplicable)
    check(r, "P3 non-perturbation", d_sig == c_sig and len(da_here) == 0,
          f"default==candidate route sets: {d_sig == c_sig}; DA emitted here: {len(da_here)}")

    # P4 -- search receipts BIND the actual algebra (a wider registry stamps a different transform-algebra digest).
    d_digest = without.receipt.transform_registry_digest
    c_digest = with_da.receipt.transform_registry_digest
    expected_c = search_algebra_digest("linear-route", CANDIDATE)
    check(r, "P4 receipt-binds-algebra", d_digest != c_digest and c_digest == expected_c,
          f"default!=candidate digest: {d_digest != c_digest}; candidate matches search_algebra_digest: {c_digest == expected_c}")

    # P5 -- aggregate completeness cannot become falsely complete: a budget-starved capped-scission makes the
    # AGGREGATE incomplete even though the reagentless DA family is complete (AND semantics, transform_provider.py:257).
    ester = parse_smiles("CC(=O)OC")  # methyl acetate: capped scission has mediated cuts to enumerate
    water = parse_smiles("O")
    _, complete_starved = CANDIDATE.enumerate(ester, (water,), budget=1)   # budget=1 starves capped-scission
    _, complete_ample = CANDIDATE.enumerate(ester, (water,), budget=100_000)
    check(r, "P5 completeness-AND", complete_starved is False and complete_ample is True,
          f"starved complete={complete_starved} (must be False), ample complete={complete_ample} (must be True)")

    # P6 -- hostile near-miss stays demoted/absent: an enone whose ring carbonyl would retro to a KETENE must
    # emit NO DA transform (guard-2b), so the wider algebra does not manufacture a fictional route.
    enone = parse_smiles("O=C1CCCC=C1")  # cyclohex-2-en-1-one
    das_enone, _ = _da_witnesses(enone)
    check(r, "P6 hostile-near-miss", len(das_enone) == 0,
          f"DA witnesses emitted for the enone: {len(das_enone)} (must be 0)")

    # P7 -- fresh holdout (NOT the design target): a substituted cyclohexene still enumerates a genuine retro-DA
    # under the wider algebra and none under the default.  Checked at the enumerate layer (no precursor guessing).
    holdout = parse_smiles("CC1CCC=CC1")  # 4-methylcyclohex-1-ene, unused in design
    das_hold, _ = _da_witnesses(holdout)
    d_hold, _ = DEFAULT_TRANSFORM_REGISTRY.enumerate(holdout, (), budget=100_000)
    d_hold_da = [e for e in d_hold if e.witness_kind == "DIELS_ALDER"]
    check(r, "P7 fresh-holdout", len(das_hold) >= 1 and len(d_hold_da) == 0,
          f"candidate DA witnesses={len(das_hold)}, default DA witnesses={len(d_hold_da)}")

    # P8 -- the DEFAULT algebra is byte/semantic-stable: it is untouched, and a default search of the DA target is
    # identical whether or not a candidate registry exists elsewhere (the default digest is the fixed baseline).
    default_again = search_routes(CHX, reagents=(), available=(BUTA, ETH), max_depth=2)
    check(r, "P8 default-stable",
          DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",)
          and default_again.receipt.transform_registry_digest == d_digest
          and len(default_again.routes) == 0,
          f"default ids={DEFAULT_TRANSFORM_REGISTRY.provider_ids}, digest stable={default_again.receipt.transform_registry_digest == d_digest}")
    return r


def render_markdown(results: list) -> str:
    lines = [
        "# v0.7 forcing vertical -- alkene Diels-Alder widens the algebra through the unchanged search",
        "",
        "Generated by `experiments/v0_7_forcing_vertical.py`. The candidate registry is",
        "`(CappedScissionProvider, DielsAlderProvider)`, selected EXPLICITLY; `DEFAULT_TRANSFORM_REGISTRY` is",
        "never mutated. Target: cyclohexene `C1CC=CCC1` retro-[4+2] -> butadiene + ethylene.",
        "",
        "| property | verdict | detail |",
        "|---|---|---|",
    ]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    passed = sum(1 for _, ok, _ in results if ok)
    lines += ["", f"**{passed}/{len(results)} properties hold.** "
              + ("The forcing vertical is sound; promotion toward a production default remains gated on the "
                 "grammar-identity content digest (plan §4)." if passed == len(results)
                 else "A property FAILED -- the vertical is not sound as stated."), ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    print("v0.7 forcing vertical -- alkene Diels-Alder through the unchanged route search:")
    results = run()
    md = render_markdown(results)
    _ARTIFACT.write_text(md, encoding="utf-8")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} properties hold. [wrote {_ARTIFACT}]")
    if passed != len(results):
        print("FORCING VERTICAL FAILED.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
