"""OPERATION XXV, Phase I-A: machine-readable synthesis-coverage gap map.

The production inventory (recognizer classes, registry digest, algebra profiles) is introspected from the
installed code at run time; it is never typed by hand. The gap table is a dated record of an audit, classified
into exactly one of seven categories:

  1 UNREPRESENTABLE            the IR cannot express the chemistry (missing element, charge, configuration)
  2 REPRESENTABLE_NOT_GENERATED the IR can express it, but no provider/event generates it
  3 GENERATED_NOT_RECOGNIZED   some generator emits it, but no oracle class vouches for it
  4 RECOGNIZED_NOT_FEASIBLE    vouched as a class, but a feasibility/condition gate demotes it
  5 SUPPORTED_NOT_SOURCED      supported, but conditions/procedures are not source-qualified
  6 BUDGET_TRUNCATED           reachable in principle, cut off by a search budget
  7 INTERNAL_ERROR             a typed internal failure

Usage:
  python -m experiments.coverage_gap_map_xxv            # write experiments/coverage_gap_map_xxv.json
  python -m experiments.coverage_gap_map_xxv --check    # exit 1 if the live inventory differs from the record

`--check` is a snapshot check: once a release adds a class (for example a 26th), the recorded snapshot is stale
by design and `--check` reports the difference instead of passing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CATEGORIES = {
    1: "UNREPRESENTABLE",
    2: "REPRESENTABLE_NOT_GENERATED",
    3: "GENERATED_NOT_RECOGNIZED",
    4: "RECOGNIZED_NOT_FEASIBLE",
    5: "SUPPORTED_NOT_SOURCED",
    6: "BUDGET_TRUNCATED",
    7: "INTERNAL_ERROR",
}

SNAPSHOT_COMMIT = "11d05bb7b17fd3546b45c329e08dadbfb2dcb79b"
SNAPSHOT_DATE = "2026-11-08"
RECORDED_CLASS_COUNT = 25
RECORDED_REGISTRY_DIGEST = "d9f7e867e8f1a1d2"

# Issues closed on GitHub as of SNAPSHOT_DATE, with the commits that closed them (from `gh issue view` and
# `git log --grep`). The 2026-10-12/13 coverage audits predate these; they are NOT open gaps.
SOLVED_SINCE_AUDIT = {
    106: ["ade0f28"], 107: ["ab35f5d", "40d1e7f"], 110: ["cb79877"], 112: ["ade0f28"],
    114: ["8776c28", "34e1891"], 115: ["cf3d942"], 119: ["be5f8a1"], 123: ["466e0e3"], 124: ["474e018"],
    126: ["eacc086"], 127: ["measured null result"], 128: ["246fbd2"], 129: ["246fbd2"], 131: ["d8adf19"],
}

# One row per remaining gap; `category` is the single best classification at SNAPSHOT_COMMIT.
GAPS = [
    {"id": "G1", "issue": 116, "gap": "alkenes from alcohols/halides (elimination, dehydration)", "category": 2,
     "note": "rank-increasing; legal only in the event_search INTRAMOLECULAR_COPRODUCT lane; oracle ABSTAINs"},
    {"id": "G2", "issue": 117, "gap": "aldol / Knoevenagel / Henry / Michael C-C enolate chemistry", "category": 2},
    {"id": "G3", "issue": 118, "gap": "[2+2] cycloaddition, hetero-ene", "category": 2},
    {"id": "G4", "issue": 120, "gap": "Grignard / RLi addition to C=O with two-stage workup", "category": 1,
     "note": "needs Li/Mg organometallic representation and charge"},
    {"id": "G5", "issue": 121, "gap": "1,3-dipolar [3+2] cycloadditions", "category": 1,
     "note": "needs per-atom charge (#105)"},
    {"id": "G6", "issue": 122, "gap": "oxidation / dehydrogenative FGI", "category": 2},
    {"id": "G7", "issue": 113, "gap": "Kumada/Negishi/Stille/Heck/Sonogashira/Buchwald recognition", "category": 3,
     "note": "needs a hybridization predicate and a catalyst gate"},
    {"id": "G8", "issue": 111, "gap": "aryl ethers, thioethers, aryl sulfonates, sulfonamides, AcOH->Ac2O",
     "category": 3, "note": "hand-built probe steps return no class"},
    {"id": "G9", "issue": "104/125", "gap": "Dieckmann, intramolecular aldol, lactam, cyclic-ether producers",
     "category": 2, "note": "Wittig additionally needs charge"},
    {"id": "G10", "issue": 105, "gap": "per-atom charge rail", "category": 1},
    {"id": "G11", "issue": 108, "gap": "Li, Sn, Ni, Al, Ti, bracket [B] elements", "category": 1},
    {"id": "G12", "issue": 130, "gap": "R/S, E/Z and isotope identity at terminal/stock matching", "category": 1,
     "note": "resonance_identity equates enantiomers, E/Z isomers and isotopologues (probed)"},
    {"id": "G13", "issue": 109, "gap": "must-not-vouch pins missing for some conserved fictions", "category": 3},
    {"id": "G14", "issue": 103, "gap": "conditions/procedure corpus small; most classes cap at REACTION_VOUCHED",
     "category": 5},
    {"id": "G15", "issue": 103, "gap": "aqueous free-acid UNKNOWN guard; anti-Bredt/strain not modeled",
     "category": 4},
    {"id": "G16", "issue": 127, "gap": "cut/lateral/coproduct budgets and max_depth bound reachability",
     "category": 6},
    {"id": "G17", "issue": 131, "gap": "typed INTERNAL_RECOGNIZER_ERROR exists; no open instance known",
     "category": 7, "note": "completeness of this row is UNVERIFIED"},
]


def live_inventory() -> dict:
    from smartchem import algebra_profiles as ap
    from smartchem.experiment.reaction_type_oracle import _RECOGNIZERS

    names = [name for name, _predicate in _RECOGNIZERS]
    digest = hashlib.sha256("\n".join(sorted(names)).encode()).hexdigest()[:16]
    profiles = {}
    for pid, registry in ap.ALGEBRA_PROFILES.items():
        profiles[pid] = [p.identity[0] for p in registry.providers]
    return {
        "recognizer_count": len(names),
        "registry_digest": digest,
        "recognizer_classes": names,
        "algebra_profiles": profiles,
        "default_route_algebra_profile": ap.DEFAULT_ROUTE_ALGEBRA_PROFILE,
    }


def build() -> dict:
    for row in GAPS:
        if row["category"] not in CATEGORIES:
            raise ValueError(f"{row['id']}: unknown category {row['category']}")
    return {
        "schema": "smartchem.research.coverage_gap_map/xxv-1",
        "snapshot_commit": SNAPSHOT_COMMIT,
        "snapshot_date": SNAPSHOT_DATE,
        "categories": {str(k): v for k, v in CATEGORIES.items()},
        "inventory": live_inventory(),
        "solved_since_2026_10_audits": {str(k): v for k, v in SOLVED_SINCE_AUDIT.items()},
        "gaps": [dict(row, category_name=CATEGORIES[row["category"]]) for row in GAPS],
        "boundary": "Issue states were read from GitHub on the snapshot date; categories are an audit judgement, "
                    "not a theorem. A gap in category 2 is a pathway gap, never a proof of impossibility.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    inv = live_inventory()
    if args.check:
        ok = inv["recognizer_count"] == RECORDED_CLASS_COUNT and inv["registry_digest"] == RECORDED_REGISTRY_DIGEST
        print(json.dumps({"recorded": [RECORDED_CLASS_COUNT, RECORDED_REGISTRY_DIGEST],
                          "live": [inv["recognizer_count"], inv["registry_digest"]], "match": ok}))
        return 0 if ok else 1
    if inv["recognizer_count"] != RECORDED_CLASS_COUNT or inv["registry_digest"] != RECORDED_REGISTRY_DIGEST:
        print("refusing to write: live inventory differs from the recorded snapshot; re-audit first", file=sys.stderr)
        return 1
    out = Path(__file__).with_name("coverage_gap_map_xxv.json")
    out.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
