"""The Experiment Compiler command line -- give it a target and inventory, get ranked route dossiers.

    python -m smartchem.experiment "CC(=O)Nc1ccc(O)cc1" \\
        --have "Nc1ccc(O)cc1" --reagents "O" "CC(=O)O" "CC(=O)OC(=O)C" \\
        --max-temp 1473 --max-pressure 1.5

It enumerates candidate synthesis routes from the decompiler (E5), autoloads sourced stability data for
every species (PubChem/Wikidata/Bradley, cached; ``--offline`` uses seed + cache only), fits and ranks the
routes against the target bench (``--max-temp`` K, ``--max-pressure`` atm, the reagents on hand), and prints
the top route as a chemist-facing DOSSIER -- under the honesty banner (no success guarantee, no
kinetic rate; every other claim graded), every number in its epistemic bucket.  This is the "download and
go" entry point.
"""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction

from ..smiles import SmilesError, parse_smiles
from ..structure_descent import ScissionError
from .drafter import ConstraintBox, draft_route_dossier, rank_routes
from .routes import search_routes

__all__ = ["main"]


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not (parsed > 0.0) or parsed == float("inf"):
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return parsed


def _parse(value: str):
    from ..structure import structure_by_name

    kind = None
    payload = value
    if ":" in value:
        prefix, rest = value.split(":", 1)
        if prefix.casefold() in {"name", "smiles"}:
            kind, payload = prefix.casefold(), rest
    if kind != "smiles":
        named = structure_by_name(payload)
        if named is not None:
            return named.molecule
        if kind == "name":
            raise ValueError(f"unknown offline chemical name {payload!r}; provide SMILES instead")
    try:
        return parse_smiles(payload)
    except SmilesError as exc:
        raise ValueError(f"could not parse or resolve {value!r} as an offline name or SMILES: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m smartchem.experiment", description=__doc__)
    p.add_argument("target", help="compound name or SMILES; explicit name:.../smiles:... prefixes are accepted")
    p.add_argument("--have", nargs="*", default=[], metavar="TARGET",
                   help="precursors already on the bench (names or SMILES)")
    p.add_argument("--reagents", nargs="*", default=["water"], metavar="TARGET",
                   help="small helper reagents the cleavage may use (default: water)")
    p.add_argument("--max-temp", type=_positive_float, default=None, metavar="K",
                   help="the bench's maximum temperature in kelvin")
    p.add_argument("--max-pressure", type=_positive_float, default=None, metavar="ATM",
                   help="the bench's maximum pressure in atm")
    p.add_argument("--max-depth", type=_positive_int, default=2, help="retrosynthesis depth (default 2)")
    p.add_argument("--max-routes", type=_positive_int, default=100,
                   help="maximum unique routes returned (default 100)")
    p.add_argument("--cut-budget", type=_positive_int, default=20_000,
                   help="candidate rewrite budget per expanded target (default 20000)")
    p.add_argument("--offline", action="store_true", help="do not fetch; use the seed + cache only")
    p.add_argument("--show", type=int, default=5, help="how many ranked routes to list (default 5)")
    p.add_argument("--poor-mans", action="store_true",
                   help="also terminate routes at WIDELY-AVAILABLE commodity compounds (table salt, "
                        "vinegar, baking soda, ...) and print a shopping list -- so a route can bottom out "
                        "at stuff you can actually buy instead of at pure elements")
    args = p.parse_args(argv)

    try:
        target = _parse(args.target)
        have = tuple(_parse(s) for s in args.have)
        reagents = tuple(_parse(s) for s in args.reagents)
        smiles_by_mol = {}
        for mol, smi in [(target, args.target), *zip(have, args.have), *zip(reagents, args.reagents)]:
            smiles_by_mol[mol] = smi

        commodities = ()
        if args.poor_mans:
            from ..data.reagents import commodity_inventory
            commodities = commodity_inventory()
        search = search_routes(
            target, reagents=reagents, available=have, commodities=commodities,
            max_depth=args.max_depth, max_routes=args.max_routes, cut_budget=args.cut_budget,
        )
    except ScissionError as exc:
        print(f"synthesize: request refused at the current chemistry-model boundary: {exc}", file=sys.stderr)
        return 5
    except ValueError as exc:
        print(f"synthesize: unsupported or invalid chemistry request: {exc}", file=sys.stderr)
        return 2
    routes = search.routes
    print(search.receipt.render())
    if search.target_in_terminal_stock:
        print(
            f"target {args.target!r} is already present in the active exact-identity terminal stock; "
            "no synthesis expansion was attempted. Quantity, assay, phase, grade, and fitness remain "
            "unassessed."
        )
        return 0
    if not routes:
        if search.receipt.complete_within_bounds:
            print(f"no synthesis route to {args.target!r} in the declared bounded search space. "
                  "This does not claim that no route exists outside the current rewrite grammar or bounds.")
            return 3
        else:
            print(f"no route returned for {args.target!r}; SEARCH WAS PARTIAL. Absence is not evidence that "
                  "no route exists. Raise --cut-budget/--max-routes or change the inventory.")
            return 4

    # autoload sourced stability for every species across the routes (unless offline)
    species = {}
    for r in routes:
        for step in r.steps:
            for m in (*step.reactants, *step.products):
                species.setdefault(m, m)
    from ..data.autoload import autoload_stability
    stability = autoload_stability(
        list(species.values()), identifiers=smiles_by_mol, allow_network=not args.offline,
    )
    # M3: the broader sourced 298 K ΔfH°/S° table, so ΔG feasibility (M1) and equilibrium K (M2) reach
    # beyond the litmus seed (every common organic here unlocks its combustion). Degrades to UNKNOWN, never
    # a fabricated value, for anything it does not cover.
    from ..data.thermo_extended import extended_thermo
    thermo = extended_thermo()

    box = ConstraintBox(
        max_temperature_k=args.max_temp,
        max_pressure_atm=Fraction(str(args.max_pressure)) if args.max_pressure is not None else None,
        available_reagents=None,  # the CLI ranks; reagent availability is implied by the inventory it built
    )
    ranked = rank_routes(list(routes), box, stability=stability, thermo=thermo)

    print(f"{len(routes)} candidate route(s) to {args.target!r}; ranked best-first:\n")
    for i, rf in enumerate(ranked[:args.show], 1):
        eqns = " ; ".join(s.equation() for s in rf.route.steps)
        print(f"  {i}. [{rf.status.value}] composability={rf.composability.verdict}  {eqns}")
        for ex in rf.exclusions[:2]:
            print(f"       EXCLUDED: {ex}")
    best = ranked[0]
    print("\n" + "=" * 90)
    print("TOP ROUTE -- evidence dossier (not a bench-ready procedure):\n")
    # --have/--reagents declare identity and availability, not amount.  The old CLI silently invented
    # 1 mol of each and could then print a false material ceiling (or crash).  A ceiling is emitted only
    # when an explicit quantitative feed is supplied through the API.
    print(draft_route_dossier(best.route, feed=None, stability=stability, thermo=thermo).render())

    if args.poor_mans:
        from ..data.reagents import shopping_list
        buy = shopping_list(best.route)
        print("\n" + "=" * 90)
        print("SHOPPING LIST -- commodity buckets this route can bottom out at:")
        if buy:
            for r in buy:
                print(f"  * {r.name} -- {r.common_source} [{r.availability.value}]")
        else:
            print("  (this route's starting materials did not match a known commodity; "
                  "raise --max-depth or add precursors)")
    return 0 if search.receipt.complete_within_bounds else 4


if __name__ == "__main__":
    sys.exit(main())
