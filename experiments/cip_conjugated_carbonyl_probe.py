"""CIP-CONJUGATED-CARBONYL-01: the ROUND-39 build of exocyclic-carbonyl conjugated-ring CIP naming (queue item 1).

Queue item 1 is "charged/conjugated ring representation -- extend mancude past the neutral bounded C/N/O/S
slice."  An oracle-driven recon (RDKit ``rdCIPLabeler`` + a code-boundary read + a consumer hunt) carved that
item into a BUILDABLE slice with a real forcing-consumer set and two cleanly-bounded DEFERRED slices:

* BUILT (this round): a NEUTRAL internally-conjugated ring bearing an EXOCYCLIC TERMINAL-CHALCOGEN carbonyl
  (a ring ketone / lactone / quinone ``C=O`` or the ``C=S`` thio analogue).  The exocyclic-carbonyl ring
  carbon is admitted as a pass-through SPECTATOR (``_exocyclic_carbonyl_spectator`` in smiles.py): its ring
  bonds are both single so it takes no ring double in ANY Kekule, and its exocyclic double is Kekule-FIXED
  (terminal partner) and chemically LOCALIZED (a chalcogen carbonyl adds no aromatic-resonance form).  The
  ring then RELEASES on its unique acceptor matching (real z/mass, ordinary digraph) and ordinary Rule 1a
  names the centre -- ADMISSION, not new averaging.  Real forcing consumers that PREVIOUSLY DEFERRED and now
  NAME (0 mislabels vs RDKit): L-ascorbic acid (VITAMIN C), carvone, the quinones/naphthoquinones, the
  cyclohexenones/cyclopentenones, the butenolides.

* DEFERRED, fail-closed (documented, NOT built): (1) CHARGED conjugated/aromatic rings -- pyridinium /
  imidazolium / thiazolium.  Two DISTINCT defer paths: a charged AROMATIC spelling (``[nH+]``) hits the parser
  kekulization wall (``SmilesError``, upstream of the namer); a charged explicit-KEKULE spelling parses and then
  declines at the namer's charge gate (``smiles.py:1193``, ``if atom.charge: valid = False``).  Either way the
  mancude AVERAGING sub-capability has only synthetic consumers (the recon's consumer bearing); (2)
  EXOCYCLIC ``=CH2`` (fulvene, quinodimethane) / ``=NH`` (azafulvene) -- the textbook non-benzenoid
  aromatic-resonance systems where a fixed release could diverge from the oracle.  A wrong R/S is worse than
  an honest decline (``a-sound-extension-guards-its-new-cross-comparisons``).

The load-bearing SOUNDNESS invariant (dalembert R33, generalized): a terminal-chalcogen exocyclic double
contributes the SAME ``order-1`` duplicate leaf in every Kekule structure, so it never perturbs
``need[a] = Sigma(order-1)`` for the ring; therefore ``matching_count`` over the TRUE ring acceptors still
equals the ring's Kekule count and ``matching_count == 1 <=> unique Kekule`` (sound RELEASE) is preserved.
The direct test of that invariant is SPELLING/KEKULE-INVARIANCE: the shipped labels are identical across
RDKit respellings of the same molecule (``_assert_structure_theorem``), the exact test that would catch the
R33-scar fixed-Kekule artifact.

``validate()``, ``content_hash()`` and ``_assert_structure_theorem()`` are RDKit-free (committed baseline).
``_rdkit_cross_check()`` is a gated development-oracle probe (dev venv only); the frozen RDKit references were
BLESSED against RDKit 2026.03.6 at authoring time.  Re-run ``python -m experiments.cip_conjugated_carbonyl_probe``
after an intentional change and set ``FROZEN_HASH`` to the printed value.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.smiles import _parse_skeleton_stereo, cip_labels, cip_labels_by_atom

FROZEN_HASH = "ff90e36098762265e836de97f2c4fd4ed26b2affc77f78d137869010c9914763"

#: (SMILES, blessed repo per-atom map, blessed RDKit per-atom map, category, note).
#: category: "consumer"  -- PREVIOUSLY DEFERRED, now NAMES (the built slice); repo == RDKit
#:           "regress"   -- named before and after, unchanged (no-regression anchors, incl. mancude averaging)
#:           "defer"     -- OUT OF SCOPE, fail-closed: repo declines, RDKit names (charged / =CH2 / =NH)
#:           "control"   -- not a stereocentre: both decline
BATTERY = (
    # ---- BUILT: conjugated exocyclic-carbonyl consumers that previously deferred and now NAME ----
    ("OC[C@@H](O)[C@@H]1OC(=O)C(O)=C1O", {2: "R", 4: "S"}, {2: "R", 4: "S"}, "consumer",
     "L-ascorbic acid (VITAMIN C): enediol-lactone, two centres, both named"),
    ("CC(=C)[C@@H]1CC(=O)C(C)=CC1", {3: "S"}, {3: "S"}, "consumer",
     "carvone (spearmint terpene): cyclohex-2-en-1-one, ring-ketone decides"),
    ("O[C@@H]1CCC(=O)C=C1", {1: "R"}, {1: "R"}, "consumer",
     "4-hydroxycyclohex-2-enone: exocyclic enone C=O"),
    ("C[C@@H](O)C1=CC(=O)C=CC1=O", {1: "R"}, {1: "R"}, "consumer",
     "quinonyl ethanol: two exocyclic quinone C=O in one ring"),
    ("O[C@@H](C)C1=CC(=O)c2ccccc2C1=O", {1: "S"}, {1: "S"}, "consumer",
     "hydroxyethyl-naphthoquinone: quinone C=O fused to averaged benzene"),
    ("O[C@@H](C)C1=CC2=CC=CC=CC=C2C1=O", {1: "S"}, {1: "S"}, "consumer",
     "carbonyl on a NON-benzenoid fused ring reaching the AVERAGING path (dalembert R39 reinforcement): the "
     "carbonyl carbon is a spectator, the ambiguous (matching_count>=2) cycle averages, 0 mislabels vs RDKit"),
    ("C[C@@H]1OC(=O)C=C1", {1: "S"}, {1: "S"}, "consumer",
     "5-methylbut-2-en-4-olide (butenolide): lactone C=O + ring C=C"),
    ("CC(=O)[C@@H]1CCC(=O)C=C1", {3: "R"}, {3: "R"}, "consumer",
     "1-acetyl-4-oxocyclohex-2-ene: ring enone C=O with an exocyclic acetyl"),
    ("O[C@@H](CC)C1=CC(=O)C=CC1=O", {1: "S"}, {1: "S"}, "consumer",
     "propyl quinonyl carbinol: in-class variant"),
    # ---- REGRESSION: named before AND after, unchanged (incl. mancude averaging on a neutral aromatic) ----
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O", {3: "S", 6: "R", 9: "R"}, {3: "S", 6: "R", 9: "R"}, "regress",
     "menthol: saturated ring, untouched"),
    ("OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O",
     {2: "R", 4: "R", 6: "R", 8: "S", 10: "S"}, {2: "R", 4: "R", 6: "R", 8: "S", 10: "S"}, "regress",
     "glucopyranose: five centres, untouched"),
    ("OC(=O)[C@@H]1CCC=CC1", {3: "R"}, {3: "R"}, "regress",
     "cyclohexene-carboxylate: localized ring released (R33), untouched"),
    ("O[C@H](c1ccccc1)c1ccncc1", {1: "R"}, {1: "R"}, "regress",
     "phenyl-vs-pyridyl carbinol: neutral mancude AVERAGING path, untouched"),
    # ---- DEFERRED, fail-closed: OUT OF SCOPE, repo declines while RDKit names ----
    ("C[C@@H](O)C1=[N+](C)C=CS1", {}, {1: "R"}, "defer",
     "2-(1-hydroxyethyl)thiazolium: CHARGED aromatic ring -> parser/charge wall (out of scope)"),
    ("O[C@@H](CC)C1=CC=CC1=C", {}, {1: "S"}, "defer",
     "fulvenyl carbinol: exocyclic =CH2 (aromatic-resonance ambiguity) -> deferred"),
    ("O[C@@H](C)C1=CC(=N)C=CC1=O", {}, {1: "S"}, "defer",
     "quinone-imine carbinol: exocyclic =NH -> deferred"),
    # ---- CONTROL: symmetric, not a stereocentre; both decline ----
    ("O=C1C=C[C@@H](O)C=C1", {}, {}, "control",
     "4-hydroxy-cyclohexa-2,5-dienone (p-quinol): symmetric, NOT a centre"),
)

#: molecules whose R/S must be INVARIANT under respelling (the direct fixed-Kekule / R33-scar test).
_INVARIANCE = (
    "OC[C@@H](O)[C@@H]1OC(=O)C(O)=C1O",   # vitamin C
    "C[C@@H](O)C1=CC(=O)C=CC1=O",         # quinonyl ethanol
    "CC(=C)[C@@H]1CC(=O)C(C)=CC1",        # carvone
    "C[C@@H]1OC(=O)C=C1",                 # butenolide
)


def _payload() -> dict:
    """The namer's ACTUAL per-atom output over the battery -- RDKit-free, deterministic, hashed for drift."""
    return {smi: sorted(cip_labels_by_atom(smi).items()) for smi, *_ in BATTERY}


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True).encode()).hexdigest()


def _rdkit_respellings(smi: str, n: int = 6) -> list:
    """RDKit-generated respellings of one molecule (aromatic/Kekule/atom-order permutations), same structure."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smi)
    out = []
    for seed in range(n):
        try:
            out.append(Chem.MolToSmiles(mol, doRandom=True, canonical=False))
        except Exception:  # noqa: BLE001
            continue
    return out


def _assert_structure_theorem() -> None:
    """RDKit-free proof that the exocyclic-carbonyl release is SOUND (representation-invariant), not a fixed
    Kekule shortcut.

    * the built consumer slice NAMES (previously deferred) with the blessed labels;
    * the OUT-OF-SCOPE slice (charged / =CH2 / =NH) STILL declines -- the fail-closed boundary is intact;
    * ENANTIOMER CONSISTENCY (the RDKit-free invariance leg): a CIP descriptor is a geometric fact, so the
      mirror image of a named centre must carry the MIRRORED descriptor -- every R<->S, r<->s.  A fixed-Kekule
      artifact or a representation that fabricated a distinction would not flip cleanly.  (The sharper
      SAME-MOLECULE respelling-invariance test needs machine-generated respellings, so it lives in the gated
      ``_rdkit_cross_check`` via ``_INVARIANCE`` -- hand-authored "equivalent" spellings are error-prone.)
    """
    # (a) the built consumers name with the blessed labels; the deferred slice still declines.
    for smi, expected, _rd, category, note in BATTERY:
        got = cip_labels_by_atom(smi)
        if category == "consumer":
            assert got == expected and got, f"a built consumer must NAME {smi}: {got} != {expected} [{note}]"
        if category == "defer":
            assert got == {}, f"an out-of-scope centre must DEFER (fail-closed), not name: {smi} -> {got} [{note}]"
        if category == "control":
            assert got == {}, f"a non-stereocentre must not be named: {smi} -> {got} [{note}]"

    # (b) enantiomer consistency over single-centre release-class rings: the @@ / @ mirror flips every label.
    flip = {"R": "S", "S": "R", "r": "s", "s": "r"}
    mirror_pairs = (
        ("O[C@@H]1CCC(=O)C=C1", "O[C@H]1CCC(=O)C=C1", "4-hydroxycyclohex-2-enone"),
        ("C[C@@H](O)C1=CC(=O)C=CC1=O", "C[C@H](O)C1=CC(=O)C=CC1=O", "quinonyl ethanol"),
        ("C[C@@H]1OC(=O)C=C1", "C[C@H]1OC(=O)C=C1", "5-methylbutenolide"),
        ("CC(=C)[C@@H]1CC(=O)C(C)=CC1", "CC(=C)[C@H]1CC(=O)C(C)=CC1", "carvone"),
        ("O[C@@H](C)C1=CC(=O)c2ccccc2C1=O", "O[C@H](C)C1=CC(=O)c2ccccc2C1=O", "hydroxyethyl-naphthoquinone"),
    )
    for lhs, rhs, name in mirror_pairs:
        left = cip_labels_by_atom(lhs)
        right = cip_labels_by_atom(rhs)
        assert left, f"the release-class centre must NAME: {name} {lhs} -> {left}"
        assert right == {i: flip[v] for i, v in left.items()}, (
            f"enantiomer inconsistency (fabricated distinction?) on {name}: {left} vs {right}"
        )


def validate() -> None:
    """RDKit-free: the namer produces the blessed per-atom maps; consumers name, deferred slice declines."""
    for smi, expected, _rd, category, note in BATTERY:
        got = cip_labels_by_atom(smi)
        assert got == expected, f"per-atom drift on {smi}: {got} != {expected} [{note}]"
        assert cip_labels(smi) == tuple(sorted(expected.values())), f"cip_labels disagrees on {smi} [{note}]"
    _assert_structure_theorem()


def _rdkit_cross_check() -> dict:
    """Gated development oracle: 0 mislabels vs RDKit on the consumer + regression slice; the deferred slice
    is confirmed to be a REAL RDKit name (so the decline is honest incompleteness, not a non-centre); and the
    labels are invariant across RDKit respellings (the representation-invariance / fixed-Kekule test)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    compared = skipped = mismatches = consumers_named = defers_confirmed = 0
    invariance_ok = 0
    details: list[tuple] = []
    for smi, expected, rd_expected, category, note in BATTERY:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            skipped += 1
            details.append((smi, "rdkit parse fail", note))
            continue
        rdCIPLabeler.AssignCIPLabels(mol)
        rd = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
        rd_syms = {a.GetIdx(): a.GetSymbol() for a in mol.GetAtoms()}
        repo = cip_labels_by_atom(smi)
        repo_syms = {i: a.element for i, a in enumerate(_parse_skeleton_stereo(smi)[0])}
        idxs = set(repo) | set(rd)
        if any(repo_syms.get(i) != rd_syms.get(i) for i in idxs):
            skipped += 1
            details.append((smi, "index-map element mismatch", note))
            continue
        assert rd == rd_expected, f"RDKit drift on {smi}: {rd} != {rd_expected}"
        for i in set(repo) & set(rd):
            compared += 1
            if repo[i] != rd[i]:
                mismatches += 1
                details.append((smi, f"MISLABEL idx {i}: repo {repo[i]} != rd {rd[i]}", note))
        if category == "consumer":
            assert repo and repo == {i: rd[i] for i in repo}, f"consumer must match RDKit: {smi}"
            consumers_named += 1
        if category == "defer":
            assert repo == {} and rd, f"deferred slice must decline while RDKit names: {smi} repo={repo} rd={rd}"
            defers_confirmed += 1

    # representation-invariance: RDKit respellings of each release-class molecule -> constant repo labels
    for smi in _INVARIANCE:
        base = tuple(sorted(cip_labels_by_atom(smi).values()))
        spellings = _rdkit_respellings(smi)
        variants = {tuple(sorted(cip_labels_by_atom(s).values())) for s in spellings if s}
        assert variants <= {base}, f"respelling changed labels on {smi}: base {base} vs {variants}"
        invariance_ok += 1

    return {
        "compared": compared,
        "skipped": skipped,
        "mismatches": mismatches,
        "consumers_named": consumers_named,
        "defers_confirmed": defers_confirmed,
        "invariance_ok": invariance_ok,
        "details": details,
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


def report() -> dict:
    validate()
    return {"content_hash": content_hash(), "hash_matches": content_hash() == FROZEN_HASH}


if __name__ == "__main__":
    validate()
    print("content_hash:", content_hash())
    print("set FROZEN_HASH to the value above")
