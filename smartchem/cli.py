"""``python -m smartchem`` -- the one coherent front door to SmartChem's chemistry verticals.

A chemist should be able to pick this up with ``--help`` alone and not have to learn the project's internal
module layout.  Six subcommands, each a thin wrapper over a built engine:

* ``plan TARGET``         -- the v0.6 human total-answer front door (PLAN-01): resolve one human chemical
                             identity through the single authority, report the strongest identity layer and the
                             (non-exhaustive) ambiguity set, refuse to guess a structure from a bare formula,
                             and route to ``recompile`` (a perceived constitution) or ``decompile`` (a bare
                             formula).  A materially-ambiguous paste (``CO`` = methanol or carbon monoxide) is
                             reported as INPUT_KIND_AMBIGUOUS, not silently resolved.
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

# The section 14.4 internal-error code, kept as a LOCAL literal (deliberately NOT imported from .service) so the
# top-level guard in main() can still report exit 70 even when the failure IS a broken import of the heavy
# service/chemistry stack -- if the constant were imported at the guard, that very import could be the thing that
# fails.  tests/test_cli_exit.py pins it equal to smartchem.service.EXIT_INTERNAL so the two never drift.
_EXIT_INTERNAL = 70
# The conventional exit code for a process whose downstream pipe reader closed early (128 + SIGPIPE=13).  A broken
# pipe (`| head`, `| less`) is a normal shell condition, NOT an internal software error, and this is none of the
# section-14.4 outcome codes, so it is never confused with a route/no-route/refusal verdict.
_EXIT_SIGPIPE = 141

_USAGE = f"""python -m smartchem <command> [args]

commands:
  plan TARGET           human front door: resolve identity, report layer + ambiguity, route to the primitive
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


def _domain_exit(exc: BaseException, prog: str) -> int:
    """Map a raised DOMAIN exception to its section-14.4 exit code, with a concise stderr line (CLI-ERR-01).

    The ONE error-classification authority every command routes through, so a refusal is exit 5 and an invalid
    input is exit 2 IDENTICALLY on every command/path/format -- no per-command hand-rolled mapping that could drift:

    * a chemistry-MODEL-boundary refusal (an unsupported scission, a charged/unsupported identity) -> 5 REFUSED;
    * an INVALID input (an unparseable identity/formula, an as-yet-unsupported input kind, a bad value) -> 2.

    A model-boundary refusal is checked FIRST because ``ScissionError``/``IdentityUnsupportedError`` are themselves
    ``ValueError`` subclasses -- classifying by the generic ValueError first would mislabel a refusal as invalid.
    An exception in NEITHER family is RE-RAISED untouched, so a genuine internal bug propagates to ``main()``'s
    top-level guard and becomes exit 70 -- it is never laundered into a domain 2/5 (the inverse of the 70 guard's
    own sin).  argparse's ``SystemExit`` / ``KeyboardInterrupt`` are ``BaseException``s the ``except Exception``
    call sites never catch, so they never reach here (a bad flag stays argparse's exit 2, ``--help`` stays 0).
    """
    from .decompiler import IdentityUnsupportedError
    from .structure_descent import ScissionError
    if isinstance(exc, (ScissionError, IdentityUnsupportedError)):
        print(f"{prog}: request refused at the current chemistry-model boundary: {exc}", file=sys.stderr)
        return 5
    if isinstance(exc, (ValueError, TypeError)):
        # IdentityParseError, DecompilerError, SmilesError are ValueErrors; a bad numeric/argument value is one too.
        print(f"{prog}: invalid chemistry input: {exc}", file=sys.stderr)
        return 2
    raise exc


def _add_process_flags(p) -> None:
    """Shared operator limits for all synthesis frontends; minutes are explicit."""
    p.add_argument("--process-profile", choices=("quick", "low-touch"), default=None,
                   help="editable operator preferences; unknown whole-step requirements never pass")
    for flag, description in (
        ("max-step-minutes", "elapsed minutes per step, including workup"),
        ("max-total-minutes", "sum of elapsed step minutes, including workup"),
        ("max-active-minutes", "sum of hands-on minutes across the route"),
        ("min-check-interval", "shortest interval in minutes at which you can return to check"),
    ):
        p.add_argument("--" + flag, type=float, default=None, metavar="MIN", help=description)
    p.add_argument("--attention", nargs="+", choices=("continuous", "periodic", "passive"), default=None,
                   help="permitted declared attention modes")
    p.add_argument("--agitation", nargs="+", choices=("none", "manual", "periodic", "continuous"), default=None,
                   help="permitted declared agitation modes; no inference from temperature")
    p.add_argument("--equipment", nargs="*", default=None, metavar="ID",
                   help="exact available equipment identifiers; empty list declares none")


def _process_bounds_from_args(args):
    from dataclasses import replace
    from .process_constraints import ProcessBounds, Attention, Agitation
    profile = getattr(args, "process_profile", None)
    values = {}
    for arg, field in (("max_step_minutes", "max_step_minutes"),
                       ("max_total_minutes", "max_total_minutes"),
                       ("max_active_minutes", "max_active_minutes"),
                       ("min_check_interval", "min_check_interval_minutes")):
        value = getattr(args, arg, None)
        if value is not None:
            values[field] = value
    for arg, field, enum in (("attention", "allowed_attention", Attention),
                              ("agitation", "allowed_agitation", Agitation)):
        value = getattr(args, arg, None)
        if value is not None:
            values[field] = tuple(enum(x.upper()) for x in value)
    equipment = getattr(args, "equipment", None)
    if equipment is not None:
        values["available_equipment"] = tuple(equipment)
    if profile is None and not values:
        return None
    bounds = ProcessBounds.preset(profile) if profile else ProcessBounds.unconstrained()
    return replace(bounds, **values)


def _add_recompile_flags(p) -> None:
    """The ONE argv surface shared by ``recompile`` and its ``compile`` alias (CLI-CAN-01).

    Numeric/list knobs default to ``None`` (not to a concrete value) so :func:`_recompile_request_from_args` can
    tell an omitted flag from an explicitly-passed one and record its :class:`~smartchem.service.FieldOrigin`
    faithfully -- a default is then a VISIBLE ``origin=DEFAULT`` field, never an invisible command branch (standard
    section 13.1).
    """
    from .identity_parse import EXPLICIT_CLI_FORMS
    _add_process_flags(p)
    p.add_argument("target", nargs="?", default=None,
                   help="compound name or SMILES (name:... and smiles:... are accepted explicitly). Alternatively "
                        "name the target with one of the section-14.2 explicit forms below")
    p.add_argument(
        "--input-kind", choices=["auto", "name", "smiles", "inchi", "formula", "target-file"], default=None,
        help=(
            "how to read TARGET (standard section 14.2; default AUTO: a registered name, else SMILES, honouring an "
            "inline name:/smiles: prefix). The parser resolves every form (ID-PARSE-01), but a bare inchi/formula "
            "names composition, not structure, so a STRUCTURE search refuses it as INVALID_INPUT (exit 2, section "
            "5.4) -- resolved, never silently mis-parsed; use name/smiles for a structure target"
        ),
    )
    for _form, _kind in EXPLICIT_CLI_FORMS:
        p.add_argument(
            f"--{_form}", default=None, metavar="TARGET",
            help=f"give the target as {_kind.replace('_', ' ').lower()} (standard section 14.2 explicit form; "
                 f"mutually exclusive with the positional target and --input-kind)",
        )
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
    p.add_argument("--max-temp", type=float, default=None, metavar="K",
                   help="section-11 bench temperature ceiling in K. Part of the request identity AND APPLIED: routes "
                        "are ranked against the bench, and a route needing a hotter step is EXCLUDED (CLI-CAN-02)")
    p.add_argument("--max-pressure", type=float, default=None, metavar="ATM",
                   help="section-11 bench pressure ceiling in atm. APPLIED to route ranking (see --max-temp): a route "
                        "needing higher pressure is EXCLUDED")
    p.add_argument("--min-pressure", type=float, default=None, metavar="ATM",
                   help="section-11 bench pressure floor in atm. APPLIED to route ranking (see --max-temp); a route "
                        "needing lower pressure is EXCLUDED; must not exceed --max-pressure")
    p.add_argument(
        "--no-commodities", "--elements", dest="no_commodities", action="store_true",
        help=(
            "disable poor-man's commodity terminals; the legacy --elements spelling does NOT add automatic "
            "element terminals to the current structural search"
        ),
    )
    p.add_argument(
        "--match-layer", choices=["formula", "constitution", "configuration", "isotopic"], default=None,
        help=(
            "the section 5.1 identity layer terminal matching is performed at (default: constitution, the "
            "structural layer). A finer layer (configuration/isotopic) is REFUSED until stereo/isotope perception "
            "lands, and formula is refused for a structure search (section 5.4) -- never silently downgraded"
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
    from .identity import MatchLayer
    from .identity_parse import EXPLICIT_CLI_FORMS, resolve_cli_target
    from .service import build_recompile_request
    # The section-14.2 identity surface -- the positional target (+ --input-kind) OR one explicit value-form flag
    # (--name/--smiles/--inchi/--formula/--target-file) -- is reconciled by the ONE shared resolver, so recompile,
    # compile and synthesize cannot drift on it; giving the target more than one way (or none) is a loud exit-2.
    target, input_kind = resolve_cli_target(
        args.target, args.input_kind,
        {form: getattr(args, form.replace("-", "_")) for form, _kind in EXPLICIT_CLI_FORMS},
    )
    # An empty `--reagents` list (the flag given with no values) is coerced to the DEFAULT reagent pool, exactly as
    # the legacy `compile` did (`compile_synthesis` injected water on an empty pool).  This keeps the two aliases on
    # ONE default -- an empty pool is not a runnable capped-scission search, so treating it as "use the default"
    # rather than as "()" is what stops `compile` (water-injected) and `recompile` (formerly a crash) from executing
    # two different searches for a byte-identical emitted request.  `--have` empty is a legitimate empty stock and is
    # left as-is.
    return build_recompile_request(
        target,
        input_kind=input_kind,
        helper_reagents=tuple(args.reagents) if args.reagents else None,
        stock_materials=tuple(args.have) if args.have is not None else None,
        commodities_enabled=False if args.no_commodities else None,
        max_depth=args.max_depth,
        max_routes=args.max_routes,
        cut_budget=args.cut_budget,
        match_layer=MatchLayer[args.match_layer.upper()] if args.match_layer else None,
        max_temperature_k=args.max_temp,
        min_pressure_atm=args.min_pressure,
        max_pressure_atm=args.max_pressure,
        process=_process_bounds_from_args(args),
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
        if response.parse_receipt_summary:  # provenance echo, if the target got far enough to be read
            lines.append(f"  {response.parse_receipt_summary}")
        return "\n".join(lines)

    lines.append(f"recompile {ir.target.canonical_repr!r}  --  outcome: {response.outcome.value} "
                 f"(exit {response.exit_code})")
    if response.request.constraints.process.constrains_anything:
        lines.append(f"  process selection: {response.process_selection_status}; "
                     f"{len(response.admissible_route_digests)} admissible returned routes")
    if not quiet:
        lines.append(f"  target: {ir.target.canonical_repr} [{ir.target.layer.value}]")
        lines.append(f"  identity match layer: {response.request.identity_policy.match_layer.value} (ID-LAYER-02)")
        lines.append(f"  search: {response.standard_status} (engine: {ir.search_status.value}); "
                     f"candidates: {ir.candidate_count}")
        _r = ir.search_receipt
        _u = lambda v: "UNKNOWN" if v is None else v  # noqa: E731 -- section 8.1 "null, not zero" display
        lines.append(
            f"  receipt ({_r.search_kind}) {_r.digest[:16]}: nodes={_u(_r.nodes_visited)}, "
            f"transforms={_u(_r.transforms_considered)}, results={_u(_r.results_returned)}"
            + (f"; stopped: {_r.stop_reason}" if _r.stop_reason else "")
        )
    # blockers/unknowns are NEVER suppressed by --quiet.  A loss is a first-class typed record (IR-LOSS-01); the
    # machine --json payload carries the STRUCTURED record, and this same summary() line is the derived string the
    # response's semantic projection exposes -- so the human and JSON views cannot disagree (CLI-JSON-01 agreement).
    for loss in ir.identity_losses:
        lines.append(f"  {loss.summary()}")
    # SVC-REQ-01 alias-collapse: the real search diagnostics AND the identity-resolution RECEIPT (now a first-class
    # parse_receipt_summary field, no longer a diagnostics line) both reach the human view, so it reports how the
    # target was read exactly as --json does (CLI-JSON-01 agreement) -- while the receipt stays out of result_digest.
    for d in response.diagnostics:
        lines.append(f"  {d}")
    if response.parse_receipt_summary:
        lines.append(f"  {response.parse_receipt_summary}")
    # SRCH-NO-01: the ONE section-8.3 no-route matrix label, uniform across the human render AND --json.  This one
    # line replaces the old split ("SEARCH WAS PARTIAL" for either incomplete cell + a separate NO_ROUTE_COMPLETE
    # line) so the four outcomes -- incomplete-empty vs complete-empty especially -- read distinctly everywhere.
    if response.search_space_status is not None:
        from .search import SECTION_8_3_NOTE
        lines.append(f"  search space [{response.search_space_status}]: "
                     f"{SECTION_8_3_NOTE[response.search_space_status]}")
    if response.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE:
        lines.append("  TARGET ALREADY AVAILABLE on the declared terminal stock; no synthesis was searched. "
                     "Quantity, assay, phase, grade and fitness remain unassessed.")
    if not quiet:
        for c in ir.candidates[:20]:
            lines.append(f"    [{c.candidate_kind}/{c.readiness_tier}] {c.equation}  #{c.candidate_digest[:12]}")
        if ir.candidate_count > 20:
            lines.append(f"    ... and {ir.candidate_count - 20} more candidate(s)")
    # CLI-CAN-02 brick 2: the section-11 bench-fit ranking (best first).  The APPLIED/DECLARED note is already in
    # diagnostics (always shown); this surfaces the per-route disposition + reasons so the human view carries the
    # same facts the --json ranked_route_dossiers do (CLI-JSON-01 agreement).  Shown when not --quiet, like candidates.
    if not quiet and response.ranked_route_dossiers:
        lines.append("  ranked routes (best first; section-11 bench fit):")
        for i, r in enumerate(response.ranked_route_dossiers[:20], 1):
            lines.append(f"    {i}. [{r.fit_status}/{r.readiness_tier}] {r.equation}  #{r.route_digest[:12]}")
            for e in r.exclusions:
                lines.append(f"        EXCLUDED: {e}")
            for g in r.gaps:
                lines.append(f"        GAP: {g}")
        if len(response.ranked_route_dossiers) > 20:
            lines.append(f"    ... and {len(response.ranked_route_dossiers) - 20} more ranked route(s)")
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
    except Exception as exc:  # noqa: BLE001 -- classified by the ONE authority; a non-domain error re-raises to 70
        return _domain_exit(exc, "recompile")

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

    from .decompiler import build_decomposition, example_inventory

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
    except Exception as exc:  # noqa: BLE001 -- routed to the ONE classifier; a non-domain error re-raises to 70
        return _domain_exit(exc, "decompile")

    # `example_inventory()` yields `Formula` OBJECTS while `--inventory` yields strings; the typed request keys on
    # canonical formula TEXT (which `_run_decompile` re-parses with `Formula.parse`).  Normalise both to `repr` --
    # the formula text the decompiler uses throughout, and a proven `Formula.parse` round-trip.
    inventory_text = tuple(item if isinstance(item, str) else repr(item) for item in inventory)

    def _decompile_request():
        """Build the typed decompile request the machine views serialize and the human view reads its outcome from.

        For --smiles the SMILES (not the pre-reduced formula) is handed to the service with input_kind=SMILES, so the
        service performs the reduction AND records the section-5.3 IdentityLoss into the response -- the same BLOCKER
        the human render prints, so the two views never disagree and structure is never silently discarded.
        """
        from .identity_parse import InputKind
        from .service import build_decompile_request
        return build_decompile_request(
            args.target if args.smiles else target,
            input_kind=InputKind.SMILES if args.smiles else None,
            formula_inventory=inventory_text,
            max_multiplicity=args.max_multiplicity,
            budget=args.budget,
            max_edges=args.max_edges,
        )

    # --json/--emit-request route through the ONE typed service over the SAME resolved target + inventory, so the
    # machine views cannot drift from the human edge list below (CLI-CAN-01).  The service default inventory is
    # pure elements; the decompile CLI defaults to the richer example inventory, so the resolved `inventory` (not
    # the builder default) is what is threaded in -- the two defaults are reconciled here, not left to diverge.
    if args.emit_request or args.json:
        from .service import run_compilation, serialize_request, serialize_response
        try:
            req = _decompile_request()
        except Exception as exc:  # noqa: BLE001 -- routed to the ONE classifier; a non-domain error re-raises to 70
            return _domain_exit(exc, "decompile")
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
    except Exception as exc:  # noqa: BLE001 -- routed to the ONE classifier; a non-domain error re-raises to 70
        return _domain_exit(exc, "decompile")

    print(f"decompile {graph.target!r}  --  status: {graph.status}")
    # Surface the typed service outcome + section 8.2 status the --json view carries, from the SAME request, so the
    # human and machine views agree on them (CLI-JSON-01).  A formula decompile is cheap, so deriving these from the
    # service here (while the rich edge list below still comes from build_decomposition) costs nothing meaningful;
    # collapsing the two decompile calculations into one is the same two-view seam named for recompile.
    from .service import run_compilation
    _resp = run_compilation(_decompile_request())
    print(f"  outcome: {_resp.outcome.value}; status: {_resp.standard_status}")
    # SRCH-NO-01: the section-8.3 no-route matrix label, the SAME token the --json view carries, so the human and
    # machine decompile views agree on the four-outcome distinction (not only outcome + section-8.2 status).
    if _resp.search_space_status is not None:
        from .search import SECTION_8_3_NOTE
        print(f"  search space [{_resp.search_space_status}]: {SECTION_8_3_NOTE[_resp.search_space_status]}")
    # every section-5.3 loss the service RECORDED, via the SAME summary strings the machine --json view carries, so
    # the two views cannot disagree (CLI-JSON-01).  For --smiles that is the SMILES->formula reduction PLUS any
    # ID-STEREO-01 stereo/isotope/local-charge blocker the input declared -- structure/features never silently lost.
    for _summary in _resp.identity_loss_summaries:
        print(f"  {_summary}")
    # the real search diagnostics AND the identity-resolution RECEIPT (now the first-class parse_receipt_summary
    # field, no longer a diagnostics line; SVC-REQ-01 alias-collapse) both reach the human view, so it reports how
    # the target was read exactly as --json does (CLI-JSON-01 agreement) -- receipt kept out of result_digest.
    for _d in _resp.diagnostics:
        print(f"  {_d}")
    if _resp.parse_receipt_summary:
        print(f"  {_resp.parse_receipt_summary}")
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
    except Exception as exc:  # noqa: BLE001 -- classified by the ONE authority; a non-domain error re-raises to 70
        return _domain_exit(exc, "compile")

    print("compile: `compile` is a deprecated alias of `recompile`; prefer `python -m smartchem recompile` "
          "(kept one deprecation cycle -- standard section 14.1).", file=sys.stderr)

    handled = _emit_or_json(args, request)
    if handled is not None:
        return handled

    try:
        from .identity import representation_losses_for
        from .identity_parse import resolve_target_with_features
        # Resolve the target HONOURING request.input_kind (CLIERR-COMPILE-INPUTKIND-BYPASS red-team fix): a declared
        # but unresolved kind (inchi/formula/target-file) raises IdentityParseError -> _domain_exit -> exit 2, so the
        # human path matches the --json/recompile paths instead of silently AUTO-mis-parsing to a confident dossier.
        # WITH features, so a stereo/isotope/zwitterion target threads its section-5.3 losses into the sourced-evidence
        # rungs (EVD-KEY-01 end-to-end bite): a sourced selectivity/kinetics verdict cannot survive a matching blocker.
        target, target_features = resolve_target_with_features(request.target_input, request.input_kind)
        losses = () if target_features is None else representation_losses_for(request.target_input, target_features)
        reagents = tuple(_parse_molecule(s) for s in request.helper_reagents)
        available = tuple(_parse_molecule(s) for s in request.stock_materials)
        from .experiment.drafter import ConstraintBox
        compiled = compile_synthesis(
            target,
            reagents=reagents,
            available=available,
            max_depth=request.search_bounds.value("max_depth"),
            max_routes=request.search_bounds.value("max_results"),
            cut_budget=request.search_bounds.value("cut_budget"),
            commodities=() if not request.terminal_policy.commodities_enabled else None,
            thermo=extended_thermo(),
            losses=losses,
            # CLI-CAN-02 brick 2: APPLY the section-11 bench box to route ranking here too, so `compile --max-temp`
            # genuinely fits the routes -- the SAME rank_routes(box) the recompile service uses (alias coherence).
            box=ConstraintBox.of_bounds(request.constraints.bounds, process=request.constraints.process),
            # STEREO-DOSSIER-01: the SAME resolved target features already feeding the section-5.3 losses now ALSO
            # surface the perceived CIP R/S + configuration completeness in the human dossier header (perception only).
            target_features=target_features,
        )
    except Exception as exc:  # noqa: BLE001 -- ScissionError -> 5, ValueError -> 2 via the ONE classifier; else 70
        return _domain_exit(exc, "compile")
    # CLI-CAN-02 brick 2 (was HON-CLI-01, brick 1): `compile`'s human path renders a compile_synthesis dossier, so it
    # discloses the section-11 constraint from its OWN applied ranking (compiled.ranked, now box-fitted) via the ONE
    # note authority -- APPLIED with the real fit/excluded/unknown tally when routes were ranked, DECLARED otherwise.
    # This can never drift from the recompile/--json disclosure (same constraint_note function).
    from .service import _fit_counts, constraint_note
    _note = constraint_note(
        request.constraints.bounds,
        fit_counts=_fit_counts(compiled.ranked) if compiled.ranked else None,
        process=request.constraints.process,
    )
    if _note is not None:
        print(f"  {_note}")
    print(compiled.render())
    if compiled.search_receipt is not None and not compiled.search_receipt.complete_within_bounds:
        return 4
    if compiled.ranked and not compiled.found_route:
        return 5
    return 0 if compiled.found_route else 3


def _cmd_plan(argv: list[str]) -> int:
    """The v0.6 human total-answer front door (PLAN-01): resolve identity, report it, route to the primitive.

    A THIN orchestration verb -- it does not fork search or duplicate a parser.  It resolves the target through
    the ONE identity authority, prints what was understood (normalized syntax, composition, identity layer, and
    the registry-known ambiguity set -- never an invented structure), then delegates to ``recompile`` (a perceived
    constitution) or ``decompile`` (a bare-formula composition), surfacing that primitive's typed outcome.
    """
    import argparse

    from .identity_parse import EXPLICIT_CLI_FORMS, InputKind, resolve_cli_target
    from .plan import plan, plan_result_to_payload, render_plan_human

    p = argparse.ArgumentParser(
        prog="python -m smartchem plan",
        description="Resolve a human chemical identity, report the strongest identity layer perceived, expose "
                    "ambiguity instead of guessing structure, and route to the eligible compiler primitive.",
    )
    p.add_argument("target", nargs="?", default=None,
                   help="the identity: a chemical FORMULA (e.g. CuSO4·5H2O, C8H10N4O2, SO4^2-), a registered name, "
                        "or SMILES. Wikipedia-style Unicode subscripts/middle-dot hydrates are accepted")
    p.add_argument(
        "--input-kind", choices=["auto", "name", "smiles", "inchi", "formula", "target-file"], default=None,
        help="how to read TARGET (standard section 14.2; default AUTO: a registered name, else SMILES, else a "
             "chemical formula -- formula is tried LAST so it never steals a valid name/SMILES)",
    )
    for _form, _kind in EXPLICIT_CLI_FORMS:
        p.add_argument(
            f"--{_form}", default=None, metavar="TARGET",
            help=f"give the target as {_kind.replace('_', ' ').lower()} (standard section 14.2 explicit form; "
                 f"mutually exclusive with the positional target and --input-kind)",
        )
    p.add_argument("--json", action="store_true",
                   help="emit the machine-readable plan payload (identity + delegated response) instead of the render")
    args = p.parse_args(argv)

    try:
        explicit_forms = {name: getattr(args, name.replace("-", "_")) for name, _ in EXPLICIT_CLI_FORMS}
        target, kind = resolve_cli_target(args.target, args.input_kind, explicit_forms)
    except Exception as exc:  # noqa: BLE001 -- routed to the ONE classifier; a non-domain error re-raises to 70
        return _domain_exit(exc, "plan")

    result = plan(target, kind if kind is not None else InputKind.AUTO)
    if args.json:
        import json

        print(json.dumps(plan_result_to_payload(result), indent=2, sort_keys=True))
    else:
        print(render_plan_human(result))
    return result.exit_code


def _dispatch(command: str, rest: list[str]) -> int:
    """Route one command to its handler, returning its section-14.4 exit code (2 for an unknown command)."""
    if command == "plan":
        return _cmd_plan(rest)
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
    # CLI-EXIT-01: the top-level guarded service.  A DOMAIN error is already caught inside each command and mapped
    # to its section-14.4 code (2 invalid / 5 refused / ...); anything that ESCAPES that is a genuine internal bug,
    # which the standard (section 14.4) requires to exit 70 (ERROR_INTERNAL) with a concise message -- never a raw
    # traceback and never Python's default exit 1.  argparse's own SystemExit (a BaseException, not Exception) and
    # a KeyboardInterrupt pass through untouched, so --help stays 0 and a bad-argument parse stays 2.  The exit-70
    # code is a LOCAL literal, so this guard reports it even when the escaping bug is a broken .service import.
    try:
        return _dispatch(command, rest)
    except BrokenPipeError:
        # a downstream reader (`| head`, `| less`) closed the pipe -- a NORMAL shell condition, never an internal
        # software error.  Do NOT launder it into exit 70 or a false ERROR_INTERNAL.  Redirect stdout to devnull so
        # the interpreter's shutdown flush cannot raise a SECOND BrokenPipeError, then exit with the conventional
        # SIGPIPE code.
        import os
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
        return _EXIT_SIGPIPE
    except Exception as exc:
        print(
            f"python -m smartchem: internal error [ERROR_INTERNAL]: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return _EXIT_INTERNAL
