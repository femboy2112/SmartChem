"""Example 02 -- formula descent: decompile ethanol (C2H6O) over a small declared inventory.

Shows: build_decomposition returns a DecompositionGraph with a completeness status and a digest; every edge
is an atom-conserving split of a formula into inventory terminals.  This is a FORMAL descent, not a procedure.
"""
from smartchem.decompiler import build_decomposition, example_inventory


def main() -> int:
    graph = build_decomposition("C2H6O", example_inventory(), max_edges=50)
    print(f"status={graph.status} complete={graph.is_complete} edges={len(graph.edges)} nodes={len(graph.nodes())}")
    print(f"digest={graph.digest[:16]}...")
    for edge in graph.edges:
        print("  ", edge)
    return 0 if graph.is_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
