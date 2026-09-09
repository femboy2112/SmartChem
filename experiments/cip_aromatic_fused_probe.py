"""CIP-AROMATIC-FUSED-01: ROUND 34 item 4 -- an aromatic ring FUSED to a saturated ring now NAMES.

R33 released LOCALIZED (unique-Kekule) rings and, to reach them, admitted a saturated sp3 ring carbon as a
matching SPECTATOR.  It then DEFERRED the ``matching_count >= 2 WITH a spectator`` case -- a DELOCALIZED ring
FUSED to a saturated ring (indane, tetralin) -- pending validation ("extending the averaging claim to this mixed
topology is unproven").

THE FIX (R34 item 4): that case is NOT new machinery.  The pi-ACCEPTORS (the aromatic ring carbons / pyridine N
that take a ring double) get the SAME exact partner-Z averaging R22 validated for benzene/pyridine/naphthalene;
the sp3 SPECTATOR carbons are not acceptors, never enter ``partners``, and keep their REAL integer Z in the
ordinary digraph.  So an aromatic-fused-to-saturated ring resolves as ``benzene averaged`` + ``saturated ring
released`` -- exactly as a standalone benzene and a standalone saturated ring already do.  ``_cip_mancude``'s
three-way collapses to: matching_count==1 -> release; matching_count>=2 -> average (spectator or not).

Consumer (recon, 2026-09-08, rdkit 2026.3.6): indane/tetralin/benzosuberane and their hetero- and PAH-fused
homologues.  ``validate()``/``content_hash()`` are RDKit-FREE; ``_rdkit_cross_check()`` re-runs the sweep live.
SOUNDNESS BAR: where both label, they MATCH; we may DEFER where RDKit names; we NEVER name where RDKit defers.
Re-run ``python -m experiments.cip_aromatic_fused_probe`` after an INTENTIONAL change and set ``FROZEN_HASH``.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from smartchem.smiles import cip_labels

FROZEN_HASH = "5ed0abb10497a71466182261ba8b07a9da391cbf9fd16d223971f0f7a4a443ea"

#: Aromatic ring fused to a saturated ring (attach at the first, saturated ring atom): benzo-fused carbocycles,
#: aza/oxa/thia-fused, naphthalene-fused, explicit-Kekule benzo-fused.
_FUSED = ("C1Cc2ccccc2C1", "C1CCc2ccccc2C1", "C1Cc2ccccc2CC1", "C1CCc2ccccc21", "C1Cc2ccccc21",
          "C1CCc2ccccc2CC1", "C1Cc2ccccc2CCC1", "C1Cc2ccncc2C1", "C1Cc2cccnc2C1", "C1CCc2ncccc2C1",
          "C1Cc2ccc3ccccc3c2C1", "C1Cc2ccoc2C1", "C1Cc2ccsc2C1", "C1CC2=CC=CC=C2C1", "C1CCC2=CC=CC=C2C1")
_SPECTATORS = ("C", "CC", "CCC", "C(C)C", "CO", "O", "N", "S", "F", "Cl")

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).
#:   fused-name | boundary-defer
BATTERY = (
    ("[C@](C1Cc2ccccc2C1)(C)(F)Cl",      ("R",), ("R",), "fused-name", "indane-2-yl (R33 fused-arom-defer, now NAMED)"),
    ("[C@](C1CCc2ccccc2C1)(C)(F)Cl",     ("R",), ("R",), "fused-name", "tetralin"),
    ("[C@](C1Cc2ccccc2CC1)(C)(F)Cl",     ("R",), ("R",), "fused-name", "benzosuberane-ish"),
    ("[C@](C1CCc2ccccc21)(C)(F)Cl",      ("R",), ("R",), "fused-name", "indan-1-yl fused directly"),
    ("[C@](C1Cc2ccccc21)(C)(F)Cl",       ("R",), ("R",), "fused-name", "indene-saturated fused"),
    ("[C@](C1Cc2ccncc2C1)(C)(F)Cl",      ("R",), ("R",), "fused-name", "aza-fused (pyridine-fused saturated)"),
    ("[C@](C1Cc2ccc3ccccc3c2C1)(C)(F)Cl", ("R",), ("R",), "fused-name", "naphthalene-fused saturated"),
    ("[C@](C1Cc2ccoc2C1)(C)(F)Cl",       ("R",), ("R",), "fused-name", "furan-fused saturated"),
    ("[C@](C1CC2=CC=CC=C2C1)(C)(F)Cl",   ("R",), ("R",), "fused-name", "explicit-Kekule benzo-fused"),
    ("[C@](C1Cc2ccc(F)cc2C1)(C)(F)Cl",   ("R",), ("R",), "fused-name", "substituted aromatic ring"),
    ("[C@](C1CCc2ccccc2C1)(CC)(O)N",     ("S",), ("S",), "fused-name", "tetralin, different spectators -> S"),
    # --- boundary DEFERRALS (RDKit also defers: a false centre or unsupported PAH) ---
    ("[C@](C1Cc2ccccc2C1)(C1Cc2ccccc2C1)(F)Cl", (), (), "boundary-defer", "identical indanyl ligands: false centre"),
    ("[C@](C1CCc2ccc3ccccc3c2C1)(C)F", (), (), "boundary-defer", "partially-hydrogenated phenanthrene (both defer)"),
)


def defers(lab) -> bool:
    return not lab or any(x in (None, "?", "") for x in (lab or ()))


def _sweep_names_only() -> dict:
    named = defrs = 0
    for frag, spec in itertools.product(_FUSED, _SPECTATORS):
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
    counts = {"fused-name": 0, "boundary-defer": 0}
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        counts[category] += 1
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi}: {got} != rdkit {rd_label} [{note}]"
        else:
            assert defers(got), f"{smi} must DEFER [{note}]"
    assert counts["fused-name"] >= 9, "must non-vacuously name the aromatic-fused class"
    assert counts["boundary-defer"] >= 2, "must pin the false-centre / ambiguous-PAH boundary"
    # indane/tetralin NAME; the benzene mancude path is unchanged; a partially-hydrogenated PAH still defers
    assert cip_labels("[C@](C1Cc2ccccc2C1)(C)(F)Cl") == ("R",), "indane must NAME"
    assert cip_labels("[C@](c1ccccc1)(C)(F)Cl") == ("R",), "standalone benzene mancude unchanged"
    sweep = _sweep_names_only()
    assert sweep["named"] >= 110, f"fused sweep should name a large population, got {sweep['named']}"


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

    for smi, rd_label_baked, _exp, _cat, note in BATTERY:
        live = rd_label(smi)
        if defers(rd_label_baked):
            continue                                             # boundary-defer: rdkit may or may not label; not pinned
        assert live is not None and set(live) == set(rd_label_baked), f"baked rdkit label stale on {smi}: {live} vs {rd_label_baked} [{note}]"

    named = mismatches = deferred = 0
    for frag, spec in itertools.product(_FUSED, _SPECTATORS):
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
    return {"battery_verified": len(BATTERY), "fused_named": named, "fused_deferred": deferred, "mismatches": mismatches}


def report() -> dict:
    sweep = _sweep_names_only()
    return {
        "battery_size": len(BATTERY),
        "fused_sweep_named": sweep["named"],
        "fused_sweep_pairs": sweep["pairs"],
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
