# CIP node enrichment — build-ready scope decision (categorical reorientation, Move 4, CIP half)

> **Status:** SCOPE DECISION, build-ready — not built this round. Move-4's tension-A half shipped
> (`resolve_stability` keyed on canonical structure, `tests/test_composability.py::TestStabilityKeyIsStructureNotFormula`).
> The CIP node-enrichment half is scoped here as its own reviewable round because it is **soundness-critical**
> (a wrong R/S label is fabrication, forbidden by `known-physics-not-new-physics`) **and** moves the `FROZEN_HASH`
> golden — the same call R19 made for ONLOAD-REDERIVE (spec'd build-ready, then built R21).

## The goal (Move 4, CIP half)

Enrich the CIP hierarchical-digraph node from `(z, children)` to carry the attributes the higher CIP rules need, so
Rules 1b / 2 (and, deferred, 4/5) become **representable** — closing the "Rule 1a only" boundary the namer has
carried since R20. Node representation today (`smartchem/smiles.py`): a 2-tuple `(atomic_number, children)`, with
`z` at index 0 and `children` at index 1; `_CIP_PHANTOM = (0, ())` (`smiles.py:946`); duplicate/closure leaves
`(z, ())` (`:1120/:1130`); aromatic boundary `(z, _CIP_AROMATIC)` (`:1112`).

## The load-bearing soundness discipline (why this is not a two-line change)

CIP applies its rules **hierarchically**: Rule *k* must be exhausted over the whole digraph **before** Rule *k+1*
is consulted, and each later rule is applied *in the exploration/ranking order the earlier rules established*
(Hanson et al. 2018 — the paper the current Rule-1a code cites, which exists precisely because naive
implementations get this wrong). Two concrete traps this forces:

1. **NEVER append `mass`/`aux` to the per-leaf tuple compared inside the existing `_cip_compare`.** That would let
   a shallow-sphere mass tie override a deeper Rule-1a atomic-number difference — an inversion of CIP precedence.
   Each new rule must be its **own full pass**, entered ONLY at the exact Rule-1a tie hand-off
   (`smiles.py:1237`, where `_cip_compare` returns `0` and `_cip_ranks` currently `return None`).
2. **Rule-2 pairing ambiguity must fail-closed to DEFER.** When Rule 1a ties two subtrees, their children are
   Rule-1a-ranked; but where several children are themselves Rule-1a-tied, the pairing for the Rule-2 comparison is
   ambiguous. A sound slice compares Rule 2 only where the pairing is unambiguous and **DEFERS (returns `None`)**
   otherwise — never a guessed label. Detecting the ambiguity is part of the build, not an afterthought.

## The build plan (each rung its own PR-sized round)

### Rung 1 — Rule 2 (mass number / isotopes) — the cleanest genuine win

- **Node shape:** `(z, mass, children)` (add exactly the `mass` slot; do NOT add slots for rules not yet decided —
  a half-wired `aux` slot invites a future reader to treat it as populated). `_CIP_PHANTOM → (0, 0, ())`.
- **Isotope threading:** `_Atom.isotope` (`smiles.py:163`, 0 = unspecified) is dropped by `_fill_hydrogens`
  (`:442`, returns element strings). Thread a **parallel mass array keyed by atom index** rather than perturbing the
  element-string canonicalization that `_kekulize_in_place`/`_wl_colours` rely on. Mass convention (2013 IUPAC Rule
  2): a specified isotope carries its exact mass number; an unspecified atom carries the element's standard atomic
  weight (a lower value than any heavier specified isotope) — so `[3H] (3) > [2H] (2) > H (~1.008)`. Duplicate/
  closure leaves carry the mass of the atom they duplicate.
- **Comparator:** a new `_cip_compare_rule2(a, b, ctx)` mirroring `_cip_compare`'s BFS structure but comparing the
  `mass` slot, descending children in **Rule-1a-sorted order** (`_cip_sorted_children`, already Rule-1a-ranked),
  invoked ONLY when full Rule 1a returns `0`. Pairing-ambiguous case → DEFER.
- **`_cip_ranks` hand-off (`:1237`):** on `c == 0`, try Rule 2; use its verdict if decisive, else `return None`.
- **Flips:** the isotope-only deferral `F[C@@](Cl)([2H])[3H]` (`cip_namer_probe.py:109 DEFERRALS[3]`) becomes a
  named centre — a **conscious `FROZEN_HASH` re-freeze** (the tripwire working as designed), not silent drift.

### Rung 2 — Rule 1b (duplicated-atom hierarchical rank) — needs a further slot

Rule 1b ranks duplicate atoms by the **hierarchical rank of the node they duplicate**. `(z, mass, children)` alone
cannot carry it; a duplicate leaf needs to reference the rank/identity of its represented node. Add a
`dup_rank` slot only when building this rung (a 4-tuple `(z, mass, dup_rank, children)`), with its own full pass
gated after Rule 2.

### Rule 3 (E/Z, seqcis/seqtrans) — an explicit DEFER between Rule 2 and Rule 4

The named "1b/2/4/5" set **skips Rule 3**. The CIP order is 1a < 1b < 2 < 3 < 4 < 5; a centre whose ligands differ
only by double-bond geometry MUST be an explicit DEFER (never silently jumped) until Rule 3 is built.

### Rules 4/5 (like/unlike, R/S descriptors) — STAY DEFERRED (`aux = None`)

These require a recursive **auxiliary-descriptor pre-pass** (provisional R/S for every interior stereocentre) — a
large, error-prone build. Populating an `aux` slot with anything less than a correct pre-pass **fabricates R/S
labels** on pseudoasymmetric centres — worse than deferring. Keep the tie→DEFER at `:1237` for any centre reaching
Rule 4; do not add the `aux` slot until the pre-pass exists.

## Coupled edit sites (fail-loud on a shape change; must be updated in lockstep)

`_CIP_PHANTOM` (`:946`); `_cip_digraph` writers (`:1112/:1120/:1130/:1131`); the `node[1] is _CIP_AROMATIC` checks
(`:1139/:1207`) and `_cip_child_zs`/`_cip_sorted_children` readers (which move to the new `children` index); and the
probe/test structural couplings that unpack the 2-tuple: `cip_namer_probe.py::_dfs_key` (`:164`), `_DIV_A/_DIV_B`
(`:236`), and `tests/test_cip_mancude.py:57` (`for z, _children in node[1]`). The geometry-oracle `FROZEN_HASH`
(`cip_geometry_oracle_probe.py`) takes priorities as INPUT and is **not** moved by node enrichment.

## Preservation obligations (regressions to re-run green before the re-freeze)

- The **di-2-pyridyl false-centre** soundness pin (`DEFERRALS[4]`) must still DEFER (the R22 mancude fix).
- The **transitivity guard** `sorted(ranks) != [0,1,2,3] → None` (`:1243`) must be re-verified to still catch any
  cmp-cycle the new passes could introduce (the R20 comparator-transitivity residual).
- The distinct-atomic-number slice must stay **byte-identical** (Rule 1a still decides everything it decides today;
  new rules fire ONLY where a case currently returns `None`).
- Adversarial (evil-morty) review before commit, as every prior CIP round had.

The result of following this: a sound-not-complete Rule-2 (then Rule-1b) extension that names strictly more centres
without ever guessing a label, with the `FROZEN_HASH` re-freeze made an explicit, reviewed decision.
