"""CIP-CHARGE-AWARE-KEKULIZER-01: the ROUND-41 build (queue item q1) -- a charged AROMATIC-spelling ring now
NAMES and unifies with its explicit-Kekulé spelling.

ROUND 40 named a CATIONIC-ring-N heterocycle written in EXPLICIT-KEKULÉ form (``C1=CC=CC=[N+]1C``) but WALLED the
natural AROMATIC spelling (``c1cccc[n+]1C``): the parser's ``_aromatic_matchings`` classified a cationic ring N as
a pyrrole-type DONOR (it has 3 sigma bonds), so the ring lost an acceptor, no perfect matching existed, and
parsing raised ``SmilesError``.  R40's own probe recorded those aromatic spellings as PROVEN-REAL DEFERRED
consumers (RDKit names them; we walled).  This round refutes that defer:

* BUILT (the kekulizer): ``_aromatic_matchings`` gets a FAIL-CLOSED CHARGE WHITELIST admitting EXACTLY the
  cationic ring N (``charge > 0 and element == "N"``) as a pi-ACCEPTOR -- its lone pair went into the
  N-H / N-substituent bond, so it takes one ring double isoelectronically with pyridine's acceptor N (the class
  R40 validated 0-mislabel vs RDKit).  So the aromatic spelling kekulises to the SAME Kekulé structure as the
  explicit form, and the R40 ``_cip_mancude`` cationic-N path (which re-applies its OWN ``[1,1,2]`` charge gate,
  a defence-in-depth) then names it.  EVERY other charged aromatic atom fails CLOSED, loudly (a cationic CHALCOGEN
  O+/S+ -- the dalembert-proven RDKit-divergent class that would otherwise land in the O/S donor branch and
  silently mis-kekulise on an even acceptor count; an anion; an exotic charge).

* ALSO FIXED (representation invariance, the R41-exposed false-split): admitting the charged aromatic spelling
  reached a LATENT bug in the resonance canonicaliser.  ``_build_molecule`` / ``_isotopic_identity`` /
  ``_kekulize_in_place`` used a two-branch placement: an EXPLICIT structure ran the global
  ``_min_constitution_placement``, but when SOME bonds were aromatic-FLAGGED it canonicalised only those and left
  an explicit ring at its AUTHORED Kekulé placement.  A molecule mixing an aromatic ring with an explicit-Kekulé
  CHARGED ring (e.g. ``O[C@H](c1ccncc1)C1=CC=CC=[N+]1C``) therefore got a DIFFERENT canonical digest than its
  fully-aromatic or fully-explicit spelling -- ONE species, TWO identities.  Neutral molecules dodged it (a
  symmetric phenyl's placement is trivial, pyridine's is forced), so it was latent until the charged ring made a
  non-trivial explicit placement reachable beside an aromatic ring.  All three functions now route through ONE
  shared ``_canonical_kekule_orders`` (kekulise flagged bonds to any matching, then place the WHOLE pi system),
  so constitution, isotope key and configuration commit to the IDENTICAL Kekulé structure -- byte-identical for
  every neutral molecule, and unifying the charged aromatic/explicit/mixed spellings.

``validate()`` / ``content_hash()`` / ``_assert_representation_invariance()`` are RDKit-FREE (committed baseline).
``_rdkit_cross_check()`` is a gated dev-venv oracle; the frozen RDKit references were blessed against RDKit
2026.03.6.  Re-run ``python -m experiments.cip_charge_aware_kekulizer_probe`` after an intentional change and set
``FROZEN_HASH`` to the printed value.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.smiles import (SmilesError, canonical_digest, cip_labels, cip_labels_by_atom, parse_smiles,
                              _parse_skeleton_stereo)

FROZEN_HASH = "aac82881274d1c2585e30b173b23bf1ae9c266610273709412c2aab45138e792"

#: (aromatic SMILES, explicit-Kekulé twin, blessed repo per-atom map, blessed RDKit per-atom map, category, note).
#: category: "consumer" -- a charged AROMATIC spelling that WALLED before R41, now NAMES and unifies with its
#:                         explicit twin (repo == RDKit == the R40 explicit label, digest(arom) == digest(explicit));
#:           "regress"  -- a NEUTRAL molecule, byte-identical digest before and after (no-regression anchor);
#:           "defer"    -- OUT OF SCOPE, fail-closed: repo RAISES (chalcogen cation / anion), RDKit names or rejects.
BATTERY = (
    # ---- BUILT: charged AROMATIC-spelling consumers (previously walled) now name + unify with explicit-Kekulé ----
    ("C[C@H](O)c1cccc[n+]1C", "C[C@H](O)C1=CC=CC=[N+]1C", {1: "S"}, {1: "S"}, "consumer",
     "N-methylpyridinium carbinol (aromatic spelling)"),
    ("C[C@@H](O)c1cccc[n+]1C", "C[C@@H](O)C1=CC=CC=[N+]1C", {1: "R"}, {1: "R"}, "consumer",
     "enantiomer: label flips"),
    ("C[C@H](O)c1cc[nH+]cc1", "C[C@H](O)C1=CC=[NH+]C=C1", {1: "S"}, {1: "S"}, "consumer",
     "protonated pyridinium (N-H), the physiological-pH form (aromatic spelling)"),
    ("C[C@@H](O)c1scc[n+]1C", "C[C@@H](O)C1=[N+](C)C=CS1", {1: "R"}, {1: "R"}, "consumer",
     "thiazolium carbinol (thiamine-family motif), aromatic spelling: N+ acceptor + S spectator"),
    ("C[C@H](O)c1[nH]cc[n+]1C", "C[C@H](O)C1=[N+](C)C=CN1", {1: "S"}, {1: "S"}, "consumer",
     "imidazolium carbinol, aromatic spelling: cationic N+ acceptor + neutral pyrrole-N donor"),
    ("C[C@H](O)c1cc[n+]([O-])cc1", "C[C@H](O)C1=CC=[N+]([O-])C=C1", {1: "S"}, {1: "S"}, "consumer",
     "pyridine N-oxide carbinol, aromatic spelling: net-neutral zwitterion, cationic ring N"),
    ("C[n+]1ccccc1[C@H](O)c1ccccc1", "O[C@H](c1ccccc1)C1=CC=CC=[N+]1C", {7: "R"}, {7: "R"}, "consumer",
     "phenyl vs N-methylpyridinium: RING-vs-RING, the averaged fractions decide"),
    ("C[n+]1ccccc1[C@@H](O)c1ccccc1", "O[C@@H](c1ccccc1)C1=CC=CC=[N+]1C", {7: "S"}, {7: "S"}, "consumer",
     "enantiomer of the phenyl/pyridinium ring-vs-ring centre: label flips"),
    ("C[n+]1ccccc1[C@H](O)c1ccncc1", "O[C@H](c1ccncc1)C1=CC=CC=[N+]1C", {7: "R"}, {7: "R"}, "consumer",
     "pyridyl vs pyridinium: the MIXED aromatic/explicit spelling that exposed the R41 false-split; now unifies"),
    ("C[n+]1ccccc1[C@@H](O)c1nccs1", "O[C@@H](C1=CC=CC=[N+]1C)C1=NC=CS1", {7: "R"}, {7: "R"}, "consumer",
     "N-methylpyridinium vs THIAZOLE (dalembert ring-vs-heteroaromatic regime), aromatic spelling"),
    ("[O-][n+]1ccc([C@@H](O)c2nccs2)cc1", "O[C@@H](C1=CC=[N+]([O-])C=C1)C1=NC=CS1", {5: "R"}, {5: "R"}, "consumer",
     "pyridine N-oxide vs THIAZOLE, aromatic spelling: cationic ring-vs-heteroaromatic"),
    ("CC(=O)O[C@@H](C)c1cccc[n+]1C", "CC(=O)O[C@@H](C)C1=CC=CC=[N+]1C", {4: "S"}, {4: "S"}, "consumer",
     "1-(pyridinium-2-yl)ethyl acetate, aromatic spelling: an ester O-ligand vs the charged ring"),
    # ---- REGRESSION: neutral molecules, byte-identical digest + CIP before and after (aromatic path untouched) ----
    ("c1ccccc1", "C1=CC=CC=C1", {}, {}, "regress", "benzene"),
    ("c1ccncc1", "C1=CC=NC=C1", {}, {}, "regress", "pyridine (acceptor N)"),
    ("c1ccc2ccccc2c1", "C1=CC2=CC=CC=C2C=C1", {}, {}, "regress", "naphthalene (the SPLIT-KEKULE red-team anchor)"),
    ("c1cc[nH]c1", "C1=CC=CN1", {}, {}, "regress", "pyrrole (donor N)"),
    ("c1ccoc1", "C1=CC=CO1", {}, {}, "regress", "furan (donor O)"),
    ("c1ccsc1", "C1=CC=CS1", {}, {}, "regress", "thiophene (donor S)"),
    ("O[C@H](c1ccccc1)c1ccncc1", "O[C@H](C1=CC=CC=C1)C1=CC=NC=C1", {1: "R"}, {1: "R"}, "regress",
     "phenyl-vs-pyridyl carbinol: NEUTRAL mancude AVERAGING path, untouched"),
    # ---- DEFERRED, fail-closed: repo RAISES (never a silent label / structure), RDKit may name or reject ----
    ("C[C@H](O)c1cccc[o+]1", None, "raise", {1: "S"}, "defer",
     "pyrylium AROMATIC (cationic O): the dalembert-divergent chalcogen class -> structural raise, never the "
     "silent O-donor mis-kekulisation an even acceptor count would otherwise allow"),
    ("C[C@@H](O)c1cccc[s+]1", None, "raise", {1: "R"}, "defer",
     "thiopyrylium AROMATIC (cationic S): same chalcogen-cation class -> raise"),
    ("C[C@H](O)c1ccc[cH-]1", None, "raise", {1: "S"}, "defer",
     "cyclopentadienide AROMATIC (anionic C): no validated anion branch -> raise"),
    ("O[C@H](c1ccccc1)c1ccc[n-]c1", None, "raise", {1: "R"}, "defer",
     "anionic ring N (deprotonated pyrrolide-type): no validated anion branch -> raise"),
    # R41-REVIEW TIGHTENING (dalembert/evil-morty/birdperson: the pre-tightening charge>0 whitelist over-reached
    # its charge==1/coordination-3 proof domain and silently NAMED these RDKit-INVALID inputs).  The differential
    # fuzzer is structurally blind to them (it samples only RDKit-VALID molecules), so they are pinned here: the
    # whitelist now admits only a formal +1 ring N of coordination 3, so an OVER-CHARGED / OVER-COORDINATED N
    # fails closed exactly as RDKit rejects the molecule (MolFromSmiles -> None).
    ("C[C@H](O)c1cccc[n+2]1C", None, "raise", {}, "defer",
     "OVER-CHARGED aromatic [n+2]: not a real aromatic valence, RDKit rejects -> we RAISE (never a silent label "
     "on a non-molecule)"),
    ("C[C@H](O)c1cccc[nH2+]1", None, "raise", {}, "defer",
     "OVER-COORDINATED aromatic [nH2+] (coordination 4): RDKit rejects -> we RAISE (fail-closed)"),
)

#: representation-invariance CLASSES: every spelling in a group is the SAME molecule, so our canonical digest AND
#: CIP-label multiset MUST be identical across the whole group (the R41 guarantee, generalised to mixed spellings).
_INVARIANCE_GROUPS = (
    ("N-methylpyridinium carbinol",
     ("C[C@H](O)c1cccc[n+]1C", "C[C@H](O)C1=CC=CC=[N+]1C", "C[C@H](O)C1=CC=CC=[N+]1C")),
    ("pyridyl-vs-pyridinium (mixed aromatic/explicit)",
     ("C[n+]1ccccc1[C@H](O)c1ccncc1", "O[C@H](c1ccncc1)C1=CC=CC=[N+]1C", "O[C@H](C1=CC=NC=C1)C1=CC=CC=[N+]1C")),
    ("naphthalene (SPLIT-KEKULE red-team, neutral)",
     ("c1ccc2ccccc2c1", "C1=CC2=CC=CC=C2C=C1", "c1ccc2c(c1)cccc2")),
    ("phenyl-vs-pyridyl carbinol (neutral averaging)",
     ("O[C@H](c1ccccc1)c1ccncc1", "O[C@H](C1=CC=CC=C1)c1ccncc1", "O[C@H](c1ccccc1)C1=CC=NC=C1")),
)


def _dg(smi: str) -> str:
    return canonical_digest(parse_smiles(smi).canonical())


def _payload() -> dict:
    """The namer's ACTUAL output over the battery + the digest-unification verdicts, RDKit-free, hashed for drift."""
    out: dict = {}
    for arom, expl, expected, _rd, category, _note in BATTERY:
        try:
            out[arom] = sorted(cip_labels_by_atom(arom).items())
        except SmilesError:
            out[arom] = "wall"
        if category in ("consumer", "regress"):
            out[f"unify:{arom}"] = (_dg(arom) == _dg(expl))
    for name, group in _INVARIANCE_GROUPS:
        out[f"inv:{name}"] = len({_dg(s) for s in group})
    return out


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True).encode()).hexdigest()


def _assert_representation_invariance() -> None:
    """RDKit-free: consumers name + unify with their explicit twin; invariance groups collapse to ONE identity;
    deferred classes fail CLOSED (raise), never a silent label."""
    for arom, expl, expected, _rd, category, note in BATTERY:
        if category == "defer":
            try:
                got = cip_labels_by_atom(arom)
                raise AssertionError(f"a deferred charged aromatic must RAISE, got {got}: {arom} [{note}]")
            except SmilesError:
                pass
            continue
        got = cip_labels_by_atom(arom)
        assert got == expected, f"per-atom drift on {arom}: {got} != {expected} [{note}]"
        assert cip_labels(arom) == tuple(sorted(expected.values())), f"cip_labels disagrees on {arom} [{note}]"
        # the R41 invariant: the aromatic spelling and its explicit-Kekulé twin are ONE identity
        assert _dg(arom) == _dg(expl), (
            f"REPRESENTATION SPLIT: aromatic and explicit spellings differ in identity: {arom} vs {expl} [{note}]"
        )
    for name, group in _INVARIANCE_GROUPS:
        digs = {_dg(s) for s in group}
        cips = {tuple(sorted(cip_labels_by_atom(s).values())) for s in group}
        assert len(digs) == 1, f"identity split in group {name!r}: {len(digs)} digests over {group}"
        assert len(cips) == 1, f"CIP split in group {name!r}: {cips} over {group}"


def validate() -> None:
    _assert_representation_invariance()


def _rdkit_cross_check() -> dict:
    """Gated dev oracle: 0 mislabels vs RDKit on the consumer slice; consumers unify aromatic<->explicit; deferred
    chalcogen/anion classes are confirmed to RAISE while RDKit names (honest incompleteness, not a non-centre)."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    compared = mismatches = consumers_named = unified = defers_confirmed = 0
    details: list[tuple] = []
    for arom, expl, expected, rd_expected, category, note in BATTERY:
        if category == "defer":
            try:
                cip_labels_by_atom(arom)
                details.append((arom, "DID NOT RAISE", note))
            except SmilesError:
                mol = Chem.MolFromSmiles(arom)
                if mol is not None:
                    rdCIPLabeler.AssignCIPLabels(mol)
                    rd = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
                    if rd:
                        defers_confirmed += 1        # RDKit names it -> our raise is honest incompleteness
            continue
        mol = Chem.MolFromSmiles(arom)
        if mol is None:
            details.append((arom, "rdkit parse fail", note))
            continue
        rdCIPLabeler.AssignCIPLabels(mol)
        rd = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
        rd_syms = {a.GetIdx(): a.GetSymbol() for a in mol.GetAtoms()}
        assert rd == rd_expected, f"RDKit drift on {arom}: {rd} != {rd_expected}"
        repo = cip_labels_by_atom(arom)
        repo_syms = {i: a.element for i, a in enumerate(_parse_skeleton_stereo(arom)[0])}
        idxs = set(repo) | set(rd)
        if any(repo_syms.get(i) != rd_syms.get(i) for i in idxs):
            details.append((arom, "index-map element mismatch", note))
            continue
        for i in set(repo) & set(rd):
            compared += 1
            if repo[i] != rd[i]:
                mismatches += 1
                details.append((arom, f"MISLABEL idx {i}: repo {repo[i]} != rd {rd[i]}", note))
        if category == "consumer":
            assert repo and repo == {i: rd[i] for i in repo}, f"consumer must match RDKit: {arom}"
            consumers_named += 1
            if _dg(arom) == _dg(expl):
                unified += 1
    return {
        "compared": compared,
        "mismatches": mismatches,
        "consumers_named": consumers_named,
        "consumers_unified_aromatic_vs_explicit": unified,
        "defers_confirmed": defers_confirmed,
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
