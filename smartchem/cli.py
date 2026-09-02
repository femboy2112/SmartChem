"""``python -m smartchem`` -- the one coherent front door to SmartChem's chemistry verticals.

A chemist should be able to pick this up with ``--help`` alone and not have to learn the project's internal
module layout.  Four subcommands, each a thin wrapper over a built engine:

* ``decompile FORMULA``   -- descend a compound to its elemental (or commodity) buckets: the AND-OR
                             decomposition hypergraph (``smartchem.decompiler.build_decomposition``).
* ``recompile TARGET``    -- the CANONICAL synthesis verb (standard section 14.1): builds the one typed
                             ``CompilationRequest`` and runs it through :func:`smartchem.service.run_compilation`,
                             yielding the typed response, ``--json``/``--emit-request`` views, and the section
                             14.4 exit codes from a single service authority.
* ``compile TARGET``      -- [DEPRECATED alias of ``recompile``, one cycle] the synthesis FRONT DOOR: a bounded,
                             bucket-terminated, ranked & graded route dossier
                             (``smartchem.experiment.compile_synthesis``).  It now builds the SAME typed request
                             as ``recompile`` (no divergent defaults), so ``compile ... --emit-request`` and
                             ``recompile ... --emit-request`` are byte-identical.
* ``synthesize TARGET``   -- [DEPRECATED alias, one cycle] the retrosynthesis route engine with the download-and-go
                             data levers (delegates to ``python -m smartchem.experiment``).  Its full uptake into
                             the typed request (its --max-temp/--max-pressure constraints and --offline provider
                             levers) is CLI-CAN-02.
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
  recompile TARGET      CANONICAL synthesis verb: one typed request -> service (--json/--emit-request/--quiet)
  compile TARGET        [deprecated alias of recompile] ranked, graded, bucket-terminated route dossier
  synthesize TARGET     [deprecated alias] retrosynthesis routes with the sourced-data levers
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
    """Accept an offline registered name or SMILES, with optional explicit ``name:``/``smiles:`` prefix.

    Delegates to the one shared identity parser (:func:`smartchem.identity_parse.resolve_target`) so the CLI and
    the typed service (:mod:`smartchem.service`) can never drift apart on the same string -- the whole point of
    SVC-REQ-01.  Behaviour and error messages are unchanged; ``IdentityParseError`` is a ``ValueError`` subclass,
    so the ``exit 2`` handlers below keep catching it.
    """
    from .identity_parse import InputKind, resolve_target
    return resolve_target(value, InputKind.AUTO)


def _parse_smiles(smiles: str):
    """Compatibility alias for callers that used the old private helper.

    Routes through the AUTO path with an explicit ``smiles:`` prefix -- byte-for-byte the old
    ``_parse_molecule("smiles:" + smiles)`` behaviour, including the error string, which quotes the prefixed form.
    """
    from .identity_parse import InputKind, resolve_target
    return resolve_target("smiles:" + smiles, InputKind.AUTO)


def _add_recompile_flags(p) -> None:
    """The ONE argv surface shared by ``recompile`` and its ``compile`` alias (CLI-CAN-01).

    Numeric/list knobs default to ``None`` (not to a concrete value) so :func:`_recompile_request_from_args` can
    tell an omitted flag from an explicitly-passed one and record its :class:`~smartchem.service.FieldOrigin`
    faithfully -- a default is then a VISIBLE ``origin=DEFAULT`` field, never an invisible command branch (standard
    section 13.1).
    """
    p.add_argument("target", help="compound name or SMILES (name:... and smiles:... are accepted explicitly)")
    p.add_argument("--reagents", nargs="*", default=None, metavar="TARGET",
                   help="small helper reagents by name or SMILES (default: water; an empty list means the default)")
    p.add_argument("--have", nargs="*", default=None, metavar="TARGET",
                   help="precursors already on the bench, by name or SMILES -- routes may bottom out here")
    p.add_argument("--max-depth", type=_positive_int, default=None, metavar="N",
                   help="retrosynthesis depth (default 3)")
    p.add_argument("--max-routes", type=_positive_int, default=None, metavar="N",
                   help="maximum unique routes returned (default 100)")
    p.add_argument("--cut-budget", type=_positive_int, default=None, metavar="N",
                   help="candidate rewrite budget per expanded target (default 20000)")
    p.add_argument(
        "--no-commodities", "--elements", dest="no_commodities", action="store_true",
        help=(
            "disable poor-man's commodity terminals; the legacy --elements spelling does NOT add automatic "
            "element terminals to the current structural search"
        ),
    )
    p.add_argument("--json", action="store_true",
                   help="emit the stable versioned response schema instead of the human render (standard 14.3)")
    p.add_argument("--emit-request", action="store_true",
                   help="print the typed request JSON and exit WITHOUT running the search (the canonical request "
                        "identity; used to prove alias-equality across the command matrix)")
    p.add_argument("--quiet", action="store_true",
                   help="suppress the narrative render, but NEVER a blocker in a successful-looking result (14.3)")


def _recompile_request_from_args(args):
    """Map the shared ``recompile`` argv to the one typed :class:`~smartchem.service.CompilationRequest`.

    This is the alias-independence engine: ``compile`` and ``recompile`` both build their request HERE, from the
    service's ONE default table (:func:`smartchem.service.build_recompile_request`), so equal explicit flags always
    resolve to an equal ``semantic_digest`` and thus an equal request/result (CLI-CAN-01's acceptance test).  An
    omitted knob is passed as ``None`` so the builder records it ``DEFAULT``; ``--no-commodities`` is the sole
    explicit toggle of the commodity terminal, recorded ``EXPLICIT`` only when opted out.
    """
    from .service import build_recompile_request
    # An empty `--reagents` list (the flag given with no values) is coerced to the DEFAULT reagent pool, exactly as
    # the legacy `compile` did (`compile_synthesis` injected water on an empty pool).  This keeps the two aliases on
    # ONE default -- an empty pool is not a runnable capped-scission search, so treating it as "use the default"
    # rather than as "()" is what stops `compile` (water-injected) and `recompile` (formerly a crash) from executing
    # two different searches for a byte-identical emitted request.  `--have` empty is a legitimate empty stock and is
    # left as-is.
    return build_recompile_request(
        args.target,
        helper_reagents=tuple(args.reagents) if args.reagents else None,
        stock_materials=tuple(args.have) if args.have is not None else None,
        commodities_enabled=False if args.no_commodities else None,
        max_depth=args.max_depth,
        max_routes=args.max_routes,
        cut_budget=args.cut_budget,
    )


def _emit_or_json(args, request) -> "int | None":
    """Centralise the ``--emit-request``/``--json`` views over any built request.

    Returns the exit code if it handled the invocation (so the caller returns early), else ``None`` (fall through
    to the human render).  ``--emit-request`` echoes the request WITHOUT searching (cheap, deterministic, canonical
    -- the matrix surface); ``--json`` runs the service and emits the typed response with its section-14.4 exit code.
    """
    if args.emit_request:
        from .service import serialize_request
        print(serialize_request(request))
        return 0
    if args.json:
        from .service import run_compilation, serialize_response
        response = run_compilation(request)
        print(serialize_response(response))
        return response.exit_code
    return None


def _render_recompile_response(response, *, quiet: bool) -> str:
    """Human render of a typed compilation response, retaining tiers, receipts, unknowns and IDs (standard 14.3).

    ``--quiet`` drops the descriptive lines but NEVER a blocker in a successful-looking result -- identity losses,
    a partial-search warning, and the outcome banner are always shown.
    """
    from .service import ResponseOutcome
    ir = response.compilation_ir
    lines = []
    if ir is None:  # a refusal/invalid outcome carries no IR -- surface every diagnostic, quiet or not.
        lines.append(f"recompile: {response.outcome.value} (exit {response.exit_code})")
        lines.extend(f"  {d}" for d in response.diagnostics)
        return "\n".join(lines)

    lines.append(f"recompile {ir.target.canonical_repr!r}  --  outcome: {response.outcome.value} "
                 f"(exit {response.exit_code})")
    if not quiet:
        lines.append(f"  target: {ir.target.canonical_repr} [{ir.target.layer.value}]")
        lines.append(f"  search: {response.standard_status} (engine: {ir.search_status.value}); "
                     f"candidates: {ir.candidate_count}")
        lines.append(f"  receipt: {ir.search_receipt_digest[:16]}")
    # blockers/unknowns are NEVER suppressed by --quiet.
    for loss in ir.identity_losses:
        lines.append(f"  IDENTITY LOSS: {loss}")
    if not ir.complete_within_bounds:
        lines.append("  SEARCH WAS PARTIAL: absence of a route is not evidence one does not exist -- "
                     "raise --cut-budget/--max-routes/--max-depth or widen the inventory.")
    if response.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE:
        lines.append("  TARGET ALREADY AVAILABLE on the declared terminal stock; no synthesis was searched. "
                     "Quantity, assay, phase, grade and fitness remain unassessed.")
    if response.outcome is ResponseOutcome.NO_ROUTE_COMPLETE:
        lines.append("  NO ROUTE within the declared bounded search space. The search was COMPLETE; this is not a "
                     "claim about routes outside the current grammar or bounds.")
    if not quiet:
        for c in ir.candidates[:20]:
            lines.append(f"    [{c.candidate_kind}/{c.readiness_tier}] {c.equation}  #{c.candidate_digest[:12]}")
        if ir.candidate_count > 20:
            lines.append(f"    ... and {ir.candidate_count - 20} more candidate(s)")
    return "\n".join(lines)


def _cmd_recompile(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="python -m smartchem recompile",
        description="Canonical synthesis verb: compile a target into the typed, bucket-terminated route-search "
                    "response through one service authority (standard section 14.1).",
    )
    _add_recompile_flags(p)
    args = p.parse_args(argv)

    try:
        request = _recompile_request_from_args(args)
    except (ValueError, TypeError) as exc:
        print(f"recompile: invalid request: {exc}", file=sys.stderr)
        return 2

    handled = _emit_or_json(args, request)
    if handled is not None:
        return handled

    from .service import run_compilation
    response = run_compilation(request)
    print(_render_recompile_response(response, quiet=args.quiet))
    return response.exit_code


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
    p.add_argument("--json", action="store_true",
                   help="emit the stable versioned response schema via the service instead of the edge list")
    p.add_argument("--emit-request", action="store_true",
                   help="print the typed decompile request JSON and exit WITHOUT descending")
    args = p.parse_args(argv)

    try:
        if args.smiles:  # reduce parsed structure to the formula-native decompiler input
            mol = _parse_molecule("smiles:" + args.target)
            target = "".join(f"{el}{n if n > 1 else ''}" for el, n in sorted(mol.formula.items()))
        else:
            target = args.target
        inventory = tuple(args.inventory) if args.inventory is not None else example_inventory()
    except (DecompilerError, ValueError) as exc:
        print(f"decompile: invalid chemistry input: {exc}", file=sys.stderr)
        return 2

    # --json/--emit-request route through the ONE typed service over the SAME resolved target + inventory, so the
    # machine views cannot drift from the human edge list below (CLI-CAN-01).  The service default inventory is
    # pure elements; the decompile CLI defaults to the richer example inventory, so the resolved `inventory` (not
    # the builder default) is what is threaded in -- the two defaults are reconciled here, not left to diverge.
    if args.emit_request or args.json:
        from .service import (
            build_decompile_request,
            run_compilation,
            serialize_request,
            serialize_response,
        )
        # `example_inventory()` yields `Formula` OBJECTS while `--inventory` yields strings; the typed request keys
        # on canonical formula TEXT (which `_run_decompile` re-parses with `Formula.parse`).  Normalise both to
        # `repr` -- the formula text the decompiler uses throughout, and a proven `Formula.parse` round-trip.
        inventory_text = tuple(item if isinstance(item, str) else repr(item) for item in inventory)
        try:
            req = build_decompile_request(
                target,
                formula_inventory=inventory_text,
                max_multiplicity=args.max_multiplicity,
                budget=args.budget,
                max_edges=args.max_edges,
            )
        except (ValueError, TypeError) as exc:
            print(f"decompile: invalid request: {exc}", file=sys.stderr)
            return 2
        if args.emit_request:
            print(serialize_request(req))
            return 0
        response = run_compilation(req)
        print(serialize_response(response))
        return response.exit_code

    try:
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
        description="[DEPRECATED alias of `recompile`, one cycle] Compile a bounded, ranked, graded, "
                    "bucket-terminated route dossier for a target.",
    )
    _add_recompile_flags(p)
    args = p.parse_args(argv)

    # Build the SAME typed request as `recompile` from the SAME default table (standard section 14.1: a legacy
    # alias MUST construct the same request and MUST NOT keep divergent defaults).  The rich graded dossier below
    # then runs off the request's RESOLVED parameters, so there is exactly one default table, not two.
    try:
        request = _recompile_request_from_args(args)
    except (ValueError, TypeError) as exc:
        print(f"compile: invalid request: {exc}", file=sys.stderr)
        return 2

    print("compile: `compile` is a deprecated alias of `recompile`; prefer `python -m smartchem recompile` "
          "(kept one deprecation cycle -- standard section 14.1).", file=sys.stderr)

    handled = _emit_or_json(args, request)
    if handled is not None:
        return handled

    try:
        target = _parse_molecule(request.target_input)
        reagents = tuple(_parse_molecule(s) for s in request.helper_reagents)
        available = tuple(_parse_molecule(s) for s in request.stock_materials)
        compiled = compile_synthesis(
            target,
            reagents=reagents,
            available=available,
            max_depth=request.search_bounds.value("max_depth"),
            max_routes=request.search_bounds.value("max_results"),
            cut_budget=request.search_bounds.value("cut_budget"),
            commodities=() if not request.terminal_policy.commodities_enabled else None,
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
    if command == "recompile":
        return _cmd_recompile(rest)
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
