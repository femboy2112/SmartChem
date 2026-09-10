"""CIP-EXOCYCLIC-RING-01: ROUND 34 item 2 -- ring substituents whose only unsaturation is EXOCYCLIC now NAME.

R33 (``cip_localized_ring_probe.py``) closed the LOCALIZED unsaturated-ring gap (a ring double bond, unique
Kekule) but left, as a characterised next gap, the EXOCYCLIC case: an off-ring stereocentre bearing a ring whose
double bond points OUT of the ring -- a ring ketone/lactone/lactam C=O, an exocyclic C=C/C=N/C=S.  ``_cip_mancude``
blocked the whole ring component (an atom with a bond order > 1 admitted it, then no pi-acceptor pattern matched
the exocyclic-double carbon -> ``else: valid=False`` -> the ring deferred).

THE FIX (R34 item 2): a ring component whose only unsaturation is EXOCYCLIC -- every RING edge is a plain single
bond (``o != 1`` on no ring edge) and no ring atom is aromatic -- is a LOCALIZED saturated ring SKELETON with no
Kekule ambiguity in the ring itself.  Its exocyclic double bonds and ring closures are handled soundly by the
ordinary ``_cip_digraph`` EXACTLY as an acyclic double bond and a saturated ring already are, so the whole
component is RELEASED (real z/mass), like R33's localized rings.  A ring with an INTERNAL ring double (an enone,
an aromatic or explicit-Kekule ring) fails the test and stays on the mancude/matching path.  ROUND 34's FIFO
Rule-1a correction also permits a Rule-1a-distinct exocyclic ring to be ranked against another ring; both single-
and two-ring cases NAME when the built rules fully order them.

ROUND 39 UPDATE (``cip_conjugated_carbonyl_probe.py``): the conjugated boundary this probe pinned has MOVED.  A
conjugated ring (internal ring double) bearing an exocyclic TERMINAL-CHALCOGEN carbonyl (a ring enone / dienone /
quinone / butenolide C=O or C=S) now NAMES too -- the exocyclic-carbonyl carbon is admitted as a ring SPECTATOR
(``_exocyclic_carbonyl_spectator``) and the ring releases on its unique acceptor matching.  The two former
boundary-defer entries (cyclohexenone, cyclopentenone) are re-tagged ``exocyclic-name`` here; the remaining
boundary-defer entries are the R39 boundary -- a conjugated ring bearing an exocyclic =CH2 / =NH (the
aromatic-resonance-ambiguous non-benzenoid systems) or a CHARGED ring, which still defer fail-closed.

Consumer size (recon, 2026-09-08, rdkit 2026.3.6): every real ring carbonyl/exocyclic-alkene substituent -- the
single largest real-molecule ring class.  This harness pins the finding ("experiments are committed") and doubles
as a DIFFERENTIAL VALIDATION against RDKit ``rdCIPLabeler`` (dev-venv-only oracle; ABSENT from the runtime + the
committed suite).  ``validate()``/``content_hash()`` are RDKit-FREE; ``_rdkit_cross_check()`` re-runs the sweep
live when rdkit is present and SKIPS otherwise.

SOUNDNESS BAR (verified by the sweep): where BOTH label, they MATCH; we may DEFER where RDKit names; we NEVER name
where RDKit defers, and never disagree.  Re-run ``python -m experiments.cip_exocyclic_ring_probe`` after an
INTENTIONAL change and set ``FROZEN_HASH`` to the printed value.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from smartchem.smiles import cip_labels

#: The committed tamper pin.  Regenerate ONLY on an intentional change.
FROZEN_HASH = "25f1bcbf840f95ad89ad20b6216e41c48b8e82ec4f058edca14ab0aab3b36723"

#: Exocyclic-unsaturation ring fragments (attach at the first ring atom): the RING skeleton is all single bonds;
#: the double bond points OUT (C=O ketone, =C alkene, =N imine, =S thioketone), at various ring sizes/positions,
#: including a spiro skeleton and a ring-1,2-dione (both ring edges still single).
_EXO_RINGS = ("C1CCC1=O", "C1CCCC1=O", "C1CCCCC1=O", "C1CCCCCC1=O", "C1CCCCC1=C", "C1CCCCC1=CC",
              "C1CCCCC1=N", "C1CCCCC1=S", "C1CCC(=O)CC1", "C1CC(=O)CC1", "C1CCC(=O)C1", "C1CCC(=O)O1",
              "C1CCC(=O)N1", "C1CC(=O)OC1", "C1CC(=C)CC1", "C1C(=O)CCCC1=O", "C1CCC2(CCCC2=O)C1")
#: ACYCLIC spectator co-ligands used by the bounded class sweep.
_SPECTATORS = ("C", "CC", "CCC", "C(C)C", "CO", "O", "N", "S", "F", "Cl")

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).  Categories:
#:   exocyclic-name | exocyclic-multi-name | boundary-defer
BATTERY = (
    ("[C@](C1CCCC1=O)(C)(F)Cl",       ("R",), ("R",), "exocyclic-name", "cyclopentanone-yl C=O (R33 exocyclic-defer, now NAMED)"),
    ("[C@](C1CCCCC1=O)(C)(F)Cl",      ("R",), ("R",), "exocyclic-name", "cyclohexanone-yl C=O"),
    ("[C@](C1CCC1=O)(C)(F)Cl",        ("R",), ("R",), "exocyclic-name", "cyclobutanone-yl C=O"),
    ("[C@](C1CCCCCC1=O)(C)(F)Cl",     ("R",), ("R",), "exocyclic-name", "cycloheptanone-yl C=O"),
    ("[C@](C1CCCCC1=C)(C)(F)Cl",      ("R",), ("R",), "exocyclic-name", "methylenecyclohexane exocyclic C=C (R33 exocyclic-defer, now NAMED)"),
    ("[C@](C1CCCCC1=CC)(C)(F)Cl",     ("R",), ("R",), "exocyclic-name", "ethylidenecyclohexane exocyclic C=C"),
    ("[C@](C1CCCCC1=N)(C)(F)Cl",      ("R",), ("R",), "exocyclic-name", "cyclohexanimine exocyclic C=N"),
    ("[C@](C1CCCCC1=S)(C)(F)Cl",      ("R",), ("R",), "exocyclic-name", "cyclohexanethione exocyclic C=S"),
    ("[C@](C1CCC(=O)CC1)(C)(F)Cl",    ("R",), ("R",), "exocyclic-name", "4-oxocyclohexyl (C=O away from attach)"),
    ("[C@](C1CCC(=O)O1)(C)(F)Cl",     ("R",), ("R",), "exocyclic-name", "gamma-butyrolactone-yl (exocyclic C=O, ring O)"),
    ("[C@](C1CCC(=O)N1)(C)(F)Cl",     ("R",), ("R",), "exocyclic-name", "lactam-yl (exocyclic C=O, ring N)"),
    ("O=C1CCCC1[C@](C)(F)Cl",         ("R",), ("R",), "exocyclic-name", "ring written before centre (spelling)"),
    ("[C@](C1CCCCC1=O)(CC)(O)N",      ("S",), ("S",), "exocyclic-name", "different spectators -> S"),
    ("[C@](C1CCCCC1=O)(C)(Cl)Br",     ("R",), ("R",), "exocyclic-name", "halogen spectators"),
    ("[C@](C1C(=O)CCCC1=O)(C)(F)Cl",  ("R",), ("R",), "exocyclic-multi-name", "ring 1,3-dione: TWO exocyclic C=O, all ring edges single"),
    ("[C@](C1CCC2(CCCC2=O)C1)(C)(F)Cl", ("R",), ("R",), "exocyclic-multi-name", "spiro skeleton, exocyclic C=O on the far ring"),
    ("[C@](C1CCCCC1=O)(C1CCCCC1)(F)Cl", ("R",), ("R",), "exocyclic-multi-name", "exocyclic-C=O ring vs saturated ring -> FIFO Rule 1a"),
    # --- ROUND 39: a conjugated ring (INTERNAL ring double) bearing an exocyclic terminal-CHALCOGEN carbonyl
    #     now NAMES -- the exocyclic-carbonyl carbon is a spectator, the ring releases on its unique acceptor
    #     matching, ordinary Rule 1a decides.  These two were R34 boundary-defers; R39 moved them (see
    #     cip_conjugated_carbonyl_probe.py). ---
    ("[C@](C1=CCCCC1=O)(C)(F)Cl",     ("R",), ("R",), "exocyclic-name", "cyclohexenone: internal ring C=C + exocyclic C=O -> NAMED (R39 conjugated-carbonyl release)"),
    ("[C@](C1C=CC(=O)C1)(C)(F)Cl",    ("R",), ("R",), "exocyclic-name", "cyclopentenone: internal ring C=C + exocyclic C=O -> NAMED (R39)"),
    # --- boundary DEFERRALS (rdkit names, we defer soundly): the R39 boundary -- a conjugated ring bearing an
    #     exocyclic =CH2/=NH (the aromatic-resonance-ambiguous non-benzenoid systems) or a CHARGED ring stay
    #     deferred (a wrong R/S is worse than an honest decline) ---
    ("[C@](C1=CCCCC1=C)(C)(F)Cl",     ("R",), (), "boundary-defer", "conjugated methylenecyclohexene: exocyclic =CH2 (aromatic-resonance) -> defer"),
    ("[C@](C1=CC=[NH+]C=C1)(C)(F)Cl", ("R",), (), "boundary-defer", "charged pyridinium ring (explicit Kekule) -> defer"),
)


def defers(lab) -> bool:
    return not lab or any(x in (None, "?", "") for x in (lab or ()))


def _sweep_names_only() -> dict:
    """RDKit-FREE reproduction of the OUR-SIDE sweep facts: how many exocyclic-ring stereocentres our namer names,
    all as real (R/S) labels.  Oracle AGREEMENT is checked live in ``_rdkit_cross_check``."""
    named = defrs = 0
    for frag, spec in itertools.product(_EXO_RINGS, _SPECTATORS):
        got = cip_labels(f"[C@]({frag})({spec})(F)Cl")
        if got and all(x in ("R", "S") for x in got):
            named += 1
        else:
            defrs += 1
    return {"named": named, "defers": defrs, "pairs": named + defrs}


def content_hash() -> str:
    payload = {
        "battery": [[smi, list(rd), list(exp), cat] for smi, rd, exp, cat, _n in BATTERY],
        "ours_live": [list(cip_labels(smi)) for smi, *_ in BATTERY],
        "sweep": _sweep_names_only(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate() -> None:
    """Raise if the shipped namer does not reproduce the oracle-verified finding (RDKit-free)."""
    counts = {"exocyclic-name": 0, "exocyclic-multi-name": 0, "boundary-defer": 0}
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        counts[category] += 1
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi}: {got} != rdkit {rd_label} [{note}]"
        else:
            assert defers(got), f"{smi} must DEFER [{note}]"
            assert rd_label, f"{smi} is only interesting if rdkit LABELS it [{note}]"
    assert counts["exocyclic-name"] >= 12, "must non-vacuously name the exocyclic-ring class"
    assert counts["exocyclic-multi-name"] >= 2, "must exercise multi-exocyclic (dione) + spiro skeletons"
    assert counts["boundary-defer"] >= 2, "must pin the unresolved conjugated-enone boundary"
    # ROUND 39 moved the conjugated exocyclic-CARBONYL boundary: a conjugated ring (internal ring double) bearing
    # an exocyclic C=O now NAMES; the remaining defer boundary is a conjugated exocyclic =CH2 (or a charged ring).
    assert cip_labels("[C@](C1=CCCCC1=O)(C)(F)Cl") == ("R",), "conjugated ring + exocyclic C=O now NAMES (R39)"
    assert cip_labels("[C@](C1=CCCCC1=C)(C)(F)Cl") == (), "conjugated ring + exocyclic =CH2 must still DEFER (R39 boundary)"
    # both the single-ring case and a Rule-1a-distinct ring pair NAME
    assert cip_labels("[C@](C1CCCCC1=O)(C)(F)Cl") == ("R",), "single exocyclic-ketone ring must NAME"
    assert cip_labels("[C@](C1CCCCC1=O)(C1CCCCC1)(F)Cl") == ("R",), "exocyclic ring pair must NAME"
    sweep = _sweep_names_only()
    assert sweep["named"] >= 120, f"exocyclic sweep should name a large population, got {sweep['named']}"


def _rdkit_cross_check() -> dict:
    """Re-verify the battery labels AND re-run the exocyclic sweep live against RDKit.  RAISES on any disagreement
    (the soundness bar: 0 mismatches).  Only where rdkit is installed (dev/probe env)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    def rd_label(smi):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            return None
        rdCIPLabeler.AssignCIPLabels(m)
        return tuple(sorted(a.GetProp("_CIPCode") for a in m.GetAtoms() if a.HasProp("_CIPCode")))

    for smi, rd_label_baked, _exp, _cat, note in BATTERY:
        live = rd_label(smi)
        assert live is not None and set(live) == set(rd_label_baked), f"baked rdkit label stale on {smi}: {live} vs {rd_label_baked} [{note}]"

    named = mismatches = deferred = 0
    for frag, spec in itertools.product(_EXO_RINGS, _SPECTATORS):
        smi = f"[C@]({frag})({spec})(F)Cl"
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
    assert mismatches == 0, f"SWEEP MISMATCH -- the fix mislabels ({mismatches})"
    return {"battery_verified": len(BATTERY), "exocyclic_named": named, "exocyclic_deferred": deferred,
            "mismatches": mismatches}


def report() -> dict:
    sweep = _sweep_names_only()
    return {
        "battery_size": len(BATTERY),
        "exocyclic_sweep_named": sweep["named"],
        "exocyclic_sweep_pairs": sweep["pairs"],
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
