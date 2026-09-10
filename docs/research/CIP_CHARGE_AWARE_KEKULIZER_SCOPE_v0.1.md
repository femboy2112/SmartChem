# CIP charge-aware kekulizer — scope & soundness (v0.1, ROUND 41)

**Queue item q1** — "charge-aware kekulizer: a charged AROMATIC spelling (`c1cccc[n+]1C`) NAMES instead of hitting
the kekulization wall; must FAIL CLOSED on out-of-scope charged aromatics."

## The gap R40 left

ROUND 40 named a cationic-ring-N heterocycle written in **explicit-Kekulé** form
(`C[C@H](O)C1=CC=CC=[N+]1C` → `S`), by adding a `charge > 0` cationic-N whitelist to `_cip_mancude`. But the
**natural aromatic spelling** `C[C@H](O)c1cccc[n+]1C` still hit a parser wall (`SmilesError: could not assign a
Kekulé structure`) **upstream** of the namer: `_aromatic_matchings` classified a cationic ring N as a pyrrole-type
**donor** (it has 3 sigma bonds and/or an explicit H), so the ring lost an acceptor, no perfect matching existed,
and parsing raised. R40's own probe recorded those aromatic spellings as **proven-real deferred consumers** (RDKit
`rdCIPLabeler` names them; we walled) — the `[[an-oracle-driven-existence-check-can-prove-a-defer]]` pattern, here
read forward: last round's proven defer is this round's proven build. A live RDKit re-check (2026.03.6) confirmed
**6/6** target consumers name in RDKit while our parser walls.

## What R41 builds

### 1. The charge-aware kekulizer (a fail-closed whitelist)

`_aromatic_matchings` gains a charge branch that mirrors the R40 `_cip_mancude` gate one layer upstream:

```python
if charge:
    if charge > 0 and element == "N":
        acceptors.append(a)      # cationic ring N: pi-acceptor (lone pair in the N-H/N-substituent bond)
    else:
        raise SmilesError(...)   # every other charged aromatic atom fails CLOSED, loudly
```

A cationic ring N is admitted as a π-acceptor — isoelectronic with pyridine's acceptor N, the class R40 validated
0-mislabel vs RDKit. So the aromatic spelling kekulises to the **same** Kekulé structure as the explicit form, and
the R40 `_cip_mancude` cationic-N path (which re-applies its **own** `[1,1,2]` charge>0 gate — defence in depth)
then names it.

**Fail-closed, structurally (not incidentally).** Every other charged aromatic atom raises:
- **Cationic chalcogen** (pyrylium `[o+]`, thiopyrylium `[s+]`) — the **dalembert-R40-proven RDKit-divergent**
  class (no neutral acceptor analogue; its charge-blind average crosses a real heteroatom). It would otherwise
  fall into the O/S **donor** branch and **silently mis-kekulise** on an even acceptor count. Now it raises —
  making the fail-closed *structural*, per `[[a-fail-closed-guarantee-must-hold-at-every-fallback-layer]]`.
- **Anionic** ring atoms (`[cH-]`, `[n-]`) and exotic over-charges — no validated branch → raise.

### 2. The unified resonance canonicaliser (a latent false-split fixed)

Admitting the charged aromatic spelling **exposed** a latent bug. `_build_molecule` (constitution identity),
`_isotopic_identity` (isotope key) and `_kekulize_in_place` (configuration/chirality) each used a **two-branch**
placement: a fully-explicit structure ran the global `_min_constitution_placement`, but when *some* bonds were
aromatic-**flagged** they canonicalised only those and left an explicit ring at its **authored** Kekulé placement.
A molecule mixing an aromatic ring with an explicit-Kekulé **charged** ring —
`O[C@H](c1ccncc1)C1=CC=CC=[N+]1C` — therefore got a **different** canonical identity than its fully-aromatic or
fully-explicit spelling: **one species, two identities** (a false split). Neutral molecules dodged it (a symmetric
phenyl's placement is trivial, pyridine's is forced), so it stayed latent until a charged ring made a non-trivial
explicit placement reachable beside an aromatic ring — exactly `[[a-sound-extension-guards-its-new-cross-comparisons]]`.

**Fix:** one shared `_canonical_kekule_orders(atoms, bonds, charge)` = kekulise the aromatic-flagged bonds to any
one perfect matching (per-atom π-demand is **matching-invariant**, so the choice is arbitrary-but-fine), then
delegate the **whole** structure to `_min_constitution_placement`. All three functions route through it, so
constitution, isotope key and configuration commit to the **identical** Kekulé structure — no layer can split a
species the layer below unified (the SPLIT-KEKULE invariant, which the naphthalene red-team pins). Proven
**byte-identical** for every neutral molecule (benzene, naphthalene, pyridine, pyrrole, furan, thiophene,
quinoline, indole, anthracene, phenanthrene, pyrene, azulene, triphenylene, fluorene, indolizine), and unifying
the charged aromatic / explicit / mixed spellings.

## Soundness

CIP priority is by **atomic number**; formal charge moves no Z. The matching enumeration and partner-Z average in
`_cip_mancude` are charge-blind by construction. The cationic ring N is admitted because it has a **neutral
isoelectronic acceptor analogue** (pyridine's N: ipso duplicate average `(C:6 + N:7)/2 = 6.5`, below any real
heteroatom Z, so it never crosses a competitor even in ring-vs-ring). A cationic **chalcogen** has no such
analogue (a neutral ring O/S is a donor), so its charge-blind average crosses a real heteroatom and RDKit diverges
— which is why it stays deferred, fail-closed. The `charge > 0 and element == "N"` guard makes the admission a
strict whitelist; the identity unification makes the representation invariant. A wrong R/S (or a false split) is
worse than an honest refusal.

## Evidence (committed)

- `experiments/cip_charge_aware_kekulizer_probe.py` (FROZEN_HASH pinned): 12 aromatic-spelling consumers name +
  match RDKit + **unify** with their explicit-Kekulé twin (`digest(aromatic) == digest(explicit)`); 4 deferred
  classes (O⁺/S⁺/C⁻/N⁻) **raise**; representation-invariance groups (incl. the mixed pyridyl-vs-pyridinium spelling
  and the naphthalene red-team) collapse to one identity. RDKit-free `validate()` + gated `_rdkit_cross_check`.
- `experiments/chem_differential_fuzzer.py` (CHEM-FUZZ-01): a seeded, structure-aware **differential fuzzer** —
  parse-robustness, representation-invariance (N RDKit respellings → one digest + one CIP multiset),
  same-molecule differential (no false merge/split), CIP-vs-RDKit, enantiomer-flip; shrinks each finding to a
  minimal reproducer; honest coverage boundary. **8-seed generational campaign: 2446 molecule-instances × 8
  respellings + 2794 same-molecule pairs → 0 findings.** Committed RDKit-free `selftest()` re-checks
  representation-invariance + enantiomer-flip over a frozen respelling corpus.

## Deferred, fail-closed (documented, NOT built)

| class | why | outcome |
|---|---|---|
| cationic chalcogen aromatic (pyrylium O⁺ / thiopyrylium S⁺) | no neutral acceptor analogue; RDKit-divergent averaging (dalembert R40) | **raises** (structural) |
| anionic ring atoms (`[cH-]`, `[n-]`) | no validated donor/acceptor branch | **raises** |
| exotic over-charge in a ring | not a real aromatic valence | **raises** |
| recursive CIP Rules 4b/4c/6 on charged rings | no forcing consumer (R36/R38 defers) | unchanged VERIFIED DEFER |

## Boundary

The oracle is RDKit `rdCIPLabeler` / `MolToSmiles`; a shared RDKit bug would be common-mode-invisible. The fuzzer
samples the seed corpus + RDKit single/multi-edit mutants; multi-step synthesis-route conservation is stubbed to a
wire-point (the `Reaction`/`ExperimentStep` conservation dimension). rdkit is a **dev-venv-only** oracle,
uninstalled before the committed baseline; the rdkit-gated probes and tests `importorskip`-skip when it is absent.

## Adversarial review (four-bearing gate)

- **dalembert (structure-theorem) — SURVIVED.** Exhaustively enumerated all 5-ring (96) and 6-ring (356) aromatic
  charged-N heterocycles: 0 double-bond-incidence mismatches vs RDKit kekulization; the predicted counterexample
  class (a cationic N RDKit treats as a π-donor) is provably empty. 840 stereocentre CIP comparisons + 12 molecules
  × 7 respellings + 4 fresh fuzz seeds: 0 mislabels, 0 splits, 19 neutrals byte-identical R41-vs-R40. **One minor
  finding:** the `charge > 0` whitelist over-reached its `charge == 1`/coordination-3 proof domain — repo NAMED
  RDKit-invalid `[n+2]`/`[nH2+]`. **Fixed:** tightened to `charge == 1 and coordination == 3` (`_aromatic_matchings`)
  and `charge == 1` (`_cip_mancude`); over-charged/over-coordinated N now fails closed exactly as RDKit rejects the
  molecule. Pinned in the probe (two new defer entries), `test_over_charged_nitrogen_fails_closed_r41_review`, and
  the fuzzer selftest.
- **evil-morty (red-team) — SOUND.** ~30k probes (4760 generated molecules / 28,430 parse+CIP calls): 0 crashes,
  0 identity splits/merges, 0 CIP mislabels, 2000 formula checks vs RDKit AddHs clean. Same over-reach nit
  (fixed); one perf nit (dense-benzenoid identity cost) noted below.
- **birdperson (principled) — SOUND.** The fail-closed whitelist holds at every reachable path; `matchings[0]` is
  provably matching-invariant; the three-layer routing couples the shared substrate, not the distinct keys. Noted
  the same over-reach (fixed) and that the differential fuzzer is structurally blind to RDKit-invalid inputs — so
  the over-charge fail-closed is now pinned explicitly (probe + fuzzer selftest).
- **mr-president (acceptance) — SHIP.** Mandate item 1 (charged aromatic NAMES) and item 2 (fail-closed on
  out-of-scope) both MET/Verified; the representation-invariance unification is in-scope, not scope-creep; the
  neutral refactor is byte-identical.

**Tracked debt (not R41-introduced, out of q1 scope):** constitution / isotope / configuration each recompute the
full `_min_constitution_placement` per parse (three times), uncached; a dense fused benzenoid's identity is a
latency smell (triphenylene ~3.5s), bounded by the `_MAX_KEKULE_MATCHINGS` cap (fail-closed beyond, never a hang).
The per-atom π-demand is matching-invariant, so an `lru_cache` on the placement would be a sound future optimisation.
