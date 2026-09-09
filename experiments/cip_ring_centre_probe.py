"""CIP-RING-CENTRE-01: ROUND 34 item 3 -- a stereocentre ON a ring (Rules 4/5 territory) is a VERIFIED DEFER.

The namer scopes a ring stereocentre OUT via ``_on_cycle`` (in both ``_cip_labels`` and ``_perceive_configuration``)
and DEFERS it -- never a guessed label.  This item asked whether ring stereocentres (menthol, cis/trans
disubstituted rings, pseudo-asymmetric centres) can be named.  Answer, oracle-verified: NO -- not soundly, not
this round.  A sound ring-centre namer needs THREE things, each a genuine build:

  1. WRITTEN NEIGHBOUR ORDER for the tetrahedral parity.  A ring-closure bond is appended to ``bonds`` at the
     CLOSING digit, not at the OPENING digit's written position -- but SMILES chirality is defined by the order the
     neighbours (branches AND ring-closure digits) appear AT the chiral atom.  The acyclic
     ``incoming``/``outgoing`` reconstruction therefore mis-orders a ring centre's neighbours -> a WRONG parity ->
     a wrong R/S.  ``_on_cycle`` fails closed exactly here.  (The parser would need per-atom written-order capture,
     like the R34-item-1 direction capture.)
  2. RELIABLE RING-vs-RING RANKING.  A ring stereocentre's two ring-path ligands ARE a ring-vs-ring comparison --
     the very deep-ring-descent ROUND 34 item 5 proved our Rule-1a digraph resolves DIFFERENTLY from the oracle for
     same-kind pairs (``_CIP_RING_VS_RING_GUARD``).  So even a diagnostic bypass of ``_on_cycle`` finds cases that
     RANK but would MISLABEL.  Item 5's unlock (a Rule-1b constitutional comparator / a verified ring digraph) is a
     prerequisite here too.
  3. RULES 4/5 (auxiliary descriptors + pseudo-asymmetry).  cis/trans-disubstituted rings and meso systems need
     Rule 4 (like/unlike auxiliary R/S descriptors, assigned recursively); pseudo-asymmetric centres need Rule 5
     (lowercase 'r'/'s', R>S) -- RDKit returns these here (``O[C@H]1CC[C@@H](C)CC1`` -> ('s','s')).  Neither is built.

So building ring-centre naming now would MISLABEL on all three counts -> DEFER (the R32 discipline: a
proven-cannot-build-soundly-yet feature is a verified defer, with committed evidence + the named unlock).

This harness pins the finding ("experiments are committed") + confirms the current defer is SOUND (0 mislabels;
``_on_cycle`` gates every marked ring centre) and the consumer is REAL (RDKit labels them, incl. pseudo-asymmetric).
``validate()``/``content_hash()`` are RDKit-FREE; ``_rdkit_cross_check()`` re-verifies the oracle labels live.
Re-run ``python -m experiments.cip_ring_centre_probe`` after an INTENTIONAL change and set ``FROZEN_HASH``.
"""
from __future__ import annotations

import hashlib
import json

from smartchem import smiles
from smartchem.smiles import cip_labels

FROZEN_HASH = "bc4ac5ec65783218953c50103dffb99fe6b0c1f8d9cf41170ba2f78972a6732d"

#: Oracle-verified battery: (smiles, rdkit_label, expected_ours, category, note).
#:   ringcentre-defer (rdkit names, we defer) | agreed-defer (both defer: not a real stereocentre)
BATTERY = (
    ("C[C@H]1CCCCC1O",                   ("S",),           (), "ringcentre-defer", "3-methylcyclohexanol centre (Rule-1a-ish, but parity needs written order)"),
    ("O[C@H]1CCCC[C@@H]1O",              ("S", "S"),       (), "ringcentre-defer", "trans-cyclohexane-1,2-diol"),
    ("[C@H]1(F)CCCC[C@@H]1Cl",           ("S", "S"),       (), "ringcentre-defer", "1-F-2-Cl-cyclohexane"),
    ("F[C@H]1CCCC[C@H]1Cl",              ("R", "S"),       (), "ringcentre-defer", "cis 1-F-2-Cl-cyclohexane (R,S)"),
    ("O[C@H]1CC[C@@H](C)CC1",            ("s", "s"),       (), "ringcentre-defer", "cis-4-methylcyclohexanol: PSEUDO-ASYMMETRIC (Rule 5, r/s)"),
    ("O[C@@H]1CC[C@H](Cl)CC1",           ("s", "s"),       (), "ringcentre-defer", "4-Cl-cyclohexanol: PSEUDO-ASYMMETRIC (Rule 5)"),
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O",  ("R", "R", "S"),  (), "ringcentre-defer", "menthol: three ring stereocentres"),
    # agreed-defer: a SYMMETRIC ring carbon is not a real stereocentre -- both we and RDKit defer (sound, not a consumer)
    ("O[C@H]1CCCCC1",                    (),               (), "agreed-defer", "cyclohexanol C1: two identical ring arms -> not a stereocentre"),
    ("C1CC[C@H](O)CC1",                  (),               (), "agreed-defer", "4-position of cyclohexanol: symmetric -> not a stereocentre"),
)


def defers(lab) -> bool:
    return not lab or any(x in (None, "?", "") for x in (lab or ()))


def _on_cycle_gates_all_marked_ring_centres() -> bool:
    """RDKit-FREE: for every ``ringcentre-defer`` battery molecule, the marked centre lies ON a ring (``_on_cycle``
    True) -- i.e. the deferral is the ring-centre scope gate, not an incidental miss."""
    from smartchem.smiles import _parse_skeleton, _kekulize_in_place, _fill_hydrogens, _on_cycle
    for smi, _rd, _exp, cat, _n in BATTERY:
        if cat != "ringcentre-defer":
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
    """RDKit-free: every ring stereocentre DEFERS (never a guessed label); the consumer is real; the gate is _on_cycle."""
    assert hasattr(smiles, "_on_cycle"), "the ring-centre scope gate must exist"
    consumers = pseudo = agreed = 0
    for smi, rd_label, expected, category, note in BATTERY:
        got = tuple(cip_labels(smi))
        assert got == expected, f"namer drift on {smi}: got {got}, expected {expected} [{note}]"
        assert defers(got), f"{smi} must DEFER (ring stereocentre out of scope) [{note}]"
        if category == "ringcentre-defer":
            assert rd_label, f"{smi} is only a consumer if rdkit LABELS it [{note}]"
            consumers += 1
            pseudo += any(x in ("r", "s") for x in rd_label)
        else:
            assert not rd_label, f"{smi} agreed-defer means rdkit also defers [{note}]"
            agreed += 1
    assert consumers >= 6, "must show a real ring-centre consumer population"
    assert pseudo >= 2, "must exhibit the pseudo-asymmetric (Rule 5, r/s) sub-class"
    assert agreed >= 1, "must include a symmetric non-stereocentre (agreed defer, sound)"
    assert _on_cycle_gates_all_marked_ring_centres(), "every deferred ring centre must be gated by _on_cycle"


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
            "consumers": sum(1 for *_r, c, _n in BATTERY if c == "ringcentre-defer")}


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
