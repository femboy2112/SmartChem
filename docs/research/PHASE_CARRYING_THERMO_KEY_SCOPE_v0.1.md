# Phase-carrying thermo key — bounded admission (item 5)

Status: **built for the table/resolver layer; the per-step phase source is a named next brick.**

Lane B·C. Closes the ROUND-26 M2b carried debt (a): a sourced `for_formula` hit was phase-blind, so a future
reaction reasoning about liquid Br₂ through the thermo layer would silently inherit the gas ΔfH° (+30.91 kJ/mol).

## What is admitted

1. `ThermoRef.phase` is now part of a record's lookup **identity**, not decoration. `ThermoTable.with_records`
   deduplicates on the `(formula, name, phase)` triple, so a gas and a liquid record of one species coexist
   instead of the later one silently overwriting the earlier at write time (the old `(formula, name)` key was a
   last-value-wins overwrite with **no error**).
2. `for_formula(formula, phase=None)` and `for_named(formula, name, phase=None)` narrow the match to `phase`
   when given; a phase-**blind** query returns a hit IFF exactly one record matches, and otherwise fails closed
   to `None`. This is the same isomer-ambiguity honesty `for_formula` already applied, extended one dimension.
   It is a **strict superset** of the prior behaviour: every single-phase species resolves identically under a
   phase-blind query; only a genuinely dual-phase species (today, only Br₂) is affected, in the **safe
   direction** — a loud `None`/UNKNOWN, never a wrong number. `resolve_thermo` also fails closed at the
   group-additivity **`derive` gate** (`ThermoTable.is_multiphase`): a phase-blind query for a dual-phase species
   does **not** fall through to a gas Benson estimate that would ignore the phase question — so the guarantee is
   the design's, not purchased by Br₂'s Benson-uncoverability (an adversarial-review fold: a Benson-*coverable*
   dual-phase species would otherwise get a silent gas estimate).
3. The live table gains bromine's true-standard-state **liquid** record, mirrored byte-for-byte from the frozen,
   cross-checked CODATA seed (`experiments/thermo_codata_seed.py`): Br₂(l), ΔfH° = 0 by convention,
   S° = 152.21 ± 0.30 J/mol/K. No new number is sourced — this closes a **wiring** gap that the frozen seed's own
   docstring named as "the next brick." `[[known-physics-not-new-physics]]`
4. `resolve_thermo`, `feasibility_of_step`, and `route_net_delta_g` now thread an optional phase. A caller
   declares the standard-state phase of any dual-phase species (keyed on canonical **structure**, never formula
   — `[[a-reaction-key-by-formula-borrows-a-rate]]`), and a phase-ambiguous species with no declaration resolves
   to `None` → a loud UNKNOWN verdict, never the silently-wrong-phase ΔfH°. So `resolve_thermo(Br₂)` phase-blind
   is UNKNOWN (the debt, as negative space), while the R26 DOW-Br₂ gas dissociation now DECLARES gas
   (`phases={Br₂: "gas"}`) and keeps its +161.65 kJ/mol verdict — the debt closed **and** the north-star result
   preserved through one interface. (This threading was forced by an adversarial review: adding the liquid record
   made the mainline `feasibility_of_step(Br₂→2Br)` fail closed and gut the R26 verdict; the fix is the resolver
   learning to say which phase it means, not the record.)

## What is not claimed

- **The upper route/rank/DAG layers do not thread `phases`.** The per-species phase override reaches
  `feasibility_of_step` and `route_net_delta_g` (the R26 consumer), keyed on canonical structural identity —
  never bare formula (`[[a-reaction-key-by-formula-borrows-a-rate]]`: two co-reacting isomers of one formula must
  not share an override, and elemental Br₂ is absent from the named registry, so the key must be structural).
  It is deliberately **not** threaded through `verify_feasibility`, `drafter`, `meta_compile`, `dag`, `classify`,
  or `equilibrium`. This is **sound, not a gap**: those layers process no phase-ambiguous species today (only Br₂
  is dual-phase, and no ranked route / DAG contains it), and if one ever did, the un-threaded call fails **closed**
  to a loud UNKNOWN — never a silent wrong-phase number. Threading `phases` up those layers is the next brick,
  triggered the first time a ranked route carries a dual-phase species.
- **Nothing is misled today.** No live route reasons about elemental Br₂ through `feasibility_of_step` (the DOW
  displacement runs on sourced electrode potentials, not Gibbs-from-thermo), so the closure is preventive for
  the first future route that does — matching the debt's own framing.
- **A phase-transition step is not representable, and this item does not make it so.** A reaction written as
  `Br₂(l) → Br₂(g)` has the same species on both sides; `_coefficient_vector` nets it to a spectator (the balance
  vector is empty), so `feasibility_of_step` returns `BORDERLINE, ΔG=0` — a pre-existing behaviour, not introduced
  here, and the single-phase-per-canonical `phases` map cannot say "liquid left, gas right" either. Item 5's scope
  is **reaction/dissociation thermo, not vaporization**; the new liquid record must not be read as enabling
  phase-transition reasoning. A first-class phase-change step (ΔvapH/ΔvapS) is separate future work.
- **The network-fetch cache is out of scope.** `smartchem/data/autoload.py`'s `ThermoCache._struct_key` is
  phase-blind at the fetch layer (its key is the canonical digest only), so a fetched liquid record for a species
  already cached in gas phase would overwrite it. That is the same architectural gap one layer further out and is
  **not** closed by wiring `SEED_THERMO_REFS`/`ThermoTable` alone; it is named tracked debt.
- The `phase.py` `estimate_phase` (Clausius–Clapeyron) mechanism is a **separate**, already-phase-aware path for
  E1's stability-transition check operating on `StabilityRef`, not `ThermoRef`; it is not conflated with this item.

## Verification

The liquid value is a transcription of an already-frozen, already-cross-checked CODATA number (NIST WebBook +
the official CODATA table agree; JANAF/Chase 1998 within ±), so no physical oracle is re-run. The key
generalization is checked by property tests: the dual-phase coexistence, the fail-closed phase-blind refusal, the
exact phase-narrowed values, a write-time no-silent-overwrite mutation test, the `resolve_thermo(Br₂) → None`
negative-space test, and a regression net over every single-phase seed species. The mandatory same-commit
migration of `experiments/dow_bromine_kinetics_probe.py` (its `for_formula("Br2")` → `phase="gas"`) keeps the gas
values, so ΔG₂₉₈(Br₂→2 Br) stays +161.65 and the probe's `FROZEN_HASH` is byte-identical (no golden regenerated).

Evidence is executable in `experiments/thermo_phase_key_probe.py` and `tests/test_thermo_phase_key.py`.
