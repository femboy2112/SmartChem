# Transform-algebra expansion round — electrocyclization, the bounded lateral search, M2 extent, and the WH layer (2026-09-20)

Status: **SHIPPED** (this round). Governs items 1–6 of the post-#87 next-steps table, built in the coherent
multiplexed order **2a/2b → 1 → 3 → 5 → 4 → 6**. Every item is either a sound build or a **verified defer with a
structure-theorem reason** — never a fabricated "done".

This round grows the rule-calculus transform algebra along three orthogonal axes at once: a **third pericyclic
archetype** (electrocyclization), a **sound bounded search** over the rank-flat lateral seam, and the **first two
non-constitutional annotation layers** (Woodward–Hoffmann stereochemistry; equilibrium extent). The reaction-TYPE
oracle grows **12 → 17** conservation-locked classes.

## What shipped (sound builds)

| # | Item | Where | Core |
|---|------|-------|------|
| 2a | thia-diene DA | `diels_alder.py` `THIA_DIENE_DA` + `ThiaDieneDielsAlderProvider` | completes the **3×2** heteroatom × {dienophile, diene} matrix (N/O/S each on both positions); shares its centre with `THIA_DA` (position-invariant), separated by **Layer A alone** |
| 2b | aza-Claisen, thia-Claisen [3,3] | `lateral_rewrite.py` `AZA_CLAISEN`, `THIA_CLAISEN` | array atom 2 = N / S → C=N / C=S product; completes the hetero-[3,3] set {O, N, S} on the same array + guards |
| 1 | electrocyclization (4π, 6π) | `lateral_rewrite.py` `ELECTRO_4PI`, `ELECTRO_6PI` | the **third pericyclic archetype**; a rank-flat ring-open/close isomerization on the SAME lateral seam (the kernel's "degree" is valence, preserved, so it is kernel-native) |
| 3 | bounded lateral search | `lateral_search.py` `lateral_closure`, `lateral_route_to` | a BFS over Molecule isomer states keyed by `resonance_identity`, terminating on its OWN visited-set + budgets, **strictly separate** from the W1 route search |
| 5 | whole-fragment neutrality | `diels_alder.py` `whole_fragment_neutral` | dalembert's Claim-2 opt-in: bounds EVERY atom (not just the matched centre) by neutral valence — a **labeled measured tradeoff**, default-off |
| 4 | M2 equilibrium extent | `equilibrium.py` `equilibrium_extent` | the declared-reference general-Δn extent solver — solve `K = Π(cᵢ/c°)^sᵢ`, strictly monotone → unique root |
| 6 | Woodward–Hoffmann layer | `pericyclic_selection.py` | a **theorem-constant** stereochemical annotation off the perceived type + electron count — no geometry oracle |

### Item 1 + 3 — electrocyclization and the lateral search

**Electrocyclization is kernel-native.** The `BondRule` kernel's "degree" is *valence* (bond-order sum), which an
electrocyclization preserves at every atom (a terminus goes `=CH2` valence 2 → ring `-CH2-` valence 2), so the
fixed-vertex degree-locked kernel accepts a ring-forming rank-flat rule with no change to `_guarded_rewrites`. Nothing
in `_SigmatropicFamily` or the guards is [3,3]-specific (they read `family.retro/forward/signature/center`), so an
electrocyclization is a **second factory** (`_electrocyclic_family`), not a rewrite of the machinery — the elegant
multiplex. Verified: 6π `C1=CCCC=C1 ↔ C=CC=CC=C`, 4π `C1=CCC1 ↔ C=CC=C`, each round-trips and recovers its isomer.

**The bounded lateral closure is the epic's sound core.** The deferred half of #87C was *auto-discovery of
isomerization routes*. The block is a structure theorem: `search_routes` recurses only onto a `precursor ∈
transform.products` and terminates by W1 (*every product strictly smaller `Formula.rank` = atom count*). An
isomerization is rank-flat, so W1 is unsatisfiable for it; forcing one through the decompiler/conditions path calls
`forget()`, which `LateralRewriteEdge` refuses (fail-loud). Inside the descent recursion a rank-flat edge would
collapse the well-ordering (the ancestor guard blocks only exact revisits *along one path*, never frontier-wide
isomer cycles).

`lateral_search.lateral_closure` terminates on its OWN measure, entirely outside the descent — the exact discipline
of the kernel's `bounded_closure` (which tolerates state-preserving cycles precisely because it carries its own
visited-set + budgets), lifted from `BondGraph` to `Molecule` and keyed by `resonance_identity` (the same canonical
key the route search already dedups on). **Termination proof:** each canonical identity is inserted and expanded at
most once (no A→B→A loop), expansion stops at `depth`, admission stops at `state_budget`, so the frontier is
exhausted in finite steps regardless of how many isomers the families could reach. It **never** calls `forget()`,
**never** registers a provider, **never** re-enters `routes_making` — so `search_routes`' termination is untouched
and this search's termination does not borrow rank descent. `lateral_route_to` reconstructs an explicit
hand-assembled route the oracle vouches step by step.

**oxy-Cope disposition (item 2, honest non-build):** oxy-Cope is NOT a new structural class. A 3-hydroxy-1,5-hexadiene's
six-atom array is all-carbon, so it is already a `COPE` match; the enol→ketone tautomerisation (the thermodynamic
"oxy" driving force) is a *separate* step and is Problem B / feasibility, not Problem A type-validity. Pinned:
`sigmatropic_rewrites(COPE, "C=CC(O)CC=C")` yields the [3,3] isomer and its step is recognized as Cope.

### Item 4 — M2 equilibrium extent (and why D stays deferred)

`equilibrium.py` already computed `K = exp(−ΔG/RT)`, the extent verdict, and the **Δn=0** ideal conversion (which
correctly *refuses* Δn≠0). `equilibrium_extent` is the opt-in the refusal message names ("inject a declared activity
model"): the caller declares the initial composition and the standard-state reference `c°`, and the solver finds the
extent ξ for the general case. **Known physics, unique root, no new physics:** with signed stoichiometry `sᵢ`
(products +, reactants −) and constant volume, `cᵢ(ξ) = cᵢ⁰ + sᵢξ`, equilibrium is `f(ξ) = Σ sᵢ·ln(cᵢ(ξ)/c°) − ln K =
0`; on the admissible open interval `df/dξ = Σ sᵢ²/cᵢ(ξ) > 0`, so f is strictly increasing from −∞ (a product → 0) to
+∞ (a reactant → 0) → the root is unique and bisection finds it. Calibrated: Haber (Δn=−2, K~5×10⁵ at 298 K) →
~98 % conversion with exact N mass balance; adding product lowers conversion (Le Chatelier).

**The D re-affirm (load-bearing).** Even with M2 extent in hand, `feasibility`'s ΔG — and now K/ξ — measures
thermodynamic **DRIVE**, not the poor-man **CAPABILITY** property a Problem-B disposition gate needs. So
`equilibrium_extent` is **RANKING / EVIDENCE ONLY**, never a "can a kitchen bench run this" gate
([[a-sound-measurement-is-not-a-capability-verdict-source]], `POOR_MAN_DEFER_LEDGER` #5). DRIVE≠CAPABILITY stands.

### Item 6 — Woodward–Hoffmann selection, a theorem-constant

Once the oracle perceives a reaction's TYPE and π-electron count, the WH rule *determines* its allowed
stereochemistry — it is a consequence of the aromatic-transition-state theorem, not a measurement. Thermal
ground-state pericyclic reactions run through the aromatic TS: **Hückel** (all-suprafacial / disrotatory) is aromatic
with **4n+2** electrons, **Möbius** (one-antarafacial / conrotatory) with **4n**; photochemical inverts.
`pericyclic_selection` attaches this provable constant (with the electron-count witness) to each of the 14 recognized
pericyclic families — supra/antara for cycloaddition & sigmatropic, con/disrotatory for electrocyclization — with no
3D coordinates, conformer, or TS energetics. Verified: 4π→conrotatory, 6π→disrotatory, [4+2]/[3,3]→suprafacial.

## Verified defers (with discharge paths)

1. **Lateral-search *fusion* into `search_routes`** — genuinely unsound (the W1 structure theorem above). The
   bounded closure is the sound alternative; fusing rank-flat edges into the rank-descent recursion stays deferred
   forever unless the termination proof is redesigned. Discharge: a lateral-aware conditions/search path that never
   borrows strict rank descent (this module IS the first step).
2. **Endo/exo *prediction*** (the Alder endo rule) — a kinetic TS preference (secondary-orbital overlap), Problem B,
   needs a stereo-aware TS/geometry oracle that does **not** exist in-tree (`geometry.py` makes ONE non-stereospecific
   VSEPR conformer for energy and explicitly disclaims stereochemistry). No pure-graph / coordinate-free model can
   express a TS facial preference — a structure-theorem defer.
3. **Endo/exo *description*** (naming a stereo-SPECIFIED adduct's diastereomer) — graph+parity-sound and would reuse
   the existing CIP parity engine, but the pericyclic pipeline carries no product stereo today (`identity.stereo_loss`
   blocks `@`/`@@` before a step). A *scoped* defer: the discharge is stereo-threading, not a new geometry oracle.
4. **Coupled / simultaneous equilibria + Le Chatelier operator** — only an additive route net-ΔG exists; a
   shared-intermediate co-solve is a larger nonlinear system. `equilibrium_extent` (single-reaction) is the sound
   foundation a future coupled solver builds on.
5. **Memory correction banked:** shipped `cip_labels`/`cip_labels_by_atom` are pure-graph CIP digraph + written-order
   parity — they do **not** use synthetic 3D coordinates (those live only in the probe cross-check
   `experiments/cip_geometry_oracle_probe.py`). The earlier "CIP oracle uses synthetic coords" note was true only of
   the probe.

## Soundness discipline preserved

- **17-way no-cross-poach:** every new class's step fires exactly one recognizer; the diene↔dienophile centre
  collisions (aza/oxa/thia) remain the ONLY centre collisions, separated by Layer A (the crown finding, now for S too).
- **Byte-identity:** the edge CLASSES were not merged (qualnames are in the content digest); only shared bodies were
  factored (`guarded_isomer_edges` ← `rewrite_edges`). The three DA probe hashes and the fuzzer `FROZEN_HASH` are
  untouched.
- **Fail-closed everywhere:** the closure reports INCOMPLETE on budget truncation; `equilibrium_extent` returns None
  on no-K / absent-reactant; a recognizer that raises abstains; `whole_fragment_neutral` is opt-in and never tightens
  the default guarded retro.
