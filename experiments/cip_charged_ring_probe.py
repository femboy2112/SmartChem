"""CIP-CHARGED-RING-01: the ROUND-40 build of CHARGED conjugated/aromatic-ring CIP naming (queue item q1).

Queue item q1 was "CHARGED ring representation -- the remaining half of the old conjugated/charged ring item",
carried as VERIFIED-DEFER-LEANING.  A full oracle-driven recon (RDKit ``rdCIPLabeler`` + a code-boundary bearing)
REFUTED the defer lean for the explicit-Kekule slice and carved q1 into a BUILDABLE slice with a real forcing
consumer set and a cleanly-bounded DEFERRED slice:

* BUILT (this round): a ring bearing a CATIONIC ring N in EXPLICIT-KEKULE spelling -- pyridinium, pyridine
  N-oxide, imidazolium, thiazolium -- attached to a stereocentre now NAMES.  The prior namer refused EVERY
  charged ring atom at a blanket charge gate (``smiles.py``, ``if atom.charge: valid = False``).  That gate is
  replaced by a FAIL-CLOSED WHITELIST admitting exactly ONE charge-EXCLUSIVE cationic ACCEPTOR pattern -- a
  cationic ring N (``[1,1,2]`` valence-4, ``atom.charge > 0``), a genuine pi-acceptor taking one ring double,
  so the ring AVERAGES over its Kekule matchings (or RELEASES on a unique matching).

* The load-bearing SOUNDNESS invariant: CIP priority is by ATOMIC NUMBER and formal charge changes NO atomic
  number.  The matching enumeration and the partner-Z average in ``_cip_mancude`` are CHARGE-BLIND BY
  CONSTRUCTION (the matching iterates pure ``ring_adj`` topology; the averaged value is keyed on the element
  string alone; ``_cip_mass`` is keyed on element+isotope, never charge).  The cationic ring N is admitted
  because it has a NEUTRAL ISOELECTRONIC ACCEPTOR ANALOGUE -- pyridine's N -- that RDKit ``rdCIPLabeler``
  averages identically: its averaged ipso duplicate is ``(C:6 + N:7)/2 = 6.5``, which stays BELOW any real
  heteroatom Z >= 7 and so never crosses a competitor's genuine value even in a ring-vs-ring comparison.  The
  ``charge > 0`` guard makes neutral safety STRUCTURAL: a neutral atom skips the branch (a neutral ring N is
  ``[1,2]`` / ``[1,1,1]``; a parser-permissive neutral overvalent N fills to ``[1,1,1,2]`` -- never the
  admitted ``[1,1,2]`` cation pattern), so every NEUTRAL ring stays byte-identical.

* DEFERRED, fail-closed (documented, NOT built): (1) a CATIONIC ring CHALCOGEN (pyrylium O+ / thiopyrylium S+,
  ``[1,2]``) -- it has NO neutral acceptor analogue (a neutral ring O/S is the ``[1,1]`` donor), so its
  charge-blind average ((C+O)/2=7, (C+S)/2=11) CROSSES a real heteroatom and RDKit does NOT reproduce it: a
  PROVEN ring-vs-ring mislabel class (dalembert R40; e.g. ``O[C@H](C1=CC=CC=[S+]1)C1=NC=CS1`` -> repo would
  say S, RDKit R).  Left fail-closed at the residual ``elif atom.charge: valid = False``.  (2) a charged
  AROMATIC spelling (``c1cccc[n+]1C``) hit the parser kekulization wall UPSTREAM of the namer
  (``_aromatic_matchings`` misclassified a cationic ring N as a pyrrole-type donor -> ``SmilesError``) -- this was
  DEFERRED at R40 and is now BUILT by the ROUND-41 charge-aware kekulizer (the two aromatic entries below moved
  from defer to consumer; full evidence in ``cip_charge_aware_kekulizer_probe.py``).  (3) ANIONIC ring atoms (a
  carbanion) -- no validated donor branch.  (4) exotic / over-charged valences (``[NH2+]`` in a ring).  A wrong
  R/S is worse than an honest decline (``a-sound-extension-guards-its-new-cross-comparisons``); every deferred
  class is proven to fail CLOSED (raises or returns ``{}``, NEVER a silent label) in ``_assert_structure_theorem``.

``validate()``, ``content_hash()`` and ``_assert_structure_theorem()`` are RDKit-free (committed baseline).
``_rdkit_cross_check()`` is a gated development-oracle probe (dev venv only); the frozen RDKit references were
BLESSED against RDKit 2026.03.6 at authoring time.  Re-run ``python -m experiments.cip_charged_ring_probe``
after an intentional change and set ``FROZEN_HASH`` to the printed value.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.smiles import SmilesError, _parse_skeleton_stereo, cip_labels, cip_labels_by_atom

FROZEN_HASH = "07f86279c922109a878655d60955d753216b2eee6781eedc14de3b1b1101f14b"

#: (SMILES, blessed repo per-atom map, blessed RDKit per-atom map, category, note).
#: category: "consumer"  -- PREVIOUSLY DEFERRED at the charge gate, now NAMES (the built slice); repo == RDKit
#:           "regress"   -- named/declined before and after, UNCHANGED (neutral no-regression anchors)
#:           "defer"     -- OUT OF SCOPE, fail-closed: repo declines (parser wall / no donor branch), RDKit names
#:           "control"   -- both decline (not a namable centre for either)
BATTERY = (
    # ---- BUILT: charged explicit-Kekule ring consumers that previously deferred at the charge gate, now NAME ----
    ("C[C@H](O)C1=CC=CC=[N+]1C", {1: "S"}, {1: "S"}, "consumer",
     "1-(N-methylpyridinium-2-yl)ethanol: cationic ring N acceptor, ring averages, centre names"),
    ("C[C@@H](O)C1=CC=CC=[N+]1C", {1: "R"}, {1: "R"}, "consumer",
     "enantiomer of the N-methylpyridinium carbinol: label flips"),
    ("C[C@H](O)C1=CC=[NH+]C=C1", {1: "S"}, {1: "S"}, "consumer",
     "protonated pyridinium (N-H) carbinol: the physiological-pH form"),
    ("C[C@@H](O)C1=[N+](C)C=CS1", {1: "R"}, {1: "R"}, "consumer",
     "thiazolium carbinol (thiamine-family motif): cationic N acceptor + neutral S spectator"),
    ("C[C@H](O)C1=[N+](C)C=CN1", {1: "S"}, {1: "S"}, "consumer",
     "imidazolium carbinol: cationic N acceptor + neutral pyrrole-N spectator"),
    ("C[C@H](O)C1=CC=[N+]([O-])C=C1", {1: "S"}, {1: "S"}, "consumer",
     "pyridine N-oxide carbinol: cationic ring N ([1,1,2] with the O- substituent), net-neutral zwitterion"),
    ("O[C@H](c1ccccc1)C1=CC=CC=[N+]1C", {1: "R"}, {1: "R"}, "consumer",
     "phenyl vs N-methylpyridinium carbinol: RING-vs-RING, the averaged fractions decide (not ring>alkyl)"),
    ("O[C@@H](c1ccccc1)C1=CC=CC=[N+]1C", {1: "S"}, {1: "S"}, "consumer",
     "enantiomer of the phenyl/pyridinium ring-vs-ring centre: label flips"),
    ("O[C@H](c1ccncc1)C1=CC=CC=[N+]1C", {1: "R"}, {1: "R"}, "consumer",
     "pyridyl vs pyridinium carbinol: neutral-averaged ring vs charged-averaged ring, both by Z"),
    # RING-vs-HETEROAROMATIC-RING: the load-bearing regime -- a cationic ring N (averaged ipso <= 6.5) vs a real
    # heteroatom competitor, the case dalembert's structure theorem showed decides ON the averaged fraction (and
    # where the original probe was BLIND: it only pitted charged rings against phenyl/alkyl, so the averaged
    # fraction never decided).  N+ is sound here because 6.5 < any real heteroatom Z; the chalcogen cation is NOT.
    ("O[C@H](C1=CC=CC=[N+]1C)C1=NC=CS1", {1: "R"}, {1: "R"}, "consumer",
     "N-methylpyridinium vs THIAZOLE: N+ ipso avg 6.5 < thiazole real values -> correct (dalembert regime)"),
    ("O[C@@H](C1=CC=CC=[N+]1C)C1=NC=CS1", {1: "S"}, {1: "S"}, "consumer",
     "enantiomer of the pyridinium-vs-thiazole ring-vs-ring centre: label flips"),
    ("O[C@H](C1=CC=[N+]([O-])C=C1)C1=NC=CS1", {1: "R"}, {1: "R"}, "consumer",
     "pyridine N-oxide vs THIAZOLE: cationic N ring-vs-heteroaromatic-ring"),
    ("O[C@H](C1=CC=CC=[N+]1C)C1=NN=CS1", {1: "R"}, {1: "R"}, "consumer",
     "N-methylpyridinium vs 1,3,4-THIADIAZOLE: two-heteroatom competitor"),
    ("CC(=O)O[C@@H](C)C1=CC=CC=[N+]1C", {4: "S"}, {4: "S"}, "consumer",
     "1-(pyridinium-2-yl)ethyl acetate: an ester O-ligand vs the charged ring"),
    # ---- REGRESSION: neutral cases, named/declined identically before and after (byte-stable) ----
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O", {3: "S", 6: "R", 9: "R"}, {3: "S", 6: "R", 9: "R"}, "regress",
     "menthol: saturated ring, untouched"),
    ("OC(=O)[C@@H]1CCC=CC1", {3: "R"}, {3: "R"}, "regress",
     "cyclohexene-carboxylate: localized ring released (R33), untouched"),
    ("O[C@H](c1ccccc1)c1ccncc1", {1: "R"}, {1: "R"}, "regress",
     "phenyl-vs-pyridyl carbinol: NEUTRAL mancude AVERAGING path, untouched"),
    ("C[C@H](O)C1=CC=CC1=O", {1: "S"}, {1: "S"}, "regress",
     "cyclopentadienone (R39 exocyclic-carbonyl): untouched"),
    ("OC[C@@H](O)[C@@H]1OC(=O)C(O)=C1O", {2: "R", 4: "S"}, {2: "R", 4: "S"}, "regress",
     "L-ascorbic acid (VITAMIN C, R39): untouched"),
    # ---- DEFERRED, fail-closed: OUT OF SCOPE, repo declines while RDKit names ----
    # ROUND 41 CAPABILITY EXTENSION: these AROMATIC spellings that R40 deferred to the "charge-aware kekulizer
    # slice" are now BUILT -- the charge-aware kekulizer (R41) names them, matching the explicit-Kekule twin.  The
    # full R41 build + representation-invariance evidence lives in experiments/cip_charge_aware_kekulizer_probe.py.
    ("C[C@H](O)c1cccc[n+]1C", {1: "S"}, {1: "S"}, "consumer",
     "N-methylpyridinium AROMATIC spelling: now NAMES via the R41 charge-aware kekulizer (was a parser wall)"),
    ("C[C@@H](O)c1csc[n+]1C", {1: "R"}, {1: "R"}, "consumer",
     "thiazolium AROMATIC spelling: now NAMES via the R41 charge-aware kekulizer (was a parser wall)"),
    ("C[C@H](O)C1=CC=C[CH-]1", {}, {1: "S"}, "defer",
     "cyclopentadienide carbanion carbinol: ANIONIC ring, no validated donor branch -- fail-closed"),
    # cationic CHALCOGEN rings (pyrylium O+ / thiopyrylium S+): DELIBERATELY fail-closed.  Unlike a cationic N
    # (which has a neutral pyridine-N acceptor analogue RDKit averages identically), a cationic chalcogen has NO
    # neutral acceptor analogue, so its charge-blind average ((C+O)/2=7, (C+S)/2=11) CROSSES a real heteroatom and
    # RDKit refuses to fold it in -- a proven ring-vs-ring mislabel class (dalembert R40).  Declined, not named.
    ("C[C@H](O)C1=CC=CC=[O+]1", {}, {1: "S"}, "defer",
     "pyrylium carbinol: cationic ring O -> fail-closed (no neutral acceptor analogue; RDKit-divergent averaging)"),
    ("O[C@H](C1=CC=CC=[S+]1)C1=NC=CS1", {}, {1: "R"}, "defer",
     "thiopyrylium vs thiazole (the dalembert R40 tombstone): chalcogen-cation ring-vs-ring -> fail-closed (was S vs R)"),
    # ---- CONTROL: both decline (parser-permissive neutral overvalent / exotic charge; RDKit rejects) ----
    ("C[C@H](O)C1=CC=[NH2+]C=C1", {}, {}, "control",
     "over-protonated [NH2+] ring: exotic valence, both the repo and RDKit decline"),
    ("C[C@H](O)C1=CC=N(C)C=C1", {}, {}, "control",
     "NEUTRAL overvalent ring N [1,1,2] (parser accepts, RDKit rejects): the charge>0 guard keeps it fail-closed "
     "byte-stable (birdperson R40 byte-stability anchor -- a neutral atom must never reach the cationic branch)"),
)

#: molecules whose R/S must be INVARIANT under RDKit respelling (the representation-invariance / fixed-Kekule test).
_INVARIANCE = (
    "C[C@H](O)C1=CC=CC=[N+]1C",             # N-methylpyridinium carbinol
    "C[C@@H](O)C1=[N+](C)C=CS1",            # thiazolium carbinol
    "O[C@H](C1=CC=CC=[N+]1C)C1=NC=CS1",     # pyridinium-vs-thiazole ring-vs-ring (the dalembert regime)
    "O[C@H](c1ccccc1)C1=CC=CC=[N+]1C",      # phenyl-vs-pyridinium ring-vs-ring
)


def _payload() -> dict:
    """The namer's ACTUAL per-atom output over the battery -- RDKit-free, deterministic, hashed for drift.
    A deferred/parser-walled entry is recorded as its outcome so a regression that started NAMING it (a
    fail-open) or that changed a consumer's label moves the hash."""
    out = {}
    for smi, *_ in BATTERY:
        try:
            out[smi] = sorted(cip_labels_by_atom(smi).items())
        except SmilesError:
            out[smi] = "parser-wall"
    return out


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True).encode()).hexdigest()


def _rdkit_respellings(smi: str, n: int = 8) -> list:
    """RDKit-generated EXPLICIT-KEKULE respellings of one molecule (Kekule double-bond placement + atom-order
    permutations), same structure.  Kekule (not aromatic) output on purpose: a charged AROMATIC respelling is
    the DEFERRED parser-wall slice, so an aromatic variant would just hit our SmilesError and prove nothing;
    the meaningful invariance is over the representations the built namer actually accepts."""
    from rdkit import Chem

    out = []
    for _seed in range(n):
        mol = Chem.MolFromSmiles(smi)
        try:
            Chem.Kekulize(mol, clearAromaticFlags=True)
            out.append(Chem.MolToSmiles(mol, doRandom=True, canonical=False, kekuleSmiles=True))
        except Exception:  # noqa: BLE001
            continue
    return out


def _assert_structure_theorem() -> None:
    """RDKit-free proof that admitting charged rings is SOUND and every deferred class fails CLOSED.

    * the built consumer slice NAMES (previously deferred) with the blessed labels;
    * the OUT-OF-SCOPE slice (aromatic spelling / anion / exotic) FAILS CLOSED -- it raises SmilesError or
      returns {}, NEVER a silent label (the honest-defer obligation: a silent wrong R/S is the only failure);
    * ENANTIOMER CONSISTENCY: a CIP descriptor is a geometric fact, so the mirror image of a named centre
      carries the MIRRORED descriptor -- every R<->S.  A representation that fabricated a charge-dependent
      distinction (rather than averaging by charge-invariant Z) would not flip cleanly.
    """
    # (a) built consumers name with the blessed labels; deferred/control classes never emit a silent label.
    for smi, expected, _rd, category, note in BATTERY:
        try:
            got = cip_labels_by_atom(smi)
        except SmilesError:
            got = "parser-wall"
        if category == "consumer":
            assert got == expected and got, f"a built consumer must NAME {smi}: {got} != {expected} [{note}]"
        if category in ("defer", "control"):
            assert got in ({}, "parser-wall"), (
                f"an out-of-scope centre must FAIL CLOSED (raise or {{}}), never a silent label: "
                f"{smi} -> {got} [{note}]"
            )

    # (b) enantiomer consistency: the @@ / @ mirror flips every label on the charged-ring release/average class.
    flip = {"R": "S", "S": "R", "r": "s", "s": "r"}
    mirror_pairs = (
        ("C[C@H](O)C1=CC=CC=[N+]1C", "C[C@@H](O)C1=CC=CC=[N+]1C", "N-methylpyridinium carbinol"),
        ("C[C@@H](O)C1=[N+](C)C=CS1", "C[C@H](O)C1=[N+](C)C=CS1", "thiazolium carbinol"),
        ("O[C@H](C1=CC=CC=[N+]1C)C1=NC=CS1", "O[C@@H](C1=CC=CC=[N+]1C)C1=NC=CS1", "pyridinium/thiazole ring-vs-ring"),
        ("O[C@H](c1ccccc1)C1=CC=CC=[N+]1C", "O[C@@H](c1ccccc1)C1=CC=CC=[N+]1C", "phenyl/pyridinium ring-vs-ring"),
        ("C[C@H](O)C1=CC=[N+]([O-])C=C1", "C[C@@H](O)C1=CC=[N+]([O-])C=C1", "pyridine N-oxide carbinol"),
    )
    for lhs, rhs, name in mirror_pairs:
        left = cip_labels_by_atom(lhs)
        right = cip_labels_by_atom(rhs)
        assert left, f"the charged-ring centre must NAME: {name} {lhs} -> {left}"
        assert right == {i: flip[v] for i, v in left.items()}, (
            f"enantiomer inconsistency (fabricated charge-dependent distinction?) on {name}: {left} vs {right}"
        )


def validate() -> None:
    """RDKit-free: the namer produces the blessed per-atom maps; consumers name, deferred slice fails closed."""
    for smi, expected, _rd, category, note in BATTERY:
        try:
            got = cip_labels_by_atom(smi)
        except SmilesError:
            got = "parser-wall"
        if category == "defer" and expected == {}:
            assert got in ({}, "parser-wall"), f"deferred entry must fail closed on {smi}: {got} [{note}]"
        else:
            assert got == expected, f"per-atom drift on {smi}: {got} != {expected} [{note}]"
            assert cip_labels(smi) == tuple(sorted(expected.values())), f"cip_labels disagrees on {smi} [{note}]"
    _assert_structure_theorem()


def _rdkit_cross_check() -> dict:
    """Gated development oracle: 0 mislabels vs RDKit on the consumer + regression slice; the deferred slice is
    confirmed a REAL RDKit name (so the decline is honest incompleteness, not a non-centre); labels are invariant
    across RDKit respellings (the representation-invariance / fixed-Kekule test)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    compared = skipped = mismatches = consumers_named = defers_confirmed = invariance_ok = 0
    details: list[tuple] = []
    for smi, expected, rd_expected, category, note in BATTERY:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            skipped += 1
            details.append((smi, "rdkit parse fail", note))
            if category in ("defer", "control"):
                # a control both decline: fine; a defer that RDKit cannot parse is not a proof of a name
                pass
            continue
        rdCIPLabeler.AssignCIPLabels(mol)
        rd = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
        rd_syms = {a.GetIdx(): a.GetSymbol() for a in mol.GetAtoms()}
        try:
            repo = cip_labels_by_atom(smi)
        except SmilesError:
            repo = {}
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
            assert repo == {} and rd, f"deferred slice must fail closed while RDKit names: {smi} repo={repo} rd={rd}"
            defers_confirmed += 1

    for smi in _INVARIANCE:
        base = tuple(sorted(cip_labels_by_atom(smi).values()))
        variants = set()
        for s in _rdkit_respellings(smi):
            if not s:
                continue
            try:
                variants.add(tuple(sorted(cip_labels_by_atom(s).values())))
            except SmilesError:
                continue                      # a stray aromatic respelling is the deferred slice, skip it
        assert variants and variants <= {base}, (
            f"respelling changed labels (or none parsed) on {smi}: base {base} vs {variants}"
        )
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
