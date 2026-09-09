"""CIP-RING-VS-RING-01: ROUND 34 item 5 -- ring-vs-ring + isotope-on-ring is a VERIFIED DEFER.

R33 released LOCALIZED rings and R34 items 2/4 released EXOCYCLIC and mixed AROMATIC-FUSED rings.  Each NAMES
soundly as the ONLY ring on a centre.  This item asked whether an off-ring stereocentre bearing TWO rings can be
named.  Answer, oracle-verified: NO -- not soundly, not yet.  A ring-vs-ring comparison forces the CIP digraph to
DESCEND into two competing ring-closure/double-bond structures, and there our Rule-1a(+2) digraph resolves the
order DIFFERENTLY from the RDKit ``rdCIPLabeler`` oracle for SAME-KIND unsaturated pairs (cyclohexenyl vs
cyclopentenyl; a ring ketone vs another ring ketone; indane vs tetralin).  This is Rule-1b territory (R32: Rule 1b
bites with ring closures -- two rings can tie under Rule 1a while being constitutionally distinct), which is
UNBUILT.  So the ``_CIP_RING_VS_RING_GUARD`` fails such a centre CLOSED (a NAMED deferral; a wrong R/S is worse
than none) -- the R32 discipline: proven-cannot-build-soundly-yet is a verified defer, WITH the evidence committed.

THE FINDING (this harness pins it, RDKit-free where it can, live-oracle where it must):
  * SOUND & NAMED (the guard is TARGETED, not a blanket ring-vs-ring veto): two SATURATED rings NAME; a SINGLE
    ring of any released/mancude kind NAMES; PURE mancude-vs-mancude (benzene/pyridyl, no spectator) ranks
    soundly (R22) -- all match the oracle.
  * VERIFIED DEFER (the guard is LOAD-BEARING): every released/fused ring vs ANOTHER ring, and every
    isotope-on-a-ring Rule-1a tie, DEFERS -- we NEVER mislabel, though RDKit names them.
  * THE PROOF the guard is necessary: ``guard_off_mislabels()`` flips ``_CIP_RING_VS_RING_GUARD`` off, re-runs the
    ring-vs-ring sweep, and shows the SAME-KIND unsaturated pairs then MISLABEL vs the oracle (non-zero).  With the
    guard ON that count is 0.  (Restores the flag; production keeps it True.)

UNLOCK (the real next consumer): a Rule-1b constitutional comparator (rank two Rule-1a-tied ring ligands by
constitution), OR a verified ring-closure/double-bond digraph representation that matches the oracle on deep
ring-descent.  Either would let ring-vs-ring NAME; neither is this round's build.

RDKit ``rdCIPLabeler`` is a dev-venv-only oracle (ABSENT from runtime + committed suite).  ``validate()`` /
``content_hash()`` are RDKit-FREE; ``_rdkit_cross_check()`` runs the live differential + the guard-off proof.
Re-run ``python -m experiments.cip_ring_vs_ring_probe`` after an INTENTIONAL change and set ``FROZEN_HASH``.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from smartchem import smiles
from smartchem.smiles import cip_labels

FROZEN_HASH = "c1e4b469f913b726410ad7fdfb9ca5927c19a5d6a215e036d3bdbb20d2ebfef0"

#: Ring fragments by KIND (attach at first ring atom).
_SAT = ("C1CC1", "C1CCC1", "C1CCCC1", "C1CCCCC1", "C1CCCCCC1")
_LOC = ("C1=CC1", "C1=CCC1", "C1=CCCC1", "C1=CCCCC1")
_EXO = ("C1CCCC1=O", "C1CCCCC1=O", "C1CCCCC1=C")
_ARO = ("c1ccccc1", "c1ccncc1", "c1ccoc1")
_FUSED = ("C1Cc2ccccc2C1", "C1CCc2ccccc2C1")

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).
#:   sound-name (guard targeted) | ringring-defer (guard load-bearing) | isotope-ring-defer
BATTERY = (
    # SOUND & NAMED -- the guard does NOT over-defer these:
    ("[C@](C1CCCCC1)(C1CCCC1)(C)F",       ("R",), ("R",), "sound-name", "two SATURATED rings (never released) -> NAME"),
    ("[C@](C1CCCCC1)(C1CCCCCC1)(C)F",     ("S",), ("S",), "sound-name", "cyclohexyl vs cycloheptyl (Rule-1a distinct saturated)"),
    ("[C@](c1ccccc1)(c1ccncc1)(C)O",      ("S",), ("S",), "sound-name", "phenyl vs pyridyl (pure mancude, R22) -> NAME"),
    ("[C@](C1CCCCC1=O)(C)(F)Cl",          ("R",), ("R",), "sound-name", "SINGLE exocyclic ring + acyclic co-ligands -> NAME"),
    ("[C@](C1Cc2ccccc2C1)(C)(F)Cl",       ("R",), ("R",), "sound-name", "SINGLE fused ring + acyclic co-ligands -> NAME"),
    # VERIFIED DEFER -- the guard fails these CLOSED (rdkit names; we never mislabel):
    ("[C@](C1=CCCCC1)(C1=CCCC1)(C)F",     ("S",), (), "ringring-defer", "two localized rings (cyclohexenyl vs cyclopentenyl)"),
    ("[C@](C1=CC1)(C1=CCC1)(C)F",         ("R",), (), "ringring-defer", "cyclopropenyl vs cyclobutenyl (guard-off mislabels)"),
    ("[C@](C1CCCC1=O)(C1CCCCC1=O)(C)F",   ("R",), (), "ringring-defer", "two exocyclic ketone rings"),
    ("[C@](C1Cc2ccccc2C1)(C1CCc2ccccc2C1)(C)F", ("R",), (), "ringring-defer", "indane vs tetralin (fused vs fused)"),
    ("[C@](C1=CCCCC1)(c1ccccc1)(F)Cl",    ("S",), (), "ringring-defer", "released localized ring vs mancude aromatic"),
    ("[C@](C1Cc2ccccc2C1)(C1=CCCCC1)(C)F", ("S",), (), "ringring-defer", "fused ring vs localized ring"),
    ("[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl", ("R",), (), "isotope-ring-defer", "13C-labelled cyclohexyl vs cyclohexyl (Rule-1b territory)"),
    ("[C@]([13CH]1CCCC1)(C1CCCC1)(F)Cl",  ("R",), (), "isotope-ring-defer", "13C cyclopentyl tie"),
)


def defers(lab) -> bool:
    return not lab or any(x in (None, "?", "") for x in (lab or ()))


def _sound_named_sweep() -> dict:
    """RDKit-FREE: how many SOUND ring-pair centres our namer names (two saturated rings; pure mancude-vs-mancude),
    all as real labels -- proving the guard is TARGETED, not a blanket ring-vs-ring veto."""
    named = defrs = 0
    for r1, r2 in itertools.chain(itertools.combinations(_SAT, 2), itertools.combinations(_ARO, 2)):
        got = cip_labels(f"[C@]({r1})({r2})(C)F")
        if got and all(x in ("R", "S") for x in got):
            named += 1
        else:
            defrs += 1
    return {"named": named, "defers": defrs}


def _ringring_defers_sweep() -> int:
    """RDKit-FREE: the count of released/fused ring-vs-ring centres that DEFER under the guard (must be all of them
    -- the guard fires; we never mislabel)."""
    defrd = 0
    total = 0
    for kind in (_LOC, _EXO, _FUSED):
        for r1, r2 in itertools.combinations_with_replacement(kind, 2):
            total += 1
            if defers(cip_labels(f"[C@]({r1})({r2})(C)F")):
                defrd += 1
    return defrd == total and total > 0


def content_hash() -> str:
    payload = {
        "battery": [[smi, list(rd), list(exp), cat] for smi, rd, exp, cat, _n in BATTERY],
        "ours_live": [list(cip_labels(smi)) for smi, *_ in BATTERY],
        "sound_sweep": _sound_named_sweep(),
        "ringring_all_defer": _ringring_defers_sweep(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def guard_off_mislabels() -> int:
    """Flip ``_CIP_RING_VS_RING_GUARD`` OFF, re-run the same-kind unsaturated ring-vs-ring sweep against RDKit, count
    mislabels, RESTORE the flag.  This is the LIVE proof the guard is load-bearing (guard-off count > 0; guard-on 0).
    Requires rdkit; raises ImportError otherwise (the caller skips)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    def rd_label(smi):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            return None
        rdCIPLabeler.AssignCIPLabels(m)
        return tuple(sorted(a.GetProp("_CIPCode") for a in m.GetAtoms() if a.HasProp("_CIPCode")))

    saved = smiles._CIP_RING_VS_RING_GUARD
    mism = 0
    try:
        smiles._CIP_RING_VS_RING_GUARD = False
        for kind in (_LOC, _EXO, _FUSED):
            for r1, r2 in itertools.combinations_with_replacement(kind, 2):
                smi = f"[C@]({r1})({r2})(C)F"
                ours = cip_labels(smi)
                rl = rd_label(smi)
                if ours and rl and not defers(rl) and set(ours) != set(rl):
                    mism += 1
    finally:
        smiles._CIP_RING_VS_RING_GUARD = saved
    return mism


def validate() -> None:
    """RDKit-free: the shipped namer reproduces the finding -- sound cases NAME, ring-vs-ring/isotope DEFER."""
    assert smiles._CIP_RING_VS_RING_GUARD is True, "the ring-vs-ring guard must ship ON"
    counts = {"sound-name": 0, "ringring-defer": 0, "isotope-ring-defer": 0}
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        counts[category] += 1
        if category == "sound-name":
            assert got == rd_label, f"MISLABEL vs oracle on {smi} [{note}]"
        else:
            assert defers(got), f"{smi} must DEFER (guard load-bearing) [{note}]"
            assert rd_label, f"{smi} is only interesting if rdkit LABELS it [{note}]"
    assert counts["sound-name"] >= 5, "must show the guard is TARGETED (sound ring pairs still name)"
    assert counts["ringring-defer"] >= 4, "must pin the ring-vs-ring verified defer"
    assert counts["isotope-ring-defer"] >= 2, "must pin the isotope-on-ring (Rule-1b) defer"
    assert _ringring_defers_sweep(), "every released/fused ring-vs-ring centre must DEFER under the guard"
    sound = _sound_named_sweep()
    assert sound["named"] >= 10, f"sound ring pairs must name a non-trivial population, got {sound['named']}"


def _rdkit_cross_check() -> dict:
    """Live differential: (a) the sound-name battery matches the oracle; (b) NO ring-vs-ring case we name mislabels
    (guard ON -> 0); (c) the guard-off PROOF: relaxing the guard reintroduces mislabels (> 0)."""
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
        if cat == "sound-name":
            live = rd_label(smi)
            assert live is not None and set(live) == set(rd_baked), f"baked rdkit label stale on {smi}: {live} [{note}]"

    guard_on_mism = 0
    for kind in (_SAT, _LOC, _EXO, _ARO, _FUSED):
        for r1, r2 in itertools.combinations_with_replacement(kind, 2):
            smi = f"[C@]({r1})({r2})(C)F"
            ours = cip_labels(smi)
            rl = rd_label(smi)
            if ours and rl and not defers(rl) and set(ours) != set(rl):
                guard_on_mism += 1
    assert guard_on_mism == 0, f"GUARD ON must never mislabel ring-vs-ring, got {guard_on_mism}"
    guard_off_mism = guard_off_mislabels()
    assert guard_off_mism > 0, "the guard must be LOAD-BEARING: relaxing it must reintroduce mislabels"
    return {"battery_verified": len(BATTERY), "guard_on_mislabels": guard_on_mism,
            "guard_off_mislabels": guard_off_mism}


def report() -> dict:
    return {
        "battery_size": len(BATTERY),
        "sound_named_sweep": _sound_named_sweep(),
        "ringring_all_defer": _ringring_defers_sweep(),
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
