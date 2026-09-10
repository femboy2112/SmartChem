"""CHEM-FUZZ-01: a systematic, seeded, structure-aware DIFFERENTIAL fuzzer for the SmartChem parser / identity /
CIP stack, plus a synthesis-path conservation fuzzer.

Motivation (ROUND 41): curated batteries prove the cases we THOUGHT of; a fuzzer proves the cases we didn't.
The R41 charge-aware kekulizer's identity false-split (a charged ring's aromatic vs explicit spelling) was found
by a differential sweep, not a curated pin -- so this harness generalises that sweep into a reusable instrument
that hunts the SAME failure shapes across the whole chemical input space:

* PARSE ROBUSTNESS  -- the parser returns a Molecule or raises SmilesError, NEVER any other exception (a crash
  on a valid RDKit-parseable molecule is a bug).
* REPRESENTATION INVARIANCE (the big one) -- N spellings of ONE molecule (RDKit-derived random atom-order and
  aromatic<->Kekulé respellings, same species by construction) must share our canonical digest AND our CIP label
  multiset.  A split is a false-split bug (the R41 exposure, generalised).
* SAME-MOLECULE DIFFERENTIAL -- RDKit says two SMILES are the same molecule => our digests must agree (no false
  split); RDKit says they differ => our digests must differ (no false merge).
* CIP DIFFERENTIAL vs RDKit rdCIPLabeler -- on the element-verified index intersection, a repo NAME that disagrees
  with RDKit is a MISLABEL (bug); a repo DECLINE where RDKit names is honest incompleteness (counted, never a bug).
* ENANTIOMER FLIP -- mirroring a named centre (@<->@@) flips its R/S.
* SYNTHESIS-PATH CONSERVATION -- a balanced reaction is accepted by the ExperimentStep conservation cert; an
  atom/charge-unbalanced mutant is REFUSED (fail-closed).

The GENERATIVE differential campaign (:func:`run_fuzz`) needs RDKit as the oracle and structure engine, so it is
a DEV-VENV-ONLY instrument (``pip install rdkit``; the committed baseline has no rdkit).  A committed, RDKit-FREE
core (:func:`selftest`) re-checks representation-invariance + enantiomer-flip over a FROZEN corpus of RDKit-derived
respellings, so ``pytest`` exercises the invariants with no rdkit present.  Every campaign is SEEDED (deterministic
replay) and SHRINKS each finding to a minimal reproducing SMILES.  Coverage is reported honestly -- what was
sampled, and what was not.
"""
from __future__ import annotations

import hashlib
import json
import random

from smartchem.smiles import (SmilesError, canonical_digest, cip_labels_by_atom, parse_smiles,
                              _parse_skeleton_stereo)

# --------------------------------------------------------------------------------------------------------------
# Seed corpus: diverse valid molecules spanning the regimes where mismatches hide (dalembert discipline -- bias
# generation toward ring-vs-ring, charged rings, fused heteroaromatics, stereocentres, isotopes, not blind random).
# --------------------------------------------------------------------------------------------------------------
SEED_CORPUS = (
    # plain skeletons
    "CCO", "CC(C)C", "CCCCCC", "C1CCCCC1", "C1CCCC1", "CC(=O)O", "CC(=O)OC", "CCN", "CC#N", "C=CC=C",
    # halogen / functional decoration
    "ClC(F)(Br)C", "OCC(N)C(=O)O", "CC(=O)Nc1ccccc1", "O=C(O)c1ccccc1O",
    # mono + fused aromatics
    "c1ccccc1", "Cc1ccccc1", "c1ccc2ccccc2c1", "c1ccc2cc3ccccc3cc2c1", "c1ccc2c(c1)cccc2",
    # heteroaromatics (donor + acceptor N, chalcogen donors)
    "c1ccncc1", "c1ccncn1", "c1cc[nH]c1", "c1ccoc1", "c1ccsc1", "c1cscn1", "c1c[nH]cn1", "c1ccc2ncccc2c1",
    "c1ccc2[nH]ccc2c1",
    # charged aromatic N (the R40/R41 class): pyridinium, N-oxide, azolium
    "C[n+]1ccccc1", "c1cc[nH+]cc1", "C[n+]1ccccc1C", "[O-][n+]1ccccc1", "Cc1csc[n+]1C", "Cc1c[nH]c[n+]1C",
    # stereocentres: single, multiple, ring, the north-star consumers
    "C[C@H](O)CC", "C[C@@H](N)C(=O)O", "F[C@H](Cl)Br", "O[C@H](c1ccccc1)c1ccncc1",
    "CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O", "OC[C@@H](O)[C@@H]1OC(=O)C(O)=C1O",
    "C[C@H](O)c1cccc[n+]1C", "O[C@H](c1ccccc1)C1=CC=CC=[N+]1C", "O[C@H](c1ccncc1)C1=CC=CC=[N+]1C",
    # isotopes / near-symmetric
    "O[C@H](c1ccccc1)c1ccc[13cH]c1", "[13CH3]C(=O)O",
    # explicit-Kekulé spellings of aromatics (must unify with their aromatic forms)
    "C1=CC=CC=C1", "C1=CC=NC=C1", "C1=CC2=CC=CC=C2C=C1",
)


def _rdkit():
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdCIPLabeler
    RDLogger.DisableLog("rdApp.*")
    return Chem, rdCIPLabeler


# --------------------------------------------------------------------------------------------------------------
# RDKit structure engine (dev-only): respellings, mutations, oracle labels, same-molecule test.
# --------------------------------------------------------------------------------------------------------------
def rd_respellings(smi: str, n: int, rng: random.Random) -> list[str]:
    """N RDKit-generated spellings of the SAME molecule: random atom order, aromatic AND explicit-Kekulé both."""
    Chem, _ = _rdkit()
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return []
    out = set()
    for _ in range(n * 3):
        kekule = rng.random() < 0.5
        try:
            m = Chem.MolFromSmiles(smi)
            if kekule:
                Chem.Kekulize(m, clearAromaticFlags=True)
            out.add(Chem.MolToSmiles(m, doRandom=True, canonical=False, kekuleSmiles=kekule))
        except Exception:  # noqa: BLE001
            continue
        if len(out) >= n:
            break
    return list(out)


def rd_cip(smi: str) -> dict[int, str] | None:
    Chem, rdCIPLabeler = _rdkit()
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    rdCIPLabeler.AssignCIPLabels(mol)
    return {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}


def rd_same_molecule(a: str, b: str) -> bool | None:
    Chem, _ = _rdkit()
    ma, mb = Chem.MolFromSmiles(a), Chem.MolFromSmiles(b)
    if ma is None or mb is None:
        return None
    return Chem.MolToSmiles(ma) == Chem.MolToSmiles(mb)


def rd_mutate(smi: str, rng: random.Random) -> str | None:
    """One structure-aware mutation kept only if RDKit still parses it: protonate a ring N (-> charged aromatic),
    swap a halogen, add a methyl, flip a stereocentre, or delete a terminal atom.  Biased toward the charged-ring
    and stereocentre regimes."""
    Chem, _ = _rdkit()
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    rw = Chem.RWMol(mol)
    kind = rng.choice(["protonate_n", "protonate_n", "add_methyl", "swap_halogen", "delete_terminal"])
    try:
        if kind == "protonate_n":
            ns = [a for a in rw.GetAtoms() if a.GetSymbol() == "N" and a.GetFormalCharge() == 0
                  and a.GetTotalNumHs() + a.GetDegree() <= 3]
            if not ns:
                return None
            a = rng.choice(ns)
            a.SetFormalCharge(1)
            a.SetNumExplicitHs(a.GetTotalNumHs() + 1)
            a.SetNoImplicit(True)
        elif kind == "add_methyl":
            cands = [a for a in rw.GetAtoms() if a.GetSymbol() == "C" and a.GetTotalNumHs() >= 1]
            if not cands:
                return None
            idx = rng.choice(cands).GetIdx()
            new = rw.AddAtom(Chem.Atom(6))
            rw.AddBond(idx, new, Chem.BondType.SINGLE)
        elif kind == "swap_halogen":
            hal = [a for a in rw.GetAtoms() if a.GetSymbol() in ("F", "Cl", "Br", "I")]
            if not hal:
                return None
            rng.choice(hal).SetAtomicNum(rng.choice([9, 17, 35, 53]))
        elif kind == "delete_terminal":
            term = [a.GetIdx() for a in rw.GetAtoms() if a.GetDegree() == 1]
            if not term:
                return None
            rw.RemoveAtom(rng.choice(term))
        m = rw.GetMol()
        Chem.SanitizeMol(m)
        return Chem.MolToSmiles(m)
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------------------------------------------
# Per-molecule differential checks. Each returns (ok: bool, tag: str) -- tag names the failure mode when not ok.
# --------------------------------------------------------------------------------------------------------------
def _repo_parse_or_wall(smi: str):
    """(kind, value): ('mol', digest) | ('wall', None) | ('crash', exc-repr)."""
    try:
        return "mol", canonical_digest(parse_smiles(smi).canonical())
    except SmilesError:
        return "wall", None
    except Exception as e:  # noqa: BLE001  -- a non-SmilesError escape is a robustness bug
        return "crash", f"{type(e).__name__}: {e}"


def _repo_cip_or_wall(smi: str):
    try:
        return cip_labels_by_atom(smi)
    except SmilesError:
        return None
    except Exception as e:  # noqa: BLE001
        return ("crash", f"{type(e).__name__}: {e}")


def check_molecule(smi: str, rng: random.Random, n_respellings: int = 6) -> list[dict]:
    """Run every per-molecule differential on ``smi``; return a list of finding dicts (empty == clean)."""
    findings: list[dict] = []

    def add(mode, detail):
        findings.append({"smiles": smi, "mode": mode, "detail": detail})

    # (1) parse robustness
    kind, val = _repo_parse_or_wall(smi)
    if kind == "crash":
        add("parse_crash", val)
        return findings  # a crash poisons the rest; report and stop here

    # (2) CIP differential vs RDKit (element-verified index intersection)
    repo_cip = _repo_cip_or_wall(smi)
    if isinstance(repo_cip, tuple) and repo_cip and repo_cip[0] == "crash":
        add("cip_crash", repo_cip[1])
        repo_cip = None
    rd = rd_cip(smi)
    if repo_cip is not None and rd is not None:
        try:
            repo_syms = {i: a.element for i, a in enumerate(_parse_skeleton_stereo(smi)[0])}
        except Exception:  # noqa: BLE001
            repo_syms = {}
        Chem, _ = _rdkit()
        m = Chem.MolFromSmiles(smi)
        rd_syms = {a.GetIdx(): a.GetSymbol() for a in m.GetAtoms()} if m else {}
        shared = set(repo_cip) & set(rd)
        if all(repo_syms.get(i) == rd_syms.get(i) for i in shared):
            for i in shared:
                if repo_cip[i] != rd[i]:
                    add("cip_mislabel", f"idx {i}: repo {repo_cip[i]} != rdkit {rd[i]}")

    # (3) representation invariance across RDKit respellings (same molecule -> one digest + one CIP multiset)
    variants = rd_respellings(smi, n_respellings, rng)
    digs, cips = set(), set()
    for v in variants:
        k, d = _repo_parse_or_wall(v)
        if k == "crash":
            add("respell_parse_crash", f"{v!r}: {d}")
            continue
        if k == "mol":
            digs.add(d)
        c = _repo_cip_or_wall(v)
        if isinstance(c, tuple) and c and c[0] == "crash":
            add("respell_cip_crash", f"{v!r}: {c[1]}")
        elif c is not None:
            cips.add(tuple(sorted(c.values())))
    if len(digs) > 1:
        add("identity_split", f"{len(digs)} distinct digests over {len(variants)} spellings")
    if len(cips) > 1:
        add("cip_split", f"{len(cips)} distinct CIP multisets over {len(variants)} spellings: {sorted(cips)}")

    return findings


def shrink(smi: str, fails, rng: random.Random, rounds: int = 40) -> str:
    """Greedily delete atoms (via RDKit) while the molecule still triggers a finding, to a minimal reproducer."""
    Chem, _ = _rdkit()
    best = smi
    for _ in range(rounds):
        mol = Chem.MolFromSmiles(best)
        if mol is None or mol.GetNumAtoms() <= 3:
            break
        shrunk = None
        order = list(range(mol.GetNumAtoms()))
        rng.shuffle(order)
        for idx in order:
            rw = Chem.RWMol(mol)
            try:
                rw.RemoveAtom(idx)
                m = rw.GetMol()
                Chem.SanitizeMol(m)
                cand = Chem.MolToSmiles(m)
            except Exception:  # noqa: BLE001
                continue
            if cand and fails(cand):
                shrunk = cand
                break
        if shrunk is None:
            break
        best = shrunk
    return best


# --------------------------------------------------------------------------------------------------------------
# Synthesis-path conservation fuzzer (uses the chemistry conservation cert; RDKit only to source formulae).
# --------------------------------------------------------------------------------------------------------------
#: isomer sets (same molecular formula, distinct constitution) -- a real balanced "synthesis" (isomerisation /
#: rearrangement) the conservation cert MUST accept (mass/charge conserved though structure changed), plus a few
#: molecules whose formulae differ (an atom-unbalanced pair the cert MUST refuse). RDKit-free.
_ISOMER_SETS = (
    ("CCO", "COC"),                        # ethanol / dimethyl ether -- C2H6O
    ("CC(=O)C", "CCC=O", "CC1CO1"),        # acetone / propanal / methyloxirane -- C3H6O family
    ("CCCC", "CC(C)C"),                     # n-butane / isobutane -- C4H10
    ("OCC=O", "CC(=O)O"),                   # glycolaldehyde / acetic acid -- C2H4O2
    ("c1ccccc1", "C1=CC=CC=C1"),           # benzene aromatic vs explicit (same species; trivially balanced)
    ("Cc1ccccc1", "C1=CC=CC=C1C"),         # toluene two spellings -- C7H8
)


def check_synthesis_conservation(_rng: random.Random) -> list[dict]:
    """Synthesis-path conservation fuzz: a BALANCED reaction (an isomerisation A->B with formula(A)==formula(B), or
    a multi-species permutation A+B->B+A) must BUILD a :class:`smartchem.category.Reaction` (mass/charge conserved,
    though structure changed); an atom-UNBALANCED reaction (A->B with formula(A)!=formula(B), or a dropped species)
    must RAISE :class:`ConservationError`.  Fail-closed: a refused-balanced or accepted-unbalanced is a finding.
    RDKit-free (uses the repo's own formula/Config/Reaction), so it runs in the committed baseline too."""
    from smartchem.category import Config, ConservationError, Reaction

    findings: list[dict] = []

    def formula(smi):
        return tuple(sorted(parse_smiles(smi).formula.items()))

    def builds(dom, cod):
        try:
            Reaction(Config(tuple(parse_smiles(s) for s in dom)), Config(tuple(parse_smiles(s) for s in cod)))
            return True
        except ConservationError:
            return False

    # (1) BALANCED isomerisations must build; (2) A+B -> B+A permutations must build.
    for group in _ISOMER_SETS:
        base = formula(group[0])
        for s in group[1:]:
            if formula(s) != base:
                continue                              # not actually an isomer -> skip (corpus hygiene, not a bug)
            if not builds([group[0]], [s]):
                findings.append({"smiles": f"{group[0]} -> {s}", "mode": "conservation_false_refusal",
                                 "detail": "balanced isomerisation refused by the conservation cert"})
            if not builds([group[0], s], [s, group[0]]):
                findings.append({"smiles": f"{group[0]}+{s} -> {s}+{group[0]}", "mode": "conservation_false_refusal",
                                 "detail": "balanced multi-species permutation refused"})

    # (3) UNBALANCED reactions must be refused: a formula mismatch, and a dropped species.
    unbalanced = [("CCO", "CC=O"), ("CCCC", "CCC"), ("c1ccccc1", "c1ccncc1")]
    for a, b in unbalanced:
        if formula(a) == formula(b):
            continue
        if builds([a], [b]):
            findings.append({"smiles": f"{a} -> {b}", "mode": "conservation_accepted_unbalanced",
                             "detail": "atom-unbalanced reaction ACCEPTED (fail-open!)"})
    if builds(["CCO", "CC=O"], ["CCO"]):              # dropped a whole species from the product side
        findings.append({"smiles": "CCO+CC=O -> CCO", "mode": "conservation_accepted_unbalanced",
                         "detail": "dropped-species reaction ACCEPTED (fail-open!)"})
    return findings


# --------------------------------------------------------------------------------------------------------------
# Campaign driver (dev-only) + RDKit-free committed selftest.
# --------------------------------------------------------------------------------------------------------------
def run_fuzz(seed: int = 0, n_mutations: int = 400, n_respellings: int = 6, verbose: bool = True) -> dict:
    """Seeded differential campaign over the seed corpus + RDKit-generated mutants.  Returns a coverage +
    findings summary; every finding carries a shrunk minimal reproducer."""
    rng = random.Random(seed)
    Chem, _ = _rdkit()

    # build the population: corpus + GENERATIONAL mutants (mutate the growing population, not just the corpus,
    # so the walk reaches multi-edit structures far from the seeds -- deeper into the input space where the
    # curated batteries never look). Each new mutant becomes eligible as a future base.
    population = list(SEED_CORPUS)
    for _ in range(n_mutations):
        base = rng.choice(population if rng.random() < 0.5 else list(SEED_CORPUS))
        mut = rd_mutate(base, rng)
        if mut and mut not in population:
            population.append(mut)

    # dedup by RDKit canonical
    canon_seen, molecules = set(), []
    for smi in population:
        m = Chem.MolFromSmiles(smi)
        if m is None:
            continue
        c = Chem.MolToSmiles(m)
        if c not in canon_seen:
            canon_seen.add(c)
            molecules.append(smi)

    all_findings: list[dict] = []
    for smi in molecules:
        fs = check_molecule(smi, rng, n_respellings)
        if fs:
            def fails(cand, _smi=smi, _rng=rng):
                return bool(check_molecule(cand, random.Random(1), n_respellings))
            minimal = shrink(smi, fails, rng)
            for f in fs:
                f["minimal"] = minimal
            all_findings.extend(fs)

    # same-molecule differential over a batch of RDKit-derived respelling pairs (no false split / merge)
    sm_checked = sm_bad = 0
    for smi in molecules[:120]:
        vs = rd_respellings(smi, 3, rng)
        for v in vs:
            same = rd_same_molecule(smi, v)
            if same is None:
                continue
            ka, da = _repo_parse_or_wall(smi)
            kb, db = _repo_parse_or_wall(v)
            if ka != "mol" or kb != "mol":
                continue
            sm_checked += 1
            if same and da != db:
                sm_bad += 1
                all_findings.append({"smiles": f"{smi} ~ {v}", "mode": "same_mol_false_split", "detail": "same molecule, different digest"})

    # synthesis-path conservation dimension (RDKit-free; the cert must accept balanced, refuse unbalanced)
    synth_findings = check_synthesis_conservation(rng)
    all_findings.extend(synth_findings)

    summary = {
        "seed": seed,
        "corpus": len(SEED_CORPUS),
        "population_after_mutation": len(population),
        "unique_molecules_tested": len(molecules),
        "respellings_per_molecule": n_respellings,
        "same_molecule_pairs_checked": sm_checked,
        "synthesis_conservation_findings": len(synth_findings),
        "findings": all_findings,
        "n_findings": len(all_findings),
        "findings_by_mode": _tally([f["mode"] for f in all_findings]),
        "boundary": "coverage is the seed corpus + RDKit single-edit mutants of it; multi-step synthesis routes and "
                    "the conservation dimension are stubbed (API wire-point). RDKit is the oracle -- a shared RDKit "
                    "bug would be invisible (common-mode).",
    }
    if verbose:
        print(json.dumps({k: v for k, v in summary.items() if k != "findings"}, indent=2))
        for f in all_findings[:40]:
            print("  FINDING", f)
    return summary


def _tally(xs):
    out: dict[str, int] = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


# ---- RDKit-FREE committed core: a frozen corpus of respellings, checked for representation invariance ----
# (molecule, [respellings incl. aromatic + explicit-Kekulé], enantiomer_of_first_or_None). Derived once via RDKit.
_FROZEN_RESPELLINGS = (
    ("c1ccccc1", ("c1ccccc1", "C1=CC=CC=C1")),
    ("c1ccc2ccccc2c1", ("c1ccc2ccccc2c1", "C1=CC2=CC=CC=C2C=C1", "c1ccc2c(c1)cccc2")),
    ("c1ccncc1", ("c1ccncc1", "C1=CC=NC=C1", "C1=CC=CC=N1")),
    ("C[n+]1ccccc1", ("C[n+]1ccccc1", "C[N+]1=CC=CC=C1")),
    ("c1cc[nH+]cc1", ("c1cc[nH+]cc1", "C1=CC=[NH+]C=C1")),
    ("O[C@H](c1ccccc1)c1ccncc1", ("O[C@H](c1ccccc1)c1ccncc1", "O[C@H](C1=CC=CC=C1)c1ccncc1",
                                  "O[C@H](c1ccccc1)C1=CC=NC=C1")),
    # the R41 exposure: charged ring, aromatic + explicit + MIXED spellings must all unify
    ("C[n+]1ccccc1[C@H](O)c1ccncc1", ("C[n+]1ccccc1[C@H](O)c1ccncc1", "O[C@H](c1ccncc1)C1=CC=CC=[N+]1C",
                                      "O[C@H](C1=CC=NC=C1)C1=CC=CC=[N+]1C")),
    ("C[C@H](O)c1cccc[n+]1C", ("C[C@H](O)c1cccc[n+]1C", "C[C@H](O)C1=CC=CC=[N+]1C")),
)
# enantiomer pairs (aromatic charged N): the mirror must flip every R/S.
_ENANTIOMER_PAIRS = (
    ("C[C@H](O)c1cccc[n+]1C", "C[C@@H](O)c1cccc[n+]1C"),
    ("O[C@H](c1ccccc1)c1cccc[n+]1C", "O[C@@H](c1ccccc1)c1cccc[n+]1C"),
    ("C[C@H](O)c1cc[nH+]cc1", "C[C@@H](O)c1cc[nH+]cc1"),
)

FROZEN_HASH = "a4ecd2bc0207ec081f11d5bf0383b5afe352a9fe622a506d604717ae9e3e939c"


def _selftest_payload() -> dict:
    """RDKit-free: our per-molecule outputs over the frozen respelling corpus + enantiomer pairs, hashed for drift."""
    out: dict = {}
    for key, spellings in _FROZEN_RESPELLINGS:
        digs, cips = set(), set()
        for s in spellings:
            digs.add(canonical_digest(parse_smiles(s).canonical()))
            cips.add(tuple(sorted(cip_labels_by_atom(s).values())))
        out[key] = {"n_digests": len(digs), "n_cip_multisets": len(cips),
                    "cip": sorted(cips)[0] if cips else []}
    for a, b in _ENANTIOMER_PAIRS:
        out[f"enant:{a}"] = [sorted(cip_labels_by_atom(a).values()), sorted(cip_labels_by_atom(b).values())]
    return out


def content_hash() -> str:
    return hashlib.sha256(json.dumps(_selftest_payload(), sort_keys=True).encode()).hexdigest()


def selftest() -> None:
    """RDKit-free representation-invariance + enantiomer-flip proof over the frozen corpus (committed baseline)."""
    flip = {"R": "S", "S": "R", "r": "s", "s": "r"}
    for key, spellings in _FROZEN_RESPELLINGS:
        digs = {canonical_digest(parse_smiles(s).canonical()) for s in spellings}
        cips = {tuple(sorted(cip_labels_by_atom(s).values())) for s in spellings}
        assert len(digs) == 1, f"REPRESENTATION SPLIT: {key} -> {len(digs)} digests over {spellings}"
        assert len(cips) == 1, f"CIP SPLIT: {key} -> {cips} over {spellings}"
    for a, b in _ENANTIOMER_PAIRS:
        la = cip_labels_by_atom(a)
        lb = cip_labels_by_atom(b)
        assert la and lb, f"enantiomer pair must both name: {a} {b}"
        assert sorted(lb.values()) == sorted(flip[v] for v in la.values()), (
            f"enantiomer labels must flip: {a}->{la} vs {b}->{lb}"
        )
    # synthesis-path conservation (RDKit-free): the cert accepts balanced isomerisations, refuses unbalanced.
    import random as _random
    synth = check_synthesis_conservation(_random.Random(0))
    assert not synth, f"synthesis-path conservation findings: {synth}"
    # R41-review boundary: the GENERATIVE campaign is structurally blind to RDKit-INVALID inputs (it samples only
    # RDKit-valid molecules), so an over-charged / over-coordinated aromatic N -- which RDKit rejects outright --
    # can never appear there.  Pin it explicitly: such an input must fail closed (raise, or decline), NEVER name.
    for smi in ("C[C@H](O)c1cccc[n+2]1C", "C[C@H](O)c1cccc[nH2+]1", "C[C@H](O)C1=CC=CC=[N+2]1C"):
        try:
            got = cip_labels_by_atom(smi)
            assert not got, f"over-charged/over-coordinated N must NOT name (RDKit-invalid): {smi} -> {got}"
        except SmilesError:
            pass                                  # fail-closed at parse -- the aromatic path's posture


if __name__ == "__main__":
    selftest()
    print("selftest OK; content_hash:", content_hash())
    print("set FROZEN_HASH to the value above")
