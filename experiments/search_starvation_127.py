"""CHEM-ALG-01 #127 -- empirical probe of raw-result-cap STARVATION of credible chemistry.

Claim under test (issue #127): "the generator can exhaust its raw result budget on formally
conserving but chemically implausible routes before more credible chemistry reaches
classification." The feared harm: a RECOGNIZED (all-steps-vouched) route pushed past
``max_routes`` by earlier UNRECOGNIZED fictions, since classification happens AFTER the cap
and provider order is transform-digest order, not chemical merit.

FINDING (Observed, this round, 2026-10-28): the harm does NOT reproduce under the production
default profile for realistic condensation targets. Wherever a recognized route exists it is
emitted at rank 0 -- ahead of every fiction -- so it survives even ``max_routes=1``. The
structural reason: capped scission drops any cut with >=2 missing precursors and recurses only
on a single missing precursor, so the COMPLETE-route set stays small (<= ~10 for these targets),
far below any realistic cap; the cap never bites. The mechanism (post-cap classification,
digest ordering) is real; the magnitude is nil in this regime. See BOUNDARY below.

This module is the permanent control: ``validate()`` asserts that for each target the credible
route is RECALLED FIRST (survives max_routes=1). If a future generator/ordering change ever
floods a fiction ahead of the credible route, cap=1 recall drops and this FAILS -- the exact
starvation regression #127 fears, caught before it ships.

Run: ``.venv/bin/python -m experiments.search_starvation_127`` (exit 0 iff the invariant holds).

BOUNDARY (what this does NOT establish): it does not prove starvation is impossible in ALL
regimes. A pathological target with >cap completable conserved cuts whose credible route hashes
late is untested (none could be constructed from realistic chemistry under the default profile
across 14 probed targets at depths 1-3). The receipt's generation counters (candidates_emitted)
are cap-dependent and not comparable across caps; recognition is measured externally here
because search_routes deliberately never consults the oracle.
"""
from __future__ import annotations

from dataclasses import dataclass

from smartchem.algebra_profiles import resolve_algebra_profile
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type_outcome
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles

PROFILE = "certified-route-v07"  # the production route default the service uses
DEPTH = 2
GENEROUS_CAP = 500

# A common-kitchen pool holding the REAL precursors so a recognized route genuinely exists to
# be (potentially) starved, plus decoy fragments that seed conserved fictions.
POOL = [
    "O", "CO", "CCO", "CC(=O)O", "CCC(=O)O", "C", "CC", "C=C", "C=O", "CC=O",
    "N", "CN", "CC(C)O", "CCC", "CCCO", "CCOC(C)=O",
]

# (label, target SMILES, extra reagents) -- each a textbook single-condensation product whose
# recognized route's precursors are in POOL.
_CASES = [
    ("ethyl_acetate",     "CCOC(C)=O",   ["O"]),
    ("methyl_acetate",    "COC(C)=O",    ["O"]),
    ("acetamide",         "CC(N)=O",     ["O"]),
    ("N-methylacetamide", "CC(=O)NC",    ["O"]),
    ("diethyl_ether",     "CCOCC",       ["O"]),
    ("ethyl_propanoate",  "CCOC(=O)CC",  ["O"]),
]


@dataclass(frozen=True)
class _Measured:
    label: str
    total: int               # routes returned at the generous cap
    recognized: int          # of those, how many are all-steps-vouched (credible)
    first_rec_rank: "int | None"   # digest/DFS rank of the first recognized route (None if none)
    candidates_emitted: "int | None"  # receipt: routes the generator emitted before dedup/cap
    status: str              # receipt standard status
    recognized_at_cap1: int  # recognized routes still returned at the brutal max_routes=1


def _route_recognized(route) -> bool:
    return all(recognize_reaction_type_outcome(s).is_match for s in route.steps)


def _search(target, reagents, avail, cap):
    return search_routes(target, reagents=reagents, available=avail,
                         max_depth=DEPTH, max_routes=cap,
                         registry=resolve_algebra_profile(PROFILE))


def _measure(label: str, target_smiles: str, extra: list[str]) -> _Measured:
    target = parse_smiles(target_smiles)
    avail = tuple(parse_smiles(s) for s in POOL if s != target_smiles)
    reagents = tuple(parse_smiles(s) for s in extra)

    res = _search(target, reagents, avail, GENEROUS_CAP)
    flags = [_route_recognized(r) for r in res.routes]
    ranks = [i for i, f in enumerate(flags) if f]

    res1 = _search(target, reagents, avail, 1)
    rec_at_1 = sum(_route_recognized(r) for r in res1.routes)

    return _Measured(
        label=label, total=len(res.routes), recognized=sum(flags),
        first_rec_rank=(ranks[0] if ranks else None),
        candidates_emitted=res.receipt.candidates_emitted,
        status=res.receipt.standard_status, recognized_at_cap1=rec_at_1,
    )


def run() -> list[_Measured]:
    return [_measure(*c) for c in _CASES]


def validate() -> tuple[bool, dict]:
    rows = run()
    have_recognized = sum(1 for m in rows if m.recognized >= 1)
    first_rank_zero = sum(1 for m in rows if m.first_rec_rank == 0)
    survive_cap1 = sum(1 for m in rows if m.recognized_at_cap1 >= 1)
    summary = {
        "cases": len(rows),
        "with_recognized_route": have_recognized,
        "recognized_at_rank_0": first_rank_zero,
        "credible_route_survives_cap1": survive_cap1,
    }
    ok = (
        have_recognized == len(rows)      # every case genuinely has a credible route to starve
        and first_rank_zero == len(rows)  # and it is emitted FIRST (ahead of every fiction)
        and survive_cap1 == len(rows)     # so it is recalled even under the most brutal cap=1
    )
    return ok, summary


def main() -> int:
    rows = run()
    print(f"{'target':<20}{'total':>6}{'recog':>6}{'rank0':>6}{'emitted':>8}{'cap1_rec':>9}  status")
    for m in rows:
        print(f"{m.label:<20}{m.total:>6}{m.recognized:>6}{str(m.first_rec_rank):>6}"
              f"{str(m.candidates_emitted):>8}{m.recognized_at_cap1:>9}  {m.status}")
    ok, summary = validate()
    print(f"\nsummary: {summary}")
    print("VALIDATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
