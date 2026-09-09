# SmartChem roadmap

> **The single source of truth for what is done, what is queued, and what is deliberately not being built.**
> `verified @ cip-ring-rules-dow-source-2026-09-09` (**ROUND 35** — priorities 1–5: written ring order, revised Rule 1b, bounded Rules 4a/5, ring-isotope release, and a modern Smackover bromine undercut source). Maintained suite: **4684 passed / 22 skipped / 1 xfailed** in four serialized partitions (1849/8; 769/14/1; 1069; 997). Fresh RDKit 2026.3.6 representation rotation: **320 randomized equivalent SMILES, 0 disagreements**. Finite oracle agreement is bounded evidence, not universal CIP completeness. · updated **2026-09-09 UTC**
>
> This file is canonical. `MEMORY.md` and `UPTAKE_MANIFEST_v0.5.0a1.md §N` point *here* rather than duplicating the
> queue — one list, not three that drift. Full per-round build history lives in the manifest (through `§22`); this file is
> the forward-looking plan plus a compact done-ledger. Sizes and first-steps were ground-truthed against the source and
> the load-bearing claims independently re-verified at their file:line anchors; earlier rounds used independent evil-morty passes;
> ROUND 22 records its separate source, implementation and adversarial-review bearings explicitly.

## Governance — the 3-lane projection (authoritative)

Every item is tagged with the lane it advances. **Progress in one lane never implies another.** (Audit:
`AUDIT_GENERIC_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md`.)

- **Lane A — Alpha-conformance.** Does it conform to the v0.5.0a1 alpha contract / laws?
- **Lane B — Chemical genericity.** The transform algebra (capped / bond-order / heterolytic / redox IR-COMMUTE
  families) driven through the **unchanged** bounded SEARCH core.
- **Lane C — Bench-readiness.** Section-11 bench fit (composability[E1] + physical box + process) and section-10.4
  pricing (dated **and** sourced, never invented).

**Poor-man ethos (the bench is a kitchen).** "The kitchen" and "my lab and equipment" mean the same thing: the
whole-path capability model satisfies-or-BLOCKS against **household + outdoors** equipment by default, never assumed
lab infrastructure. "Poor man's fume hood = experiment done outside" — outdoors is a valid *ventilation* control, but
ventilation ≠ hazard clearance (a toxic/corrosive vapour like Br₂/Cl₂ is still surfaced). Affordability is a whole-path
capability claim (material identity, controllable operations, measurement, containment, separation, verification,
closure), not a cheap-reagent list — a route cheap in reagents but needing a control the kitchen can't provide is
`CAPABILITY_BLOCKED`, surfaced, never papered over. See `docs/research/PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md`.
**Cheap epistemology counts too:** the ethos prefers chemistry that *tells you what it is doing* — a route whose
success/failure is legible from cheap, redundant, chemistry-supplied signals (colour change, precipitate, gas evolution,
pH/temperature excursion) beats one that fails silently and needs a $20k instrument to notice. That is a *ranking*
objective (the Observability Score, shipped ROUND 18), kept honest by the rule that a visible checkpoint is **not** chemical
proof (process-indicator / identity / purity stay separate axes — invariants 5 & 7).

## North-star litmus tests (the acceptance gates that keep the lanes honest)

- **Paracetamol litmus (Lane C):** *could a real chemist use our paracetamol decompilation to pick real steps?* Tests
  step-level usefulness.
- **DOW bromine litmus (Lanes B + C + EM) — NEW:** *can we predict Br₂'s decomposition and synthesis, enumerate the
  synthesis paths, rank them **quantitatively on cost**, and reproduce why Herbert Dow's brine-bromine process undercut
  the German bromine cartel?* It forces the WHOLE stack at once — the **redox** IR-COMMUTE family (Cl₂ + 2Br⁻ → Br₂ +
  2Cl⁻), the **electromagnetic** scope (electrolytic oxidation of bromide — electrons at an anode; the one litmus that
  bridges the chemistry core and the electron/circuit layer), **thermodynamics/feasibility**, and the **cost/affordability
  buckets** (`cash_floor`, `affordability_frontier`, `material_quantity`) — down to the humble "poor-man's" evidence
  buckets. A pass quantitatively shows the cheap-brine route beats the mineral route. **Sourcing is favorable:** bromine
  is a USGS-priced inorganic (same pattern as NaCl/Na₂CO₃), so unlike the organic-price wall this litmus's cost axis is
  genuinely achievable. Spawns the queue items marked *(DOW)* below.
  **The litmus's decomposition, synthesis, and bounded modern cost questions are now answered.** **✅ Phase 1
  — pricing (ROUND 16, DOW-BROMINE-01):** elemental bromine is a first-class SOURCED, USGS-priced commodity ($2.70/kg 2024,
  MCS 2026), INDUSTRIAL-tier (the DOW insight encoded), costed end-to-end through the buckets. **✅ Phase 2 — mechanism
  (ROUND 17, REDOX-DISPLACE-01):** the coupled half-reaction combiner enumerates `Cl₂ + 2 Br⁻ → Br₂ + 2 Cl⁻`, the reaction
  no prior mechanism could reach. **✅ Phase 3 — electrochemistry (ROUND 18, ELECTROCHEM-01):** sourced standard potentials
  prove displacement is SPONTANEOUS (E°cell = +0.271 V, ΔG° = −52.3 kJ/mol) and reproduce why chlorine displaces bromide
  but not the reverse; the electrolytic anode leg is modelled. **✅ Phase 4 — Br₂ decomposition, thermo + kinetics
  (ROUND 26 + ROUND 30):** `Br₂ → 2 Br•` is thermodynamically UNFAVORABLE at 298 K (ΔG = +161.65 kJ/mol, sourced CODATA,
  R26) AND the collisional dissociation KINETICS (Warshay NASA TN D-3502, modelled R30) confirm Br₂ SURVIVES at any
  kitchen-achievable T (a lower-bounded, thermo-corroborated verdict) and dissociates only at shock-tube T — the two
  independent bearings agree Br₂ is stable. **✅ Phase 5 — cost ranking (ROUND 31, DOW-BROMINE-COST-01):** answered honestly
  and layered — no *modern* undercut is demonstrable from sourced single-benchmark data (Theorem 1, the degeneracy: a NaBr
  contained-Br proxy of the benchmark costs exactly the benchmark → brine ≥ mined; the user's "may not pass today" flag
  confirmed), while the *historical* undercut IS reproduced from sourced period prices as a one-sided economic bound (Theorem
  2: cartel 49 ¢/lb vs USGS-bounded US brine-route cost → ≈39 % pre-war, ≥ ≈80 % war-survival). **The DOW-bromine litmus is
  now fully exercised across every lane.** **✅ ROUND-35 modern source:** the 2026 SEC-filed Magnolia 1P forecast supplies
  an independent-from-price Smackover operating-cost basis. The all-in 2026 cash-outflow quotient is $2.5365/kg: below
  spot ($4.89) and spot-minus-30% ($3.42), while the minus-45% edge ($2.69) reverses under +10% opex uncertainty. This is
  model-derived, not realized cost, and is not admitted to route ranking. See
  `docs/research/DOW_BROMINE_MODERN_UNDERCUT_SCOPE_v0.1.md`.

---

## ✅ DONE — current shipped capability

**ROUND 35 — priorities 1–5** (branch `cip-ring-rules-dow-source-2026-09-09`) — parser-level written-neighbour
capture admits ring stereocentres; revised Rule 1b is isolated on the official IUPAC P-9 consumer; bounded Rule 4a
and revised Rule 5 name one-descriptor and one-opposed-pair cases; isotope-on-ring ties now proceed soundly into
Rule 2; and an SEC-filed modern Smackover model closes the previous DOW sourcing wall within explicit uncertainty
and provenance limits. Recursive Rule 4b/4c/6 stays fail-closed. Evidence:
`experiments/cip_ring_aux_rules_probe.py`, `tests/test_cip_ring_aux_rules.py`,
`docs/research/CIP_RING_AUX_RULES_SCOPE_v0.1.md`, and the DOW modern-undercut probe/receipt/doc/test.

**ROUND 34 — Lane B CIP items 1–5, completed in coherent dependency order** (branch
`cip-rules-3-4-5-ring-2026-09-08`) — Rule 3 E/Z naming, exocyclic-unsaturation ring admission,
aromatic-fused-to-saturated admission, two evidence-backed scope decisions, and the final cross-cutting Rule-1a
correction. Adversarial review falsified item 5's initial “ring representation / Rule 1b” explanation: the real defect
was a general recursive-top-branch traversal that disagreed with the FIFO pair queue in RDKit's Hanson/Mayfield
implementation. The fix covers Rule 1a and its Rule 2/3 passes, removes the now-ceremonial released-ring guard, and also
rejects contradictory directional markers rather than fabricating an E/Z descriptor.

**Current-status note:** ROUND 35 supersedes ROUND 34's ring-centre and isotope-ring deferrals; this section is the
historical record of what ROUND 34 established.

| Item | Lane | Result |
|---|---|---|
| **1 · CIP Rule 3** | B | **BUILT.** Acyclic constitutionally identical ligands can be ordered by seqcis/seqtrans (`Z > E`) only after Rules 1a and 2 tie. Missing, ambiguous, ring-double, or contradictory geometry defers. Evidence: `experiments/cip_rule3_ez_probe.py` + `tests/test_cip_rule3_ez.py`. |
| **2 · exocyclic ring unsaturation** | B | **BUILT.** Ring ketones/lactones/lactams and exocyclic C=C/C=N/C=S with all-single ring skeletons use the ordinary digraph. Internal conjugated ring doubles remain deferred. Evidence: `experiments/cip_exocyclic_ring_probe.py` + `tests/test_cip_exocyclic_ring.py`. |
| **3 · ring-on-centre Rules 4/5** | B | **VERIFIED DEFER.** Real consumers exist, but written-neighbour capture and recursive Rules 4/5 auxiliary descriptors are both unbuilt; `_on_cycle` remains fail-closed. The corrected comparator removed the earlier ring-ranking wall. Evidence: `experiments/cip_ring_centre_probe.py` + `tests/test_cip_ring_centre.py` + scope decision. |
| **4 · aromatic fused to saturated** | B | **BUILT.** Mancude acceptors retain exact partner-Z averaging while saturated spectator atoms retain real Z/mass. Evidence: `experiments/cip_aromatic_fused_probe.py` + `tests/test_cip_aromatic_fused.py`. |
| **5 · ring vs ring / isotope on ring** | B | **BUILT + BOUNDED DEFER.** Rule-1a-distinct ring pairs now NAME after the FIFO correction; seven pre-fix adversarial disagreements now match RDKit. Rule-1a-tied isotope ring pairs still defer before Rule 2 because Rule 1b may intervene. Evidence: `experiments/cip_ring_vs_ring_probe.py`, `experiments/cip_namer_probe.py`, tests, and corrected scope decision. |

**Verification boundary:** RDKit 2026.3.6 was a development-only oracle and was removed before the maintained baseline.
Its [source-pinned FIFO implementation](https://github.com/rdkit/rdkit/blob/613d0906052edb65b8f7e3f8efa1225b17a967c3/Code/GraphMol/CIPLabeler/rules/SequenceRule.cpp)
is an independent implementation bearing, while the committed probes preserve the input/output evidence. The 0-mismatch
finite sweeps establish no universal theorem about arbitrary graphs.

**ROUND 33 — Localized unsaturated-ring substituents NAME (the R32-surfaced gap, closed)** (branch
`cip-localized-ring-2026-09-08`) — the user's "unsaturated-ring-substituent CIP handling, full blast." A LOCALIZED
unsaturated ring (a UNIQUE Kekulé structure — cyclopropene, cyclohexene, cyclopentadiene, a cyclic enol ether, a localized
fused bicyclic) is released to the ordinary `_cip_digraph` (real z + real mass), so the R32 isolation now NAMES both
(`[C@](C1CC1)(C)(F)Cl` and `[C@](C1=CC1)(C)(F)Cl` → R). Over the UNCHANGED comparator, gated by two soundness gates + an
oracle sweep. Three bearings (butter-robot YAGNI, birdperson SOUND-BUT-HEED → the three-way release, dalembert SURVIVED +
proved `matching_count==1 ⟺ unique Kekulé` and found the Rule-1b gate). RDKit `rdCIPLabeler` (dev-venv-only) drove a
~5,600-molecule sweep → **0 mismatches** after two guards closed the fused/bridged ghost. Full detail: manifest §33.

| Item | Lane | What shipped |
|---|---|---|
| **CIP localized unsaturated rings** | B | `smartchem/smiles.py` (`_cip_mancude` sp³-spectator + three-way release `matching_count==1`→release / `≥2` no-spectator→average byte-identical / `≥2`+spectator→defer, returns `(blocked, averages, released)`; `_cip_rank_compare` **Rule-1b gate** — Rule 2 breaks a Rule-1a tie only when both ligands are trees; `_ligand_atoms` + `_cip_ranks` **multiring guard** — a released ring may only rank against ACYCLIC co-ligands). Names the localized class incl. localized fused bicyclics + reroutes furan/pyrrole/thiophene to real mass (Rule 1a byte-identical); benzene/pyridine averaging UNCHANGED; two saturated rings unaffected (no regression). Evidence: `experiments/cip_localized_ring_probe.py` (FROZEN_HASH; RDKit-free `validate()` + gated live `_rdkit_cross_check`, 30-case battery + 192-case localized sweep, 0 mismatches) + `tests/test_cip_localized_ring.py` + `docs/research/CIP_LOCALIZED_RING_SCOPE_v0.1.md`. **dalembert's theorem:** `need[a]=Σ(order−1)` Kekulé-invariant → acceptor matching count == true Kekulé count → `matching_count==1 ⟺ unique Kekulé ⟹ spelling-invariant`. **Boundary (sound deferrals):** exocyclic doubles, aromatic-fused-to-saturated, ring-vs-ring, isotope-on-a-ring. R32 harness updated (localized frags now NAME → ring-sub deferrals 24→12 (ring-vs-ring); acyclic 992/0 + crux UNCHANGED). |

**ROUND 32 — CIP Rule 1b (Rung 2): oracle-verified consumer investigation → VERIFIED DEFER** (branch
`cip-rule1b-consumer-defer-2026-09-08`, stacked on the open R31 branch) — the user's "then do 3 (CIP rung 2)." The sound way
to *do* Rung 2 was to investigate whether Rule 1b can be built without fabricating; it cannot (no in-scope consumer), so
building the `dup_rank` machinery = dead structure + mislabel-prone. RDKit `rdCIPLabeler` drove it as an external oracle
(dev venv only). Two bearings (birdperson SOUND-BUT-HEED + dalembert adversarial hunt, which PROVED the claim). No
code-feature built — a committed evidence harness + a scope decision. **The shipped Rule-1a+2 namer is UNTOUCHED —
byte-stable, NO golden moved.** Full detail: manifest §32.

| Item | Lane | What shipped |
|---|---|---|
| **Move 4 CIP Rung 2** · Rule 1b VERIFIED DEFER | B | `experiments/cip_rule1b_consumer_probe.py` (FROZEN_HASH; RDKit-free `validate()` + committed sweep generators + a gated live `_rdkit_cross_check`) + `tests/test_cip_rule1b_consumer.py` + `docs/research/CIP_RULE1B_CONSUMER_SCOPE_DECISION_v0.1.md`. **The finding:** Rule 1b has no in-scope consumer. **dalembert PROVED** the lemma (acyclic Rule-1a-tie ⟺ identical rooted constitution → Rule 1b constitutional → inert on trees; bites only with ring closures), corroborated by 25,212 constitutions + 300k shipped-comparator pairs + 30k molecules (0 Rule-1b consumers). In-scope deferrals are a distinct **unsaturated-ring-substituent** gap (992 acyclic → 0; 60 ring-sub → 24, ALL ring-unsaturation, ligands Rule-1a-distinct — isolation exact: `[C@](C1CC1)(C)(F)Cl` NAMES, `[C@](C1=CC1)(C)(F)Cl` DEFERS) + acyclic **Rule 3** (E/Z, `C[C@](/C=C\C)(/C=C/C)O`) — never Rule 1b. **birdperson** forced the 60-molecule ring-substituent sweep (the unexamined non-tree class) + reproducible committed counts; **dalembert** pinned the crux invariant (`duplicate_never_collides_with_real()`: a real terminal C/N/O/S node must outrank a same-Z duplicate leaf under `_cip_compare`) + the Rule-3 boundary. The harness doubles as a permanent differential validation of the shipped namer against the oracle. |

**ROUND 31 — DOW bromine COST RANKING (queue item 2's last lane): the DOW-bromine litmus's final open question** (branch
`dow-bromine-cost-ranking-2026-09-08`, stacked on the open R30 branch) — the user's "full blast do 2 (DOW cost ranking) ...
the DOW litmus may not technically pass with today's prices vs early-1900s prices." That flag is CORRECT; confirming it
rigorously (not fabricating a modern pass) is half the deliverable. Contract-first
(`docs/research/DOW_BROMINE_COST_RANKING_CONTRACT_v0.1.md`); two PARALLEL pre-build bearings (butter-robot NO-MODULE +
birdperson SOUND-BUT-HEED) + one evil-morty pass (math holds, 4 framing folds). **Additive** — a committed harness + a
receipt + a doc + a test; **NO importable module, NO ranker change, NO Cl₂ committed → byte-stable, NO golden moved.** Full
detail: manifest §31.

| Item | Lane | What shipped |
|---|---|---|
| **2 (cost)** · DOW brine-vs-mined cost ranking *(DOW)* | C | `experiments/dow_bromine_cost_probe.py` (FROZEN_HASH) + `experiments/dow_bromine_cost_recon_2026_09_08.json` + `tests/test_dow_bromine_cost.py` (9). **Theorem 1 (modern degeneracy):** a NaBr feedstock priced by contained-Br mass fraction from the same benchmark `q` costs EXACTLY `q` per unit Br₂ (mass factors cancel), so `brine = q + Cl₂ + process ≥ q = mined`, strict → **NO_UNDERCUT**, SCOPED ("not demonstrable from the sourced same-benchmark proxy," NEVER "brine worse in reality" — real well-brine bromine DOES undercut via an independent basis we can't source). **Theorem 2 (historical, one-sided ECONOMIC bound, route/industry level):** the sustained USGS US bromine unit value (PRIMARY, DS-140, metric tonne) upper-bounds the US brine-route marginal cost; vs the cartel's 49 ¢/lb → ≈39 % undercut pre-war (USGS 1904 = 30 ¢) and **≥ ≈80 %** war-survival (USGS 1908 = 10 ¢). The German dumping floor (15/12/10.5 ¢) is the CARTEL's price and the 27 ¢ re-export is arbitrage — NEITHER used as Dow's cost; Dow attributed only under a LABELLED assumption; cross-subsidy caveat aloud (predatory pricing is the named exception — economic, defeasible, NOT R30's physical law). **The only UNLOCK for a modern undercut is a sourced independent brine-feedstock cost basis** (Smackover/Dead Sea). [[a-one-sided-model-certifies-only-its-safe-direction]] |

**ROUND 30 — DOW-Br₂ collider/modified-Arrhenius kinetics (queue item 3b): the DOW-bromine litmus's rate half** (branch
`dow-bromine-kinetics-2026-09-08`, stacked on the open R29 branch) — the user's "keep going, full blast" (DOW-Br₂ kinetics
chosen at the fork). Contract-first (`docs/research/DOW_BROMINE_KINETICS_CONTRACT_v0.1.md`); a first-hand source + arithmetic
reproduction, two PARALLEL pre-build bearings (butter-robot PASS+TRIM + birdperson SOUND-BUT-HEED) + one evil-morty pass.
Two commits (`44af121` the model, `adc4cee` a separate gate guard). **Additive** (new sibling module; `KineticRef`/
`DEFAULT_KINETICS` untouched — recon-compliant) + one latent-on-seed gate guard; **byte-stable, NO golden moved.** Full
detail: manifest §30.

| Item | Lane | What shipped |
|---|---|---|
| **3b** · DOW-Br₂ collider / modified-Arrhenius kinetics *(DOW)* | B·C | `smartchem/experiment/collider_kinetics.py` — the modified-Arrhenius bimolecular collisional-dissociation model from the recovered Warshay primary (NASA TN D-3502; `kD = A·T^½·exp(-Ea/RT)`, `-d[Br₂]/dt = kD·[Br₂][M]`, 1200–1900 K). A NEW sibling because `KineticRef` is plain-Arrhenius s⁻¹ (the schema enforces the recon's "do not add to the first-order seed"). `dissociation_rate` reproduces kD(1825 K, Ar)≈1.574e6 (a TRANSCRIPTION self-consistency check, NOT independent validation); `pseudo_first_order_k` = `kD·[M]` ([M] REQUIRED, validated). **`collider_survival` certifies SURVIVES ONLY** — the irreversible forward fraction is a rigorous LOWER bound on the true reverse-inclusive fraction (the omitted reverse only adds Br₂ back), so a DEGRADES would be a fabricated refutation → every sub-SURVIVES fails closed to UNKNOWN; SURVIVES certified only in/below the window (above-window DEFERS — evil-morty F1). **The litmus answer:** Br₂ SURVIVES at kitchen T (PREDICTED, lower-bounded, cross-referenced to the INDEPENDENT R26 thermo ΔG₂₉₈=+161.65); dissociates sub-ms only at shock-tube T (the sourced reverse-free rate). Ar-only seed (Ne/Kr parked in the contract doc); committed harness (FROZEN_HASH) + 24 tests. |
| **gate guard** · no refutation from an out-of-window extrapolation | A·B | A separate anti-fabrication fix the Br₂ work surfaced: `_apply_duration_gate` flipped `DEGRADES→DEGENERATE` from an out-of-window (PREDICTED) extrapolated rate (birdperson VERIFIED: N₂O₅ at 360 K → a fabricated DEGENERATE). Now an out-of-window DEGRADES fails closed to UNKNOWN; the in-window DEGENERATE is preserved (surgical). RED-first regression. Latent on the seed → byte-stable. |

**ROUND 29 — Move 6: conditions distribute through a route's CAUSAL order (the withdrawn λ, re-aimed)** (branch
`move6-conditions-effects-distributive-law-2026-09-07`, stacked on the open R28 branch) — the user's "full blast move 6."
Contract-first (`docs/research/CONDITIONS_EFFECTS_DISTRIBUTIVE_LAW_CONTRACT_v0.1.md`); a 3-way recon + a first-hand
reproduction + two PARALLEL pre-build bearings (birdperson SOUND-BUT-HEED + butter-robot PASS) + one post-build
adversarial pass. **Additive + one internal API split; byte-stable on all digests/goldens (NO golden moved).** Full
detail: manifest §29.

| Item | Lane | What shipped |
|---|---|---|
| **Move 6** · conditions distribute through the causal partial order | A·B·C | `THE_ORBITAL §IX`'s withdrawn distributive law `λ : T∘W ⇒ W∘T`, re-aimed to the live route pipeline (the literal pairing — `pathway.py` monad × `conditions.py Conditioned` comonad — are DEAD islands; a literal build = the zero-call-sites trap). Fixes a **VERIFIED** order-dependence bug: the whole-DAG duration-survival verdict flipped `DEGENERATE`↔`UNKNOWN` purely on which independent branch a caller listed first (`_serial_hold_segments` charged one arbitrary `_topological_order` window; R23's gate flips on it). The gate now charges only the **forced-between** hold `{k : i→*k→*j}` (unavoidable in every schedule → order-independent), the disclosure the **possibly-between** hold (schedule-relative, never a verdict); `_judge_transition` threads two distinct sets (birdperson breach #4 — feeding the gate the possibly set fabricates a wrong `DEGENERATE`). MIN not MAX (a wrong refutation = fabrication; matches the critical-path precedent). LAW pinned: **linear-extension invariance** (`tests/test_dag_linearization_invariance.py` — verdict + hold multiset invariant under every branch permutation; the convergent join no longer flips on a schedule-avoidable hold; a genuine forced-between hold still flips; goes RED on pre-Move-6 code). NO new runtime object (a naming + a law). **birdperson:** breach #4 folded + MIN mandated + the makespan completeness gap & W3 spoken in the docstring. **butter-robot:** PASS on the minimal gate fix; possibly-between kept for disclosure (its cut-condition met — R15's documented purpose is convergent-DAG disclosure). Makespan/schedulability is out-of-scope named debt; §IX's literal adjunction stays correctly withdrawn. |

**ROUND 28 — Move-4 CIP half: node enrichment + CIP Rule 2 (mass number)** (branch
`move4-cip-rule2-enrichment-2026-09-07`, stacked off the open R27 branch) — the user's "go full blast on Move-4 CIP
node enrichment." Two PARALLEL pre-build bearings (birdperson SOUND-BUT-HEED + butter-robot YAGNI) + one evil-morty
adversarial pass. ADDITIVE + a **conscious `FROZEN_HASH` re-freeze** (the isotope deferral now names); byte-identical on
the distinct-Z slice; **NO response golden moved** (4 files changed, zero fixtures). Suite **4599 / 14 / 1** (= R27 4598
+ 1 new Rule-2 test). Full detail: manifest §28.

| Item | Lane | What shipped |
|---|---|---|
| **Move 4 CIP** · node enrichment + CIP Rule 2 | B | The CIP digraph node `(z, children)` → `(z, mass, children)` and **CIP Rule 2 (mass number)** wired in as its OWN full pass at the Rule-1a tie hand-off (`smartchem/smiles.py`: `_cip_mass`, `_cip_compare_rule2`, `_cip_rank_compare`, `_CipAmbiguous`). The isotope-only deferral now NAMES — `F[C@@](Cl)([2H])[3H]`→R, `[2H]O[C@@](Br)(Cl)O[3H]`→S — at any sphere the pairing is unambiguous (spheres 0–3 pinned in the battery). SOUND, not complete: a Rule-1a-tied-sibling pairing, an unknown mass, or a Rule-1b/3/4/5 tie is a NAMED DEFERRAL (all-pairs + is-None guards, transitivity-free). REUSES the sourced `standard_atomic_weight` (no re-derived table). **birdperson SOUND-BUT-HEED: 3 breaches folded** (adjacent→all-pairs sibling guard + per-pair precondition enforcement; `is None` before compare; mancude-superposition duplicate mass=None→DEFER). **evil-morty: no wrong-label kill** (4845-case isotope fuzz all enantiomer-invert + spelling-invariant); 1 coverage fold — sphere-2/3 correctly NAME but were unpinned → added to the battery + unit test, scope claim corrected. **Rung 2 (Rule 1b) DEFERRED to its own round** (both reviewers: soundness asymmetry — computed rank pre-pass vs sourced lookup; no half-wired `dup_rank` slot). |

**ROUND 27 — Move-3 provider-algebra formalization + Move-4 tension-A (CIP enrichment spec'd build-ready)** (branch
`moves-3-4-provider-category-cip-2026-09-07`, off `main@b2a5518`) — the user's "go full blast on move 3, do 4 as well
if you're able." Two pre-build design bearings (birdperson soundness + butter-robot YAGNI) + one evil-morty adversarial
pass. Additive + one small logic fix. Move 3 byte-stable; **tension-A intentionally moves ONE golden**
(`recompile_routes_found.json`) — a correct fabrication-removal (a non-acetic-acid C2H4O2 intermediate was borrowing
acetic acid's `isolable` → now an honest UNKNOWN), NOT a silent regression. Suite **4598 / 14 / 1** (= R26 4590 + 8;
skip/xfail unchanged). Full detail: manifest §27.

| Item | Lane | What shipped |
|---|---|---|
| **Move 3** · provider algebra as a generating set of the open SMC | B | A **formalization, not new machinery** — both bearings + recon found the categorical structure ALREADY EXISTS and is ALREADY LIVE (`open_core`/`OpenChemDiagram` IS the SMC with proven coherence; the registry's providers ARE a generating set with 3 AST-pinned live `enumerate` call sites; `route.open()` is the functor's word-action, live in `meta_compile`), so a `free_functor`/`TransformGenerator` runtime would be the zero-call-sites failure (THE_DIFFERENCE) reincarnated as a *trusted green mirror*. Shipped: `docs/research/PROVIDER_ALGEBRA_AS_SMC_GENERATORS_v0.1.md` (the honest functor claim, **correcting three over-claims against the tree**: NOT "free" → a *semantics functor* F; NOT "IR-COMMUTE is the coherence law" → a *forgetful naturality square*, coherence lives in `open_core`; NOT "typed generators" → *provenance tags*, composition is total) + `tests/test_provider_category.py` (three non-vacuous laws w/ non-vacuity controls: provenance-out-of-identity, F quotients symmetric cuts / faithful on reactions, forget/open naturality) + a legibility docstring pointer. A false "branch-order interchange" law was DROPPED (grounding caught it: the ordered boundary makes it reconcilable only up to `open_core`'s already-proven braid). No source runtime, no digest churn. |
| **Move 4 tension-A** · `resolve_stability` keyed on canonical structure | B·C | `smartchem/experiment/composability.py::resolve_stability` no longer borrows a same-formula sibling's sourced record ([[a-reaction-key-by-formula-borrows-a-rate]], the guard now LIVE on default data). A KNOWN isomer → its NAMED record or a loud None; an UNREGISTERED isomer of a KNOWN formula (`known_compounds` non-empty, none matched) → None (fail-closed); a NOVEL formula (`known_compounds` empty) → the formula fallback (the injection lever). Closes the ester borrow (4-aminophenyl acetate ↮ paracetamol's onset) AND — evil-morty MEDIUM fold — the GENERAL class (ethynol↮ketene, 2-aminophenol↮4-aminophenol). Regression: `test_composability.py::TestStabilityKeyIsStructureNotFormula` (3 guards). **Moves one golden** (`recompile_routes_found.json`): a non-acetic-acid C2H4O2 recompile intermediate stops borrowing acetic acid's `isolable` (fabricated COMPOSABLE → honest UNKNOWN, ranking reorders downstream) — a-reaction-key-by-formula-borrows-a-rate firing on a live route. |
| **Move 4 CIP** · node enrichment | B | **Spec'd build-ready, NOT built** — `docs/research/CIP_NODE_ENRICHMENT_SCOPE_DECISION_v0.1.md` (soundness-critical + `FROZEN_HASH`-moving ⇒ its own reviewed round; the R19 ONLOAD-REDERIVE precedent). Queued above. |

**ROUND 26 — Move-2 M2b (objective LIVE in the ranker) + DOW-thermo (sourced Br₂ dissociation)** (branch
`m2b-dow-thermo-2026-09-07`: DOW-thermo `67d6b14`, M2b `a6ad71b`, docs this commit) — the M2-FP objective wired into
the core route/DAG scorer, and the DOW-Br₂ *thermodynamic* verdict unlocked by a sourced data add. Two builds, each
`design → recon → build → reproduce → review → fold → verify`; ranking-only + sourced data add ⇒ NO golden regen
(digests byte-stable). Suite **4590 / 14 / 1** (= R25 4579 + 11; skip/xfail unchanged ⇒ P2 holds).

| Item | Lane | What shipped |
|---|---|---|
| **M2b** · Move-2 objective LIVE in the ranker | B·C | `_pareto_front_indices` (peeling `pareto_optimal` into non-dominated layers) runs on EVERY `rank_routes`/`rank_dags` call; two NEW tiers ride `_route_score`/`_dag_score` (tier-identical — the DAG-RANK-01 promise) between the worst-node feasibility SIGN and equilibrium: a Pareto **FRONT** over `PhysicsProduct(net ΔG, survival)`, then the additive-**ΔG magnitude** (the Hess functor). Tie-break decision: incomparable-complete routes SHARE a front (never a fabricated dominance), presented by ΔG then discovery order — the front index is the honest dominance datum, the two axes never collapsed into a scalar. The ΔG-magnitude axis is the broadly-live surface; the two-axis front is DATA-GATED (survival None without a seeded serial-hold rate) — inert on the default seed, the R25-`frontier` discipline. **birdperson design-fold** (peel termination + index remap; SIGN above the additive refinement; leapfrog/tie DISCLOSED; a NON-VACUOUS front-flip test). **evil-morty KILL-1 fold:** the ΔG-magnitude `None→0.0` sentinel rewarded ignorance inside the UNFAVORABLE class → the magnitude tier now fires ONLY in the FAVORABLE class (net guaranteed known+negative). Ranking-only, byte-stable. |
| **DOW-thermo** · the DOW-Br₂ thermodynamic verdict | B·C | Sourced Br(g)/Br₂(g)/Br₂(l) ΔfH°/S° from the CODATA Key Values (fetched + cross-checked 2026-09-07: NIST WebBook + the official CODATA table, two agreeing bearings; JANAF/Chase within ±), NOT recited. Frozen CODATA seed extended (FROZEN_HASH re-frozen), gas records mirrored into the live `SEED_THERMO_REFS` (single-valued `for_formula`). `Br₂ → 2 Br•` now FIRES, calibrated to known chemistry: ΔH=+192.83 kJ/mol (= the Br–Br bond enthalpy), ΔG₂₉₈=+161.65, σ=0.26 ⇒ UNFAVORABLE (Br₂ stable against dissociation at 298 K). HBr stays UNKNOWN (no formula-borrow). The R25 data-gated fail-close is consciously superseded. Reviewed by evil-morty (values/calibration/no-borrow/frozen-hash verified). |

**ROUND 25 — Move-1 keystone Rungs C + D and Move-2 M2-FP** (branch `move1-rungs-c-d-m2fp-2026-09-07`:
Rung C `3e34265` + M2-FP `a8b61ce` + Rung D `35a5e64` + review fold `d42d7a2`) — three rungs of the
categorical reorientation, additive/byte-stable/fail-closed, each reviewed (evil-morty ×2 + birdperson).
Suite **4579 / 14 / 1** (= 4536 + 43; skip/xfail unchanged ⇒ P2 holds, legacy xfail preserved).

| Item | Lane | What shipped |
|---|---|---|
| K-C · Move-1 keystone **Rung C** (the pipeline speaks open-diagram) | A·B | `ExperimentRoute.open()` / `SynthesisDAG.open()` project a whole multi-step synthesis onto ONE `OpenChemDiagram` via a new **port-level `plug_all`** partial-pushout primitive (a real step carries byproducts + fresh reagents, so its cod ≠ next dom — the whole-vessel `then`/`Reaction.then` cannot chain it; `plug_all` glues a chosen SUBSET, keeps the rest boundary — the open-morphism composition the contract promised). Gluing is BY TOKEN not port position. `net_reaction()` = the conserving overall equation of any saturated diagram (distinct from `close()`, which reduces only a whole-vessel linear chain; a catalytic/cyclic net is NOT the identity). Gates: saturation + conservation-as-closure (P1/P3), provenance DAG deps == `dag.edges` (P4), interchange invariance + a boundary-order tripwire. **Closes 3 Rung-B debts:** (2) token-gluing beats a canonical species re-sort; (3) `_derive_provenance` fails CLOSED on a structurally-identical-step collision; (5) `edge_incidence` (distinct generators) replaces terminal count. |
| M2-FP · Move-2 functorial-physics product | B·C | `Δ_rG` recognized as the **additive functor** `G: Process→(ℝ,+,≤)` — Hess's law IS the functoriality (`net_ΔG(route)==Σ steps`, pinned non-vacuously on a sourced steam-reforming route). `RouteFeasibility.net_delta_g_kj` surfaces it as a property (no digest/golden move) — DISTINCT from `verdict`, the worst-node sign. `PhysicsProduct(ΔG, survival)` = the **Pareto product** with `dominates`/`pareto_optimal` (no scalar collapse; "favorable≠fast"; unknown axis incomparable, fail-closed). `FreeEnergyDecoration` = a 2nd instance of the `open_core` decoration slot (law-tested). **Anti-fabrication fix (both reviewers):** `estimate_thermo` empty-group assignment → None (was fabricating `(ΔfH°=0,S°=0) DERIVED` for bare halogens/HBr); DOW-Br₂ now fail-closes on Br• genuinely UNKNOWN. Scorer unchanged (survival still absent from `_route_score` — tracked debt). |
| K-D · Move-1 keystone **Rung D** (closing = compiling) | A·B·C | `compile_open(target, ...)` treats "synthesise from stock" as the open spec, CLOSES it with the shipped bounded route search, projects each candidate via Rung C, and scores by the M2-FP objective — the **load-bearing call site** for Rungs B/C + M2-FP. `MetaCompilation.by_free_energy` (the LIVE additive-ΔG ranking, new over `compile_synthesis`) + `frontier` (the two-axis Pareto, DATA-GATED: survival is sourced-kinetics-gated so usually empty — the DOW-Br₂ discipline). Fail-closed: uncompilable spec → no closures. `ClosedCompilation` validates its route (no half-built objects). |

**ROUND 24 — Move-1 keystone Rung B** (branch `move1-rung-b-open-chem-diagram-2026-09-07`, docs-fold `de21c06` + code `944ad8c`; **MERGED via PR #19 → `main@5f1b3e3`**) — the open-diagram chemistry-morphism backbone's first buildable increment, **alongside** `Reaction`, additive/byte-stable/fail-closed. `smartchem/open_core.py` (domain-neutral open-SMC core: multi-terminal `Hyperedge`s, a monoidal `Decoration` slot, `then`/`tensor`/`identity`/`braid`, a hyperedge+decoration-aware `canonicalize` — WL + bounded brute force, `CanonicalizationBudgetExceeded` fail-closed; `open_diagram.py` untouched) + `smartchem/open_chem_diagram.py` (`OpenChemDiagram`: species-typed ports, reaction hyperedges, three `PortState`s, `from_reaction` functor, `close()` to a byte-identical `Reaction`) + `ExperimentStep.open()` (`+22` lines) + `tests/test_open_chem_diagram.py` (26 tests). Ritual: design-fold → recon (2) → build → reproduce → **evil-morty + birdperson** → fold → verify. **evil-morty [HIGH, VERIFIED] fold:** the first cut's `canonicalize`-equality was **not a congruence** — a `compare=False` provenance frontier that `then_combine` consumed to decide the compared `deps` made `f ≡ f;id` yet they diverged under a later `then` (and `(f;id);g` crashed on `close()`); **fixed** by deriving provenance from the composed **topology** (a node shared between a product terminal and a reactant terminal ⇒ a dependency) ⇒ a pure function of the canonical topology ⇒ congruent, wires handled for free. **Two apex kinds:** conservation is a genuine additive **decoration** (homomorphic sum over generators — the ΔG/survival shape); provenance is a topology **read** (not a decoration). **birdperson [SOUND-BUT-HEED]:** gate honestly delivered, legacy xfail (`test_laws.py:330`) preserved-not-flipped, P2 additive-only; added the conservation `is_balanced ⟺ CONSERVING` cross-check. Verified: full suite 4 batches **4536/14/1** (= 4510 + 26; skip/xfail unchanged ⇒ P2 holds). New lesson: `a-quotient-must-be-a-congruence`.

| Item | Lane | What shipped (dev branch) |
|---|---|---|
| K-B · Move-1 keystone Rung B | A·B | `OpenChemDiagram` alongside `Reaction` on a generic open-SMC core; the 3-part gate GREEN — (1) interchange/braid/hexagon under the `canonicalize` quotient + fail-closed budget refusal; (2) real non-test consumer `ExperimentStep.open().close()` reproducing the `Reaction` certificate byte-for-byte (P3); (3) P4 provenance round-trip + interchange-equivalent assemblies yield equal provenance. Conservation-as-closure (OPEN ⇒ UNDECIDED). Congruence pinned by regression. Rungs C (pipeline migration) / D (meta-compiler) follow. |

**Categorical reorientation — Move-1 keystone (design contract, no code)** (merged **PR #17 → `main@f6e887a`**; contract
commit `d6c61cd`, `docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md`) — the **keystone** of the categorical
reorientation, spec'd as a design gate. Proposes an open-SMC chemistry morphism backbone (reuse `open_diagram.py`'s
already-lawful composition core; conservation as a **closure predicate** not a construction gate; the
conservation-at-construction theorem preserved exactly as the closed-diagram special case — obligations P1–P4). Hardened
pre-commit by two adversarial reviews (evil-morty + birdperson) that **converged on an unsound acceptance gate**; resolved
via the **"central knot"** — two kinds of order (genuine causal DAG, preserved / spurious linearization of independent
steps, quotiented) at two levels (coarse **structural ports** carry the SMC/interchange laws; an interchange-invariant
**`Config` apex decoration** carries conservation-closure; a **partial-order record** carries provenance). Re-specified
gate = interchange under the honest `canonicalize` quotient + a **real non-test consumer** (`ExperimentStep.open/.close`
round-trip) + a P4 demonstration; the legacy `Reaction` xfail preserved-and-annotated, not flipped. **This is the build
gate for Rung B (queued below).**

**ROUND 23** (branch `categorical-duration-functor-2026-09-07`, code `8e97664`, merged **PR #16 → `main@0e6bba0`**) — the **categorical
reorientation's first rung** (Move 2: physics as a functor): the duration-aware survival verdict wired into core E1, closing
the core-E1 half of queue item 3. `design → recon (2 mappers) → build → reproduce → evil-morty → fold → verify`; **additive**
(3 source files + 1 new test), **byte-stable** (the survival field is `compare=False` digest-excluded; the seed kinetics hold
only N₂O₅/cyclopropane so no existing route is assessed → no golden churn). One evil-morty MEDIUM soundness fix folded before commit.

| Item | Lane | What shipped |
|---|---|---|
| DURATION-SURVIVAL-01 (item 3, core-E1 half) | B·C | E1's `_judge_transition` now **consumes** the DAG-HOLD-01 serial hold: where an intermediate has a SOURCED first-order decomposition rate (`stability_horizon`, matched on canonical structure, never formula), a duration-aware survival reading MOVES the composability verdict (`smartchem/experiment/composability.py` `_apply_duration_gate`/`_hold_survival`/`_survival_product` + `dag.py` `_serial_hold_segments` + `tests/test_duration_survival_gate.py`). It only ever **TIGHTENS**: `DEGRADES → DEGENERATE` (even where the onset table was silent — a sourced kinetic refutation beats a missing record), `MARGINAL → UNKNOWN`, `SURVIVES` confirms without upgrading, and never touches an already-`DEGENERATE` base. The functor: `Transition.surviving_fraction` (digest-excluded) + `route_surviving_fraction` on `Composability`/`DAGComposability` = the product of per-transition fractions, the survival monoid functor `S: Process → ([0,1], ×)` (the hold survival itself composes multiplicatively over its segments). **evil-morty MEDIUM fold:** survival is read over the intervening SIBLING steps' OWN declared temperatures (the temperatures the intermediate idles at) — NOT a producer/consumer endpoint's, which could mint a false DEGENERATE *and* launder a real degradation — and **fails closed** on any undeclared hold temperature or non-finite rate (never a verdict on a temperature the model doesn't know). `survival_verdict` promoted to a shared public band-policy helper (no drift). **Still remaining on item 3:** the DOW-Br₂ collider/modified-Arrhenius half (sourcing/modeling-gated), and linear-route holds are unmodeled (only DAG serial holds carry a hold) — see QUEUE + TRACKED DEBT. |

**ROUND 22** (branch `codex/mancude-duration-sourcing-2026-09-07`, code `07651a0`, isolated from `main@043a3cd`) — neutral mancude CIP
extension, duration admission fix, and source-access corrections. Full verification and source hashes are recorded in
`experiments/validation/round22_2026_09_07.json`; the source and external-oracle reports preserve the claim boundaries.

| Item | Lane | What changed |
|---|---|---|
| CIP-MANCUDE-01 | B | Exact rational multiple-bond duplicate atomic numbers over distinct feasible partner positions in bounded neutral C/N/O/S mancude rings, including supported fused systems. Ring topology recognizes aromatic and explicit Kekulé inputs through the same path. Fixes the independently discovered uppercase pyridyl/diazinyl **wrong-label** mirror pair; names aryl/heteroaryl centres while identical ligands remain unnamed. Primary VS032/033 anchors, fractional-number controls, three fail-closed work caps, and optional accurate-RDKit panels (1,224 + 1,134 representation cases) are reproducible. Higher-rule ties and unsupported ring chemistry remain deferred. |
| DURATION-UNIT-01 | B·C | `ConditionEnvelope.duration` requires exactly `min`, through direct construction and replay. Non-minute callers must convert explicitly. Existing valid minute payloads and route digests are unchanged; 59 new unit/admission controls. Core E1 still needs an intermediate-hold interpretation and seconds conversion. |
| DOW-SOURCE-RECON-01 | B·C | Recovered Warshay's NASA Br₂ initial-dissociation primary and an approved Los Fresnos Cl₂ procurement offer. Both blanket primary-access claims are corrected. These are source receipts, not new default seeds: collider/modified-Arrhenius/hold modeling and package-aware pricing/feedstock integration remain open. |

**ROUND 21** (branch `cip-load-stability-2026-09-06`, code `6e14d51`) — 1 build, full-blast on **queue item 2** (the L
round); `design → external review (ChatGPT, folded against the tree) → recon (8-agent) → build → reproduce → evil-morty →
fold → verify`; **additive** (new codecs + a `compare=False` field + a load-time check in `service.py`, plus a new test
file), **route identity byte-stable** (no schema bump, no golden churn — the default wire is byte-identical); one VERIFIED
evil-morty finding + one LOW folded:

| Item | Lane | What shipped |
|---|---|---|
| ONLOAD-REDERIVE (item 2) | C | **On-load re-derivation of the composability + physical + ranking axes** (`smartchem/service.py` + `tests/test_onload_rederivation.py`). Closes the free-text trust boundary PROCESS-ADMIT-01 left open: a route non-FITS for a **composability** or **physical** reason (or with fabricated **ranking** verdicts) could be bare-relabeled to FITS and admitted on load. Structural close, **no key**. A thick **replay payload** (the route's complete steps: target/reactants/products/reagents + full 10-field `ConditionEnvelope`) is carried `compare=False` (digest-excluded → route identity byte-stable) and emitted opt-in (`include_replay`, default off → default wire byte-identical). `response_from_payload(require_verified_admission=True)` **reconstructs** the exact route/DAG, re-projects it through the SAME producer path (`rank_routes`+`of_fit` / `of_dag`) under the response's pinned eval-context, and requires `resummary == claimed` — ONE equality subsuming route-binding (`reconstruct.digest == route_digest`, closing the substitution hole ChatGPT found), the combined fold verdict, the composability + 4 ranking verdicts, and the process/edge projections. **Fail-CLOSED**: a FITS dossier with no payload is UNVERIFIED, refused (the **deletion door** the adversary found — closed with NO schema bump, lower blast than the reviewer proposed). Reconstruction re-runs the real `ExperimentStep`/`Route`/`DAG` constructors (conservation, linearity, acyclicity); molecule codec mirrors the digest-stable `_graph_payload` (positional, no SMILES re-parse). Edges int-coercion trap fixed (`_exact_int_pair`). **evil-morty folds:** (F1 MEDIUM, VERIFIED) keyless **eval-context relaxation** — the box is built from the response's own request, so a keyless request-relaxer could re-derive an out-of-bounds route to FITS; corrected the docstring overclaim (residuals are TWO) + added `expected_request_digest` (consumer pins its request; a signature closes it cryptographically), both directions pinned. (F2 LOW) `serial_holds` was `compare=False` → the DAG branch now re-derives + checks it. Design: `docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.2.md` (folds the ChatGPT external review against the tree; supersedes v0.1). |

**ROUND 20** (branch `cip-load-stability-2026-09-06`) — 1 build, full-blast on **queue item 1**; `design → recon → build →
reproduce → evil-morty → fold → verify`; **additive to the engine** (new `_cip_*` in `smiles.py` + harness + test), plus a
**conscious supersession** of the ID-STEREO-01 same-element *deferral* tests (the deferral was "not built yet", now built);
byte-identical on the distinct-Z slice; one self-caught soundness bug + one evil-morty finding folded, two residuals
discharged/documented:

| Item | Lane | What shipped |
|---|---|---|
| ID-STEREO-CIP-NAMER (item 1, the namer) | B | The **general CIP R/S namer** (`smartchem/smiles.py` `_cip_ranks`/`_cip_compare`/`_cip_digraph` + `experiments/cip_namer_probe.py` + `tests/test_cip_namer.py`) — closing item 1 (the R19 oracle unblocked it). CIP **Rule 1a** priority via a hierarchical digraph, **breadth-first, branch-by-branch with need-to-know pruning** (Hanson et al. 2018) — the fix for the R13/R14 **depth-first** bug (`C[C@H](CCC)C(C)C`: DFS says S, truth **R**). Phantom atoms for multiple bonds + ring closures; reuses the shipped `_perm_parity ^ sense` emit line (byte-identical distinct-Z). Now NAMES the common same-element case (amino acids/sugars: L-alanine S, the **L-serine S / L-cysteine R flip**, glyceraldehyde R). **SOUND, not complete**: Rule 1b/2/4/5 ties and aromatic-reaching ties DEFER (a wrong R/S is worse than none). Committed harness with 5 layers (textbook absolutes, oracle cross-check, R14 differential, branch-paired-vs-pooling proof, 840-case alkyl pool), FROZEN_HASH. **Self-caught soundness fix:** a fixed Kekulé wrongly NAMED the di-2-pyridyl false centre → lazy aromatic-boundary guard (atomic number still decides, onward aromatic connectivity withheld). **evil-morty ("could not make it lie"):** folded a spurious over-defer on an aromatic ring in an already-decided branch; discharged the exocyclic-aromatic residual; documented the comparator-transitivity residual. |

**ROUND 19** (branch `cip-load-stability-2026-09-06`) — 3 builds + 1 recorded decision; each build `design → recon →
build → reproduce → evil-morty → fold → verify`; **additive** (5 new files + additive edits to `service.py`, no existing
behaviour changed); two evil-morty passes found real weaknesses, all folded or documented and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| CIP-ORACLE-01 (item 1, the oracle) | B | The committed **geometric handedness oracle** (`experiments/cip_geometry_oracle_probe.py` + test) — meeting item 1's oracle gate. Builds synthetic tetrahedron coordinates from the OpenSMILES sense bit, reads R/S off a real signed volume (lowest priority away, trace 1→2→3), takes priorities as an INPUT so it decouples geometry from priority-ranking. Green on an exhaustive 48-case {F,Cl,Br,I} battery + two textbook absolute anchors ([C@H](F)(Cl)Br = S, L-alanine = S from one derived convention). **evil-morty (MED-HIGH) right-sized the claim:** it is algebraically `perm_parity ^ sense`, so the 48-case sweep confirms ONE constant, not 48 bearings — it buys one independent bit (a global convention-flip guard) + the decoupling instrument, NOT a ranking-bug catch. Folded: docstrings corrected to that honest scope, `cip_labels` pinned into the frozen hash (so a regression in the *audited* slice reddens it too), the algebraic identity + an external-absolute pipeline check baked into the tests, the dead degeneracy-guard overclaim fixed. |
| DURATION-STABILITY-01 (item 3, the primitive) | B·C | The duration-aware **survival primitive** (`smartchem/experiment/stability_horizon.py` + harness + test) — the time axis on known physics. `f = exp(-k t)`, k = A·exp(-Ea/RT) mirroring the L1 rate engine (R pinned equal, no drift); non-vacuous on N₂O₅ (SURVIVES 60 s → MARGINAL 1 h → DEGRADES 6 h at 298 K), DERIVED/PREDICTED graded, instrument-calibrated (k(298) reproduces the measured 3.38e-5 to ~5%). Fail-closed UNKNOWN with no sourced rate; the compound→rate bridge is structure-keyed + direction-specific (cyclopropane/propene C₃H₆ collision proves no isomer or product borrows a rate). Standalone — NOT wired into core E1 (a stated boundary). **evil-morty SIGNED the anti-fabrication core** (no fail-open, no overflow/NaN reaches a verdict); folded 3 LOW: `is_sourced` docstring softened, an `isfinite` guard added (fail-closed on a non-finite injected record), the "decomposition"→"first-order consumption" naming fixed; documented the reactant-coefficient rate-convention assumption (tracked debt). |
| DAG-HOLD-MR-01 (item 2b) | C | `serial_holds` on `RankedDAGSummary` — the DAG-HOLD-01 serial-schedule hold made machine-readable as `(producer, consumer, minutes)` triples (was a human note only). **Digest-EXCLUDED** (`compare=False`): fully determined by `edges` + `process_requirements`, so it adds no identity and every existing DAG digest stays byte-stable; schema `v1alpha3→v1alpha4`, descriptor `v1alpha15→v1alpha16`, one golden (`response_schema.json`) regenerated, non-vacuous (the 40-min DAG carries `(0,2,40.0)`). |
| ONLOAD-REDERIVE (item 2, decided not built) | C | **Scope decision recorded, build-ready** (`docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`) — item 2's gate was "a scope decision". Resolved: opt-in **digest-excluded** thick per-step payload + a load-time coherence check (mirroring PROCESS-ADMIT-01), protection-equivalent to folding into `result_digest` without changing every route identity. The build (new Molecule/Envelope serializers + conservation-certified route reconstruction + 4 coherence checks) is larger than items 1+2b+3 combined and touches the module that gates every compile, so it is scheduled as its own round rather than rushed. |

**ROUND 18** (commit `5f83f6a` on branch `observability-electrochem-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; **additive** (6 new files + 1 package `__init__` re-export — new exports
only, no schema/golden/compiler-behaviour change); a 6-lens evil-morty workflow found **6 real weaknesses**, all folded
(4 code) or documented (1 boundary + 1 docstring) and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| OBSERVABILITY-01 | C·B | The **three-axis Observability Score** (`smartchem/observation/observability.py`) — cheap epistemology as a ranking objective. A SOURCED `OBSERVABLE_SIGNATURES` table keyed on **canonical structure** (Br₂ the DOW flagship: orange-red colour + phase separation; I₂ the contrast with the starch test), citations REQUIRED (§10.4). The `ObservabilityProfile` keeps **process / identity / purity as three SEPARATE axes**, never one number (invariants 5 & 7 — there is no `overall_score`); Pareto ranking (`observability_dominates`/`_frontier`) that refuses to collapse (a process-strong route does NOT dominate an identity-strong one — incomparable). Non-vacuous: Br₂ (2,1,0) dominates I₂ (1,1,0). Negation-aware bridge to ROUND-17's VERIFICATION bucket. Self-contained (NOT wired into the CostVector — that axis wire-in is a deferred schema bump). Folds: **(HIGH)** corroboration read "colourless" as corroborating COLOUR (the ROUND-17 negation fold via morphological absence) → word-boundary + extended veto; **(MED)** corroboration ignored the signature axis (process→identity leak) → axis-aware evidence; **(MED)** `sourced` was a stored forgeable flag → a computed table-provenance property. |
| ELECTROCHEM-01 | B·EM | The **electrochemical/EM bridge** (`smartchem/electrochemistry.py`) — SOURCED standard reduction potentials (CRC / Bard & Faulkner, known physics) → cell potential, ΔG° = −nFE°, spontaneity, Nernst, electrolysis voltage. Fills the documented fail-closed `open_circuit_voltage` hole in `smartchem/cell.py` for the standard-state case; reuses that module's Faraday law. **Closes the DOW loop with ROUND-17**: `Cl2 + 2 Br- -> Br2 + 2 Cl-` is not only enumerable but **SPONTANEOUS** (E°cell = +0.271 V, ΔG° = −52.3 kJ/mol), the reverse non-spontaneous — the known-answer calibration. Keyed on the couple's structural digest, fail-closed UNKNOWN, W3 (thermodynamic tendency, never rate). Folds: **(MED)** `gibbs_j_per_mol` took n as an unvalidated guess → derive n = lcm(cathode.e, anode.e), refuse a wrong one; **(MED, documented)** aqueous phase-scope boundary (F5, tracked debt); **(LOW)** citation-guarantee docstring overclaim corrected. |

**ROUND 17** (commit `6761350` on branch `process-observation-redox-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; **purely additive** (`git diff --stat main` empty — six new files, zero
edits to existing code, so no schema/golden blast radius); both evil-morty red-teams found REAL weaknesses, all folded and
pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| PROCESS-OBS-01 | C | The **read-only `ProcessObservationIR` evidence-ingress layer** (contract P1) — the poor-man ethos made computational. A new `smartchem/observation/` sibling package (like `smartchem/evidence/`: reuses `Digestible`+`ReactionDirection`, never enters the executor registry, drags zero heavy modules): an immutable source-fragment IR, the five whole-path **capability bundles** (MATERIAL/CAPABILITY/VERIFICATION/CLOSURE/SCALE → EVIDENCED/GAP/BLOCKED, fail-closed), a **no-Frankenprocedure** merge, and a read-only **projection gate**. All 7 contract invariants enforced in code (`provenance_digest` computed not stored; NO readiness field). NOT wired into the response — no schema/golden change. Folds: **(CRITICAL)** negation-blind matcher read "no containment" as containment → whole-support-text negation veto; **(HIGH)** silently-omitted calibration passed a numeric conclusion → fail-closed (positive calibration required), test corrected; **(MEDIUM)** merge spliced different reactions under one self-declared context → identity+direction agreement required. |
| REDOX-DISPLACE-01 | B | The **coupled half-reaction combiner** — the DOW enumeration wall falls. `HalfReactionCouple` (molecular redox couple) + `combine_half_reactions` (electron-balanced by LCM) → a conservation-checked `RedoxDisplacementEdge` that rides the **unchanged** search through an opt-in `RedoxDisplacementProvider` (absent from `DEFAULT_TRANSFORM_REGISTRY`, like heterolytic/redox). Enumerates `Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻` — the 1:2 recon proved unreachable by `redox_edges` (single-species) or `capped_scissions` (1:1). Committed harness (`experiments/redox_displacement_probe.py`, FROZEN_HASH). Fold: **(MEDIUM)** the certificate proved conservation but not redox-ness (a hand-built edge accepted a fabricated electron count / fictitious labels / an identity `Na→Na`) → an electron-ledger verification ties `electrons_transferred` + labels to the actual charge redistribution. |

**ROUND 16** (commit `c9e0fed` on branch `dag-thermo-bromine-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; both evil-morty findings folded and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| DAG-THERMO-01 | C·B | A **per-node thermochemical roll-up** feeds convergent-DAG ranking, so a DAG ranking is now as rich as a linear one. `dag_thermo_rollup` aggregates the four sourced per-reaction verdicts (selectivity/feasibility/equilibrium/kinetics) worst-node-dominated — reusing the *same* per-step providers, default tables, and worst-folds the linear `fit_route` runs; `_dag_score` now mirrors `_route_score` tier-for-tier; `RankedDAGSummary` (schema v1alpha3) surfaces all five verdicts, parity with the route summary. RANKING-ONLY — never changes a section-11 status. Folds: non-vacuous selectivity/kinetics wiring test (a real FAVORED DAG, was all-UNKNOWN); reverted a `rank_dags` table-param trap that re-opened the exact ROUND-15 divergence. |
| DOW-BROMINE-01 | B·C | **Phase 1 of the DOW-bromine litmus:** elemental bromine is now a first-class **SOURCED, USGS-priced** commodity ($2.70/kg 2024, MCS 2026, bromine content), added to both the frozen provenance seed and the live copy; new `INDUSTRIAL` availability tier (not a kitchen commodity — the DOW insight, encoded); costed end-to-end through `basket_cost_vector`/`cash_floor`. Folds: the basis now discloses the figure is a compound-dominated import blend normalized to contained bromine, not an elemental-Br₂ spot price. |

**ROUND 15** (merge `978da9b`) — DAG-HOLD-01 (serial-hold disclosure), DAG-RANK-01 (best-first DAG ranking, structural).
**ROUND 14** (`574a3e2`) — DAG-BENCH-01, STEREO-DOSSIER-01, ORGANIC-PRICE-01 (methanol/Methanex) + 2 refutations.
**Prior rounds (R5–R13):** resonance-canonical identity + caps, the 4 IR-COMMUTE families, per-route/DAG process
re-derivation, cost/affordability, USGS inorganic pricing, combined-verdict HMAC, the sound distinct-Z CIP slice. Full
ledger: `UPTAKE_MANIFEST_v0.5.0a1.md §5`–`§16`.

---

## 🎯 QUEUE — what needs doing, ranked

Ranked by value ÷ cost. **Size** = build effort (S/M/L). **Horizon** = short (cheap, self-contained) / medium (needs a
scope decision or a real build) / long (blocked on a sourcing or oracle wall). *(DOW)* = advances the DOW-bromine litmus.

> **ROUND 23 CLOSED item 3's core-E1 half** — the duration-aware survival verdict is now wired into E1 (`DEGRADES →
> DEGENERATE` over a sourced serial hold, the survival monoid functor `S: Process → ([0,1], ×)`). What remains of item 3 is
> the **DOW-Br₂ collider/modified-Arrhenius kinetics** half (item 3b below), which is sourcing/modeling-gated, not
> build-gated. **ROUND 21 CLOSED item 2** — on-load re-derivation of the composability + physical + ranking axes shipped (the
> ChatGPT external review was folded against the tree first; two holes it/the adversary found were closed before code).
> **ROUND 20 CLOSED item 1** — the general CIP breadth-first **namer** (Rules 1b/2/4/5 + aromatic Kekulé-averaging
> sound-deferred, tracked below).

> **ROUND 26 CLOSED M2b + DOW-thermo** (the user's numbered next-steps 1 & 2). M2b wired the M2-FP Pareto product
> (`PhysicsProduct`/`pareto_optimal` + the additive-ΔG functor) LIVE into `_route_score`/`_dag_score`; DOW-thermo sourced
> Br(g)/Br₂(g) and the DOW-Br₂ dissociation verdict now fires (UNFAVORABLE, calibrated). See the DONE ledger + manifest §26.
> **ROUND 29 CLOSED Move 6** — conditions distribute through a route's CAUSAL order, not an incidental linearization
> (the `THE_ORBITAL §IX` withdrawn λ, re-aimed to the live route pipeline). It fixed a VERIFIED order-dependence bug: the
> whole-DAG duration-survival verdict flipped DEGENERATE<->UNKNOWN purely on which independent branch a caller listed
> first. The gate now charges only the FORCED-BETWEEN (unavoidable-in-every-schedule) hold; the linear-extension
> invariance law is pinned. See the DONE ledger + manifest §29.
> **ROUND 30 CLOSED item 3b** — DOW-Br₂ collider/modified-Arrhenius kinetics, the DOW litmus's decomposition RATE half.
> The Warshay shock-tube fit is modelled in a new sibling; Br₂ SURVIVES at bench (a lower-bounded PREDICTED read,
> cross-referenced to the independent R26 thermo), dissociates sub-ms only at shock-tube T. A separate commit fixed a
> latent gate fabrication (an out-of-window extrapolated DEGRADES → UNKNOWN). See the DONE ledger + manifest §30.
> **⭐ ROUND 35 closed the five standing follow-ups.** Ring written order, revised Rule 1b, bounded Rules 4a/5, and
> isotope-on-ring naming are built; the modern Smackover undercut has a disclosed forecast basis with an explicit
> uncertainty boundary. The highest-value next CIP work is target-relative recursive Rules 4b/4c, then Rule 6 and
> unsupported charged/conjugated ring representations. On the cost lane, seek provenance-diverse realized operating
> data before promoting the Magnolia model into route ranking. Move 5 remains deferred until a second-domain consumer.

| # | Item | Lane | Size | Horizon | Gate / blocker |
|---|---|---|---|---|---|
| **Move 4 CIP Rung 2** | **CIP Rule 1b** — ✅ **BUILT ROUND 35.** IUPAC P-9 supplied the consumer missing from the bounded R32 generators; the committed isolation ties under Rule 1a and splits under revised Rule 1b. | B | — | **DONE** | See manifest §35 and `CIP_RING_AUX_RULES_SCOPE_v0.1.md`. |
| **1** | **Target-relative Rules 4b/4c** — recursively assign auxiliary descriptors without bootstrapping a guessed fixed point; close the mutually pseudo ring-pair dark fringe. | B | M | medium | Needs a target-relative graph construction and oracle counterexamples beyond absolute first-pass labels. |
| **2** | **CIP Rule 6** — complete the reference-dependent sequence-rule tail after 4b/4c. | B | M | medium | Build only with a real Rule-6 consumer and source-exact discriminator. |
| **3** | **Charged/conjugated ring representation** — extend mancude handling past the neutral bounded C/N/O/S slice. | B | L | medium | Requires a sound source-pinned representation; fixed-Kekulé shortcuts remain forbidden. |
| **4** | **Modern bromine provenance rotation** — find realized, non-Albemarle operating evidence or a genuinely independent cost model. | C | S/M | long | Magnolia is forecast/model evidence; JBC shares the issuer/reporting family. |
| **5** | **Phase-aware Br₂ identity and thermo resolution** — prevent gas data from standing in for liquid standard-state claims. | B·C | M | medium | Requires a phase-carrying key across thermo consumers, not a local special case. |
| **Move 5** | **Domain-neutral parameterization** — step/route/cost types over a "conserved-inventory transition + survival predicate", not concretely `Molecule`, so chemistry/circuits/radiation are functor images of one base SMC ([[electromagnetic-scope]] as a theorem) | B | **L** | **DEFERRED — premature** | **Scope decision (R28 recon): `docs/research/MOVE5_DOMAIN_NEUTRAL_PARAMETERIZATION_SCOPE_DECISION_v0.1.md`.** No second-domain pipeline consumer exists (electrochem/cell are `Molecule`-typed; circuits are on `open_diagram.py` with no route/step/DAG shape; the `*_domain.py` files are oracle-coverage domains, not pipeline consumers) → building it now = a zero-call-sites abstraction. UNLOCK: a genuine multi-step non-chemistry process, or a concrete `Molecule`-forced-fit pain report. |
| ~~3b~~ | ✅ **DONE (ROUND 30)** — DOW-Br₂ collider/modified-Arrhenius kinetics. See the DONE ledger + manifest §30. | B·C | — | — | The Warshay modified-Arrhenius bimolecular fit is modelled in a new sibling (`collider_kinetics.py`); Br₂ SURVIVES at bench (a lower-bounded PREDICTED read, thermo-corroborated), dissociates sub-ms at shock-tube T. Live wire-in of the collider model into E1's gate is TRACKED DEBT (verdict-inert today; no Br₂-intermediate DAG consumer). |

### K-B/C/D · Move-1 keystone — ✅ **DONE (Rung B ROUND 24 / Rungs C+D ROUND 25)**
**Rung B** (`944ad8c`, MERGED PR #19 → `main@5f1b3e3`): `open_core.py` + `open_chem_diagram.py` + `ExperimentStep.open()`
— the generic open-SMC core + chemistry layer, 3-part gate GREEN, congruence pinned. **Rung C** (`3e34265`, ROUND 25):
the pipeline speaks open-diagram — `ExperimentRoute.open()`/`SynthesisDAG.open()` via the port-level `plug_all` primitive +
`net_reaction()`, closing 3 Rung-B debts (see DONE ledger). **Rung D** (`35a5e64`, ROUND 25): the meta-compiler
`compile_open` — closing an open spec = compiling it, the load-bearing call site for B/C + M2-FP. Legacy `Reaction` xfail
(`tests/test_laws.py:330`) preserved-not-flipped throughout. Full spec + folds:
`docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md` (v0.2); `docs/research/FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md`.
**Next in the arc (the user's to steer):** wire the M2-FP objective LIVE into the ranking scorer (`drafter._route_score` —
churns route ordering/goldens, a deliberate schema-bump round); Moves 3–6 (provider-as-free-category, quotient/CIP enrichment
+ tension-A, domain-neutral parameterization now that `open_core` IS domain-neutral, the conditions⤳effects distributive law).

### M2-FP · Move-2 functorial-physics product — ✅ **DONE (ROUND 25)**
Shipped (`a8b61ce` + fold `d42d7a2`): `Δ_rG` recognized as the additive functor `G: Process→(ℝ,+,≤)` (Hess = functoriality,
`net_ΔG(route)==Σ steps` pinned non-vacuously); `RouteFeasibility.net_delta_g_kj` (property, digest-neutral, distinct from the
worst-node `verdict`); `PhysicsProduct`/`pareto_optimal` (the Pareto product, no scalar collapse); `FreeEnergyDecoration` (2nd
decoration-slot instance). **Anti-fabrication fix:** `estimate_thermo` empty-group → None (was fabricating `(0,0) DERIVED` for
bare halogens/HBr — both reviewers converged); DOW-Br₂ now fail-closes on Br• genuinely UNKNOWN. **Scorer wired LIVE in
ROUND 26 (M2b):** the Pareto product (front over `PhysicsProduct(net ΔG, survival)`) + the additive-ΔG magnitude now ride
`_route_score`/`_dag_score`; the DOW-Br₂ *thermodynamic* verdict was unlocked by the ROUND-26 DOW-thermo data add. See the
DONE ledger + manifest §§25/26.

### 1 · General CIP — the breadth-first namer — ✅ **DONE (ROUND 20, ID-STEREO-CIP-NAMER)**
Shipped: `smartchem/smiles.py` `_cip_ranks`/`_cip_compare`/`_cip_digraph`, wired into `_cip_labels`; validated by
`experiments/cip_namer_probe.py` (5 layers, FROZEN_HASH) + `tests/test_cip_namer.py`. CIP **Rule 1a**, breadth-first,
branch-by-branch with need-to-know pruning (the DFS-vs-BFS fix), phantom atoms for multiple bonds + ring closures,
validated `namer(mol) == geometric_handedness(true_priorities, sense)` on the textbook battery (incl. the L-serine (S) /
L-cysteine (R) flip). At R20, aromatic-reaching ties deferred. **ROUND 22 extends this with bounded neutral mancude
averaging and corrects the R20 soundness claim:** uppercase Kekulé inputs bypassed the old guard and could emit a wrong
label. The concrete mirror pair is now fixed and regression-tested. See the DONE ledger and manifest §§20/22;
higher-rule ties and unsupported ring systems remain TRACKED DEBT below.

### 2 · Composability + physical re-derivation on load — DAG **and** linear — ✅ **DONE (ROUND 21, ONLOAD-REDERIVE)**
Shipped: `smartchem/service.py` (thick `replay_payload` + `_reconstruct_route`/`_reconstruct_dag` +
`_check_verified_admission`) + `tests/test_onload_rederivation.py`. The ChatGPT external design review was folded
**against the tree** (8-agent recon+adversary pass) before any code — see `docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.2.md`
(supersedes v0.1). It corrected TWO holes in the v0.1 design: (1) the load-time coherence check did **not** bind the
payload to `route_digest` (a substitution attack) — closed by `reconstruct(payload).digest == route_digest`, cheap because
`route_digest` already covers the full step content; (2) the `compare=False` payload was bypassable by **deletion** —
closed by a **fail-closed** consumer policy (verified-admission requires every FITS route to carry a matching payload),
which needed **no schema bump** (route identity byte-stable, no golden churn — lower blast than the reviewer proposed).
Plus the v0.1 HMAC conflation was corrected (a public digest recompute is free; the key-holding residual is irreducible).
See the DONE ledger and manifest §21. TRACKED DEBT below: the keyless eval-context-relaxation boundary + the
verified-admission cost lever (evil-morty F1/residual).

### 3 · Wire the duration-aware verdict into core E1 — ✅ **DONE (ROUND 23, DURATION-SURVIVAL-01)**
Shipped: `smartchem/experiment/composability.py` (`_apply_duration_gate`/`_hold_survival`/`_survival_product`) +
`dag.py` (`_serial_hold_segments`) + `tests/test_duration_survival_gate.py`. E1's `_judge_transition` consumes the
DAG-HOLD-01 serial hold: with a sourced first-order decomposition rate (R19 primitive, matched on canonical structure),
the surviving fraction over the hold's intervening-step temperatures MOVES the verdict (`DEGRADES → DEGENERATE`, even
where the onset table is silent; `MARGINAL → UNKNOWN`; `SURVIVES` confirms; only ever tightens, never touches an
already-`DEGENERATE` base). Survival is the monoid functor `S: Process → ([0,1], ×)` — `route_surviving_fraction` is the
product over duration-assessed handoffs. Fail-closed on undeclared hold temperatures or non-finite rates; the R22 unit
lock (`ConditionEnvelope.duration = min`) is the declaration side, converted explicitly to the primitive's seconds. See
the DONE ledger and manifest §23. TRACKED DEBT below: linear-route holds are unmodeled (only DAG serial holds carry a
hold), and the R19 reactant-coefficient rate-convention residual still applies.

### 3b · Model the recovered DOW-Br₂ collider / modified-Arrhenius primary — ✅ **DONE (ROUND 30)** *(DOW)*
Shipped: `smartchem/experiment/collider_kinetics.py` (the Warshay `kD = A·√T·exp(-Ea/RT)` bimolecular fit as a NEW
sibling — the plain-Arrhenius first-order seed literally cannot represent it) + committed harness
`experiments/dow_bromine_kinetics_probe.py` (FROZEN_HASH) + `tests/test_collider_kinetics.py`. The model reproduces the
Warshay Table I point (a transcription check), turns the bimolecular coefficient into a *conditional derived*
pseudo-first-order coefficient at a declared `[M]`, and reads a survival verdict that **certifies SURVIVES only** (the
irreversible forward fraction is a rigorous lower bound on the true reverse-inclusive fraction). **The litmus answer:**
Br₂ SURVIVES at kitchen T (a PREDICTED extrapolation ~900 K below the window, lower-bounded and cross-referenced to the
independent R26 thermo ΔG₂₉₈=+161.65), and dissociates sub-ms only at shock-tube T (the sourced reverse-free rate). The
reverse/hold "wall" is dissolved by the lower-bound argument (SURVIVES is sound WITHOUT a reverse model; a DEGRADES would
be fabrication → refused). See the DONE ledger + manifest §30; spec `docs/research/DOW_BROMINE_KINETICS_CONTRACT_v0.1.md`;
source receipts `docs/research/SOURCING_RECON_2026-09-07.md`. **Tracked debt:** the live wire-in of the collider model into
E1's duration gate (verdict-inert today — Br₂ is SURVIVES; no Br₂-intermediate DAG with a declared collider state exists).

### 2b (DONE R19) · machine-readable `serial_holds` on `RankedDAGSummary`
Shipped — the DAG-HOLD-01 serial hold is now a `(producer, consumer, minutes)` triple field (digest-excluded disclosure),
not just a human note. See the DONE ledger.

---

## ⏸️ DEFERRED — explicit remaining gates (not fabricated)

- **The DOW brine-vs-mined *cost ranking*** — ✅ **ANSWERED (ROUND 31), honestly + layered** (the DOW litmus's last lane,
  Lane C). Pricing (R16), mechanism (R17), electrochemistry (R18) shipped. R31 delivered the cost verdict: **Theorem 1** —
  at today's sourced single-benchmark data, no undercut is *demonstrable* (a NaBr contained-Br proxy of the benchmark `q`
  costs exactly `q` per unit Br₂ → `brine ≥ mined`; the user's "may not pass at today's prices" flag confirmed as a proven
  algebraic degeneracy, SCOPED — never "brine worse in reality"); **Theorem 2** — the historical undercut IS reproduced from
  sourced period prices as a one-sided ECONOMIC bound at the route/industry level (USGS DS-140 sustained unit value upper-
  bounds the US brine-route marginal cost; vs the cartel's 49 ¢/lb → ≈39 % undercut pre-war, ≥ ≈80 % war-survival). See the
  DONE ledger + manifest §31. **REMAINING UNLOCK (a sourcing wall, not a build):** a *modern* undercut demonstration needs a
  sourced, INDEPENDENT brine-feedstock/extraction cost basis (Smackover/Dead Sea well-brine), distinct from the benchmark
  being undercut — the same-benchmark proxy provably cannot show it. The R22 Los Fresnos Cl₂ offer ($1.24/lb, 2,000-lb
  cylinder, +$50/mo rental, approved not invoiced) stays labelled reconnaissance, used only as a demonstration input, never
  committed to default commodity pricing.
  **ROUND-35 supersession:** the Magnolia SEC report supplies that independent-from-price Smackover cost basis. It
  supports undercut at spot and spot-minus-30%; the minus-45% edge is not +10%-opex robust. Remaining work is stronger
  provenance/realized-cost corroboration before any production-ranker admission, not recovery of the missing basis.
- **A second sourced organic price** (was ROUND-15 item 3; Lane C). Attempted acetic acid (highest value — it ripples
  the methyl-acetate golden) and ethanol. **Wall:** organic producers post price *increases* (Celanese: +$50/MT Feb,
  +$0.10/lb Mar 2026), not absolute reference sheets; absolutes are aggregator-walled (Intratec/ChemAnalyst). Ethanol's
  only primaries are a government *projection* (EIA AEO Table 12 — a forecast, not an observed price) or a *foreign,
  regulated, denatured fuel-grade* price (IPART NSW, needing FX+density+unit conversions for a weak match). None clears
  the bar methanol set (a directly-readable, dated, observed absolute for the exact chemical), so per §10.4
  anti-fabrication this is a **DEFER, not a fabricated price** — the same call R13 made. Revisit if the bar is
  explicitly relaxed, or pivot to **bromine (USGS-priced)** via DOW litmus item 2.

---

## 🚫 NOT BUILDING — deliberately parked (with the reason, so nobody re-walks it)

- **The >64-heavy work-metered resonance escape valve.** Characterized and **refused** (RESONANCE-WORK-01). Reinforced
  YAGNI: the largest *real* target is 13 heavy (aspirin); the 24-heavy figure is a benchmark (coronene); a **72-heavy**
  fixture already proves the >64 path falls back to literal identity in ms — the door is tested-shut. Even built it
  can't separate malice from legit, and it entangles `Molecule.canonical()` (system-wide identity hot path) with an
  uncached meter that conflicts with `resonance_canonical`'s `@lru_cache`. Pinned by `tests/test_resonance_actual_work.py`.
  Re-open only when a real >64-heavy target appears — then re-measure the branch *before* touching core code.

---

## ⚠️ TRACKED DEBT — known, carried, not silently

- **Move-3 law scope** (Lane B; ROUND 27, honestly bounded, none blocking): the three `test_provider_category.py`
  laws are exactly scoped, not over-claimed (evil-morty LOW folds). Law 1 (provenance-out-of-identity) is a **forward
  change-detector** — provenance is structurally absent from the functor's domain (`from_transform` never receives the
  `EnumeratedTransform` wrapper), so it guards against a future edit threading provenance in, NOT a proven congruence.
  Law 3 (forget/open naturality) is **common-mode on the product multiset** (both functors read the same `transform`
  fields) — it catches the reversal orientation + Molecule↔Formula altitude, not product correctness (which the
  conservation certificate owns). Law 2 is the one that catches a broken functor. The framing claims *a semantics
  functor* F, never *freeness* (universal property unproven). SMC coherence itself is `open_core`'s, not re-proven here.
- **M2b carried debt** (Lane B·C; ROUND 26, from the evil-morty + birdperson reviews — none blocking):
  (a) **Sourced Br₂(g) phase hazard** (evil-morty KILL 2) — only the GAS Br₂ record is in the live `SEED_THERMO_REFS`, and a
  sourced `for_formula` hit gets NO phase correction (that path is Benson-only); `Molecule` carries no phase, so ANY reaction
  treating Br₂ as its true standard-state LIQUID would silently get the gas ΔfH° (+30.91 kJ/mol error). No current path
  reasons about liquid Br₂ through `feasibility_of_step` (the DOW displacement runs on electrode potentials), so nothing is
  misled today — but the guard rests on nobody writing a liquid-Br₂ reaction, not on an enforced phase key. Closing needs a
  phase-aware resolve (out of scope). Same species as the ROUND-18 F5 phase-scope debt.
  (b) **No front-driven reorder pinned THROUGH the public `rank_dags`** — `_pareto_front_indices` runs on every ranking call
  (a genuine call site) and `TestParetoFrontTierFiresOnRealSurvival` proves the layering flips a real survival-bearing
  objective, but via `dag_composability(dag, kinetics=injected)` directly, because `dag_bench_fit`/`rank_dags` with the
  DEFAULT tables don't thread kinetics to the duration gate. End-to-end the front fires only for a DEFAULT-seeded held
  intermediate (N₂O₅/cyclopropane); the front is otherwise inert (the ΔG-magnitude axis carries M2b). Data-gated, honest —
  the R25-`frontier` discipline; a fuller end-to-end pin awaits either a seeded-intermediate DAG fixture or threading
  kinetics through `rank_dags` (which the ROUND-15 fold deliberately declined).
  (c) **`route_net_delta_g` fan-out double-count** (evil-morty residual, pre-existing/orthogonal) — the additive Hess sum over
  `dag.steps` is topology-independent when each step occurs once; a diamond DAG whose shared producer feeds two consumers with
  molar multiplicity (if representable and not cross-node molar-balanced) could undercount the producer. No such construction
  found; not introduced by M2b (it just sums); the DAG-model molar-balance question is the DAG's concern, carried not silent.
- **Interchange-law xfail** (Lane A) — `tests/test_laws.py:330`: the *legacy linear `Reaction`* representation cannot
  quotient independent events by interchange. **ROUND 24's `OpenChemDiagram` supersedes it for parallel events** (interchange
  holds under the `canonicalize` quotient), but the legacy xfail is **preserved-and-annotated, not flipped** (flipping it in
  place was the zero-call-sites trap / a P2 violation, per the keystone contract). Orthogonal architecture debt; 1 xfail.
- **Rung-B open-diagram carried debt** (Lane A·B; ROUND 24 → **debts 2/3/5 CLOSED by Rung C (ROUND 25)**):
  (1) the `Decoration` interchange-invariance obligation is enforced only by docstring + per-instance tests, not by a generic
  guard (birdperson C) — a future decoration author could violate it *[still open]*; (2) ✅ **CLOSED R25** — gluing is BY TOKEN
  (`_first_free`), not port position, so a canonical species re-sort cannot misalign a port; (3) ✅ **CLOSED R25** (as a
  fail-closed refusal, not full occurrence-aware provenance) — `_derive_provenance` now RAISES on a structurally-identical-step
  collision instead of silently merging; a legitimate `A→B→A→B` route therefore fail-closes on `.open().apex`/`.close()` (a
  refusal, documented, not a wrong answer — full occurrence-aware provenance keyed by hyperedge occurrence is still future work);
  (4) WL completeness on highly symmetric chemistry apices is not proven — the budget refusal fail-closes a *wrong* answer but a
  WL-indistinguishable non-isomorphic pair under budget would over-merge silently (contract Open Q3) *[still open]*; (5) ✅
  **CLOSED R25** — `port_state`/`open_nodes` use distinct-EDGE incidence (`edge_incidence`), so a within-one-hyperedge
  self-incidence is not misclassified INTERNAL, and `plug_all` refuses a self-plug.
- **Rung-C/D + M2-FP carried debt** (Lane A·B·C; ROUND 25, from the evil-morty ×2 + birdperson reviews — none blocking):
  (a) the **M2-FP two-axis Pareto `frontier` is DATA-GATED** — survival is `None` for single-step routes (no inter-step hold) and
  for multi-step routes not hitting the two sourced kinetic records, so `compile_open(...).frontier` is usually EMPTY and the LIVE
  ranking surface is `by_free_energy` (the additive-ΔG axis); the two-axis product fires only where sourced kinetics exist (the
  DOW-Br₂ data-gating discipline). Making the product LIVE in the scorer is queue item **M2b**; (b) `MetaCompilation.by_free_energy`
  silently OMITS unknown-ΔG closures from its ranked list (disclosed in the docstring; `.closures` retains all) — a count/marker
  of the dropped set would be more honest; (c) the **Hess property test is genuine-but-relational** (net==Σ over the same thermo
  table — a wrong ΔfH° cancels on both sides); the VALUE calibration lives in the Haber/water thermo tests, not this test.
- **Load-time free-text trust boundary** (Lane C) — ✅ **STRUCTURALLY CLOSED (ROUND 21, item 2)** for a verified-admission
  consumer: `response_from_payload(require_verified_admission=True)` reconstructs the route/DAG from the thick
  `replay_payload` and re-derives all three axes + ranking, refusing a bare-relabel or substituted evidence with no key.
  The default (non-verified) path is unchanged (still process-axis-only, HMAC-optional), so a consumer must **opt in** to
  the close. Two residuals carried below.
- **Verified-admission keyless eval-context relaxation** (Lane C; ROUND-21, evil-morty F1 VERIFIED) — the re-derivation
  builds its bench box from the response's OWN request, so a keyless attacker who relaxes that request (and recomputes the
  free public `result_digest`) can re-derive an out-of-bounds route to FITS. The check authenticates verdict↔route
  coherence UNDER THE STATED context, not the context itself. Closed by pinning the request (`expected_request_digest`) or
  a `verification_key` (the request is folded into `result_digest`); NOT forced (the process axis trusts the request
  identically). Documented + pinned both directions.
- **Verified-admission compute cost** (perf; ROUND-21) — `_check_verified_admission` runs the full `rank_routes` fold per
  FITS dossier on load (amide-heavy targets pay the ~500 ms `Molecule.canonical()` resonance cost each). Opt-in and
  bounded by candidate count; a verified-admission consumer pays for the assurance. Reduce (if it ever matters) by
  caching the per-route fit; not worth it today.
- **DAG `dag_bench_fit` compute multiplicity** (perf, correctness-neutral) — a DAG-mode compile runs `dag_bench_fit`
  ~3×N (rank_dags key + `of_dag` + `_dag_bench_note`), and each call now ALSO computes the four-provider thermo roll-up
  per node (DAG-THERMO-01), so it is heavier. Still bounded and compile-time (real DAGs are small). Reduce by threading
  one computed fit through all three if it ever matters; not worth a refactor today.
- **Phase-specific electrode potentials** (Lane B·EM; ROUND-18 evil-morty F5) — the halogen couple is phaseless, so the
  sourced `STANDARD_REDUCTION_POTENTIALS` are the AQUEOUS standard values. This is CORRECT for the aqueous DOW displacement
  (+1.087 V) and fail-closed for an explicitly-phased couple (returns UNKNOWN, never a wrong number), but a liquid-phase
  value (Br₂(l) = +1.066 V) is unreachable until a phase-carrying couple API exists. YAGNI today; revisit if a route ever
  reasons about the liquid product.
- **Observability Score → CostVector verification axis** (Lane C; ROUND-18) — the Observability Score is a self-contained
  ranking primitive; feeding its process/identity/purity strengths into the affordability `CostVector` as a verification
  axis needs a new `_AXES` entry + a frontier-entry schema bump + golden regen (a deliberate deferral, not an oversight —
  the score is honest and usable standalone now).
- **CIP external-oracle scope** (Lane B; ROUND-22) — `experiments/cip_external_oracle_probe.py` now compares against the
  accurate RDKit `rdCIPLabeler` through an external parser/graph/labeler, including aromatic, explicit-Kekulé and reversed
  atom-order spellings. RDKit remains an optional probe dependency, absent from the runtime. Its implementation is
  separate but the CIP specification is shared; finite agreement does not prove correctness on arbitrary graphs.
- **CIP full completeness — higher rules and unsupported ring systems** (Lane B; ROUND-20/22/28/34/35) — the namer implements
  **Rules 1a, revised 1b, 2, 3, and bounded 4a/5**. Neutral mancude averaging is built for the bounded C/N/O/S valence
  slice, including supported fused systems. **Target-relative recursive Rules 4b/4c and Rule 6 remain UNBUILT** —
  a tie needing them is a NAMED deferral (never guessed). Recursive stereochemistry-dependent ties and
  comparisons needing charged, internally conjugated, untyped or over-budget ring connectivity still DEFER.
  Limits: 30 atoms per ring system, 128 complete matchings, 10,000 matching-search visits; a partial partner set is never
  used. The aromatic parser's charged-donor limitations remain separate (some aromatic inputs refuse while explicit
  spellings reach CIP deferral). See `docs/research/CIP_MANCUDE_SCOPE_2026-09-07.md` and
  `docs/research/CIP_NODE_ENRICHMENT_SCOPE_DECISION_v0.1.md`. External finite agreement does not prove full CIP soundness.
- **CIP unsaturated/ring-substituent gap — ✅ bounded classes CLOSED (ROUNDS 33–35); residuals tracked** (Lane B). R33 released
  LOCALIZED unsaturated rings (unique Kekulé — cyclopropene…cyclohexadiene, cyclic enol ethers,
  localized fused bicyclics) to the ordinary digraph, so the R32 isolation now NAMES both (`[C@](C1CC1)(C)(F)Cl` and
  `[C@](C1=CC1)(C)(F)Cl` → R), oracle-verified over ~5,600 molecules (0 mismatches). R34 added bounded EXOCYCLIC
  unsaturation/carbonyls, AROMATIC-fused-to-saturated systems, and Rule-1a-distinct RING-vs-RING comparisons. **Still
  DEFERRED, soundly:** internal conjugated/charged ring systems outside the admitted representation and ring centres
  needing mutually recursive Rule 4b/4c descriptors. ROUND 35 closes the former isotope-on-ring and constitutional
  ring-centre boundaries. See the corrected scope docs + manifest §§33–35.
- **CIP Rule-2 sound scope + residuals** (Lane B; ROUNDS 28/35) — Rule 2 (mass number) remains its own full FIFO pass
  after Rules 1a and revised 1b; child pairing uses the cumulative comparator through Rule 2. Unknown mass (a mancude
  superposition duplicate or an untyped radioactive/synthetic element) still defers. ROUND 35 independently checks the
  former ring-closure isotope cases against RDKit and admits them. Remaining evidence is finite: broader isotope/ring
  graphs and unknown-mass interactions still need fresh oracle cases before any completeness claim.
- **CIP comparator transitivity residual** (Lane B; ROUND-20/28, evil-morty) — `_cip_compare` is used as a `cmp_to_key` sort
  key, which assumes transitivity; a deep degenerate tie tree could in principle violate it. No counterexample found
  (fuzzer-clean) and the `sorted(ranks)==[0,1,2,3]` guard in `_cip_ranks` catches any top-level cycle (→ DEFER, sound),
  but a transitivity PROOF is not in hand — documented, not eliminated. **ROUND 28 MITIGATES it for Rule 2**: the
  `_cip_compare_rule2` all-pairs sibling guard + per-pair precondition enforcement DEFER rather than trust the sort order,
  so a non-transitive mis-sort fails closed instead of mislabelling. (The exocyclic-multiple-bond-into-aromatic path IS
  discharged, by an explicit guard in `_cip_digraph`.)
- **Duration-stability reactant-coefficient rate convention** (Lane B·C; ROUND-19, evil-morty) — `surviving_fraction`
  assumes the sourced `k` is the per-species rate (`-d[A]/dt = k[A]`), which both seeded records pin in their provenance;
  a future first-order record with coefficient > 1 sourced under the *reaction-rate* convention would be off by the
  stoichiometric factor. The module can't detect the convention from the data — documented boundary, not a silent guess.
- **Duration-survival hold scope** (Lane B·C; ROUND-23) — ✅ core E1 **now consumes** the hold: `_apply_duration_gate`
  turns a DAG serial hold + a sourced first-order rate into a verdict (DURATION-SURVIVAL-01), fail-closed on undeclared
  hold temperatures or non-finite rates. Residuals carried, not silent: (1) only **DAG serial holds** carry a modeled
  hold — a **linear route's** adjacent handoff passes no hold, so its intermediates are never duration-assessed (a linear
  route has no idle-between-siblings time the model can source; a genuine bench hold would need an explicit hold
  declaration the type does not yet carry); (2) each intervening segment uses the **hi end** of its declared temperature
  range (worst-case within that step) — a policy, stated; (3) the R19 reactant-coefficient rate-convention residual
  (below) still applies. The R22 unit lock (`ConditionEnvelope.duration = min`) remains the declaration side, converted
  explicitly to the primitive's seconds.
- **DOW-Br₂ collider-kinetics carried debt** (Lane B·C; ROUND-30, from the three reviews — none blocking): (1) the
  **live wire-in** of `collider_kinetics` into E1's `_apply_duration_gate` is NOT built — the gate's contract is
  first-order s⁻¹ single-reactant and carries no collider `[M]`, Br₂'s bench verdict is SURVIVES (verdict-inert in a
  tightening-only gate), and no kitchen DAG reaches the 1200–1900 K in-window regime; building it now = machinery for a
  caller that does not exist (UNLOCK: a real Br₂-intermediate DAG with a declared collider state — the R19→R23 precedent).
  (2) the **reverse-recombination / falloff net-loss model** is deliberately unbuilt — the lower-bound argument makes the
  SURVIVES verdict sound without it, and `collider_survival` refuses every DEGRADES rather than fabricate one. (3) the
  gate guard's **`all_in_window` mixed-window over-reach** (a forced-between hold mixing an in-window destroying segment
  with an out-of-window harmless one conservatively fails closed to UNKNOWN) — a completeness cost in the SAFE direction
  (evil-morty F3), never a fabrication; a per-segment "which segment drove the destruction" refinement is not built.
  (4) **Ne/Kr collider fits parked** in the contract doc, not seeded (no collider-comparison caller this round). (5) the
  Warshay transcription check is a self-consistency reproduction (reuses the fit), NOT an independent validation; the next
  research task (per the sourcing recon) is to compare the NASA fit with later primary corrections before leaning on it as
  a modern reference.

---

## How this file stays current (so it never needs a workflow to rebuild)

Updating `ROADMAP.md` is part of the per-round ritual, the same reflex as bumping `UPTAKE_MANIFEST §N` and the README
suite count:

1. Ship a round → move each shipped item from **QUEUE** to the **DONE** ledger with its commit.
2. Re-stamp `verified @ <commit>` and the suite count at the top.
3. Add any new queue items with lane + size + gate + cheapest first step. Anything walled → **DEFERRED**; anything
   refused → **NOT BUILDING**; anything carried → **TRACKED DEBT**.

Next session: read *this file*, not a 5-agent recon.
