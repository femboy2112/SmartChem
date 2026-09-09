"""CIP-RING-CENTRE-01: ROUND 35 supersedes the ROUND-34 ring-centre deferral.

The parser now preserves the exact written-neighbour sequence, including a ring digit at its opening position.
Constitutionally ordered ring centres therefore name, including menthol.  Bounded Rules 4a/5 name non-recursive
auxiliary cases elsewhere, while mutually dependent pseudo-asymmetric ring pairs still defer pending Rule 4b/4c.

The original ROUND-34 failure analysis is retained in the superseded scope document.  This harness now pins both
the newly named constitutional population and the still-dark recursive pseudo population.  ``_on_cycle`` is used
only as a topology control here, not as the public-parser gate.
``validate()``/``content_hash()`` are RDKit-FREE; ``_rdkit_cross_check()`` re-verifies the oracle labels live.
Re-run ``python -m experiments.cip_ring_centre_probe`` after an INTENTIONAL change and set ``FROZEN_HASH``.
"""
from __future__ import annotations

import hashlib
import json

from smartchem import smiles
from smartchem.smiles import cip_labels

FROZEN_HASH = "7bd5eadcc97787ed703cfc7307431dcb8964772d4dc693ead6f2255b86a76caa"

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).
#:   ringcentre-name | rule45-defer | agreed-defer
BATTERY = (
    ("C[C@H]1CCCCC1O",                   ("S",),           ("S",), "ringcentre-name", "3-methylcyclohexanol"),
    ("O[C@H]1CCCC[C@@H]1O",              ("S", "S"),       ("S", "S"), "ringcentre-name", "trans-cyclohexane-1,2-diol"),
    ("[C@H]1(F)CCCC[C@@H]1Cl",           ("S", "S"),       ("S", "S"), "ringcentre-name", "1-F-2-Cl-cyclohexane"),
    ("F[C@H]1CCCC[C@H]1Cl",              ("R", "S"),       ("R", "S"), "ringcentre-name", "cis 1-F-2-Cl-cyclohexane"),
    ("O[C@H]1CC[C@@H](C)CC1",            ("s", "s"),       (), "rule45-defer", "mutually pseudo-asymmetric; needs Rule 4b/4c"),
    ("O[C@@H]1CC[C@H](Cl)CC1",           ("s", "s"),       (), "rule45-defer", "mutually pseudo-asymmetric; needs Rule 4b/4c"),
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O",  ("R", "R", "S"),  ("R", "R", "S"), "ringcentre-name", "menthol"),
    # agreed-defer: a SYMMETRIC ring carbon is not a real stereocentre -- both we and RDKit defer (sound, not a consumer)
    ("O[C@H]1CCCCC1",                    (),               (), "agreed-defer", "cyclohexanol C1: two identical ring arms -> not a stereocentre"),
    ("C1CC[C@H](O)CC1",                  (),               (), "agreed-defer", "4-position of cyclohexanol: symmetric -> not a stereocentre"),
)


def defers(lab) -> bool:
    return not lab or any(x in (None, "?", "") for x in (lab or ()))


def _on_cycle_gates_all_marked_ring_centres() -> bool:
    """RDKit-free topology control: every marked non-agreed battery centre lies on a ring."""
    from smartchem.smiles import _parse_skeleton, _kekulize_in_place, _fill_hydrogens, _on_cycle
    for smi, _rd, _exp, cat, _n in BATTERY:
        if cat == "agreed-defer":
            continue
        atoms, bonds = _parse_skeleton(smi)
        charge = sum(a.charge for a in atoms)
        work = [list(b) for b in bonds]
        _kekulize_in_place(atoms, work, charge)
        fa, fb = _fill_hydrogens(atoms, work)
        nbr: dict = {i: [] for i in range(len(fa))}
        for b in fb:
            nbr[b.i].append(b.j)
            nbr[b.j].append(b.i)
        marked = [a for a in range(len(atoms)) if atoms[a].chirality]
        if not all(_on_cycle(a, nbr, len(fa)) for a in marked):
            return False
    return True


def content_hash() -> str:
    payload = {
        "battery": [[smi, list(rd), list(exp), cat] for smi, rd, exp, cat, _n in BATTERY],
        "ours_live": [list(cip_labels(smi)) for smi, *_ in BATTERY],
        "on_cycle_gates": _on_cycle_gates_all_marked_ring_centres(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> None:
    """RDKit-free: admitted centres match baked labels and recursive pseudo cases defer."""
    named = deferred = agreed = 0
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        if category == "ringcentre-name":
            assert got == rd_label
            named += 1
        elif category == "rule45-defer":
            assert defers(got) and rd_label
            deferred += 1
        else:
            assert not rd_label, f"{smi} agreed-defer means rdkit also defers [{note}]"
            agreed += 1
    assert named >= 5
    assert deferred >= 2
    assert agreed >= 1, "must include a symmetric non-stereocentre (agreed defer, sound)"
    assert _on_cycle_gates_all_marked_ring_centres()


def _rdkit_cross_check() -> dict:
    """Re-verify the baked oracle labels live (the consumer really is named by RDKit)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    def rd_label(smi):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            return None
        rdCIPLabeler.AssignCIPLabels(m)
        return tuple(sorted(a.GetProp("_CIPCode") for a in m.GetAtoms() if a.HasProp("_CIPCode")))

    for smi, rd_baked, _exp, _cat, note in BATTERY:
        live = rd_label(smi)
        assert live is not None and set(live) == set(rd_baked), f"baked rdkit label stale on {smi}: {live} vs {rd_baked} [{note}]"
    return {"battery_verified": len(BATTERY),
            "named": sum(1 for *_r, c, _n in BATTERY if c == "ringcentre-name")}


def report() -> dict:
    return {
        "battery_size": len(BATTERY),
        "on_cycle_gates_all": _on_cycle_gates_all_marked_ring_centres(),
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
