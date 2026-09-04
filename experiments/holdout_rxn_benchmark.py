"""HOLDOUT-RXN-01: a FROZEN, family-stratified coverage benchmark for the transform algebra (Lane B).

Now that >=2 qualitatively distinct transform families ride the same bounded decompile (capped scission, bond-order
edit, heterolytic scission), this benchmark MEASURES cross-family coverage honestly: for each frozen target it finds
the smallest registry in an increasing chain -- [capped-only] < [+bond-order] < [+heterolytic] -- that constructs a
complete structural decomposition, attributing the target to the family that FIRST unlocks it (or OUTSIDE_CLOSURE if
no registered family does). The coverage report is then the count per attribution: exactly how much each algebra
widening buys.

The discipline (why it is a benchmark, not a demo):
  * FROZEN. The target set + each target's expected attribution + a content hash are frozen below (FROZEN_ATTRIB /
    FROZEN_HASH). tests/test_holdout_rxn.py asserts the LIVE attribution equals the frozen one and the hash matches,
    so the benchmark cannot silently drift and the holdout cannot be quietly re-labelled to flatter coverage.
  * NON-VACUOUS. The set deliberately spans every bucket -- families the default algebra CANNOT do
    (UNLOCKED_BY_BOND_ORDER, UNLOCKED_BY_HETEROLYTIC) and targets NO registered family can do (OUTSIDE_CLOSURE) --
    so coverage is never vacuously 100%. A target outside the whole algebra is reported as outside, not hidden.
  * A TRAIN/DEV/HOLDOUT split. The HOLDOUT ids + their expected attributions are frozen (HOLDOUT_HASH) as a held-out
    measurement set; the providers are hand-built chemistry (not fitted to it), and the anti-gaming property above
    means a wrong provider change moves a frozen attribution and fails the test rather than passing silently.

W3 unchanged: "constructible" here means a conservation- and valence-valid structural decomposition EXISTS within
the algebra and bounds (a FORMAL_CANDIDATE), never that any synthesis runs.

Run it:  .venv/bin/python experiments/holdout_rxn_benchmark.py
"""
from __future__ import annotations

import hashlib
import json

from smartchem.category import Bond, Molecule
from smartchem.smiles import parse_smiles
from smartchem.compilation_ir import decompile_structure_to_ir
from smartchem.transform_provider import (
    CappedScissionProvider,
    HeterolyticScissionProvider,
    TransformProviderRegistry,
)
from smartchem.bond_order_edit import BondOrderEditProvider

# the reagent pool (capped scission caps with it; bond-order and heterolytic ignore it) -- fixed so a target's
# attribution is a property of the ALGEBRA, not of a varying reagent set.
WATER = parse_smiles("O")

# the increasing registry chain: each step ADDS one family, so the first step that constructs a target names the
# family that unlocked it.  (capped is the default algebra; the two extensions are the genericity payoff.)
_CAPPED = TransformProviderRegistry((CappedScissionProvider(),))
_CAPPED_BOND = TransformProviderRegistry((CappedScissionProvider(), BondOrderEditProvider()))
_FULL = TransformProviderRegistry((CappedScissionProvider(), BondOrderEditProvider(), HeterolyticScissionProvider()))
REGISTRY_CHAIN = (
    ("CONSTRUCTIBLE_BY_CAPPED", _CAPPED),
    ("UNLOCKED_BY_BOND_ORDER", _CAPPED_BOND),
    ("UNLOCKED_BY_HETEROLYTIC", _FULL),
)


def _diatomic(a: str, b: str, order: int = 1) -> Molecule:
    return Molecule((a, b), frozenset({Bond(0, 1, order)}), 0, "")


# The FROZEN, family-stratified target set.  Each entry: id -> (builder, split).  A builder is a zero-arg callable so
# the set is data, not a live import-time computation.  Splits: train / dev / holdout.
TARGETS: dict = {
    # -- CAPPED (constructible by the default capped-scission algebra over water) --
    "paracetamol": (lambda: parse_smiles("CC(=O)Nc1ccc(O)cc1"), "train"),
    "aspirin": (lambda: parse_smiles("CC(=O)Oc1ccccc1C(=O)O"), "train"),
    "ethane": (lambda: parse_smiles("CC"), "train"),
    "propane": (lambda: parse_smiles("CCC"), "train"),
    "methyl_acetate": (lambda: parse_smiles("CC(=O)OC"), "dev"),
    "propene": (lambda: parse_smiles("CC=C"), "dev"),
    "ethyl_acetate": (lambda: parse_smiles("CC(=O)OCC"), "holdout"),
    "butane": (lambda: parse_smiles("CCCC"), "holdout"),
    # -- BOND_ORDER (capped cannot; a dehydrogenation bond-order edit unlocks it) --
    "ethylene": (lambda: parse_smiles("C=C"), "dev"),
    "benzene": (lambda: parse_smiles("c1ccccc1"), "holdout"),
    # -- HETEROLYTIC (neither capped nor bond-order; a charged single-bond heterolysis unlocks it) --
    "hydrogen_chloride": (lambda: _diatomic("H", "Cl"), "train"),
    "hydrogen_fluoride": (lambda: _diatomic("H", "F"), "train"),
    "methane": (lambda: parse_smiles("C"), "dev"),
    "acetylene": (lambda: parse_smiles("C#C"), "holdout"),
    "water": (lambda: WATER, "holdout"),
    # -- OUTSIDE_CLOSURE (no registered family constructs it at these bounds) --
    "dinitrogen": (lambda: _diatomic("N", "N", 3), "train"),
    "neon": (lambda: Molecule(("Ne",), frozenset(), 0, ""), "dev"),
    "dioxygen": (lambda: _diatomic("O", "O", 2), "holdout"),
}


def attribute(molecule) -> str:
    """The family that FIRST constructs a complete structural decomposition of ``molecule`` in the increasing chain,
    or ``OUTSIDE_CLOSURE`` if none does; ``INCOMPLETE_WITHIN_BOUNDS`` if a step found candidates but truncated."""
    for family, registry in REGISTRY_CHAIN:
        ir = decompile_structure_to_ir(molecule, reagents=(WATER,), registry=registry)
        if ir.structural_candidates:
            return family if ir.complete_within_bounds else "INCOMPLETE_WITHIN_BOUNDS"
    return "OUTSIDE_CLOSURE"


def measure() -> dict:
    """The live attribution of every frozen target (id -> attribution)."""
    return {tid: attribute(builder()) for tid, (builder, _split) in TARGETS.items()}


def target_fingerprint() -> str:
    """A content hash of the frozen target set -- the canonical (id, canonical-molecule-digest, split) triples.  Any
    silent edit to a target's structure or split moves this, so the frozen expectations cannot drift unnoticed."""
    from smartchem.compilation_ir import StructuralSpecies
    rows = []
    for tid, (builder, split) in sorted(TARGETS.items()):
        mol = builder()
        rows.append([tid, StructuralSpecies.of_molecule(mol).structure.identity_digest, split])
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


# ---- the FROZEN expectations (regenerate deliberately with --freeze after an INTENTIONAL algebra change) ----------
FROZEN_ATTRIB: dict = {
    "acetylene": "UNLOCKED_BY_HETEROLYTIC",
    "aspirin": "CONSTRUCTIBLE_BY_CAPPED",
    "benzene": "UNLOCKED_BY_BOND_ORDER",
    "butane": "CONSTRUCTIBLE_BY_CAPPED",
    "dinitrogen": "OUTSIDE_CLOSURE",
    "dioxygen": "OUTSIDE_CLOSURE",
    "ethane": "CONSTRUCTIBLE_BY_CAPPED",
    "ethyl_acetate": "CONSTRUCTIBLE_BY_CAPPED",
    "ethylene": "UNLOCKED_BY_BOND_ORDER",
    "hydrogen_chloride": "UNLOCKED_BY_HETEROLYTIC",
    "hydrogen_fluoride": "UNLOCKED_BY_HETEROLYTIC",
    "methane": "UNLOCKED_BY_HETEROLYTIC",
    "methyl_acetate": "CONSTRUCTIBLE_BY_CAPPED",
    "neon": "OUTSIDE_CLOSURE",
    "paracetamol": "CONSTRUCTIBLE_BY_CAPPED",
    "propane": "CONSTRUCTIBLE_BY_CAPPED",
    "propene": "CONSTRUCTIBLE_BY_CAPPED",
    "water": "UNLOCKED_BY_HETEROLYTIC",
}
FROZEN_HASH = "be026aaff5127006a5110f0676e7c427468a7f2980ba30f59fb347ef5cebe687"
HOLDOUT_HASH = "3da693ad062fcdddce6d7ee2f73da3f52d4c9a740f6b62938b4c273673be187b"   # the holdout subset, frozen separately


def _holdout_fingerprint() -> str:
    from smartchem.compilation_ir import StructuralSpecies
    rows = []
    for tid, (builder, split) in sorted(TARGETS.items()):
        if split != "holdout":
            continue
        rows.append([tid, StructuralSpecies.of_molecule(builder()).structure.identity_digest,
                     FROZEN_ATTRIB.get(tid)])
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def coverage_report() -> str:
    live = measure()
    by_bucket: dict = {}
    for tid, attrib in live.items():
        by_bucket.setdefault(attrib, []).append(tid)
    order = ["CONSTRUCTIBLE_BY_CAPPED", "UNLOCKED_BY_BOND_ORDER", "UNLOCKED_BY_HETEROLYTIC",
             "INCOMPLETE_WITHIN_BOUNDS", "OUTSIDE_CLOSURE"]
    total = len(live)
    constructible = sum(len(by_bucket.get(b, [])) for b in order[:3])
    lines = [f"HOLDOUT-RXN-01 coverage over {total} family-stratified targets (frozen hash {target_fingerprint()[:12]})", ""]
    cumulative = 0
    for b in order:
        ids = sorted(by_bucket.get(b, []))
        if b in order[:3]:
            cumulative += len(ids)
        lines.append(f"  {b:26} {len(ids):2}   {', '.join(ids)}")
    lines += [
        "",
        f"  default (capped) algebra constructs : {len(by_bucket.get('CONSTRUCTIBLE_BY_CAPPED', []))}/{total}",
        f"  + bond-order unlocks                : +{len(by_bucket.get('UNLOCKED_BY_BOND_ORDER', []))}",
        f"  + heterolytic unlocks               : +{len(by_bucket.get('UNLOCKED_BY_HETEROLYTIC', []))}",
        f"  constructible within the full algebra: {constructible}/{total}   outside-closure: "
        f"{len(by_bucket.get('OUTSIDE_CLOSURE', []))}/{total}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if "--freeze" in sys.argv:
        # deliberate regeneration after an intentional algebra change: prints the blocks to paste back in.
        live = measure()
        print("FROZEN_ATTRIB = {")
        for tid in sorted(live):
            print(f"    {tid!r}: {live[tid]!r},")
        print("}")
        print(f'FROZEN_HASH = "{target_fingerprint()}"')
        print(f'HOLDOUT_HASH = "{_holdout_fingerprint()}"')
    else:
        print(coverage_report())
