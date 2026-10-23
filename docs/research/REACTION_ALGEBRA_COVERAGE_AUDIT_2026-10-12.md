# Reaction-Algebra Coverage Audit — what SmartChem 1.0 cannot synthesize, and the families that would fix it

**Date:** 2026-10-12 (consolidated 2026-10-13) · **Method:** six read-only researchers fanned out across the
synthesis-chemistry space (heteroatom condensations+sigmatropic · carbonyl C–C · organometallic C–C · redox/FGI ·
substitution+arene · pericyclic+ring-forming), each confirming failures with live `search_routes` probes.

> This is a **coverage** audit, not a correctness-bug report. SmartChem's fail-closed promise held throughout: it
> refuses to *vouch* for what it cannot prove, rather than inventing chemistry. The task is to widen the algebra
> **soundly**, one conservation-locked family at a time — and, as it turns out, mostly to *recognise* and *gate*
> chemistry the generator already emits.

## Executive summary — the shape is not "missing reactions," it's a few structural walls + a recognition gap

The six probes converged on one picture, and it corrects the premise that triggered this audit (that the compiler
"only knows scission + Diels–Alder"):

1. **Capped scission is a general σ-bond metathesis**, not a fragmenter. `A–B + X–Y → A–X + B–Y`. Given the right
   byproduct in the reagent pool and the synthons in `available`, it **already generates** dehydrative
   condensations (esters, amides, ethers), SN2 substitutions, and metal cross-couplings (Kumada/Negishi/Heck/
   Sonogashira/Buchwald). **Paracetamol synthesises today** (4-aminophenol + acetic acid → paracetamol + water,
   vouched as acyl condensation). The earlier "paracetamol = 0 routes" claim was wrong — it used acetic *anhydride*.
2. **So the dominant gap is RECOGNITION, not generation.** Most of these generated routes are *demoted* because the
   reaction-type oracle (`reaction_type_oracle._RECOGNIZERS`, 17 classes) returns `None` on them. A demoted route is
   real chemistry the compiler refuses to vouch — correct fail-closed behaviour, but it means the route is invisible
   to the user. The cheapest wins are **conservation-locked recognizers for chemistry the generator already emits.**
3. **Bond-order-changing reactions need a `BondRule` (the DA mechanism), which capped scission cannot express.**
   Aldol, Michael, Henry, Mannich, Grignard addition, Wittig, imine/oxime formation, hydrogenation and all
   cycloadditions change a bond's order. These need new rule families — and **one already exists unwired**:
   `BondOrderEditProvider` does hydrogenation but is in no profile and has no recognizer.
4. **A handful of INFRASTRUCTURE walls each gate whole swaths of chemistry at once** (the Tier-0 section). These are
   the highest-leverage fixes: every one unlocks multiple families.

## Tier 0 — Cross-cutting infrastructure walls (each blocks many families)

Every one of these was hit independently by multiple researchers. They are the spine of the audit.

### W0.1 — The W1 strict-rank descent rule (hit by ALL SIX researchers)
`DecompositionEdge.__post_init__` / the capped-scission certificate require every retro precursor to be **strictly
fewer atoms** than the target (`decompiler.py:342`, `structure_descent.py:632,642`; `MediatedEdge` enforces it on
reagents too, `decompiler_mediated.py:101-110`). This blocks every retro step whose fragments aren't smaller:
- **Oxidation / dehydrogenation** (alcohol→carbonyl, amine→imine): precursor is heavier.
- **Hydrogenolysis / deoxygenation** (nitro→amine, ester→alcohol): precursor ≥ target.
- **Aryl-halide formation** (bromobenzene 12 atoms → benzene 12): rank-flat.
- **Intramolecular cyclo-dehydration** (lactones, lactams, furans, Dieckmann, intramolecular aldol): 1→1+H₂O, the
  open-chain precursor is larger.
- **Stoichiometric-carrier olefination** (Wittig Ph₃P=O rank 35 > stilbene 26; HWE phosphonate): the carrier
  byproduct exceeds the target.
- **Ring-closing metathesis**, and every **lateral (rank-flat) isomerisation** (Cope/Claisen/Nazarov).
**Fix:** a well-founded non-atom-count measure — candidates proposed by the researchers: lexicographic
`(heavy-atom-count, bounded-H-count)` or `(ring-count, atom-count)`, or a mediated/lateral edge class exempt from
strict descent. **Must be proven terminating** and must not break the `rule_calculus`/`lateral_search` proofs that
currently assume W1.

### W0.2 — Per-atom charge is dropped; charged species are refused
The molecule graph carries only **net** charge; the kernel bridge refuses charged species (`rule_calculus_bridge.py`
`_joined`), capped scission refuses charged atoms (`structure_descent.py:846`), and `BondRule` requires per-atom
bond-order-sum preservation which **every charge-separated species violates**. This blocks:
- **All 1,3-dipolar [3+2] cycloadditions** — azide/nitrile-oxide/nitrone/diazo — i.e. **triazoles (click chemistry),
  tetrazoles (the sartan drugs), isoxazoles/isoxazolines**. Highest pharma payoff behind one wall.
- **Diazonium chemistry** (Sandmeyer, Balz–Schiemann, azo coupling).
- **Phosphonium ylides** (Wittig), **iminium** (Mannich), nitro-group FGI.
Worse, DA guard-2c (`diels_alder.py:74,372`) was *built to reject* over-valent charge-separated centres (the
oxocarbenium/iminium false-vouch), so a dipole family needs a **principled carve-out** to it, re-adversaried.

### W0.3 — `ReactionCenter` is context-free (no hybridization / aromaticity / ring position)
`ReactionCenter` holds only element-pair + bond-order + component-count (`reaction_center.py:42-60`). So distinct
reactions have **byte-identical centres**, and centre-equality cannot tell them apart:
- SN2-at-sp3 ≡ SNAr (the R63 aryl-amination fake).
- Heck ≡ Friedel–Crafts alkylation ≡ a non-existent alkane C–H/R–X coupling.
- Buchwald ≡ alkyl-halide N-alkylation; Kumada ≡ Wurtz.
- Aldol ≡ acyloin ≡ "carbonyl hydroalkylation" fiction; benzoin ≡ Tishchenko ester.
- *ortho*/*meta*/*para* EAS are all identical (the compiler emits o/m/p-nitrotoluene identically).
**Fix:** a **radius-1 positive-whitelist predicate** (the carbon's hybridization/aromaticity, the director environment)
supplied *alongside* centre equality. The discriminators are bounded-radius (unlike the R49–R55 do-not-retry class),
so this is sound-able, but each needs its own conservation-lock + adversary pass.

### W0.4 — Catalysts, activators, bases and metal reagents are outside the conserved equation
Pd/Ni/Cu, AlCl₃, the base, the stoichiometric metal (Mg/Zn) and the hand-declared HX byproduct are not in the
stoichiometry. `catalyst_availability` treats an **undeclared catalyst as NEUTRAL** ("genuine silence"), so a vouched
Suzuki/Heck step with `envelope.catalysts == ()` would read as **kitchen-runnable — a false-VOUCH path.**
**Fix:** a coupling/catalysed recognizer must **require** a declared catalyst (else BLOCK), and an organometallic
reactant must trigger the inert-atmosphere equipment obligation (`equipment.py:178` currently fires only on a medium
keyword). An "activator ledger" (acid/base/Lewis-acid slot) is needed to cost Williamson, Friedel–Crafts etc. honestly.

### W0.5 — Missing elements block organometallics at the parser
`Li, Sn, Ni, Al, Ti` and bracketed `[B]` fail to parse (`atoms.py` PT). Organolithium (n-BuLi, LDA), Stille (Sn) and
boron-bracket reagents **cannot be `Molecule`s at all.** `units.molar_mass` already knows the masses, so this is a
data/PT + `_MAX_COORDINATION` gap only.

### W0.6 — Latent-fiction hazard: capped scission over-generates conserved nonsense
Because capped scission is an unguarded σ-metathesis, with the wrong helper in the pool it emits **conserved
fictions** caught *only* by the oracle's "unrecognized" demotion: `benzene + MgBr₂ → PhMgBr + HBr`, phenol-Suzuki,
unactivated `PhCl + NH₃ → aniline`, `butanone = acetic acid + ethane`, an `H₂O₃` peroxide ladder. **Soundness/security
item:** confirm every non-frontier consumer (plain `recompile`, DAG mode) also demotes these, and add must-not-vouch
regression controls. If a consumer does *not* demote, these surface as advertised routes.

---

## Categorical gap inventory

Verdict key: **CLEAN** (conservation-lock straightforward / proof already exists), **HARD** (a named extra invariant
or infra fix required), **COLLIDES** (hits a Tier-0 wall or a centre collision). "generate+demote" = capped scission
already emits it but the oracle won't vouch it.

### A. Heteroatom dehydrative condensations + [3,3]-sigmatropic
- **GENERATE + RECOGNISE today (the correction):** esters, amides, thioesters, dialkyl ethers, N-alkylation —
  paracetamol, aspirin, ethyl acetate, benzocaine, ibuprofen ester, glycylglycine, N,N-dimethylacetamide, diethyl
  ether all return `routes=1`, each step VOUCHED as acyl condensation / etherification / N-alkylation.
- **generate+demote (need a recognizer):** activated-donor acyl transfer (**acetic anhydride, acyl chloride** —
  the *industrial* paracetamol/aspirin route; demoted by the feasibility census at `feasibility.py:312-335,302`),
  transesterification, aryl-alkyl ethers (anisole, phenacetin), thioethers, sulfonate/phosphate/**nitrate** esters
  (tosylates, trimethyl phosphate, nitroglycerin class), intermolecular anhydride formation. Verdict: mostly CLEAN
  (R63-style census on the existing centre); transesterification HARD-lite (R48 non-locality).
- **not generated:** C=O⇄C=N condensations (imine/oxime/hydrazone/semicarbazone), acetal/ketal — need a `BondRule`
  (HARD: masked-carbonyl guard); intramolecular cyclo-dehydration (lactone/lactam/cyclic ether) — **W0.1 wall**.
- **[3,3]-sigmatropic (Cope/Claisen/aza-/thia-Claisen):** RECOGNISE-ONLY — oracle-vouched but **unreachable from
  `search_routes`** (lateral seam not wired in; W0.1 rank-flat; `forget()` raises). This is the one truly
  "recognize-but-not-generate" tier.

### B. Carbonyl-based C–C bond formation (9/10 absent, 1 by accident)
- **generate+demote:** Claisen ester condensation only — capped scission emits `2 EtOAc → ethyl acetoacetate` and
  **also the fiction `butanone = AcOH + ethane`** (nothing restricts the cut to a 1,3-dicarbonyl). Promote with a
  recognizer + a 1,3-dicarbonyl lock.
- **not generated (need H-shift `BondRule` + donor-EWG whitelist):** **aldol** addition/condensation, **Knoevenagel**,
  **Henry** (nitroaldol), **Michael** 1,4-addition — all CLEAN with a positive donor-activating-group whitelist (the
  4-vertex H-shift centre is shared across them, so the environment lock is mandatory — W0.3). **benzoin** CLEAN
  (centre collides with Tishchenko). **Mannich / Robinson** HARD (bundled multi-bond, R58 non-locality; needs iminium
  stock → W0.2). **Reformatsky** HARD (Zn ledger → W0.4). **Dieckmann / intramolecular aldol** HARD (**W0.1**).

### C. Organometallic & olefination C–C
- **generate+demote (need recognizer + W0.4 catalyst gate):** **Kumada/Negishi/Stille** cross-coupling — CLEAN at the
  type level (the metal-halide byproduct MgBr₂/ZnBr₂ is a real species); **Heck/Sonogashira/Buchwald** — **COLLIDE**
  at the centre (W0.3; need the sp2/sp-hybridization radius-1 discriminator). **Suzuki** HARD (the boron byproduct
  `BrB(OH)₂` is a fiction).
- **not generated (bond-order change):** **Grignard/RLi addition** to C=O (HARD — two-stage alkoxide+workup, W0.1
  workup, Mg(0) insertion not representable; RLi **blocked** by W0.5 missing Li); **Wittig/HWE** (centre CLEAN but
  **W0.1 + W0.2** block it — the Ph₃P=O carrier exceeds the target and the ylide is a phosphonium salt).

### D. Redox & functional-group interconversion
- **EXISTS-but-unwired (cheap win):** `BondOrderEditProvider` (`bond_order_edit.py:214`) does **hydrogenation**
  (C=C/C≡C/C=O/C=N/C≡N → saturated), supports linear+convergent routes, is in **no profile** and has **no recognizer**.
  Wire it in + add a recognizer and acetone→iPrOH, benzaldehyde→benzyl alcohol, nitrile→amine light up. Verdict HARD
  (catalyst-gate via `catalyst_availability.py`; chemoselectivity; the aromatic-Kekulé edit needs an adversary).
- **dead end:** `redox-half-reaction` is charge-only, `redox_displacement`/`electrochemistry` are inorganic-halogen
  and decompile-only — not wireable into organic FGI (record a VERIFIED-DEFER).
- **W0.1-blocked:** all **oxidation** (alcohol→carbonyl→acid, amine→imine, sulfide→sulfoxide), **hydrogenolysis**,
  **nitro→amine**, **reductive amination** (also needs a C=N condensation provider).

### E. Nucleophilic substitution, elimination & arene
- **generate+demote:** SN2 (Williamson, R–X→nitrile/azide/thiol/amine), EAS (nitration/sulfonation/Friedel–Crafts),
  SNAr — all emitted by capped scission, all `recognize_reaction_type → None`, several are **fictions** (unactivated
  SNAr→aniline/phenol, wrong-regiochem m-nitrotoluene, non-rearranged n-propylbenzene).
- **families:** **Elimination (E1/E2, dehydration)** — **CLEAN**, a 4-vertex fixed `BondRule` (C,C,H,X); today alkenes
  are reachable *only* via retro-DA; cheapest in this category. **SN2** HARD (leaving-group census vs SNAr collision,
  W0.3). **EAS** HARD (ring-local directing predicate, W0.3 + W0.4). **SNAr** COLLIDES (= aryl-amination fake; needs
  an activated-only ortho/para-EWG whitelist). **Aryl-halide formation** W0.1-blocked. **Diazonium** HARD (W0.2+W0.5).

### F. Pericyclic beyond [4+2] & ring-forming condensations
- **CLEAN new `BondRule` families (Tier-2 cheapest after A):** **[2+2]** cycloaddition (+ ketene/Staudinger
  β-lactam/Paternò–Büchi variants — exact 4-vertex centre); **hetero-ene** (carbonyl-/imino-/azo-ene — CLEAN for
  hetero enophiles, COLLIDES all-carbon so needs an enophile whitelist).
- **chemically CLEAN but W0.2-blocked:** **1,3-dipolar [3+2]** — triazoles, **tetrazoles (sartans)**, isoxazoles,
  isoxazolines. The rule objects are cheap; the charge wall is the blocker.
- **lateral seam (W0.1 rank-flat):** Nazarov, hetero-6π electrocyclisation, [2,3]-sigmatropic, intramolecular ene.
- **ring-construction condensations (HARD):** Paal–Knorr (pyrrole is **W0.1-safe**, the cheapest; furan/thiophene are
  W0.1-blocked), Knorr pyrazole, Pinner pyrimidine, Hantzsch, Biginelli, Fischer indole — each a multi-water bundle
  needing its own conservation-lock proof + Kekulé-aware rule.
- **RCM** W0.1-blocked (acyclic cross-metathesis already works).

---

## Tiered issue roadmap

**Tier 0 — infrastructure** (unlocks whole classes; do these first): W0.1 W1-rank redesign · W0.2 charged rail ·
W0.3 ReactionCenter context · W0.4 catalyst/activator ledger · W0.5 missing elements · W0.6 latent-fiction audit.

**Tier 1 — recognisers for already-generated chemistry** (cheapest; the generator exists): activated-donor acyl
transfer (anhydride/acyl chloride) · aryl/thio/oxoacid ethers & esters · SN2 at sp3 · metal cross-couplings
[needs W0.3,W0.4] · wire `BondOrderEditProvider` hydrogenation + recogniser · Claisen condensation + decline fiction.

**Tier 2 — clean new `BondRule` families** (DA pattern transfers): elimination · carbonyl-C–C enolate
(aldol/Knoevenagel/Henry/Michael) · [2+2] + hetero-ene · C=O⇄C=N condensation (imine/oxime) · Grignard C=O addition.

**Tier 3 — blocked-on-infra families:** 1,3-dipolar [3+2] [needs W0.2] · oxidation / dehydrogenative FGI [needs W0.1]
· lateral-hop route search for [3,3]-sigmatropic + ring-construction condensations + SNAr activated-only.

Every family above carries a conservation-lock obligation and an independent adversary pass (evil-morty/dalembert)
before it may VOUCH, per the repo's standing discipline; family expansion stays frozen-by-default and each lands
behind its own gate. Filed issues track each cluster; this document is their shared reference.
