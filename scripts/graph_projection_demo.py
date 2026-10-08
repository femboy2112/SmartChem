"""Generate reproducible graph projections from REAL SmartChem objects.

Usage from repo root / editable install:
  python -m scripts.graph_projection_demo formula H2O --format dot
  python -m scripts.graph_projection_demo formula C3H6O --max-edges 3 --format mermaid
  python -m scripts.graph_projection_demo convergent-fixture --format dot

The convergent fixture is a balance-certified graph test, NOT a vetted procedure.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from smartchem.category import Molecule
from smartchem.decompiler import search_decomposition
from smartchem.experiment.dag import SynthesisDAG
from smartchem.experiment.step import ExperimentStep
from smartchem.graph_projection import (
    project_decomposition, project_synthesis, render_dot, render_mermaid,
)


def _convergent_fixture() -> SynthesisDAG:
    """Two stoichiometrically certified branches joined into one target."""
    h, cl = Molecule.atom("H"), Molecule.atom("Cl")
    h2 = Molecule.diatomic("H", "H")
    cl2 = Molecule.diatomic("Cl", "Cl")
    hcl = Molecule.diatomic("H", "Cl")
    a = ExperimentStep.assembling(h2, (h, h), (h2,))
    b = ExperimentStep.assembling(cl2, (cl, cl), (cl2,))
    c = ExperimentStep.assembling(hcl, (h2, cl2), (hcl, hcl))
    return SynthesisDAG.of(a, b, c)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view", choices=("formula", "convergent-fixture"))
    parser.add_argument("target", nargs="?", help="formula target (required for formula)")
    parser.add_argument("--inventory", nargs="*", default=(),
                        help="exact formula terminal inventory, no stock by default")
    parser.add_argument("--max-edges", type=int, default=500,
                        help="formula decomposition result budget")
    parser.add_argument("--budget", type=int, default=100_000,
                        help="formula decomposition search work budget")
    parser.add_argument("--format", choices=("json", "dot", "mermaid"), default="dot")
    parser.add_argument("--output", type=Path,
                        help="file path (defaults to stdout)")
    args = parser.parse_args(argv)

    if args.view == "formula":
        if not args.target:
            parser.error("formula view requires a target formula")
        result = search_decomposition(
            args.target, inventory=tuple(args.inventory),
            budget=args.budget, max_edges=args.max_edges,
        )
        graph = project_decomposition(result)
    else:
        if args.target is not None:
            parser.error("convergent-fixture has no target argument")
        graph = project_synthesis(_convergent_fixture())

    generated = (
        graph.to_json() + "\n" if args.format == "json" else
        render_dot(graph) if args.format == "dot" else
        render_mermaid(graph)
    )
    if args.output is None:
        sys.stdout.write(generated)
    else:
        args.output.write_text(generated, encoding="utf-8")
        print(f"Wrote {args.output} ({len(graph.nodes)} nodes, {len(graph.arcs)} arcs)",
              file=sys.stderr)

    # Whether or not DOT/Mermaid is successfully displayed, the user sees this
    # critical disclaimer as metadata or as a stderr status message.
    print(f"SmartChem source={graph.source_kind} status={graph.search_status} "
          f"source_digest={graph.source_digest} receipt={graph.receipt_digest or 'UNATTESTED'}",
          file=sys.stderr)
    return 0 if graph.search_status in ("COMPLETE", "COMPLETE_WITHIN_BOUNDS", "UNATTESTED") else 4


if __name__ == "__main__":
    raise SystemExit(main())
