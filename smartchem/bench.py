"""
Benchmark harness. Reports measured accuracy against experimental reference data.

Run:  python -m smartchem.bench [--split test] [--oracle NAME ...]

Design rules, so a number from this module can be trusted:

* Coverage is printed before any MAE. A good conditional score over three species is not a
  good overall score, and incomplete coverage receives no accuracy-tier verdict.
* Refusals remain excluded from the arithmetic mean because no defensible numerical error
  exists for a missing prediction. They are included in the decision: an incomplete model
  cannot earn “chemical accuracy” by declining hard cases.
* The historical train/test partition is declared in ``smartchem.data.reference``. The
  current ``test`` partition was inspected during 2026 model selection and is therefore not
  a pristine holdout; future fitted models need a newly locked external validation set.
* Wall-clock is measured per species so the accuracy/cost curve is visible. That curve is
  the deliverable: it says where to sit on the speed/accuracy dial, rather than assuming.
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from .category import Molecule
from .data import (
    CHEMICAL_ACCURACY_EV,
    GOOD_SEMIEMPIRICAL_EV,
    KCAL_PER_EV,
    bonds,
    coverage_report,
)


@dataclass
class Row:
    formula: str
    reference_ev: float
    predicted_ev: float | None   # None == the oracle refused to predict
    seconds: float
    kind: str
    reference_scale_ev: float | None = None  # curation/source scale, coverage unspecified

    @property
    def error_ev(self) -> float | None:
        if self.predicted_ev is None:
            return None
        return self.predicted_ev - self.reference_ev


@dataclass
class Result:
    oracle: str
    rows: list[Row]

    @property
    def scored(self) -> list[Row]:
        return [r for r in self.rows if r.predicted_ev is not None]

    @property
    def refused(self) -> list[Row]:
        return [r for r in self.rows if r.predicted_ev is None]

    @property
    def mae_ev(self) -> float | None:
        s = self.scored
        if not s:
            return None
        return sum(abs(r.error_ev) for r in s) / len(s)

    @property
    def max_abs_error_ev(self) -> float | None:
        s = self.scored
        return max(abs(r.error_ev) for r in s) if s else None

    @property
    def total_seconds(self) -> float:
        return sum(r.seconds for r in self.rows)


def evaluate(oracle, split: str | None = None, verbose: bool = True) -> Result:
    """
    Score one oracle against the reference bond set.

    ``oracle`` must expose ``name`` and ``atomization_energy(Molecule) -> Estimate | None``.
    The returned value is a positive dissociation energy in eV, or None to decline. The
    reference row's conventional bond order is included in the molecular graph, so species
    identity is not silently collapsed to an unordered atom pair.
    """
    rows: list[Row] = []
    for ref in bonds(split):
        molecule = Molecule.diatomic(*ref.atoms, order=ref.bond_order)
        t0 = time.perf_counter()
        try:
            estimate = oracle.atomization_energy(molecule)
            predicted = None if estimate is None else estimate.value_ev
        except (KeyError, NotImplementedError):
            predicted = None   # element or regime the oracle does not cover
        dt = time.perf_counter() - t0
        rows.append(Row(
            ref.formula,
            ref.d0_ev,
            predicted,
            dt,
            ref.kind,
            reference_scale_ev=ref.uncertainty_ev,
        ))
        if verbose:
            if predicted is None:
                print(f"  {ref.formula:6} {'REFUSED':>10} {ref.d0_ev:>9.3f} "
                      f"{'--':>9} {'--':>10} {dt:7.2f}s")
            else:
                err = predicted - ref.d0_ev
                print(f"  {ref.formula:6} {predicted:>10.3f} {ref.d0_ev:>9.3f} "
                      f"{err:>+9.3f} {err * KCAL_PER_EV:>+10.2f} {dt:7.2f}s")
    return Result(oracle.name, rows)


def verdict(mae_ev: float | None, *, refused: int = 0) -> str:
    """State an accuracy tier only when coverage is complete."""
    if refused:
        return "INCOMPLETE COVERAGE (conditional MAE only; no accuracy tier)"
    if mae_ev is None:
        return "NO PREDICTIONS"
    if mae_ev < CHEMICAL_ACCURACY_EV:
        return "CHEMICAL ACCURACY (< 1 kcal/mol)"
    if mae_ev < GOOD_SEMIEMPIRICAL_EV:
        return "good semi-empirical"
    if mae_ev < 1.0:
        return "usable for screening"
    return "NOT USABLE for quantitative work"


def report(results: list[Result], available_elements: frozenset[str], split: str | None) -> None:
    cov = coverage_report(available_elements)
    print()
    print("=" * 78)
    print("COVERAGE  (read this before any accuracy number below)")
    print("=" * 78)
    print(f"  elements required by reference set : {cov['elements_required']}")
    print(f"  elements available                 : {cov['elements_available']}")
    if cov["elements_missing"]:
        print(f"  elements MISSING                   : {', '.join(cov['elements_missing'])}")
    print(f"  reference bonds                    : {cov['bonds_attemptable']}"
          f" attemptable of {cov['bonds_total']}")
    if cov["bonds_skipped"]:
        print(f"  skipped for missing elements       : {', '.join(cov['bonds_skipped'])}")
    print(f"  split evaluated                    : {split or 'all'}")
    print("  reference uncertainty fields       : retained as curation/source scales; "
          "not folded into MAE")

    print()
    print("=" * 78)
    print(f"{'oracle':22} {'cond MAE':>9} {'kcal/mol':>10} {'max err':>9} "
          f"{'n':>4} {'refused':>8} {'sec':>8}")
    print("-" * 78)
    def order(result: Result) -> tuple:
        return (
            bool(result.refused),
            len(result.refused) / len(result.rows) if result.rows else 1.0,
            result.mae_ev is None,
            result.mae_ev or 0.0,
        )
    for r in sorted(results, key=order):
        mae = r.mae_ev
        if mae is None:
            print(f"{r.oracle:22} {'--':>9} {'--':>10} {'--':>9} "
                  f"{0:>4} {len(r.refused):>8} {r.total_seconds:>8.2f}")
            continue
        print(f"{r.oracle:22} {mae:>9.4f} {mae * KCAL_PER_EV:>10.2f} "
              f"{r.max_abs_error_ev:>9.3f} {len(r.scored):>4} {len(r.refused):>8} "
              f"{r.total_seconds:>8.2f}")

    print()
    print("VERDICT")
    for r in sorted(results, key=order):
        line = f"  {r.oracle:22} {verdict(r.mae_ev, refused=len(r.refused))}"
        if r.refused:
            line += (f"   [declined {len(r.refused)}/{len(r.rows)}; conditional MAE "
                     "excludes them]")
        print(line)
    print()
    print(f"  chemical accuracy threshold = {CHEMICAL_ACCURACY_EV} eV "
          f"(1.00 kcal/mol)")


def _load_oracles(names: list[str] | None):
    from .oracle import available_oracles
    registry = available_oracles()
    if names:
        missing = [n for n in names if n not in registry]
        if missing:
            raise SystemExit(
                f"unknown oracle(s): {', '.join(missing)}. "
                f"available: {', '.join(sorted(registry))}"
            )
        return [registry[n] for n in names]
    return list(registry.values())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Measure oracle accuracy against experiment.")
    p.add_argument("--split", choices=["train", "test"], default=None,
                   help="restrict to one split (default: all)")
    p.add_argument("--oracle", action="append", dest="oracles", default=None,
                   help="oracle name; repeatable (default: every available oracle)")
    p.add_argument("--quiet", action="store_true", help="summary only, no per-species rows")
    args = p.parse_args(argv)

    from .atoms import PT

    oracles = _load_oracles(args.oracles)
    results = []
    for oracle in oracles:
        if not args.quiet:
            print()
            print(f"--- {oracle.name} ---")
            print(f"  {'species':6} {'predicted':>10} {'reference':>9} "
                  f"{'err eV':>9} {'err kcal':>10} {'time':>8}")
        results.append(evaluate(oracle, args.split, verbose=not args.quiet))

    report(results, frozenset(PT.keys()), args.split)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
