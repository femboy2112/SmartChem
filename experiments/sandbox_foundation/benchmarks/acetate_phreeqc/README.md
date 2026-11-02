# Acetate/water model vs PHREEQC — independent benchmark (Wave D, 2026-10-22)

An independent cross-check of `experiments/sandbox_foundation/aqueous_equilibrium.py`
(`AcetateWaterSystem.solve`) against **PHREEQC** (via `phreeqpython`), using thermodynamic
databases with **different constants and an extra species** than the SmartChem model carries,
so an agreement is evidence of implementation correctness rather than a tautology.

This is a committed record of a benchmark that was run in an **isolated scratch venv** (not the
main SmartChem venv, which stays free of `phreeqpython`). It is **outside `testpaths`** — it does
not run in the core suite or the sandbox CI job.

## Verdict (what the numbers support)

- **VERIFICATION-grade (Verified):** the corrected model reproduces PHREEQC acetate speciation to
  **|ΔpH| ≤ 0.015 for ionic strength I ≤ 0.10 M**, against *two* databases (minteq.v4, llnl). With
  PHREEQC's NaAc ion pair removed, the Davies speciation agrees to ~0.0003 pH for buffers up to
  I = 0.3. The model's Davies `pH_activity` at the C3 buffer is 4.6720, matching the module's own
  reference case (4.67201) — i.e. this benchmarks the post-Wave-A corrected model.
- **DIVERGE:** at I ≈ 0.45 (0.45 M Na-acetate) |ΔpH| ≈ 0.052 vs both databases. **Root cause: the
  model OMITS ion pairing (NaAc, logK ≈ −0.18 ⇒ K ≈ 0.66 M⁻¹).** Removing the pair from PHREEQC
  cuts that disagreement roughly in half. This is a model scope gap, **not** Davies invalidity
  (0.5 M is the standard Davies limit). It is why the model's `DAVIES_I_MAX = 0.5` admitted domain
  is *wider* than the demonstrated independent-agreement domain (~0.1 M for 0.02 pH, ~0.4 M for
  0.05 pH). Fed back to `aqueous_equilibrium.py` as a documented benchmark-agreement domain +
  ion-pair-omission limitation (do NOT read a bare `SOLVED` at I > ~0.1 M as independently
  benchmarked).
- **Genuine independence is thin.** Every acetic-acid pKa traces to the same Harned/MacInnes
  lineage, and minteq's Davies is the *same functional form* as the model's — so minteq agreement
  is an implementation check. Only **llnl** is a genuinely different activity model (B-dot), and it
  carries its own constant offsets (effective pKa 4.772, pKw 14.016 via its `-analytic` terms).
- **EXTERNAL VALIDATION — UNKNOWN.** No defensible independent *measured* pH/speciation datum for an
  acetate buffer at 25 °C was retrievable here (IUPAC primary PDFs were Cloudflare-blocked). Leads
  for a human: Partanen & Covington, *J. Chem. Eng. Data* 48(4), 797–807 (2003),
  doi:10.1021/je030100v; Buck et al., *Pure Appl. Chem.* 74, 2169 (2002). No measured value is used
  or fabricated. The `reaktoro_benchmark_obligation()` and this rung both stand at
  `EXTERNAL_VALIDATION_UNAVAILABLE`.

See `PREREGISTRATION.md` (written before any speciation run, with dated amendments A0–A7) and
`comparison_stdout.txt` / `comparison_table.json` for the full sweep.

## Round VI update (2026-10-23) — the NaAc(aq) ion pair is now MODELED (opt-in), closing the C5 divergence

Wave D *diagnosed* the C5 divergence as the omitted NaAc(aq) ion pair. Round VI ("The Salt Bridge") *acts* on that:
the model gains an **opt-in** ion pair, `AcetateWaterSystem(..., include_ion_pair=True)`, with association constant
`K_NAAC_ION_PAIR_25C` (logK = −0.18 at 25 °C, **NIST 46.4** via minteq.v4; provenance + uncertainty in the model file).
The PHREEQC reference is **unchanged** (it already included the pair; same inputs, same sha256-pinned DBs, deterministic),
so only the code side was re-run — see `ion_pair_comparison.py` / `ion_pair_comparison.json` / `ion_pair_comparison_stdout.txt`.

Result (code `pH_activity` vs the committed PHREEQC-with-pair `pH_ph`):

| case | I (M) | no-pair \|ΔpH\| | **with-pair \|ΔpH\|** | class shift |
|---|---|---|---|---|
| C3 (buffer) | 0.05 | 0.0090 | **0.0002** (minteq) | AGREE → AGREE |
| C4 (0.1 M NaAc) | 0.10 | 0.0129 | **0.0057** (minteq) | AGREE → AGREE |
| C5 (0.45 M NaAc) | 0.40 | 0.0517 / 0.0527 | **0.0229 / 0.0238** | **DIVERGE → MARGINAL** |

- **Worst case over all 28 rows: 0.0527 (2 DIVERGE) → 0.0238 (0 DIVERGE). No case diverges with the pair.**
- Against **minteq.v4** (the DB carrying the *same* logK −0.18 we adopted) every sodium case improves uniformly.
- Against **llnl** (a weaker pair, logK ≈ −0.079, *and* a different B-dot activity model) the high-I divergence is
  closed and every case stays AGREE, though the low-I buffer shifts slightly (our stronger pair over-corrects vs llnl's).
- The residual MARGINAL ~0.023 at C5 is **not** the ion pair — it is the Davies-vs-WATEQ-Debye-Hückel activity-model +
  molal/molar difference, which the pair does not touch (closing it would need a different *activity model*, not a
  different species set). That is why the pair-included caveat past 0.1 M speaks of an activity-model residual.
- **EXTERNAL VALIDATION still UNKNOWN.** The pair improves agreement with an independent *implementation* (PHREEQC); it
  is **not** validation against a *measured* datum. A fresh search (2026-10-23) reconfirmed the Wave D finding: the
  acetate buffer is not an NBS/NIST primary pH standard, and the acetate dissociation-constant literature
  (Harned/MacInnes lineage; Partanen & Covington 2003; Archer & Monk 1964 for the NaAc pair) shares the Ka provenance,
  so it is not an independent check of Ka. No measured datum is fabricated.

**Adversarial hardening (evil-morty, reproduced + fixed).** A read-only adversarial pass found that Route 2's `h_of_a`
catastrophically cancelled in the *basic* regime (free Na⁺ > free Ac⁻ ⇒ `-b + √(b²+4Kw_c)` subtracts near-equal large
numbers), which fails **closed** but spuriously *refused* every basic Na>C_T case the base model solves (e.g. 0.1/0.12,
0.1/0.4 — excess-base / NaOH-spiked acetate, where hydrolysis-suppressing pairing matters most). Fixed with the
cancellation-free conjugate branch `2·Kw_c/(b+√(…))` for b>0; regression test
`test_ion_pair_admits_basic_excess_base_regime_no_route2_cancellation`. The pre-registered C1–C5 results are
**unchanged** (they sit at Na≤C_T, b≈0, outside the cancellation regime). The adversary also flagged the gate's
sodium-balance check as a dead identity (it was computed on the gate's own re-derivation, which conserves Na by
construction); rewritten to guard `solve()`'s *reported* split. **No soundness break was found** — the solver fails
closed, and the γ-scaling direction, admission forgeability, conservation, and out-of-domain refusal all held.

## Database provenance (NOT committed — ~0.5–0.7 MB each; fetch to reproduce)

Official USGS phreeqc3 databases (the bundled `phreeqc.dat` has no acetate):

| file | sha256 | source |
|---|---|---|
| `minteq.v4.dat` (primary) | `4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3` | `raw.githubusercontent.com/usgs-coupled/phreeqc3/master/database/minteq.v4.dat` |
| `llnl.dat` (secondary) | `1324b807f0f864806fc42df308f6ca7c5e8ce2ed8060d76351452f76beeb819b` | `raw.githubusercontent.com/usgs-coupled/phreeqc3/master/database/llnl.dat` |

## Reproduce

```sh
python -m venv /tmp/wave-d-venv && /tmp/wave-d-venv/bin/pip install phreeqpython
# fetch the two databases above into ./db_dl/ and verify their sha256
# then see reproduce.sh (paths are illustrative of the scratch run):
#   run_phreeqc.py  -> phreeqc per-case speciation (inputs/*.pqi are the executable references)
#   run_code.py     -> AcetateWaterSystem.solve per case
#   compare.py      -> comparison_table.json + comparison_stdout.txt
#   diagnostics.py  -> isolates the ion-pair and constant-offset contributions
```

Cases: C1 pure water · C2 0.1 M HAc · C3 0.1 M HAc + 0.05 M Na (buffer) · C4 0.1 M NaAc ·
C5 0.45 M NaAc (near `DAVIES_I_MAX`) · C6 0.6 M NaAc (model correctly REFUSES: `NUMERICALLY_UNVERIFIED`).

**Stopping rule honored:** this establishes a domain of accuracy for *acetate* only. No carbonate/CO₂
chemistry was added on the back of it.
