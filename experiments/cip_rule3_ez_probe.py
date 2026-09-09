"""CIP-RULE3-EZ-01: ROUND 34 item 1 -- CIP Rule 3 (double-bond seqcis 'Z' > seqtrans 'E') is BUILT.

R32 identified the acyclic deferrals that RDKit labels but our namer left as ``()`` -- and PROVED they are Rule 3
(E/Z geometry) on constitutionally-identical ligands, NEVER Rule 1b (an acyclic Rule-1a tie <=> identical
constitution, so Rule 1b is inert on trees).  The isolation: ``C[C@](/C=C\\C)(/C=C/C)O`` -- a stereocentre whose
two propenyl arms are identical except one is Z, one is E -- ties under Rules 1a AND 2, so only Rule 3 decides.

THE BUILD (R34 item 1):
  * PARSER: ``_parse_skeleton_dirs`` recovers the ``/``/``\\`` directional markers (``_parse_skeleton`` collapses
    them to single bonds), keyed by the written endpoint order.  No downstream ``bonds`` consumer changes.
  * PERCEPTION: ``_cip_ez_by_atom`` gives each stereogenic ACYCLIC double-bond END atom a CIP-RELATIVE E/Z code
    (2='Z'/seqcis, 1='E'/seqtrans), computed by ranking the double-bond substituents with the SAME ``_cip_compare``
    and DEFERRING (no code) on any ambiguity -- unknown geometry (no marker), a ring double bond, or a tied
    substituent.  Calibrated to ``F/C=C/F`` (E) and ``F/C=C\\F`` (Z).
  * DIGRAPH: the node gains an ``ez`` slot at index 3 (append-only; the index-0/1/2 z/mass/children code is
    byte-untouched).  ``_cip_compare_rule3`` mirrors Rule 2's breadth-first shape on that slot (Z=2 > E=1), entered
    ONLY at the Rule-1a-AND-Rule-2 tie hand-off in ``_cip_rank_compare`` (CIP hierarchy).
  * A Rule-2/3 SIBLING-GUARD relaxation: the all-pairs tied-sibling guard now raises ``_CipAmbiguous`` only when the
    tied siblings are STRUCTURALLY DISTINCT (deep tuple ``!=``); STRUCTURALLY IDENTICAL tied siblings (a methyl's
    three H's) are interchangeable -> safe to pair, do NOT defer.  Without this, Rule 2 raised mid-descent on any
    symmetric substituent and Rule 3 never ran.  (Sound; makes Rule 2 itself more complete -- 0 new mislabels.)

Consumer (recon, 2026-09-08, rdkit 2026.3.6): a stereocentre with two E/Z-differing acyclic ligands (R32's
boundary).  ``validate()``/``content_hash()`` are RDKit-FREE; ``_rdkit_cross_check()`` re-runs the sweep live.
SOUNDNESS BAR: where both label, they MATCH; we may DEFER where RDKit names; we NEVER name where RDKit defers.
Re-run ``python -m experiments.cip_rule3_ez_probe`` after an INTENTIONAL change and set ``FROZEN_HASH``.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from smartchem.smiles import cip_labels

FROZEN_HASH = "f065f6a3b50dcd6df1f96aa8c9f283cc7b96b31cd9972d27b9c304ed4bc77659"

#: E/Z-bearing alkene ligands (Z and E of the same constitution, plus a diene) for the sweep.
_ALKENES = (r"/C=C\C", r"/C=C/C", r"/C=C\CC", r"/C=C/CC", r"/C=C\Cl", r"/C=C/Cl", r"/C=C\Br", r"/C=C/Br",
            r"/C=C/CO", r"/C=C\CO", r"/C=C/C=C/C", r"/C=C\C=C\C")
_OTHERS = ("O", "F", "Cl", "N", "CC")   # trailing spectator; a LEADING methyl gives the centre 4 explicit
#: neighbours (rdkit does not assign the centre-first ``[C@](...)`` implicit-H form, so the sweep writes ``C[C@]...``)

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).  ez-name | boundary-defer
BATTERY = (
    (r"C[C@](/C=C\C)(/C=C/C)O",     ("R",), ("R",), "ez-name", "the R32 isolation: Z-propenyl > E-propenyl (Rule 3)"),
    (r"C[C@](/C=C/C)(/C=C\C)O",     ("S",), ("S",), "ez-name", "swap arms -> S"),
    (r"O[C@](/C=C\C)(/C=C/C)F",     ("R",), ("R",), "ez-name", "different spectators"),
    (r"F[C@](/C=C\CC)(/C=C/CC)Cl",  ("R",), ("R",), "ez-name", "but-2-enyl arms, Z vs E"),
    (r"[C@H](/C=C/C)(/C=C\C)O",     ("S",), ("S",), "ez-name", "implicit-H centre"),
    (r"CC[C@](/C=C\Br)(/C=C/Br)O",  ("R",), ("R",), "ez-name", "bromo-alkene arms (higher-Z substituent)"),
    (r"C/C=C/[C@](C)(O)/C=C\C",     ("S",), ("S",), "ez-name", "E and Z arms written across the centre"),
    (r"OC[C@](/C=C/C)(/C=C\C)N",    ("S",), ("S",), "ez-name", "CH2OH + N spectators"),
    (r"C[C@](/C=C\CO)(/C=C/CO)F",   ("R",), ("R",), "ez-name", "allylic-alcohol arms"),
    # --- boundary DEFERRALS (rdkit ALSO defers, or geometry unresolvable) ---
    (r"C[C@](C=CC)(C=CC)O",         (), (), "boundary-defer", "NO direction markers -> geometry unknown (rdkit defers too)"),
    (r"[C@]1(/C=C/C)CCCC1",         (), (), "boundary-defer", "ring stereocentre -> out of scope (rdkit defers too)"),
)


def defers(lab) -> bool:
    return not lab or any(x in (None, "?", "") for x in (lab or ()))


def _ez_sweep_named() -> dict:
    """RDKit-FREE: how many E/Z stereocentres our namer names, all as real labels -- Rule 3 non-vacuously firing."""
    named = defrs = 0
    for a, b in itertools.combinations(_ALKENES, 2):
        for o in _OTHERS:
            got = cip_labels(f"C[C@]({a})({b}){o}")
            if got and all(x in ("R", "S") for x in got):
                named += 1
            else:
                defrs += 1
    return {"named": named, "defers": defrs, "pairs": named + defrs}


def content_hash() -> str:
    payload = {
        "battery": [[smi, list(rd), list(exp), cat] for smi, rd, exp, cat, _n in BATTERY],
        "ours_live": [list(cip_labels(smi)) for smi, *_ in BATTERY],
        "sweep": _ez_sweep_named(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> None:
    counts = {"ez-name": 0, "boundary-defer": 0}
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        counts[category] += 1
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi}: {got} != rdkit {rd_label} [{note}]"
        else:
            assert defers(got), f"{smi} must DEFER [{note}]"
    assert counts["ez-name"] >= 8, "must non-vacuously name the E/Z (Rule 3) class"
    assert counts["boundary-defer"] >= 2, "must pin the unresolvable-geometry + ring-centre boundaries"
    # the R32 isolation now NAMES (Rule 3 built); an isotope Rule-2 tie and a plain centre are unchanged.
    assert cip_labels(r"C[C@](/C=C\C)(/C=C/C)O") == ("R",), "the R32 Rule-3 isolation must NAME (R34)"
    assert cip_labels("F[C@@](Cl)([2H])[3H]") == ("R",), "isotope Rule 2 unchanged"
    assert cip_labels("C[C@H](N)C(=O)O") == ("S",), "plain Rule-1a centre unchanged"
    sweep = _ez_sweep_named()
    assert sweep["named"] >= 40, f"E/Z sweep should name a non-trivial population, got {sweep['named']}"


def _rdkit_cross_check() -> dict:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    def rd_label(smi):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            return None
        rdCIPLabeler.AssignCIPLabels(m)
        return tuple(sorted(a.GetProp("_CIPCode") for a in m.GetAtoms() if a.HasProp("_CIPCode")))

    for smi, rd_baked, _exp, cat, note in BATTERY:
        if cat.endswith("-name"):
            live = rd_label(smi)
            assert live is not None and set(live) == set(rd_baked), f"baked rdkit label stale on {smi}: {live} [{note}]"

    named = mismatches = deferred = 0
    for a, b in itertools.combinations(_ALKENES, 2):
        for o in _OTHERS:
            smi = f"C[C@]({a})({b}){o}"
            ours = cip_labels(smi)
            rl = rd_label(smi)
            if rl is None:
                continue
            if defers(ours):
                deferred += 1
            elif defers(rl) or set(ours) != set(rl):
                mismatches += 1
            else:
                named += 1
    assert mismatches == 0, f"SWEEP MISMATCH -- Rule 3 mislabels ({mismatches})"
    return {"battery_verified": len(BATTERY), "ez_named": named, "ez_deferred": deferred, "mismatches": mismatches}


def report() -> dict:
    sweep = _ez_sweep_named()
    return {
        "battery_size": len(BATTERY),
        "ez_sweep_named": sweep["named"],
        "ez_sweep_pairs": sweep["pairs"],
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
