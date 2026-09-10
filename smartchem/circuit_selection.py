"""Move 5 evidence (EM scope): a circuit-route SELECTOR -- the open-circuit pipeline's first NON-TEST caller.

The pipeline (:mod:`smartchem.open_circuit_pipeline`) supplied the second-domain ``ingest -> generic core ->
cost -> survival`` shape, but by its OWN zero-call-sites standard it awaited a real consumer: *"nothing OUTSIDE
this module + its test/probe plans, ranks, or verifies a circuit through this shape."*  This module is that
consumer.  It PLANS / RANKS / VERIFIES circuit designs the way the chemistry ``drafter`` ranks synthesis routes:
read each candidate's domain COST (:func:`~smartchem.open_circuit_pipeline.equivalent_resistance`), gate on the
Move-5 SURVIVAL predicate (:func:`~smartchem.open_circuit_pipeline.within_spec`), and present the survivors in a
deterministic, legible order -- never a fabricated "optimum" (the R26 Pareto-front discipline: present the
honest datum, do not collapse axes into a fake scalar winner; here there is genuinely ONE cost axis, exact
resistance, so a total order is honest -- and it is a total order on an EXACT ``Fraction``, so "best" is
reproducible, never floating-point-fragile).

**What this does to the Move-5 case, bounded honestly (the last-round over-claim lesson).**  It advances the case
by exactly ONE concrete step: the pipeline's stated residual (*"awaits its first non-test caller"*) is now
discharged -- the pipeline has a PRODUCTION consumer of the same KIND the chemistry side has (a route ranker with
a user-facing entry point, ``python -m smartchem.circuit_selection``).  That is a single step, NOT proximity to
completion: the distance from here to actual Move-5 completion is the ENTIRE deferred domain-neutral refactor,
not one more brick.  Completion requires making the CHEMISTRY ``ExperimentStep`` / ``ExperimentRoute`` literally
parametric over a "conserved-inventory transition + survival predicate" AND retrofitting BOTH domains onto ONE
shared ranker -- its own large round.  The chemistry ranker (``smartchem.experiment.drafter.rank_routes``) is
hard-typed to ``ExperimentRoute`` (its ``fit_routes`` path raises ``TypeError`` on anything else); nothing forces
the two domains through a single primitive yet, and this brick deliberately does not fabricate one.  So: the
genericity is exercised end to end by a real consumer with a real caller in the CIRCUIT vertical alone -- no
chemistry code and no shared primitive flows through any of it, and the cross-domain UNIFICATION that would
COMPLETE Move 5 is untouched.

Fail-closed throughout: a candidate whose cost is ``None`` (an open / short / non-two-terminal apex) NEVER
survives -- it is DISCLOSED in :attr:`CircuitSelection.rejected`, never silently dropped.  The spec band is
validated up front, BEFORE the candidate loop and regardless of candidate count, so a malformed band is refused
even on an empty candidate set (the ``vacuous-green-over-an-empty-subject`` lesson: a check that only fires when
the subject is non-empty passes a bad spec vacuously).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .open_circuit_pipeline import (
    CircuitRoute,
    CircuitStage,
    _spec_bound,  # single source of truth for exact-bound / +-inf validation (never duplicate the rules -> drift)
)

__all__ = [
    "CircuitCandidate",
    "RankedCandidate",
    "CircuitSelection",
    "select_within_spec",
    "main",
]


@dataclass(frozen=True)
class CircuitCandidate:
    """A named candidate circuit design: a human label + the :class:`CircuitRoute` that realises it."""

    name: str
    route: CircuitRoute

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise ValueError("CircuitCandidate.name must be a non-empty string")
        if type(self.route) is not CircuitRoute:
            raise TypeError("CircuitCandidate.route must be a CircuitRoute")

    @property
    def equivalent_resistance(self) -> Fraction | None:
        """The candidate's two-terminal equivalent resistance (``None``, fail-closed, for a non-resistor apex)."""
        return self.route.equivalent_resistance


@dataclass(frozen=True)
class RankedCandidate:
    """A survivor: its label, route, and the finite in-band cost it was ranked on (never ``None`` here)."""

    name: str
    route: CircuitRoute
    equivalent_resistance: Fraction


@dataclass(frozen=True)
class CircuitSelection:
    """The result of ranking candidates against a resistance spec band ``[low, high]``.

    :attr:`within_spec` are the survivors, ordered ascending by EXACT resistance then by name (a deterministic,
    legible presentation order -- NOT a claim that the lowest-resistance design is uniquely "optimal"; within the
    band every survivor meets spec).  :attr:`rejected` discloses every non-survivor as ``(name, cost-or-None)`` --
    an out-of-band finite cost, or ``None`` for an open / short / non-two-terminal apex -- so nothing is dropped
    silently.  The band is echoed for legibility.
    """

    within_spec: tuple[RankedCandidate, ...]
    rejected: tuple[tuple[str, Fraction | None], ...]
    low_ohms: object
    high_ohms: object

    @property
    def best(self) -> RankedCandidate | None:
        """The lowest-resistance in-band survivor (the head of the deterministic order), or ``None`` if none survived."""
        return self.within_spec[0] if self.within_spec else None


def select_within_spec(
    candidates: Iterable[CircuitCandidate], low_ohms, high_ohms
) -> CircuitSelection:
    """Rank circuit-route candidates against a resistance spec band -- the pipeline's first non-test caller.

    Keep the candidates whose equivalent resistance is finite AND inside ``[low_ohms, high_ohms]`` (the
    :func:`within_spec` survival predicate), order the survivors ascending by exact resistance then name, and
    disclose every reject with its cost (or ``None``).  Bounds are EXACT (``int`` / ``Fraction`` / ``Rational``,
    or ``+-math.inf`` for a one-sided band); ``low <= high`` is required.  The band is validated FIRST, so a
    malformed spec is refused even when ``candidates`` is empty.
    """
    lo = _spec_bound(low_ohms, "low_ohms")
    hi = _spec_bound(high_ohms, "high_ohms")
    if lo > hi:  # Fraction vs +-inf comparisons are well-defined, so a one-sided band still orders correctly
        raise ValueError("select_within_spec requires low_ohms <= high_ohms")

    survivors: list[RankedCandidate] = []
    rejected: list[tuple[str, Fraction | None]] = []
    for candidate in candidates:
        if type(candidate) is not CircuitCandidate:
            raise TypeError("every candidate must be a CircuitCandidate")
        cost = candidate.equivalent_resistance  # ONE assemble+solve, read through the candidate's own cost property
        # The within_spec survival predicate, applied to that single-solved cost (lo/hi are already
        # _spec_bound-normalised -- the single source of truth): a None cost (open / short / non-two-terminal
        # apex) NEVER survives; otherwise it must lie in the exact band.  `cost is not None` keeps a survivor's
        # ranked resistance provably finite -- a RankedCandidate never carries a None cost.  Reading `cost` ONCE
        # and gating on it (rather than a second within_spec re-solve) removes the redundant apex solve while the
        # answer is identical (equivalent_resistance is a pure, deterministic read).
        if cost is not None and lo <= cost <= hi:
            survivors.append(RankedCandidate(candidate.name, candidate.route, cost))
        else:
            rejected.append((candidate.name, cost))
    survivors.sort(key=lambda ranked: (ranked.equivalent_resistance, ranked.name))
    return CircuitSelection(tuple(survivors), tuple(rejected), lo, hi)


# --------------------------------------------------------------------------------------------------------------
# A minimal, fail-closed user-facing driver: `python -m smartchem.circuit_selection`.  This is the SELECTOR's
# earned call site (so the selector is not itself a zero-call-sites structure), and it keeps the circuit domain
# OFF the chemistry front door (`smartchem.cli`) -- circuits are the SECOND domain, their own EM-scope vertical.
# --------------------------------------------------------------------------------------------------------------

def _parse_resistor_spec(spec: str) -> CircuitRoute:
    """Parse a tiny fail-closed grammar into a :class:`CircuitRoute`.

    A spec is a comma-separated SERIES of stages; a stage is either a single integer resistance (ohms) or a
    ``|``-separated PARALLEL block of integer resistances, folded left through
    :meth:`CircuitStage.in_parallel`.  Example: ``"2,3,4|4"`` is ``2 -> 3 -> (4 || 4)`` = ``7 ohms``.  Anything
    that is not a non-negative integer token is refused (no floats -- resistances are exact).
    """
    def resistor(token: str) -> CircuitStage:
        token = token.strip()
        # ASCII non-negative integers only.  `isascii()` is required BEFORE `isdigit()`: bare `isdigit()` also
        # admits non-ASCII decimals (e.g. Arabic-Indic '٣') and superscripts ('²'), which the plain-integer
        # contract does not intend -- so an over-generous token never slips through even though `int()` would
        # have parsed the decimal ones to the right value.
        if not token or not token.isascii() or not token.isdigit():
            raise ValueError(f"resistance token {token!r} is not an ASCII non-negative integer")
        return CircuitStage.resistor(int(token))

    stages: list[CircuitStage] = []
    for raw_stage in spec.split(","):
        parts = raw_stage.split("|")
        stage = resistor(parts[0])
        for part in parts[1:]:
            stage = CircuitStage.in_parallel(stage, resistor(part))
        stages.append(stage)
    if not stages:
        raise ValueError("a circuit spec needs at least one stage")
    return CircuitRoute.of(*stages)


def _parse_bound(token: str):
    """Parse a spec-band bound: an ASCII non-negative integer, or ``inf`` for an unbounded ceiling.

    ``-inf`` is intentionally NOT offered here: for a NON-NEGATIVE resistance a ``-inf`` floor is equivalent to
    ``0``, and argparse's tokenizer would reject a leading-dash ``-inf`` value before this parser ever saw it, so
    advertising it would be a dead promise.  (``select_within_spec`` itself still accepts ``-inf`` for a
    domain-general one-sided band -- this is only the resistance CLI's bound grammar.)
    """
    token = token.strip().lower()
    if token in ("inf", "+inf"):
        return float("inf")
    if not token.isascii() or not token.isdigit():
        raise ValueError(f"bound {token!r} must be an ASCII non-negative integer or inf")
    return int(token)


def main(argv: list[str] | None = None) -> int:
    """Rank ``--candidate NAME=SPEC`` designs against a ``--band LOW HIGH`` resistance spec.

    Exit codes mirror the chemistry front door: ``0`` a survivor was selected, ``3`` no candidate met spec,
    ``2`` invalid input.  Fail-closed: a malformed spec or band is a ``2``, never a fabricated selection.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m smartchem.circuit_selection",
        description="Select an in-spec resistor-network design (EM-scope Move-5 pipeline consumer).",
    )
    parser.add_argument(
        "--band", nargs=2, metavar=("LOW", "HIGH"), required=True,
        help="the resistance spec band in ohms (non-negative integers; HIGH may be 'inf' for no upper limit)",
    )
    parser.add_argument(
        "--candidate", action="append", default=[], metavar="NAME=SPEC",
        help="a named design; SPEC is a comma-series of ohm stages, '|' for a parallel block (e.g. dividerA=2,3,4|4)",
    )
    args = parser.parse_args(argv)

    try:
        low, high = _parse_bound(args.band[0]), _parse_bound(args.band[1])
        candidates: list[CircuitCandidate] = []
        for entry in args.candidate:
            name, sep, spec = entry.partition("=")
            if not sep or not name:
                raise ValueError(f"candidate {entry!r} must be NAME=SPEC")
            candidates.append(CircuitCandidate(name, _parse_resistor_spec(spec)))
        selection = select_within_spec(candidates, low, high)
    except (ValueError, TypeError) as exc:
        print(f"circuit_selection: {exc}", file=sys.stderr)
        return 2

    print(f"spec band: [{args.band[0]}, {args.band[1]}] ohms")
    for ranked in selection.within_spec:
        print(f"  IN-SPEC  {ranked.name}: {ranked.equivalent_resistance} ohms")
    for name, cost in selection.rejected:
        shown = f"{cost} ohms" if cost is not None else "not a two-terminal resistor (open/short)"
        print(f"  reject   {name}: {shown}")
    best = selection.best
    if best is None:
        print("no candidate met spec")
        return 3
    print(f"best: {best.name} ({best.equivalent_resistance} ohms)")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via main(argv) in tests
    raise SystemExit(main())
