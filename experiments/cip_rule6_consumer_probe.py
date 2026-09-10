"""CIP-RULE6-CONSUMER-01: the VERIFIED DEFER of CIP Rule 6 (queue item 1).

Rule 6 -- the reference-dependent like/unlike sequence-rule tail that fires only AFTER target-relative Rules
4b/4c -- has NO reachable consumer in this codebase, so building it would be dead, mislabel-prone code.  This
probe is the committed EVIDENCE that a defer is the correct outcome this round, exactly the R32 Rule-1b /
R36 Rule-4b/4c precedent (``an-oracle-driven-existence-check-can-prove-a-defer``).  It is the strict SIBLING of
``cip_target_relative_rules_probe`` (the 4b/4c defer): Rule 6 sits STRICTLY DOWNSTREAM of 4b/4c, and the SAME
auxiliary-pool bottleneck that starves 4b/4c starves Rule 6 a fortiori.

The structure theorem (proved RDKit-free from repo output + the code path; adversarially reviewed):

1.  DOWNSTREAM (a SPEC-hierarchy fact) + THE ADMISSION CAP (the OPERATIVE code-level gate).  In the CIP
    *specification* hierarchy Rule 6 fires only on a pair that has already tied through Rules 1a-5 INCLUDING the
    target-relative Rules 4b/4c, itself a VERIFIED DEFER (R36).  But in the *code* there is no literal 4b / 4c / 6
    dispatch -- the reference-dependent discrimination is folded into ``_cip_compare_rules45`` (a Rule5New
    two-fixed-reference port, not a per-branch majority-vote 4b), so "downstream of 4b/4c" is a statement about
    the spec, not the executed path.  What actually gates reachability is the auxiliary-pool ADMISSION CAP
    (``smiles.py:1961-1964``): a pool larger than size 1 or a single R,S pair is REFUSED admission before any
    auxiliary comparison, and part (c) below verifies that cap BEHAVIOURALLY (the aux pass is never entered with
    ``|pool| > 2``).  This is the reachability argument that holds regardless of how the spec rules are numbered.

2.  THE SHARED BOTTLENECK.  Rule 6 discriminates a pair by the LIKE/UNLIKE relative pairing of AUXILIARY
    descriptors -- the same pool the bounded ROUND-35 Rule-4a/5 pass reads (``auxiliary = dict(labels_by_atom)``,
    ``smartchem/smiles.py:1957``).  That pool is admitted ONLY at size 1 or a single R,S pair
    (``smartchem/smiles.py:1961-1962``); a larger auxiliary system -- the first place a like/unlike PAIR
    distinction can even exist (you need >= two descriptor pairs to compare 'like' vs 'unlike') -- is REFUSED
    admission and defers before any auxiliary comparison.  Within the admitted <=2 pool, every pair that reaches
    ``_cip_compare_rules45`` is either resolved by revised Rule 5 (an ordinary +-1 Rule-4a distinction or a +-2
    pseudoasymmetry, ``smartchem/smiles.py:1649-1662``) or has an EMPTY effective pool and defers
    (``return None``, ``smartchem/smiles.py:1843-1844``).  Neither branch leaves a like/unlike residual for a
    Rule 6 to break: the resolved branch is already ordered, and the empty-pool branch has nothing to compare.

3.  NO REACHABLE TRIGGER (empirical).  Across the battery -- the shared empty-pool forcing class (repo DEFERS /
    RDKit names ``s,s`` by recursion), the non-empty-pool controls (revised Rule 5 NAMES the pseudoasymmetric
    centre, no Rule-6 residual), and the existence set (north-star achiral targets + fully-named real chiral
    drugs) -- NO centre reaches a state where only a like/unlike Rule-6 discriminator could name it.  The shipped
    namer has 0 mislabels vs RDKit ``rdCIPLabeler`` on everything it names; where it declines, RDKit's label is a
    pseudoasymmetric 4b/4c-class assignment, never a Rule-6-only tie.

A trigger requires FIRST admitting a larger auxiliary system AND building target-relative Rules 4b/4c to
populate and order it -- the deferred 4b/4c round.  Rule 6 unparks strictly after 4b/4c.  The build boundary and
the phased path live in ``docs/research/CIP_RULE6_CONSUMER_SCOPE_DECISION_v0.1.md``.

``validate()``, ``content_hash()`` and the structure-theorem assertion are RDKit-free (committed baseline).
``_rdkit_cross_check()`` is a gated development-oracle probe (dev venv only); the frozen RDKit references below
were BLESSED against RDKit 2026.03.6 at authoring time.  Re-run
``python -m experiments.cip_rule6_consumer_probe`` after an intentional change and set ``FROZEN_HASH`` to the
printed value.
"""
from __future__ import annotations

import hashlib
import json

from smartchem.smiles import _parse_skeleton_stereo, cip_labels, cip_labels_by_atom

FROZEN_HASH = "7be84bc8466f556e77f0bed0bbb1b12c533855026acf1cd6ec1603c8e36684a3"

#: (SMILES, blessed repo per-atom map, blessed RDKit per-atom map, category, note).
#: category: "forcing"  -- repo DEFERS (empty aux pool), RDKit names pseudoasymmetric; the shared 4b/4c+Rule-6 wall
#:           "rule5"    -- NON-empty aux pool, revised Rule 5 RESOLVES it (no Rule-6 residual left)
#:           "existence"-- no consumer: north-star achiral targets + fully-named real chiral drugs
BATTERY = (
    # --- the shared empty-pool forcing class.  Both centres unresolved by Rules 1a-3 -> aux pool empty ->
    #     the bounded 4a/5 pass is never admitted -> defers.  Rule 6 (which reads the SAME pool) is starved too.
    ("O[C@H]1CC[C@@H](C)CC1", {}, {1: "s", 4: "s"}, "forcing",
     "4-methylcyclohexan-1-ol: mutual pseudo, repo DEFERS / RDKit s,s"),
    ("C[C@H]1CC[C@@H](C)CC1", {}, {1: "s", 4: "s"}, "forcing",
     "1,4-dimethylcyclohexane: mutual pseudo, repo DEFERS / RDKit s,s"),
    # --- NON-empty aux pool: revised Rule 5 (the +-2 pseudoasymmetry) RESOLVES the centre.  Proof the aux
    #     machinery names when seeded, and that the resolved case leaves NO like/unlike residual for a Rule 6.
    ("O[C@H]1[C@H](O)[C@@H](O)CCC1", {1: "R", 4: "S", 2: "r"}, {1: "R", 2: "r", 4: "S"}, "rule5",
     "ring pseudo, non-empty pool -> revised Rule 5 names the r (no Rule-6 residual)"),
    ("OC(=O)[C@@H](O)[C@H](O)[C@@H](O)C(=O)O", {3: "S", 7: "R", 5: "s"}, {3: "S", 5: "s", 7: "R"}, "rule5",
     "trihydroxyglutaric: non-empty pool -> revised Rule 5 names the s (no Rule-6 residual)"),
    # --- EXISTENCE: no in-scope consumer.  North-star targets stereocenter-free; real chiral drugs fully named.
    ("CC(=O)Nc1ccc(O)cc1", {}, {}, "existence", "paracetamol (north star): achiral, no centres"),
    ("CC(=O)Oc1ccccc1C(=O)O", {}, {}, "existence", "aspirin (north star): achiral"),
    ("CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O", {3: "S", 6: "R", 9: "R"}, {3: "S", 6: "R", 9: "R"}, "existence",
     "menthol: fully named by the shipped rules"),
    ("OC(=O)[C@@H](O)[C@H](O)C(=O)O", {3: "S", 5: "S"}, {3: "S", 5: "S"}, "existence",
     "(2S,3S)-tartaric: fully named"),
    ("OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O",
     {2: "R", 4: "R", 6: "R", 8: "S", 10: "S"}, {2: "R", 4: "R", 6: "R", 8: "S", 10: "S"}, "existence",
     "glucopyranose: five centres, all named"),
)


def _payload() -> dict:
    """The namer's ACTUAL per-atom output over the battery -- RDKit-free, deterministic, hashed for drift."""
    return {smi: sorted(cip_labels_by_atom(smi).items()) for smi, *_ in BATTERY}


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_payload(), sort_keys=True).encode()).hexdigest()


def _assert_structure_theorem() -> None:
    """RDKit-free proof, from repo output + the code path, that Rule 6 has no reachable trigger.

    * the shared empty-pool forcing class defers ALL its centres (the pool Rule 6 would read is empty);
    * a NON-empty aux pool is RESOLVED by revised Rule 5 (the +-2 pseudoasymmetry), leaving no like/unlike
      residual -- so no admitted-pool pair reaches a Rule-6-only tie either;
    * the bounded admission cap is size 1 or a single R,S pair, so a larger auxiliary system (the first place a
      like/unlike PAIR distinction can exist) never enters the aux pass at all.
    """
    # (a) the empty-pool wall: both centres marked, none named -> nothing seeds the pool Rule 6 consumes.
    forcing = "O[C@H]1CC[C@@H](C)CC1"
    marked = [i for i, a in enumerate(_parse_skeleton_stereo(forcing)[0]) if a.chirality]
    assert len(marked) == 2, f"the forcing target must carry two marked centres, got {marked}"
    assert cip_labels_by_atom(forcing) == {}, "the empty-pool class must DEFER all centres"
    # (b) a non-empty pool is resolved by revised Rule 5 -> no Rule-6 residual.
    assert cip_labels_by_atom("O[C@H]1[C@H](O)[C@@H](O)CCC1") == {1: "R", 4: "S", 2: "r"}, (
        "revised Rule 5 must NAME the pseudoasymmetric centre when the aux pool is non-empty"
    )
    # (c) the admission cap, checked BEHAVIOURALLY -- NOT by grepping the source of the function it audits (the
    #     `checks-derived-from-their-own-subject` / `derived-menu-without-a-check` hazard dalembert flagged: a
    #     source grep false-alarms on a benign refactor like `{"S","R"}` and can be defeated by editing the string
    #     to match a weakened gate).  Wrap the aux-pass ENTRY and assert it is NEVER admitted an auxiliary pool
    #     larger than the <=2 cap (smiles.py:1961-1964), across a battery that includes 3- and 5-stereocentre
    #     molecules.  A genuine WEAKENING of the gate (admitting |pool|>2) trips this; a spelling refactor does not.
    from smartchem import smiles as _smiles

    seen_pool_sizes: list[int] = []
    original = _smiles._cip_ranks_with_aux

    def _spy(*args, **kwargs):
        auxiliary = kwargs["auxiliary"] if "auxiliary" in kwargs else args[8]
        seen_pool_sizes.append(len(auxiliary))
        return original(*args, **kwargs)

    _smiles._cip_ranks_with_aux = _spy
    try:
        for smi, *_ in BATTERY:
            cip_labels_by_atom(smi)
    finally:
        _smiles._cip_ranks_with_aux = original
    assert seen_pool_sizes, "non-vacuity: the aux pass must be entered at least once, or the cap check is empty"
    assert all(n <= 2 for n in seen_pool_sizes), (
        f"the aux pass must never be admitted a pool > 2 (the admission cap); saw {seen_pool_sizes}"
    )


def validate() -> None:
    """RDKit-free: the namer still produces the blessed per-atom maps; the empty-pool class defers, controls name."""
    for smi, expected, _rd, category, note in BATTERY:
        got = cip_labels_by_atom(smi)
        assert got == expected, f"per-atom drift on {smi}: {got} != {expected} [{note}]"
        assert cip_labels(smi) == tuple(sorted(expected.values())), f"cip_labels disagrees on {smi} [{note}]"
        if category == "forcing":
            assert got == {}, f"a forcing-class (empty-pool) centre must DEFER, not name: {smi} -> {got}"
        if category == "rule5":
            assert got != {}, f"a non-empty-pool centre must be NAMED by revised Rule 5: {smi} -> {got}"
    _assert_structure_theorem()


def _rdkit_cross_check() -> dict:
    """Gated development oracle: 0 mislabels vs RDKit; the declines are 4b/4c-class, never Rule-6-only ties."""
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")

    compared = skipped = mismatches = forcing_confirmed = 0
    details: list[tuple] = []
    for smi, expected, rd_expected, category, note in BATTERY:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            skipped += 1
            continue
        rdCIPLabeler.AssignCIPLabels(mol)
        rd = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
        rd_syms = {a.GetIdx(): a.GetSymbol() for a in mol.GetAtoms()}
        repo = cip_labels_by_atom(smi)
        repo_syms = {i: a.element for i, a in enumerate(_parse_skeleton_stereo(smi)[0])}
        # element-verified mapping: repo index == rdkit index here, checked, never trusted blindly
        idxs = set(repo) | set(rd)
        if any(repo_syms.get(i) != rd_syms.get(i) for i in idxs):
            skipped += 1
            details.append((smi, "index-map element mismatch", note))
            continue
        assert rd == rd_expected, f"RDKit drift on {smi}: {rd} != {rd_expected}"
        # a MISLABEL is a centre BOTH name but disagree on
        for i in set(repo) & set(rd):
            compared += 1
            if repo[i] != rd[i]:
                mismatches += 1
                details.append((smi, f"MISLABEL idx {i}: repo {repo[i]} != rd {rd[i]}", note))
        if category == "forcing":
            # repo declines (empty), RDKit names a PSEUDOASYMMETRIC (lowercase) 4b/4c-class label -> not Rule-6
            assert repo == {}, f"forcing class must decline: {smi} -> {repo}"
            assert rd and all(code.islower() for code in rd.values()), (
                f"the decline must be a pseudoasymmetric 4b/4c-class case, not a Rule-6-only tie: {smi} -> {rd}"
            )
            forcing_confirmed += 1
    return {
        "compared": compared,
        "skipped": skipped,
        "mismatches": mismatches,
        "forcing_confirmed": forcing_confirmed,
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
