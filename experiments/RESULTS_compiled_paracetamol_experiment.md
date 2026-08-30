# M-5 Experiment Compiler — paracetamol litmus, end to end

**Harness:** `experiments/compiled_paracetamol_experiment.py` · **Gate:** exits non-zero on any hard failure
**Run:** `.venv/bin/python experiments/compiled_paracetamol_experiment.py` → **VERDICT: PASS (17/17), exit 0**

## The question

Given the decompiler's candidate routes to a real target, can the Experiment Compiler (M-5) verify them as
runnable experiments, refuse the degenerate ones for the right *sourced* reasons, fit them to a real bench,
and draft a chemist-usable procedure — all under the **known-not-new-physics** discipline (reproduce known
chemistry; never invent a feasibility/kinetics/yield model)? Not *"does the synthesis work"* — W3 forbids
that — but every fact the compiler asserts must hold, and every refusal must cite a sourced fact.

## What ran, and what held (17/17)

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

- **W3 held.** No rate, no time-to-completion, no yield below the ceiling. The 100%-efficiency ceiling is
  the only outcome number, `CONSERVATION`-labelled as an upper bound.
- **Universal engine, sourced data.** Formal layers (E0/E1-logic/E2/equipment) run on any parsed molecule;
  the stability/thermo data is a SEED that degrades to a loud `UNKNOWN` and is injectable per call — proven
  by the off-seed lever above. Not a whitelist.
- **Sourced-model gaps, stated:** the pressure-dependence of phase (Clausius–Clapeyron) is not attempted by
  E1; a chemist injects sourced pressure tolerance to extend it. Equipment selection is standard bench
  practice, not a claim the reaction proceeds.
