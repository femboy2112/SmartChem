"""
How long a legal shepherding round can run, as a function of one declared rank.

    python experiments/ledger_rank_blowup.py --max-rank 12

WHAT THIS EXISTS TO PIN DOWN
-----------------------------
``Spec.round_bound`` was written to answer "does this loop stop", and it does. It was then
read -- by me, in the same session that wrote it -- as if it also answered "does this loop
stop *soon*". It does not, and the gap is exponential.

An adversarial pass over ``smartchem/ledger.py`` raised this: a responder that repeatedly
splits the highest-rank hole into two holes one rank down is entirely legal, honours
``fan_out=2`` throughout, never comes close to the budget, and still runs for a length that
is exponential in a single integer taken from the public API. Nothing is broken. Descending
sequences below ``omega**omega`` can be arbitrarily long, and admitting deepening at all is
what buys that. But a termination theorem and a practical guard are different objects, and
this file is the measurement that keeps them from being confused again.

THE RESPONDER
--------------
``split_deepest`` binds the deepest open hole and, unless it was rank 0, replaces it with
exactly two holes one rank lower. That walks a complete binary tree of depth ``K``, so the
round count is ``2**(K+1) - 1`` -- every node gets bound exactly once. This is a DIFFERENT
responder from the one that first surfaced the blowup (that one reported ``2**K``); the
shape of the tree depends on how the rank-0 case is handled, and the point survives either
way. The number below is this file's responder, measured by this file.

WHAT IS AND IS NOT A MEASUREMENT HERE
--------------------------------------
The ROUND COUNTS are exact, deterministic, and load-independent -- they are a property of
the responder and the order, not of the machine. The WALL TIMES are not: they are sensitive
to whatever else holds the box, and they are printed to show the *shape* (superlinear in the
round count, because ``bind`` and ``widen`` each rebuild the whole slot tuple, making the
cost quadratic in the slots alive) rather than to be quoted as a benchmark.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smartchem.ledger import COMPILED, Slot, Spec, shepherd    # noqa: E402


def split_deepest(spec: Spec, holes: tuple[Slot, ...]) -> Spec:
    """Bind the deepest hole; if it was not atomic, open two holes one rank below it."""
    target = max(holes, key=lambda hole: hole.rank)
    spec = spec.bind(target.name, "unfolded")
    if target.rank == 0:
        return spec
    stamp = len(spec.slots)
    return spec.widen(*[Slot(f"{target.name}.{stamp}.{i}", "<sub>", rank=target.rank - 1)
                        for i in range(2)])


def one_rank(rank: int, fan_out: int = 2) -> dict:
    spec = Spec("root", (Slot("q", "constrain it, somehow", rank=rank),))
    bound = spec.round_bound(fan_out)
    started = time.perf_counter()
    session = shepherd(spec, split_deepest, fan_out=fan_out)
    return {
        "rank": rank,
        "rounds": len(session.rounds),
        "predicted": 2 ** (rank + 1) - 1,
        "bound": bound,
        "wall": time.perf_counter() - started,
        "outcome": session.outcome,
        # Every round of this responder is a legal descent, so the budget is never the
        # thing that stops it. Asserted per-run rather than reasoned about once.
        "all_descended": all(r.descended for r in session.rounds),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rank", type=int, default=12)
    parser.add_argument("--fan-out", type=int, default=2)
    args = parser.parse_args(argv)

    print("=" * 78)
    print("LEDGER RANK BLOWUP -- rounds a legal responder can run from one declared rank")
    print("=" * 78)
    print(f"  fan_out          : {args.fan_out}")
    print(f"  responder        : split the deepest hole into {args.fan_out}, one rank down")
    print()
    print(f"  {'rank':>4}  {'rounds':>8}  {'2**(K+1)-1':>11}  {'round_bound':>12}  "
          f"{'wall':>9}  outcome")

    failures = 0
    for rank in range(1, args.max_rank + 1):
        row = one_rank(rank, args.fan_out)
        ok = (row["rounds"] == row["predicted"]
              and row["outcome"] == COMPILED
              and row["all_descended"]
              and row["rounds"] < row["bound"])
        failures += 0 if ok else 1
        print(f"  {row['rank']:>4}  {row['rounds']:>8}  {row['predicted']:>11}  "
              f"{row['bound']:>12}  {row['wall']:>8.3f}s  {row['outcome']}"
              + ("" if ok else "   <-- UNEXPECTED"))
        sys.stdout.flush()

    print()
    print("  Round counts are exact and load-independent. Wall times are not: they show")
    print("  the shape (superlinear in rounds, because every bind/widen rebuilds the slot")
    print("  tuple) and must not be quoted as a benchmark.")
    print()
    print("  The budget is never what stops this responder -- it runs 2**(K+1)-1 rounds")
    print("  against 3**K and finishes early every time. round_bound says the loop halts.")
    print("  It does not say when, and at rank 12 'when' is already tens of seconds.")
    if failures:
        print(f"\n  {failures} row(s) did not match the predicted shape.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
