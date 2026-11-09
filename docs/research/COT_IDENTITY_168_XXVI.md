# Cyclooctatetraene bond-shift identity collision (#168) — OPERATION XXVI, Packet I (2026-11-08)

**Issue:** #168 — *the SMILES parser and `resonance_identity` merge cyclooctatetraene bond-shift isomers (distinct species).* Related: #130 (identity-carrier layers), #116 (the 1.7 dehydration candidate whose round-4 blind adversary surfaced this).
**Scope of this packet:** RESEARCH ONLY. It reproduces the defect, confirms the inputs are genuinely distinct by a SmartChem-independent method, and proposes a versioned migration. **No production code is changed** — a breaking identity change is out of scope for this packet.
**Base:** `main` @ `4d8149a`, worktree `research/cot-identity-168-xxvi`. Venv `/home/leah/SmartChem/.venv` (import verified under the worktree).
**Artifacts:** `tests/test_cot_identity_168_xxvi.py` (defect pin, 5 tests GREEN today); this document.

---

## 1. The two pairs (ground-truth inputs)

Both pairs are substituted cyclooctatetraenes (COT, [8]annulene). Within each pair, A and B are **bond-shift isomers**: the ring's alternating single/double bonds sit in two different positions, so the substituents straddle different bonds.

| pair | member | SMILES | the distinguishing fact |
|---|---|---|---|
| **1 — disubstituted** | A | `CC1=C(C)C=CC=CC=C1` | the two methyls sit on the two carbons of **one C=C** (double bond between them) |
| | B | `CC1=CC=CC=CC=C1C` | the two methyls sit across a **C–C single bond** (single bond between them) |
| **2 — tetrasubstituted** | A | `CC1=C(C)C(C)=C(C)C=CC=C1` | 1,2,3,4-tetramethyl, methyl-carbon adjacency orders `[2,1,2]` |
| | B | `CC1=CC=CC=C(C)C(C)=C1C` | the bond-shift isomer, methyl-carbon adjacency orders `[1,2,1]` |

Written ring-bond orders, read with an independent reader that preserves the SMILES bond symbols (atom indices are from that reader):

```
Pair 1  A ring: 1=2, 2-4, 4=5, 5-6, 6=7, 7-8, 8=9, 9-1   (methyls on 1,2 — joined by the 1=2 DOUBLE bond)
Pair 1  B ring: 1=2, 2-3, 3=4, 4-5, 5=6, 6-7, 7=8, 8-1   (methyls on 1,8 — joined by the 8-1 SINGLE bond)
```

---

## 2. The collapse stage (evidence)

Probe (`parse_smiles` + the identity functions, per pair member) traced along the pipeline. "EQUAL/DISTINCT" compares member A's key to member B's key; digests are `canonical_digest(...)`.

```
PAIR 1 (disubstituted COT)
  stage a0  literal (NO-kekule) canonical_digest ........ DISTINCT   A=27e26636…  B=207a567a…
  stage a   parse_smiles -> Molecule canonical_digest ... EQUAL      A=207a567a…  B=207a567a…
  stage c   Molecule.canonical() digest ................. EQUAL
  stage d   resonance_identity() ....................... EQUAL      207a567a…
  stage e   isotope_refined_key() ...................... EQUAL
  stage e   configuration_key() ....................... EQUAL

PAIR 2 (tetrasubstituted COT)
  stage a0  literal (NO-kekule) canonical_digest ........ DISTINCT   A=25977738…  B=479372f0…
  stage a   parse_smiles -> Molecule canonical_digest ... EQUAL      A=25977738…  B=25977738…
  stage c   Molecule.canonical() digest ................. EQUAL
  stage d   resonance_identity() ....................... EQUAL      25977738…
  stage e   isotope_refined_key() ...................... EQUAL
  stage e   configuration_key() ....................... EQUAL
```

**The first function that equates the two inputs is `parse_smiles` itself — the collapse happens at PARSE TIME, before `canonical()` or `resonance_identity()` is called.**

Mechanism (all in `smartchem/smiles.py`):

```
parse_smiles(text)
  -> _build_molecule(atoms, bonds, charge)
       -> _canonical_kekule_orders(atoms, bonds, charge)
            -> _canonical_kekule_orders_computed(...)
                 -> _min_constitution_placement(...)   # re-places the double bonds
```

`_canonical_kekule_orders_computed` takes *"the constitution-minimal multiple-bond placement over the WHOLE pi system, so any two Kekulé drawings of one molecule collapse to a single identity"*, and — the load-bearing line — *"For an all-explicit input the kekulise step is a no-op and this is exactly the old `_min_constitution_placement` path."* So an all-explicit, **non-aromatic** COT ring is redistributed exactly like an aromatic one, and the two bond-shift isomers are mapped to one minimal placement.

The decisive control is **stage a0**: when the raw written-order graph is materialised as a `Molecule` *without* `_canonical_kekule_orders` (literal bond orders, `canonical()` relabel only), the two members are **DISTINCT** (`27e26636…` ≠ `207a567a…`). It is precisely the Kekulé re-placement that erases the difference. Downstream, `resonance_identity`, `isotope_refined_key` and `configuration_key` all route through the same shared placement (the SPLIT-KEKULE invariant: every identity layer commits to the one Kekulé structure), so all inherit the collapse — none of them is a second, independent bug; they are one defect seen at one place.

The issue's own one-liner `A.canonical() == B.canonical()  # True  -- the parser already re-kekulises to one graph` is confirmed exactly: by the time `canonical()` runs, A and B are already the same `Molecule`.

---

## 3. Independent confirmation that A and B are distinct species

`rdkit` is **not** importable in the venv and `networkx` is **not** importable in the venv (both `ModuleNotFoundError`). Distinctness was therefore confirmed with a **self-contained, complete** method sharing none of SmartChem's canonicalisation: an independent SMILES reader (preserving written bond orders) feeding a **backtracking bond-labelled graph-isomorphism test** (element + implicit-H node labels, bond-order edge labels, WL-colour-pruned exhaustive search). A corroborating 1-WL run on the **disjoint union** of the two graphs (shared colour space) is reported alongside.

```
PAIR 1 (disubstituted COT)
  exact bond-labelled graph isomorphism : NON-ISOMORPHIC (distinct)
  disjoint-union 1-WL colour multiset   : DISTINCT
  A methylated ring carbons [1, 2];  bond orders BETWEEN them: [2]   (double)
  B methylated ring carbons [1, 8];  bond orders BETWEEN them: [1]   (single)

PAIR 2 (tetrasubstituted COT)
  exact bond-labelled graph isomorphism : NON-ISOMORPHIC (distinct)
  disjoint-union 1-WL colour multiset   : DISTINCT
  A methyl-carbon adjacency bond orders: [2, 1, 2]
  B methyl-carbon adjacency bond orders: [1, 2, 1]
```

**Verdict: both pairs are NON-ISOMORPHIC — genuinely distinct bond-labelled molecular graphs.** The reason is hand-checkable: a graph isomorphism must preserve bond order, but the bond *directly joining the two methylated ring carbons* is a **double** bond in A and a **single** bond in B (pair 1), so no bond-order-preserving bijection can exist. The collapse in §2 is therefore a genuine defect, not correct behaviour.

> **Method caveat (recorded honestly):** a first pass used a per-graph-compressed 1-WL certificate and wrongly reported EQUAL. 1-WL is *incomplete* (it cannot separate every non-isomorphic pair) **and** that implementation compressed colours to integers independently per graph, making the two multisets non-comparable. The authoritative result above is the **complete** backtracking isomorphism test; the corrected disjoint-union 1-WL merely corroborates it. Do not read a 1-WL "equal" as "isomorphic".

---

## 4. Why merging bond-shift COT isomers is wrong — and when merging is right

**Merging is correct for genuine aromatic delocalisation.** Benzene's two Kekulé structures are not two molecules; the six pi electrons are delocalised over a planar, cyclic, Hückel-aromatic (4n+2) ring, and the "double bonds" have no fixed position. Collapsing `C1=CC=CC=C1` and `c1ccccc1` to one identity is physically right, and SmartChem must keep doing it (benzene, pyridine, naphthalene/benzenoids, the aspirin salicylate fragment vs its parsed form, the R41 charged-aromatic rings). This is the whole reason `resonance_canonical` exists.

**Merging is wrong for COT.** Cyclooctatetraene is **not aromatic**: with 8 pi electrons it is a 4n (anti-aromatic *count*) annulene that escapes antiaromaticity by puckering into a **tub (D2d) shape** with **localised, alternating** single and double bonds. Its two bond-shift forms are **distinct species** interconverting by a *bond shift* with a measurable barrier (on the order of ~tens of kJ/mol; distinct enough that heavily substituted COTs have separable bond-shift isomers). They are not resonance structures of one delocalised molecule.

**Where the current soundness argument breaks.** `resonance_canonical` claims it "never over-unifies" because it "only re-distributes multiple-bond orders that satisfy the SAME per-atom demand — a genuine resonance form of the SAME constitution." The hidden premise is *"equal per-atom pi-demand + same connectivity ⟹ resonance forms of one species."* That premise holds for a **delocalised** pi-system but **fails for a localised one**: both COT Kekulé forms give every ring carbon pi-demand 1, yet they are different species because the pi-system is *not* delocalised. Equal pi-demand is necessary, not sufficient; the missing condition is **real delocalisation (aromaticity)**, which `_min_constitution_placement` never tests. COMPATIBILITY.md §5 states the current contract as *"two different species are never merged"* — the COT case is a **counterexample to that sentence**, and the fix must correct both the code and that claim.

The discriminator is **aromaticity, not alternancy.** Benzene (alternant, aromatic) merges; azulene (non-alternant, aromatic) should still merge — its resonance is real; COT (an alternant ring, but **non-aromatic**) must split. So the fix cannot key on "has an alternating Kekulé matching" (COT has one); it must key on perceived aromatic delocalisation of the pi-subsystem.

---

## 5. Versioned migration design

### 5.1 Why this is a contract break, not a patch

Per COMPATIBILITY.md §3 and §5, *material identity is the resonance class* (`resonance_identity`), and *"a change of meaning bumps the [schema] id even when the Python field shape does not (e.g. 0.9.5 bumped the material component id when the structure key coarsened to the resonance class)."* Splitting COT isomers **changes `canonical()` output, `resonance_identity`, and every digest** for affected molecules — the material-component key, the request `semantic_digest` for any search touching one, stored stock keys, goldens. That is explicitly **not** a silent MINOR. It needs a versioned, opt-in path and a digest review, which is exactly why the issue files it with the #130 identity-carrier work.

### 5.2 The opt-in: an identity-policy version flag

Introduce an explicit **identity policy version** threaded through the one shared Kekulé-placement path:

- **`IdentityPolicy.V1` (current, default through 1.x):** `_min_constitution_placement` over the whole pi system. Over-merges non-aromatic bond-shift isomers (the #168 behaviour). Preserved verbatim so every existing 1.x digest is byte-stable.
- **`IdentityPolicy.V2` (opt-in in 1.x; becomes default at the next MAJOR):** **aromaticity-aware**. Redistribute/merge multiple-bond placements **only within pi-subsystems perceived as genuinely aromatic** (planar cyclic conjugation satisfying Hückel 4n+2 over the perceived aromatic atom set — the same perception `_aromatic_matchings` already begins for flagged rings, now generalised to decide *mergeability*). Bonds in a **non-aromatic** conjugated ring keep their **literal, as-written** placement, so the two COT Kekulé forms retain distinct keys.

The flag is read once per parse and carried on the identity call; it is **not** a per-call kwarg scattered across call sites. A new `material-component` schema id (and the dependent digest ids) is minted for V2, exactly as 0.9.5 did when the key coarsened; V1 keys stay readable as a legacy generation (read-only), never silently reinterpreted.

### 5.3 Where the fix lives (and what must flow through one place)

The change is localised to the **shared placement** so no identity layer can split a species another layer merged (the SPLIT-KEKULE soundness invariant):

- `smartchem/smiles.py::_canonical_kekule_orders_computed` / `_min_constitution_placement` — gate the redistribution on an **aromaticity predicate** per pi-subsystem; non-aromatic rings freeze their written orders.
- `smartchem/smiles.py::resonance_canonical` — same predicate on the fragment-surgery path, so a fragment and its parsed form still agree **for aromatic rings** (keeps the aspirin NO_ROUTE fix) while non-aromatic rings no longer over-merge.
- The predicate is **one function** that `_build_molecule` (constitution), `_isotopic_identity` (isotope key) and `_kekulize_in_place` (configuration) all call, since those three already commit to the identical Kekulé structure via `_canonical_kekule_orders`.

### 5.4 Forward/backward controls (a representative corpus)

| class | corpus | V1 | V2 (fixed) |
|---|---|---|---|
| **MUST-MERGE — aromatic (regression guard)** | benzene `C1=CC=CC=C1` vs `c1ccccc1`; toluene/o-xylene two Kekulé spellings; pyridine; naphthalene aromatic vs explicit-Kekulé; aspirin salicylate fragment vs parsed; R41 charged-aromatic ring aromatic vs explicit | EQUAL | **EQUAL (unchanged)** |
| **MUST-SPLIT — non-aromatic bond-shift (the fix)** | the two #168 COT pairs; parent COT `C1=CC=CC=CC=C1` bond-shift forms; larger non-Hückel annulenes; radialenes | EQUAL | **DISTINCT** |
| **alternant vs non-alternant (discriminator check)** | benzene (alternant+aromatic → merge); **azulene** (non-alternant+aromatic → still merge); COT (alternant+non-aromatic → split) | — | merge / **merge** / **split** |
| **constitutional isomers (must stay split under both)** | o-/m-/p-xylene; the COT isomers vs a constitutional isomer | DISTINCT | DISTINCT |

Backward control: every MUST-MERGE row's V1 digest must be **byte-identical** under V2 (the fix touches only non-aromatic rings). Forward control: each MUST-SPLIT row flips EQUAL→DISTINCT and gains a fresh, stable V2 digest. The **azulene** row is the load-bearing discriminator test — a naive "freeze all explicit bonds" fix would wrongly split azulene and re-break naphthalene; the predicate must be *aromaticity*, not *explicitness* or *alternancy*.

### 5.5 What the fix must NOT break

- The **aspirin NO_ROUTE fix** — an aromatic fragment must still unify with its parsed form (`resonance_canonical` still merges aromatic Kekulé forms).
- **Benzenoid merging** (naphthalene/anthracene aromatic vs explicit-Kekulé) and the **R41 charged-aromatic** unification.
- The **SPLIT-KEKULE invariant** across constitution / isotope / configuration — all three must adopt the same predicate in lock-step (one shared function), or an isotope/configuration key could split a species constitution merged, or vice-versa.
- The **DoS size cap** fallback (`_RESONANCE_MAX_HEAVY` / `_RESONANCE_MAX_MATCHINGS`) and **idempotence** on an already-parsed molecule.
- **V1 digest stability** — default behaviour and every stored 1.x key stay exactly as today until a consumer opts into V2; V2 ships under new schema ids with a migration note in COMPATIBILITY.md §5 (and the "two different species are never merged" sentence corrected).

---

## 6. Status ledger

- **Reproduced:** YES. The collision is real on `main` @ `4d8149a`; first equated at `parse_smiles` (parse-time Kekulé re-placement), inherited by `canonical()`, `resonance_identity`, `isotope_refined_key`, `configuration_key`. (§2, evidence shown.)
- **Independent distinctness:** CONFIRMED by a complete backtracking bond-labelled graph isomorphism (rdkit absent, networkx absent). Both pairs NON-ISOMORPHIC. (§3.)
- **Defect vs correct behaviour:** DEFECT — COT is non-aromatic with localised bonds; the merge violates `resonance_canonical`'s own "never over-unifies" contract and COMPATIBILITY.md §5. (§4.)
- **Fix:** NOT APPLIED (out of scope for this packet). Design in §5 is a proposal.
- **UNVERIFIED / left open:** the exact literature citation for separable *1,2,3,4-tetrasubstituted* COT bond-shift isomers (the issue flags it UNVERIFIED; not independently confirmed here). The breadth of OTHER affected ring systems (larger annulenes, radialenes) is noted by the issue as **unmeasured** and is not quantified in this packet. Whether V2's aromaticity predicate should treat borderline cases (e.g. heteroannulenes, partially-saturated rings) as mergeable is a design question for the implementing round.
