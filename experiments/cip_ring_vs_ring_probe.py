"""CIP-RING-VS-RING-01: ROUND 34 item 5 -- Rule-1a-distinct ring-vs-ring comparisons NAME.

The first R34 implementation classified this item as VERIFIED DEFER because disabling its released-ring guard
reproduced same-kind unsaturated-ring mislabels.  The round's final adversarial review found the deeper cause: the
Rule-1a comparator exhausted its highest-ranked child recursively before visiting a lower-ranked sibling.  That was
not the Hanson/Mayfield FIFO pair queue and it also mislabelled purely acyclic and saturated-heteroring molecules.

After the queue correction, the former ring-vs-ring failures all match RDKit ``rdCIPLabeler``.  The old guard then
has no remaining load-bearing counterexample: a 30-fragment all-kind holdout (2,586 named comparisons over @/@@ and
three spectator contexts) produced zero mismatches with the guard absent.  Production therefore removes both the
guard and its ``released`` bookkeeping rather than retaining a ceremonial defer.

BOUNDARY: a ring-bearing pair that TIES under Rule 1a still defers before Rule 2 because Rule 1b can act on ring-
closure duplicates.  The isotope-on-identical-ring cases below pin that safe boundary.  Ring-on-centre Rules 4/5
remain a separate scope wall.

``validate()`` and ``content_hash()`` are RDKit-free. ``_rdkit_cross_check()`` is a gated development-oracle probe.
Re-run ``python -m experiments.cip_ring_vs_ring_probe`` after an intentional change and update ``FROZEN_HASH``.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from smartchem.smiles import cip_labels

FROZEN_HASH = "d22a18f49d7740b73347be1e1a5698ee69e5391b9d1ec97eb25fdfe90cf941f3"

_SAT = ("C1CC1", "C1CCC1", "C1CCCC1", "C1CCCCC1", "C1CCCCCC1", "C1OCC1", "C1OCCC1",
        "C1OCCCC1", "C1CCCO1", "C1CCCCO1", "C1NCCC1", "C1NCCCC1", "C1CCNC1", "C1SCCC1",
        "C1CCCS1", "C1COCC1", "C1CNCC1", "C1COCCC1")
_LOC = ("C1=CC1", "C1=CCC1", "C1=CCCC1", "C1=CCCCC1")
_EXO = ("C1CCCC1=O", "C1CCCCC1=O", "C1CCCCC1=C")
_ARO = ("c1ccccc1", "c1ccncc1", "c1ccoc1")
_FUSED = ("C1Cc2ccccc2C1", "C1CCc2ccccc2C1")
_RINGS = tuple(dict.fromkeys(_SAT + _LOC + _EXO + _ARO + _FUSED))

#: (SMILES, RDKit label, expected ours, category, note): ringring-name | isotope-ring-defer.
BATTERY = (
    ("[C@](C1CCCCC1)(C1CCCC1)(C)F", ("R",), ("R",), "ringring-name", "two carbocyclic saturated rings"),
    ("C[C@](C1OCCC1)(C1OCC1)O", ("S",), ("S",), "ringring-name", "heterorings: THF vs oxetane"),
    ("C[C@](C1NCCC1)(C1NCCCC1)O", ("R",), ("R",), "ringring-name", "pyrrolidine vs piperidine"),
    ("[C@](c1ccccc1)(c1ccncc1)(C)O", ("S",), ("S",), "ringring-name", "pure mancude: phenyl vs pyridyl"),
    ("[C@](C1=CCCCC1)(C1=CCCC1)(C)F", ("S",), ("S",), "ringring-name", "two localized unsaturated rings"),
    ("[C@](C1=CC1)(C1=CCC1)(C)F", ("R",), ("R",), "ringring-name", "cyclopropenyl vs cyclobutenyl"),
    ("[C@](C1CCCC1=O)(C1CCCCC1=O)(C)F", ("R",), ("R",), "ringring-name", "two exocyclic ketone rings"),
    ("[C@](C1Cc2ccccc2C1)(C1CCc2ccccc2C1)(C)F", ("R",), ("R",), "ringring-name", "indane vs tetralin"),
    ("[C@](C1=CCCCC1)(c1ccccc1)(F)Cl", ("S",), ("S",), "ringring-name", "localized vs mancude"),
    ("[C@](C1Cc2ccccc2C1)(C1=CCCCC1)(C)F", ("S",), ("S",), "ringring-name", "fused vs localized"),
    ("[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl", ("R",), (), "isotope-ring-defer", "Rule-1a-tied isotope ring"),
    ("[C@]([13CH]1CCCC1)(C1CCCC1)(F)Cl", ("R",), (), "isotope-ring-defer", "Rule-1a-tied isotope ring"),
)


def defers(label) -> bool:
    return not label or any(value in (None, "?", "") for value in (label or ()))


def _ringring_named_sweep() -> dict:
    """RDKit-free non-vacuity over all pairwise ring classes in one spectator context."""
    named = deferred = 0
    for ring_a, ring_b in itertools.combinations(_RINGS, 2):
        got = cip_labels(f"[C@]({ring_a})({ring_b})(C)F")
        if got and all(value in ("R", "S") for value in got):
            named += 1
        else:
            deferred += 1
    return {"named": named, "deferred": deferred, "pairs": named + deferred}


def content_hash() -> str:
    payload = {
        "battery": [[smi, list(rd), list(expected), category] for smi, rd, expected, category, _note in BATTERY],
        "ours_live": [list(cip_labels(smi)) for smi, *_rest in BATTERY],
        "sweep": _ringring_named_sweep(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> None:
    counts = {"ringring-name": 0, "isotope-ring-defer": 0}
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        counts[category] += 1
        if category == "ringring-name":
            assert got == rd_label, f"MISLABEL vs baked oracle on {smi} [{note}]"
        else:
            assert defers(got) and rd_label, f"{smi} must remain a non-vacuous Rule-1b defer [{note}]"
    assert counts["ringring-name"] >= 10
    assert counts["isotope-ring-defer"] >= 2
    sweep = _ringring_named_sweep()
    assert sweep["named"] >= 300, f"ring-vs-ring sweep names too few centres: {sweep}"


def _rdkit_cross_check() -> dict:
    """All-kind ring-pair holdout across both senses and three spectator contexts."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    def rd_label(smi):
        molecule = Chem.MolFromSmiles(smi)
        if molecule is None:
            return None
        rdCIPLabeler.AssignCIPLabels(molecule)
        return tuple(sorted(atom.GetProp("_CIPCode") for atom in molecule.GetAtoms()
                            if atom.HasProp("_CIPCode") and atom.GetProp("_CIPCode") in ("R", "S")))

    for smi, baked, _expected, _category, note in BATTERY:
        live = rd_label(smi)
        assert live is not None and live == baked, f"baked RDKit label stale on {smi}: {live} [{note}]"

    compared = deferred = skipped = mismatches = 0
    for ring_a, ring_b in itertools.combinations(_RINGS, 2):
        for tag in ("@", "@@"):
            for tail in ("(C)F", "(C)O", "(N)O"):
                smi = f"[C{tag}]({ring_a})({ring_b}){tail}"
                ours, oracle = cip_labels(smi), rd_label(smi)
                if oracle is None:
                    skipped += 1
                elif defers(ours):
                    deferred += 1
                elif len(ours) == len(oracle) == 1:
                    compared += 1
                    if ours != oracle:
                        mismatches += 1
    assert mismatches == 0, f"ring-vs-ring holdout produced {mismatches} wrong labels"
    return {"battery_verified": len(BATTERY), "compared": compared, "deferred": deferred,
            "skipped": skipped, "mismatches": mismatches}


def report() -> dict:
    return {
        "battery_size": len(BATTERY),
        "ringring_sweep": _ringring_named_sweep(),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    try:
        print("rdkit cross-check:", _rdkit_cross_check())
    except ImportError:
        print("rdkit cross-check: SKIPPED (rdkit absent)")
    for key, value in report().items():
        print(f"{key}: {value}")
    print(f"\ncontent_hash (set FROZEN_HASH to this to freeze): {content_hash()}")
