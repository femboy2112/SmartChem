# OPERATION SMARTCHEM XII — scientific hardening of the 1.5 candidate (2026-10-31)

A hostile scientific review of the CI-green 1.5 release candidate (PR #149), repairing claims that are not
scientifically universal. This record is **append-only** relative to the 1.5 consolidation dossier
([`V1_5_CONSOLIDATION_2026-10-30.md`](V1_5_CONSOLIDATION_2026-10-30.md)), which stays a dated record of what was known
on 2026-10-30; the corrections below revise specific conclusions and say so explicitly.

> **Reviewable work on the candidate branch `integration/v1.5-candidate` (PR #149). Nothing is merged into protected
> `main`, tagged, or published.** The release remains the production 1.1.0 (`main` `9e8fa5f`, tag `v1.1.0`).

## Coordinates

- Branch `integration/v1.5-candidate`; baseline this round began at `55a44c6` (the 1.5 candidate, all §4 gates MET).
- `9e8fa5f` (= released `v1.1.0`) is an ancestor; `main` is untouched.
- Commits this round (newest last): `75c0119` (1A), `1c46279` (1B), `5c29f70` (1C).

## P0 — hostile scientific review (§1 of OPERATION XII)

### 1A — the universal transition-metal hydrogenation requirement was scientifically false (REPAIRED · `75c0119`)

**Claim refuted.** The activator ledger stamped EVERY recognized hydrogenation with a universal
`TRANSITION_METAL_CATALYST` requirement (its docstring asserted "a UNIVERSAL requirement"). That is false for the
nitrogen-unsaturation subdomain: metal-free frustrated-Lewis-pair (FLP) catalysts catalytically hydrogenate **imines
(C=N)** and lone-pair-sequestered **nitriles (C≡N)** — Chase, Welch, Jurca & Stephan, *Metal-Free Catalytic
Hydrogenation*, Angew. Chem. Int. Ed. **2007**, 46, 8050–8053, DOI [10.1002/anie.200702908](https://doi.org/10.1002/anie.200702908)
— and explicitly **not aldehydes** (C=O reacts only stoichiometrically). Source read and substrate domain confirmed
before any code change.

**Direction.** The ledger is a demoter; the defect was a false *reason / false universal* ("only a transition metal
can"), not a false-VOUCH. The repair stays on the feasibility axis.

**Repair.** The requirement is split by the reduced bond, keyed on the step (mirroring the existing SN2 pKa-regime
precedent), so hydrogenation moves from the class-keyed `REQUIRED_ACTIVATORS` to `_conditional_required_roles`:

| reduced bond | required role | cleared by |
|---|---|---|
| genuine imine (C=N) / nitrile (C≡N) | `HYDROGEN_ACTIVATION_CATALYST` (new) | a transition metal **or** a metal-free FLP (`B(C6F5)3` / `BCF` / tris(pentafluorophenyl)borane) |
| C=C / C=O / C≡C / indeterminate | `TRANSITION_METAL_CATALYST` | a transition metal only (fail-closed to the narrower set) |

- The metal-free whitelist is **disjoint** from the transition-metal set and case-certified (no arbitrary text label
  clears), so a C=C / C=O hydrogenation is **never** cleared by an FLP — the module's named unsafe direction
  (false-CLEAR) stays closed by construction. A transition metal clears the imine/nitrile case a fortiori.
- The recognizer is behavior-identical (the bool recognizer is now "the reduced-bond witness is not None").
- New import-time guard protects the step-conditional class anchors (SN2, hydrogenation) against a silent
  rename-disarm.

**Adversarial re-attack (evil-morty, read-only).** Five of six attack vectors held (verified). One **false-CLEAR**
found and **repaired in the same round**: keying on the reduced bond's element pair `{C,N}` was too coarse — an
**oxime** (C=N–O), **hydrazone / azine** (C=N–N), **amidine / guanidine** (the C=N carbon bearing a second N) and the
**isocyanate / carbodiimide cumulenes** (the carbon carrying a second multiple bond) all reduce through a C=N yet are
not metal-free-FLP substrates. Replaced the element predicate with a structural witness
(`hydrogenation_reduces_imine_or_nitrile`) that reads the reduced bond's *environment* and excludes all five; locked by
regression tests.

**Residual boundary (honest, Problem B).** The catalytic FLP turnover classically needs a *sterically hindered* imine
(unhindered imines run B(C6F5)3-mediated); the constitution-only graph cannot represent sterics, so the vouch stays the
existential Problem-A claim "a metal-free catalytic hydrogenation of an imine/nitrile of this constitution is
experimentally established", not a feasibility claim for a specific substrate.

### 1B — the SN2 recognizer over-claimed a mechanism constraint (REPAIRED · `1c46279`)

**Claim corrected.** A graph rewrite cannot establish a reaction *mechanism*. The `_sn2_substitution` docstring claimed
the radius-1 carbon gate "supplies the MECHANISM constraint". Corrected: the gate supplies **SN2-COMPATIBILITY** (a
necessary structural condition — sp3, non-tertiary, single-heteroatom, halide LG), excluding the structural impostors
(SNAr / vinylic / acyl / tertiary-SN1 / oxocarbenium). It does **not** resolve the SN1/SN2/E2 competition
(solvent/kinetics-dependent, unrepresented) and mints **no** stereochemical (Walden-inversion) claim (the
constitution-only `Molecule` carries no configuration; the CLI `--match-layer configuration` is refused until stereo
perception exists). IUPAC Gold Book terms `SN2` / `bimolecular`.

**Scope.** Documentary + one boundary test; no wire rename, recognizer registry digest `0dfb95140ad927ef` untouched,
golden NO DRIFT. Independently confirmed nothing downstream mints a stereochemistry or SN1-vs-SN2 claim. The vouch is
the oracle's standard existential "a mechanism of the SN2 TYPE is structurally available"; a secondary substrate (where
SN1/E2 compete) still vouches, because SN2 is a structurally available mechanism there — the vouch does not claim it
wins.

### 1C — the oxygen base-regime classifier calibrated against a preregistered corpus (VERIFIED SOUND · `5c29f70`)

**Claim corroborated (no code fix needed).** `sn2_oxygen_base_regime` keys on the **hydroxyl carbon's own** order≥2
bond, so a C=C / C=O *near but not on* it does not relax the base requirement. Verified against a preregistered
source-backed corpus + hostile holdouts, now locked as tests:

- positive: carboxylic acid (pKa 4.76), phenol (9.95), enol (~10.5) → `mild`;
- the positional discriminators a naive "any unsaturation → mild" rule would false-CLEAR:
  **enol** (C=C *on* the OH-carbon → mild) vs **allyl alcohol** (C=C *near*, pKa ~15.5 → strong) — same bond, opposite
  regime; carboxylic acid (C=O *on*) vs **β-hydroxy carbonyl** / glycolaldehyde (C=O *near* → strong); **1,2-diol**
  (poly-ol, ambiguous nucleophile → fail-closed strong); the **C=N iminol** (amidate-level pKa ~17–22 → strong, the
  prior evil-morty exclusion).
- Every `strong` holdout stays demoted under a mild base (K2CO3 / NaOH / Et3N / DBU) — the unsafe false-CLEAR direction
  is closed. The `mild` whitelist tops out at conjugate-acid pKa ~10.5 (carbonate), so only sub-11 acids clear mild.

## Scientific claim ledger (P0 §1)

| claim | status | evidence |
|---|---|---|
| hydrogenation universally needs a transition metal | **REFUTED** → repaired | Stephan 2007 (DOI above); `75c0119` |
| a C=N element pair implies a metal-free-FLP substrate | **REFUTED** (false-CLEAR) → repaired | evil-morty; structural witness in `75c0119` |
| the SN2 gate establishes the SN2 mechanism / inversion | **CORRECTED** to SN2-compatibility, existential vouch | `1c46279` |
| the O base-regime classifier is fooled by nearby unsaturation | **REFUTED** (classifier is positional) | preregistered corpus `5c29f70` |

## Gates (P0 §1, local, on each commit)

- ruff clean (changed files); targeted suites green (activator 259, SN2 40, hydrogenation/recognizer 52, corpus 4).
- Version-independent payload golden: **NO DRIFT** on every commit (all three corrections ride the feasibility layer
  or are documentary; none moves a search/semantic identity).
- Full OOM-safe suite + hosted CI: pending on the P0 §1 tip (recorded in this file when complete).

## Remaining (scoped, not yet executed this round)

- **P0 §2** — DAG admission trust-tier matrix (advisory vs verified); honest tier labelling.
- **P1/P2** — event-type invariant enforcement; a real type-3 `INTRAMOLECULAR_COPRODUCT` generator (lactonization)
  with its own well-founded termination proof.
- **P3** — independent imine-condensation witness; elimination via the rank-increasing event rail; aldol scoping.
- **P4** — physicalization (separate 2.0 research branch): mixed acetate/carbonate PHREEQC benchmark; open/sealed gas
  boundaries; conservative chamber transport.
