"""CIP-RULE1B-CONSUMER-01: the oracle-verified investigation behind ROUND 32's Rule-1b VERIFIED DEFER.

Rule 1b (Rung 2) ranks the CIP digraph's DUPLICATE atoms by the hierarchical rank of the node each represents.
R28 deferred it on a soundness asymmetry (a computed-rank pre-pass MISLABELS rather than defers, so it needs a
real decisive molecule + an EXTERNAL oracle before it can be built).  This harness records the investigation's
finding and, per "experiments are committed", pins it as reproducible evidence -- doubling as a permanent
DIFFERENTIAL VALIDATION of the shipped Rule-1a+2 namer against the accurate RDKit ``rdCIPLabeler`` (the opposite
of a self-mirror: live shipped code checked against an independent oracle).

THE FINDING (see docs/research/CIP_RULE1B_CONSUMER_SCOPE_DECISION_v0.1.md): Rule 1b has NO demonstrated consumer
anywhere in the namer's scope.

  * ACYCLIC centres (tree digraphs): a double-bond duplicate represents a DIRECT neighbour already compared at
    Rule 1a, so acyclic Rule 1b is subsumed by Rule 1a (Rule 1b bites only with ring closures -- Hanson 2018).
    The committed acyclic sweep finds 0 cases where RDKit labels and we defer over 992 stereocentres.
  * RING-SUBSTITUENT, off-ring centres (NON-tree digraphs -- the class a first pass missed, birdperson): a first
    pass found 24/60 deferrals where RDKit labels, ALL triggered by ring UNSATURATION and Rule-1a-DISTINCT (NOT a
    Rule-1b tie).  ROUND 33 CLOSED that gap: a LOCALIZED unsaturated ring (unique Kekule) now NAMES, so 12/60
    remain -- and those are RING-vs-RING (a released localized ring ranked against ANOTHER ring), a Rule-1b /
    clean-mancude territory soundly deferred by R33's multiring guard, still NOT the acyclic Rule-1b tie this
    harness rules out.  See ``experiments/cip_localized_ring_probe.py`` for the R33 evidence.
  * RING-ON-CENTRE: filtered out of scope by ``_on_cycle`` before CIP ranking; RDKit labels, we defer (scope).

Therefore building the acyclic ``dup_rank`` machinery would be dead structure + mislabel-prone: DEFER.  ROUND 33
addressed the ring gap this harness surfaced (localized-ring substituents), NOT by building Rule 1b.

Each battery entry's RDKit label is baked as a frozen constant, VERIFIED against ``rdCIPLabeler`` at authoring
(2026-09-08, rdkit 2026.3.6).  ``validate()`` and ``content_hash()`` are RDKit-FREE (the committed test
environment has no rdkit); ``_rdkit_cross_check()`` re-runs the two committed sweeps + battery live when rdkit is
present and SKIPS otherwise (the ``cip_geometry_oracle`` pattern).

Deterministic, tamper-pinned: re-run ``python -m experiments.cip_rule1b_consumer_probe`` after an INTENTIONAL
change and set ``FROZEN_HASH`` to the printed value; drift reddens ``report()['hash_matches']``.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from smartchem.smiles import _cip_compare, _cip_mass, cip_labels

#: Elements that form multiple bonds and so appear as DUPLICATE atoms in the CIP digraph.  The acyclic
#: soundness of the Rule-1b defer rests on one invariant (dalembert): a duplicate leaf ``(z, mass, ())`` is
#: always Rule-1a-separated from a REAL same-Z atom, because a real C/N/O/S node always carries a Z>=1 child
#: (an H from valence-filling, or its own duplicate-back atom) while a duplicate leaf carries only phantom-0
#: children.  If a future edit made H-filling conditional or gave a duplicate a non-empty child, a real node
#: could collide with a duplicate and re-open the acyclic Rule-1b gap -- so this crux is pinned below.
_DUPLICATE_CAPABLE = ("C", "N", "O", "S")

#: The committed tamper pin.  Regenerate ONLY on an intentional change.
FROZEN_HASH = "2d4e1fd0c07ca7679f1cb01dc0da76b52697df0e5f640108ec1088b63b5097ec"

# --- committed sweep generators (reproducible; the counts below are what THESE produce, not orphaned numbers) ---

#: Acyclic ligand fragments for the tree-digraph sweep (single/double/triple bonds; C/N/O/S).
_ACYCLIC_FRAGS = ("C", "CC", "CCC", "C(C)C", "CCCC", "C=C", "C=CC", "CC=C", "C(=C)C", "C=C(C)C", "C#C", "C#CC",
                  "CO", "CCO", "C=CO", "OCC", "CN", "CCN", "C=CN", "CS", "C=O", "CC=O", "C(=O)C", "OC=O", "C=N",
                  "CC=N", "C(C)=CC", "CC(C)=C", "C=CCC", "CCC=C", "C(=O)O", "C(=O)N")
#: Ring substituents (saturated + unsaturated) and the other ligand, for the non-tree sweep.
_RING_FRAGS = ("C1CC1", "C1CCC1", "C1CCCC1", "C1=CC1", "C1=CCC1", "C1=CCCC1", "C1CO1", "C1CN1", "C1CC1C", "CC1CC1")
_RING_OTHERS = ("C", "CC", "C=C", "CO", "C1CC1", "C1=CC1")

#: Frozen sweep results (reproduced live by ``_rdkit_cross_check`` when rdkit is present).
ACYCLIC_SWEEP_PAIRS = 992
ACYCLIC_RULE1B_CONSUMERS = 0                        # RDKit-labels/we-defer over acyclic (tree) centres
# ROUND 33 closed the SINGLE localized-unsaturated-ring gap this sweep originally found (24 -> was every
# unsaturated ring; those now NAME).  The deferrals that REMAIN in this frag set are RING-vs-RING -- a released
# localized ring ranked against ANOTHER ring (Rule-1b / clean-mancude territory, soundly deferred by R33's
# multiring guard), not the old single-ring boundary.  Both still carry a ring double bond, so unsaturated ==
# inscope still holds.  See ``experiments/cip_localized_ring_probe.py`` for the R33 evidence.
RING_SUB_INSCOPE_DEFERRALS = 12                     # off-ring-centre defers where RDKit labels (now ring-vs-ring)
RING_SUB_UNSATURATED = 12                           # ...all still involve an unsaturated ring

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).  Categories:
#:   acyclic-name | ring-sub-sat-name | ring-sub-unsat-name | ring-sub-multiring-defer | ring-centre-defer |
#:   rule3-defer | false-centre
BATTERY = (
    ("N[C@@H](C)C(=O)O",        ("S",), ("S",), "acyclic-name", "L-alanine (Rule 1a)"),
    ("N[C@H](C)C(=O)O",         ("R",), ("R",), "acyclic-name", "D-alanine"),
    ("OC[C@@H](O)C=O",          ("R",), ("R",), "acyclic-name", "D-glyceraldehyde"),
    ("[C@H](F)(Cl)Br",          ("S",), ("S",), "acyclic-name", "CHFClBr (distinct-Z)"),
    ("[C@@H](F)(Cl)Br",         ("R",), ("R",), "acyclic-name", "enantiomer"),
    ("N[C@@H](C)CC",            ("S",), ("S",), "acyclic-name", "2-aminobutane"),
    ("F[C@@](Cl)([2H])[3H]",    ("R",), ("R",), "acyclic-name", "isotope: Rule 2 decides (R28)"),
    ("[2H]O[C@@](Br)(Cl)O[3H]", ("S",), ("S",), "acyclic-name", "isotope: Rule 2 (R28)"),
    ("O[C@H](c1ccccc1)c1ccccn1",("R",), ("R",), "acyclic-name", "aromatic phenyl vs pyridyl (mancude names)"),
    # saturated ring substituent, OFF-ring centre -> we NAME (matches rdkit): ring closures handled by Rule 1a.
    ("[C@](C1CC1)(C)(F)Cl",     ("R",), ("R",), "ring-sub-sat-name", "cyclopropyl substituent, saturated"),
    ("[C@](C1CCC1)(C)(F)Cl",    ("R",), ("R",), "ring-sub-sat-name", "cyclobutyl substituent, saturated"),
    ("C[C@](C1CC1)(CC)C(C)C",   ("S",), ("S",), "ring-sub-sat-name", "cyclopropyl/isopropyl/ethyl (Rule 1a)"),
    # LOCALIZED UNSATURATED ring substituent, OFF-ring centre -> NAMED SINCE ROUND 33 (the gap this harness found
    # is closed; the ligands were always Rule-1a-DISTINCT, only the ring-digraph boundary was too eager):
    ("[C@](C1=CC1)(C)(F)Cl",    ("R",), ("R",), "ring-sub-unsat-name", "cyclopropenyl: localized -> NAMED (R33)"),
    ("[C@](C1=CCC1)(C)(F)Cl",   ("R",), ("R",), "ring-sub-unsat-name", "cyclobutenyl: localized -> NAMED (R33)"),
    # a localized ring ranked against ANOTHER ring stays DEFERRED (ring-vs-ring is Rule-1b territory -- R33 guard):
    ("[C@](C1=CCCCC1)(C1=CCCC1)(C)F", ("S",), (), "ring-sub-multiring-defer", "two localized rings -> Rule-1b territory (R33)"),
    # ACYCLIC deferral that is provably NOT Rule 1b -> Rule 3 (E/Z geometry).  The two propenyl arms are
    # CONSTITUTIONALLY IDENTICAL (-CH=CH-CH3, differing only E vs Z), so by the acyclic lemma they tie under
    # Rule 1a AND Rule 1b (both constitutional); only Rule 3 (double-bond geometry) can decide, and we defer
    # soundly.  (dalembert's boundary case.)
    ("C[C@](/C=C\\C)(/C=C/C)O", ("R",), (), "rule3-defer", "acyclic E/Z: Rule 3 decides (NOT Rule 1b) -> we defer"),
    # RING-ON-CENTRE -> filtered out of scope by _on_cycle before CIP ranking; rdkit labels, we defer.
    ("N[C@]1(F)CCCCO1",         ("R",), (),     "ring-centre-defer", "ring stereocentre (out of scope)"),
    ("C[C@H]1CCCCO1",           ("S",), (),     "ring-centre-defer", "2-methyltetrahydropyran (out of scope)"),
    # genuine false centres -- rdkit finds no centre, we agree (no mislabel):
    ("C[C@](C)(N)O",            (),     (),     "false-centre", "twin methyls"),
    ("CC[C@](CC)(N)O",          (),     (),     "false-centre", "twin ethyls"),
    ("O[C@H](c1ccccc1)c1ccccc1",(),     (),     "false-centre", "diphenyl"),
)


def content_hash() -> str:
    payload = {
        "sweeps": [ACYCLIC_SWEEP_PAIRS, ACYCLIC_RULE1B_CONSUMERS, RING_SUB_INSCOPE_DEFERRALS, RING_SUB_UNSATURATED],
        "battery": [[smi, list(rd), list(exp), cat] for smi, rd, exp, cat, _n in BATTERY],
        "ours_live": [list(cip_labels(smi)) for smi, *_ in BATTERY],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def duplicate_never_collides_with_real() -> int:
    """The acyclic soundness CRUX (dalembert), pinned against an H-filling / phantom-child regression: for every
    duplicate-capable element E, a REAL terminal-E node (carrying at least one Z>=1 child, as valence-filling
    builds it) must outrank a DUPLICATE-E leaf ``(z, mass, ())`` under the shipped ``_cip_compare`` -- i.e. they
    never tie.  This is the invariant that makes "acyclic Rule-1a-tie <=> identical constitution" true (a real
    node and a same-Z duplicate are always Rule-1a-separated), from which Rule 1b's acyclic inertness follows.
    Returns the number of elements checked.  RAISES if the invariant ever regresses."""
    ctx = {"cmp": {}, "sc": {}, "budget": [400000]}
    mh = _cip_mass("H", 0)
    checked = 0
    for element in _DUPLICATE_CAPABLE:
        z = {"C": 6, "N": 7, "O": 8, "S": 16}[element]
        m = _cip_mass(element, 0)
        real = (z, m, ((1, mh, ()),))               # a real terminal E: at least one Z>=1 (H) child
        dup = (z, m, ())                             # a duplicate-E leaf: only phantom-0 children
        assert _cip_compare(real, dup, ctx) != 0, f"CRUX REGRESSION: real {element} collides with its duplicate"
        checked += 1
    return checked


def validate() -> None:
    """Raise if the shipped namer does not reproduce the oracle-verified finding (RDKit-free)."""
    acyclic_agreements = ring_names = multiring_defers = rule3_defers = 0
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"

        if category in ("acyclic-name", "ring-sub-sat-name", "ring-sub-unsat-name"):
            # we emit a label; it must MATCH the RDKit oracle (never mislabel).  ring-sub-unsat-name is the class
            # ROUND 33 closed (a localized ring substituent, the only ring on the centre).
            assert got == rd_label, f"MISLABEL vs oracle on {smi}: {got} != rdkit {rd_label}"
            acyclic_agreements += category == "acyclic-name"
            ring_names += category in ("ring-sub-sat-name", "ring-sub-unsat-name")
        elif category == "ring-sub-multiring-defer":
            # rdkit labels, we defer -- a localized ring ranked against ANOTHER ring is Rule-1b territory (R33 guard).
            assert rd_label and not got, f"{smi} must be rdkit-labels/we-defer"
            multiring_defers += 1
        elif category == "rule3-defer":
            # an ACYCLIC rdkit-labels/we-defer case that is provably NOT Rule 1b: the contested ligands are
            # constitutionally identical (E/Z isomers), so Rule 1b (constitutional) ties too -- Rule 3 decides.
            assert rd_label and not got, f"{smi} must be an acyclic rdkit-labels/we-defer (Rule 3) case"
            rule3_defers += 1

    # non-vacuity: the battery must genuinely exercise oracle agreement, ring naming, and the boundary defers.
    assert acyclic_agreements >= 8, "battery must non-vacuously exercise acyclic oracle agreement"
    assert ring_names >= 4, "battery must exercise ring-substituent naming (saturated + localized-unsaturated)"
    assert multiring_defers >= 1, "battery must pin the ring-vs-ring (Rule-1b territory) deferral"
    assert rule3_defers >= 1, "battery must include the acyclic Rule-3 (not Rule-1b) deferral boundary"

    # the acyclic soundness crux (dalembert): a duplicate never collides with a real same-Z node.
    assert duplicate_never_collides_with_real() == len(_DUPLICATE_CAPABLE)

    # THE ISOLATION, post-R33: a saturated ring substituent NAMES, and so does the SAME ring with a double bond
    # (the R32 gap is closed).  Both were always Rule-1a-DISTINCT from the C/F/Cl spectators -- never a Rule-1b tie.
    assert cip_labels("[C@](C1CC1)(C)(F)Cl") == ("R",), "saturated cyclopropyl substituent must NAME"
    assert cip_labels("[C@](C1=CC1)(C)(F)Cl") == ("R",), "localized cyclopropenyl substituent must NAME (R33 closed the gap)"

    # THE FINDING (unchanged): no acyclic Rule-1b consumer.  The ring-substituent deferrals that remain are
    # ring-vs-ring (Rule-1b territory), all still carrying an unsaturated ring.
    assert ACYCLIC_RULE1B_CONSUMERS == 0, "no acyclic Rule-1b consumer"
    assert RING_SUB_UNSATURATED == RING_SUB_INSCOPE_DEFERRALS, "every remaining in-scope ring-sub deferral involves an unsaturated ring"


def _acyclic_sweep(rd_labels, defers) -> dict:
    """Reproduce the acyclic (tree) sweep: no stereocentre where RDKit labels and we defer."""
    tested = hits = 0
    for a, b in itertools.combinations(_ACYCLIC_FRAGS, 2):
        for t, u in (("F", "Cl"), ("O", "N")):
            smi = f"[C@]({a})({b})({t}){u}"
            rl, m = rd_labels(smi)
            if m is None:
                continue
            tested += 1
            if rl and defers(smi):
                hits += 1
    return {"pairs": tested, "rule1b_consumers": hits}


def _ring_substituent_sweep(rd_labels, defers) -> dict:
    """Reproduce the ring-substituent sweep: off-ring-centre deferrals, all triggered by ring unsaturation."""
    tested = inscope = unsat = 0
    for r in _RING_FRAGS:
        for o in _RING_OTHERS:
            smi = f"[C@]({r})({o})(F)Cl"
            rl, m = rd_labels(smi)
            if m is None:
                continue
            tested += 1
            if rl and defers(smi) and m.GetRingInfo().NumAtomRings(0) == 0:      # off-ring centre = in scope
                inscope += 1
                if any(b.GetBondTypeAsDouble() == 2.0 and b.IsInRing() for b in m.GetBonds()):
                    unsat += 1
    return {"pairs": tested, "inscope_deferrals": inscope, "unsaturated": unsat}


def _rdkit_cross_check() -> dict:
    """Re-verify the battery labels AND re-run both committed sweeps live against RDKit.  RAISES on any
    disagreement.  Only where rdkit is installed (dev/probe env, NOT the committed suite)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    def rd_labels(smi):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            return None, None
        rdCIPLabeler.AssignCIPLabels(m)
        return tuple(a.GetProp("_CIPCode") for a in m.GetAtoms() if a.HasProp("_CIPCode")), m

    def defers(smi):
        try:
            r = cip_labels(smi)
            return r == () or any(x in (None, "?", "") for x in r)
        except Exception:
            return True

    for smi, rd_label, _exp, _cat, note in BATTERY:
        live, _m = rd_labels(smi)
        assert live is not None and set(live) == set(rd_label), f"baked rdkit label stale on {smi}: {live} vs {rd_label} [{note}]"

    ac = _acyclic_sweep(rd_labels, defers)
    rs = _ring_substituent_sweep(rd_labels, defers)
    assert ac["pairs"] == ACYCLIC_SWEEP_PAIRS, f"acyclic sweep size drift: {ac['pairs']} != {ACYCLIC_SWEEP_PAIRS}"
    assert ac["rule1b_consumers"] == 0, f"acyclic Rule-1b consumer appeared ({ac['rule1b_consumers']}) -- re-open the defer"
    assert rs["inscope_deferrals"] == RING_SUB_INSCOPE_DEFERRALS, f"ring-sub deferral count drift: {rs['inscope_deferrals']}"
    assert rs["unsaturated"] == rs["inscope_deferrals"], f"a SATURATED-ring in-scope deferral appeared -- may be a Rule-1b tie, scrutinise: {rs}"
    return {"battery_verified": len(BATTERY), "acyclic": ac, "ring_substituent": rs}


def report() -> dict:
    return {
        "battery_size": len(BATTERY),
        "acyclic_sweep_pairs": ACYCLIC_SWEEP_PAIRS,
        "acyclic_rule1b_consumers": ACYCLIC_RULE1B_CONSUMERS,
        "ring_sub_inscope_deferrals": RING_SUB_INSCOPE_DEFERRALS,
        "ring_sub_unsaturated": RING_SUB_UNSATURATED,
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
