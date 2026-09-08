# DOW-BROMINE-KINETICS-01 — the kinetic half of the DOW-bromine litmus (queue item 3b)

> ROUND 30. Branch `dow-bromine-kinetics-2026-09-08` (stacked on the open R29 branch). Lane B·C, *(DOW)*.
> Governing discipline: `known-physics-not-new-physics` — reproducing a wrong rate/verdict is FABRICATION and
> forbidden; a DEFER/UNKNOWN is always acceptable. A precise bench-T rate obtained by naively extrapolating a
> shock-tube fit across a ~900 K gap WOULD be fabrication; this contract says exactly what is and is not
> licensed.

## 1. The task

The DOW-bromine litmus (`ROADMAP.md`) asks us to *predict Br₂'s decomposition and synthesis*. ROUND 26 closed
the **thermodynamic** half (`Br₂ → 2 Br•` is endergonic at 298 K, ΔG = +161.65 kJ/mol, so Br₂ is stable at the
bench). This round closes the **kinetic** half from the recovered primary — the last modeling wall on the
litmus's decomposition question. (The *cost ranking* remains the only other open lane; see ROADMAP DEFERRED.)

## 2. The recovered primary (SOURCED)

Marvin Warshay, *Shock-Tube Investigation of Bromine Dissociation Rates in Presence of Argon, Neon, and
Krypton*, NASA TN D-3502 (July 1966). Gas mixtures 1 % Br₂ / 99 % noble gas, incident shocks, **1200–1900 K**.
Receipts (URL, SHA-256 `c29f0b03…afdd7`, page anchors): `docs/research/SOURCING_RECON_2026-09-07.md`.

```
Br2 + M <=> 2 Br + M        -d[Br2]/dt = kD·[Br2]·[M]        (BIMOLECULAR, collider M)
kD = A · T^(1/2) · exp(-Ea/RT)                               (MODIFIED Arrhenius, √T prefactor), L mol^-1 s^-1
```

| Collider M | A (L mol⁻¹ s⁻¹ K⁻½) | Ea (kcal/mol) | Ea (kJ/mol) |
|---|---:|---:|---:|
| **Ar** (seeded) | 2.18 × 10⁸ | 31.5 | 131.80 |
| Ne (parked) | 1.82 × 10⁸ | 31.3 | 130.96 |
| Kr (parked) | 4.32 × 10⁸ | 33.6 | 140.58 |

Representative Table I point: kD(1825 K, Ar) observed **1.48 × 10⁶**; the fit gives **1.574 × 10⁶** (+6.3 %).
Warshay's fit **omits the reverse recombination and Br₂-as-collider** (dilute, initial-rate measurement).

## 3. The modeling bridge — a new sibling, not the first-order seed

`smartchem.data.kinetics.KineticRef` is *plain* Arrhenius (`k = A·exp(-Ea/RT)`) and its `is_first_order` is
literally `a_units == "s^-1"` — Warshay's √T *bimolecular* form cannot be represented there, which is exactly
the boundary the sourcing recon drew ("do not add these values to the existing first-order seed or rename their
units"). So the model is a **sibling**, `smartchem/experiment/collider_kinetics.py`, keyed on canonical
structure like every other rate:

- `ColliderDissociationRef` — the sourced modified-Arrhenius fit (`log10_a`, `t_exponent`, `ea_kj_per_mol`,
  `a_units`, `collider` **label**, `temperature_range_k`, `provenance`). The collider is a plain element label
  (`"Ar"`), not a SMILES — a monatomic inert third body has no structure to canonicalise, and `[Ar]`/`[Ne]` are
  not even parseable; the label still prevents applying Ar's `(A,Ea)` under a neon `[M]`.
- `dissociation_rate(ref, T)` = `A·T^n·exp(-Ea/RT)` (log-space, overflow-honest) — the reverse-free RATE.
- `pseudo_first_order_k(ref, T, [M])` = `kD·[M]` — the *conditional derived* pseudo-first-order coefficient;
  `[M]` is REQUIRED and validated finite > 0 (a fabricated/absent collider concentration is a fabricated rate).
- `collider_survival(ref, T, hold_s, [M])` — the duration-aware verdict (§4).

The interpretive band (`survival_verdict`, the 99 %/50 % edges) and the gas constant are **imported** from
`stability_horizon`, never re-declared, so the sibling cannot drift to a different SURVIVES edge or R.

## 4. The anti-fabrication guards (the whole point)

**(a) SURVIVES is the only CERTIFIED verdict; everything else DEFERS to UNKNOWN.** Warshay's fit is the
FORWARD, initial-rate, reverse-omitted channel. The irreversible `exp(-k' t)` therefore *undercounts* the true
surviving fraction — the omitted reverse recombination can only add Br₂ back, never remove more — so the
forward fraction is a rigorous **lower bound**: `true_fraction ≥ forward_fraction`. A SURVIVES read (forward
≥ 99 %) is thus sound (the truth is at least that intact). A sub-SURVIVES forward fraction does NOT certify
destruction (the omitted reverse may cap net loss at equilibrium), so a `DEGRADES` off the irreversible model
would be a **fabricated refutation** — refused. The model NEVER emits DEGRADES or MARGINAL; sub-SURVIVES fails
closed to UNKNOWN. The fast-at-shock-T fact lives in the reverse-free RATE (`dissociation_rate`; t½(1825 K,
1 atm) ≈ 66 µs).

**(b) No refutation from an out-of-window extrapolation.** In-window (1200–1900 K) reads are DERIVED; outside,
PREDICTED. Because only SURVIVES is ever certified, and a SURVIVES *below* the window is provably conservative
(colder is monotone-slower in *both* `exp(-Ea/RT)` and the √T prefactor; already ~14 orders from the flip at
298 K), the **bench SURVIVES is sound as a labelled PREDICTED reading**. An extrapolated *refutation* is the
forbidden direction and cannot occur by construction (guard (a) refuses every DEGRADES).

**(c) Scope: a W3 tendency of the MODELLED collisional channel**, never "Br₂ is stable" unconditionally
(photochemical/catalysed/aqueous fates are unmodelled). The bench SURVIVES is cross-referenced to the
**INDEPENDENT** ROUND-26 thermodynamic bearing (calorimetric CODATA ΔfH°/S°, computed by a different code path
from a different source family, and a different physical quantity — an equilibrium state function, not a
barrier): both agree Br₂ is stable at 298 K. The kinetic Ea (131.8 kJ/mol) is **below** the Br–Br bond enthalpy
(192.83 kJ/mol, R26) — the known **collisional-Ea-below-D₀** feature; it is carried honestly and never forced
to match the thermo quantity (forcing agreement between two different quantities would itself be fabrication).
The only coupling between the two bearings is *motivational* (both serve the desire to unblock DOW), mitigated
because SURVIVES is also the boring null ("colder → nothing happens"), not a surprising narrative-confirming
result.

The representative-point reproduction (1.574 × 10⁶) is labelled everywhere a **transcription self-consistency**
check that REUSES the fit — NOT an independent validation like N₂O₅'s ~7 % instrument check.

## 5. Ne/Kr — parked, not seeded

Only the **Ar** fit is seeded (the collider of Warshay's representative point; the litmus verdict needs one
collider reproduced and one bench extrapolation). The Ne/Kr coefficients are recorded in §2 for a future round
that needs a collider-comparison ("does the third body matter to Dow's process choice"), added then with that
caller named — not as live seed records with no consumer today.

## 6. The gate guard (a separate, self-standing change)

While reading the R23/R29 duration gate this round surfaced a **latent fabrication** in shipped code:
`_apply_duration_gate` (composability.py) flipped `DEGRADES → DEGENERATE` even when the survival fraction came
from an **out-of-window (PREDICTED) extrapolation** — a verdict-flipping refutation resting on an unvalidated
rate. Demonstrated: N₂O₅ (fit 298–338 K) held at 360 K → a fabricated DEGENERATE. Fixed as its **own commit**
(not bundled under the Br₂ litmus justification): an out-of-window DEGRADES now fails closed to UNKNOWN,
disclosing the extrapolated concern; an in-window DEGRADES is still a legitimate DEGENERATE (the guard is
surgical). RED-first regression:
`tests/test_duration_survival_gate.py::test_out_of_window_degrades_fails_closed_to_unknown_not_a_fabricated_degenerate`
(goes red on the pre-guard code). The asymmetry mirrors guard (b): an extrapolated SURVIVES is safe (colder is
slower), an extrapolated refutation is not. **Latent, not active:** the default kinetics seed matches no DAG
intermediate, so no live path reached it — byte-stable, no golden moved.

## 7. NOT built this round (tracked debt, not silent)

- **Live wire-in of the collider model into E1's duration gate.** The gate's contract is first-order s⁻¹
  single-reactant and carries no collider concentration; Br₂'s bench verdict is SURVIVES (verdict-inert in a
  tightening-only gate); no kitchen DAG reaches the 1200–1900 K in-window regime. Wiring it now would be
  machinery for a caller that does not exist. UNLOCK: a real Br₂-intermediate DAG with a declared collider
  state. (The R19→R23 precedent: `stability_horizon` shipped standalone, wired when a consumer appeared.)
- **The reverse-recombination / falloff kinetics** (an equilibrium-aware net-loss model) — deliberately out of
  scope; the lower-bound argument (guard (a)) makes the SURVIVES verdict sound *without* it.

## 8. The litmus verdict

Item 3b is closed as a **model + a sourced bench verdict**: Br₂'s thermal collisional dissociation channel
SURVIVES at any kitchen-achievable temperature (a DERIVED-from-known-physics PREDICTED reading, lower-bounded
and thermo-corroborated), and dissociates on a sub-ms timescale only at shock-tube temperatures (the sourced
reverse-free rate). The DOW litmus's decomposition question — thermodynamics (R26) + kinetics (R30) — is now
answered; only the brine-vs-mined **cost ranking** (Lane C) remains open.

## Reviews

- **butter-robot (pre-build, PASS with two TRIMs):** standalone module + deferred gate wire-in is correct YAGNI
  (real call site: the litmus verdict, not a self-mirror); new sibling is the smaller surface; **cut Ne/Kr to
  Ar-only** (folded); **cut the gate guard from the Br₂ commit** — its own change (folded: separate commit);
  no `ColliderKineticTable` class (folded: a bare tuple + linear-scan lookup).
- **birdperson (pre-build, SOUND-BUT-HEED):** bench SURVIVES-by-extrapolation is the *correct* call, not merely
  tolerable (refusing would itself violate known-physics); independence of the two bearings verified (not the
  reframed-check disease); the out-of-window-DEGRADES guard is a real latent fabrication, fix as its own commit
  with a RED-first test; harness must ASSERT. Breaches folded: reverse-recombination via the lower-bound
  operational trigger (HIGH); the gate guard (HIGH); transcription-not-validation label (MED); import-not-
  re-declare the band/R (MED); the three-leg warrant in the SURVIVES reason (LOW-MED); validate `[M]` (LOW).
- **evil-morty (post-build):** core signed off — the lower-bound argument proven airtight (`[Br₂](t) ≥
  [Br₂]₀·exp(−k_f[M]t)` by comparison, for constant excess [M]), bench SURVIVES sound + correctly graded, the
  transcription label honest everywhere, `[M]`/overflow/lookup/independence all unbroken, the gate guard
  surgical and unable to launder a degradation. Folds: **F1 (MED)** an above-window SURVIVES shipped a false
  *below-window* warrant ("colder is slower") → above-window SURVIVES-band now DEFERS to UNKNOWN (fixes the
  false warrant AND the Conjectured above-window-soundness residual in one move); **F2 (LOW)** `isfinite`
  guards on T and hold added; **negative-`n` residual** `t_exponent >= 0` guard added; **F3 (LOW, safe)** the
  gate `all_in_window` mixed-window over-reach is fail-closed (a completeness cost, never a fabrication) —
  documented as tracked debt, not fixed. Pre-existing R23 `temperature.hi` worst-case-within-a-segment noted
  as out of R30 scope.
