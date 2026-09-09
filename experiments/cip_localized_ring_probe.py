"""CIP-LOCALIZED-RING-01: ROUND 33 -- localized unsaturated-ring substituents now NAME.

R32 (``cip_rule1b_consumer_probe.py``) proved Rule 1b has no in-scope consumer and surfaced the REAL next CIP
gap: an off-ring stereocentre bearing a substituent ring that carries a double bond DEFERRED even where Rule 1a
trivially decided (isolation: ``[C@](C1CC1)(C)(F)Cl`` named, ``[C@](C1=CC1)(C)(F)Cl`` deferred).  Root cause:
``_cip_mancude`` blocked the WHOLE unsaturated ring component as a Kekule-dependent boundary whenever any ring
atom fit no pi-acceptor/donor pattern (e.g. an sp3 CH2 in cyclopropene).

THE FIX (R33): a LOCALIZED unsaturated ring -- one whose double-bond positions are FORCED (its acceptor set has
a UNIQUE perfect matching == a single valid Kekule structure) -- is released to the ordinary ``_cip_digraph``
with REAL atomic number and REAL mass, exactly as an ACYCLIC double bond is handled.  Two additions to
``_cip_mancude``: (a) admit a saturated sp3 ring carbon (all bonds order 1) as a pass-through spectator so a
partially-unsaturated ring reaches the matching enumeration; (b) release matching_count==1 with real z/mass.
R33 originally deferred matching_count>=2 with a spectator; R34 item 4 validated and admitted that fused class,
while clean benzene/pyridine averaging remains byte-identical. One soundness gate remains after ROUND 34:
  * the Rule-1b gate (dalembert): Rule 2 may break a Rule-1a tie only when both tied ligands are TREES; a ring
    closure means Rule 1b (unbuilt) territory -> DEFER (R32 proved 1b inert only on trees).

The original released-ring/mancude-cross guard is superseded by ROUND 34's FIFO Rule-1a correction: its reported
ring-vs-ring mislabels came from exhausting the highest branch recursively, not from the ring representation.
Rule-1a-distinct localized-vs-localized and localized-vs-mancude pairs now NAME and match the oracle.

This harness pins the finding, per "experiments are committed", and doubles as a DIFFERENTIAL VALIDATION of the
shipped namer against RDKit ``rdCIPLabeler`` (installed dev-venv-only as a probe oracle; ABSENT from the runtime
and committed suite -- the labels are baked as frozen constants verified at authoring, 2026-09-08, rdkit
2026.3.6).  ``validate()`` and ``content_hash()`` are RDKit-FREE; ``_rdkit_cross_check()`` re-runs the sweep live
when rdkit is present and SKIPS otherwise (the ``cip_geometry_oracle`` pattern).

SOUNDNESS BAR (verified by the sweep): for every molecule where BOTH we and RDKit assign a label they MATCH;
we may DEFER where RDKit names (sound incompleteness); we NEVER name where RDKit defers, and never disagree.

Deterministic, tamper-pinned: re-run ``python -m experiments.cip_localized_ring_probe`` after an INTENTIONAL
change and set ``FROZEN_HASH`` to the printed value; drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from smartchem.smiles import cip_labels

#: The committed tamper pin.  Regenerate ONLY on an intentional change.
FROZEN_HASH = "b508ae80028faed55942ad44a0141b48e534402b4271b5d95a0c890e953281dd"

# --- committed sweep generator (reproducible; the counts below are what THIS produces) ---

#: Localized unsaturated ring substituents (single ring double, multiple localized doubles, sp2/sp3 attach,
#: hetero enol-ether/enamine, a localized fused bicyclic) -- every one a UNIQUE Kekule structure.
_LOCALIZED_FRAGS = ("C1=CC1", "C1=CCC1", "C1=CCCC1", "C1=CCCCC1", "C1CC=C1", "C1CCC=C1", "C1CCCC=C1",
                    "C1CC=CC1", "C1C=CC=C1", "C1=CC=CC1", "C1=CC=CCC1", "C1=CCC=CC1", "C1=CC=CC=CC1",
                    "C1=CCO1", "C1CC=CO1", "C1CCC=CO1", "C1=CCN1", "C1CC=CN1", "C1=CCS1",
                    "C1=CCC2CCCCC12", "C1CC2CC1C=C2")
#: Aromatic heterocycles that are UNIQUE-matching (rerouted from mass=None to real mass) + benzene (unchanged).
_REROUTE_FRAGS = ("c1ccoc1", "c1ccsc1", "c1cc[nH]c1")
#: ACYCLIC spectator co-ligands for the cited-gap shape.
_SPECTATORS = ("C", "CC", "CCC", "C(C)C", "CO", "C=C", "O", "N")

#: Frozen sweep facts (reproduced live by ``_rdkit_cross_check`` when rdkit is present).
LOCALIZED_NAMES = None            # (smi, ours) pairs where a localized/reroute ring NAMES and MATCHES rdkit
LOCALIZED_TESTED = None
SWEEP_MISMATCHES = 0              # the soundness bar: 0 disagreements over the whole sweep

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).  Categories:
#:   localized-name | reroute-name | mancude-name | isolation-sat-name |
#:   multiring-name | isotope-ring-defer | ring-centre-defer
BATTERY = (
    # --- localized rings: NAME (match rdkit) -- the R32 gap, now closed ---
    ("[C@](C1=CC1)(C)(F)Cl",         ("R",), ("R",), "localized-name", "cyclopropenyl @sp2 (the R32 isolation)"),
    ("[C@](C1=CCC1)(C)(F)Cl",        ("R",), ("R",), "localized-name", "cyclobutenyl @sp2"),
    ("[C@](C1=CCCC1)(C)(F)Cl",       ("R",), ("R",), "localized-name", "cyclopentenyl @sp2"),
    ("[C@](C1=CCCCC1)(C)(F)Cl",      ("R",), ("R",), "localized-name", "cyclohexenyl @sp2"),
    ("[C@](C1CC=CC1)(C)(F)Cl",       ("R",), ("R",), "localized-name", "cyclopentene @sp3 attach"),
    ("[C@](C1C=CC=C1)(C)(F)Cl",      ("R",), ("R",), "localized-name", "cyclopentadiene @sp3"),
    ("[C@](C1=CC=CCC1)(C)(F)Cl",     ("R",), ("R",), "localized-name", "1,3-cyclohexadienyl"),
    ("[C@](C1=CCC=CC1)(C)(F)Cl",     ("R",), ("R",), "localized-name", "1,4-cyclohexadienyl"),
    ("[C@](C1=CC=CC=CC1)(C)(F)Cl",   ("R",), ("R",), "localized-name", "cycloheptatrienyl (localized)"),
    ("[C@](C1=CCC2CCCCC12)(C)(F)Cl", ("R",), ("R",), "localized-name", "fused hydrindane-ene (birdperson guard 5)"),
    ("[C@](C1CC2CC1C=C2)(C)(F)Cl",   ("R",), ("R",), "localized-name", "bridged norbornene-like"),
    ("[C@](C1=CCO1)(C)(F)Cl",        ("R",), ("R",), "localized-name", "2H-oxete (cyclic enol ether)"),
    ("[C@](C1CC=CO1)(C)(F)Cl",       ("R",), ("R",), "localized-name", "2,3-dihydrofuran"),
    ("[C@](C1CCC=CO1)(C)(F)Cl",      ("R",), ("R",), "localized-name", "3,4-dihydro-2H-pyran"),
    ("[C@](C1=CCN1)(C)(F)Cl",        ("R",), ("R",), "localized-name", "dihydroazole"),
    # --- aromatic-heterocycle reroute: NAME (unique Kekule -> real mass; Rule 1a byte-identical) ---
    ("[C@](c1ccoc1)(C)(F)Cl",        ("R",), ("R",), "reroute-name", "2-furyl (unique matching -> real mass)"),
    ("[C@](c1ccsc1)(C)(F)Cl",        ("R",), ("R",), "reroute-name", "2-thienyl"),
    ("[C@](c1cc[nH]c1)(C)(F)Cl",     ("R",), ("R",), "reroute-name", "2-pyrrolyl"),
    # --- mancude benzene: unchanged averaging path, still NAMES (byte-identical) ---
    ("[C@](c1ccccc1)(C)(F)Cl",       ("R",), ("R",), "mancude-name", "phenyl (mancude averaging, unchanged)"),
    ("O[C@H](c1ccccc1)c1ccccn1",     ("R",), ("R",), "mancude-name", "phenyl vs pyridyl (R22 mancude, unchanged)"),
    # --- THE ISOLATION: saturated ring names (since R20); the SAME ring + a double bond ALSO names now (R33) ---
    ("[C@](C1CC1)(C)(F)Cl",          ("R",), ("R",), "isolation-sat-name", "saturated cyclopropyl"),
    # --- boundary DEFERRALS (rdkit names, we defer soundly -- the characterised next gaps) ---
    # (the EXOCYCLIC boundary R33 recorded here was CLOSED by ROUND 34 item 2 -- see tests/test_cip_exocyclic_ring.py;
    #  the AROMATIC-FUSED-to-saturated boundary was CLOSED by ROUND 34 item 4 -- see tests/test_cip_aromatic_fused.py.)
    # ROUND 34 FIFO correction: Rule-1a-distinct ring pairs now NAME (the former guard was masking traversal bugs).
    ("[C@](C1=CCCCC1)(C1=CCCC1)(C)F",     ("S",), ("S",), "multiring-name", "two localized rings"),
    ("[C@](C1=CCC1)(C1=CC1)(C)F",         ("S",), ("S",), "multiring-name", "two localized rings"),
    ("[C@](C1=CC=CC=CC1)(c1ccccc1)(F)Cl", ("S",), ("S",), "multiring-name", "localized vs mancude aromatic"),
    ("[C@](C1=CCCCC1)(c1ccccc1)(F)Cl",    ("S",), ("S",), "multiring-name", "cyclohexenyl vs phenyl"),
    ("[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl", ("R",), (), "isotope-ring-defer", "13C ring tie -> Rule-1b territory (gated)"),
    ("N[C@]1(F)CCCCO1",              ("R",), (), "ring-centre-defer", "ring stereocentre (out of scope, _on_cycle)"),
)


def content_hash() -> str:
    payload = {
        "battery": [[smi, list(rd), list(exp), cat] for smi, rd, exp, cat, _n in BATTERY],
        "ours_live": [list(cip_labels(smi)) for smi, *_ in BATTERY],
        "sweep": _localized_sweep_names_only(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _localized_sweep_names_only() -> dict:
    """RDKit-FREE reproduction of the sweep's OUR-SIDE facts: how many localized/reroute ring stereocentres our
    namer names, and that every one is a real (R/S) label.  (The oracle AGREEMENT is checked live in
    ``_rdkit_cross_check``; here we pin only what needs no oracle.)"""
    named = defers = 0
    for frag, spec in itertools.product(_LOCALIZED_FRAGS + _REROUTE_FRAGS, _SPECTATORS):
        got = cip_labels(f"[C@]({frag})({spec})(F)Cl")
        if got and all(x in ("R", "S") for x in got):
            named += 1
        else:
            defers += 1
    return {"named": named, "defers": defers, "pairs": named + defers}


def defers(lab) -> bool:
    return not lab or any(x in (None, "?", "") for x in (lab or ()))


def validate() -> None:
    """Raise if the shipped namer does not reproduce the oracle-verified finding (RDKit-free)."""
    counts = {"localized-name": 0, "reroute-name": 0, "mancude-name": 0, "isolation-sat-name": 0,
              "multiring-name": 0, "isotope-ring-defer": 0, "ring-centre-defer": 0}
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        counts[category] += 1
        if category.endswith("-name"):
            assert got == rd_label, f"MISLABEL vs oracle on {smi}: {got} != rdkit {rd_label} [{note}]"
        else:                                                    # a *-defer category
            assert defers(got), f"{smi} must DEFER [{note}]"
            assert rd_label, f"{smi} is only interesting if rdkit LABELS it [{note}]"

    # non-vacuity: every regime is genuinely exercised
    assert counts["localized-name"] >= 10, "must non-vacuously name the localized-ring class"
    assert counts["reroute-name"] >= 3, "must exercise the aromatic-heterocycle reroute"
    assert counts["multiring-name"] >= 3, "must pin the corrected Rule-1a-distinct ring-vs-ring path"
    assert counts["isotope-ring-defer"] >= 1, "must pin the Rule-1b (isotope-on-ring) gate"

    # THE ISOLATION (R32 -> R33): the saturated ring named; the SAME ring + a double bond now ALSO names (gap closed).
    assert cip_labels("[C@](C1CC1)(C)(F)Cl") == ("R",), "saturated cyclopropyl must NAME"
    assert cip_labels("[C@](C1=CC1)(C)(F)Cl") == ("R",), "localized cyclopropenyl must NAME (R33 closed the R32 gap)"

    # The Rule-1a-distinct ring comparison names; the Rule-1b boundary still fails closed.
    assert cip_labels("[C@](C1=CCCCC1)(c1ccccc1)(F)Cl") == ("S",)
    assert cip_labels("[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl") == (), "isotope-on-ring Rule-1a tie must DEFER (Rule-1b territory)"

    # the localized-ring sweep names a non-trivial population, all as real labels.
    sweep = _localized_sweep_names_only()
    assert sweep["named"] >= 150, f"localized sweep should name a large population, got {sweep['named']}"


def _rdkit_cross_check() -> dict:
    """Re-verify the battery labels AND re-run the localized sweep live against RDKit.  RAISES on any
    disagreement (the soundness bar: 0 mismatches).  Only where rdkit is installed (dev/probe env)."""
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
    for frag, spec in itertools.product(_LOCALIZED_FRAGS + _REROUTE_FRAGS, _SPECTATORS):
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
    return {"battery_verified": len(BATTERY), "localized_named": named, "localized_deferred": deferred,
            "mismatches": mismatches}


def report() -> dict:
    sweep = _localized_sweep_names_only()
    return {
        "battery_size": len(BATTERY),
        "localized_sweep_named": sweep["named"],
        "localized_sweep_pairs": sweep["pairs"],
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
