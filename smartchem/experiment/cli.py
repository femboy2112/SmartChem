"""The Experiment Compiler command line -- give it a target and an inventory, get ranked runnable drafts.

    python -m smartchem.experiment "CC(=O)Nc1ccc(O)cc1" \\
        --have "Nc1ccc(O)cc1" --reagents "O" "CC(=O)O" "CC(=O)OC(=O)C" \\
        --max-temp 1473 --max-pressure 1.5

It enumerates candidate synthesis routes from the decompiler (E5), autoloads sourced stability data for
every species (PubChem/Wikidata/Bradley, cached; ``--offline`` uses seed + cache only), fits and ranks the
routes against the target bench (``--max-temp`` K, ``--max-pressure`` atm, the reagents on hand), and prints
the top runnable route as a chemist-facing DRAFT -- under the honesty banner (no success guarantee, no
kinetic rate; every other claim graded), every number in its epistemic bucket.  This is the "download and
go" entry point.
"""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction

from ..smiles import SmilesError, parse_smiles
from .drafter import ConstraintBox, draft_procedure, rank_routes
from .routes import enumerate_routes

__all__ = ["main"]


def _parse(smiles: str):
    try:
        return parse_smiles(smiles)
    except SmilesError as exc:
        raise SystemExit(f"could not parse SMILES {smiles!r}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m smartchem.experiment", description=__doc__)
    p.add_argument("target", help="SMILES of the compound to synthesise")
    p.add_argument("--have", nargs="*", default=[], metavar="SMILES",
                   help="precursors already on the bench (SMILES)")
    p.add_argument("--reagents", nargs="*", default=["O"], metavar="SMILES",
                   help="small helper reagents the cleavage may use (default: water)")
    p.add_argument("--max-temp", type=float, default=None, metavar="K",
                   help="the bench's maximum temperature in kelvin")
    p.add_argument("--max-pressure", type=float, default=None, metavar="ATM",
                   help="the bench's maximum pressure in atm")
    p.add_argument("--max-depth", type=int, default=2, help="retrosynthesis depth (default 2)")
    p.add_argument("--offline", action="store_true", help="do not fetch; use the seed + cache only")
    p.add_argument("--show", type=int, default=5, help="how many ranked routes to list (default 5)")
    args = p.parse_args(argv)

    target = _parse(args.target)
    have = tuple(_parse(s) for s in args.have)
    reagents = tuple(_parse(s) for s in args.reagents)
    smiles_by_mol = {}
    for mol, smi in [(target, args.target), *zip(have, args.have), *zip(reagents, args.reagents)]:
        smiles_by_mol[mol] = smi

    routes = enumerate_routes(target, reagents=reagents, available=have, max_depth=args.max_depth)
    if not routes:
        print(f"no synthesis route to {args.target!r} from the given inventory within depth "
              f"{args.max_depth}. Add precursors with --have, reagents with --reagents, or raise "
              f"--max-depth. (A loud 'no route', never a fabricated one.)")
        return 1

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

    box = ConstraintBox(
        max_temperature_k=args.max_temp,
        max_pressure_atm=Fraction(args.max_pressure).limit_denominator() if args.max_pressure else None,
        available_reagents=None,  # the CLI ranks; reagent availability is implied by the inventory it built
    )
    ranked = rank_routes(list(routes), box, stability=stability)

    print(f"{len(routes)} candidate route(s) to {args.target!r}; ranked best-first:\n")
    for i, rf in enumerate(ranked[:args.show], 1):
        eqns = " ; ".join(s.equation() for s in rf.route.steps)
        print(f"  {i}. [{rf.status.value}] composability={rf.composability.verdict}  {eqns}")
        for ex in rf.exclusions[:2]:
            print(f"       EXCLUDED: {ex}")
    best = ranked[0]
    print("\n" + "=" * 90)
    print("TOP ROUTE -- drafted procedure:\n")
    feed = {m: 1 for m in (*have, *reagents)}
    print(draft_procedure(best.route, feed=feed or None, stability=stability).render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
