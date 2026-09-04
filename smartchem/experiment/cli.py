"""The Experiment Compiler command line -- give it a target and inventory, get ranked route dossiers.

    python -m smartchem.experiment "CC(=O)Nc1ccc(O)cc1" \\
        --have "Nc1ccc(O)cc1" --reagents "O" "CC(=O)O" "CC(=O)OC(=O)C" \\
        --max-temp 1473 --max-pressure 1.5

It builds the ONE shared typed ``CompilationRequest`` (SVC-REQ-01) from its argv and renders its dossier through
the SAME shared engine ``compile`` uses (:func:`~smartchem.experiment.compile.compile_synthesis`), built from the
request's RESOLVED parameters -- so it no longer runs a second search or a second argv parse (CLI-CAN-02 remainder).
``--emit-request`` and ``--json`` expose the machine views through :func:`~smartchem.service.run_compilation`,
exactly as ``recompile``/``compile`` do.  The human dossier still enumerates candidate routes from the decompiler
(E5), autoloads sourced stability for every discovered species (PubChem/Wikidata/Bradley, cached) via the
request's section-9 provider lever, ranks them against the bench (``--max-temp`` K, ``--max-pressure`` atm), and
prints the top route as a chemist-facing DOSSIER -- under the honesty banner (no success guarantee, no kinetic
rate; every other claim graded), every number in its epistemic bucket.

As a DEPRECATED alias of ``recompile`` (standard section 14.1, one deprecation cycle), it builds the byte-identical
typed request under equal flags and keeps NO divergent defaults: the reality-respecting default is the OFFLINE,
reproducible seed + cache provider, a full depth-3 search, and commodity terminals ON.  Its "download and go" live
fetch is the EXPLICIT ``--network`` opt-in -- a network fetch is never the default, and section 9/13 requires the
fetched data to carry a snapshot, so a defaulted request stays byte-reproducible and its response replayable.
"""
from __future__ import annotations

import argparse
import sys

from ..decompiler import IdentityUnsupportedError
from ..smiles import SmilesError, parse_smiles
from ..structure_descent import ScissionError
from .drafter import ConstraintBox

# CLI-EXIT-01 exit codes as LOCAL literals (so main()'s top-level guard reports them even when the escaping bug is a
# broken import): 70 == internal software error (ERROR_INTERNAL); 141 == the conventional SIGPIPE code.
_EXIT_INTERNAL = 70
_EXIT_SIGPIPE = 141

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


def _syn_domain_exit(exc: BaseException) -> int:
    """Map a synthesize build/search DOMAIN error to its section-14.4 exit code, concise stderr, never a traceback.

    A chemistry-MODEL-boundary refusal (an unsupported scission or an unperceived identity layer) -> 5; an INVALID
    input (an unparseable identity, an empty/invalid target or reagent, a bad value) -> 2 -- the SAME 5/2 split the
    recompile/compile verbs give the identical error (and the same families the main CLI's ``_domain_exit`` uses).

    ERR-EVIDENCE-01: this is called ONLY on genuine DOMAIN exceptions.  The input stages catch ``(ScissionError,
    ValueError, TypeError)`` because a raised ValueError/TypeError THERE is invalid input; the ENGINE stage
    (``compile_synthesis``, which runs the conditions/route/DAG search) catches ONLY the model-boundary family
    ``(ScissionError, IdentityUnsupportedError)``, so an internal fault from the engine (a ValueError/TypeError bug --
    the exact class ERR-EVIDENCE-01 stopped ``assembly_conditions`` from laundering into a false "conditions unknown")
    is NOT re-laundered here into a false "invalid chemistry request".  It escapes to ``main()``'s top-level exit-70
    guard (ERROR_INTERNAL), matching the ``--json`` path's ``run_compilation`` contract.
    """
    if isinstance(exc, (ScissionError, IdentityUnsupportedError)):
        print(f"synthesize: request refused at the current chemistry-model boundary: {exc}", file=sys.stderr)
        return 5
    print(f"synthesize: unsupported or invalid chemistry request: {exc}", file=sys.stderr)
    return 2


def _synthesize_request(args):
    """Build the ONE shared typed ``CompilationRequest`` (SVC-REQ-01) from ``synthesize``'s argv.

    ``synthesize`` renders its human dossier through the SHARED engine (``compile_synthesis``) built from THIS
    request's resolved params -- it no longer keeps its own route engine (CLI-CAN-02 remainder).  The request carries
    the alias-independent identity (so ``synthesize --emit-request`` / ``--json`` are comparable to ``recompile``'s)
    and, load-bearing, the section-9 :class:`~smartchem.service.EvidenceProviderSelection` that DRIVES the stability
    autoload.  SVC-REQ-01 alias-unity (standard section 14.1): every OMITTED knob is threaded as ``None`` so the ONE
    builder records it ``origin=DEFAULT`` and applies recompile's SAME default table -- so ``synthesize X`` emits the
    byte-identical request as ``recompile X`` with NO divergent defaults (offline provider, depth 3, commodities on).
    The reality-respecting default is OFFLINE (reproducible seed + cache); the "download and go" live fetch is the
    EXPLICIT ``--network`` opt-in (``--offline`` explicitly stamps the default).  The builder VALIDATES the target and
    reagents, so it MAY raise a domain error (an empty or invalid target, an empty-string reagent); the caller wraps
    this build in the same 5/2 handler as the render, so such an input is a clean section-14.4 exit 2, never a
    traceback or a laundered exit-70 (red-team fold).
    """
    from ..identity_parse import EXPLICIT_CLI_FORMS, resolve_cli_target
    from ..service import NETWORK_PROVIDER, OFFLINE_PROVIDER, build_recompile_request
    # the section-14.2 identity surface, via the ONE shared resolver (same as recompile/compile): the positional
    # target (+ --input-kind) OR one explicit value-form flag; more than one, or none, is a loud domain error.
    target, input_kind = resolve_cli_target(
        args.target, args.input_kind,
        {form: getattr(args, form.replace("-", "_")) for form, _kind in EXPLICIT_CLI_FORMS},
    )
    return build_recompile_request(
        target,
        input_kind=input_kind,
        # SVC-REQ-01 alias-unity (standard 14.1 "same request under equal flags"): reagents/stock follow recompile's
        # rule EXACTLY -- an OMITTED or VALUELESS ``--reagents`` (both falsy) takes the default water pool, so
        # `synthesize X --reagents` and `recompile X --reagents` build the byte-identical request; an empty ``--have``
        # stays the honest empty stock (``is not None``, matching recompile). The emit still faithfully matches the
        # search (both use the water default), which is what the empty-reagents red-team fold actually required.
        helper_reagents=tuple(args.reagents) if args.reagents else None,
        stock_materials=tuple(args.have) if args.have is not None else None,
        commodities_enabled=False if args.no_commodities else None,
        max_depth=args.max_depth,
        max_routes=args.max_routes,
        cut_budget=args.cut_budget,
        max_temperature_k=args.max_temp,
        max_pressure_atm=args.max_pressure,
        # the reality-respecting provider lever: OFFLINE (reproducible) unless --network opts into the download-and-go
        # fetch; --offline stamps the default value EXPLICIT; neither -> None -> the builder's DEFAULT-origin offline.
        evidence_provider_selection=(
            NETWORK_PROVIDER if args.network else OFFLINE_PROVIDER if args.offline else None
        ),
    )


def main(argv: list[str] | None = None) -> int:
    from ..identity_parse import EXPLICIT_CLI_FORMS
    p = argparse.ArgumentParser(prog="python -m smartchem.experiment", description=__doc__)
    p.add_argument("target", nargs="?", default=None,
                   help="compound name or SMILES (name:.../smiles:... prefixes accepted), or use a section-14.2 "
                        "explicit form below")
    p.add_argument("--input-kind", choices=["auto", "name", "smiles", "inchi", "formula", "target-file"],
                   default=None,
                   help="how to read TARGET (standard section 14.2; default AUTO). A bare inchi/formula names "
                        "composition, not structure, so this structure search refuses it (exit 2, section 5.4)")
    for _form, _kind in EXPLICIT_CLI_FORMS:
        p.add_argument(f"--{_form}", default=None, metavar="TARGET",
                       help=f"give the target as {_kind.replace('_', ' ').lower()} (section-14.2 explicit form; "
                            f"mutually exclusive with the positional target and --input-kind)")
    # SVC-REQ-01 alias-unity: list/numeric knobs default to None (an OMITTED flag) so the ONE builder records them
    # origin=DEFAULT and applies recompile's SAME default table -- `synthesize X` emits recompile's byte-identical
    # request (default reagents=water, depth 3, routes 100, budget 20000).  A passed value is origin=EXPLICIT.
    p.add_argument("--have", nargs="*", default=None, metavar="TARGET",
                   help="precursors already on the bench (names or SMILES)")
    p.add_argument("--reagents", nargs="*", default=None, metavar="TARGET",
                   help="small helper reagents the cleavage may use (default: water)")
    p.add_argument("--max-temp", type=_positive_float, default=None, metavar="K",
                   help="the bench's maximum temperature in kelvin")
    p.add_argument("--max-pressure", type=_positive_float, default=None, metavar="ATM",
                   help="the bench's maximum pressure in atm")
    p.add_argument("--max-depth", type=_positive_int, default=None, help="retrosynthesis depth (default 3)")
    p.add_argument("--max-routes", type=_positive_int, default=None,
                   help="maximum unique routes returned (default 100)")
    p.add_argument("--cut-budget", type=_positive_int, default=None,
                   help="candidate rewrite budget per expanded target (default 20000)")
    p.add_argument(
        "--no-commodities", "--elements", dest="no_commodities", action="store_true",
        help="disable the poor-man's commodity terminals (table salt, vinegar, baking soda, ...), which are ON by "
             "default like `recompile`; routes then bottom out at pure elements instead of buyable stock",
    )
    # The reality-respecting provider lever (standard 14.1): OFFLINE (reproducible seed + cache) is the DEFAULT for
    # every verb; the "download and go" live fetch is the EXPLICIT --network opt-in.  --offline stamps the default
    # EXPLICIT.  Mutually exclusive; neither given -> the builder's DEFAULT-origin offline selection.
    _provider = p.add_mutually_exclusive_group()
    _provider.add_argument("--offline", action="store_true",
                           help="explicitly use the seed + cache only (already the default)")
    _provider.add_argument("--network", action="store_true",
                           help="the download-and-go opt-in: fetch sourced stability for discovered species from "
                                "the section-9 network provider (PubChem/Wikidata/Bradley). A live fetch is never "
                                "the default; fetched data carries a snapshot so the request stays replayable (14.1)")
    p.add_argument("--emit-request", action="store_true",
                   help="print the ONE typed request JSON (SVC-REQ-01) and exit WITHOUT searching -- the "
                        "canonical, alias-independent request identity, including the section-9 provider selection")
    p.add_argument("--json", action="store_true",
                   help="run the request through the ONE service (run_compilation) and print the typed response "
                        "JSON with its section-14.4 exit code, instead of the human dossier (SVC-REQ-01)")
    args = p.parse_args(argv)
    # CLI-EXIT-01 (ERR-EVIDENCE-01 fold): the top-level guarded service, mirroring `python -m smartchem`.  A DOMAIN
    # error is already caught inside _run and mapped to its section-14.4 code (2 invalid / 5 refused); anything that
    # ESCAPES -- e.g. an internal fault from the conditions/route/DAG engine now that ERR-EVIDENCE-01 stopped it being
    # laundered into a false "conditions unknown" -- is a genuine internal bug and exits 70 (ERROR_INTERNAL) with a
    # concise message, never a raw traceback.  argparse's SystemExit (a BaseException) passes through, so a bad flag
    # stays exit 2.  The 70/141 are LOCAL literals, robust to a broken .service import.
    try:
        return _run(args)
    except BrokenPipeError:
        # a downstream `| head`/`| less` close is a NORMAL shell condition, never an internal error -- do not launder
        # it into exit 70 (mirrors the main CLI's CLI-EXIT-01-F1 red-team fold).
        import os
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
        return _EXIT_SIGPIPE
    except Exception as exc:  # noqa: BLE001 -- the top-level exit-70 net; a domain error was already mapped in _run
        print(
            f"python -m smartchem.experiment: internal error [ERROR_INTERNAL]: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return _EXIT_INTERNAL


def _run(args) -> int:
    """Execute one parsed ``synthesize`` invocation.  DOMAIN errors are mapped to their section-14.4 code (2/5) here;
    an internal fault escapes to :func:`main`'s top-level exit-70 guard (ERR-EVIDENCE-01)."""
    # CLI-CAN-02 (remainder): synthesize builds the ONE shared typed request (SVC-REQ-01) and no longer runs a second
    # search or a second argv parse.  The build VALIDATES the target/reagents, so it is wrapped in the SAME 5/2 domain
    # handler as the render below: an invalid target/reagent is a clean section-14.4 exit (2/5) like recompile/compile,
    # never a traceback or a laundered exit-70 (red-team fold).
    try:
        request = _synthesize_request(args)
    except (ScissionError, ValueError, TypeError) as exc:
        return _syn_domain_exit(exc)

    # The MACHINE views go through the ONE service (run_compilation), exactly as recompile/compile do: --emit-request
    # echoes the canonical request identity WITHOUT searching; --json runs the request and emits the typed response
    # with its section-14.4 exit code.  So synthesize's machine contract IS run_compilation's, not a second one.
    if args.emit_request:
        from ..service import serialize_request
        print(serialize_request(request))
        return 0
    if args.json:
        from ..service import run_compilation, serialize_response
        response = run_compilation(request)
        print(serialize_response(response))
        return response.exit_code

    # The HUMAN dossier renders through the ONE shared engine `compile` uses (compile_synthesis), built from the
    # REQUEST's resolved parameters -- so synthesize no longer parses argv a second time or runs its own
    # search_routes/rank_routes/draft.  The TARGET resolves through the one parser service (the same resolution the
    # request and run_compilation use), carrying its section-5.3 losses; reagents/stock are helper inputs.
    try:
        from ..identity import representation_losses_for
        from ..identity_parse import IdentityParseError, resolve_identity
        # resolve ONCE through the one parser service: molecule + dropped features + the section-14.2 ParseReceipt.
        resolved = resolve_identity(request.target_input, request.input_kind)
        if resolved.molecule is None:
            raise IdentityParseError(
                f"{resolved.receipt.requested_kind.value} input resolved to a "
                f"{resolved.receipt.identity_layer}-layer identity ({resolved.receipt.normalized}) with no "
                "perceived structure; a synthesis search needs a molecule (a name or SMILES), not a bare "
                "formula/InChI (section 5.4)"
            )
        target, target_features = resolved.molecule, resolved.features
        parse_receipt_summary = resolved.receipt.summary()
        losses = () if target_features is None else representation_losses_for(request.target_input, target_features)
        reagents = tuple(_parse(s) for s in request.helper_reagents)
        available = tuple(_parse(s) for s in request.stock_materials)
    except (ScissionError, ValueError, TypeError) as exc:
        return _syn_domain_exit(exc)

    # An empty reagent pool has nothing for the capped-scission grammar to cut with.  run_compilation (the --json
    # path) returns INVALID here, so the human path agrees -- ONE contract, both views (a valueless --reagents is a
    # clean exit 2 on both, never a water-defaulted human dossier that disagrees with its own --json; red-team fold).
    if not reagents:
        return _syn_domain_exit(ValueError(
            "the capped-scission grammar requires at least one helper reagent, but the reagent pool is empty"
        ))

    # synthesize's unique download-and-go feature: source stability for the discovered route species (intermediates
    # included) under the request's section-9 provider lever.  The loader is invoked by compile_synthesis AFTER its
    # search -- so --offline is expressed ONCE, in the request identity, and read back HERE; there is no second
    # offline flag the engine could silently disagree with (CLI-CAN-02).  identifiers map the resolved input molecules
    # to their request strings so a provider has something to query by; intermediates fall back to seed + cache.
    identifiers = {}
    for mol, s in [(target, request.target_input), *zip(reagents, request.helper_reagents),
                   *zip(available, request.stock_materials)]:
        identifiers.setdefault(mol, s)
    allow_network = request.evidence_provider_selection.allow_network

    def _load_stability(species):
        from ..data.autoload import autoload_stability
        return autoload_stability(list(species), identifiers=identifiers, allow_network=allow_network)

    from ..data.thermo_extended import extended_thermo
    from .compile import compile_synthesis
    try:
        compiled = compile_synthesis(
            target,
            reagents=reagents,
            available=available,
            # commodities are sourced from the REQUEST's terminal policy (ON by default, --no-commodities/--elements
            # to disable) -- the SAME single source of truth `compile` reads, so the human search cannot diverge from
            # the request `--emit-request`/`--json` describe (SVC-REQ-01 alias-unity).
            commodities=() if not request.terminal_policy.commodities_enabled else None,
            max_depth=request.search_bounds.value("max_depth"),
            max_routes=request.search_bounds.value("max_results"),
            cut_budget=request.search_bounds.value("cut_budget"),
            thermo=extended_thermo(),
            losses=losses,
            box=ConstraintBox.of_bounds(request.constraints.bounds),
            stability_loader=_load_stability,
        )
    except (ScissionError, IdentityUnsupportedError) as exc:
        # ERR-EVIDENCE-01: the ENGINE stage catches ONLY the genuine model-boundary refusal family (-> exit 5).  A
        # ValueError/TypeError raised HERE is an internal fault (target/reagents were already validated above), NOT
        # invalid input, so it PROPAGATES to main()'s exit-70 guard instead of being laundered to a false domain 2/5.
        return _syn_domain_exit(exc)

    # The section-11 constraint disclosure through the ONE note authority -- APPLIED with the real fit/excluded/
    # unknown tally when routes were ranked against a bench box, DECLARED otherwise; identical to recompile/compile.
    from ..service import _fit_counts, constraint_note
    note = constraint_note(
        request.constraints.bounds, fit_counts=_fit_counts(compiled.ranked) if compiled.ranked else None
    )
    if note is not None:
        print(f"  {note}")
    # echo HOW the target was read (the section-14.2 ParseReceipt) -- the same provenance recompile/decompile
    # surface, so synthesize's human view no longer silently drops it (CLI-NAME-01).
    print(f"  {parse_receipt_summary}")
    print(compiled.render())
    # Exit codes mirror recompile/compile: a partial search is exit 4; else routes/target-in-stock is 0, no-route is 3.
    if compiled.search_receipt is not None and not compiled.search_receipt.complete_within_bounds:
        return 4
    return 0 if compiled.found_route else 3


if __name__ == "__main__":
    sys.exit(main())
