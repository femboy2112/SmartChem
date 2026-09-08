# DOW bromine cost ranking — contract (ROUND 31, queue item 2's last lane)

> **Status:** design contract, build-ready — folded against two pre-build bearings (butter-robot YAGNI + birdperson soundness).
> The DOW-bromine litmus's **decomposition + synthesis** questions are answered (pricing R16, mechanism R17, electrochem R18,
> thermo R26, kinetics R30). This closes the **last open lane**: *can we rank the two Br₂ routes on cost, and reproduce why
> Herbert Dow's brine-bromine process undercut the German Bromkonvention cartel?* — subject to the user's explicit flag: **the
> litmus may not pass at today's prices vs early-1900s prices.** That flag is correct; confirming it rigorously (not fabricating
> a modern "pass") is half the deliverable.

## The two questions, kept separate (conflating them is the fabrication trap)

1. **Modern:** rank the brine-displacement route (Cl₂ + 2 Br⁻ → Br₂ + 2 Cl⁻, R17) against buying Br₂ at market, on today's
   sourced prices. **Answer: no undercut is *demonstrable from the sourced data* — the only priced feedstock basis is a proxy
   of the very benchmark being undercut, and it collapses the two routes.** *The litmus's cost-undercut does NOT pass at today's
   prices with the data we can source.*
2. **Historical:** reproduce *why* Dow undercut the cartel ~1904–1907. **Answer: the US brine route's sustainable marginal cost
   was far below the cartel's administered price — a ≳39 % undercut at normal pre-war prices, and ≳79 % against the war-survival
   cost ceiling — proven as a one-sided lower bound from cross-corroborated sourced period prices.** *The litmus passes historically.*

## Theorem 1 — the modern degeneracy (why today's *sourced* prices cannot show an undercut)

Established in `docs/research/SOURCING_RECON_2026-09-07.md` (conditional cost obstruction), made a first-class tested result here.
Let `q > 0` be the sourced bromine benchmark **price per unit mass of contained Br** (USGS import unit value, $2.70/kg contained
Br, 2024). A NaBr feedstock priced *purely by its contained-Br mass fraction from that same benchmark* is `p(NaBr) = q·M(Br)/M(NaBr)`.
Stoichiometry needs `M(NaBr)/M(Br)` mass units of NaBr per unit mass of Br₂ (Br₂ is pure Br). The feedstock cost per unit Br₂ is
therefore **exactly `q`** — the mass factors cancel — *before* any chlorine, cylinder rental, yield loss, energy, or process cost:

> **brine_total = q + (Cl₂ + rental + losses + process) ≥ q = mined_total,** strict whenever any oxidant/process cost is positive.

**This is a conditional algebraic result about the same-benchmark PROXY, not an observation about real brine economics** (the
sourcing recon's own words). Two soundness heeds (birdperson), both binding on the verdict:

- **The negative is scoped, never absolute.** `NO_UNDERCUT` means *"no undercut is demonstrable from the sourced same-benchmark
  proxy,"* and **must never be read as "brine is worse in reality."** Real modern brine bromine (Smackover, Dead Sea) *does*
  undercut market Br₂ — well-brine bromide is nearly-free raw material oxidized by cheap Cl₂ — precisely because it carries an
  **independent** feedstock cost basis. We simply cannot *source* that independent basis today, so we cannot *demonstrate* the
  real-world undercut. The degeneracy proves independence is the *only* representable route to an undercut; it does not prove
  brine loses.
- **The certification guard needs its own sourcing bar.** An undercut is certified *only* when the brine feedstock carries an
  **independent, separately sourced + dated + labelled** basis (clearing the same bar as `q`) **and** brine < mined. An unsourced
  injected "cheap NaBr" number must NOT open the gate (that would manufacture the very fabrication this round forbids). A gate that
  opens on any handed-in value is not a gate.

Concrete modern instantiation (recorded, not admitted — the R22 discipline): the sourced Cl₂ reconnaissance price (Los Fresnos
approved municipal offer, $2.7337/kg Cl₂, `SOURCING_RECON_2026-09-07.md`) makes `brine_total = q + (positive Cl₂ term) > q` explicit.
Used as a **labelled reconnaissance input to the demonstration**, never committed to default commodity pricing.

## Theorem 2 — the historical undercut (a one-sided *economic* bound at the route/industry level)

**Re-anchored per birdperson** — the earlier draft misattributed the German *dumping* floor to Dow and leaned on *arbitrage* as
if it were production cost. Corrected:

- The bound is anchored on the **sustained multi-year USGS US bromine unit value** (revenue ÷ tonnage, an industry aggregate), a
  defensible **upper bound on the US brine-route marginal cost**: the US industry *produced and sold* bromine in tonnage at these
  unit values for years, and competitive entry/exit makes a *whole-industry* multi-year cross-subsidy implausible (a single firm
  could sustain losses; an industry cannot for four straight years). The claim is stated at the **route/industry level**.
- **Attribution to Dow specifically is a LABELLED assumption**: Dow was a leading *continuing US brine-bromine producer* through
  1904–1908, so the industry bound plausibly applies to him — but the sources do **not** disclose Dow's own price or cost, so his
  specific margin is asserted only under that stated assumption.
- **The one-sidedness is ECONOMIC, not physical** — "a firm/industry will not sustainably sell below marginal cost." This is the
  *same one-sided shape* as ROUND 30's kinetics bound but a **weaker, defeasible foundation** (R30's was a physical law); the named
  exception — **predatory pricing** — is exactly this episode's theme, so **cross-subsidy over a multi-year loss cannot be
  excluded from these sources and is carried aloud.** NOT "identical to R30."
- The German dumping floor (15 → 12 → 10.5 ¢/lb) is the **cartel's aggressor price**, presented as the price-war *trajectory* —
  **explicitly NOT used as Dow's cost.** Re-export at 27 ¢/lb is **arbitrage** (buy German at 15 ¢, resell in Europe) — evidence of
  a spread, **not** a production-cost datum.

### The layered result (inflation-neutral — ratios of same-era prices)

1. **Pre-war undercut (robust, undistorted):** cartel administered **world price 49 ¢/lb** vs the US sustainable price **~30 ¢/lb**
   (USGS 1904 unit value $661/t = 30.0 ¢/lb) / **36 ¢/lb** (secondary US producer price) → the US brine route undercut the cartel by
   **≈ 39 %** (USGS) to **≈ 27 %** (secondary) at *normal, sustained, undistorted* prices. This alone reproduces "the US brine route
   undercut the cartel."
2. **War-survival cost ceiling (deeper, one-sided):** the US industry *survived* the price war *producing* at **~10 ¢/lb** (USGS
   1908 unit value $220/t = 9.98 ¢/lb) → US brine-route marginal cost **≤ ~10 ¢/lb** → the achievable undercut of the 49 ¢ cartel
   price was **≥ ≈ 80 %.** This explains why Dow could *win* the war: the brine route's cost floor was far below the cartel's price.

The cartel's 49 ¢ was a monopoly-administered price far above brine-route marginal cost; today's single blended benchmark has no
such spread, so the modern undercut is unrepresentable from sourced data (Theorem 1).

### Sourced period prices (two provenance-diverse families; agreement corroborates the PRICE LEVEL, not Dow's cost)

**Secondary (business-history narrative, cross-corroborated across independent outlets):** cartel fixed world price **49 ¢/lb**,
US price (pre-1904) **36 ¢/lb**, German US dumping (1905) **15 → 12 → 10.5 ¢/lb**, Dow re-export **27 ¢/lb**.
- Folsom, B.W. Jr., *Herbert Dow and Predatory Pricing*, FEE — https://fee.org/articles/herbert-dow-and-predatory-pricing/
- Mackinac Center, *Herbert Dow, the Monopoly Breaker* (V1997-13) — https://www.mackinac.org/V1997-13

Neither discloses Dow's own production cost — *why* the one-sided industry bound (not a fabricated exact cost) is the only honest route.

**Primary (USGS Data Series 140, bromine historical statistics — the same source family as the R16 USGS bromine price):** US
bromine **unit value, nominal $/t, bromine content**; the file header states *"[All values are in metric tons (t) bromine content]"*
(so the ¢/lb conversions use the **metric tonne**, 2204.62 lb — the short-ton misread would shift every figure ~10 %). File sha256
`1a4c1cf512ff48de60456c4f546f3d66eafac5b2549cbe3be9bb811438744258`, last modified 2023-08-07:
1904 **$661/t = 30.0 ¢/lb** (pre-war) · 1905 **$331/t = 15.0 ¢/lb** · 1906 **$282/t = 12.8 ¢/lb** · 1908 **$220/t = 10.0 ¢/lb**
(war floor). The 1904→1905 unit value fell **49.9 %** — the price-war halving.

**On the two bearings (birdperson):** they are provenance-diverse (a narrative transaction price vs a computed statistical unit
value) — *not* the reframed-check disease (not one quantity in two costumes). But their ~1 ¢ agreement corroborates the **price
level** only; it does **not** touch the load-bearing `price → cost upper bound` step (that rests entirely on the economic-rationality
premise above). And full independence-to-root is **not proven** — both could ultimately draw on the same period trade-journal price
reporting (possible common-mode); asserted, not established. Confidence is not laundered from where it is earned (the price level)
to where it is not (Dow's cost).

## The build (a committed harness + receipt + doc + test — NO importable module; butter-robot)

The two theorems are one-shot arithmetic over sourced numbers. A `smartchem/experiment/` module with a `modern_undercut`/
`historical_undercut` API would be imported *only by its own test* (the self-mirror / zero-call-sites disease) and parameterizes a
computation invariant to its own inputs (the degeneracy holds for any `q`). So — the R30 *analogy is dropped* (R30's module computed
a reusable rate law; this computes a fact):

- **`experiments/dow_bromine_cost_probe.py`** — a committed FROZEN_HASH harness (the "experiments are committed" discipline). Flat
  module-level helpers (not a public API): computes `p(NaBr)`, shows it equals `q`, adds the sourced Cl₂ recon term to show
  `brine_total > mined_total` → the scoped `NO_UNDERCUT` verdict; computes the layered historical undercut bounds; asserts the
  two-family price-level agreement; `validate()` asserts every claim, `content_hash()` freezes, `report()` prints.
- **`experiments/dow_bromine_cost_recon_2026_09_08.json`** — the machine-readable sourcing receipt (URLs, sha256, figures, dates,
  boundaries, the metric-tonne basis, the caveats).
- **`tests/test_dow_bromine_cost.py`** — the degeneracy strict inequality + direction, the fail-closed refusal to certify an undercut
  from an unsourced/proxy basis, the scoped-negative wording, the one-sided layered historical bounds, the two-family agreement, and
  `hash_matches`.
- **`docs/research/DOW_BROMINE_COST_RANKING_CONTRACT_v0.1.md`** — this doc, the answer.

## Scope boundaries (named DEFERRED, not silently skipped)

- **Cost is NOT wired into the general route ranker** (`_route_score`/`_dag_score` stay thermochem+composability only) — a deliberate
  schema-bump round churning every route golden, needing a real *multi-route cost-ordering* consumer. The DOW two-route question is
  answered by the theorems without it; the standalone Pareto affordability frontier (`affordability.py`) stays the cost citizen.
- **No contested Cl₂ spot price is committed to default commodity pricing** (the Los Fresnos offer stays reconnaissance — R22).
- **Historical figures are HISTORICAL** — recorded in the harness/receipt/doc, never admitted to the modern USGS/Methanex seeds.
- **A sourced independent brine-feedstock cost basis** (Smackover/Dead Sea well-brine extraction cost) would let the *modern*
  undercut be demonstrated; it is the open sourcing wall (UNLOCK for a modern pass).

## Preservation obligations
- Additive: a harness + receipt + test + this doc. **NO existing table, seed, golden, or digest moves** (no Cl₂ committed, no ranker
  change) — byte-stable, the R30 shape.
- `known-physics-not-new-physics`: every price sourced + dated + labelled; the modern verdict is a *scoped* honest negative; the
  historical undercut is a one-sided *lower* bound at the route/industry level with the cross-subsidy caveat aloud; nothing tuned to
  force the historical narrative (the sourcing recon's explicit warning).
- Adversarial (evil-morty) review before commit, as every prior DOW round had. Build-time check (birdperson): the harness/test never
  cross the modern and historical inputs, and the certification guard requires a *sourced* independent basis.
