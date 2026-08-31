# M-5 Experiment Compiler — paracetamol litmus, end to end

**Harness:** `experiments/compiled_paracetamol_experiment.py` · **Gate:** exits non-zero on any hard failure
**Run:** `.venv/bin/python experiments/compiled_paracetamol_experiment.py` → **VERDICT: PASS (69/69), exit 0**

## The question

Given the decompiler's candidate routes to a real target, can the Experiment Compiler (M-5) verify them as
runnable experiments, refuse the degenerate ones for the right *sourced* reasons, fit them to a real bench,
and draft a chemist-usable procedure — all under the **known-not-new-physics** discipline (reproduce known
chemistry; never invent a feasibility/kinetics/yield model)? Not *"does the synthesis work"* — W3 forbids
that — but every fact the compiler asserts must hold, and every refusal must cite a sourced fact.

## What ran, and what held (47/47)

| Rung | Criterion | Result |
|------|-----------|--------|
| E1 | ketene route is `DEGENERATE` on the **sourced not-isolable fact** (the operator's own degenerate-path example) | PASS |
| E1 | the degeneracy **cites** ketene's non-isolability (generated/consumed in situ; NJ RTK / CAMEO) | PASS |
| E1 | anhydride route is not degenerate | PASS |
| E4 | the real anhydride route **ranks first**; the ketene route ranks last | PASS |
| E4 | a **1200 °C (1473 K) burner** bench `EXCLUDES` the 1000 K ketene pyrolysis | PASS |
| E4 | the anhydride route (ambient pressure declared) `FITS` a "≤1.5 bar" bench | PASS |
| E4 | a bench **without acetic anhydride** `EXCLUDES` the route, citing the missing reagent | PASS |
| E4 | a bench with **no heating apparatus** `EXCLUDES` the heated step | PASS |
| E4 | an **undeclared pressure** under a pressure-capped bench is `UNKNOWN`, never a silent `FITS` | PASS |
| E2 | the ceiling is **exactly 1 mol** paracetamol, limited by 4-aminophenol, `CONSERVATION`-bucketed | PASS |
| — | **universality:** ethyl acetate (off-seed) drafts + ceilings without a crash or a whitelist hit | PASS |
| — | **the universality lever:** an off-seed intermediate is `UNKNOWN` until sourced data is injected, then `COMPOSABLE` | PASS |
| E4 | the draft carries the **honesty banner** ("NOT a predicted successful synthesis") | PASS |
| E4 | the draft names the heating apparatus — the "Bunsen and flasks" **click** | PASS |
| E4 | the draft attaches **sourced-hazard containment** (a fume hood; inform, never neuter) | PASS |
| E5 | rediscovers the **acetic-anhydride** acetylation of 4-aminophenol from the decompiler | PASS |
| E5 | rediscovers the **acetic-acid condensation** route from the decompiler | PASS |
| E5 | returns a **loud empty** (no route) from an empty inventory, never a fabricated route | PASS |
| E5+ | the amide (paracetamol) is the **sourced FAVORED** product of acetylating 4-aminophenol | PASS |
| E5+ | the **O-acetyl ester** from the same reactants is `DISFAVORED` (major product is the amide) | PASS |
| E5+ | the ketene acetylation carries **no sourced N-/O-selectivity** → a loud `UNKNOWN`, never fabricated | PASS |
| E5+ | ranking **floats the FAVORED (right-isomer) route above** the disfavored one | PASS |
| E5+ | the draft **surfaces the sourced regiochemistry** (this route makes the major isomer) | PASS |
| M1 | the ΔG engine **recovers the textbook −474 kJ** for 2H₂+O₂→2H₂O (the instrument reads true) | PASS |
| M1 | Haber is **FAVORABLE at 298 K** (DERIVED, ΔG ≈ −33 kJ) | PASS |
| M1 | Haber **flips UNFAVORABLE at 700 K, flagged PREDICTED** (extrapolated) — the real T-dependence | PASS |
| M1 | paracetamol acetylation feasibility is a **loud UNKNOWN** (no seed thermo), never a fabricated ΔG | PASS |
| M1 | ranking **floats the thermodynamically FAVORABLE route above** the endergonic one | PASS |
| M2 | `K = exp(−ΔG/RT)` **recovers Haber's K ≈ 6×10⁵** at 298 K (the instrument reads true) | PASS |
| M2 | Haber's equilibrium **collapses below K=1 at 700 K** → NEGLIGIBLE — the real "why it needs pressure" | PASS |
| M2 | a **Δn=0** reaction gets an **exact ideal-reference equilibrium conversion** fraction (tighter than 100%) | PASS |
| M2 | a **Δn≠0** reaction's conversion is a **loud UNKNOWN** (needs a reference state) — but its K is DERIVED | PASS |
| M2 | paracetamol acetylation equilibrium is a **loud UNKNOWN** (no seed thermo), never a fabricated K | PASS |
| M2 | ranking **floats the ESSENTIALLY_COMPLETE route above** the negligible-equilibrium one | PASS |
| M3 | ethanol combustion is **UNKNOWN on the 8-species seed** (ethanol not seeded) | PASS |
| M3 | the **extended NIST-sourced table recovers** ethanol combustion's textbook ΔG ≈ −1325 kJ (unlock + instrument) | PASS |
| M3 | M2 reaches the unlocked reaction too — ethanol combustion is **ESSENTIALLY_COMPLETE** at equilibrium | PASS |
| M3 | **no fabricated paracetamol thermo record** exists (its ΔfH° is sourced, its S° is not) | PASS |
| M3 | the paracetamol litmus gap is **DOCUMENTED** (entropy S° unsourced), never papered over | PASS |
| M3 | paracetamol's acetylation step **stays honestly UNKNOWN** under the extended table (the entropy gap holds) | PASS |
| M4 | a **convergent** ethyl-acetate synthesis is a **DAG with one join** (the acid and alcohol branches meet) | PASS |
| M4 | the **convergent ceiling** is limited by the **scarcer branch** (ethanol, branch B) — 1 mol at 100% | PASS |
| M4 | **starving branch B halves** the convergent ceiling (the join follows the scarcer branch) | PASS |
| M4 | M1/M2 **reused per-step over a DAG** — every step DERIVED, the endergonic branch dominates the aggregate | PASS |
| M4 | a **malformed DAG** (two unconsumed targets) is **refused**, never silently accepted | PASS |
| L2 | the real acetylation grades **KNOWN** (sourced chemistry attests it) with thermodynamics honestly **UNKNOWN** — both true at once | PASS |
| L2 | the O-acetyl ester route grades **KNOWN yet flags the MINOR isomer** (KNOWN ≠ favored) | PASS |
| L2 | an **unbalanced** formal combination grades **REFUTED**, citing *conservation of mass and charge* | PASS |
| L2 | the ketene route grades **REFUTED**, its law citing the **sourced not-isolable fact** (E1, unified) | PASS |
| L2 | water synthesis grades **DERIVED/FAVORABLE**, ΔG ≈ −474 kJ (the model reads true in-envelope) | PASS |
| L2 | Haber at 700 K grades **PREDICTED** (extrapolated), UNFAVORABLE — the real temperature flip | PASS |
| L2 | paracetamol hydrolysis grades **HYPOTHESIZED** — a balanced, formally valid candidate, no data | PASS |
| L2 | a route is **worst-step-dominated** — a DERIVED step under a HYPOTHESIZED step grades HYPOTHESIZED | PASS |
| — | **the litmus bottoms out at ELEMENTAL BUCKETS {C,H,N,O}**: the decompiler descends the whole compound to atoms, conserving every edge | PASS |
| — | read backwards, that descent **is the assembly of paracetamol from those buckets** (a 16-node chain, not one atomisation edge) | PASS |
| R1 | `ring_aware` **opens paracetamol's aromatic ring into gradeable reactions** — the ring-opening subset of the full 2-cut (8 ⊂ 80 ⊂ 404), tractable, never invents an edge | PASS |
| R1×L2 | a ring-opening **read backwards is the assembly of the ring**, graded **HYPOTHESIZED** — the STRUCTURED chain reaches *through* the ring, not just to its core | PASS |

## The ledger completed this arc (E1 depth · coverage/autoload · E5 · CLI)

- **E1 pressure/phase (Clausius–Clapeyron).** A real pressure DROP that boils a condensed intermediate off
  is now `DEGENERATE`, grounded in the integrated CC equation over a sourced boiling point + enthalpy of
  vaporisation — the operator's "pressure can't be reconciled" case. Verified: water is liquid at 5 atm but
  a gas at 0.1 atm across a transition → `DEGENERATE`; same pressure stays `COMPOSABLE`; a missing dHvap
  leaves the dimension a labeled `UNKNOWN`, never a fabricated verdict.
- **Coverage / autoload ("download and go").** A pluggable provider stack — **PubChem** (public domain),
  **Wikidata** (CC0), **Bradley Open MP Dataset** (CC0, ~28k mp) — fetches sourced property data and caches
  it locally under the bundled seed. Offline-first + live-fetch-that-caches, no API key, degrades to a loud
  `UNKNOWN`. Verified live end to end (aspirin autoloaded from PubChem, cached); committed tests parse
  recorded fixtures offline. Bulk: `python -m smartchem.data.fetch_open_data bradley`.
- **E5 + the CLI.** `enumerate_routes` reads the decompiler's cleavages backward into candidate syntheses;
  `python -m smartchem.experiment "<SMILES>" --have ... --reagents ... --max-temp K --max-pressure atm`
  enumerates, autoloads, fits/ranks against the bench, and prints the top drafted procedure.

## The drafted procedure (verbatim)

```
STEP 1: C6H7NO + C4H6O3 -> C8H9NO2 + C2H4O2
    reaction enthalpy (0 K) = UNKNOWN  [UNKNOWN: no sourced 0 K formation enthalpy]
    temperature = [295.0, 353.0] K     [KNOWN_SOURCED: ACS J.Chem.Educ. teaching synthesis]
    pressure    = [1.0, 1.0] atm       [KNOWN_SOURCED: ...]
    medium      = aqueous, mild acid; volumetric make-up  [KNOWN_SOURCED: ...]
    equipment:
      - reaction flask (Erlenmeyer or round-bottom) + a few beakers   (vessel)
      - hotplate or water bath                                        (heating)
      - volumetric flask, graduated cylinder, pipette + balance       (measuring)
      - fume hood (and appropriate PPE)                               (containment)
route ceiling: 1 mol C8H9NO2 at 100% efficiency  [CONSERVATION — an idealised upper bound, not a yield]
```

A chemist reads this and it clicks: *a flask, a hotplate, a volumetric, a fume hood — 1 mol in, 1 mol out
at best.* The heat is honestly `UNKNOWN` (paracetamol has no sourced 0 K formation enthalpy — no guess).

## The boundaries this pins (loud, not hidden)

- **The corrected frame held (no *new* physics).** Two outcome numbers now appear, each an ESTABLISHED model
  on sourced inputs, each wearing its grade: the `CONSERVATION` 100%-efficiency ceiling (an exact upper
  bound), and the M2 `KNOWN_SOURCED`/DERIVED **equilibrium extent** (`K = exp(−ΔG/RT)` and, where Δn=0, an
  exact ideal-reference conversion) — a *tighter* bound than the ceiling, labelled equilibrium-not-kinetics.
  What is still refused: a reaction **RATE** / time-to-completion (no established kinetics model — roadmap L1),
  a fabricated K/ΔG for an unsourced species (a loud `UNKNOWN` instead), and any claim contradicting a sourced
  fact. Equilibrium is *how far*, never *how fast*.
- **Universal engine, sourced data.** Formal layers (E0/E1-logic/E2/equipment) run on any parsed molecule;
  the stability/thermo data is a SEED that degrades to a loud `UNKNOWN` and is injectable per call — proven
  by the off-seed lever above. Not a whitelist.
- **M3 breadth, sourced not recalled.** The extended thermo table (`data/thermo_extended.py`) broadens M1/M2
  beyond the 8-species seed with common organics whose 298 K ΔfH°+S° were **verified against the NIST
  WebBook**, each carrying its measurement's author/year — never a number recalled from memory (this repo has
  a documented history of memory-recall poisoning). The paracetamol litmus is *honestly half-unlocked*: its
  ΔfH°(cr) = −410.4 is sourced, but no S°(cr) is cleanly sourced, so its ΔG stays `UNKNOWN` on a **documented
  entropy gap** — the correct refusal, loud about exactly which species and quantity blocks it.
- **Sourced-model gaps, stated:** the pressure-dependence of phase (Clausius–Clapeyron) is not attempted by
  E1; the M2 equilibrium conversion is exact only for Δn=0 under an ideal reference (Δn≠0 needs a caller's
  sourced activity model — a loud `UNKNOWN`, never a guess). Equipment selection is standard bench practice,
  not a claim the reaction proceeds.
- **L2 — the mission made literal.** One classifier (`experiment/classify.py`) now grades ANY formal
  combination — a step, a linear route, a convergent DAG, or raw reactants→products — with a single verdict:
  `KNOWN` / `DERIVED` / `PREDICTED` / `HYPOTHESIZED` / `REFUTED` / `UNKNOWN`. No new engine, no new physics:
  it *composes* the existing verified rungs exactly as `bucket.py` already documented (a DERIVED/PREDICTED
  verdict carried by `KNOWN_SOURCED` quantities; a REFUTED verdict naming a `CONSERVATION`/`COMPOSABILITY`
  fact; UNKNOWN all-gap). Each grade is earned by a checkable condition; routes/DAGs are worst-step-dominated
  on the ladder `HYPOTHESIZED < PREDICTED < DERIVED < KNOWN`; a `DEGENERATE` handoff overrides to `REFUTED`
  citing the sourced fact. The nuance the frame exists for holds: paracetamol acetylation grades **KNOWN**
  (a documented reaction) with **UNKNOWN thermodynamics** — both true, neither faked.
- **The litmus is the ENTIRE chain, from elemental buckets.** The paracetamol experiment does not start
  mid-chain: the decompiler descends `C8H9NO2` to a 16-node AND-OR hypergraph terminating in the atom buckets
  `{C, H, N, O}`, COMPLETE and conserving every edge — read backwards, that *is* the assembly of paracetamol
  from elemental buckets. The honest boundary: this from-buckets chain is FORMULA-level (conservation), so
  every edge is L2's `HYPOTHESIZED` floor (a formally valid candidate); L2 **lifts** the structured rungs to
  `KNOWN`/`DERIVED` where sourced data reaches (the acetylation grades KNOWN).
- **R1 — the STRUCTURED descent now reaches through the ring (reaction level).** Ring-aware descent already
  existed at the *skeleton* level (`ScissionEdge`), so a ring atomises there; the gap was the *reaction* level
  — `capped_scissions` had no `ring_aware`, so a single cut opened no ring and ring-opening REACTIONS needed
  the full, expensive 2-cut powerset. R1 adds targeted ring-bond-pair cutting to `capped_scissions`: on
  paracetamol the ring opens into gradeable reactions as the *ring-opening subset* of the full 2-cut
  (`8 ⊂ 80 ⊂ 404` — tractable, never inventing an edge), and read backwards a ring-opening is the assembly of
  the ring, which L2 grades `HYPOTHESIZED`. So the structured chain reaches *through* the aromatic ring, not
  just to its irreducible core.
- **Chain assembly — the structured descent graded as ONE object.** The bridge that was missing between the
  decompiler and L2: `experiment/assembly.py` (`assemble_synthesis` + `find_scission`) turns a chosen
  multi-level structured descent — the amide hydrolysis, then a genuine *ring-opening* of 4-aminophenol — into
  one `SynthesisDAG` that `classify()` grades in a single shot (`HYPOTHESIZED`, worst-step-dominated, reaching
  *through* the aromatic ring). The backbone is the **capped** descent, chosen deliberately: its fragments are
  closed-shell real molecules (unlike the formula chain's `Formula` buckets or the structure graph's radical
  fragments), so they are legitimate gradeable steps. The two halves of "the whole chain from buckets" now
  both exist: the FORMULA chain proves atoms→target is conservation-complete; this STRUCTURED chain grades the
  chemist-legible rungs, lifting above `HYPOTHESIZED` where sourced data reaches. It reaches real intermediates,
  not bare atoms — stated as an assertion (`leaf_inputs` are polyatomic), never hidden.
- **R5-lite — a sourced aromatic rung lifts HYPOTHESIZED→DERIVED, gaps kept honest.** Four same-phase 298 K
  ΔfH°+S° pairs (phenol, aniline, nitrobenzene, toluene) were *fetched from the raw NIST WebBook and
  phase-checked* — not recalled — closing the anti-poisoning discipline. On them a real skeleton rung
  (nitrobenzene→aniline reduction) lifts from `HYPOTHESIZED` (seed) to `DERIVED` (R5-lite). The rungs that reach
  the drug itself stay honest, documented GAPS: 4-nitrophenol has no S° in any phase (a *fourth* instance of the
  same entropy-gap disease), 4-aminophenol has disagreeing ΔfH° sources.
- **SMILES aromatic heteroatoms — N-heterocycles unblocked.** The front door refused every aromatic heteroatom
  before R2's Kekulé matcher ran; the fix splits aromatic atoms into π-acceptors (C, pyridine-type `n` — join
  the perfect matching) and π-donors (`o`, `s`, pyrrole `[nH]` — sit out, single-bonded), so pyridine (C5H5N),
  pyrrole (C4H5N), furan (C4H4O), thiophene, imidazole now parse with correct valence; aromatic P still refused
  loudly. `_fill_hydrogens` needed zero changes.
- **R3 — recursive ionic descent.** v1 heterolysis split neutrals only, so an ion was a dead end (a single
  ionic level). R3 generalises `HeterolyticScission` to a CHARGED reactant under the *localized-charge model*
  (one fragment carries only the bond pair `±1`, the other the pre-existing charge; reduces to the neutral
  `(−1,+1)` at q=0; the even-charge split is the documented boundary — and this resurrects the dead charge-sum
  check as the live certificate). `IonicDecompositionGraph`/`ionic_decompose` then recurse it into a real graph
  with W1 termination: water dissociates recursively through its `[OH]` ion to bare ions; CO₂ (no order-1
  bridge) is surfaced as an HONEST irreducible ionic leaf — the same honest-leaf discipline R1 uses for ring
  cores.
- **R4 — the cross-level radical (open-valence) ledger.** Each `ScissionEdge` self-checks its LOCAL valence
  balance; nothing checked that a WHOLE descent conserves. `verify_radical_ledger` threads a spanning descent
  and verifies `total cut bond order + total surviving (core) order == target total bond order` — so the open
  valence created across every level is exactly accounted (benzene at cut=1: `6 cut + 9 surviving = 15`; ethane:
  `7 cut + 0 = 7`). The documented boundary: it conserves the open-valence BUDGET across levels; per-atom,
  per-path radical identity is bounded by canonical dedup — the remaining refinement.

**Still open:** the deep intermediates of a fully-structured atoms→paracetamol route still grade `HYPOTHESIZED`
for lack of sourced data (R5-full); L1 TST kinetics (the honest "real rate") remains the deeper frontier, atop
the permanent physical W3 wall.
