"""The Experiment Compiler command line -- give it a target and inventory, get ranked route dossiers.

    python -m smartchem.experiment "CC(=O)Nc1ccc(O)cc1" \\
        --have "Nc1ccc(O)cc1" --reagents "O" "CC(=O)O" "CC(=O)OC(=O)C" \\
        --max-temp 1473 --max-pressure 1.5

It builds the ONE shared typed ``CompilationRequest`` (SVC-REQ-01) from its argv and renders its dossier through
the SAME shared engine ``compile`` uses (:func:`~smartchem.experiment.compile.compile_synthesis`), built from the
request's RESOLVED parameters -- so it no longer runs a second search or a second argv parse (CLI-CAN-02 remainder).
``--emit-request`` and ``--json`` expose the machine views through :func:`~smartchem.service.run_compilation`,
exactly as ``recompile``/``compile`` do.  The human dossier still enumerates candidate routes from the decompiler
(E5), autoloads sourced stability for every discovered species (PubChem/Wikidata/Bradley, cached; ``--offline``
uses seed + cache only) via the request's section-9 provider lever, ranks them against the bench (``--max-temp`` K,
``--max-pressure`` atm), and prints the top route as a chemist-facing DOSSIER -- under the honesty banner (no
success guarantee, no kinetic rate; every other claim graded), every number in its epistemic bucket.  This is the
"download and go" entry point.
"""
from __future__ import annotations

import argparse
import sys

from ..smiles import SmilesError, parse_smiles
from ..structure_descent import ScissionError
from .drafter import ConstraintBox

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

    A chemistry-MODEL-boundary refusal (an unsupported scission) -> 5; an INVALID input (an unparseable identity, an
    empty/invalid target or reagent, a bad value) -> 2.  This is the SAME 5/2 split the recompile/compile verbs give
    the identical builder error, so `synthesize ''` is a clean exit 2 like `recompile ''` -- it no longer laundered an
    INVALID_INPUT into ERROR_INTERNAL/exit-70 by validating the request OUTSIDE the handler (red-team fold).  A
    non-domain error is NOT caught by the call sites (`except (ValueError, TypeError)`), so a genuine internal bug
    still escapes to the top-level exit-70 guard -- it is never laundered into a domain 2/5.
    """
    if isinstance(exc, ScissionError):
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
    autoload -- ``--offline`` selects the offline provider, its absence the network provider.  Reagents and stock are
    passed as the RAW arg lists (``tuple(args.reagents)`` / ``tuple(args.have)``), so the emitted identity matches
    what the shared engine searches even when a flag is given empty -- ``synthesize``'s own defaults (depth 2,
    commodities only under ``--poor-mans``) are threaded explicitly.  The builder VALIDATES the target and reagents,
    so it MAY raise a domain error (an empty or invalid target, an empty-string reagent); the caller wraps this build
    in the same 5/2 handler as the render, so such an input is a clean section-14.4 exit 2, never a traceback or a
    laundered exit-70 (red-team fold).
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
        helper_reagents=tuple(args.reagents),
        stock_materials=tuple(args.have),
        commodities_enabled=bool(args.poor_mans),
        max_depth=args.max_depth,
        max_routes=args.max_routes,
        cut_budget=args.cut_budget,
        max_temperature_k=args.max_temp,
        max_pressure_atm=args.max_pressure,
        evidence_provider_selection=OFFLINE_PROVIDER if args.offline else NETWORK_PROVIDER,
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
    p.add_argument("--poor-mans", action="store_true",
                   help="also terminate routes at WIDELY-AVAILABLE commodity compounds (table salt, "
                        "vinegar, baking soda, ...) and print a shopping list -- so a route can bottom out "
                        "at stuff you can actually buy instead of at pure elements")
    p.add_argument("--emit-request", action="store_true",
                   help="print the ONE typed request JSON (SVC-REQ-01) and exit WITHOUT searching -- the "
                        "canonical, alias-independent request identity, including the section-9 provider selection")
    p.add_argument("--json", action="store_true",
                   help="run the request through the ONE service (run_compilation) and print the typed response "
                        "JSON with its section-14.4 exit code, instead of the human dossier (SVC-REQ-01)")
    args = p.parse_args(argv)

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
            commodities=None if args.poor_mans else (),
            max_depth=request.search_bounds.value("max_depth"),
            max_routes=request.search_bounds.value("max_results"),
            cut_budget=request.search_bounds.value("cut_budget"),
            thermo=extended_thermo(),
            losses=losses,
            box=ConstraintBox.of_bounds(request.constraints.bounds),
            stability_loader=_load_stability,
        )
    except (ScissionError, ValueError, TypeError) as exc:
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
