"""CHEM-ALG-01 #114 -- the opt-in ``bond-order-edit-v1`` profile AND its reaction-type recognizer.

Claim under test (DISCLOSED within this grammar): wiring the bond-order-edit (de/hydrogenation) family behind a named
opt-in profile makes the synthesis-direction hydrogenation route ``unsaturated + H2 -> saturated`` REACHABLE, while
neither production default profile reaches it; AND the #114 reaction-type recognizer now RECOGNISES those genuine
single bond-order edits as ``hydrogenation`` (promoting them from FORMAL_CANDIDATE to REACTION_VOUCHED), re-derived
from the molecules via the family's own generator -- so every bench step is recognised as hydrogenation and NONE is
mis-attributed to another family. (The no-FICTION-vouch and conjugated-ring-deferral guarantees are proved in
tests/test_hydrogenation_recognizer_114.py.)

Run: ``.venv/bin/python -m experiments.bond_order_edit_profile_114``  (exit 0 iff the measured invariants hold).
``validate()`` is imported by tests/test_bond_order_edit_profile_114.py so the measured gain is a permanent control.
"""
from __future__ import annotations

from dataclasses import dataclass

from smartchem.algebra_profiles import resolve_algebra_profile
from smartchem.experiment.reaction_type_oracle import recognize_reaction_type_outcome
from smartchem.experiment.routes import search_routes
from smartchem.smiles import parse_smiles

PROFILE = "bond-order-edit-v1"
_DEFAULTS = ("legacy-capped-v1", "certified-route-v07")  # the low-level default and the promoted route default
H2 = parse_smiles("[H][H]")

# (label, saturated target, unsaturated precursor on hand) -- each a textbook hydrogenation.
_CASES = [
    ("ethane",      "CC",        "C=C"),
    ("propane",     "CCC",       "CC=C"),
    ("butane",      "CCCC",      "CC=CC"),
    ("cyclohexane", "C1CCCCC1",  "C1=CCCCC1"),
]


@dataclass(frozen=True)
class _Measured:
    label: str
    under_profile: int       # hydrogenation routes reachable under bond-order-edit-v1
    under_defaults: int      # hydrogenation routes reachable under ANY default profile (must be 0)
    steps_seen: int          # bond-order steps the oracle was asked to classify
    recognized: int          # steps the #114 recognizer MATCHED as hydrogenation (now the expected outcome)
    misattributed: int       # steps MATCHED as something OTHER than hydrogenation (a cross-poach; must be 0)


def _routes_to_saturated(target, precursor, registry):
    return search_routes(target, reagents=(), available=(precursor, H2), max_depth=1, registry=registry)


def _measure_case(label: str, target_smiles: str, precursor_smiles: str) -> _Measured:
    target, precursor = parse_smiles(target_smiles), parse_smiles(precursor_smiles)
    prof = _routes_to_saturated(target, precursor, resolve_algebra_profile(PROFILE))
    under_defaults = sum(
        len(_routes_to_saturated(target, precursor, resolve_algebra_profile(pid)).routes) for pid in _DEFAULTS
    )
    steps_seen = recognized = misattributed = 0
    for r in prof.routes:
        for step in r.steps:
            steps_seen += 1
            out = recognize_reaction_type_outcome(step)
            if out.is_match:
                if "hydrogenation" in (out.reaction_class or ""):
                    recognized += 1
                else:
                    misattributed += 1
    return _Measured(label, len(prof.routes), under_defaults, steps_seen, recognized, misattributed)


def run() -> list[_Measured]:
    return [_measure_case(*c) for c in _CASES]


def validate() -> tuple[bool, dict]:
    rows = run()
    reachable = sum(1 for m in rows if m.under_profile >= 1)
    default_hits = sum(m.under_defaults for m in rows)
    recognized = sum(m.recognized for m in rows)
    misattributed = sum(m.misattributed for m in rows)
    steps = sum(m.steps_seen for m in rows)
    summary = {
        "cases": len(rows),
        "reachable_under_profile": reachable,
        "reachable_under_defaults": default_hits,
        "steps_classified": steps,
        "recognized_as_hydrogenation": recognized,
        "misattributed": misattributed,
    }
    ok = (
        reachable == len(rows)         # the hydrogenation route is reachable in EVERY case under the opt-in profile
        and default_hits == 0          # and in NO case under either default profile
        and steps >= len(rows)         # at least one bond-order step was actually classified (non-vacuous)
        and recognized == steps        # and the #114 recognizer vouches EVERY genuine hydrogenation step
        and misattributed == 0         # and never mis-attributes one to another family (cross-poach)
    )
    return ok, summary


def main() -> int:
    rows = run()
    print(f"{'case':<13} {'under_profile':>13} {'under_defaults':>15} {'steps':>6} {'recognized':>11} {'misattr':>8}")
    for m in rows:
        print(f"{m.label:<13} {m.under_profile:>13} {m.under_defaults:>15} {m.steps_seen:>6} "
              f"{m.recognized:>11} {m.misattributed:>8}")
    ok, summary = validate()
    print(f"\nsummary: {summary}")
    print("VALIDATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
