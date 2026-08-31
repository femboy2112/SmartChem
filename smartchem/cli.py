"""``python -m smartchem`` -- the one coherent front door to SmartChem's chemistry verticals.

A chemist should be able to pick this up with ``--help`` alone and not have to learn the project's internal
module layout.  Four subcommands, each a thin wrapper over a built engine:

* ``decompile FORMULA``   -- descend a compound to its elemental (or commodity) buckets: the AND-OR
                             decomposition hypergraph (``smartchem.decompiler.build_decomposition``).
* ``compile SMILES``      -- the synthesis FRONT DOOR: a complete, bucket-terminated, ranked & graded
                             synthesis with full chemist detail (``smartchem.experiment.compile_synthesis``).
* ``synthesize SMILES``   -- the retrosynthesis route engine with the download-and-go data levers
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
  compile SMILES        compile a full ranked, graded, bucket-terminated synthesis (the front door)
  synthesize SMILES     enumerate retrosynthesis routes with the sourced-data levers
  audit PATH            audit a probe-evidence manifest (or directory)

Run `python -m smartchem <command> --help` for a command's options.
Depth and background: {_WIKI}
"""


def _parse_smiles(smiles: str):
    from .smiles import SmilesError, parse_smiles
    try:
        return parse_smiles(smiles)
    except SmilesError as exc:
        raise SystemExit(f"could not parse SMILES {smiles!r}: {exc}") from exc


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
    p.add_argument("--max-multiplicity", type=int, default=1, metavar="N",
                   help="how many copies of a reactant one edge may consume (default 1)")
    args = p.parse_args(argv)

    if args.smiles:  # turn the parsed molecule into its formula string for the (formula-native) decompiler
        mol = _parse_smiles(args.target)
        target = "".join(f"{el}{n if n > 1 else ''}" for el, n in sorted(mol.formula.items()))
    else:
        target = args.target
    inventory = tuple(args.inventory) if args.inventory is not None else example_inventory()

    try:
        graph = build_decomposition(target, inventory, max_multiplicity=args.max_multiplicity)
    except DecompilerError as exc:
        raise SystemExit(f"decompile: {exc}") from exc

    print(f"decompile {graph.target!r}  --  status: {graph.status}")
    if graph.refusal_reason:
        print(f"  (partial: {graph.refusal_reason})")
    print(f"  inventory (buckets): {', '.join(repr(f) for f in inventory) or '(pure elements)'}")
    print(f"  {len(graph.edges)} decomposition edge(s):")
    for edge in graph.edges:
        print(f"    {_edge_line(edge)}")
    if not graph.edges:
        print("    (none -- the target is already a bucket)")
    return 0


def _cmd_compile(argv: list[str]) -> int:
    import argparse

    from .data.thermo_extended import extended_thermo
    from .experiment.compile import compile_synthesis

    p = argparse.ArgumentParser(
        prog="python -m smartchem compile",
        description="Compile a full, ranked, graded, bucket-terminated synthesis for a target (SMILES).",
    )
    p.add_argument("target", help="SMILES of the compound to make")
    p.add_argument("--reagents", nargs="*", default=[], metavar="SMILES",
                   help="small helper reagents the cleavage may use (default: water)")
    p.add_argument("--have", nargs="*", default=[], metavar="SMILES",
                   help="precursors already on the bench (SMILES) -- routes may bottom out here")
    p.add_argument("--max-depth", type=int, default=3, metavar="N", help="retrosynthesis depth (default 3)")
    p.add_argument("--elements", action="store_true",
                   help="bottom out at pure ELEMENTS only (disable the poor-man's commodity buckets)")
    args = p.parse_args(argv)

    target = _parse_smiles(args.target)
    reagents = tuple(_parse_smiles(s) for s in args.reagents)
    available = tuple(_parse_smiles(s) for s in args.have)
    compiled = compile_synthesis(
        target,
        reagents=reagents,
        available=available,
        max_depth=args.max_depth,
        commodities=() if args.elements else None,
        thermo=extended_thermo(),
    )
    print(compiled.render())
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
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
