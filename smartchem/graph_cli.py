"""The ``smartchem graph`` verb: render the compiler's reasoning as an evidence-aware graph.

A THIN presentation front end over the SAME search objects the other verbs use -- it never
searches a second way, never parses a printed equation, and never promotes a formal candidate
into a sourced or executable synthesis.  Formula decomposition reuses
:func:`smartchem.decompiler.search_decomposition`; synthesis reuses
:func:`smartchem.experiment.routes.search_routes` / :func:`~smartchem.experiment.routes.search_dags`
and the shared identity parser (:func:`smartchem.cli._parse_molecule`).

Exit codes mirror the standard's incompleteness discipline: 0 when the underlying search is
complete-within-bounds (or an unattested single candidate), 4 when it is PARTIAL (so a script can
detect that candidates may be missing), 2 for a bad argument (argparse), and 5 when a projection is
refused (a display limit exceeded, a membership mismatch) -- a refusal is never laundered into a
diagram.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .decompiler import search_decomposition
from .experiment.routes import search_dags, search_routes
from .graph_projection import (
    GraphProjectionError,
    project_decomposition,
    project_synthesis,
    project_synthesis_ensemble,
    render_dot,
    render_html,
    render_mermaid,
    render_svg,
)

_COMPLETE = ("COMPLETE", "COMPLETE_WITHIN_BOUNDS", "UNATTESTED")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m smartchem graph",
        description="Render SmartChem's bounded chemical reasoning as an evidence-aware graph. "
                    "The diagram communicates the chemistry; it never invents it.",
    )
    p.add_argument("view", choices=("formula", "synthesis"),
                   help="formula: composition decomposition hypergraph; synthesis: route/DAG graph")
    p.add_argument("target", help="formula string (formula view) or molecule name/SMILES (synthesis)")
    p.add_argument("--format", choices=("json", "dot", "mermaid", "svg", "html"), default="json")
    p.add_argument("--output", type=Path, help="write to a file instead of stdout")
    p.add_argument("--max-visible-nodes", type=int, default=None,
                   help="html/display viewport ceiling; omitted nodes are disclosed, never clipped silently")
    # formula view
    p.add_argument("--inventory", nargs="*", default=(),
                   help="formula: molecular terminal buckets (empty = elements only, always a 1-edge star)")
    p.add_argument("--max-edges", type=int, default=500, help="formula: returned-edge budget")
    p.add_argument("--budget", type=int, default=100_000, help="formula: search work budget")
    # synthesis view
    p.add_argument("--reagents", nargs="*", default=(),
                   help="synthesis: helper reagents (name/SMILES); defaults to water if omitted")
    p.add_argument("--available", nargs="*", default=(),
                   help="synthesis: on-hand precursors that terminate the backward search")
    p.add_argument("--max-depth", type=int, default=2, help="synthesis: retrosynthetic depth")
    p.add_argument("--max-candidates", type=int, default=100,
                   help="synthesis: candidate cap (max_routes / max_dags)")
    p.add_argument("--dag", action="store_true",
                   help="synthesis: search convergent DAGs instead of linear routes")
    p.add_argument("--ensemble", action="store_true",
                   help="synthesis: project ALL returned candidates as one AND-OR graph (default: the first)")
    return p


def _project(args):
    if args.view == "formula":
        result = search_decomposition(
            args.target, inventory=tuple(args.inventory),
            budget=args.budget, max_edges=args.max_edges,
        )
        return project_decomposition(result)

    from .cli import _parse_molecule  # the one shared identity parser (lazy: avoids import cycle)

    target = _parse_molecule(args.target)
    reagents = tuple(_parse_molecule(s) for s in args.reagents) or (_parse_molecule("smiles:O"),)
    available = tuple(_parse_molecule(s) for s in args.available)
    if args.dag:
        search = search_dags(target, reagents=reagents, available=available,
                             max_depth=args.max_depth, max_dags=args.max_candidates)
        members = search.dags
    else:
        search = search_routes(target, reagents=reagents, available=available,
                               max_depth=args.max_depth, max_routes=args.max_candidates)
        members = search.routes
    if args.ensemble or not members:
        # empty members -> the ensemble projector shows the lone target and invents no reaction.
        return project_synthesis_ensemble(search)
    return project_synthesis(members[0], search_result=search)


def _render(graph, fmt: str, max_visible_nodes) -> str:
    if fmt == "json":
        return graph.to_json() + "\n"
    if fmt == "dot":
        return render_dot(graph)
    if fmt == "mermaid":
        return render_mermaid(graph)
    if fmt == "svg":
        return render_svg(graph)
    return render_html(graph, max_visible_nodes=max_visible_nodes)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        graph = _project(args)
        rendered = _render(graph, args.format, args.max_visible_nodes)
    except GraphProjectionError as exc:
        print(f"python -m smartchem graph: refused: {exc}", file=sys.stderr)
        return 5

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote {args.output} ({len(graph.nodes)} nodes, {len(graph.arcs)} arcs)",
              file=sys.stderr)

    # The scientific status always reaches stderr, whatever the format or display medium.
    print(f"SmartChem graph source={graph.source_kind} search={graph.search_status} "
          f"source_digest={graph.source_digest} "
          f"receipt={graph.receipt_digest or 'UNATTESTED'} view_digest={graph.digest}",
          file=sys.stderr)
    return 0 if graph.search_status in _COMPLETE else 4


if __name__ == "__main__":
    raise SystemExit(main())
