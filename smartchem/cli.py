"""``python -m smartchem`` -- the one coherent front door to SmartChem's chemistry verticals.

A chemist should be able to pick this up with ``--help`` alone and not have to learn the project's internal
module layout.  Four subcommands, each a thin wrapper over a built engine:

* ``decompile FORMULA``   -- descend a compound to its elemental (or commodity) buckets: the AND-OR
                             decomposition hypergraph (``smartchem.decompiler.build_decomposition``).
* ``compile TARGET``      -- the synthesis FRONT DOOR: a bounded, bucket-terminated, ranked & graded
                             route dossier (``smartchem.experiment.compile_synthesis``).
* ``synthesize TARGET``   -- the retrosynthesis route engine with the download-and-go data levers
                             (delegates to ``python -m smartchem.experiment``).
* ``audit PATH``          -- the probe-evidence auditor (delegates to ``python -m smartchem.evidence``).

Depth (the algorithms, the epistemic grades, the sourcing discipline) lives in the GitHub wiki; this is the
map, not the manual.
"""
from __future__ import annotations

import sys

__all__ = ["main"]

_WIKI = "https://github.com/femboy2112/SmartChem/wiki"

_USAGE = f"""python -m smartchem <command> [args]

commands:
  decompile FORMULA     descend a compound to its element/commodity buckets (AND-OR hypergraph)
  compile TARGET        compile a ranked, graded, bucket-terminated route dossier (name or SMILES)
  synthesize TARGET     enumerate retrosynthesis routes with the sourced-data levers
  audit PATH            audit a probe-evidence manifest (or directory)

Run `python -m smartchem <command> --help` for a command's options.
Depth and background: {_WIKI}
"""


def _positive_int(value: str) -> int:
    import argparse
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _parse_molecule(value: str):
    """Accept an offline registered name or SMILES, with optional explicit ``name:``/``smiles:`` prefix."""
    from .smiles import SmilesError, parse_smiles
    from .structure import structure_by_name

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
            raise ValueError(
                f"unknown offline chemical name {payload!r}; provide SMILES (optionally smiles:...) or use "
                "a registered name"
            )
    try:
        return parse_smiles(payload)
    except SmilesError as exc:
        raise ValueError(
            f"could not resolve {value!r} as an offline name or parse it as SMILES: {exc}; "
            "use name:... or smiles:... to make the input form explicit"
        ) from exc


def _parse_smiles(smiles: str):
    """Compatibility alias for callers that used the old private helper."""
    return _parse_molecule("smiles:" + smiles)


def _edge_line(edge) -> str:
    """Render one decomposition edge as ``n reactant -> m1 p1 + m2 p2`` (formulae by their canonical repr)."""
    def term(formula, mult: int) -> str:
        return f"{mult} {formula!r}" if mult > 1 else repr(formula)
    lhs = term(edge.reactant, edge.reactant_multiplicity)
    rhs = " + ".join(term(f, m) for f, m in edge.products)
    return f"{lhs} -> {rhs}"


def _cmd_decompile(argv: list[str]) -> int:
    import argparse

    from .decompiler import DecompilerError, build_decomposition, example_inventory

    p = argparse.ArgumentParser(
        prog="python -m smartchem decompile",
        description="Descend a compound to its elemental (or commodity) buckets as an AND-OR hypergraph.",
    )
    p.add_argument("target", help="the target as a chemical FORMULA (e.g. C8H9NO2), or a SMILES with --smiles")
    p.add_argument("--smiles", action="store_true",
                   help="read the target as a SMILES string and decompose its formula")
    p.add_argument("--inventory", nargs="*", default=None, metavar="FORMULA",
                   help="the closed set of buckets to bottom out at (default: the example inventory -- the "
                        "atom buckets plus a few small molecules); pass none for pure elements")
    p.add_argument("--max-multiplicity", type=_positive_int, default=1, metavar="N",
                   help="how many copies of a reactant one edge may consume (default 1)")
    p.add_argument("--budget", type=_positive_int, default=100_000, metavar="N",
                   help="candidate budget for each formula expansion (default 100000)")
    p.add_argument("--max-edges", type=_positive_int, default=5_000, metavar="N",
                   help="maximum graph edges before a loud partial refusal (default 5000)")
    args = p.parse_args(argv)

    try:
        if args.smiles:  # reduce parsed structure to the formula-native decompiler input
            mol = _parse_molecule("smiles:" + args.target)
            target = "".join(f"{el}{n if n > 1 else ''}" for el, n in sorted(mol.formula.items()))
        else:
            target = args.target
        inventory = tuple(args.inventory) if args.inventory is not None else example_inventory()
        graph = build_decomposition(
            target,
            inventory,
            max_multiplicity=args.max_multiplicity,
            budget=args.budget,
            max_edges=args.max_edges,
        )
    except (DecompilerError, ValueError) as exc:
        print(f"decompile: invalid chemistry input: {exc}", file=sys.stderr)
        return 2

    print(f"decompile {graph.target!r}  --  status: {graph.status}")
    if args.smiles:
        print(
            "  IDENTITY LOSS: this command used only the SMILES-derived formula; connectivity, isomer, "
            "stereochemistry, isotope placement, and local charge are not represented in this graph."
        )
    if graph.refusal_reason:
        print(f"  (partial: {graph.refusal_reason})")
    print(f"  inventory (buckets): {', '.join(repr(f) for f in inventory) or '(pure elements)'}")
    print(f"  {len(graph.edges)} decomposition edge(s):")
    for edge in graph.edges:
        print(f"    {_edge_line(edge)}")
    if not graph.edges:
        print("    (none -- the target is already a bucket)")
    return 0 if graph.status == "COMPLETE" else 4


def _cmd_compile(argv: list[str]) -> int:
    import argparse

    from .data.thermo_extended import extended_thermo
    from .experiment.compile import compile_synthesis
    from .structure_descent import ScissionError

    p = argparse.ArgumentParser(
        prog="python -m smartchem compile",
        description="Compile a bounded, ranked, graded, bucket-terminated route dossier for a target.",
    )
    p.add_argument("target", help="compound name or SMILES (name:... and smiles:... are accepted explicitly)")
    p.add_argument("--reagents", nargs="*", default=[], metavar="TARGET",
                   help="small helper reagents by name or SMILES (default: water)")
    p.add_argument("--have", nargs="*", default=[], metavar="TARGET",
                   help="precursors already on the bench, by name or SMILES -- routes may bottom out here")
    p.add_argument("--max-depth", type=_positive_int, default=3, metavar="N",
                   help="retrosynthesis depth (default 3)")
    p.add_argument("--max-routes", type=_positive_int, default=100, metavar="N",
                   help="maximum unique routes returned (default 100)")
    p.add_argument("--cut-budget", type=_positive_int, default=20_000, metavar="N",
                   help="candidate rewrite budget per expanded target (default 20000)")
    p.add_argument(
        "--no-commodities", "--elements", dest="no_commodities", action="store_true",
        help=(
            "disable poor-man's commodity terminals; the legacy --elements spelling does NOT add automatic "
            "element terminals to the current structural search"
        ),
    )
    args = p.parse_args(argv)

    try:
        target = _parse_molecule(args.target)
        reagents = tuple(_parse_molecule(s) for s in args.reagents)
        available = tuple(_parse_molecule(s) for s in args.have)
        compiled = compile_synthesis(
            target,
            reagents=reagents,
            available=available,
            max_depth=args.max_depth,
            max_routes=args.max_routes,
            cut_budget=args.cut_budget,
            commodities=() if args.no_commodities else None,
            thermo=extended_thermo(),
        )
    except ScissionError as exc:
        print(f"compile: request refused at the current chemistry-model boundary: {exc}", file=sys.stderr)
        return 5
    except ValueError as exc:
        print(f"compile: unsupported or invalid chemistry request: {exc}", file=sys.stderr)
        return 2
    print(compiled.render())
    if compiled.search_receipt is not None and not compiled.search_receipt.complete_within_bounds:
        return 4
    return 0 if compiled.found_route else 3


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-V", "--version"):
        from . import __version__
        print(f"smartchem {__version__}")
        return 0
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(_USAGE)
        return 0
    command, rest = argv[0], argv[1:]
    if command == "decompile":
        return _cmd_decompile(rest)
    if command == "compile":
        return _cmd_compile(rest)
    if command == "synthesize":
        from .experiment.cli import main as experiment_main
        return experiment_main(rest)
    if command == "audit":
        from .evidence.cli import main as evidence_main
        return evidence_main(rest)
    print(f"python -m smartchem: unknown command {command!r}\n", file=sys.stderr)
    print(_USAGE, file=sys.stderr)
    return 2
